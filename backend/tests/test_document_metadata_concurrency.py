"""Actual-PG B2a-L admission counts and lock boundaries, never business services.

All absent-production imports occur inside tests. SQLite explicitly skips; it
cannot establish durable commits, lock compatibility or inter-worker ordering.
"""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, fields, replace
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
from django.db import close_old_connections, connection, transaction
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.core.document_authority import capture_document_context, DocumentServiceError
from apps.core.models import Branch, DocumentMetadataRateWindow, IdentitySecurity, Membership, Organisation
from apps.core.network_models import NetworkPolicyState
from apps.security.network_policy import policy_digest

pytestmark = pytest.mark.django_db(transaction=True)
PATIENT = 'ab1d44b8-27c1-4c45-b39b-9ef210920593'
DOCUMENT = 'dc0cbca3-debb-4d64-b4dd-70591f1a1cdb'
OPS = ('intent.list', 'intent.detail', 'intent.create', 'intent.withdraw')


def _request(user):
    request = RequestFactory().get('/', REMOTE_ADDR='127.0.0.1')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    return request


@pytest.fixture
def actor(settings):
    if connection.vendor != 'postgresql':
        pytest.skip('Requires actual PostgreSQL >=17 durable admission, separate connections and pg_blocking_pids; no SQLite success substitute.')
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    user = get_user_model().objects.create_user(username='synthetic-admission-count', password='Synthetic-count-287!')
    branch = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic admission'), name='Desk', code='ADMIT')
    Membership.objects.create(user=user, branch=branch, role='reception')
    return SimpleNamespace(user=user, branch=branch, request=_request(user))


@pytest.fixture
def clock(monkeypatch):
    # Fixed wall time only. Each actual request retains its real monotonic budget.
    value = [timezone.now().replace(second=30, microsecond=0)]
    monkeypatch.setattr(timezone, 'now', lambda: value[0])
    return value


def _args(operation):
    if operation == 'intent.list':
        return {}
    if operation == 'intent.detail':
        return {'document_id': DOCUMENT}
    if operation == 'intent.create':
        return {'key': str(uuid4()), 'body': json.dumps({'category': 'registration', 'filename': 'synthetic.png',
                'media_type': 'image/png', 'size_bytes': 1, 'sha256': 'a' * 64}).encode()}
    return {'document_id': DOCUMENT, 'key': str(uuid4()),
            'body': b'{"expected_version":1,"reason":"Synthetic withdrawal"}'}


@contextmanager
def _no_business():
    with CaptureQueriesContext(connection) as queries:
        try:
            yield
        finally:
            for item in queries:
                sql = item['sql'].lower()
                assert not any(table in sql for table in ('core_patient', 'core_documentintentreceipt',
                              'core_documentaccessevent', 'core_auditevent')), sql
                if 'for update' in sql or 'for no key update' in sql:
                    assert not any(table in sql for table in ('core_membership', 'core_staffaccessrevision',
                                  'core_organisation', 'core_branch', 'core_network')), sql


def _call(api, actor, operation='intent.list', context=None):
    context = context or capture_document_context(actor.request, operation)
    with _no_business():
        return api.admit_document_command(context, PATIENT, **_args(operation))


def _seed(actor, instant, count):
    # Explicit seeded boundary, not evidence of count distinct requests.
    return DocumentMetadataRateWindow.objects.create(actor=actor.user,
        window_started_at=instant.replace(second=0, microsecond=0), admitted_count=count)


def _pid():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_backend_pid()')
        return cursor.fetchone()[0]


def _independent(function):
    close_old_connections()
    try:
        return function()
    finally:
        connection.close()


def _committed_count(actor_id):
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_independent, lambda: DocumentMetadataRateWindow.objects.get(actor_id=actor_id).admitted_count).result(10)


