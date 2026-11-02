"""Business-service acceptance uses real sessions and isolated synthetic patients.

No success mock or SQLite fallback: portable tests cover only rejection boundaries.
"""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from hashlib import sha256
from importlib import import_module
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.core import document_authority as authority
from apps.core.document_models import (DocumentAccessEvent, DocumentIntentReceipt,
    DocumentMetadataRateWindow, PatientDocumentIntent)
from apps.core.models import Branch, Membership, Organisation, Patient


pytestmark = pytest.mark.django_db(transaction=True)
pg = pytest.mark.skipif(connection.vendor != 'postgresql', reason='Actual PostgreSQL business success only')
CREATE = json.dumps(dict(category='registration', filename='synthetic-registration.png',
    media_type='image/png', size_bytes=128, sha256='a'*64)).encode()
WITHDRAW = b'{"expected_version":1,"reason":"Synthetic correction only"}'


def service():
    # Deliberately inside tests: absent production module is RED, not collection error.
    return import_module('apps.core.document_services')


@contextmanager
def fails(code, retry=None):
    with pytest.raises(authority.DocumentServiceError) as caught:
        yield
    assert caught.value.code == code
    assert caught.value.retry_after == retry


def forbidden(*args, **kwargs):
    pytest.fail('Boundary must reject before database access')


def request_for(user):
    request = RequestFactory().get('/', REMOTE_ADDR='198.51.100.26')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    persisted = Session.objects.get(session_key=request.session.session_key).get_decoded()
    assert persisted['_auth_user_id'] == str(user.pk)
    assert persisted['_auth_user_hash'] == user.get_session_auth_hash()
    return request


