"""RED-first B2a-L preparation/preflight tests; no SQLite admission success.

Actual PostgreSQL public precedence cases below never admit valid commands;
count/commit/locking evidence is owned by the separate concurrency/timeout files.
"""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from datetime import timedelta
from importlib import import_module
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.core import document_authority as authority
from apps.core.document_contracts import command_fingerprint, parse_create, parse_withdraw
from apps.core.models import Branch, IdentitySecurity, Membership, Organisation


pytestmark = pytest.mark.django_db(transaction=True)
PATIENT = 'a1111111-1111-4111-8111-111111111111'
DOCUMENT = 'b2222222-2222-4222-8222-222222222222'
KEY = 'c3333333-3333-4333-8333-333333333333'
CREATE = json.dumps({'category': 'registration', 'filename': 'synthetic-registration.png',
                     'media_type': 'image/png', 'size_bytes': 128, 'sha256': 'a' * 64}).encode()
WITHDRAW = b'{"expected_version":1,"reason":"Synthetic correction only"}'
ERRORS = {
    'not_authenticated': (401, 'Your session ended. Sign in again.'),
    'permission_denied': (403, 'You do not have access to this action.'),
    'network_denied': (403, 'Access is not available from this network. Contact your administrator.'),
    'document_metadata_unavailable': (503, 'Document details are unavailable. Try again later.'),
    'validation_error': (400, 'Check the highlighted details.'),
    'not_found': (404, 'This record is unavailable.'),
    'request_too_large': (413, 'This request is too large.'),
    'rate_limited': (429, 'Too many requests. Try again shortly.'),
}


def access():
    # Missing implementation is an executable RED, never a collection error.
    return import_module('apps.core.document_access')


def forbidden(*args, **kwargs):
    pytest.fail('Admission guard/preflight attempted a forbidden dependency')


@contextmanager
def error(code):
    with pytest.raises(authority.DocumentServiceError) as caught:
        yield
    value = caught.value
    assert (value.code, value.status, value.message, value.retry_after) == (code, *ERRORS[code], None)


def frozen_object(value):
    if type(value) is dict:
        return tuple((key, frozen_object(item)) for key, item in sorted(value.items()))
    assert type(value) in (str, int, type(None))
    return value