def test_sixty_real_calls_across_operations_then_61st_and_issued_proof(actor, clock, monkeypatch):
    api = import_module('apps.core.document_access')
    first = first_context = None
    for number in range(60):
        operation = OPS[number % len(OPS)]
        context = capture_document_context(actor.request, operation)
        result = _call(api, actor, operation, context)
        assert result.operation == operation and result.patient_id == PATIENT
        assert result.operation_started_at == context.operation_started_at
        assert result.monotonic_started_at == context.monotonic_started_at
        if first is None:
            first, first_context = result, context
    assert _committed_count(actor.user.pk) == 60
    with CaptureQueriesContext(connection) as saturated_queries, pytest.raises(DocumentServiceError) as denied:
        _call(api, actor)
    assert (denied.value.code, denied.value.status, denied.value.retry_after) == ('rate_limited', 429, 30)
    _assert_no_rate_writes(saturated_queries)
    assert _committed_count(actor.user.pk) == 60
    with pytest.raises(FrozenInstanceError):
        first.patient_id = DOCUMENT
    forged = type(first)(**{field.name: getattr(first, field.name) for field in fields(first)})
    other = capture_document_context(actor.request, 'intent.list')
    def forbidden(*args, **kwargs):
        pytest.fail('Pure admission issuance validator performed I/O')
    monkeypatch.setattr(timezone, 'now', forbidden)
    monkeypatch.setattr('time.monotonic', forbidden)
    actor.request.user = actor.request.session = None
    with connection.execute_wrapper(lambda *args: forbidden()):
        api._validate_document_admission(first, first_context, 'intent.list')
        for value, context, operation in (
            (copy.copy(first), first_context, 'intent.list'), (replace(first), first_context, 'intent.list'),
            (forged, first_context, 'intent.list'), (first, other, 'intent.list'),
            (first, first_context, 'intent.withdraw'),
        ):
            with pytest.raises(DocumentServiceError) as denied:
                api._validate_document_admission(value, context, operation)
            assert denied.value.code == 'document_metadata_unavailable'


@pytest.mark.parametrize('backward', [False, True])
def test_exact_minute_reset_or_backward_time_without_repair(actor, clock, backward):
    api = import_module('apps.core.document_access')
    row = _seed(actor, clock[0], 60)
    clock[0] = row.window_started_at + timedelta(minutes=-1 if backward else 1)
    if backward:
        with pytest.raises(DocumentServiceError) as denied:
            _call(api, actor)
        assert denied.value.code == 'document_metadata_unavailable'
        row.refresh_from_db()
        assert row.admitted_count == 60
    else:
        _call(api, actor)
        row.refresh_from_db()
        assert (row.admitted_count, row.window_started_at) == (1, clock[0])


@pytest.mark.parametrize('saturated', [False, True])
def test_final_minute_crossing_keeps_sampled_charge_or_saturation(actor, clock, saturated, settings):
    api = import_module('apps.core.document_access')
    row = _seed(actor, clock[0], 60 if saturated else 59)
    if saturated:
        settings.HMS_DOCUMENT_METADATA_ENABLED = False  # Valid false still yields final-authorised429.
    clock[0] = row.window_started_at + timedelta(seconds=59, microseconds=999999)
    crossed = []
    def cross_after_constraints(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.strip().upper().startswith('SET CONSTRAINTS ALL IMMEDIATE'):
            clock[0] = row.window_started_at + timedelta(minutes=1)
            crossed.append(True)
        return result
    with connection.execute_wrapper(cross_after_constraints), CaptureQueriesContext(connection) as queries:
        if saturated:
            with pytest.raises(DocumentServiceError) as denied:
                _call(api, actor)
            assert (denied.value.code, denied.value.retry_after) == ('rate_limited', 1)
        else:
            result = _call(api, actor)
            assert result.admitted_at == clock[0]
    assert crossed == [True]
    if saturated:
        _assert_no_rate_writes(queries)
    row.refresh_from_db()
    assert row.admitted_count == 60
    assert row.window_started_at == clock[0] - timedelta(minutes=1)


def test_disabled_valid_attempt_is_committed_before_503(actor, clock, settings):
    api = import_module('apps.core.document_access')
    settings.HMS_DOCUMENT_METADATA_ENABLED = False
    with pytest.raises(DocumentServiceError) as denied:
        _call(api, actor)
    assert (denied.value.code, denied.value.status) == ('document_metadata_unavailable', 503)
    assert _committed_count(actor.user.pk) == 1
    assert not IdentitySecurity.objects.filter(user=actor.user).exists()


@pytest.mark.parametrize('change,code', [('grant', 'permission_denied'), ('network', 'network_denied'), ('expiry', 'not_authenticated')])
def test_final_denial_supersedes_provisional_saturation(actor, clock, change, code):
    api = import_module('apps.core.document_access')
    row = _seed(actor, clock[0], 60)
    changed = []
    def revoke():
        if change == 'grant':
            Membership.objects.filter(user=actor.user).update(is_active=False)
        elif change == 'expiry':
            Session.objects.filter(session_key=actor.request.session.session_key).update(expire_date=clock[0])
        else:
            policy = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['127.0.0.1/32']}
            NetworkPolicyState.objects.filter(pk=1).update(confirmed_policy=policy, confirmed_policy_digest=policy_digest(policy))
    def after_constraints(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.strip().upper().startswith('SET CONSTRAINTS ALL IMMEDIATE'):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(_independent, revoke).result(10)
            changed.append(True)
        return result
    with connection.execute_wrapper(after_constraints), pytest.raises(DocumentServiceError) as denied:
        _call(api, actor)
    assert changed == [True]
    assert denied.value.code == code
    row.refresh_from_db()
    assert row.admitted_count == 60


def _observe_wait(waiter, blocker):
    # Production lock_timeout=2s: observe and release promptly, never sleep out it.
    deadline = monotonic() + 1.5
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [blocker, waiter])
            if cursor.fetchone()[0]:
                return
    pytest.fail('Actual PostgreSQL actor lock wait was not observed')


