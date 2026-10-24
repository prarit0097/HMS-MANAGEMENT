"""Transactional network changes. Frozen bindings, fixed deadlines, no GET repair."""
from copy import deepcopy
from datetime import timedelta
from uuid import UUID
import unicodedata
from django.db import transaction
from django.utils import timezone
from apps.security.network_policy import canonical_policy, policy_digest, validate_saved_policy
from .models import Organisation, NetworkPolicyState, NetworkPolicyPreview as Preview, NetworkPolicyChange as Change, NetworkPolicyEvent as Event
from .network_models import MAX_SAFE_INTEGER
from .network_authority import NetworkError, require_network_operator, lock_network_operator
from .network_environment import digest, environment_snapshot, overlay_allows
from .network_snapshot import _snapshot, _bindings, _sha, _integer, _aware, load_network_snapshot, NetworkStateUnavailable
from .network_history import timestamp


def revision(value):
    if type(value) is not int or not 1 <= value <= MAX_SAFE_INTEGER:
        raise NetworkError('validation_error', 400)
    return value


def uuid_value(value):
    try:
        if type(value) is not str or len(value) != 36 or str(UUID(value)) != value:
            raise ValueError()
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise NetworkError('validation_error', 400) from None


def reason_value(value):
    if type(value) is not str or not 10 <= len(value.strip()) <= 500 or any(unicodedata.category(c).startswith('C') for c in value):
        raise NetworkError('validation_error', 400)
    return value.strip()


def bump(state):
    if type(state.revision) is not int or not 1 <= state.revision < MAX_SAFE_INTEGER:
        raise NetworkError('network_policy_unavailable', 503)
    state.revision += 1


def deadline(now):
    try:
        return now+timedelta(seconds=300)
    except (OverflowError, ValueError):
        raise NetworkError('network_policy_unavailable', 503) from None


def snapshot_locked(state, now=None):
    try:
        state.refresh_from_db()
        return _snapshot(state, now or timezone.now())
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise NetworkStateUnavailable() from None


def _event(state, action, outcome, reason, *, actor_id=None, os_actor=None, change=None, before=None, after=None, **private):
    return Event.objects.create(owner_id=state.bound_owner_id, actor_id=actor_id, os_actor=os_actor, change=change, action=action, outcome=outcome, revision=state.revision, reason=reason, before_policy=deepcopy(before), after_policy=deepcopy(after), created_at=timezone.now(), **private)


def _result(change, state, now=None):
    return {'change_id': str(change.pk), 'outcome': change.status, 'activation_revision': change.activation_revision, 'revision': state.revision, 'activated_at': timestamp(change.activated_at), 'rollback_at': timestamp(change.rollback_at), 'finished_at': timestamp(change.finished_at) if change.finished_at else None, 'server_time': timestamp(now or timezone.now())}


