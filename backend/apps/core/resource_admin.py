"""Organisation-scoped configuration services and their API adapter.

Configuration never grants operational/clinical permissions. Lock ordering is
organisation (branch creation) or branch then bed (bed configuration). Branch
locks use NO KEY UPDATE: allocation holds the bed while its admission's branch
foreign key acquires KEY SHARE, which must remain compatible with configuration.
"""
import re
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .authorization import branch_ids
from .models import Organisation, Branch, Bed, Admission, AuditEvent
from .pagination import BoundedPagination
from .serializers import StrictSerializer, ConcealedRelatedField
from .services import Conflict

CONFIG_STATUSES = ['available', 'cleaning', 'blocked']
BED_SNAPSHOT_FIELDS = ['number', 'room_number', 'category', 'status', 'version']


def configuration_organisation(user, organisation_id):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied('You do not have access to this action.')
    ids = branch_ids(user, 'platform.configure')
    if not ids:
        raise PermissionDenied('You do not have access to this action.')
    return get_object_or_404(Organisation.objects.filter(branch__id__in=ids).distinct(), pk=organisation_id)


class BranchConfiguration(StrictSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'code']
        read_only_fields = ['id']
        validators = []

    def validate_code(self, value):
        # Validate ASCII before uppercase so Unicode case expansion cannot
        # introduce aliases (for example sharp-s becoming SS).
        if not re.fullmatch(r'[A-Za-z0-9-]+', value):
            raise serializers.ValidationError('Use letters, numbers and hyphens only.')
        return value.upper()


class BedConfiguration(StrictSerializer):
    category = serializers.ChoiceField(choices=Bed.CATEGORIES)
    status = serializers.ChoiceField(choices=CONFIG_STATUSES, default='available')

    class Meta:
        model = Bed
        fields = ['id', 'branch', 'number', 'room_number', 'category', 'status', 'version']
        read_only_fields = ['id', 'version']
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        organisation = self.context.get('organisation')
        if organisation is not None:
            self.fields['branch'] = ConcealedRelatedField(queryset=Branch.objects.filter(organisation=organisation))

    def validate_number(self, value):
        return normalise_label(value)

    def validate_room_number(self, value):
        return normalise_label(value)


def normalise_label(value):
    value = value.strip().upper()
    if len(value) > 32:
        raise serializers.ValidationError('Use 32 characters or fewer.')
    return value


class BedChange(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    number = serializers.CharField(max_length=32, required=False)
    room_number = serializers.CharField(max_length=32, required=False)
    category = serializers.ChoiceField(choices=Bed.CATEGORIES, required=False)
    status = serializers.ChoiceField(choices=CONFIG_STATUSES, required=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({'non_field_errors': 'Send a JSON object with named fields.'})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: 'This field cannot be changed.' for key in unknown})
        return super().to_internal_value(data)

    def validate_number(self, value):
        return normalise_label(value)

    def validate_room_number(self, value):
        return normalise_label(value)


def snapshot(bed):
    return {field: getattr(bed, field) for field in BED_SNAPSHOT_FIELDS}


def configuration_audit(user, action, obj, branch, before, after):
    AuditEvent.objects.create(actor=user, action=action, object_id=str(obj.pk), branch=branch, details={'before': before, 'after': after})


@transaction.atomic
def create_branch(user, organisation_id, validated):
    organisation = configuration_organisation(user, organisation_id)
    organisation = Organisation.objects.select_for_update().get(pk=organisation.pk)
    if Branch.objects.filter(organisation=organisation, code__iexact=validated['code']).exists():
        raise Conflict('A branch with this code already exists. Use another code.')
    result = Branch.objects.create(organisation=organisation, **validated)
    configuration_audit(user, 'branch.created', result, result, {}, {'name': result.name, 'code': result.code})
    return result


@transaction.atomic
def create_bed(user, organisation_id, validated):
    organisation = configuration_organisation(user, organisation_id)
    branch = get_object_or_404(Branch.objects.select_for_update(no_key=True).filter(organisation=organisation), pk=validated['branch'].pk)
    if Bed.objects.filter(branch=branch, number__iexact=validated['number']).exists():
        raise Conflict('A bed with this number already exists in this branch. Use another number.')
    result = Bed.objects.create(**{**validated, 'branch': branch})
    configuration_audit(user, 'bed.created', result, branch, {}, snapshot(result))
    return result


@transaction.atomic
def change_bed(user, organisation_id, bed_id, validated):
    organisation = configuration_organisation(user, organisation_id)
    # Resolve the immutable branch first; then take locks in the same order as
    # bed creation, serialising duplicate-number checks across configuration.
    # NO KEY UPDATE allows admission FK KEY SHARE while allocation holds bed.
    selected = get_object_or_404(Bed.objects.filter(branch__organisation=organisation), pk=bed_id)
    branch = Branch.objects.select_for_update(no_key=True).get(pk=selected.branch_id)
    bed = Bed.objects.select_for_update().get(pk=bed_id)
    if bed.status in {'occupied', 'reserved'} or Admission.objects.filter(bed=bed, status='active').exists():
        raise Conflict('This bed has an active allocation and cannot be edited. Reload the bed inventory.')
    if bed.version != validated['expected_version']:
        raise Conflict('This bed changed. Reload the bed inventory before saving again.')
    number = validated.get('number', bed.number)
    if Bed.objects.filter(branch=branch, number__iexact=number).exclude(pk=bed.pk).exists():
        raise Conflict('A bed with this number already exists in this branch. Use another number.')
    before = snapshot(bed)
    for field in ['number', 'room_number', 'category', 'status']:
        if field in validated:
            setattr(bed, field, validated[field])
    bed.version += 1
    bed.save(update_fields=BED_SNAPSHOT_FIELDS)
    configuration_audit(user, 'bed.changed', bed, branch, before, snapshot(bed))
    return bed


class ConfigurationBranches(generics.ListCreateAPIView):
    serializer_class = BranchConfiguration
    pagination_class = BoundedPagination

    def get_queryset(self):
        organisation = configuration_organisation(self.request.user, self.kwargs['organisation_id'])
        return Branch.objects.filter(organisation=organisation)

    def create(self, request, *args, **kwargs):
        self.get_queryset()  # Authorise before validating any submitted fields.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = create_branch(request.user, kwargs['organisation_id'], serializer.validated_data)
        return Response(self.get_serializer(result).data, status=201)


class ConfigurationBeds(generics.ListCreateAPIView):
    serializer_class = BedConfiguration
    pagination_class = BoundedPagination

    def get_queryset(self):
        organisation = configuration_organisation(self.request.user, self.kwargs['organisation_id'])
        queryset = Bed.objects.filter(branch__organisation=organisation)
        branch_id = self.request.query_params.get('branch')
        if branch_id is not None:
            field = serializers.UUIDField()
            parsed = field.run_validation(branch_id)
            branch = get_object_or_404(Branch.objects.filter(organisation=organisation), pk=parsed)
            queryset = queryset.filter(branch=branch)
        return queryset

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'organisation': configuration_organisation(self.request.user, self.kwargs['organisation_id'])}

    def create(self, request, *args, **kwargs):
        self.get_queryset()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = create_bed(request.user, kwargs['organisation_id'], serializer.validated_data)
        return Response(self.get_serializer(result).data, status=201)


class ConfigurationBedDetail(APIView):
    def patch(self, request, organisation_id, pk):
        configuration_organisation(request.user, organisation_id)
        serializer = BedChange(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = change_bed(request.user, organisation_id, pk, serializer.validated_data)
        return Response(BedConfiguration(result).data)