def test_first_rate_row_two_workers_serialize_on_actor_lock(actor, clock):
    api = import_module('apps.core.document_access')
    contexts = [capture_document_context(actor.request, 'intent.list') for _ in range(2)]
    held, release, attempting = Event(), Event(), Event()
    pids = {}
    def worker(number):
        def run():
            pids[number] = _pid()
            def hold_first_insert(execute, sql, params, many, context):
                result = execute(sql, params, many, context)
                if number == 0 and sql.lstrip().upper().startswith('INSERT INTO "CORE_DOCUMENTMETADATARATEWINDOW"'):
                    held.set()
                    assert release.wait(5), 'First rate writer was not released'
                return result
            if number == 1:
                attempting.set()
            with connection.execute_wrapper(hold_first_insert):
                return _call(api, actor, context=contexts[number]).operation
        return _independent(run)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(worker, 0)
        try:
            assert held.wait(3), 'First worker did not create the rate row'
            second = pool.submit(worker, 1)
            assert attempting.wait(2)
            assert pids[0] != pids[1] != _pid()
            _observe_wait(pids[1], pids[0])
        finally:
            release.set()
        assert first.result(10) == second.result(10) == 'intent.list'
    assert DocumentMetadataRateWindow.objects.filter(actor=actor.user).count() == 1
    assert _committed_count(actor.user.pk) == 2


@pytest.mark.parametrize('staff_first', [False, True])
def test_staff_target_fk_key_share_and_admission_no_key_are_compatible(actor, clock, staff_first):
    api = import_module('apps.core.document_access')
    context = capture_document_context(actor.request, 'intent.list')
    held, release, other_finished = Event(), Event(), Event()
    pids = {}
    branch = Branch.objects.create(organisation=actor.branch.organisation, name='Staff target', code='STAFF')
    def staff():
        def run():
            pids['staff'] = _pid()
            with transaction.atomic():
                Membership.objects.create(user=actor.user, branch=branch, role='doctor')
                # A real target-user FK check obtains KEY SHARE, retained to exit.
                with connection.cursor() as cursor:
                    cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                if staff_first:
                    held.set()
                    assert release.wait(5)
                else:
                    other_finished.set()
        return _independent(run)
    def admit():
        def run():
            pids['admit'] = _pid()
            def hold_insert(execute, sql, params, many, dbcontext):
                result = execute(sql, params, many, dbcontext)
                if not staff_first and sql.lstrip().upper().startswith('INSERT INTO "CORE_DOCUMENTMETADATARATEWINDOW"'):
                    held.set()
                    assert release.wait(5)
                return result
            with connection.execute_wrapper(hold_insert):
                _call(api, actor, context=context)
            if staff_first:
                other_finished.set()
        return _independent(run)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(staff if staff_first else admit)
        try:
            assert held.wait(3)
            second = pool.submit(admit if staff_first else staff)
            assert other_finished.wait(3), 'Compatible target FK and actor lock blocked one another'
            assert pids['staff'] != pids['admit'] != _pid()
            with connection.cursor() as cursor:
                cursor.execute('SELECT cardinality(pg_blocking_pids(%s))', [pids['admit' if staff_first else 'staff']])
                assert cursor.fetchone()[0] == 0
        finally:
            release.set()
        first.result(10)
        second.result(10)
    assert _committed_count(actor.user.pk) == 1


