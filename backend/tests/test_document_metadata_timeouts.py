"""Isolated PG admission controls/failures; no live database may run these tests.

The deferred trigger and injected sleeps are test infrastructure, not actor-FK
waits or evidence of a production outage. Lost acknowledgement is explicitly a
real commit followed by a simulated client exception, not a real network fault.
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

from apps.core.models import Branch, DocumentMetadataRateWindow, Membership, Organisation
from apps.core.network_models import NetworkPolicyChange, NetworkPolicyPreview, NetworkPolicyState
from apps.security.network_policy import policy_digest


pytestmark = pytest.mark.django_db(transaction=True)
CONTROLS = ('lock_timeout', 'statement_timeout', 'transaction_timeout')


@pytest.fixture(autouse=True)
def actual_pg_only():
    if connection.vendor != 'postgresql':
        pytest.skip('Actual PostgreSQL>=17 LOCAL controls, locks, disconnects and commit acknowledgement are required; SQLite is not timeout acceptance.')
    if connection.pg_version < 170000:
        pytest.skip('PostgreSQL>=17 transaction_timeout is required.')


@pytest.fixture
def actor(settings):
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.DATABASE_ROUTERS = []
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    user = get_user_model().objects.create_user(username='synthetic-admission-timeout', password='Synthetic-admission-timeout-28!')
    branch = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic admission timeout'), name='Desk', code='TIMEOUT')
    Membership.objects.create(user=user, branch=branch, role='reception')
    request = RequestFactory().get('/synthetic-admission-timeout', REMOTE_ADDR='127.0.0.1')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    allow = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
    NetworkPolicyState.objects.update_or_create(pk=1, defaults={
        'confirmed_policy': allow, 'confirmed_policy_digest': policy_digest(allow), 'pending_change': None,
    })
    return SimpleNamespace(user=user, request=request, patient=str(uuid4()))


def _context(actor):
    from apps.core.document_authority import capture_document_context
    return capture_document_context(actor.request, 'intent.list')


def _pid():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_backend_pid()')
        return cursor.fetchone()[0]


def _controls():
    with connection.cursor() as cursor:
        return tuple(_setting(cursor, name) for name in CONTROLS)


def _setting(cursor, name):
    # Names are fixed test constants, never external SQL input.
    cursor.execute('SHOW ' + name)
    return cursor.fetchone()[0]


def _count_elsewhere(actor_id):
    def read():
        close_old_connections()
        try:
            return DocumentMetadataRateWindow.objects.filter(actor_id=actor_id).values_list('admitted_count', flat=True).first()
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(read).result(10)


def _seed(actor):
    DocumentMetadataRateWindow.objects.create(
        actor=actor.user, window_started_at=timezone.now().replace(second=0, microsecond=0), admitted_count=1)


@contextmanager
def _unavailable():
    from apps.core.document_authority import DocumentServiceError
    with pytest.raises(DocumentServiceError) as caught:
        yield
    assert (caught.value.code, caught.value.status, caught.value.message, caught.value.retry_after) == (
        'document_metadata_unavailable', 503, 'Document details are unavailable. Try again later.', None)


def _state(exc):
    return getattr(exc, 'sqlstate', None) or getattr(exc.__cause__, 'sqlstate', None)


def _actor_lock(sql):
    upper = sql.upper()
    return 'FOR NO KEY UPDATE' in upper and 'AUTH_USER' in upper


def test_local_2_3_5_controls_are_active_before_locks_and_reset_after_commit(actor):
    api = import_module('apps.core.document_access')
    context = _context(actor)
    before, observed = _controls(), []

    def inspect(execute, sql, params, many, execution_context):
        if _actor_lock(sql):
            observed.append(_controls())
        return execute(sql, params, many, execution_context)

    with connection.execute_wrapper(inspect):
        result = api.admit_document_command(context, actor.patient)
    assert observed == [('2s', '3s', '5s')]
    assert result._context is context
    assert _controls() == before
    assert connection.connection.info.transaction_status.name == 'IDLE'
    assert _count_elsewhere(actor.user.pk) == 1


def test_real_actor_lock_timeout_rolls_back_and_connection_is_reusable(actor):
    api = import_module('apps.core.document_access')
    _seed(actor)
    context, waiter_pid = _context(actor), _pid()
    ready, release, observed_wait = Event(), Event(), Event()
    states = []

    def holder():
        close_old_connections()
        try:
            with transaction.atomic():
                get_user_model().objects.select_for_update(no_key=True, of=('self',)).get(pk=actor.user.pk)
                holder_pid = _pid()
                ready.set()
                deadline = monotonic() + 8
                while not release.is_set() and monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [holder_pid, waiter_pid])
                        if cursor.fetchone()[0]:
                            observed_wait.set()
                    release.wait(.02)
                assert release.wait(5), 'Admission did not finish its bounded lock attempt'
        finally:
            connection.close()

    def record(execute, sql, params, many, execution_context):
        try:
            return execute(sql, params, many, execution_context)
        except Exception as exc:
            states.append(_state(exc))
            raise

    with ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(holder)
        try:
            assert ready.wait(5), 'Actor holder did not acquire its lock'
            with connection.execute_wrapper(record), _unavailable():
                api.admit_document_command(context, actor.patient)
            assert observed_wait.is_set(), 'No actual PostgreSQL blocker was observed'
            assert '55P03' in states
        finally:
            release.set()
            worker.result(10)
    assert _count_elsewhere(actor.user.pk) == 1
    assert _pid() > 0
    assert connection.connection.info.transaction_status.name == 'IDLE'


def test_real_statement_timeout_rolls_back_before_allowance(actor):
    api = import_module('apps.core.document_access')
    _seed(actor)
    context, injected, states = _context(actor), [], []

    def pause(execute, sql, params, many, execution_context):
        if _actor_lock(sql) and not injected:
            injected.append(True)
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_sleep(3.4)')
            except Exception as exc:
                states.append(_state(exc))
                raise
        return execute(sql, params, many, execution_context)

    with connection.execute_wrapper(pause), _unavailable():
        api.admit_document_command(context, actor.patient)
    assert injected == [True]
    assert states == ['57014']  # A single pg_sleep(6) would only prove this timeout.
    assert _count_elsewhere(actor.user.pk) == 1
    assert _pid() > 0


@pytest.mark.parametrize('mode', ['cumulative_short_statements', 'idle_then_query'])
def test_real_transaction_timeout_terminates_and_reconnects_distinct_from_statement_timeout(actor, mode):
    api = import_module('apps.core.document_access')
    _seed(actor)
    context, old_pid = _context(actor), _pid()
    injected, completed_short_statements, states = [], [], []

    def expire_transaction(execute, sql, params, many, execution_context):
        if _actor_lock(sql) and not injected:
            injected.append(True)
            try:
                with connection.cursor() as cursor:
                    if mode == 'cumulative_short_statements':
                        for _ in range(4):
                            cursor.execute('SELECT pg_sleep(1.4)')
                            completed_short_statements.append(True)
                    else:
                        # Labelled injected idle pause: server transaction timeout,
                        # not the cooperative budget, must kill this connection.
                        Event().wait(5.25)
                        cursor.execute('SELECT 1')
            except Exception as exc:
                states.append(_state(exc))
                raise
        return execute(sql, params, many, execution_context)

    with connection.execute_wrapper(expire_transaction), _unavailable():
        api.admit_document_command(context, actor.patient)
    assert injected == [True]
    assert states and '57014' not in states
    assert all(state in (None, '25P04') for state in states)
    if mode == 'cumulative_short_statements':
        assert len(completed_short_statements) >= 3
    assert _count_elsewhere(actor.user.pk) == 1
    assert _pid() != old_pid
    assert connection.connection.info.transaction_status.name == 'IDLE'


@contextmanager
def _isolated_deferred_failure_trigger():
    """DDL solely in pytest's disposable DB; no actor FK wait is manufactured."""
    name = 'synthetic_doc_admission_' + uuid4().hex
    quoted = connection.ops.quote_name(name)
    table = connection.ops.quote_name(DocumentMetadataRateWindow._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE FUNCTION {quoted}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic deferred guard' USING ERRCODE='23514'; END $$")
        cursor.execute(f'CREATE CONSTRAINT TRIGGER {quoted} AFTER INSERT OR UPDATE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION {quoted}()')
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP TRIGGER IF EXISTS {quoted} ON {table}')
            cursor.execute(f'DROP FUNCTION IF EXISTS {quoted}()')


def test_actual_deferred_failure_is_forced_before_final_samples_and_rolls_back(actor):
    api = import_module('apps.core.document_access')
    context, sql_seen, states = _context(actor), [], []

    def record(execute, sql, params, many, execution_context):
        sql_seen.append(sql.upper())
        try:
            return execute(sql, params, many, execution_context)
        except Exception as exc:
            states.append(_state(exc))
            raise

    with _isolated_deferred_failure_trigger(), connection.execute_wrapper(record), _unavailable():
        api.admit_document_command(context, actor.patient)
    constraint = next(i for i, sql in enumerate(sql_seen) if 'SET CONSTRAINTS ALL IMMEDIATE' in sql)
    assert '23514' in states
    assert not any('DJANGO_SESSION' in sql or 'CORE_NETWORK' in sql for sql in sql_seen[constraint + 1:])
    assert _count_elsewhere(actor.user.pk) is None
    assert connection.connection.info.transaction_status.name == 'IDLE'


def test_success_forces_constraints_before_final_samples_with_no_later_writes(actor):
    api = import_module('apps.core.document_access')
    context, sql_seen = _context(actor), []

    def record(execute, sql, params, many, execution_context):
        sql_seen.append(sql.upper().lstrip())
        return execute(sql, params, many, execution_context)

    with connection.execute_wrapper(record):
        admission = api.admit_document_command(context, actor.patient)
    constraint = next(i for i, sql in enumerate(sql_seen) if 'SET CONSTRAINTS ALL IMMEDIATE' in sql)
    assert any(sql.startswith(('INSERT ', 'UPDATE ')) and 'DOCUMENTMETADATARATEWINDOW' in sql for sql in sql_seen[:constraint])
    assert any('DJANGO_SESSION' in sql for sql in sql_seen[constraint + 1:])
    assert any('CORE_NETWORK' in sql for sql in sql_seen[constraint + 1:])
    assert not any(sql.startswith(('INSERT ', 'UPDATE ', 'DELETE ')) for sql in sql_seen[constraint + 1:])
    assert admission._context is context
    assert _count_elsewhere(actor.user.pk) == 1


def test_labelled_real_commit_then_simulated_lost_ack_discards_connection_without_refund_or_retry(actor, monkeypatch):
    api = import_module('apps.core.document_access')
    context = _context(actor)
    original_commit, original_close = connection.commit, connection.close
    driver, commits, closes = connection.connection, [], []

    def committed_but_ack_lost():
        original_commit()  # This is a real durable database commit.
        commits.append(True)
        raise OperationalError('Synthetic committed-but-lost acknowledgement')

    def record_close():
        closes.append(connection.connection)
        return original_close()

    with monkeypatch.context() as patch:
        patch.setattr(connection, 'commit', committed_but_ack_lost)
        patch.setattr(connection, 'close', record_close)
        with _unavailable():
            api.admit_document_command(context, actor.patient)
        assert commits == [True], 'No automatic retry is permitted after uncertain acknowledgement'
        assert driver in closes and driver.closed
        assert _count_elsewhere(actor.user.pk) == 1  # Unknown is not a refund/rollback claim.
    fresh_context = _context(actor)
    admission = api.admit_document_command(fresh_context, actor.patient)
    assert admission._context is fresh_context
    assert _count_elsewhere(actor.user.pk) == 2  # A later explicit attempt consumes again.


@contextmanager
def _isolated_deferred_advisory_trigger(advisory_key):
    """Synthetic isolated-test wait, NOT a production actor-FK wait.

    A deferred rate-row trigger waits for a separately held advisory lock when
    production executes SET CONSTRAINTS. No production schema is changed.
    """
    name = 'synthetic_doc_wait_' + uuid4().hex
    quoted = connection.ops.quote_name(name)
    table = connection.ops.quote_name(DocumentMetadataRateWindow._meta.db_table)
    assert type(advisory_key) is int and 0 < advisory_key < 2**63
    with connection.cursor() as cursor:
        cursor.execute(f'CREATE FUNCTION {quoted}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_advisory_xact_lock({advisory_key}); RETURN NEW; END $$')
        cursor.execute(f'CREATE CONSTRAINT TRIGGER {quoted} AFTER INSERT OR UPDATE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION {quoted}()')
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP TRIGGER IF EXISTS {quoted} ON {table}')
            cursor.execute(f'DROP FUNCTION IF EXISTS {quoted}()')


def _saved_pending_allow_until(context, actor, boundary):
    """Persist a genuine reciprocal graph; real loader validation/SELECT stays on."""
    owner = Membership.objects.select_related('branch__organisation').get(user=actor.user).branch.organisation
    allow = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
    deny = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['127.0.0.1/32']}
    activated = boundary - timedelta(seconds=300)
    bindings = dict(owner=owner, actor=actor.user, session_digest=context.session_digest,
                    epoch=0, operator_version=1, verified_ip=context.verified_ip,
                    environment_digest=context.environment_digest, base_revision=1)
    preview = NetworkPolicyPreview.objects.create(
        **bindings, policy=allow, policy_digest=policy_digest(allow), request_digest='c' * 64,
        reason='Synthetic deferred-wait test only', normalisations=[],
        created_at=activated - timedelta(seconds=1), expires_at=activated + timedelta(seconds=299),
        request_key=uuid4())
    change = NetworkPolicyChange.objects.create(
        **bindings, preview=preview, candidate_policy=allow, candidate_policy_digest=policy_digest(allow),
        fallback_policy=deny, fallback_policy_digest=policy_digest(deny), activation_revision=2,
        activated_at=activated, rollback_at=boundary, reason='Synthetic deferred-wait test only')
    NetworkPolicyPreview.objects.filter(pk=preview.pk).update(result_change=change)
    NetworkPolicyState.objects.filter(pk=1).update(
        bound_owner=owner, revision=2, confirmed_policy=deny, confirmed_policy_digest=policy_digest(deny),
        pending_change=change)
    return change