def _binding(context, row, operator, *, preview=False):
    # Conceal actor/session guesses only after current authority has passed.
    if row.actor_id != context.actor_id or row.session_digest != context.session_digest:
        raise NetworkError('not_found', 404)
    owner_id = require_network_operator(context)[2]
    if row.owner_id != owner_id or row.epoch != context.epoch or row.operator_version != operator.version or row.verified_ip != context.verified_ip or row.environment_digest != context.environment_digest:
        raise NetworkError('network_preview_invalidated')
    try:
        _bindings(row)
        if reason_value(row.reason) != row.reason:
            raise ValueError()
        if isinstance(row, Preview):
            _sha(row.request_digest)
            validate_saved_policy(row.policy, row.policy_digest)
            if not _aware(row.created_at) or not _aware(row.expires_at) or row.expires_at != row.created_at+timedelta(seconds=300) or timezone.now() < row.created_at:
                raise ValueError()
            if type(row.normalisations) is not list or len(row.normalisations) > 200:
                raise ValueError()
            seen = set()
            for entry in row.normalisations:
                if type(entry) is not dict or set(entry) != {'list', 'index', 'input', 'canonical'} or entry['list'] not in ('allowlist', 'blocklist') or type(entry['index']) is not int or not 0 <= entry['index'] <= 99 or type(entry['canonical']) is not str or len(entry['canonical']) > 49:
                    raise ValueError()
                identity = (entry['list'], entry['index'])
                if identity in seen or entry['canonical'] not in row.policy[entry['list']]:
                    raise ValueError()
                seen.add(identity)
                single = canonical_policy({'allowlist_only': False, 'allowlist': [entry['input']], 'blocklist': []})['allowlist'][0]
                if single != entry['canonical'] or entry['input'] == single:
                    raise ValueError()
        else:
            validate_saved_policy(row.candidate_policy, row.candidate_policy_digest)
            validate_saved_policy(row.fallback_policy, row.fallback_policy_digest)
            _integer(row.activation_revision)
            if not _aware(row.activated_at) or not _aware(row.rollback_at) or row.rollback_at != row.activated_at+timedelta(seconds=300) or row.activation_revision != row.base_revision+1 or timezone.now() < row.activated_at:
                raise ValueError()
            if row.status not in Change.STATUSES:
                raise ValueError()
            if row.status == 'pending':
                if any(value is not None for value in (row.finished_at, row.terminal_revision, row.confirm_expected_revision, row.revert_expected_revision)):
                    raise ValueError()
            else:
                _integer(row.terminal_revision)
                if not _aware(row.finished_at) or row.finished_at < row.activated_at or row.terminal_revision <= row.activation_revision:
                    raise ValueError()
                for action, desired in (('confirm', 'confirmed'), ('revert', 'reverted')):
                    if getattr(row, action+'_expected_revision') != (row.activation_revision if row.status == desired else None):
                        raise ValueError()
            if row.preview_id is None:
                raise ValueError()
            saved = row.preview
            if saved.result_change_id != row.pk or any(getattr(saved, field) != getattr(row, field) for field in ('actor_id', 'owner_id', 'session_digest', 'epoch', 'operator_version', 'verified_ip', 'environment_digest', 'base_revision')) or saved.policy_digest != row.candidate_policy_digest or saved.reason != row.reason:
                raise ValueError()
            validate_saved_policy(saved.policy, saved.policy_digest)
            if not saved.created_at <= row.activated_at < saved.expires_at:
                raise ValueError()
    except (ValueError, TypeError, OverflowError, NetworkError):
        raise NetworkStateUnavailable() from None


def _reconcile_locked(state, *, os_actor=None, reason='Automatic deadline expiry'):
    snapshot = snapshot_locked(state)
    if snapshot.pending_status != 'expired_unreconciled':
        return False
    change = Change.objects.select_for_update().get(pk=state.pending_change_id)
    # Caller already holds singleton, preventing any other legitimate mutation.
    snapshot = snapshot_locked(state)
    if snapshot.pending_status != 'expired_unreconciled':
        return False
    now = timezone.now()
    bump(state)
    state.pending_change = None
    state.save(update_fields=['pending_change', 'revision'])
    change.status = 'expired'
    change.finished_at = now
    change.terminal_revision = state.revision
    change.save(update_fields=['status', 'finished_at', 'terminal_revision'])
    _event(state, 'policy.expired', 'expired', reason, os_actor=os_actor, change=change, before=snapshot.candidate_policy, after=snapshot.confirmed_policy)
    return True


def _run(context, callback, *, preview_id=None, change_id=None, preview_key=None):
    failure = None
    result = None
    with transaction.atomic():
        state = lock_network_operator(context)
        addressed_preview = None
        if preview_id is not None:
            addressed_preview = Preview.objects.select_for_update().filter(pk=preview_id).first()
        elif preview_key is not None:
            addressed_preview = Preview.objects.select_for_update().filter(actor_id=context.actor_id, request_key=preview_key).first()
        change_ids = {value for value in (state.pending_change_id, change_id, addressed_preview.result_change_id if addressed_preview else None) if value is not None}
        list(Change.objects.select_for_update().filter(pk__in=change_ids).order_by('pk'))
        require_network_operator(context)
        _reconcile_locked(state)
        require_network_operator(context)
        try:
            with transaction.atomic():
                result = callback(state)
        except NetworkError as exc:
            if exc.status_code in (401, 403, 503):
                raise
            failure = exc
            state.refresh_from_db()
            require_network_operator(context)
            _reconcile_locked(state)
        # Post-event INSERT/FK/unique wait: all authority, proof and effective path fresh.
        require_network_operator(context)
    if failure:
        raise failure
    return result


