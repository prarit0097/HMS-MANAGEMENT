"""Scoped staff access services: organisation lock precedes actor reauthorisation."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404
from django.views.decorators.debug import sensitive_variables, sensitive_post_parameters
from django.utils.decorators import method_decorator
from rest_framework import serializers, generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .authorization import branch_ids
from .models import Organisation, Branch, Membership, StaffAccessRevision, AuditEvent
from .pagination import BoundedPagination
from .services import Conflict


def staff_organisation(user, organisation_id):
    ids = branch_ids(user, 'platform.staff.manage')
    if not ids:
        raise PermissionDenied('You do not have access to this action.')
    organisation_id = serializers.UUIDField().run_validation(organisation_id)
    return get_object_or_404(Organisation.objects.filter(branch__id__in=ids).distinct(), pk=organisation_id)


class StrictFields(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise ValidationError({'non_field_errors': 'Send a JSON object with named fields.'})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise ValidationError({key: 'This field cannot be changed.' for key in unknown})
        return super().to_internal_value(data)


class Assignment(StrictFields):
    branch = serializers.UUIDField()
    role = serializers.ChoiceField(choices=Membership.ROLES)


class AssignmentsMixin:
    def validate_assignments(self, value):
        pairs = {(row['branch'], row['role']) for row in value}
        if len(pairs) != len(value):
            raise ValidationError('Choose each branch and role only once.')
        organisation = self.context['organisation']
        selected = {row['branch'] for row in value}
        available = set(Branch.objects.filter(organisation=organisation, pk__in=selected).values_list('pk', flat=True))
        if selected != available:
            from rest_framework.exceptions import NotFound
            raise NotFound('Record not found.')
        return value


class StaffCreate(AssignmentsMixin, StrictFields):
    username = serializers.CharField(max_length=150, validators=get_user_model()._meta.get_field('username').validators)
    name = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=12, max_length=128, write_only=True, trim_whitespace=False)
    assignments = Assignment(many=True, min_length=1, max_length=100)

    @sensitive_variables('attrs')
    def validate(self, attrs):
        candidate = get_user_model()(username=attrs['username'], first_name=attrs['name'])
        try:
            validate_password(attrs['password'], user=candidate)
        except DjangoValidationError as exc:
            raise ValidationError({'password': exc.messages})
        return attrs


class StaffChange(AssignmentsMixin, StrictFields):
    expected_version = serializers.IntegerField(min_value=0)
    status = serializers.ChoiceField(choices=['active', 'suspended'], required=False)
    assignments = Assignment(many=True, min_length=1, max_length=100, required=False)

    def validate(self, attrs):
        if not {'status', 'assignments'} & set(attrs):
            raise ValidationError({'non_field_errors': 'Choose access status or assignments to change.'})
        return attrs


def staff_snapshot(rows, version):
    return {'status': 'active' if any(row.is_active for row in rows) else 'suspended', 'version': version,
            'assignments': [{'branch': str(row.branch_id), 'role': row.role} for row in rows]}


def staff_response(user, organisation):
    # READ COMMITTED may otherwise pair old assignments with a new version,
    # defeating the next edit's optimistic check. Retry a bounded read window.
    for _ in range(3):
        version = StaffAccessRevision.objects.filter(user=user, organisation=organisation).values_list('version', flat=True).first() or 0
        rows = list(Membership.objects.filter(user=user, branch__organisation=organisation).order_by('branch_id', 'role'))
        latest = StaffAccessRevision.objects.filter(user=user, organisation=organisation).values_list('version', flat=True).first() or 0
        if version == latest:
            return {'id': user.pk, 'username': user.username, 'name': user.get_full_name() or user.username,
                    'account_active': user.is_active, **staff_snapshot(rows, version)}
    raise Conflict('Staff access is changing. Reload staff before trying again.')


def staff_audit(actor, target, organisation, before, after, branch_id, action):
    AuditEvent.objects.create(actor=actor, action=action, object_id=str(target.pk), branch_id=branch_id,
        details={'target_user_id': target.pk, 'organisation_id': str(organisation.pk), 'before': before, 'after': after})


def locked_organisation(actor, organisation_id):
    # No permission decision before this lock may authorise the write. Sibling
    # admins racing to suspend one another must observe the winner's revocation.
    organisation_id = serializers.UUIDField().run_validation(organisation_id)
    organisation = get_object_or_404(Organisation.objects.select_for_update(), pk=organisation_id)
    return staff_organisation(actor, organisation.pk)


@sensitive_variables('validated', 'values', 'password')
@transaction.atomic
def create_staff(actor, organisation_id, validated):
    organisation = locked_organisation(actor, organisation_id)
    values = dict(validated)
    assignments = values.pop('assignments')
    password = values.pop('password')
    if get_user_model().objects.filter(username=values['username']).exists():
        raise Conflict('This username is unavailable. Choose another username.')
    try:
        with transaction.atomic():
            target = get_user_model().objects.create_user(username=values['username'], first_name=values['name'], password=password)
    except IntegrityError:
        raise Conflict('This username is unavailable. Choose another username.')
    # Revalidate the same organisation ceiling inside the transaction, including
    # direct service calls; callers cannot smuggle a foreign assignment.
    checked = StaffCreate(context={'organisation': organisation})
    checked.validate_assignments(assignments)
    Membership.objects.bulk_create([Membership(user=target, branch_id=row['branch'], role=row['role']) for row in assignments])
    StaffAccessRevision.objects.create(user=target, organisation=organisation, version=1)
    after = staff_response(target, organisation)
    staff_audit(actor, target, organisation, {}, {key: after[key] for key in ['status','version','assignments']}, assignments[0]['branch'], 'staff.created')
    return after


@transaction.atomic
def change_staff(actor, organisation_id, target_id, validated):
    organisation = locked_organisation(actor, organisation_id)
    if actor.pk == target_id:
        raise PermissionDenied('You cannot change your own staff access.')
    target = get_object_or_404(get_user_model().objects.filter(memberships__branch__organisation=organisation).distinct(), pk=target_id)
    rows = list(Membership.objects.select_for_update().filter(user=target, branch__organisation=organisation).order_by('branch_id','role'))
    revision = StaffAccessRevision.objects.select_for_update().filter(user=target, organisation=organisation).first()
    version = revision.version if revision else 0
    if version != validated['expected_version']:
        raise Conflict('This staff access changed. Reload staff before saving again.')
    before = staff_snapshot(rows, version)
    status = validated.get('status', before['status'])
    assignments = validated.get('assignments', [{'branch':row.branch_id,'role':row.role} for row in rows])
    StaffChange(context={'organisation': organisation}).validate_assignments(assignments)
    desired = {(row['branch'],row['role']) for row in assignments}
    for row in rows:
        if (row.branch_id,row.role) not in desired:
            row.delete()
    for branch_id, role in desired:
        Membership.objects.update_or_create(user=target, branch_id=branch_id, role=role, defaults={'is_active':status=='active'})
    if revision:
        revision.version += 1; revision.save(update_fields=['version'])
    else:
        StaffAccessRevision.objects.create(user=target, organisation=organisation, version=1)
    after = staff_response(target, organisation)
    staff_audit(actor, target, organisation, before, {key:after[key] for key in ['status','version','assignments']}, assignments[0]['branch'], 'staff.changed')
    return after


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
class StaffList(APIView):
    def get(self, request, organisation_id):
        organisation = staff_organisation(request.user, organisation_id)
        query = request.query_params.get('q','').strip()
        if len(query)>200:
            raise ValidationError({'q':'Search must be 200 characters or fewer.'})
        users = get_user_model().objects.filter(memberships__branch__organisation=organisation).annotate(display_name=Concat('first_name', Value(' '), 'last_name')).filter(Q(username__icontains=query)|Q(display_name__icontains=query)).distinct().order_by('username','id')
        paginator = BoundedPagination()
        rows = paginator.paginate_queryset(users, request, view=self)
        return paginator.get_paginated_response([staff_response(user,organisation) for user in rows])

    @sensitive_variables('request', 'serializer')
    def post(self, request, organisation_id):
        organisation = staff_organisation(request.user, organisation_id)
        serializer = StaffCreate(data=request.data, context={'organisation':organisation})
        serializer.is_valid(raise_exception=True)
        return Response(create_staff(request.user, organisation.pk, serializer.validated_data), status=201)


class StaffDetail(APIView):
    def patch(self, request, organisation_id, pk):
        organisation = staff_organisation(request.user, organisation_id)
        if request.user.pk == pk:
            raise PermissionDenied('You cannot change your own staff access.')
        serializer = StaffChange(data=request.data, context={'organisation':organisation})
        serializer.is_valid(raise_exception=True)
        return Response(change_staff(request.user, organisation.pk, pk, serializer.validated_data))


class StaffBranches(generics.ListAPIView):
    pagination_class = BoundedPagination
    def get(self, request, organisation_id):
        organisation = staff_organisation(request.user, organisation_id)
        rows = self.paginate_queryset(Branch.objects.filter(organisation=organisation))
        return self.get_paginated_response([{'id':str(row.pk),'name':row.name,'code':row.code} for row in rows])