@pytest.mark.parametrize('crossing,code', [('session_expiry', 'not_authenticated'),
                                         ('network_rollback', 'network_denied')])
def test_labelled_deferred_trigger_real_wait_resamples_expiry_or_saved_network_graph(
        actor, monkeypatch, crossing, code):
    api = import_module('apps.core.document_access')
    from apps.core.document_authority import DocumentServiceError
    clock = [timezone.now()]
    boundary = clock[0] + timedelta(seconds=1)
    monkeypatch.setattr(timezone, 'now', lambda: clock[0])
    context = _context(actor)
    if crossing == 'session_expiry':
        Session.objects.filter(session_key=actor.request.session.session_key).update(expire_date=boundary)
    else:
        _saved_pending_allow_until(context, actor, boundary)
    before_policy = list(NetworkPolicyState.objects.values())
    key, waiter = uuid4().int % (2**62) + 1, _pid()
    ready, stop, observed = Event(), Event(), Event()
    sql_seen = []

    def blocker():
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_lock(%s)', [key])
            holder = _pid()
            ready.set()
            try:
                deadline = monotonic() + 4
                while not stop.is_set() and monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [holder, waiter])
                        if cursor.fetchone()[0]:
                            # Controlled wall-clock crossing only AFTER PostgreSQL
                            # proves the constraint statement is really waiting.
                            clock[0] = boundary
                            observed.set()
                            return
                    stop.wait(.01)
            finally:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock(%s)', [key])
        finally:
            connection.close()

    def record(execute, sql, params, many, execution_context):
        sql_seen.append(sql.upper())
        return execute(sql, params, many, execution_context)

    with _isolated_deferred_advisory_trigger(key), ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(blocker)
        try:
            assert ready.wait(3), 'Synthetic advisory blocker did not acquire its lock'
            with connection.execute_wrapper(record), pytest.raises(DocumentServiceError) as denied:
                api.admit_document_command(context, actor.patient)
            assert (denied.value.code, denied.value.status) == (code, 401 if crossing == 'session_expiry' else 403)
            assert observed.is_set(), 'No actual PG constraint-statement wait was observed'
        finally:
            stop.set()
            worker.result(6)
    constraint = next(i for i, sql in enumerate(sql_seen) if 'SET CONSTRAINTS ALL IMMEDIATE' in sql)
    assert any('DJANGO_SESSION' in sql for sql in sql_seen[constraint + 1:])
    if crossing == 'network_rollback':
        assert any('CORE_NETWORKPOLICYSTATE' in sql for sql in sql_seen[constraint + 1:])
    assert not any(sql.lstrip().startswith(('INSERT ', 'UPDATE ', 'DELETE ')) for sql in sql_seen[constraint + 1:])
    assert _count_elsewhere(actor.user.pk) is None
    assert list(NetworkPolicyState.objects.values()) == before_policy


