"""Portable RED-first acceptance for the frozen read-only B2a-A boundary.

Transaction=True is intentional: capture must execute outside an ambient atomic
block. Actual PostgreSQL lock/visibility evidence lives in the separate PG file.
"""
import copy
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.utils.functional import empty

from apps.core.models import Branch, IdentitySecurity, Membership, Organisation
from apps.core.network_models import NetworkPolicyState
from apps.core.network_snapshot import NetworkSnapshot
from apps.security.network_policy import policy_digest

pytestmark = pytest.mark.django_db(transaction=True)
OPS = ('intent.list', 'intent.detail', 'intent.create', 'intent.withdraw')
ERRORS = {
    'not_authenticated': (401, 'Your session ended. Sign in again.'),
    'permission_denied': (403, 'You do not have access to this action.'),
    'network_denied': (403, 'Access is not available from this network. Contact your administrator.'),
    'document_metadata_unavailable': (503, 'Document details are unavailable. Try again later.'),
}
ALLOW = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}


def authority():
    # Import here, never during collection: missing production is literal RED.
    return import_module('apps.core.document_authority')


def forbidden(*args, **kwargs):
    pytest.fail('Read-only authority attempted a forbidden dependency')


@contextmanager
def error(api, code):
    with pytest.raises(api.DocumentServiceError) as caught:
        yield
    value = caught.value
    assert (value.code, value.status, value.message, value.retry_after) == (
        code, *ERRORS[code], None)


@contextmanager
def read_guard(monkeypatch, *, network=False):
    """No session/framework repair, business access or hidden writes, even on denial."""
    with monkeypatch.context() as patch:
        for name in ('load', 'save', 'create', 'cycle_key', 'flush'):
            patch.setattr(SessionStore, name, forbidden)
        patch.setattr('django.contrib.auth.get_user', forbidden)
        patch.setattr('apps.core.identity_security.session_hash', forbidden)
        patch.setattr('apps.core.identity_security.lock_identity', forbidden)
        with CaptureQueriesContext(connection) as queries:
            yield
        for query in queries:
            sql = query['sql'].lower()
            assert not sql.lstrip().startswith(('insert ', 'update ', 'delete ')), sql
            assert 'for update' not in sql and 'for no key update' not in sql, sql
            for table in ('core_patient', 'documentuploadintent', 'documentmutationreceipt',
                          'documentevent', 'documentmetadataratewindow', 'core_auditevent',
                          'core_documentintentreceipt', 'core_documentaccessevent'):
                assert table not in sql, sql
            if not network:
                assert 'core_network' not in sql, sql


