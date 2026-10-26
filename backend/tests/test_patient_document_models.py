"""Dormant schema guarantees only; no upload, authorisation or disclosure service."""
from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock
import hashlib
import uuid

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.utils import timezone

NAMES = ['PatientDocumentIntent', 'DocumentIntentReceipt', 'DocumentAccessEvent']


def model(name):
    found = next((m for m in apps.get_app_config('core').get_models() if m.__name__ == name), None)
    assert found is not None, f'{name} must be registered by core model discovery'
    return found


@pytest.mark.parametrize('name', NAMES)
def test_foundation_models_are_discovered(name):
    model(name)


@pytest.fixture
def rows(db):
    owner = apps.get_model('core', 'Organisation').objects.create(name='Synthetic document owner')
    branch = apps.get_model('core', 'Branch').objects.create(organisation=owner, name='Synthetic', code='DOC')
    patient = apps.get_model('core', 'Patient').objects.create(branch=branch, full_name='Synthetic patient')
    actor = get_user_model().objects.create(username='document-synthetic')
    return patient, actor, timezone.now()


def intent(rows, **changes):
    patient, actor, now = rows
    values = dict(patient=patient, created_by=actor, category='registration', declared_filename='card.png',
                  declared_media_type='image/png', declared_size_bytes=1, declared_sha256='a'*64,
                  created_at=now, expires_at=now+timedelta(minutes=30))
    values.update(changes)
    return model('PatientDocumentIntent').objects.create(**values)


def receipt(rows, **changes):
    values = dict(actor=rows[1], operation='intent.create', key=uuid.uuid4(), fingerprint='b'*64, result=intent(rows))
    values.update(changes)
    return model('DocumentIntentReceipt').objects.create(**values)


def event(rows, **changes):
    values = dict(actor=rows[1], patient=rows[0], operation='intent.list', result_count=0, projection_sha256='c'*64)
    values.update(changes)
    return model('DocumentAccessEvent').objects.create(**values)


def rejects(fn):
    # PostgreSQL VARCHAR rejects overlength values before the explicit CHECK;
    # SQLite instead reaches the length CHECK. Both are strict DB rejection.
    with pytest.raises((IntegrityError, DataError)), transaction.atomic():
        fn()


@pytest.mark.django_db
@pytest.mark.parametrize('changes', [
    {'category': 'clinical_reference'}, {'category': ''}, {'declared_media_type': 'application/pdf'},
    {'declared_media_type': ''}, {'declared_size_bytes': 0}, {'declared_size_bytes': 10485761},
    {'version': 0}, {'version': 2147483648}, {'declared_sha256': 'a'*63},
    {'declared_sha256': 'a'*65}, {'declared_sha256': 'A'*64}, {'declared_sha256': 'g'*64},
    {'declared_sha256': 'a'*63+'\n'}, {'declared_sha256': 'a'*64+'\n'},
    {'declared_filename': ''}, {'declared_filename': 'a'*121}, {'status': 'ready'},
    {'status': ''}, {'status': 'withdrawn'}, {'withdrawal_reason': 'Unexpected'},
    {'withdrawn_at': timezone.now()}, {'withdrawn_by_id': uuid.uuid4()},
    {'patient': None}, {'created_by': None}, {'expires_at': None},
])
def test_intent_database_rejects_invalid_metadata(rows, changes):
    # Use the valid existing actor for the pending-with-actor case, avoiding dangling FKs.
    if 'withdrawn_by_id' in changes:
        changes = {'withdrawn_by': rows[1]}
    rejects(lambda: intent(rows, **changes))


@pytest.mark.django_db
@pytest.mark.parametrize('seconds', [0, 1799, 1801])
def test_intent_expiry_is_exact(rows, seconds):
    rejects(lambda: intent(rows, expires_at=rows[2]+timedelta(seconds=seconds)))


@pytest.mark.django_db
@pytest.mark.parametrize('changes', [
    {'withdrawn_at': None}, {'withdrawn_by': None}, {'withdrawal_reason': ''},
    {'withdrawal_reason': 'a'*9}, {'withdrawal_reason': 'a'*501}, {'withdrawn_at': 'before'},
])
def test_withdrawn_database_requires_complete_metadata(rows, changes):
    values = dict(status='withdrawn', withdrawn_at=rows[2], withdrawn_by=rows[1], withdrawal_reason='Synthetic reason')
    values.update(changes)
    if values['withdrawn_at'] == 'before':
        values['withdrawn_at'] = rows[2]-timedelta(microseconds=1)
    rejects(lambda: intent(rows, **values))