def test_labelled_real_rollback_then_lost_ack_discards_connection_and_allows_fresh_attempt(actor, monkeypatch):
    api = import_module('apps.core.document_access')
    from apps.core.document_authority import DocumentServiceError
    context, old_pid = _context(actor), _pid()
    driver = connection.connection
    original_rollback, original_close = connection.rollback, connection.close
    rollbacks, closes, writes = [], [], []

    def rolled_back_but_ack_lost():
        original_rollback()  # Actual rollback; acknowledgement exception is simulated.
        rollbacks.append(True)
        raise OperationalError('Synthetic rolled-back-but-lost acknowledgement')

    def record_close():
        closes.append(connection.connection)
        return original_close()

    def fail_after_rate_write(execute, sql, params, many, execution_context):
        result = execute(sql, params, many, execution_context)
        if sql.lstrip().upper().startswith('INSERT INTO "CORE_DOCUMENTMETADATARATEWINDOW"'):
            writes.append(True)
            raise DocumentServiceError('document_metadata_unavailable', 503,
                                       'Document details are unavailable. Try again later.')
        return result

    with monkeypatch.context() as patch:
        patch.setattr(connection, 'rollback', rolled_back_but_ack_lost)
        patch.setattr(connection, 'close', record_close)
        with connection.execute_wrapper(fail_after_rate_write), _unavailable():
            api.admit_document_command(context, actor.patient)
        assert writes == [True] and rollbacks == [True], 'Uncertain rollback must not retry admission'
        assert driver in closes and driver.closed
        assert _count_elsewhere(actor.user.pk) is None  # Independent observation, not an uncertainty refund claim.
    assert _pid() != old_pid
    fresh = _context(actor)
    result = api.admit_document_command(fresh, actor.patient)
    assert result._context is fresh and _count_elsewhere(actor.user.pk) == 1