@pytest.fixture
def signed(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    user = get_user_model().objects.create_user(username='authority-synthetic', password='Synthetic-session-72!')
    branch = Branch.objects.create(organisation=Organisation.objects.create(name='Synthetic authority'), name='Desk', code='AUTH')
    Membership.objects.create(user=user, branch=branch, role='reception')
    request = RequestFactory().get('/', REMOTE_ADDR='198.51.100.24')
    request.session = SessionStore()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    request.user = user
    # Prove the fixture is a genuine signed persisted Django login.
    row = Session.objects.get(session_key=request.session.session_key)
    assert row.get_decoded()['_auth_user_id'] == str(user.pk)
    assert row.get_decoded()['_auth_user_hash'] == user.get_session_auth_hash()
    NetworkPolicyState.objects.update_or_create(pk=1, defaults={
        'confirmed_policy': ALLOW, 'confirmed_policy_digest': policy_digest(ALLOW), 'pending_change': None,
    })
    return SimpleNamespace(request=request, user=user, branch=branch)


def persist(fixture, mutate):
    row = Session.objects.get(session_key=fixture.request.session.session_key)
    data = row.get_decoded()
    mutate(data)
    row.session_data = fixture.request.session.encode(data)
    row.save(update_fields=['session_data'])


def samples(api, fixture, operation='intent.list'):
    context = api.capture_document_context(fixture.request, operation)
    with transaction.atomic():
        # Portable evidence checks transaction presence only; PG tests acquire locks.
        auth = api.sample_document_authority(context, operation)
    network = api.sample_document_network(context, timezone.now())
    return context, auth, network


@pytest.mark.parametrize('operation', OPS)
def test_genuine_session_capture_is_read_only(signed, monkeypatch, operation):
    api = authority()
    before = list(Session.objects.values())
    with read_guard(monkeypatch):
        context = api.capture_document_context(signed.request, operation)
        with transaction.atomic():
            sample = api.sample_document_authority(context, operation)
    assert sample.eligible_branches == frozenset({signed.branch.pk})
    assert context.actor_id == sample.actor_id == signed.user.pk
    assert context.captured_epoch == sample.captured_epoch == 0
    assert context.operation == sample.operation == operation
    assert sample.sampled_at >= context.operation_started_at
    assert not IdentitySecurity.objects.exists()
    assert list(Session.objects.values()) == before


@pytest.mark.parametrize('mode', ['atomic', 'manual'])
def test_capture_rejects_ambient_before_reads(signed, mode):
    api = authority()
    with CaptureQueriesContext(connection) as queries:
        if mode == 'atomic':
            with transaction.atomic(), error(api, 'document_metadata_unavailable'):
                api.capture_document_context(signed.request, 'intent.list')
        else:
            transaction.set_autocommit(False)
            try:
                with error(api, 'document_metadata_unavailable'):
                    api.capture_document_context(signed.request, 'intent.list')
            finally:
                transaction.set_autocommit(True)
    assert not any(q['sql'].lstrip().upper().startswith('SELECT') for q in queries)


@pytest.mark.parametrize('kind', ['unresolved', 'missing_cache', 'nondict_cache', 'subclass'])
def test_unresolved_actor_and_missing_cache_never_evaluate_or_load(signed, monkeypatch, kind):
    api = authority()
    if kind == 'unresolved':
        signed.request.user = SimpleLazyObject(forbidden)
    elif kind == 'missing_cache':
        del signed.request.session.__dict__['_session_cache']
    elif kind == 'nondict_cache':
        signed.request.session.__dict__['_session_cache'] = []
    else:
        class HostileStore(SessionStore):
            @property
            def session_key(self):
                forbidden()
        signed.request.session = HostileStore()
    with read_guard(monkeypatch), error(api, 'not_authenticated'):
        api.capture_document_context(signed.request, 'intent.list')


def test_resolved_lazy_actor_is_accepted(signed):
    api = authority()
    actor = SimpleLazyObject(forbidden)
    actor._wrapped = signed.user
    signed.request.user = actor
    assert api.capture_document_context(signed.request, 'intent.list').actor_id == signed.user.pk


def test_unresolved_lazy_actor_subclass_never_evaluates(signed, monkeypatch):
    api = authority()
    class LazyActor(SimpleLazyObject):
        pass
    actor = LazyActor(forbidden)
    signed.request.user = actor
    with read_guard(monkeypatch), error(api, 'not_authenticated'):
        api.capture_document_context(signed.request, 'intent.list')
    assert actor._wrapped is empty


@pytest.mark.parametrize('setting,value', [
    ('SESSION_ENGINE', 'django.contrib.sessions.backends.signed_cookies'),
    ('AUTHENTICATION_BACKENDS', ['django.contrib.auth.backends.AllowAllUsersModelBackend']),
])
def test_unsupported_configuration_fails_closed(signed, settings, monkeypatch, setting, value):
    api = authority()
    setattr(settings, setting, value)
    with read_guard(monkeypatch), error(api, 'document_metadata_unavailable'):
        api.capture_document_context(signed.request, 'intent.list')


@pytest.mark.parametrize('location,value', [
    ('live', None), ('persisted', None), ('live', True), ('persisted', True),
    ('live', -1), ('persisted', -1), ('live', '0'), ('persisted', '0'),
])
def test_explicit_null_and_noninteger_epochs_are_invalid(signed, monkeypatch, location, value):
    api = authority()
    if location == 'live':
        signed.request.session._session_cache['auth_epoch'] = value
    else:
        persist(signed, lambda data: data.update(auth_epoch=value))
    with read_guard(monkeypatch), error(api, 'not_authenticated'):
        api.capture_document_context(signed.request, 'intent.list')


@pytest.mark.parametrize('location,authoritative,allowed', [
    ('both', 0, True), ('both', 1, False), ('live', 0, False), ('persisted', 0, False),
])
def test_legacy_missing_epoch_requires_authoritative_zero(signed, location, authoritative, allowed):
    api = authority()
    if location in ('both', 'live'):
        del signed.request.session._session_cache['auth_epoch']
    if location in ('both', 'persisted'):
        persist(signed, lambda data: data.pop('auth_epoch'))
    IdentitySecurity.objects.create(user=signed.user, auth_epoch=authoritative)
    if allowed:
        assert api.capture_document_context(signed.request, 'intent.list').captured_epoch is None
    else:
        with error(api, 'not_authenticated'):
            api.capture_document_context(signed.request, 'intent.list')


@pytest.mark.parametrize('damage', ['deleted', 'expired', 'corrupt', 'partial', 'backend', 'hash', 'inactive', 'epoch'])
def test_session_and_epoch_failures(signed, monkeypatch, damage):
    api = authority()
    rows = Session.objects.filter(session_key=signed.request.session.session_key)
    if damage == 'deleted':
        rows.delete()
    elif damage == 'expired':
        rows.update(expire_date=timezone.now() - timedelta(seconds=1))
    elif damage == 'corrupt':
        rows.update(session_data='synthetic-corrupt-signed-payload')
    elif damage in ('partial', 'backend', 'hash'):
        def corrupt(data):
            if damage == 'partial':
                data.pop('_auth_user_hash')
            else:
                data['_auth_user_backend' if damage == 'backend' else '_auth_user_hash'] = 'invalid'
        persist(signed, corrupt)
    elif damage == 'inactive':
        get_user_model().objects.filter(pk=signed.user.pk).update(is_active=False)
    else:
        IdentitySecurity.objects.create(user=signed.user, auth_epoch=1)
    with read_guard(monkeypatch), error(api, 'not_authenticated'):
        api.capture_document_context(signed.request, 'intent.list')


@pytest.mark.parametrize('fallback', ['signing', 'auth_hash'])
def test_fallback_hash_acceptance_without_rotation(signed, settings, monkeypatch, fallback):
    api = authority()
    old_secret = settings.SECRET_KEY
    if fallback == 'auth_hash':
        settings.SECRET_KEY = 'new-synthetic-secret-authority'
        settings.SECRET_KEY_FALLBACKS = [old_secret]
        # Resign old authentication hash under the new signing key.
        row = Session.objects.get(session_key=signed.request.session.session_key)
        data = row.get_decoded()
        row.session_data = signed.request.session.encode(data)
        row.save(update_fields=['session_data'])
    else:
        settings.SECRET_KEY = 'new-synthetic-secret-authority'
        settings.SECRET_KEY_FALLBACKS = [old_secret]
    before = list(Session.objects.values())
    with read_guard(monkeypatch):
        assert api.capture_document_context(signed.request, 'intent.list').actor_id == signed.user.pk
    assert list(Session.objects.values()) == before


@pytest.mark.parametrize('binding', ['actor', 'key', 'cache', 'flush'])
def test_live_binding_changes_invalidate_materialisation(signed, binding):
    api = authority()
    context = api.capture_document_context(signed.request, 'intent.list')
    if binding == 'actor':
        signed.request.user = get_user_model().objects.create_user(username='other-synthetic')
    elif binding == 'key':
        signed.request.session = SessionStore('a' * 32)
        signed.request.session._session_cache = {'auth_epoch': 0}
    elif binding == 'cache':
        signed.request.session._session_cache['auth_epoch'] = 1
    else:
        signed.request.session.flush()
    with transaction.atomic(), error(api, 'not_authenticated'):
        api.sample_document_authority(context, 'intent.list')


@pytest.mark.parametrize('target', ['context', 'authority', 'network'])
@pytest.mark.parametrize('clone', ['copy', 'replace'])
def test_foreign_mint_and_sample_rejected(signed, target, clone):
    api = authority()
    context, auth, network = samples(api, signed)
    values = {'context': context, 'authority': auth, 'network': network}
    value = values[target]
    duplicate = copy.copy(value) if clone == 'copy' else replace(value)
    values[target] = duplicate
    with error(api, 'document_metadata_unavailable'):
        api.validate_document_selection(values['context'], values['authority'], values['network'], timezone.now())


def test_direct_constructor_and_same_actor_foreign_context_are_not_proof(signed):
    api = authority()
    context, auth, network = samples(api, signed)
    forged = type(context)(**{f.name: getattr(context, f.name) for f in fields(context)})
    for other in (forged, api.capture_document_context(signed.request, 'intent.list')):
        with error(api, 'document_metadata_unavailable'):
            api.validate_document_selection(other, auth, network, timezone.now())


def test_policy_sample_detached_and_repr_safe(signed, monkeypatch):
    api = authority()
    context, auth, network = samples(api, signed)
    for value in (context, auth, network):
        with pytest.raises(FrozenInstanceError):
            value._mint = object()
    assert type(network.confirmed_policy) is tuple
    assert all(type(part) is tuple for part in network.confirmed_policy[1:])
    hidden = (signed.request.session.session_key, signed.user.get_session_auth_hash(), context.session_digest,
              context.remote_addr, context.verified_ip, context.environment_digest)
    assert all(secret not in repr((context, auth, network)) for secret in hidden)
    assert type(auth.eligible_branches) is frozenset
    # Final validation must use detached samples even after the live request changes.
    signed.request.session = None
    signed.request.user = None
    with monkeypatch.context() as patch:
        patch.setattr('django.utils.timezone.now', forbidden)
        patch.setattr('time.monotonic', forbidden)
        with connection.execute_wrapper(lambda *args: forbidden()):
            api.validate_document_selection(context, auth, network, max(auth.sampled_at, network.sampled_at))


@pytest.mark.parametrize('instant,code', [('before', None), ('equal', 'not_authenticated'), ('after', 'not_authenticated'), ('backward', 'document_metadata_unavailable'), ('naive', 'document_metadata_unavailable')])
def test_selection_expiry_equalities_and_invalid_time(signed, instant, code):
    api = authority()
    context, auth, network = samples(api, signed)
    selected = {'before': auth.expires_at-timedelta(microseconds=1), 'equal': auth.expires_at,
                'after': auth.expires_at+timedelta(microseconds=1),
                'backward': context.operation_started_at-timedelta(microseconds=1),
                'naive': timezone.now().replace(tzinfo=None)}[instant]
    if code:
        with error(api, code):
            api.validate_document_selection(context, auth, network, selected)
    else:
        api.validate_document_selection(context, auth, network, selected)


@pytest.mark.parametrize('offset,code', [(-1, 'network_denied'), (0, None), (1, None)])
@pytest.mark.parametrize('inverse', [False, True])
def test_selection_rollback_equalities_ignore_preread_effective_policy(signed, monkeypatch, offset, code, inverse):
    api = authority()
    context, auth, _ = samples(api, signed)
    now = timezone.now()
    rollback = now + timedelta(seconds=5)
    denied = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['198.51.100.24/32']}
    confirmed, candidate = (denied, copy.deepcopy(ALLOW)) if inverse else (copy.deepcopy(ALLOW), denied)
    if inverse:
        code = None if offset < 0 else 'network_denied'
    graph = NetworkSnapshot(2, uuid4(), confirmed, candidate, uuid4(), 'expired_unreconciled',
                            candidate, now-timedelta(seconds=295), rollback, 2)
    monkeypatch.setattr(api, 'load_network_snapshot', lambda when: graph)
    network = api.sample_document_network(context, now)
    denied['blocklist'].clear()  # No retained mutable loader graph.
    selected = rollback + timedelta(microseconds=offset)
    if code:
        with error(api, code):
            api.validate_document_selection(context, auth, network, selected)
    else:
        api.validate_document_selection(context, auth, network, selected)