def read_network_state(context):
    _, _, owner_id, _, snapshot = require_network_operator(context)
    now = timezone.now()
    owner = Organisation.objects.get(pk=owner_id)
    if type(owner.name) is not str or len(owner.name) > 160:
        raise NetworkStateUnavailable()
    environment = environment_snapshot()
    final_owner = require_network_operator(context)[2]
    if final_owner != owner_id or snapshot.bound_owner_id != owner_id:
        raise NetworkError('network_owner_unavailable', 503)
    pending = None
    if snapshot.pending_change_id:
        pending = {'change_id': str(snapshot.pending_change_id), 'status': snapshot.pending_status, 'activated_at': timestamp(snapshot.activated_at), 'rollback_at': timestamp(snapshot.rollback_at), 'activation_revision': snapshot.activation_revision, 'candidate': snapshot.candidate_policy}
    return {'scope': 'deployment', 'revision': snapshot.revision, 'owner_organisation': {'id': str(owner_id), 'name': owner.name}, 'server_time': timestamp(now), 'verified_client_ip': context.verified_ip, 'confirmed_policy': snapshot.confirmed_policy, 'effective_policy': snapshot.effective_policy, 'pending': pending, 'environment_allows_current_ip': environment.allows(context.verified_ip), 'effective_allows_current_ip': environment.allows(context.verified_ip) and overlay_allows(snapshot.effective_policy, context.verified_ip)}


def _normalisations(raw):
    result = []
    for name in ('allowlist', 'blocklist'):
        for index, value in enumerate(raw[name]):
            canonical = canonical_policy({'allowlist_only': False, 'allowlist': [value] if name == 'allowlist' else [], 'blocklist': [value] if name == 'blocklist' else []})[name][0]
            if canonical != value:
                result.append({'list': name, 'index': index, 'input': value, 'canonical': canonical})
    return result


def _preview_projection(preview, context):
    env_allows = environment_snapshot().allows(context.verified_ip)
    candidate_allows = overlay_allows(preview.policy, context.verified_ip)
    return {'preview_id': str(preview.pk), 'base_revision': preview.base_revision, 'policy': deepcopy(preview.policy), 'normalisations': deepcopy(preview.normalisations), 'current_path': {'environment_allows': env_allows, 'candidate_allows': candidate_allows, 'effective_allows': env_allows and candidate_allows}, 'can_activate': env_allows and candidate_allows, 'created_at': timestamp(preview.created_at), 'expires_at': timestamp(preview.expires_at), 'server_time': timestamp(timezone.now())}


def preview_network_policy(context, expected_revision, policy, reason, request_key):
    revision(expected_revision)
    key = uuid_value(request_key)
    original_reason = reason
    reason = reason_value(reason)
    try:
        canonical = canonical_policy(policy)
        normalisations = _normalisations(policy)
    except (ValueError, TypeError):
        raise NetworkError('validation_error', 400) from None
    request_digest = digest({'expected_revision': expected_revision, 'policy': policy, 'reason': original_reason})
    def operation(state):
        _, _, owner_id, operator, snapshot = require_network_operator(context)
        existing = Preview.objects.select_for_update().filter(actor_id=context.actor_id, request_key=key).first()
        if existing:
            _binding(context, existing, operator, preview=True)
            if existing.request_digest != request_digest:
                raise NetworkError('idempotency_conflict')
            if timezone.now() >= existing.expires_at:
                raise NetworkError('network_preview_expired')
            return _preview_projection(existing, context), False
        if state.revision != expected_revision:
            raise NetworkError('network_revision_conflict')
        if state.pending_change_id:
            raise NetworkError('network_change_pending')
        now = timezone.now()
        expires = deadline(now)
        preview = Preview.objects.create(actor_id=context.actor_id, owner_id=owner_id, session_digest=context.session_digest, epoch=context.epoch, operator_version=operator.version, verified_ip=context.verified_ip, environment_digest=context.environment_digest, base_revision=state.revision, policy=canonical, policy_digest=policy_digest(canonical), request_digest=request_digest, reason=reason, normalisations=normalisations, created_at=now, expires_at=expires, request_key=key)
        require_network_operator(context)
        if timezone.now() >= preview.expires_at:
            raise NetworkError('network_preview_expired')
        return _preview_projection(preview, context), True
    return _run(context, operation, preview_key=key)


