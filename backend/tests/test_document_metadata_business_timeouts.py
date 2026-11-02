"""PG-only phase-B acceptance. Synthetic fault injection is labelled explicitly.

Real server timeouts use real SQL; lost acknowledgements are simulated AFTER
real commit/rollback. Nothing here claims a production outage or HTTP deadline.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from importlib import import_module
from threading import Event
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import OperationalError, close_old_connections, connection, transaction
from django.test import RequestFactory
from django.utils import timezone

from apps.core.document_authority import capture_document_context, DocumentServiceError
from apps.core.models import (Branch, DocumentAccessEvent, DocumentIntentReceipt,
    DocumentMetadataRateWindow, Membership, Organisation, Patient, PatientDocumentIntent)
from apps.core.network_models import NetworkPolicyChange, NetworkPolicyPreview, NetworkPolicyState
from apps.security.network_policy import policy_digest

pytestmark = pytest.mark.django_db(transaction=True)
BODY = b'{"category":"registration","filename":"synthetic.png","media_type":"image/png","size_bytes":1,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
CONTROLS = ('lock_timeout', 'statement_timeout', 'transaction_timeout')


@pytest.fixture(autouse=True)
def actual_pg_only():
    if connection.vendor != 'postgresql' or connection.pg_version < 170000:
        pytest.skip('Actual PostgreSQL>=17 phase-B controls/commit acceptance required; no SQLite substitute.')


@pytest.fixture
def actor(settings, monkeypatch):
    # Keep explicit same-key reconciliation inside one fixed UTC minute; the
    # real monotonic clock and actual PostgreSQL timeouts remain untouched.
    fixed_wall = timezone.now().replace(second=10, microsecond=0)
    monkeypatch.setattr(timezone, 'now', lambda: fixed_wall)
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.DATABASE_ROUTERS = []
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    user = get_user_model().objects.create_user(username='synthetic-business-fault', password='Synthetic-business-28!')
    branch = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic business faults'), name='Desk', code='BFAULT')
    Membership.objects.create(user=user, branch=branch, role='reception')
    patient = Patient.objects.create(branch=branch, full_name='Synthetic fault patient')
    request = RequestFactory().get('/synthetic-business-fault', REMOTE_ADDR='127.0.0.1')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    allow = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
    NetworkPolicyState.objects.update_or_create(pk=1, defaults={
        'confirmed_policy': allow, 'confirmed_policy_digest': policy_digest(allow), 'pending_change': None})
    return SimpleNamespace(user=user, branch=branch, patient=patient, request=request, key=str(uuid4()))


def _create(api, actor):
    return api.create_document_intent(capture_document_context(actor.request, 'intent.create'),
                                      str(actor.patient.pk), actor.key, BODY)


@contextmanager
def _denied(code='document_metadata_unavailable', status=503):
    with pytest.raises(DocumentServiceError) as error:
        yield
    assert (error.value.code, error.value.status) == (code, status)
    if status == 503:
        assert (error.value.message, error.value.retry_after) == (
            'Document details are unavailable. Try again later.', None)


def _observed(actor):
    def read():
        close_old_connections()
        try:
            return (DocumentMetadataRateWindow.objects.get(actor_id=actor.user.pk).admitted_count,
                    PatientDocumentIntent.objects.count(), DocumentIntentReceipt.objects.count(), DocumentAccessEvent.objects.count())
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(read).result(10)


def _controls():
    with connection.cursor() as cursor:
        values = []
        for name in CONTROLS:
            cursor.execute('SHOW ' + name)
            values.append(cursor.fetchone()[0])
        return tuple(values)


def _pid():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_backend_pid()')
        return cursor.fetchone()[0]


def _business_lock(sql):
    return 'CORE_ORGANISATION' in sql.upper() and 'FOR NO KEY UPDATE' in sql.upper()


def _state(exc):
    return getattr(exc, 'sqlstate', None) or getattr(exc.__cause__, 'sqlstate', None)


def test_phase_b_actual_local_controls_before_business_locks_reset_after_commit(actor):
    api = import_module('apps.core.document_services')
    before, observed, actor_locks = _controls(), [], []
    def inspect(execute, sql, params, many, context):
        # The first actor lock belongs to separately committed admission. The
        # second is phase B's FIRST lock, before Identity/Organisation; observing
        # only Organisation would miss controls installed too late.
        upper = sql.upper()
        if 'AUTH_USER' in upper and 'FOR NO KEY UPDATE' in upper:
            actor_locks.append(True)
            if len(actor_locks) == 2:
                observed.append(_controls())
                assert observed[-1] == ('2s', '3s', '5s')
        if _business_lock(sql):
            observed.append(_controls())
        return execute(sql, params, many, context)
    with connection.execute_wrapper(inspect):
        result = _create(api, actor)
    assert result.status == 201 and type(result.body) is bytes
    assert len(actor_locks) == 2
    assert len(observed) >= 2 and all(value == ('2s', '3s', '5s') for value in observed)
    assert _controls() == before
    assert _observed(actor) == (1, 1, 1, 1)


@pytest.mark.parametrize('model', [PatientDocumentIntent, DocumentIntentReceipt, DocumentAccessEvent])
def test_actual_business_write_failure_rolls_back_all_phase_b_rows_retaining_allowance(actor, model):
    api = import_module('apps.core.document_services')
    fired = []
    def fail(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.lstrip().upper().startswith('INSERT') and model._meta.db_table.upper() in sql.upper():
            fired.append(True)
            raise OperationalError('Synthetic injected business write failure')
        return result
    with connection.execute_wrapper(fail), _denied():
        _create(api, actor)
    assert fired == [True]
    assert _observed(actor) == (1, 0, 0, 0)


@contextmanager
def _event_trigger(body):
    """Temporary test-only deferred event trigger, removed even on failure."""
    name = connection.ops.quote_name('synthetic_business_' + uuid4().hex)
    table = connection.ops.quote_name(DocumentAccessEvent._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN {body} RETURN NEW; END $$')
        cursor.execute(f'CREATE CONSTRAINT TRIGGER {name} AFTER INSERT ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION {name}()')
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP TRIGGER IF EXISTS {name} ON {table}')
            cursor.execute(f'DROP FUNCTION IF EXISTS {name}()')


def test_deferred_event_failure_is_forced_before_final_selection_retaining_allowance(actor):
    api = import_module('apps.core.document_services')
    seen, states = [], []
    def record(execute, sql, params, many, context):
        seen.append(sql.upper())
        try:
            return execute(sql, params, many, context)
        except Exception as exc:
            states.append(_state(exc))
            raise
    with _event_trigger("RAISE EXCEPTION 'synthetic deferred business guard' USING ERRCODE='23514';"), connection.execute_wrapper(record), _denied():
        _create(api, actor)
    assert '23514' in states
    forced = [i for i, sql in enumerate(seen) if 'SET CONSTRAINTS ALL IMMEDIATE' in sql]
    assert len(forced) == 2  # separately committed admission, then business
    assert not any('DJANGO_SESSION' in sql or 'CORE_NETWORK' in sql for sql in seen[forced[-1] + 1:])
    assert _observed(actor) == (1, 0, 0, 0)


@pytest.mark.parametrize('mode', ['statement_3s', 'transaction_5s'])
def test_real_phase_b_server_timeout_and_control_reset_retains_admission(actor, mode):
    api = import_module('apps.core.document_services')
    before, old_pid, fired, states, completed = _controls(), _pid(), [], [], []
    def sleep(execute, sql, params, many, context):
        if _business_lock(sql) and not fired:
            fired.append(True)
            try:
                with connection.cursor() as cursor:
                    if mode == 'statement_3s':
                        cursor.execute('SELECT pg_sleep(3.4)')
                    else:
                        for _ in range(4):
                            cursor.execute('SELECT pg_sleep(1.4)')
                            completed.append(True)
            except Exception as exc:
                states.append(_state(exc))
                raise
        return execute(sql, params, many, context)
    with connection.execute_wrapper(sleep), _denied():
        _create(api, actor)
    assert fired == [True] and states
    if mode == 'statement_3s':
        assert states == ['57014']
    else:
        assert len(completed) >= 3 and '57014' not in states
        assert all(state in (None, '25P04') for state in states)
        assert _pid() != old_pid
    assert _observed(actor) == (1, 0, 0, 0)
    assert _controls() == before


def test_real_phase_b_organisation_lock_2s_timeout_observes_pg_blocker(actor):
    api = import_module('apps.core.document_services')
    waiter, ready, release, blocked, states = _pid(), Event(), Event(), Event(), []
    def holder():
        close_old_connections()
        try:
            with transaction.atomic():
                Organisation.objects.select_for_update(no_key=True).get(pk=actor.branch.organisation_id)
                pid = _pid()
                ready.set()
                deadline = monotonic() + 8
                while not release.is_set() and monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [pid, waiter])
                        if cursor.fetchone()[0]:
                            blocked.set()
                    release.wait(.01)
        finally:
            connection.close()
    def record(execute, sql, params, many, context):
        try:
            return execute(sql, params, many, context)
        except Exception as exc:
            states.append(_state(exc))
            raise
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(holder)
        try:
            assert ready.wait(4)
            with connection.execute_wrapper(record), _denied():
                _create(api, actor)
            assert blocked.is_set() and '55P03' in states
        finally:
            release.set()
            future.result(10)
    assert _observed(actor) == (1, 0, 0, 0)


@pytest.mark.parametrize('mode', ['rollback_only', 'closed_in_transaction'])
def test_phase_b_normal_exit_cannot_release_bytes_after_rollback_or_close(actor, mode):
    api = import_module('apps.core.document_services')
    event, fired = [], []
    def mark(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        upper = sql.upper()
        if upper.lstrip().startswith('INSERT') and 'CORE_DOCUMENTACCESSEVENT' in upper:
            event.append(True)
        if event and not fired and 'CORE_NETWORKPOLICYSTATE' in upper:
            fired.append(True)
            if mode == 'rollback_only':
                transaction.set_rollback(True)
            else:
                connection.close()
        return result
    with connection.execute_wrapper(mark), _denied():
        _create(api, actor)
    assert event == [True] and fired == [True]
    assert _observed(actor) == (1, 0, 0, 0)


@pytest.mark.parametrize('outcome', ['commit', 'rollback'])
def test_labelled_real_phase_b_outcome_then_simulated_lost_ack_discards_and_key_reconciles(actor, monkeypatch, outcome):
    api = import_module('apps.core.document_services')
    original_commit, original_rollback, original_close = connection.commit, connection.rollback, connection.close
    commits, rollbacks, closes, business_write = [], [], [], []
    driver = connection.connection
    def commit():
        original_commit()
        commits.append(True)
        if outcome == 'commit' and len(commits) == 2:
            raise OperationalError('Synthetic ACK lost after actual business COMMIT')
    def rollback():
        original_rollback()
        rollbacks.append(True)
        if outcome == 'rollback':
            raise OperationalError('Synthetic ACK lost after actual business ROLLBACK')
    def close():
        closes.append(connection.connection)
        return original_close()
    def fail(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.lstrip().upper().startswith('INSERT') and 'CORE_DOCUMENTINTENTRECEIPT' in sql.upper():
            business_write.append(True)
            if outcome == 'rollback':
                raise OperationalError('Synthetic business failure before rollback')
        return result
    with monkeypatch.context() as patch:
        patch.setattr(connection, 'commit', commit)
        patch.setattr(connection, 'rollback', rollback)
        patch.setattr(connection, 'close', close)
        with connection.execute_wrapper(fail), _denied():
            _create(api, actor)
        assert len(commits) == (2 if outcome == 'commit' else 1)
        # Django atomic attempts rollback when COMMIT raises DatabaseError.
        # After our actual acknowledged server commit, that idle rollback is a
        # no-op and cannot undo persisted rows; independent observation below
        # distinguishes the true outcomes rather than counting it as a refund.
        assert len(rollbacks) == 1
        assert business_write == [True] and driver in closes and driver.closed
    assert _observed(actor) == ((1, 1, 1, 1) if outcome == 'commit' else (1, 0, 0, 0))
    result = _create(api, actor)  # explicit fresh-context same-key attempt, no automatic retry
    assert result.status == 201 and type(result.body) is bytes
    assert _observed(actor) == ((2, 1, 1, 2) if outcome == 'commit' else (2, 1, 1, 1))


@pytest.mark.parametrize('after_commit', [False, True])
def test_phase_b_flag_flip_withholds_bytes_with_actual_commit_distinction(actor, settings, after_commit):
    api = import_module('apps.core.document_services')
    fired = []
    original_commit = connection.commit
    def flip_on_event(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.lstrip().upper().startswith('INSERT') and 'CORE_DOCUMENTACCESSEVENT' in sql.upper():
            fired.append(True)
            if not after_commit:
                settings.HMS_DOCUMENT_METADATA_ENABLED = False
        return result
    def commit():
        original_commit()
        if fired and after_commit:
            settings.HMS_DOCUMENT_METADATA_ENABLED = False
    from unittest.mock import patch
    with patch.object(connection, 'commit', commit), connection.execute_wrapper(flip_on_event), _denied():
        _create(api, actor)
    assert fired == [True]
    assert _observed(actor) == ((1, 1, 1, 1) if after_commit else (1, 0, 0, 0))


def _pending_network_boundary(actor, context, boundary):
    """A genuine saved reciprocal graph; real loader and pure selection remain on."""
    allow = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
    deny = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['127.0.0.1/32']}
    activated = boundary - timedelta(seconds=300)
    bindings = dict(owner=actor.branch.organisation, actor=actor.user, session_digest=context.session_digest,
        epoch=0, operator_version=1, verified_ip=context.verified_ip,
        environment_digest=context.environment_digest, base_revision=1)
    preview = NetworkPolicyPreview.objects.create(**bindings, policy=allow, policy_digest=policy_digest(allow),
        request_digest='c' * 64, reason='Synthetic phase-B boundary only', normalisations=[],
        created_at=activated - timedelta(seconds=1), expires_at=activated + timedelta(seconds=299), request_key=uuid4())
    change = NetworkPolicyChange.objects.create(**bindings, preview=preview, candidate_policy=allow,
        candidate_policy_digest=policy_digest(allow), fallback_policy=deny, fallback_policy_digest=policy_digest(deny),
        activation_revision=2, activated_at=activated, rollback_at=boundary, reason='Synthetic phase-B boundary only')
    NetworkPolicyPreview.objects.filter(pk=preview.pk).update(result_change=change)
    NetworkPolicyState.objects.filter(pk=1).update(bound_owner=actor.branch.organisation, revision=2,
        confirmed_policy=deny, confirmed_policy_digest=policy_digest(deny), pending_change=change)


@pytest.mark.parametrize('crossing,code,status', [
    ('session_expiry', 'not_authenticated', 401),
    ('network_rollback', 'network_denied', 403),
    ('withdraw_expiry', 'intent_state_conflict', 409),
])
def test_real_deferred_phase_b_wait_then_exact_wall_boundary_rolls_back(actor, monkeypatch, crossing, code, status):
    """Actual pg advisory wait plus controlled wall crossing, not real elapsed expiry."""
    api = import_module('apps.core.document_services')
    clock = [timezone.now()]
    boundary = clock[0] + timedelta(seconds=1)
    monkeypatch.setattr(timezone, 'now', lambda: clock[0])
    operation = 'intent.withdraw' if crossing == 'withdraw_expiry' else 'intent.create'
    context = capture_document_context(actor.request, operation)
    document = None
    if crossing == 'session_expiry':
        Session.objects.filter(session_key=actor.request.session.session_key).update(expire_date=boundary)
    elif crossing == 'network_rollback':
        _pending_network_boundary(actor, context, boundary)
    else:
        document = PatientDocumentIntent.objects.create(patient=actor.patient, created_by=actor.user,
            category='registration', declared_filename='synthetic.png', declared_media_type='image/png',
            declared_size_bytes=1, declared_sha256='a' * 64,
            created_at=boundary - timedelta(minutes=30), expires_at=boundary)
    policy_before = list(NetworkPolicyState.objects.values())
    key, waiter = uuid4().int % 2**62 + 1, _pid()
    ready, release, observed = Event(), Event(), Event()
    seen = []
    def blocker():
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_lock(%s)', [key])
            holder = _pid()
            ready.set()
            try:
                deadline = monotonic() + 6
                while not release.is_set() and monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [holder, waiter])
                        if cursor.fetchone()[0]:
                            clock[0] = boundary
                            observed.set()
                            return
                    release.wait(.01)
            finally:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock(%s)', [key])
        finally:
            connection.close()
    def record(execute, sql, params, many, execution_context):
        seen.append(sql.upper())
        return execute(sql, params, many, execution_context)
    with _event_trigger(f'PERFORM pg_advisory_xact_lock({key});'), ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(blocker)
        try:
            assert ready.wait(3)
            with connection.execute_wrapper(record), _denied(code, status):
                if document is None:
                    api.create_document_intent(context, str(actor.patient.pk), actor.key, BODY)
                else:
                    api.withdraw_document_intent(context, str(actor.patient.pk), str(document.pk), actor.key,
                        b'{"expected_version":1,"reason":"Synthetic withdrawal boundary"}')
            assert observed.is_set(), 'Actual PostgreSQL deferred constraint wait was not observed'
        finally:
            release.set()
            worker.result(8)
    assert _observed(actor) == (1, 1 if document else 0, 0, 0)
    if document:
        document.refresh_from_db()
        assert (document.status, document.version, document.withdrawn_at) == ('pending', 1, None)
    assert list(NetworkPolicyState.objects.values()) == policy_before
    constraints = [i for i, sql in enumerate(seen) if 'SET CONSTRAINTS ALL IMMEDIATE' in sql]
    assert len(constraints) == 2
    assert any('DJANGO_SESSION' in sql for sql in seen[constraints[-1] + 1:])
    assert not any(sql.lstrip().startswith(('INSERT ', 'UPDATE ', 'DELETE ')) for sql in seen[constraints[-1] + 1:])


@pytest.mark.parametrize('after_commit', [False, True])
def test_original_monotonic_budget_exhaustion_withholds_phase_b_bytes(actor, monkeypatch, after_commit):
    """Controlled clock injection; this is cooperative-budget acceptance, not a server timeout."""
    api = import_module('apps.core.document_services')
    from apps.core import document_access
    context = capture_document_context(actor.request, 'intent.create')
    original_commit = connection.commit
    business, exhausted = [], []
    def exhaust():
        exhausted.append(True)
        # Existing admission budget remains authoritative when reused by phase B.
        monkeypatch.setattr(document_access, 'monotonic', lambda: context.monotonic_started_at + 5)
        # A phase-B local import is permitted; patch the clock source, not a decision.
        if hasattr(api, 'monotonic'):
            monkeypatch.setattr(api, 'monotonic', lambda: context.monotonic_started_at + 5)
        monkeypatch.setattr('time.monotonic', lambda: context.monotonic_started_at + 5)
    def record(execute, sql, params, many, execution_context):
        result = execute(sql, params, many, execution_context)
        if sql.lstrip().upper().startswith('INSERT') and 'CORE_DOCUMENTACCESSEVENT' in sql.upper():
            business.append(True)
            if not after_commit:
                exhaust()
        return result
    def commit():
        original_commit()
        if business and after_commit:
            exhaust()
    monkeypatch.setattr(connection, 'commit', commit)
    with connection.execute_wrapper(record), _denied():
        api.create_document_intent(context, str(actor.patient.pk), actor.key, BODY)
    assert exhausted == [True]
    assert _observed(actor) == ((1, 1, 1, 1) if after_commit else (1, 0, 0, 0))


@pytest.mark.parametrize('extra,accepted', [(0, True), (1, False)])
def test_artificial_encoder_boundary_262144_bytes_does_not_widen_metadata_schema(extra, accepted):
    """Pure artificial payload measures the frozen encoding seam, not accepted input."""
    api = import_module('apps.core.document_services')
    payload = {'x': 'a' * (262136 + extra)}  # compact ASCII JSON has 8 bytes overhead
    if accepted:
        result = api._encode_document_body(payload)
        assert type(result) is bytes and len(result) == 262144
        assert result[:6] == b'{"x":"' and result[-2:] == b'"}'
    else:
        with _denied():
            api._encode_document_body(payload)


def test_original_budget_exhaustion_after_real_encoding_rolls_back_before_commit(actor, monkeypatch):
    api = import_module('apps.core.document_services')
    from apps.core import document_access
    context = capture_document_context(actor.request, 'intent.create')
    original_encode = api._encode_document_body
    encoded = []
    def encode_then_clock_crosses(payload):
        result = original_encode(payload)  # real production encoder executes
        assert type(result) is bytes
        encoded.append(len(result))
        exhausted = lambda: context.monotonic_started_at + 5
        monkeypatch.setattr(document_access, 'monotonic', exhausted)
        if hasattr(api, 'monotonic'):
            monkeypatch.setattr(api, 'monotonic', exhausted)
        monkeypatch.setattr('time.monotonic', exhausted)
        return result
    monkeypatch.setattr(api, '_encode_document_body', encode_then_clock_crosses)
    with _denied():
        api.create_document_intent(context, str(actor.patient.pk), actor.key, BODY)
    assert len(encoded) == 1 and 0 < encoded[0] <= 262144
    assert _observed(actor) == (1, 0, 0, 0)