@pytest.mark.parametrize('change,code', [('drift', 'document_metadata_unavailable'), ('corrupt', 'document_metadata_unavailable'), ('spoof', 'network_denied')])
def test_network_environment_drift_corruption_and_untrusted_header(signed, settings, change, code):
    api = authority()
    if change == 'spoof':
        settings.HMS_IP_BLOCKLIST = ['198.51.100.24/32']
        signed.request.META['HTTP_X_FORWARDED_FOR'] = '127.0.0.1'
        with error(api, code):
            api.capture_document_context(signed.request, 'intent.list')
        return
    context = api.capture_document_context(signed.request, 'intent.list')
    if change == 'drift':
        settings.HMS_TRUSTED_PROXIES = ['192.0.2.0/24']
    else:
        NetworkPolicyState.objects.update(confirmed_policy_digest='0' * 64)
    with error(api, code):
        api.sample_document_network(context, timezone.now())


def test_sampler_requires_transaction_and_known_operation(signed):
    api = authority()
    context = api.capture_document_context(signed.request, 'intent.list')
    with error(api, 'document_metadata_unavailable'):
        api.sample_document_authority(context, 'intent.list')
    with transaction.atomic(), error(api, 'document_metadata_unavailable'):
        api.sample_document_authority(context, 'intent.withdraw')
    with error(api, 'document_metadata_unavailable'):
        api.capture_document_context(signed.request, 'arbitrary.operation')