@pytest.mark.django_db
def test_valid_boundaries_and_protected_intent_relations(rows):
    item = intent(rows, declared_filename='a'*120, declared_size_bytes=10485760, version=2147483647)
    intent(rows, status='withdrawn', withdrawn_at=rows[2], withdrawn_by=rows[1], withdrawal_reason='a'*10)
    intent(rows, declared_media_type='image/jpeg', status='withdrawn', withdrawn_at=rows[2], withdrawn_by=rows[1], withdrawal_reason='a'*500)
    assert item.status == 'pending'
    for obj in rows[:2]:
        with pytest.raises(ProtectedError):
            obj.delete()
    assert model('PatientDocumentIntent')._meta.ordering == ['-created_at', '-id']
    assert [i.fields for i in model('PatientDocumentIntent')._meta.indexes] == [['patient', '-created_at', '-id'], ['status', 'expires_at', 'id']]


@pytest.mark.django_db
def test_withdrawal_actor_is_independently_protected(rows):
    actor = get_user_model().objects.create(username='document-withdrawer')
    intent(rows, status='withdrawn', withdrawn_at=rows[2], withdrawn_by=actor, withdrawal_reason='Synthetic reason')
    with pytest.raises(ProtectedError):
        actor.delete()


@pytest.mark.django_db
def test_receipt_collision_scope_and_protection(rows):
    item = receipt(rows)
    rejects(lambda: receipt(rows, key=item.key, fingerprint='d'*64))
    receipt(rows, key=item.key, operation='intent.withdraw')
    other = get_user_model().objects.create(username='document-other')
    receipt(rows, key=item.key, actor=other)
    receipt(rows)
    for obj in [item.result, rows[1]]:
        with pytest.raises(ProtectedError):
            obj.delete()


@pytest.mark.django_db
@pytest.mark.parametrize('changes', [{'operation': ''}, {'operation': 'upload'}, {'fingerprint': ''},
    {'fingerprint': 'A'*64}, {'fingerprint': 'g'*64}, {'fingerprint': 'a'*63},
    {'fingerprint': 'a'*63+'\n'}, {'fingerprint': 'a'*64+'\n'}, {'fingerprint': 'a'*65},
    {'result': None}, {'actor': None}, {'key': None}])
def test_receipt_database_rejects_invalid_metadata(rows, changes):
    rejects(lambda: receipt(rows, **changes))


@pytest.mark.django_db
@pytest.mark.parametrize('changes', [{'operation': ''}, {'operation': 'download'}, {'result_count': -1},
    {'result_count': 101}, {'operation': 'intent.detail'}, {'projection_sha256': ''},
    {'projection_sha256': 'A'*64}, {'projection_sha256': 'g'*64}, {'projection_sha256': 'a'*63},
    {'projection_sha256': 'a'*63+'\n'}, {'projection_sha256': 'a'*64+'\n'}, {'projection_sha256': 'a'*65},
    {'actor': None}, {'patient': None}, {'correlation_id': None}, {'result_count': None}])
def test_event_database_rejects_invalid_metadata(rows, changes):
    rejects(lambda: event(rows, **changes))


@pytest.mark.django_db
def test_event_shape_protection_and_cross_patient_validation(rows):
    item = intent(rows)
    rejects(lambda: event(rows, document=item))
    for operation in ['intent.detail', 'intent.create_result', 'intent.withdraw_result']:
        rejects(lambda: event(rows, document=item, operation=operation, result_count=0))
        rejects(lambda: event(rows, document=item, operation=operation, result_count=2))
        event(rows, document=item, operation=operation, result_count=1)
    event(rows, result_count=100)
    other = apps.get_model('core', 'Patient').objects.create(branch=rows[0].branch, full_name='Synthetic other')
    candidate = model('DocumentAccessEvent')(actor=rows[1], patient=other, document=item, operation='intent.detail', result_count=1, projection_sha256='d'*64)
    with pytest.raises(ValidationError, match='patient'):
        candidate.clean()
    for obj in [item, rows[0], rows[1]]:
        with pytest.raises(ProtectedError):
            obj.delete()
    assert [i.fields for i in model('DocumentAccessEvent')._meta.indexes] == [['patient', '-created_at', '-id'], ['actor', '-created_at', '-id']]


@pytest.mark.django_db
def test_event_full_clean_reports_missing_document_as_validation_error(rows):
    candidate = model('DocumentAccessEvent')(actor=rows[1], patient=rows[0], document_id=uuid.uuid4(),
        operation='intent.detail', result_count=1, projection_sha256='d'*64)
    with pytest.raises(ValidationError) as error:
        candidate.full_clean()
    assert 'document' in error.value.message_dict


