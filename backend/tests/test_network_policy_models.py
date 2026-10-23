"""Portable schema constraints; no middleware/locking/runtime authority claims."""
from datetime import timedelta
import hashlib
import json
import uuid

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.utils import timezone

POLICY = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
DIGEST = hashlib.sha256(json.dumps(POLICY, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
MAX = 9007199254740991


def model(name):
    found = next((m for m in apps.get_app_config('core').get_models() if m.__name__ == name), None)
    assert found is not None, f'{name} must be registered by core model discovery'
    return found


def test_network_models_are_discovered():
    for name in ['NetworkPolicyState', 'NetworkOperator', 'NetworkPolicyPreview', 'NetworkPolicyChange', 'NetworkPolicyEvent']:
        model(name)


@pytest.fixture
def rows(db):
    owner = apps.get_model('core', 'Organisation').objects.create(name='Synthetic network owner')
    user = get_user_model().objects.create(username='network-synthetic')
    now = timezone.now()
    state = model('NetworkPolicyState').objects.filter(pk=1).first()
    if state is None:  # Explicit local fixture after transaction-test flush, never runtime repair.
        state = model('NetworkPolicyState').objects.create(id=1, revision=1, confirmed_policy=POLICY, confirmed_policy_digest=DIGEST)
    return owner, user, now, state


def preview(rows, **overrides):
    owner, user, now, _ = rows
    values = dict(actor=user, owner=owner, session_digest='a'*64, epoch=0, operator_version=1,
                  verified_ip='192.0.2.1', environment_digest='b'*64, base_revision=1,
                  policy=POLICY, policy_digest=DIGEST, request_digest='c'*64, reason='Synthetic policy test',
                  normalisations=[], created_at=now, expires_at=now+timedelta(seconds=300), request_key=uuid.uuid4())
    values.update(overrides)
    return model('NetworkPolicyPreview').objects.create(**values)


def change(rows, **overrides):
    owner, user, now, _ = rows
    values = dict(owner=owner, actor=user, session_digest='a'*64, epoch=0, operator_version=1,
                  verified_ip='192.0.2.1', environment_digest='b'*64, candidate_policy=POLICY,
                  candidate_policy_digest=DIGEST, fallback_policy=POLICY, fallback_policy_digest=DIGEST,
                  base_revision=1, activation_revision=2, activated_at=now, rollback_at=now+timedelta(seconds=300),
                  reason='Synthetic policy test')
    values.update(overrides)
    return model('NetworkPolicyChange').objects.create(**values)


def rejects(operation):
    with pytest.raises(IntegrityError), transaction.atomic():
        operation()


@pytest.mark.django_db
@pytest.mark.parametrize('field,value', [('id', 2), ('revision', 0), ('revision', MAX+1)])
def test_state_database_bounds(rows, field, value):
    state = rows[3]
    rejects(lambda: model('NetworkPolicyState').objects.filter(pk=state.pk).update(**{field: value}))


@pytest.mark.django_db
def test_singleton_primary_key_and_explicit_flush_fixture(rows):
    assert rows[3].pk == 1
    rejects(lambda: model('NetworkPolicyState').objects.create(id=1, revision=1, confirmed_policy=POLICY, confirmed_policy_digest=DIGEST))


@pytest.mark.django_db
def test_operator_unique_and_protected(rows):
    owner, user, _, _ = rows
    cls = model('NetworkOperator')
    item = cls.objects.create(user=user, organisation=owner)
    rejects(lambda: cls.objects.create(user=user, organisation=owner))
    for version in [0, MAX+1]:
        rejects(lambda: cls.objects.filter(pk=item.pk).update(version=version))
    with pytest.raises(ProtectedError):
        user.delete()
    with pytest.raises(ProtectedError):
        owner.delete()


@pytest.mark.django_db
def test_preview_request_key_scope_and_pointer_uniqueness(rows):
    item = preview(rows)
    rejects(lambda: preview(rows, request_key=item.request_key))
    result = change(rows, preview=item)
    item.result_change = result
    item.save(update_fields=['result_change'])
    second = preview(rows)
    rejects(lambda: model('NetworkPolicyPreview').objects.filter(pk=second.pk).update(result_change=result))
    rejects(lambda: change(rows, preview=item, activation_revision=3))
    with pytest.raises(ProtectedError):
        result.delete()


@pytest.mark.django_db
@pytest.mark.parametrize('field,value', [('base_revision', 0), ('base_revision', MAX+1), ('epoch', -1), ('operator_version', 0)])
def test_preview_scalar_bounds(rows, field, value):
    rejects(lambda: preview(rows, **{field: value}))


@pytest.mark.django_db
@pytest.mark.parametrize('seconds', [-1, 0, 299, 301])
def test_preview_fixed_deadline(rows, seconds):
    rejects(lambda: preview(rows, expires_at=rows[2]+timedelta(seconds=seconds)))


@pytest.mark.django_db
@pytest.mark.parametrize('values', [dict(status='unknown'), dict(base_revision=0), dict(activation_revision=MAX+1), dict(activation_revision=1), dict(rollback_at=None), dict(status='confirmed'), dict(finished_at=timezone.now()), dict(terminal_revision=3), dict(confirm_expected_revision=0), dict(revert_expected_revision=MAX+1)])
def test_change_scalar_and_terminal_constraints(rows, values):
    rejects(lambda: change(rows, **values))


@pytest.mark.django_db
def test_change_unique_activation_fixed_deadline_and_terminal_order(rows):
    item = change(rows)
    rejects(lambda: change(rows))
    rejects(lambda: change(rows, activation_revision=3, rollback_at=rows[2]+timedelta(seconds=301)))
    rejects(lambda: model('NetworkPolicyChange').objects.filter(pk=item.pk).update(status='confirmed', finished_at=rows[2]-timedelta(seconds=1), terminal_revision=3))
    rejects(lambda: model('NetworkPolicyChange').objects.filter(pk=item.pk).update(status='confirmed', finished_at=rows[2], terminal_revision=2))
    assert model('NetworkPolicyChange').objects.filter(pk=item.pk).update(status='confirmed', finished_at=rows[2], terminal_revision=3) == 1


@pytest.mark.django_db
def test_event_private_accountability_and_constraints(rows):
    owner, user, now, _ = rows
    cls = model('NetworkPolicyEvent')
    item = cls.objects.create(actor=None, os_actor='synthetic-operator', owner=owner, action='operator.granted', outcome='granted', revision=1, reason='Synthetic grant test', created_at=now, target_user=user, entitlement_version_before=0, entitlement_version_after=1)
    for field, value in [('action', 'invalid'), ('outcome', 'invalid'), ('revision', 0), ('revision', MAX+1), ('entitlement_version_before', -1), ('entitlement_version_after', 0)]:
        rejects(lambda: cls.objects.filter(pk=item.pk).update(**{field: value}))
    with pytest.raises(ProtectedError):
        user.delete()
    assert any(index.fields == ['owner', '-created_at', '-id'] for index in cls._meta.indexes)


@pytest.mark.django_db(transaction=True)
def test_migration_upgrade_pristine_reverse_and_nonpristine_refusal(rows):
    old = [('core', '0006_audit_history_indexes')]
    latest = [('core', '0007_network_policy')]
    executor = MigrationExecutor(connection)
    try:
        executor.migrate(old)
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        state_apps = executor.loader.project_state(latest).apps
        cls = state_apps.get_model('core', 'NetworkPolicyState')
        assert list(cls.objects.values('id', 'revision', 'bound_owner_id', 'pending_change_id', 'confirmed_policy', 'confirmed_policy_digest')) == [dict(id=1, revision=1, bound_owner_id=None, pending_change_id=None, confirmed_policy=POLICY, confirmed_policy_digest=DIGEST)]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        cls.objects.filter(pk=1).update(revision=2)
        with pytest.raises(RuntimeError, match='pristine'):
            MigrationExecutor(connection).migrate(old)
        assert cls.objects.get(pk=1).revision == 2
    finally:
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db
@pytest.mark.parametrize('kind', ['NetworkOperator', 'NetworkPolicyPreview', 'NetworkPolicyChange', 'NetworkPolicyEvent'])
def test_pristine_reverse_refuses_every_nonempty_network_table(rows, kind):
    from importlib import import_module
    from types import SimpleNamespace
    owner, user, now, state = rows
    if kind == 'NetworkOperator':
        model(kind).objects.create(user=user, organisation=owner)
    elif kind == 'NetworkPolicyPreview':
        preview(rows)
    elif kind == 'NetworkPolicyChange':
        change(rows)
    else:
        model(kind).objects.create(owner=owner, action='owner.bound', outcome='bound', revision=1, reason='Synthetic owner binding', created_at=now)
    reverse = import_module('apps.core.migrations.0007_network_policy').reverse_pristine_only
    with pytest.raises(RuntimeError, match='pristine'):
        reverse(apps, SimpleNamespace(connection=connection))
    assert model('NetworkPolicyState').objects.get(pk=1).revision == state.revision
    assert model(kind).objects.count() == 1

@pytest.mark.django_db(transaction=True)
def test_migration_reverse_rejects_integer_in_boolean_policy(rows):
    latest = [('core', '0007_network_policy')]
    old = [('core', '0006_audit_history_indexes')]
    cls = model('NetworkPolicyState')
    cls.objects.filter(pk=1).update(confirmed_policy={'allowlist_only': 0, 'allowlist': [], 'blocklist': []})
    try:
        with pytest.raises(RuntimeError, match='pristine'):
            MigrationExecutor(connection).migrate(old)
        assert cls.objects.get(pk=1).confirmed_policy['allowlist_only'] == 0
        assert type(cls.objects.get(pk=1).confirmed_policy['allowlist_only']) is int
    finally:
        MigrationExecutor(connection).migrate(latest)