def test_normal_atomic_exit_after_final_read_rollback_only_cannot_mint_admission(actor, monkeypatch):
    """Actual Django rollback-only exit, with no fake COMMIT acknowledgement.

    A final real network SELECT is allowed to complete, then a transaction-local
    rollback marker simulates an enclosing dependency marking the owned phase.
    atomic may return normally after ROLLBACK; normal exit is not commit proof.
    """
    api = import_module('apps.core.document_access')
    context = _context(actor)
    constraints, marked, commits, rollbacks = [], [], [], []
    original_commit, original_rollback = connection.commit, connection.rollback

    def record_commit():
        original_commit()
        commits.append(True)

    def record_rollback():
        original_rollback()
        rollbacks.append(True)

    def mark_after_final_real_network_read(execute, sql, params, many, execution_context):
        result = execute(sql, params, many, execution_context)
        upper = sql.upper().lstrip()
        if upper.startswith('SET CONSTRAINTS ALL IMMEDIATE'):
            constraints.append(True)
        elif (constraints and not marked and upper.startswith('SELECT')
              and 'CORE_NETWORKPOLICYSTATE' in upper):
            transaction.set_rollback(True, using='default')
            marked.append(True)
        return result

    monkeypatch.setattr(connection, 'commit', record_commit)
    monkeypatch.setattr(connection, 'rollback', record_rollback)
    with connection.execute_wrapper(mark_after_final_real_network_read), _unavailable():
        api.admit_document_command(context, actor.patient)
    assert constraints == [True] and marked == [True]
    assert commits == [] and rollbacks == [True]
    assert _count_elsewhere(actor.user.pk) is None