def test_different_actors_have_independent_allowances(actor, clock):
    api = import_module('apps.core.document_access')
    _seed(actor, clock[0], 60)
    user = get_user_model().objects.create_user(username='synthetic-independent-actor')
    Membership.objects.create(user=user, branch=actor.branch, role='reception')
    other = SimpleNamespace(user=user, request=_request(user))
    _call(api, other)
    assert _committed_count(actor.user.pk) == 60
    assert _committed_count(user.pk) == 1


def _assert_no_rate_writes(queries):
    for item in queries:
        sql = item['sql'].lstrip().upper()
        assert not (sql.startswith(('INSERT ', 'UPDATE ', 'DELETE '))
                    and 'DOCUMENTMETADATARATEWINDOW' in sql), sql


@pytest.mark.parametrize('transition,retained', [
    ('entry_false_later_true', True),
    ('precommit_false_post_true', True),
    ('postcommit_false', True),
    ('postcommit_malformed', True),
    ('precommit_malformed', False),
    ('entry_malformed', False),
])
def test_three_flag_observations_never_mint_after_disabled_or_malformed_value(
        actor, clock, settings, monkeypatch, transition, retained):
    api = import_module('apps.core.document_access')
    context = capture_document_context(actor.request, 'intent.list')
    settings.HMS_DOCUMENT_METADATA_ENABLED = (False if transition == 'entry_false_later_true'
                                             else 0 if transition == 'entry_malformed' else True)
    constraints, commits = [], []
    original_commit = connection.commit

    def after_constraints(execute, sql, params, many, execution_context):
        result = execute(sql, params, many, execution_context)
        if sql.strip().upper().startswith('SET CONSTRAINTS ALL IMMEDIATE'):
            constraints.append(True)
            if transition == 'entry_false_later_true':
                settings.HMS_DOCUMENT_METADATA_ENABLED = True
            elif transition == 'precommit_false_post_true':
                settings.HMS_DOCUMENT_METADATA_ENABLED = False
            elif transition == 'precommit_malformed':
                settings.HMS_DOCUMENT_METADATA_ENABLED = 'false'
        return result

    def acknowledged_commit():
        original_commit()  # Genuine commit, no simulated acknowledgement failure.
        commits.append(True)
        if transition == 'precommit_false_post_true':
            settings.HMS_DOCUMENT_METADATA_ENABLED = True
        elif transition == 'postcommit_false':
            settings.HMS_DOCUMENT_METADATA_ENABLED = False
        elif transition == 'postcommit_malformed':
            settings.HMS_DOCUMENT_METADATA_ENABLED = 0

    monkeypatch.setattr(connection, 'commit', acknowledged_commit)
    with connection.execute_wrapper(after_constraints), pytest.raises(DocumentServiceError) as denied:
        _call(api, actor, context=context)
    assert (denied.value.code, denied.value.status) == ('document_metadata_unavailable', 503)
    assert commits == ([True] if retained else [])
    assert constraints == ([] if transition == 'entry_malformed' else [True])
    if retained:
        assert _committed_count(actor.user.pk) == 1
    else:
        assert not DocumentMetadataRateWindow.objects.filter(actor=actor.user).exists()


@pytest.mark.parametrize('elapsed', [5.0, -0.001, float('nan'), float('inf')],
                         ids=['exact_five_seconds', 'backward', 'nan', 'infinite'])
