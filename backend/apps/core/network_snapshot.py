"""Coherent read-only selection of a stored network overlay.

This is an internal data-consistency boundary, not an authority check or a
request decision. The environment ceiling and current authority belong to
the later adapters. Never repair unavailable state here.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError
from django.utils.timezone import is_aware

from apps.security.ip_policy import _address
from apps.security.network_policy import validate_saved_policy
from .network_models import MAX_SAFE_INTEGER, NetworkPolicyState


class NetworkStateUnavailable(Exception):
    """The stored graph cannot safely supply an effective policy."""

    def __init__(self):
        super().__init__('Network policy state is unavailable')


@dataclass(frozen=True)
class NetworkSnapshot:
    revision: int
    bound_owner_id: UUID | None
    confirmed_policy: dict
    effective_policy: dict
    pending_change_id: UUID | None
    pending_status: str | None
    candidate_policy: dict | None
    activated_at: datetime | None
    rollback_at: datetime | None
    activation_revision: int | None


def _require(condition):
    if not condition:
        raise ValueError('Invalid stored network state')


def _integer(value, minimum=1):
    _require(type(value) is int and minimum <= value <= MAX_SAFE_INTEGER)


def _aware(value):
    return isinstance(value, datetime) and is_aware(value)


def _sha(value):
    _require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value))


def _bindings(record):
    _require(record.actor_id is not None)
    _sha(record.session_digest)
    _sha(record.environment_digest)
    _integer(record.epoch, minimum=0)
    _integer(record.operator_version)
    _integer(record.base_revision)
    _require(type(record.verified_ip) is str and str(_address(record.verified_ip)) == record.verified_ip)


def _snapshot(state, now):
    _require(type(state.pk) is int and state.pk == 1)
    _integer(state.revision)
    confirmed = validate_saved_policy(state.confirmed_policy, state.confirmed_policy_digest)
    if state.pending_change_id is None:
        return NetworkSnapshot(state.revision, state.bound_owner_id, confirmed, deepcopy(confirmed),
                               None, None, None, None, None, None)

    change = state.pending_change
    _require(change is not None and change.pk == state.pending_change_id)
    candidate = validate_saved_policy(change.candidate_policy, change.candidate_policy_digest)
    fallback = validate_saved_policy(change.fallback_policy, change.fallback_policy_digest)
    _require(fallback == confirmed and change.fallback_policy_digest == state.confirmed_policy_digest)
    _require(state.bound_owner_id is not None and change.owner_id == state.bound_owner_id)
    _bindings(change)
    _integer(change.activation_revision)
    _require(change.base_revision + 1 == change.activation_revision == state.revision)
    _require(change.status == 'pending' and all(getattr(change, field) is None for field in
             ['finished_at', 'terminal_revision', 'confirm_expected_revision', 'revert_expected_revision']))
    _require(_aware(change.activated_at) and _aware(change.rollback_at))
    _require(change.rollback_at == change.activated_at + timedelta(seconds=300))
    _require(change.preview_id is not None)
    preview = change.preview
    _require(preview is not None and preview.pk == change.preview_id and preview.result_change_id == change.pk)
    _bindings(preview)
    _sha(preview.request_digest)
    for field in ['owner_id', 'actor_id', 'base_revision', 'session_digest', 'epoch', 'operator_version', 'verified_ip', 'environment_digest']:
        _require(getattr(preview, field) == getattr(change, field))
    preview_policy = validate_saved_policy(preview.policy, preview.policy_digest)
    _require(preview_policy == candidate and preview.policy_digest == change.candidate_policy_digest)
    _require(_aware(preview.created_at) and _aware(preview.expires_at))
    _require(preview.expires_at == preview.created_at + timedelta(seconds=300))
    _require(preview.created_at <= change.activated_at < preview.expires_at)
    _require(now >= change.activated_at)
    active = now < change.rollback_at
    return NetworkSnapshot(state.revision, state.bound_owner_id, confirmed,
        deepcopy(candidate if active else fallback), change.pk,
        'pending' if active else 'expired_unreconciled', candidate,
        change.activated_at, change.rollback_at, change.activation_revision)


def load_network_snapshot(now: datetime) -> NetworkSnapshot:
    """Load a single joined statement snapshot, validate fully, then select."""
    if not _aware(now):
        raise ValueError('An aware datetime is required')
    try:
        state = NetworkPolicyState.objects.select_related('pending_change__preview').get(pk=1)
        return _snapshot(state, now)
    except (DatabaseError, ObjectDoesNotExist, ValueError, TypeError, OverflowError, AttributeError):
        raise NetworkStateUnavailable() from None
