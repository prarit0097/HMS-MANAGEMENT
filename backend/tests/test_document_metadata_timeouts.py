"""Isolated PG admission controls/failures; no live database may run these tests.

The deferred trigger and injected sleeps are test infrastructure, not actor-FK
waits or evidence of a production outage. Lost acknowledgement is explicitly a
real commit followed by a simulated client exception, not a real network fault.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from importlib import import_module
from threading import Event
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.db import SessionStore
from django.db import OperationalError, close_old_connections, connection, transaction
from django.test import RequestFactory
from django.utils import timezone

from apps.core.models import Branch, DocumentMetadataRateWindow, Membership, Organisation
from apps.core.network_models import NetworkPolicyState
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