@pytest.fixture
def signed(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    user = get_user_model().objects.create_user(username='admission-synthetic', password='Synthetic-admission-82!')
    branch = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic admission'), name='Desk', code='ADM')
    Membership.objects.create(user=user, branch=branch, role='reception')
    request = RequestFactory().get('/', REMOTE_ADDR='198.51.100.26')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    row = Session.objects.get(session_key=request.session.session_key)
    assert row.get_decoded()['_auth_user_id'] == str(user.pk)
    assert row.get_decoded()['_auth_user_hash'] == user.get_session_auth_hash()
    return SimpleNamespace(request=request, user=user, branch=branch)


@pytest.mark.parametrize('operation', ['intent.list', 'intent.detail', 'intent.create', 'intent.withdraw'])
def test_private_preparation_exact_normalized_values_are_detached_and_frozen(operation):
    api = access()
    kwargs = {}
    if operation in ('intent.detail', 'intent.withdraw'):
        kwargs['document_id'] = DOCUMENT
    if operation in ('intent.create', 'intent.withdraw'):
        kwargs.update(key=KEY, body=CREATE if operation == 'intent.create' else WITHDRAW)
    pairs = [('limit', '2')]
    if operation == 'intent.list':
        kwargs['query_pairs'] = pairs
    with connection.execute_wrapper(forbidden):
        result = api._prepare_document_command(operation, PATIENT, **kwargs)
    assert result.operation == operation and result.patient_id == PATIENT
    assert result.document_id == kwargs.get('document_id') and result.key == kwargs.get('key')
    assert not hasattr(result, '_mint') and not hasattr(result, '_context')
    if operation in ('intent.create', 'intent.withdraw'):
        payload = parse_create(CREATE) if operation == 'intent.create' else parse_withdraw(WITHDRAW)
        assert result.payload == frozen_object(payload)
        assert result.fingerprint == command_fingerprint(operation, PATIENT, kwargs.get('document_id'), payload)
        assert result.query is None
    elif operation == 'intent.list':
        pairs.clear()
        assert result.query == (('category', 'registration'), ('cursor', None), ('limit', 2))
        assert result.payload is None and result.fingerprint is None
    else:
        assert result.payload is result.query is result.fingerprint is None
    with pytest.raises(FrozenInstanceError):
        result.patient_id = DOCUMENT
    assert all(secret not in repr(result) for secret in (PATIENT, DOCUMENT, KEY, 'synthetic-registration.png', 'a' * 64))


@pytest.mark.parametrize('operation,patient,kwargs,code', [
    ('unknown', PATIENT, {}, 'validation_error'),
    ('intent.list', 'malformed', {}, 'not_found'),
    ('intent.detail', PATIENT, {'document_id': 'malformed'}, 'not_found'),
    ('intent.create', PATIENT, {'key': None, 'body': CREATE}, 'validation_error'),
    ('intent.create', PATIENT, {'key': KEY, 'body': b'{'}, 'validation_error'),
    ('intent.create', PATIENT, {'key': KEY, 'body': b'x' * 4097}, 'request_too_large'),
    ('intent.list', PATIENT, {'body': b'{}'}, 'validation_error'),
    ('intent.detail', PATIENT, {'document_id': DOCUMENT, 'key': KEY}, 'validation_error'),
    ('intent.create', PATIENT, {'document_id': DOCUMENT, 'key': KEY, 'body': CREATE}, 'validation_error'),
    ('intent.list', PATIENT, {'query_pairs': [('limit', '2'), ('limit', '3')]}, 'validation_error'),
])
def test_private_preparation_rejects_exact_operation_inputs_without_io(operation, patient, kwargs, code):
    api = access()
    with connection.execute_wrapper(forbidden), error(code):
        api._prepare_document_command(operation, patient, **kwargs)


@pytest.mark.parametrize('code', ['validation_error', 'not_found', 'request_too_large'])
def test_new_fixed_nonlimiter_errors_are_exact(code):
    value = authority.DocumentServiceError(code, *ERRORS[code])
    assert (value.code, value.status, value.message, value.retry_after) == (code, *ERRORS[code], None)


def test_original_four_error_tuples_and_arbitrary_detail_rejection_remain_unchanged():
    for code in ('not_authenticated', 'permission_denied', 'network_denied', 'document_metadata_unavailable'):
        value = authority.DocumentServiceError(code, *ERRORS[code])
        assert value.retry_after is None
        with pytest.raises(ValueError):
            authority.DocumentServiceError(code, *ERRORS[code], 1)
    for args in [('raw-synthetic-secret', 400, 'raw-synthetic-secret'),
                 ('validation_error', True, ERRORS['validation_error'][1]),
                 ('validation_error', 400, 'raw-synthetic-secret')]:
        with pytest.raises(ValueError) as caught:
            authority.DocumentServiceError(*args)
        assert 'raw-synthetic-secret' not in str(caught.value)


@pytest.mark.parametrize('retry', [1, 60])
def test_rate_limited_exact_retry_bounds_are_accepted(retry):
    value = authority.DocumentServiceError('rate_limited', *ERRORS['rate_limited'], retry)
    assert (value.code, value.status, value.message, value.retry_after) == ('rate_limited', *ERRORS['rate_limited'], retry)


@pytest.mark.parametrize('retry', [None, True, 0, 61])
def test_rate_limited_retry_must_be_actual_integer_in_range(retry):
    with pytest.raises(ValueError):
        authority.DocumentServiceError('rate_limited', *ERRORS['rate_limited'], retry)


@pytest.mark.parametrize('flag,accepted', [(None, True), ('true', True), ('invalid-synthetic-value', False)])
def test_metadata_flag_default_and_startup_environment_validation(flag, accepted):
    env = os.environ.copy()
    env.update(HMS_ENV='development', HMS_DB_ENGINE='sqlite')
    env.pop('HMS_DOCUMENT_METADATA_ENABLED', None)
    if flag is not None:
        env['HMS_DOCUMENT_METADATA_ENABLED'] = flag
    expected = 'True' if flag == 'true' else 'False'
    script = 'from hms import settings; assert settings.HMS_DOCUMENT_METADATA_ENABLED is ' + expected
    result = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True, timeout=15)
    if accepted:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
        assert 'ImproperlyConfigured' in result.stderr and 'HMS_DOCUMENT_METADATA_ENABLED' in result.stderr


def test_preflight_preserves_original_context_start_and_has_no_writes_or_network_reads(signed, monkeypatch):
    context = authority.capture_document_context(signed.request, 'intent.list')
    before = list(Session.objects.values())
    with monkeypatch.context() as patch:
        for name in ('load', 'save', 'create', 'cycle_key', 'flush'):
            patch.setattr(SessionStore, name, forbidden)
        patch.setattr(authority, 'capture_document_context', forbidden)
        with CaptureQueriesContext(connection) as queries:
            sample = authority.preflight_document_authority(context, 'intent.list')
    assert sample._context is context and sample.actor_id == context.actor_id
    assert sample.captured_epoch == context.captured_epoch and sample.operation == context.operation
    assert sample.sampled_at >= context.operation_started_at
    assert context.monotonic_started_at == sample._context.monotonic_started_at
    assert sample.eligible_branches == frozenset({signed.branch.pk})
    assert not IdentitySecurity.objects.exists() and list(Session.objects.values()) == before
    for query in queries:
        sql = query['sql'].lower()
        assert sql.lstrip().startswith('select') and 'for update' not in sql and 'for no key update' not in sql
        assert not any(table in sql for table in ('core_network', 'core_patient', 'core_document', 'core_auditevent'))


