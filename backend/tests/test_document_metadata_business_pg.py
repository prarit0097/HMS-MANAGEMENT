"""B2b real business races, not the completed B2a admission acceptance.

Removing the business authority gates, actor/key serialization, quota gate or
patient lock must break these tests. SQL wrappers only pause real statements;
all commands invoke the actual public service on independent connections.
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib import import_module
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.db import SessionStore
from django.db import close_old_connections, connection, transaction
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.core.document_authority import capture_document_context, DocumentServiceError
from apps.core.models import (
    Admission, Bed, Branch, DocumentAccessEvent, DocumentIntentReceipt,
    DocumentMetadataRateWindow, IdentitySecurity, Membership, Organisation,
    Patient, PatientDocumentIntent,
)

pytestmark = pytest.mark.django_db(transaction=True)
BODY = b'{"category":"registration","filename":"synthetic.png","media_type":"image/png","size_bytes":1,"sha256":"' + b'a' * 64 + b'"}'
WITHDRAW = b'{"expected_version":1,"reason":"Synthetic withdrawal"}'


def _request(user):
    request = RequestFactory().get('/', REMOTE_ADDR='127.0.0.1')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    return request


@pytest.fixture
def world(settings, monkeypatch):
    if connection.vendor != 'postgresql':
        pytest.skip('Requires PostgreSQL >=17 independent connections, actual business services and pg_blocking_pids; SQLite is no race evidence.')
    assert connection.pg_version >= 170000
    # Keep exact admitted-count assertions inside one UTC minute. Actual
    # monotonic budgets and PostgreSQL lock/server clocks remain real.
    fixed_wall = timezone.now().replace(second=10, microsecond=0)
    monkeypatch.setattr(timezone, 'now', lambda: fixed_wall)
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    settings.HMS_REQUIRE_ADMIN_MFA = False
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    org = Organisation.objects.create(name='Synthetic business race')
    branch = Branch.objects.create(organisation=org, name='Synthetic desk', code='BUS-RACE')
    sibling = Branch.objects.create(organisation=org, name='Sibling', code='SIBLING')
    user = get_user_model().objects.create_user(username='synthetic-document-business', password='Synthetic-business-only-287!')
    other = get_user_model().objects.create_user(username='synthetic-document-business-other')
    admin = get_user_model().objects.create_user(username='synthetic-document-business-admin')
    for person in (user, other):
        Membership.objects.create(user=person, branch=branch, role='reception')
    Membership.objects.create(user=admin, branch=branch, role='master_admin')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic race patient')
    patient2 = Patient.objects.create(branch=branch, full_name='Synthetic second patient')
    return SimpleNamespace(org=org, branch=branch, sibling=sibling, user=user,
        other=other, admin=admin, patient=patient, patient2=patient2,
        request=_request(user), other_request=_request(other))


def _call(world, operation, *, key=None, body=None, document=None, other=False, patient=None):
    api = import_module('apps.core.document_services')  # literal RED, never collection failure
    request = world.other_request if other else world.request
    context = capture_document_context(request, operation)
    patient_id = str((patient or world.patient).pk)
    try:
        if operation == 'intent.list':
            return api.list_document_intents(context, patient_id)
        if operation == 'intent.detail':
            return api.get_document_intent(context, patient_id, str(document.pk))
        if operation == 'intent.create':
            return api.create_document_intent(context, patient_id, key or str(uuid4()), body or BODY)
        return api.withdraw_document_intent(context, patient_id, str(document.pk), key or str(uuid4()), body or WITHDRAW)
    except DocumentServiceError as exc:
        return exc


def _success(result, status):
    assert not isinstance(result, Exception), repr(result)
    assert result.status == status
    assert type(result.body) is bytes
    return json.loads(result.body)


def _error(result, code, status):
    assert isinstance(result, DocumentServiceError), repr(result)
    assert (result.code, result.status) == (code, status)


def _seed(world, *, patient=None, created_at=None, status='pending'):
    now = created_at or timezone.now()
    values = dict(patient=patient or world.patient, created_by=world.user,
        category='registration', declared_filename='synthetic.png', declared_media_type='image/png',
        declared_size_bytes=1, declared_sha256='a' * 64, created_at=now,
        expires_at=now + timedelta(minutes=30), status=status)
    if status == 'withdrawn':
        values.update(withdrawn_at=now, withdrawn_by=world.user, withdrawal_reason='Synthetic old withdrawal', version=2)
    return PatientDocumentIntent.objects.create(**values)


def _pid():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_backend_pid()')
        return cursor.fetchone()[0]


def _wait_for_database_block(waiter, blocker):
    deadline = monotonic() + 1.5  # below the actual 2s business lock timeout
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [blocker, waiter])
            if cursor.fetchone()[0]:
                return
        sleep(.005)
    pytest.fail('Expected real PostgreSQL lock dependency was never observed')


def _gate(table, *, command='SELECT', occurrence=1):
    """Pause after a real locking SELECT or actual persistence mutation."""
    count = 0
    def matches(sql):
        nonlocal count
        upper = sql.strip().upper()
        if not upper.startswith(command) or f'"{table}"' not in sql:
            return False
        if command == 'SELECT' and 'FOR UPDATE' not in upper and 'FOR NO KEY UPDATE' not in upper:
            return False
        count += 1
        return count == occurrence
    return matches


def _ordered(first, second, gate):
    """First real transaction holds its gate; second actually waits on it."""
    held, release, started = Event(), Event(), Event()
    pids = {}
    def run(name, function, pause):
        close_old_connections()
        try:
            pids[name] = _pid()
            if name == 'second':
                started.set()
            def wrapper(execute, sql, params, many, context):
                result = execute(sql, params, many, context)
                if pause and gate(sql):
                    held.set()
                    assert release.wait(8), 'First transaction was not released'
                return result
            with connection.execute_wrapper(wrapper):
                return function()
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(run, 'first', first, True)
        second_future = None
        try:
            if not held.wait(3):
                if first_future.done():
                    first_future.result()  # preserve genuine missing-service RED
                pytest.fail('Actual first service never reached its gate')
            second_future = pool.submit(run, 'second', second, False)
            assert started.wait(2)
            assert len({pids['first'], pids['second'], _pid()}) == 3
            _wait_for_database_block(pids['second'], pids['first'])
        finally:
            release.set()
        # Database deadlocks/other exceptions propagate; no 40P01 is swallowed.
        return first_future.result(10), second_future.result(10)


def _allowance(user):
    return DocumentMetadataRateWindow.objects.filter(actor=user).values_list('admitted_count', flat=True).first() or 0


def _events(world, count):
    rows = list(DocumentAccessEvent.objects.filter(patient=world.patient))
    assert len(rows) == count
    for row in rows:
        if row.operation == 'intent.list':
            # These race fixtures contain one disclosed row and no page sentinel.
            ids = [str(value) for value in PatientDocumentIntent.objects.filter(patient_id=row.patient_id).values_list('id', flat=True)]
            assert row.result_count == len(ids)
        else:
            ids = [str(row.document_id)]
            assert row.result_count == 1
            assert row.document.patient_id == row.patient_id
        assert row.projection_sha256 == hashlib.sha256(json.dumps(sorted(ids), separators=(',', ':')).encode()).hexdigest()
        assert row.correlation_id is not None


@pytest.mark.parametrize('change', ['replace', 'suspend'])
@pytest.mark.parametrize('operation', ['intent.list', 'intent.detail', 'intent.create', 'replay'])
@pytest.mark.parametrize('writer_first', [True, False])
def test_actual_staff_writer_serializes_disclosure_write_and_replay(world, change, operation, writer_first):
    import_module('apps.core.document_services')
    from apps.core.staff_access import change_staff
    key = str(uuid4())
    if operation == 'replay':
        _success(_call(world, 'intent.create', key=key), 201)
        document = PatientDocumentIntent.objects.get()
    else:
        document = _seed(world)
    before_rate, before_events = _allowance(world.user), DocumentAccessEvent.objects.count()
    def writer():
        with transaction.atomic():
            values = {'expected_version': 0}
            if change == 'replace':
                values['assignments'] = [{'branch': world.branch.pk, 'role': 'doctor'}]
            else:
                values['status'] = 'suspended'
            return change_staff(world.admin, world.org.pk, world.user.pk, values)
    def service():
        return _call(world, 'intent.create' if operation == 'replay' else operation, key=key, document=document)
    if writer_first:
        _, result = _ordered(writer, service, _gate('core_organisation'))
        _error(result, 'permission_denied', 403)
        assert _allowance(world.user) == before_rate + 1  # phase A committed before waiting on organisation
        _events(world, before_events)
    else:
        result, _ = _ordered(service, writer, _gate('core_organisation'))
        _success(result, 201 if operation in ('intent.create', 'replay') else 200)
        assert _allowance(world.user) == before_rate + 1
        _events(world, before_events + 1)
    assert Membership.objects.filter(user=world.user, is_active=True, role='reception').count() == 0
    assert DocumentIntentReceipt.objects.count() == (1 if operation == 'replay' or (operation == 'intent.create' and not writer_first) else 0)


@pytest.mark.parametrize('change', ['epoch', 'first_profile', 'synthetic_deactivation'])
@pytest.mark.parametrize('operation', ['intent.list', 'intent.create', 'replay'])
@pytest.mark.parametrize('writer_first', [True, False])
def test_actual_identity_writers_gate_business_both_orders(world, change, operation, writer_first):
    import_module('apps.core.document_services')
    from apps.core.identity_security import lock_identity, bump
    if change != 'first_profile':
        IdentitySecurity.objects.create(user=world.user, auth_epoch=0)
    key = str(uuid4())
    if operation == 'replay':
        _success(_call(world, 'intent.create', key=key), 201)
    assert IdentitySecurity.objects.filter(user=world.user).count() == (0 if change == 'first_profile' else 1)
    before_rate, before_events = _allowance(world.user), DocumentAccessEvent.objects.count()
    def writer():
        with transaction.atomic():
            fresh, state = lock_identity(world.user)
            if change == 'synthetic_deactivation':
                # Synthetic locked persistence control: no delivered deactivation API exists.
                fresh.is_active = False
                fresh.save(update_fields=['is_active'])
            else:
                bump(state)
    def service():
        return _call(world, 'intent.create' if operation == 'replay' else operation, key=key)
    if writer_first:
        _, result = _ordered(writer, service, _gate('auth_user'))
        _error(result, 'not_authenticated', 401)
        assert _allowance(world.user) == before_rate  # rejected in admission, no charge
        _events(world, before_events)
    else:
        # First User lock belongs to admission; second is phase B.
        result, _ = _ordered(service, writer, _gate('auth_user', occurrence=2))
        _success(result, 200 if operation == 'intent.list' else 201)
        assert _allowance(world.user) == before_rate + 1
        _events(world, before_events + 1)
    if change != 'synthetic_deactivation':
        assert IdentitySecurity.objects.get(user=world.user).auth_epoch == 1
    assert DocumentIntentReceipt.objects.count() == (1 if operation == 'replay' or (operation == 'intent.create' and not writer_first) else 0)


@pytest.mark.parametrize('change', ['epoch', 'first_profile', 'synthetic_deactivation'])
@pytest.mark.parametrize('operation', ['intent.list', 'intent.create'])
def test_identity_writer_after_committed_admission_denies_phase_b_and_retains_charge(world, monkeypatch, change, operation):
    """Review coverage amendment: phase-A denial alone cannot prove this gate.

