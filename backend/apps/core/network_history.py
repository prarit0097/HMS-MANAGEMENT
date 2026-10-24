"""Private, bounded network history projected field by field."""
from datetime import timedelta, timezone as dt_timezone
import re
from uuid import UUID
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.security.network_policy import canonical_policy
from .audit_history import date_bound
from .models import NetworkPolicyEvent
from .network_authority import require_network_operator, NetworkError
from .network_models import MAX_SAFE_INTEGER


def timestamp(value):
    try:
        if value.tzinfo is None:
            raise ValueError()
        return value.astimezone(dt_timezone.utc).isoformat().replace('+00:00', 'Z')
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise NetworkError('network_policy_unavailable', 503) from None


def _text(value, maximum, minimum=0):
    return type(value) is str and minimum <= len(value) <= maximum and all(ord(c) >= 32 and ord(c) != 127 for c in value)


def _policy(value):
    try:
        parsed = canonical_policy(value)
        return parsed if parsed == value else None
    except (ValueError, TypeError):
        return None


def event_projection(event):
    if not isinstance(event.pk, UUID) or event.action not in NetworkPolicyEvent.ACTIONS or event.outcome not in NetworkPolicyEvent.OUTCOMES or type(event.revision) is not int or not 1 <= event.revision <= MAX_SAFE_INTEGER or not _text(event.reason, 500, 10):
        raise NetworkError('network_policy_unavailable', 503)
    actor = event.actor
    actor_data = {'id': actor.pk, 'username': actor.username} if actor and type(actor.pk) is int and 1 <= actor.pk <= MAX_SAFE_INTEGER and _text(actor.username, 150, 1) else None
    return {'id': str(event.pk), 'created_at': timestamp(event.created_at), 'action': event.action, 'outcome': event.outcome, 'actor': actor_data, 'os_actor': event.os_actor if _text(event.os_actor, 150, 1) else None, 'reason': event.reason, 'change_id': str(event.change_id) if isinstance(event.change_id, UUID) else None, 'revision': event.revision, 'before': _policy(event.before_policy), 'after': _policy(event.after_policy)}


def network_history(context, query):
    _, _, owner_id, _, _ = require_network_operator(context)
    if any(key not in {'limit', 'offset', 'after', 'before', 'outcome'} or len(query.getlist(key)) != 1 for key in query):
        raise NetworkError('validation_error', 400)
    def integer(key, default, minimum, maximum):
        value = query.get(key, str(default))
        if type(value) is not str or len(value) > 5 or not re.fullmatch('[0-9]+', value) or not minimum <= int(value) <= maximum:
            raise NetworkError('validation_error', 400)
        return int(value)
    limit = integer('limit', 25, 1, 100)
    offset = integer('offset', 0, 0, 10000)
    try:
        if any(len(query[key]) > 35 for key in ('after', 'before') if key in query):
            raise ValueError()
        before = min(date_bound(query['before']), timezone.now()) if 'before' in query else timezone.now()
        after = date_bound(query['after']) if 'after' in query else before-timedelta(days=30)
        if after >= before or before-after > timedelta(days=90):
            raise ValueError()
    except (ValueError, OverflowError, ValidationError):
        raise NetworkError('validation_error', 400) from None
    events = NetworkPolicyEvent.objects.filter(owner_id=owner_id, created_at__gte=after, created_at__lt=before)
    if 'outcome' in query:
        if query['outcome'] not in NetworkPolicyEvent.OUTCOMES:
            raise NetworkError('validation_error', 400)
        events = events.filter(outcome=query['outcome'])
    count = events.count()
    results = [event_projection(event) for event in events.select_related('actor').order_by('-created_at', '-id')[offset:offset+limit]]
    if require_network_operator(context)[2] != owner_id:
        raise NetworkError('network_owner_unavailable', 503)
    return {'count': count, 'results': results, 'window': {'after': timestamp(after), 'before': timestamp(before)}}