def test_preflight_rechecks_expiry_after_membership_materialisation(signed, monkeypatch):
    context = authority.capture_document_context(signed.request, 'intent.list')
    expires = timezone.now() + timedelta(seconds=60)
    Session.objects.filter(session_key=signed.request.session.session_key).update(expire_date=expires)
    clock = [timezone.now()]
    monkeypatch.setattr(authority.timezone, 'now', lambda: clock[0])
    def cross_expiry(execute, sql, params, many, execution_context):
        result = execute(sql, params, many, execution_context)
        if 'core_membership' in sql.lower():
            clock[0] = expires
        return result
    with connection.execute_wrapper(cross_expiry), error('not_authenticated'):
        authority.preflight_document_authority(context, 'intent.list')


@pytest.mark.parametrize('mode', ['atomic', 'manual'])
def test_preflight_ambient_misuse_rejected_before_queries(signed, mode):
    context = authority.capture_document_context(signed.request, 'intent.list')
    if mode == 'atomic':
        with transaction.atomic(), connection.execute_wrapper(forbidden), error('document_metadata_unavailable'):
            authority.preflight_document_authority(context, 'intent.list')
    else:
        transaction.set_autocommit(False)
        try:
            with connection.execute_wrapper(forbidden), error('document_metadata_unavailable'):
                authority.preflight_document_authority(context, 'intent.list')
        finally:
            transaction.set_autocommit(True)


@pytest.mark.parametrize('configuration', ['extra_alias', 'router'])
def test_public_admission_rejects_unsupported_database_configuration_before_connection(signed, settings, monkeypatch, configuration):
    api = access()
    context = authority.capture_document_context(signed.request, 'intent.list')
    if configuration == 'extra_alias':
        monkeypatch.setattr(settings, 'DATABASES', {**settings.DATABASES, 'unsupported': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}})
    else:
        monkeypatch.setattr(settings, 'DATABASE_ROUTERS', ['synthetic.unsupported.Router'])
    monkeypatch.setattr(connection, 'ensure_connection', forbidden)
    with connection.execute_wrapper(forbidden), error('document_metadata_unavailable'):
        api.admit_document_command(context, PATIENT)


def test_public_admission_has_no_sqlite_success_or_domain_reads(signed):
    if connection.vendor != 'sqlite':
        pytest.skip('SQLite dependency-negative case; real admission succeeds only on PostgreSQL>=17.')
    api = access()
    context = authority.capture_document_context(signed.request, 'intent.list')
    with connection.execute_wrapper(forbidden), error('document_metadata_unavailable'):
        api.admit_document_command(context, PATIENT)


@pytest.mark.parametrize('mode', ['atomic', 'manual'])
def test_public_admission_ambient_misuse_rejected_before_queries(signed, mode):
    api = access()
    context = authority.capture_document_context(signed.request, 'intent.list')
    if mode == 'atomic':
        with transaction.atomic(), connection.execute_wrapper(forbidden), error('document_metadata_unavailable'):
            api.admit_document_command(context, PATIENT)
    else:
        transaction.set_autocommit(False)
        try:
            with connection.execute_wrapper(forbidden), error('document_metadata_unavailable'):
                api.admit_document_command(context, PATIENT)
        finally:
            transaction.set_autocommit(True)


@pytest.mark.parametrize('damage,code', [('session', 'not_authenticated'), ('membership', 'permission_denied'),
                                       ('path', 'not_found'), ('key', 'validation_error'),
                                       ('body', 'request_too_large')])
def test_actual_pg_public_precedence_before_allowance_and_target_reads(signed, settings, damage, code):
    if connection.vendor != 'postgresql':
        pytest.skip('Requires actual PostgreSQL for public admission precedence; no permissive SQLite service fallback.')
    api = access()
    settings.HMS_DOCUMENT_METADATA_ENABLED = True
    context = authority.capture_document_context(signed.request, 'intent.create')
    patient, key, body = 'malformed', None, b'x' * 4097
    if damage == 'session':
        Session.objects.filter(session_key=signed.request.session.session_key).delete()
    elif damage == 'membership':
        Membership.objects.filter(user=signed.user).update(is_active=False)
    elif damage == 'key':
        patient = PATIENT
    elif damage == 'body':
        patient, key = PATIENT, KEY
    with CaptureQueriesContext(connection) as queries, error(code):
        api.admit_document_command(context, patient, key=key, body=body)
    assert all(query['sql'].lstrip().upper().startswith('SELECT') for query in queries)
    assert not any(table in query['sql'].lower() for query in queries
                   for table in ('core_patient', 'core_document', 'core_network'))


def test_actual_pg_older_server_dependency_rejected_without_domain_reads(signed, monkeypatch):
    if connection.vendor != 'postgresql':
        pytest.skip('Requires actual PostgreSQL backend to exercise its version ceiling independently of SQLite rejection.')
    api = access()
    context = authority.capture_document_context(signed.request, 'intent.list')
    monkeypatch.setattr(connection, 'pg_version', 160000)
    with connection.execute_wrapper(forbidden), error('document_metadata_unavailable'):
        api.admit_document_command(context, PATIENT)