The wrapper invokes genuine admission and pauses only after its acknowledged
commit. The real identity writer then owns User before phase B attempts it.
"""
    api = import_module('apps.core.document_services')
    from apps.core.identity_security import lock_identity, bump
    if change != 'first_profile':
        IdentitySecurity.objects.create(user=world.user, auth_epoch=0)
    admitted, writer_held, release_writer = Event(), Event(), Event()
    pids = {}
    real_admit = api.admit_document_command

    def admit_then_wait_for_identity_writer(*args, **kwargs):
        proof = real_admit(*args, **kwargs)
        assert not connection.in_atomic_block and connection.get_autocommit()
        admitted.set()
        assert writer_held.wait(3), 'Identity writer did not acquire interphase gate'
        return proof

    monkeypatch.setattr(api, 'admit_document_command', admit_then_wait_for_identity_writer)

    def service():
        close_old_connections()
        try:
            pids['service'] = _pid()
            return _call(world, operation)
        finally:
            connection.close()

    def writer():
        close_old_connections()
        try:
            pids['writer'] = _pid()
            assert admitted.wait(3), 'Genuine admission did not commit'
            # Independent connection sees the durable phase-A charge already.
            assert _allowance(world.user) == 1
            assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == DocumentAccessEvent.objects.count() == 0
            with transaction.atomic():
                fresh, state = lock_identity(world.user)
                if change == 'synthetic_deactivation':
                    # Explicit synthetic persistence control, no deactivation API.
                    fresh.is_active = False
                    fresh.save(update_fields=['is_active'])
                else:
                    bump(state)
                writer_held.set()
                assert release_writer.wait(8), 'Interphase identity writer not released'
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        service_future = pool.submit(service)
        writer_future = pool.submit(writer)
        try:
            if not writer_held.wait(3):
                if service_future.done():
                    service_future.result()
                if writer_future.done():
                    writer_future.result()
                pytest.fail('Interphase identity writer never held its gate')
            assert len({pids['service'], pids['writer'], _pid()}) == 3
            _wait_for_database_block(pids['service'], pids['writer'])
        finally:
            release_writer.set()
        writer_future.result(10)
        result = service_future.result(10)
    _error(result, 'not_authenticated', 401)
    assert _allowance(world.user) == 1
    assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == DocumentAccessEvent.objects.count() == 0
    if change == 'synthetic_deactivation':
        assert not get_user_model().objects.get(pk=world.user.pk).is_active
    else:
        assert IdentitySecurity.objects.get(user=world.user).auth_epoch == 1


@pytest.mark.parametrize('changed', [False, True])
def test_same_key_create_competing_real_calls_have_one_result(world, changed):
    import_module('apps.core.document_services')
    key = str(uuid4())
    first, second = _ordered(lambda: _call(world, 'intent.create', key=key),
        lambda: _call(world, 'intent.create', key=key, body=BODY.replace(b'synthetic.png', b'changed.png') if changed else BODY),
        _gate('core_organisation'))
    original = _success(first, 201)
    if changed:
        _error(second, 'idempotency_conflict', 409)
    else:
        assert _success(second, 201)['document']['id'] == original['document']['id']
    assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == 1
    assert _allowance(world.user) == 2
    _events(world, 1 if changed else 2)


@pytest.mark.parametrize('same_key', [True, False])
def test_concurrent_withdraw_same_or_different_key_changes_version_once(world, same_key):
    import_module('apps.core.document_services')
    document = _seed(world)
    key = str(uuid4())
    first, second = _ordered(lambda: _call(world, 'intent.withdraw', key=key, document=document),
        lambda: _call(world, 'intent.withdraw', key=key if same_key else str(uuid4()), document=document),
        _gate('core_organisation'))
    _success(first, 200)
    if same_key:
        _success(second, 200)
    else:
        _error(second, 'intent_state_conflict', 409)
    document.refresh_from_db()
    assert (document.status, document.version, document.withdrawn_by_id) == ('withdrawn', 2, world.user.pk)
    assert document.withdrawal_reason == 'Synthetic withdrawal'
    assert DocumentIntentReceipt.objects.count() == 1
    assert _allowance(world.user) == 2
    _events(world, 2 if same_key else 1)


@pytest.mark.parametrize('read_operation', ['intent.list', 'intent.detail', 'replay'])
@pytest.mark.parametrize('withdraw_first', [True, False])
def test_real_read_or_create_replay_and_withdraw_serialize_current_state(world, read_operation, withdraw_first):
    import_module('apps.core.document_services')
    key = str(uuid4())
    _success(_call(world, 'intent.create', key=key), 201)
    document = PatientDocumentIntent.objects.get()
    def reader():
        return _call(world, 'intent.create' if read_operation == 'replay' else read_operation, key=key, document=document)
    def withdrawer():
        return _call(world, 'intent.withdraw', document=document)
    first, second = _ordered(withdrawer if withdraw_first else reader, reader if withdraw_first else withdrawer,
        _gate('core_organisation'))
    read_result = second if withdraw_first else first
    payload = _success(read_result, 201 if read_operation == 'replay' else 200)
    projected = payload['results'][0] if read_operation == 'intent.list' else payload['document']
    assert (projected['status'], projected['version']) == (('withdrawn', 2) if withdraw_first else ('pending', 1))
    _success(first if withdraw_first else second, 200)
    document.refresh_from_db()
    assert (document.status, document.version) == ('withdrawn', 2)
    assert DocumentIntentReceipt.objects.count() == 2
    assert _allowance(world.user) == 3
    _events(world, 3)


@pytest.mark.parametrize('quota', ['patient', 'organisation'])
def test_different_actors_compete_for_one_final_quota_slot(world, quota):
    import_module('apps.core.document_services')
    now = timezone.now()
    if quota == 'patient':
        for _ in range(19):
            _seed(world, created_at=now)
        second_patient = world.patient
    else:
        # Retained withdrawn creations still consume organisation rolling quota.
        for _ in range(999):
            _seed(world, patient=world.patient2, created_at=now - timedelta(minutes=40), status='withdrawn')
        second_patient = world.patient2
    first, second = _ordered(lambda: _call(world, 'intent.create'),
        lambda: _call(world, 'intent.create', other=True, patient=second_patient), _gate('core_organisation'))
    _success(first, 201)
    _error(second, 'rate_limited', 429)
    assert type(second.retry_after) is int and 1 <= second.retry_after <= 3600
    assert PatientDocumentIntent.objects.count() == (20 if quota == 'patient' else 1000)
    assert DocumentIntentReceipt.objects.count() == DocumentAccessEvent.objects.count() == 1
    assert _allowance(world.user) == _allowance(world.other) == 1


@pytest.mark.parametrize('writer', ['patient_patch', 'bed_allocation'])
@pytest.mark.parametrize('writer_first', [True, False])
def test_actual_patient_patch_and_bed_allocation_do_not_invert_business_locks(world, writer, writer_first):
    import_module('apps.core.document_services')
    from apps.core.api import PatientDetail
    from apps.core.services import allocate_bed
    bed = Bed.objects.create(branch=world.branch, number='SYN-1', room_number='SYN-ROOM')
    def existing_writer():
        if writer == 'patient_patch':
            request = APIRequestFactory().patch('/', {'full_name': 'Synthetic corrected patient'}, format='json')
            force_authenticate(request, user=world.other)
            response = PatientDetail.as_view()(request, pk=world.patient.pk)
            assert response.status_code == 200
            return response.status_code
        return allocate_bed(world.other, {'bed': bed, 'patient': world.patient, 'treating_doctor': 'Synthetic clinician'}).pk
    def service():
        return _call(world, 'intent.create')
    if writer_first:
        # PATCH locks through its real UPDATE, allocation through real SELECT FOR UPDATE.
        gate = _gate('core_patient', command='UPDATE' if writer == 'patient_patch' else 'SELECT')
        _, result = _ordered(existing_writer, service, gate)
    else:
        result, _ = _ordered(service, existing_writer, _gate('core_patient'))
    _success(result, 201)
    assert PatientDocumentIntent.objects.count() == DocumentIntentReceipt.objects.count() == 1
    assert _allowance(world.user) == 1
    _events(world, 1)
    world.patient.refresh_from_db()
    bed.refresh_from_db()
    if writer == 'patient_patch':
        assert world.patient.full_name == 'Synthetic corrected patient'
        assert Admission.objects.count() == 0
    else:
        assert (bed.status, Admission.objects.filter(patient=world.patient, bed=bed, status='active').count()) == ('occupied', 1)