def test_original_cooperative_budget_rejects_before_phase_without_allowance(actor, clock, monkeypatch, elapsed):
    api = import_module('apps.core.document_access')
    context = capture_document_context(actor.request, 'intent.list')
    # Patch only the frozen admission clock seam. Authority capture and real
    # Event/worker deadline clocks remain untouched; the context is not reminted.
    monkeypatch.setattr(api, 'monotonic', lambda: context.monotonic_started_at + elapsed)
    with CaptureQueriesContext(connection) as queries, pytest.raises(DocumentServiceError) as denied:
        _call(api, actor, context=context)
    assert (denied.value.code, denied.value.status) == ('document_metadata_unavailable', 503)
    assert not DocumentMetadataRateWindow.objects.filter(actor=actor.user).exists()
    assert not any('DOCUMENTMETADATARATEWINDOW' in item['sql'].upper() for item in queries)


@pytest.mark.parametrize('stage,retained', [('final_before_commit', False), ('after_acknowledged_commit', True)])
def test_original_budget_exact_boundary_rolls_back_or_retains_known_commit(
        actor, clock, monkeypatch, stage, retained):
    api = import_module('apps.core.document_access')
    context = capture_document_context(actor.request, 'intent.list')
    elapsed = [0.1]
    monkeypatch.setattr(api, 'monotonic', lambda: context.monotonic_started_at + elapsed[0])
    constraints, commits = [], []
    original_commit = connection.commit

    def after_constraints(execute, sql, params, many, execution_context):
        result = execute(sql, params, many, execution_context)
        if sql.strip().upper().startswith('SET CONSTRAINTS ALL IMMEDIATE'):
            constraints.append(True)
            if stage == 'final_before_commit':
                elapsed[0] = 5.0
        return result

    def acknowledged_commit():
        original_commit()
        commits.append(True)
        if stage == 'after_acknowledged_commit':
            elapsed[0] = 5.0

    monkeypatch.setattr(connection, 'commit', acknowledged_commit)
    with connection.execute_wrapper(after_constraints), pytest.raises(DocumentServiceError) as denied:
        _call(api, actor, context=context)
    assert (denied.value.code, denied.value.status) == ('document_metadata_unavailable', 503)
    assert constraints == [True]
    assert commits == ([True] if retained else [])
    if retained:
        assert _committed_count(actor.user.pk) == 1
    else:
        assert not DocumentMetadataRateWindow.objects.filter(actor=actor.user).exists()