def test_fixed_error_constructor_refuses_arbitrary_detail():
    api = authority()
    for code, (status, message) in ERRORS.items():
        value = api.DocumentServiceError(code, status, message)
        assert (value.code, value.status, value.message, value.retry_after) == (code, status, message, None)
    for args in [('raw-secret', 503, 'raw-secret'), ('not_authenticated', 503, ERRORS['not_authenticated'][1]),
                 ('not_authenticated', 401, 'raw-secret'), ('not_authenticated', 401, ERRORS['not_authenticated'][1], 2)]:
        with pytest.raises((ValueError, TypeError)) as caught:
            api.DocumentServiceError(*args)
        assert 'raw-secret' not in str(caught.value)


@pytest.mark.parametrize('operation', OPS)
@pytest.mark.parametrize('role', ['doctor', 'nurse', 'master_admin'])
def test_authority_rejects_nonreception_roles(signed, monkeypatch, operation, role):
    api = authority()
    Membership.objects.filter(user=signed.user).update(role=role)
    with read_guard(monkeypatch), error(api, 'permission_denied'):
        api.capture_document_context(signed.request, operation)


@pytest.mark.parametrize('operation', OPS)
def test_authority_mixed_roles_scope_and_revocation(signed, monkeypatch, operation):
    api = authority()
    branch_a = Branch.objects.create(organisation=signed.branch.organisation, name='Clinical', code='CLIN')
    Membership.objects.create(user=signed.user, branch=branch_a, role='doctor')
    context = api.capture_document_context(signed.request, operation)
    with read_guard(monkeypatch), transaction.atomic():
        sample = api.sample_document_authority(context, operation)
    assert sample.eligible_branches == frozenset({signed.branch.pk})
    Membership.objects.filter(user=signed.user, role='reception').update(is_active=False)
    with read_guard(monkeypatch), transaction.atomic(), error(api, 'permission_denied'):
        api.sample_document_authority(context, operation)


