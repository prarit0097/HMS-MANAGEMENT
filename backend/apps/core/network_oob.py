"""Typed local OS authority for explicit network bootstrap and recovery."""
from dataclasses import dataclass
from copy import deepcopy
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from apps.security.network_policy import validate_saved_policy, policy_digest
from .models import Organisation, Membership, IdentitySecurity, NetworkPolicyState as State, NetworkOperator, NetworkPolicyChange as Change
from .network_authority import NetworkError
from .network_environment import configured_owner
from .network_access import reason_value, uuid_value, revision, bump, snapshot_locked, _event, _reconcile_locked


@dataclass(frozen=True)
class OutOfBandContext:
    os_actor: str
    reason: str

    def __post_init__(self):
        if type(self.os_actor) is not str or not 1 <= len(self.os_actor) <= 150 or any(not c.isprintable() for c in self.os_actor):
            raise NetworkError('validation_error', 400)
        object.__setattr__(self, 'reason', reason_value(self.reason))


def require_oob(context):
    if type(context) is not OutOfBandContext:
        raise NetworkError('permission_denied', 403)
    context.__post_init__()


def _owner(state, organisation_id=None, *, unbound=False):
    owner = configured_owner()
    if not owner or (organisation_id is not None and owner != organisation_id) or (state.bound_owner_id is not None and state.bound_owner_id != owner) or (not unbound and state.bound_owner_id != owner):
        raise NetworkError('network_owner_unavailable', 503)
    return owner


def _expected(state, expected):
    if state.revision != revision(expected):
        raise NetworkError('network_revision_conflict')


def inspect_policy(context):
    require_oob(context)
    from .network_snapshot import load_network_snapshot
    snapshot = load_network_snapshot(timezone.now())
    return {'revision': snapshot.revision, 'bound_owner': str(snapshot.bound_owner_id) if snapshot.bound_owner_id else None, 'confirmed_policy': snapshot.confirmed_policy, 'effective_policy': snapshot.effective_policy, 'pending_status': snapshot.pending_status}


def bind_owner(context, organisation_id, expected_revision):
    require_oob(context)
    owner_id = uuid_value(organisation_id)
    with transaction.atomic():
        Organisation.objects.select_for_update(no_key=True).get(pk=owner_id)
        state = State.objects.select_for_update().get(pk=1)
        snapshot_locked(state)
        _owner(state, owner_id, unbound=True)
        _expected(state, expected_revision)
        if state.bound_owner_id is not None:
            raise NetworkError('network_revision_conflict')
        bump(state)
        state.bound_owner_id = owner_id
        state.save(update_fields=['bound_owner', 'revision'])
        _event(state, 'owner.bound', 'bound', context.reason, os_actor=context.os_actor)
        _owner(state, owner_id)
        return {'revision': state.revision, 'outcome': 'bound'}


def change_operator(context, organisation_id, user_id, expected_version, expected_revision, action):
    require_oob(context)
    owner_id = uuid_value(organisation_id)
    if type(user_id) is not int or not 1 <= user_id <= 9007199254740991 or type(expected_version) is not int or not 0 <= expected_version <= 9007199254740991 or action not in ('grant', 'revoke'):
        raise NetworkError('validation_error', 400)
    failure = None
    result = None
    with transaction.atomic():
        user = get_user_model().objects.select_for_update(no_key=True).get(pk=user_id)
        IdentitySecurity.objects.select_for_update().filter(user_id=user_id).first()
        Organisation.objects.select_for_update(no_key=True).get(pk=owner_id)
        operator = NetworkOperator.objects.select_for_update().filter(user_id=user_id, organisation_id=owner_id).first()
        state = State.objects.select_for_update().get(pk=1)
        snapshot_locked(state)
        _owner(state, owner_id)
        _reconcile_locked(state, os_actor=context.os_actor, reason=context.reason)
        if state.revision != revision(expected_revision):
            failure = NetworkError('network_revision_conflict')
        elif (operator.version if operator else 0) != expected_version:
            failure = NetworkError('network_revision_conflict')
        elif action == 'grant' and (not user.is_active or not Membership.objects.filter(user_id=user_id, is_active=True, role='master_admin', branch__organisation_id=owner_id).exists()):
            failure = NetworkError('permission_denied', 403)
        elif action == 'revoke' and operator is None:
            failure = NetworkError('network_revision_conflict')
        else:
            if expected_version >= 9007199254740991:
                raise NetworkError('network_policy_unavailable', 503)
            before = expected_version
            if operator is None:
                operator = NetworkOperator.objects.create(user_id=user_id, organisation_id=owner_id, active=True, version=1)
            else:
                operator.version += 1
                operator.active = action == 'grant'
                operator.save(update_fields=['version', 'active', 'updated_at'])
            _event(state, 'operator.granted' if action == 'grant' else 'operator.revoked', 'granted' if action == 'grant' else 'revoked', context.reason, os_actor=context.os_actor, target_user_id=user_id, entitlement_version_before=before, entitlement_version_after=operator.version)
            _owner(state, owner_id)
            snapshot_locked(state)
            result = {'revision': state.revision, 'version': operator.version, 'active': operator.active, 'recovery_dependency': 'A revoked pending initiator must wait for automatic rollback or use audited OS recovery.' if action == 'revoke' else None}
    if failure:
        raise failure
    return result