@pytest.mark.django_db
def test_event_cached_document_cannot_bypass_persisted_patient_validation(rows):
    document = intent(rows)
    other = apps.get_model('core', 'Patient').objects.create(branch=rows[0].branch, full_name='Synthetic other')
    document.patient_id = other.pk  # Deliberately unsaved relation on the cached object.
    candidate = model('DocumentAccessEvent')(actor=rows[1], patient=other, document=document,
        operation='intent.detail', result_count=1, projection_sha256='d'*64)
    assert model('PatientDocumentIntent').objects.get(pk=document.pk).patient_id == rows[0].pk
    with pytest.raises(ValidationError, match='patient'):
        candidate.full_clean()


@pytest.mark.django_db
def test_event_only_and_receipt_actor_relations_are_protected(rows):
    event(rows)
    for obj in rows[:2]:
        with pytest.raises(ProtectedError):
            obj.delete()
    actor = get_user_model().objects.create(username='receipt-only-actor')
    receipt(rows, actor=actor)
    with pytest.raises(ProtectedError):
        actor.delete()


def network_snapshot():
    return list(apps.get_model('core', 'NetworkPolicyState').objects.values())


def ensure_synthetic_network_row():
    # Transaction-test flush may remove the migration seed. This explicit fixture
    # makes preservation non-vacuous; it is never a runtime singleton repair.
    apps.get_model('core', 'NetworkPolicyState').objects.get_or_create(pk=1, defaults={
        'revision': 7, 'confirmed_policy': {'allowlist_only': False, 'allowlist': [], 'blocklist': []},
        'confirmed_policy_digest': hashlib.sha256(b'synthetic policy fixture').hexdigest(),
    })


@pytest.mark.django_db(transaction=True)
def test_foundation_migration_pristine_round_trip_preserves_existing_rows(rows):
    model(NAMES[0])
    old = [('core', '0007_network_policy')]
    leaf = MigrationExecutor(connection).loader.graph.leaf_nodes()
    ensure_synthetic_network_row()
    before = network_snapshot()
    appointment = apps.get_model('core', 'Appointment').objects.create(patient=rows[0], branch=rows[0].branch,
        doctor_name='Synthetic clinician', scheduled_at=rows[2])
    apps.get_model('core', 'Encounter').objects.create(appointment=appointment)
    appointment_before = list(apps.get_model('core', 'Appointment').objects.values())
    encounter_before = list(apps.get_model('core', 'Encounter').objects.values())
    try:
        MigrationExecutor(connection).migrate(old)
        assert all(model(n)._meta.db_table not in connection.introspection.table_names() for n in NAMES)
        MigrationExecutor(connection).migrate(leaf)
        assert all(model(n)._meta.db_table in connection.introspection.table_names() for n in NAMES)
        assert network_snapshot() == before
        assert apps.get_model('core', 'Patient').objects.get(pk=rows[0].pk).full_name == 'Synthetic patient'
        assert list(apps.get_model('core', 'Appointment').objects.values()) == appointment_before
        assert list(apps.get_model('core', 'Encounter').objects.values()) == encounter_before
    finally:
        MigrationExecutor(connection).migrate(leaf)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('kind', NAMES)
def test_foundation_reverse_refuses_rows_before_any_drop(rows, kind):
    leaf = MigrationExecutor(connection).loader.graph.leaf_nodes()
    obj = {NAMES[0]: intent, NAMES[1]: receipt, NAMES[2]: event}[kind](rows)
    ensure_synthetic_network_row()
    before = network_snapshot()
    try:
        with pytest.raises(RuntimeError, match='empty'):
            MigrationExecutor(connection).migrate([('core', '0007_network_policy')])
        assert all(model(n)._meta.db_table in connection.introspection.table_names() for n in NAMES)
        assert model(kind).objects.filter(pk=obj.pk).exists()
        assert network_snapshot() == before
    finally:
        MigrationExecutor(connection).migrate(leaf)


@pytest.mark.parametrize('nonempty', NAMES)
def test_reverse_guard_uses_historical_models_and_alias_for_every_branch(nonempty):
    # Isolate historical managers to cover dependent-only branches without impossible FK rows.
    model(NAMES[0])
    migration = import_module('apps.core.migrations.0008_patient_document_foundation')
    historical = Mock()
    historical.get_model.side_effect = lambda app, name: SimpleNamespace(objects=managers[name])
    managers = {name: Mock() for name in NAMES}
    for name, manager in managers.items():
        manager.using.return_value.exists.return_value = name == nonempty
    with pytest.raises(RuntimeError, match='empty'):
        migration.reverse_empty_only(historical, SimpleNamespace(connection=SimpleNamespace(alias='schema_test')))
    for name in NAMES[:NAMES.index(nonempty)+1]:
        managers[name].using.assert_called_once_with('schema_test')
    assert migration.Migration.operations[-1].reverse_code is migration.reverse_empty_only