def activate_network_preview(context, preview_id, expected_revision):
    preview_id = uuid_value(preview_id)
    revision(expected_revision)
    def operation(state):
        operator = require_network_operator(context)[3]
        preview = Preview.objects.select_for_update().filter(pk=preview_id).first()
        if not preview:
            raise NetworkError('not_found', 404)
        _binding(context, preview, operator, preview=True)
        if preview.base_revision != expected_revision:
            raise NetworkError('network_revision_conflict')
        if preview.result_change_id:
            change = Change.objects.select_for_update().get(pk=preview.result_change_id)
            _binding(context, change, operator)
            if change.preview_id != preview.pk or change.candidate_policy_digest != preview.policy_digest:
                raise NetworkStateUnavailable()
            return _result(change, state)
        if timezone.now() >= preview.expires_at:
            raise NetworkError('network_preview_expired')
        snapshot = snapshot_locked(state)
        if state.revision != expected_revision:
            raise NetworkError('network_revision_conflict')
        if state.pending_change_id:
            raise NetworkError('network_change_pending')
        if not environment_snapshot().allows(context.verified_ip) or not overlay_allows(preview.policy, context.verified_ip):
            raise NetworkError('validation_error', 400, 'These settings would block your current network. Add your current address and preview again.')
        now = timezone.now()
        rollback_at = deadline(now)
        bump(state)
        change = Change.objects.create(preview=preview, owner_id=preview.owner_id, actor_id=context.actor_id, session_digest=context.session_digest, epoch=context.epoch, operator_version=operator.version, verified_ip=context.verified_ip, environment_digest=context.environment_digest, candidate_policy=preview.policy, candidate_policy_digest=preview.policy_digest, fallback_policy=snapshot.confirmed_policy, fallback_policy_digest=policy_digest(snapshot.confirmed_policy), base_revision=expected_revision, activation_revision=state.revision, activated_at=now, rollback_at=rollback_at, reason=preview.reason)
        preview.result_change = change
        preview.save(update_fields=['result_change'])
        state.pending_change = change
        state.save(update_fields=['pending_change', 'revision'])
        _event(state, 'policy.activated', 'pending', preview.reason, actor_id=context.actor_id, change=change, before=snapshot.confirmed_policy, after=preview.policy)
        require_network_operator(context)
        if timezone.now() >= preview.expires_at:
            raise NetworkError('network_preview_expired')
        if timezone.now() >= change.rollback_at:
            raise NetworkError('network_change_expired')
        return _result(change, state)
    return _run(context, operation, preview_id=preview_id)


def finish_network_change(context, change_id, expected_revision, action):
    change_id = uuid_value(change_id)
    revision(expected_revision)
    if action not in ('confirm', 'revert'):
        raise NetworkError('validation_error', 400)
    def operation(state):
        operator = require_network_operator(context)[3]
        change = Change.objects.select_for_update().filter(pk=change_id).first()
        if not change:
            raise NetworkError('not_found', 404)
        _binding(context, change, operator)
        if change.activation_revision != expected_revision:
            raise NetworkError('network_revision_conflict')
        desired = 'confirmed' if action == 'confirm' else 'reverted'
        if change.status == 'expired':
            raise NetworkError('network_change_expired')
        if change.status != 'pending':
            if change.status == desired and getattr(change, action+'_expected_revision') == expected_revision:
                return _result(change, state)
            raise NetworkError('network_change_finished')
        snapshot = snapshot_locked(state)
        if timezone.now() >= change.rollback_at:
            raise NetworkError('network_change_expired')
        if state.pending_change_id != change.pk or state.revision != expected_revision:
            raise NetworkError('network_revision_conflict')
        selected = change.candidate_policy if action == 'confirm' else change.fallback_policy
        bump(state)
        state.confirmed_policy = deepcopy(selected)
        state.confirmed_policy_digest = policy_digest(selected)
        state.pending_change = None
        state.save(update_fields=['confirmed_policy', 'confirmed_policy_digest', 'pending_change', 'revision'])
        change.status = desired
        change.finished_at = timezone.now()
        change.terminal_revision = state.revision
        setattr(change, action+'_expected_revision', expected_revision)
        change.save(update_fields=['status', 'finished_at', 'terminal_revision', action+'_expected_revision'])
        _event(state, 'policy.'+desired, desired, change.reason, actor_id=context.actor_id, change=change, before=snapshot.effective_policy, after=selected)
        require_network_operator(context)
        if timezone.now() >= change.rollback_at:
            raise NetworkError('network_change_expired')
        return _result(change, state)
    return _run(context, operation, change_id=change_id)


def reconcile_expired_policy(oob_context):
    from .network_oob import require_oob
    require_oob(oob_context)
    with transaction.atomic():
        state = NetworkPolicyState.objects.select_for_update().get(pk=1)
        changed = _reconcile_locked(state, os_actor=oob_context.os_actor, reason=oob_context.reason)
        return {'changed': changed, 'revision': state.revision}