def _recover_policy(context, change_id, snapshot, expected_revision, *, apply=False):
    require_oob(context)
    change_id = uuid_value(change_id)
    revision(expected_revision)
    if snapshot not in ('candidate', 'fallback') or type(apply) is not bool:
        raise NetworkError('validation_error', 400)
    with transaction.atomic():
        owner_id = configured_owner()
        if not owner_id:
            raise NetworkError('network_owner_unavailable', 503)
        Organisation.objects.select_for_update(no_key=True).get(pk=owner_id)
        state = State.objects.select_for_update().get(pk=1)
        current = snapshot_locked(state)
        _owner(state)
        _expected(state, expected_revision)
        ids = {change_id} | ({state.pending_change_id} if state.pending_change_id else set())
        changes = {item.pk: item for item in Change.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
        addressed = changes.get(change_id)
        if not addressed or addressed.owner_id != owner_id:
            raise NetworkError('not_found', 404)
        try:
            candidate = validate_saved_policy(addressed.candidate_policy, addressed.candidate_policy_digest)
            fallback = validate_saved_policy(addressed.fallback_policy, addressed.fallback_policy_digest)
        except (ValueError, TypeError):
            raise NetworkError('network_policy_unavailable', 503) from None
        selected = candidate if snapshot == 'candidate' else fallback
        result = {'applied': apply, 'revision': state.revision, 'before': current.effective_policy, 'after': selected}
        if not apply:
            return result
        bump(state)
        if state.pending_change_id:
            pending = changes[state.pending_change_id]
            pending.status = 'recovered'
            pending.finished_at = timezone.now()
            pending.terminal_revision = state.revision
            pending.save(update_fields=['status', 'finished_at', 'terminal_revision'])
        state.confirmed_policy = deepcopy(selected)
        state.confirmed_policy_digest = policy_digest(selected)
        state.pending_change = None
        state.save(update_fields=['confirmed_policy', 'confirmed_policy_digest', 'pending_change', 'revision'])
        _event(state, 'policy.recovered', 'recovered', context.reason, os_actor=context.os_actor, change=addressed, before=current.effective_policy, after=selected)
        _owner(state)
        snapshot_locked(state)
        result['revision'] = state.revision
        return result


def _transfer_owner(context, previous_owner, new_owner, expected_revision, *, apply=False):
    require_oob(context)
    old_id, new_id = uuid_value(previous_owner), uuid_value(new_owner)
    revision(expected_revision)
    if old_id == new_id or type(apply) is not bool:
        raise NetworkError('validation_error', 400)
    with transaction.atomic():
        for owner in sorted([old_id, new_id]):
            Organisation.objects.select_for_update(no_key=True).get(pk=owner)
        state = State.objects.select_for_update().get(pk=1)
        current = snapshot_locked(state)
        if configured_owner() != new_id or state.bound_owner_id != old_id:
            raise NetworkError('network_owner_unavailable', 503)
        _expected(state, expected_revision)
        result = {'applied': apply, 'revision': state.revision, 'confirmed_policy': current.confirmed_policy, 'entitlements_copied': False}
        if not apply:
            return result
        if state.pending_change_id:
            pending = Change.objects.select_for_update().get(pk=state.pending_change_id)
            snapshot_locked(state)
        bump(state)
        if state.pending_change_id:
            pending.status = 'owner_transferred'
            pending.finished_at = timezone.now()
            pending.terminal_revision = state.revision
            pending.save(update_fields=['status', 'finished_at', 'terminal_revision'])
        state.bound_owner_id = new_id
        state.pending_change = None
        state.save(update_fields=['bound_owner', 'pending_change', 'revision'])
        _event(state, 'owner.transferred', 'transferred', context.reason, os_actor=context.os_actor, change=pending if current.pending_change_id else None, before=current.effective_policy, after=current.confirmed_policy, previous_owner_id=old_id, new_owner_id=new_id)
        _owner(state)
        snapshot_locked(state)
        result['revision'] = state.revision
        return result


def _maintenance_operation(context, expected_revision, owners, operation, *, addressed_change=None, transfer=False):
    """Commit valid expiry even if a later requested OS operation conflicts."""
    require_oob(context)
    revision(expected_revision)
    failure = None
    result = None
    with transaction.atomic():
        for owner in sorted(set(owners)):
            Organisation.objects.select_for_update(no_key=True).get(pk=owner)
        state = State.objects.select_for_update().get(pk=1)
        snapshot_locked(state)
        if transfer:
            if state.bound_owner_id != owners[0] or configured_owner() != owners[1]:
                raise NetworkError('network_owner_unavailable', 503)
        else:
            _owner(state)
        ids = {value for value in (state.pending_change_id, addressed_change) if value is not None}
        list(Change.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
        _reconcile_locked(state, os_actor=context.os_actor, reason=context.reason)
        try:
            with transaction.atomic():
                _expected(state, expected_revision)
                result = operation()
        except NetworkError as exc:
            if exc.status_code in (401, 403, 503):
                raise
            failure = exc
        snapshot_locked(state)
    if failure:
        raise failure
    return result


def recover_policy(context, change_id, snapshot, expected_revision, *, apply=False):
    if not apply:
        return _recover_policy(context, change_id, snapshot, expected_revision, apply=apply)
    owner = configured_owner()
    if not owner:
        raise NetworkError('network_owner_unavailable', 503)
    addressed = uuid_value(change_id)
    return _maintenance_operation(context, expected_revision, [owner], lambda: _recover_policy(context, change_id, snapshot, expected_revision, apply=True), addressed_change=addressed)


def transfer_owner(context, previous_owner, new_owner, expected_revision, *, apply=False):
    if not apply:
        return _transfer_owner(context, previous_owner, new_owner, expected_revision, apply=apply)
    old_id, new_id = uuid_value(previous_owner), uuid_value(new_owner)
    return _maintenance_operation(context, expected_revision, [old_id, new_id], lambda: _transfer_owner(context, previous_owner, new_owner, expected_revision, apply=True), transfer=True)
