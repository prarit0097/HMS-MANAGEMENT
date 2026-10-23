"""Read-only bounded audit projections. Stored payloads never form responses."""
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from uuid import UUID
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .authorization import branch_ids
from .identity_security import require_platform, require_session
from .models import AuditEvent, Organisation, Branch, Membership, Bed

ADMIN_ACTIONS = ('branch.created', 'bed.created', 'bed.changed', 'staff.created', 'staff.changed')
SELF_ACTIONS = tuple('security.' + action for action in ('enrolled', 'enrollment_started', 'login_verified', 'step_up', 'password', 'rotate', 'revoke', 'disable'))
MAX_INT = 2**63 - 1


def uuid_value(value):
    if not isinstance(value, str) or len(value) > 36:
        return None
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        return None


def bounded_int(value, minimum=0):
    return type(value) is int and minimum <= value <= MAX_INT


def short_string(value, length):
    return isinstance(value, str) and len(value) <= length


def user_label(user):
    if user and bounded_int(user.pk, 1) and short_string(user.username, 150):
        return {'id': user.pk, 'username': user.username}
    return None


def branch_label(branch):
    if branch and short_string(branch.name, 160) and short_string(branch.code, 32):
        return {'id': str(branch.pk), 'name': branch.name, 'code': branch.code}
    return None


def reference(row):
    if row.action in ('branch.created', 'bed.created', 'bed.changed'):
        return uuid_value(row.object_id) or ''
    value = row.object_id
    if isinstance(value, str) and len(value) <= 19 and re.fullmatch(r'[1-9][0-9]*', value) and int(value) <= MAX_INT:
        return value
    return ''


def summary(row):
    details = row.details if isinstance(row.details, dict) else {}
    method = details.get('method')
    return {'id': str(row.pk), 'created_at': row.created_at.isoformat(), 'action': row.action,
            'actor': user_label(row.actor), 'branch': branch_label(row.branch), 'object_id': reference(row),
            'method': method if row.action in SELF_ACTIONS and method in ('totp', 'backup_code') else None}


def organisation_for(user, organisation_id):
    require_platform(user)  # Pure reads: never create/lock an identity profile.
    parsed = serializers.UUIDField().run_validation(organisation_id)
    ids = branch_ids(user, 'platform.audit.read')
    if not ids:
        raise PermissionDenied('You do not have access to this action.')
    return get_object_or_404(Organisation.objects.filter(branch__id__in=ids).distinct(), pk=parsed)


def strict_query(query, allowed):
    if any(key not in allowed or len(query.getlist(key)) != 1 for key in query):
        raise ValidationError({'query': 'Use only the supported filters, once each.'})


def date_bound(value):
    try:
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})', value):
            raise ValueError()
        if not value.endswith('Z') and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
            raise ValueError()
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(dt_timezone.utc)
    except (ValueError, TypeError, OverflowError):
        raise ValidationError({'window': 'Use valid dates with an explicit timezone.'})


def page(queryset, request, organisation=None):
    query = request.query_params
    allowed = {'limit', 'offset', 'action', 'after', 'before'} | ({'branch'} if organisation else set())
    strict_query(query, allowed)
    def integer(key, default, minimum, maximum=None):
        value = query.get(key, str(default))
        if len(value) > 20 or not re.fullmatch(r'[0-9]+', value):
            raise ValidationError({key: 'Use a valid whole number.'})
        result = int(value)
        if result < minimum or (maximum is not None and result > maximum):
            raise ValidationError({key: 'This page is outside the supported range.'})
        return result
    limit = min(integer('limit', 25, 1), 100)
    offset = integer('offset', 0, 0, 10000)
    now = timezone.now()
    before = min(date_bound(query['before']), now) if 'before' in query else now
    try:
        after = date_bound(query['after']) if 'after' in query else before - timedelta(days=30)
        if after >= before or before - after > timedelta(days=90):
            raise ValueError()
    except (OverflowError, ValueError):
        raise ValidationError({'window': 'Choose a date window of up to 90 days.'})
    actions = ADMIN_ACTIONS if organisation else SELF_ACTIONS
    if 'action' in query:
        if query['action'] not in actions:
            raise ValidationError({'action': 'Choose a supported activity.'})
        queryset = queryset.filter(action=query['action'])
    if 'branch' in query:
        parsed = serializers.UUIDField().run_validation(query['branch'])
        branch = get_object_or_404(Branch.objects.filter(organisation=organisation), pk=parsed)
        queryset = queryset.filter(branch=branch)
    queryset = queryset.filter(created_at__gte=after, created_at__lt=before).order_by('-created_at', '-id')
    return {'count': queryset.count(), 'results': [summary(row) for row in queryset[offset:offset+limit]],
            'window': {'after': after.isoformat(), 'before': before.isoformat()}}