@pytest.mark.parametrize('operation', OPS)
@pytest.mark.parametrize('same_branch', [False, True])
def test_authority_intersects_each_required_permission_branch(signed, monkeypatch, operation, same_branch):
    api = authority()
    from apps.core.authorization import ROLE_PERMISSIONS
    other = signed.branch if same_branch else Branch.objects.create(
        organisation=signed.branch.organisation, name='Other desk', code='OTHER')
    # Neither role alone has the complete conjunction; a global union is unsafe.
    monkeypatch.setitem(ROLE_PERMISSIONS, 'reception', {'patients.read', 'patients.write'})
    monkeypatch.setitem(ROLE_PERMISSIONS, 'doctor', {'documents.registration.read', 'documents.registration.write'})
    Membership.objects.create(user=signed.user, branch=other, role='doctor')
    if not same_branch:
        with read_guard(monkeypatch), error(api, 'permission_denied'):
            api.capture_document_context(signed.request, operation)
    else:
        with read_guard(monkeypatch):
            context = api.capture_document_context(signed.request, operation)
            with transaction.atomic():
                sample = api.sample_document_authority(context, operation)
        assert sample.eligible_branches == frozenset({signed.branch.pk})


@pytest.mark.parametrize('operation', OPS)
@pytest.mark.parametrize('missing', ['patients.write', 'documents.registration.write'])
def test_write_permissions_must_share_the_read_branch(signed, monkeypatch, operation, missing):
    api = authority()
    from apps.core.authorization import ROLE_PERMISSIONS
    required = {'patients.read', 'documents.registration.read', 'patients.write', 'documents.registration.write'}
    monkeypatch.setitem(ROLE_PERMISSIONS, 'reception', required - {missing})
    monkeypatch.setitem(ROLE_PERMISSIONS, 'doctor', {missing})
    other = Branch.objects.create(organisation=signed.branch.organisation, name='Write desk', code='WRITE')
    Membership.objects.create(user=signed.user, branch=other, role='doctor')
    if operation in ('intent.create', 'intent.withdraw'):
        with read_guard(monkeypatch), error(api, 'permission_denied'):
            api.capture_document_context(signed.request, operation)
    else:
        with read_guard(monkeypatch):
            context = api.capture_document_context(signed.request, operation)
            with transaction.atomic():
                sample = api.sample_document_authority(context, operation)
        assert sample.eligible_branches == frozenset({signed.branch.pk})