@pytest.mark.parametrize('change', ['epoch', 'first_profile', 'deactivation'])
@pytest.mark.parametrize('writer_first', [False, True])
def test_admission_and_identity_revocation_follow_observed_actor_lock_order(actor, clock, change, writer_first):
    api = import_module('apps.core.document_access')
    if change == 'epoch':
        IdentitySecurity.objects.create(user=actor.user, auth_epoch=0)
    # Preserve the original real session and epoch before either transaction.
    context = capture_document_context(actor.request, 'intent.list')
    held, attempting, release = Event(), Event(), Event()
    pids = {}

    def revoke():
        def run():
            pids['writer'] = _pid()
            with transaction.atomic():
                if not writer_first:
                    attempting.set()
                user = get_user_model().objects.select_for_update(no_key=True, of=('self',)).get(pk=actor.user.pk)
                state = IdentitySecurity.objects.select_for_update(of=('self',)).filter(user=user).first()
                if change == 'first_profile':
                    assert state is None
                    IdentitySecurity.objects.create(user=user, auth_epoch=1)
                elif change == 'epoch':
                    assert state is not None and state.auth_epoch == 0
                    state.auth_epoch = 1
                    state.save(update_fields=['auth_epoch'])
                else:
                    user.is_active = False
                    user.save(update_fields=['is_active'])
                if writer_first:
                    held.set()
                    assert release.wait(5), 'Revocation holder was not released'
            return 'revoked'
        return _independent(run)

    def admit():
        def run():
            pids['admission'] = _pid()
            def observe_stage(execute, sql, params, many, execution_context):
                upper = sql.upper()
                if writer_first and 'AUTH_USER' in upper and 'FOR NO KEY UPDATE' in upper:
                    # Preflight has already read the old committed authority.
                    attempting.set()
                result = execute(sql, params, many, execution_context)
                if not writer_first and upper.strip().startswith('SET CONSTRAINTS ALL IMMEDIATE'):
                    held.set()
                    assert release.wait(5), 'Admission holder was not released'
                return result
            with connection.execute_wrapper(observe_stage):
                if writer_first:
                    with pytest.raises(DocumentServiceError) as denied:
                        _call(api, actor, context=context)
                    assert (denied.value.code, denied.value.status) == ('not_authenticated', 401)
                    return 'denied'
                admission = _call(api, actor, context=context)
                assert admission._context is context
                api._validate_document_admission(admission, context, 'intent.list')
                return 'admitted'
        return _independent(run)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(revoke if writer_first else admit)
        try:
            assert held.wait(3), 'First transaction did not reach its actor-locked stage'
            if not writer_first and change == 'first_profile':
                assert not IdentitySecurity.objects.filter(user=actor.user).exists()
            second = pool.submit(admit if writer_first else revoke)
            assert attempting.wait(2), 'Second transaction did not attempt the actor lock'
            assert len({pids['writer'], pids['admission'], _pid()}) == 3
            _observe_wait(pids['admission' if writer_first else 'writer'],
                          pids['writer' if writer_first else 'admission'])
        finally:
            release.set()
        assert set((first.result(10), second.result(10))) == {'revoked', 'denied' if writer_first else 'admitted'}
    if writer_first:
        assert not DocumentMetadataRateWindow.objects.filter(actor=actor.user).exists()
    else:
        assert _committed_count(actor.user.pk) == 1
        # An already committed admission may precede revocation. A subsequent
        # attempt with the same original context must not consume another count.
        with pytest.raises(DocumentServiceError) as denied:
            _call(api, actor, context=context)
        assert (denied.value.code, denied.value.status) == ('not_authenticated', 401)
        assert _committed_count(actor.user.pk) == 1
    if change in ('epoch', 'first_profile'):
        assert IdentitySecurity.objects.get(user=actor.user).auth_epoch == 1
        assert IdentitySecurity.objects.filter(user=actor.user).count() == 1


def test_org_gated_grant_removal_commits_while_admission_waits_for_actor(actor, clock):
    api = import_module('apps.core.document_access')
    context = capture_document_context(actor.request, 'intent.list')
    held, attempting, release = Event(), Event(), Event()
    pids = {}

    def hold_actor():
        def run():
            pids['holder'] = _pid()
            with transaction.atomic():
                get_user_model().objects.select_for_update(no_key=True, of=('self',)).get(pk=actor.user.pk)
                held.set()
                assert release.wait(5), 'Actor holder was not released'
        return _independent(run)

    def admit():
        def run():
            pids['admission'] = _pid()
            def before_actor(execute, sql, params, many, execution_context):
                if 'AUTH_USER' in sql.upper() and 'FOR NO KEY UPDATE' in sql.upper():
                    attempting.set()
                return execute(sql, params, many, execution_context)
            with connection.execute_wrapper(before_actor), pytest.raises(DocumentServiceError) as denied:
                _call(api, actor, context=context)
            assert (denied.value.code, denied.value.status) == ('permission_denied', 403)
        return _independent(run)

    with ThreadPoolExecutor(max_workers=2) as pool:
        holder = pool.submit(hold_actor)
        try:
            assert held.wait(3)
            admission = pool.submit(admit)
            assert attempting.wait(2)
            assert len({pids['holder'], pids['admission'], _pid()}) == 3
            _observe_wait(pids['admission'], pids['holder'])
            # Follow the supported organisation gate for membership changes.
            # No Membership lock is invented in the admission transaction.
            with transaction.atomic():
                Organisation.objects.select_for_update(no_key=True, of=('self',)).get(pk=actor.branch.organisation_id)
                assert Membership.objects.filter(user=actor.user, role='reception').update(is_active=False) == 1
            assert not Membership.objects.filter(user=actor.user, is_active=True).exists()
        finally:
            # Grant removal has committed before the blocked admission resumes.
            release.set()
        holder.result(10)
        admission.result(10)
    assert not DocumentMetadataRateWindow.objects.filter(actor=actor.user).exists()