def detail(row, organisation):
    result = summary(row)
    safe, labels, truncated = {}, {}, False
    raw = row.details if isinstance(row.details, dict) else {}
    staff = row.action in ('staff.created', 'staff.changed')
    # Only bounded candidate assignment IDs are used in the scoped label query.
    candidates = set()
    if staff:
        for side in ('before', 'after'):
            snapshot = raw.get(side)
            assignments = snapshot.get('assignments') if isinstance(snapshot, dict) else None
            if isinstance(assignments, list):
                truncated |= len(assignments) > 1000
                for assignment in assignments[:1000]:
                    if isinstance(assignment, dict):
                        parsed = uuid_value(assignment.get('branch'))
                        if parsed: candidates.add(parsed)
    branches = {str(b.pk): b for b in Branch.objects.filter(organisation=organisation, pk__in=candidates)}
    for side in ('before', 'after'):
        snapshot = raw.get(side)
        if not isinstance(snapshot, dict):
            continue
        clean = {}
        if row.action == 'branch.created':
            for key, maximum in (('name', 160), ('code', 32)):
                if short_string(snapshot.get(key), maximum): clean[key] = snapshot[key]
        elif not staff:
            for key in ('number', 'room_number'):
                if short_string(snapshot.get(key), 32): clean[key] = snapshot[key]
            if isinstance(snapshot.get('category'), str) and snapshot['category'] in dict(Bed.CATEGORIES): clean['category'] = snapshot['category']
            if isinstance(snapshot.get('status'), str) and snapshot['status'] in dict(Bed.STATUSES): clean['status'] = snapshot['status']
            if bounded_int(snapshot.get('version')): clean['version'] = snapshot['version']
        else:
            if snapshot.get('status') in ('active', 'suspended'): clean['status'] = snapshot['status']
            if bounded_int(snapshot.get('version')): clean['version'] = snapshot['version']
            assignments = snapshot.get('assignments')
            if isinstance(assignments, list):
                clean['assignments'] = []
                for assignment in assignments[:1000]:
                    if not isinstance(assignment, dict): continue
                    branch_id = uuid_value(assignment.get('branch'))
                    role = assignment.get('role')
                    if branch_id in branches and isinstance(role, str) and role in dict(Membership.ROLES):
                        clean['assignments'].append({'branch': branch_id, 'role': role})
                        label = branch_label(branches[branch_id])
                        if label: labels[branch_id] = label
        safe[side] = clean
    target = None
    if staff:
        target_id = raw.get('target_user_id')
        if bounded_int(target_id, 1):
            safe['target_user_id'] = target_id
            target = user_label(get_user_model().objects.filter(pk=target_id, memberships__branch__organisation=organisation).distinct().first())
        if uuid_value(raw.get('organisation_id')) == str(organisation.pk): safe['organisation_id'] = str(organisation.pk)
    return {**result, 'details': safe, 'details_truncated': truncated, 'branch_labels': labels, 'target': target}


def administration_queryset(organisation):
    return AuditEvent.objects.filter(branch__organisation=organisation, action__in=ADMIN_ACTIONS).select_related('actor', 'branch')


class AdministrationHistory(APIView):
    def get(self, request, organisation_id):
        organisation = organisation_for(request.user, organisation_id)
        return Response(page(administration_queryset(organisation), request, organisation))


class AdministrationChange(APIView):
    def get(self, request, organisation_id, event_id):
        organisation = organisation_for(request.user, organisation_id)
        strict_query(request.query_params, set())
        parsed = serializers.UUIDField().run_validation(event_id)
        row = get_object_or_404(administration_queryset(organisation), pk=parsed)
        return Response(detail(row, organisation))


class OwnSecurityActivity(APIView):
    def get(self, request):
        require_session(request.user)
        queryset = AuditEvent.objects.filter(actor=request.user, branch__isnull=True, action__in=SELF_ACTIONS).select_related('actor', 'branch')
        return Response(page(queryset, request))