@pytest.fixture
def business(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    org = Organisation.objects.create(name='Synthetic business')
    branch = Branch.objects.create(organisation=org, name='Synthetic desk', code='BUS')
    user = get_user_model().objects.create_user(username='synthetic-business', password='Synthetic-82!')
    membership = Membership.objects.create(user=user, branch=branch, role='reception')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic service patient')
    return SimpleNamespace(user=user, branch=branch, org=org, membership=membership,
                           patient=patient, request=request_for(user))


def context(business, operation):
    return authority.capture_document_context(business.request, operation)


def invoke(business, operation, *, patient=None, document=None, key=None, body=None, query_pairs=()):
    api = service()
    ctx = context(business, operation)
    patient = str((patient or business.patient).pk)
    if operation == 'intent.list':
        return api.list_document_intents(ctx, patient, query_pairs)
    if operation == 'intent.detail':
        return api.get_document_intent(ctx, patient, str(document.pk))
    if operation == 'intent.create':
        return api.create_document_intent(ctx, patient, str(key or uuid4()), body if body is not None else CREATE)
    return api.withdraw_document_intent(ctx, patient, str(document.pk), str(key or uuid4()), body if body is not None else WITHDRAW)


def decoded(result, status):
    assert type(result.status) is int and result.status == status
    assert type(result.body) is bytes and len(result.body) <= 262144
    value = json.loads(result.body.decode('utf-8'))
    assert result.body == json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
    assert 'synthetic-registration.png' not in repr(result)
    with pytest.raises(FrozenInstanceError):
        result.status = 500
    return value


def seed_intent(business, *, patient=None, creator=None, created_at=None, **changes):
    created_at = created_at or timezone.now()
    values = dict(patient=patient or business.patient, created_by=creator or business.user,
        category='registration', declared_filename='synthetic-registration.png', declared_media_type='image/png',
        declared_size_bytes=128, declared_sha256='a'*64, created_at=created_at,
        expires_at=created_at+timedelta(minutes=30))
    values.update(changes)
    return PatientDocumentIntent.objects.create(**values)


def audit(business, operation, ids):
    event = DocumentAccessEvent.objects.latest('created_at')
    assert event.actor_id == business.user.pk and event.patient_id == business.patient.pk
    assert event.operation == operation and event.result_count == len(ids)
    assert event.document_id == (None if operation == 'intent.list' else UUID(ids[0]))
    assert event.projection_sha256 == sha256(json.dumps(sorted(ids), separators=(',', ':')).encode()).hexdigest()
    assert isinstance(event.correlation_id, UUID)
    assert DocumentAccessEvent.objects.count() >= 1


@pytest.mark.parametrize('operation', ['intent.list', 'intent.detail', 'intent.create', 'intent.withdraw'])
def test_public_wrappers_reject_forged_context_without_io(business, operation):
    api = service()
    ctx = replace(context(business, operation))
    args = [ctx, str(business.patient.pk)]
    if operation in ('intent.detail', 'intent.withdraw'):
        args.append(str(uuid4()))
    if operation in ('intent.create', 'intent.withdraw'):
        args.extend([str(uuid4()), CREATE if operation == 'intent.create' else WITHDRAW])
    name = {'intent.list':'list_document_intents', 'intent.detail':'get_document_intent',
            'intent.create':'create_document_intent', 'intent.withdraw':'withdraw_document_intent'}[operation]
    with connection.execute_wrapper(forbidden), fails('document_metadata_unavailable'):
        getattr(api, name)(*args)


def test_wrong_operation_context_cannot_be_rebound(business):
    api = service()
    ctx = context(business, 'intent.create')
    with connection.execute_wrapper(forbidden), fails('document_metadata_unavailable'):
        api.list_document_intents(ctx, str(business.patient.pk))


@pytest.mark.parametrize('mode', ['atomic', 'manual'])
def test_public_service_rejects_ambient_transaction_before_queries(business, mode):
    api = service()
    ctx = context(business, 'intent.list')
    if mode == 'atomic':
        with transaction.atomic(), connection.execute_wrapper(forbidden), fails('document_metadata_unavailable'):
            api.list_document_intents(ctx, str(business.patient.pk))
    else:
        transaction.set_autocommit(False)
        try:
            with connection.execute_wrapper(forbidden), fails('document_metadata_unavailable'):
                api.list_document_intents(ctx, str(business.patient.pk))
        finally:
            transaction.set_autocommit(True)


@pytest.mark.parametrize('mode', ['router', 'extra_alias'])
def test_public_service_requires_default_database_without_router(business, settings, monkeypatch, mode):
    api = service()
    ctx = context(business, 'intent.list')
    if mode == 'router':
        monkeypatch.setattr(settings, 'DATABASE_ROUTERS', [object()])
    else:
        monkeypatch.setattr(settings, 'DATABASES', {**settings.DATABASES, 'unsupported': {'ENGINE':'django.db.backends.sqlite3', 'NAME':':memory:'}})
    with connection.execute_wrapper(forbidden), fails('document_metadata_unavailable'):
        api.list_document_intents(ctx, str(business.patient.pk))


@pg
def test_empty_list_is_detached_and_audited(business):
    result = invoke(business, 'intent.list')
    with connection.execute_wrapper(forbidden):
        body = decoded(result, 200)
    assert set(body) == {'server_time', 'results', 'has_more', 'next_cursor', 'capabilities'}
    assert body['results'] == [] and body['has_more'] is False and body['next_cursor'] is None
    audit(business, 'intent.list', [])
    assert DocumentAccessEvent.objects.count() == 1
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 1


@pg
def test_create_replay_detail_and_withdraw_each_take_fresh_admission_and_required_event(business, monkeypatch):
    api = service()
    access = import_module('apps.core.document_access')
    original = access.admit_document_command
    calls = []
    def observed(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(api, 'admit_document_command', observed)
    key = uuid4()
    first = decoded(invoke(business, 'intent.create', key=key), 201)
    record = PatientDocumentIntent.objects.get(pk=first['document']['id'])
    audit(business, 'intent.create_result', [str(record.pk)])
    assert record.expires_at-record.created_at == timedelta(minutes=30)
    assert record.status == 'pending' and record.version == 1
    assert set(first) == {'server_time', 'document', 'capabilities'}
    replay = decoded(invoke(business, 'intent.create', key=key), 201)
    assert replay['document']['id'] == str(record.pk)
    audit(business, 'intent.create_result', [str(record.pk)])
    assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == 1
    decoded(invoke(business, 'intent.detail', document=record), 200)
    audit(business, 'intent.detail', [str(record.pk)])
    withdraw_key = uuid4()
    withdrawn = decoded(invoke(business, 'intent.withdraw', document=record, key=withdraw_key), 200)
    assert withdrawn['document']['status'] == 'withdrawn' and withdrawn['document']['version'] == 2
    audit(business, 'intent.withdraw_result', [str(record.pk)])
    record.refresh_from_db()
    persisted = (record.version, record.withdrawn_at, record.withdrawal_reason)
    later = decoded(invoke(business, 'intent.withdraw', document=record, key=withdraw_key), 200)
    assert later['document']['status'] == 'withdrawn'
    record.refresh_from_db()
    assert (record.version, record.withdrawn_at, record.withdrawal_reason) == persisted
    assert len(calls) == DocumentAccessEvent.objects.count() == 5
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 5
    assert DocumentIntentReceipt.objects.count() == 2
    audit(business, 'intent.withdraw_result', [str(record.pk)])


@pg
@pytest.mark.parametrize('mode,code', [('missing','not_found'), ('foreign','not_found'), ('wrong_document','not_found'),
    ('global_permission','permission_denied'), ('noncreator','permission_denied')])
def test_scope_and_creator_errors_retain_admission_without_disclosure(business, mode, code):
    api = service()
    target = business.patient
    document = seed_intent(business)
    if mode == 'missing':
        target = SimpleNamespace(pk=uuid4())
    if mode == 'foreign':
        foreign = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic foreign'), name='Other', code='OTH')
        target = Patient.objects.create(branch=foreign, full_name='Synthetic foreign patient')
    if mode == 'wrong_document':
        other = Patient.objects.create(branch=business.branch, full_name='Synthetic second patient')
        document = seed_intent(business, patient=other)
    if mode == 'global_permission':
        business.membership.is_active = False
        business.membership.save(update_fields=['is_active'])
    if mode == 'noncreator':
        other = get_user_model().objects.create_user(username='synthetic-other')
        document = seed_intent(business, creator=other)
    operation = 'intent.withdraw' if mode == 'noncreator' else 'intent.detail'
    with fails(code):
        invoke(business, operation, patient=target, document=document)
    assert not DocumentAccessEvent.objects.exists() and not DocumentIntentReceipt.objects.exists()
    row = DocumentMetadataRateWindow.objects.filter(actor=business.user).first()
    assert (None if row is None else row.admitted_count) == (None if mode == 'global_permission' else 1)


@pg
def test_changed_patient_fingerprint_conflict_precedes_old_result_dereference(business):
    key = uuid4()
    decoded(invoke(business, 'intent.create', key=key), 201)
    other = Patient.objects.create(branch=business.branch, full_name='Synthetic changed target')
    with fails('idempotency_conflict'):
        invoke(business, 'intent.create', patient=other, key=key)
    assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == DocumentAccessEvent.objects.count() == 1
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 2


@pg
def test_matching_receipt_corrupt_linkage_is_unavailable_without_disclosure(business):
    key = uuid4()
    decoded(invoke(business, 'intent.create', key=key), 201)
    other = Patient.objects.create(branch=business.branch, full_name='Synthetic corrupt linkage')
    foreign_result = seed_intent(business, patient=other)
    DocumentIntentReceipt.objects.update(result=foreign_result)
    with fails('document_metadata_unavailable'):
        invoke(business, 'intent.create', key=key)
    assert DocumentAccessEvent.objects.count() == 1


@pg
@pytest.mark.parametrize('mode,expected', [('expired','intent_state_conflict'), ('withdrawn','intent_state_conflict'),
    ('stale','version_conflict'), ('maximum','version_conflict')])
def test_new_withdrawal_state_precedes_version_and_rolls_back(business, mode, expected):
    values = {}
    if mode == 'expired':
        values['created_at'] = timezone.now()-timedelta(hours=1)
        values['version'] = 2
    if mode == 'withdrawn':
        values.update(status='withdrawn', version=2, withdrawn_by=business.user,
                      withdrawn_at=timezone.now()+timedelta(seconds=1), withdrawal_reason='Synthetic prior correction')
    if mode == 'stale':
        values['version'] = 2
    if mode == 'maximum':
        values['version'] = 2147483647
    record = seed_intent(business, **values)
    with fails(expected):
        invoke(business, 'intent.withdraw', document=record)
    record.refresh_from_db()
    assert record.version == values.get('version', 1)
    assert not DocumentIntentReceipt.objects.exists() and not DocumentAccessEvent.objects.exists()
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 1


@pg
def test_create_replay_returns_current_state_even_when_quota_is_full(business):
    key = uuid4()
    created = decoded(invoke(business, 'intent.create', key=key), 201)
    record = PatientDocumentIntent.objects.get(pk=created['document']['id'])
    decoded(invoke(business, 'intent.withdraw', document=record), 200)
    for _ in range(20):
        seed_intent(business)
    replay = decoded(invoke(business, 'intent.create', key=key), 201)
    assert replay['document']['status'] == 'withdrawn' and replay['document']['version'] == 2
    assert PatientDocumentIntent.objects.count() == 21


@pg
def test_patient_quota_denial_keeps_allowance_but_no_receipt_or_event(business):
    for _ in range(20):
        seed_intent(business)
    with pytest.raises(authority.DocumentServiceError) as caught:
        invoke(business, 'intent.create')
    assert caught.value.code == 'rate_limited' and 1 <= caught.value.retry_after <= 1800
    assert PatientDocumentIntent.objects.count() == 20
    assert not DocumentIntentReceipt.objects.exists() and not DocumentAccessEvent.objects.exists()
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 1


@pg
def test_retained_expired_and_withdrawn_history_counts_organisation_rolling_quota(business):
    now = timezone.now()
    other = Patient.objects.create(branch=business.branch, full_name='Synthetic quota history')
    rows = []
    for index in range(1000):
        created = now-timedelta(minutes=40)
        rows.append(PatientDocumentIntent(patient=other, created_by=business.user, category='registration',
            declared_filename='synthetic.png', declared_media_type='image/png', declared_size_bytes=128,
            declared_sha256='a'*64, created_at=created, expires_at=created+timedelta(minutes=30),
            status='withdrawn' if index % 2 else 'pending', version=2 if index % 2 else 1,
            withdrawn_at=created+timedelta(minutes=1) if index % 2 else None,
            withdrawn_by=business.user if index % 2 else None,
            withdrawal_reason='Synthetic history correction' if index % 2 else ''))
    PatientDocumentIntent.objects.bulk_create(rows)
    with pytest.raises(authority.DocumentServiceError) as caught:
        invoke(business, 'intent.create')
    assert caught.value.code == 'rate_limited' and 1190 <= caught.value.retry_after <= 1201
    assert not DocumentIntentReceipt.objects.exists() and not DocumentAccessEvent.objects.exists()


@pg
def test_keyset_order_sentinel_digest_and_deleted_anchor_position(business):
    now = timezone.now()
    records = [seed_intent(business, created_at=now-timedelta(seconds=i)) for i in range(4)]
    first = decoded(invoke(business, 'intent.list', query_pairs=[('limit','2')]), 200)
    assert [item['id'] for item in first['results']] == [str(item.pk) for item in records[:2]]
    assert first['has_more'] is True and first['next_cursor']
    audit(business, 'intent.list', [str(item.pk) for item in records[:2]])
    records[1].delete()  # Cursor is a position, not a live anchor requirement.
    second = decoded(invoke(business, 'intent.list', query_pairs=[('limit','2'),('cursor',first['next_cursor'])]), 200)
    assert [item['id'] for item in second['results']] == [str(item.pk) for item in records[2:]]
    assert second['has_more'] is False and second['next_cursor'] is None
    audit(business, 'intent.list', [str(item.pk) for item in records[2:]])


@pg
def test_read_permission_does_not_imply_exact_branch_write_capability(business, monkeypatch):
    from apps.core.authorization import ROLE_PERMISSIONS
    monkeypatch.setitem(ROLE_PERMISSIONS, 'doctor', {'patients.read', 'documents.registration.read'})
    business.membership.role = 'doctor'
    business.membership.save(update_fields=['role'])
    other_branch = Branch.objects.create(organisation=business.org, name='Synthetic write desk', code='WRITE')
    Membership.objects.create(user=business.user, branch=other_branch, role='reception')
    record = seed_intent(business)
    body = decoded(invoke(business, 'intent.detail', document=record), 200)
    assert body['capabilities']['can_create_intent'] is False
    assert body['document']['can_withdraw'] is False
    assert body['document']['is_creator'] is True


@pg
def test_disabled_flag_after_admission_retains_allowance_and_has_no_patient_access(business, settings):
    settings.HMS_DOCUMENT_METADATA_ENABLED = False
    with CaptureQueriesContext(connection) as queries, fails('document_metadata_unavailable'):
        invoke(business, 'intent.list')
    assert not any('core_patient' in query['sql'].lower() or 'core_patientdocumentintent' in query['sql'].lower() for query in queries)
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 1
    assert not DocumentAccessEvent.objects.exists()


def test_sqlite_has_no_public_service_success(business):
    if connection.vendor != 'sqlite':
        pytest.skip('SQLite rejection boundary only')
    api = service()
    ctx = context(business, 'intent.list')
    with connection.execute_wrapper(forbidden), fails('document_metadata_unavailable'):
        api.list_document_intents(ctx, str(business.patient.pk))


@pg
def test_changed_body_same_key_is_conflict_without_new_disclosure(business):
    key = uuid4()
    decoded(invoke(business, 'intent.create', key=key), 201)
    changed = json.loads(CREATE)
    changed['filename'] = 'synthetic-changed.png'
    with fails('idempotency_conflict'):
        invoke(business, 'intent.create', key=key, body=json.dumps(changed).encode())
    assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == DocumentAccessEvent.objects.count() == 1
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 2


@pg
def test_replay_rechecks_current_target_scope_before_receipt(business):
    key = uuid4()
    decoded(invoke(business, 'intent.create', key=key), 201)
    foreign = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic moved'), name='Moved', code='MOV')
    Patient.objects.filter(pk=business.patient.pk).update(branch=foreign)
    with fails('not_found'):
        invoke(business, 'intent.create', key=key)
    assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == DocumentAccessEvent.objects.count() == 1
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 2


@pg
def test_read_expired_projection_does_not_mutate_persisted_status_or_version(business):
    record = seed_intent(business, created_at=timezone.now()-timedelta(hours=1))
    body = decoded(invoke(business, 'intent.detail', document=record), 200)
    assert body['document']['status'] == 'expired' and body['document']['can_withdraw'] is False
    record.refresh_from_db()
    assert (record.status, record.version) == ('pending', 1)
    audit(business, 'intent.detail', [str(record.pk)])


@pg
def test_keyset_equal_time_uses_uuid_descending_and_excludes_sentinel(business):
    now = timezone.now()
    records = [seed_intent(business, created_at=now) for _ in range(3)]
    expected = sorted((str(item.pk) for item in records), reverse=True)
    with CaptureQueriesContext(connection) as queries:
        body = decoded(invoke(business, 'intent.list', query_pairs=[('limit','2')]), 200)
    assert [item['id'] for item in body['results']] == expected[:2]
    assert body['has_more'] is True
    audit(business, 'intent.list', expected[:2])
    assert not any('count(' in query['sql'].lower() and 'core_patientdocumentintent' in query['sql'].lower() for query in queries)


@pg
def test_expired_history_and_other_organisation_are_not_active_patient_quota(business):
    for _ in range(20):
        seed_intent(business, created_at=timezone.now()-timedelta(hours=2))
    foreign = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic other quota'), name='Other', code='OQ')
    patient = Patient.objects.create(branch=foreign, full_name='Synthetic foreign quota')
    for _ in range(20):
        seed_intent(business, patient=patient)
    created = decoded(invoke(business, 'intent.create'), 201)
    assert created['document']['status'] == 'pending'
    assert DocumentIntentReceipt.objects.count() == DocumentAccessEvent.objects.count() == 1


@pg
def test_withdrawal_creator_denial_precedes_other_intent_receipt_conflict(business):
    """A visible noncreator record cannot become a receipt-fingerprint oracle."""
    owned = seed_intent(business)
    other_actor = get_user_model().objects.create_user(username='synthetic-review-creator')
    nonowned = seed_intent(business, creator=other_actor)
    key = uuid4()
    decoded(invoke(business, 'intent.withdraw', document=owned, key=key), 200)
    receipt = DocumentIntentReceipt.objects.get(actor=business.user, operation='intent.withdraw', key=key)
    assert receipt.result_id == owned.pk
    before_events = list(DocumentAccessEvent.objects.values())
    with fails('permission_denied'):
        invoke(business, 'intent.withdraw', document=nonowned, key=key)
    nonowned.refresh_from_db()
    assert (nonowned.status, nonowned.version) == ('pending', 1)
    assert list(DocumentAccessEvent.objects.values()) == before_events
    assert DocumentIntentReceipt.objects.count() == 1
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == 2


@pg
@pytest.mark.parametrize('mode', ['detail', 'withdraw', 'corrupt_receipt'])
def test_intent_lock_predicate_excludes_foreign_patient_before_execute(business, mode):
    """Inspect the actual locking SQL before executing it, never fake a success."""
    foreign_branch = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic lock isolation'),
                                          name='Foreign lock desk', code='LOCK')
    foreign_patient = Patient.objects.create(branch=foreign_branch, full_name='Synthetic foreign lock patient')
    foreign_intent = seed_intent(business, patient=foreign_patient)
    key = uuid4()
    if mode == 'corrupt_receipt':
        decoded(invoke(business, 'intent.create', key=key), 201)
        DocumentIntentReceipt.objects.filter(actor=business.user, operation='intent.create', key=key).update(result=foreign_intent)
    before_events = list(DocumentAccessEvent.objects.values())
    before_receipts = list(DocumentIntentReceipt.objects.values())
    observed = []

    def require_patient_predicate(execute, sql, params, many, execution_context):
        lowered = sql.lower()
        if ('core_patientdocumentintent' in lowered and lowered.lstrip().startswith('select')
                and ('for update' in lowered or 'for no key update' in lowered)):
            observed.append(sql)
            predicate = lowered.partition(' where ')[2]
            assert '"patient_id" =' in predicate, 'Intent lock must filter current patient in WHERE before locking'
            assert str(business.patient.pk) in {str(value) for value in params}, 'Intent lock must bind scoped patient'
        return execute(sql, params, many, execution_context)

    with connection.execute_wrapper(require_patient_predicate):
        with fails('document_metadata_unavailable' if mode == 'corrupt_receipt' else 'not_found'):
            if mode == 'corrupt_receipt':
                invoke(business, 'intent.create', key=key)
            else:
                invoke(business, 'intent.detail' if mode == 'detail' else 'intent.withdraw', document=foreign_intent, key=key)
    assert observed, 'Exercise an actual intent locking statement'
    assert list(DocumentAccessEvent.objects.values()) == before_events
    assert list(DocumentIntentReceipt.objects.values()) == before_receipts
    foreign_intent.refresh_from_db()
    assert (foreign_intent.status, foreign_intent.version) == ('pending', 1)
    assert DocumentMetadataRateWindow.objects.get(actor=business.user).admitted_count == (2 if mode == 'corrupt_receipt' else 1)