@pytest.mark.parametrize('sampler', ['authority', 'network'])
@pytest.mark.parametrize('clone', ['copy', 'replace', 'constructor'])
def test_each_sampler_rejects_unissued_context(signed, sampler, clone):
    api = authority()
    context = api.capture_document_context(signed.request, 'intent.list')
    forged = (copy.copy(context) if clone == 'copy' else replace(context) if clone == 'replace'
              else type(context)(**{f.name: getattr(context, f.name) for f in fields(context)}))
    with transaction.atomic():
        with connection.execute_wrapper(lambda *args: forbidden()), error(api, 'document_metadata_unavailable'):
            if sampler == 'authority':
                api.sample_document_authority(forged, 'intent.list')
            else:
                api.sample_document_network(forged, timezone.now())


@pytest.mark.parametrize('case', ['allowed', 'denied', 'corrupt'])
def test_network_sampling_is_read_only_even_on_denial(signed, monkeypatch, case):
    api = authority()
    context = api.capture_document_context(signed.request, 'intent.list')
    if case == 'corrupt':
        NetworkPolicyState.objects.update(confirmed_policy_digest='0' * 64)
    elif case == 'denied':
        denied = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['198.51.100.24/32']}
        NetworkPolicyState.objects.update(confirmed_policy=denied, confirmed_policy_digest=policy_digest(denied))
    before = list(NetworkPolicyState.objects.values())
    with read_guard(monkeypatch, network=True):
        if case == 'corrupt':
            with error(api, 'document_metadata_unavailable'):
                api.sample_document_network(context, timezone.now())
        else:
            network = api.sample_document_network(context, timezone.now())
            with transaction.atomic():
                auth = api.sample_document_authority(context, 'intent.list')
            if case == 'denied':
                with error(api, 'network_denied'):
                    api.validate_document_selection(context, auth, network, max(auth.sampled_at, network.sampled_at))
            else:
                api.validate_document_selection(context, auth, network, max(auth.sampled_at, network.sampled_at))
    assert list(NetworkPolicyState.objects.values()) == before
