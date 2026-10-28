"""Authority sampling under actual PG locks; these are not admission tests.

The test caller supplies User NO KEY UPDATE -> existing IdentitySecurity locks.
Removing fresh epoch reads, creating a missing profile during sampling, or
silently widening the sampler's lock scope must break these tests.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic

import pytest
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.db import close_old_connections, connection, transaction
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from apps.core.models import Branch, IdentitySecurity, Membership, Organisation


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def authority_actor(settings):
    if connection.vendor != 'postgresql':
        pytest.skip('Requires actual PostgreSQL separate connections, row locks and pg_blocking_pids; SQLite cannot prove authority ordering.')
    settings.AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.HMS_IP_ALLOWLIST_ONLY = False
    settings.HMS_IP_ALLOWLIST = []
    settings.HMS_IP_BLOCKLIST = []
    settings.HMS_TRUSTED_PROXIES = []
    user = get_user_model().objects.create_user(username='synthetic-document-authority-race', password='Synthetic-authority-only-287!')
    org = Organisation.objects.create(name='Synthetic document authority')
    branch = Branch.objects.create(organisation=org, name='Registration', code='DOC-AUTH')
    Membership.objects.create(user=user, branch=branch, role='reception')
    # Installed login creates the genuine signed DB session and concrete actor.
    # No force_authenticate / fabricated session dictionary is authentication proof.
    request = RequestFactory().get('/synthetic-document-authority', REMOTE_ADDR='127.0.0.1')
    request.session = SessionStore()
    request.user = AnonymousUser()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_epoch'] = 0
    request.session.save()
    assert request.user is user
    assert not connection.in_atomic_block
    return user, branch, request


def _pid():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_backend_pid()')
        return cursor.fetchone()[0]


def _observe_wait(waiter, blocker):
    expires = monotonic() + 10
    while monotonic() < expires:
        with connection.cursor() as cursor:
            cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [blocker, waiter])
            if cursor.fetchone()[0]:
                return
    pytest.fail('Expected actual PostgreSQL actor lock wait was not observed')


def _lock_actor_then_existing_identity(actor_id):
    actor = get_user_model().objects.select_for_update(no_key=True, of=('self',)).get(pk=actor_id)
    return IdentitySecurity.objects.select_for_update(of=('self',)).filter(user=actor).first()


def _change_epoch(actor_id, create):
    state = _lock_actor_then_existing_identity(actor_id)
    if create:
        assert state is None
        IdentitySecurity.objects.create(user_id=actor_id, auth_epoch=1)
    else:
        assert state is not None
        state.auth_epoch = 1
        state.save(update_fields=['auth_epoch'])


def _assert_sampler_scope(queries):
    # Only the explicit caller precondition above may acquire row locks.
    assert not any('FOR UPDATE' in row['sql'].upper() or 'FOR NO KEY UPDATE' in row['sql'].upper() for row in queries)
    forbidden = ('core_patient', 'core_document', 'core_patientdocument', 'core_staffaccessrevision', 'core_organisation')
    assert not any(table in row['sql'].lower() for row in queries for table in forbidden)
    assert not any(row['sql'].lstrip().upper().startswith(('INSERT ', 'UPDATE ', 'DELETE ')) for row in queries)


def _identity_order(authority_actor, *, create, writer_first):
    # Imports stay inside execution so the portable module collects without the
    # new production file. PG RED is observed separately by the coordinator.
    from apps.core.document_authority import capture_document_context, sample_document_authority, DocumentServiceError

    user, branch, request = authority_actor
    if not create:
        IdentitySecurity.objects.create(user=user, auth_epoch=0)
    context = capture_document_context(request, 'intent.list')
    assert IdentitySecurity.objects.filter(user=user).count() == (0 if create else 1)
    held, waiting, release = Event(), Event(), Event()
    pids = {}

    def writer():
        close_old_connections()
        try:
            pids['writer'] = _pid()
            with transaction.atomic():
                if not writer_first:
                    waiting.set()
                _change_epoch(user.pk, create)
                if writer_first:
                    held.set()
                    assert release.wait(15), 'Writer not released'
            return IdentitySecurity.objects.get(user_id=user.pk).auth_epoch
        finally:
            connection.close()

    def sampler():
        close_old_connections()
        try:
            pids['sampler'] = _pid()
            with transaction.atomic():
                if writer_first:
                    waiting.set()
                _lock_actor_then_existing_identity(user.pk)
                with CaptureQueriesContext(connection) as queries:
                    if writer_first:
                        with pytest.raises(DocumentServiceError) as denied:
                            sample_document_authority(context, 'intent.list')
                        assert (denied.value.code, denied.value.status, denied.value.message, denied.value.retry_after) == (
                            'not_authenticated', 401, 'Your session ended. Sign in again.', None)
                        result = 'not_authenticated'
                    else:
                        sample = sample_document_authority(context, 'intent.list')
                        assert sample.captured_epoch == 0
                        assert sample.eligible_branches == frozenset({branch.pk})
                        result = 'sampled'
                _assert_sampler_scope(queries.captured_queries)
                if not writer_first:
                    # Sampling an absent row must not create one, even while a
                    # first-profile writer is queued behind the held actor.
                    assert IdentitySecurity.objects.filter(user_id=user.pk).count() == (0 if create else 1)
                    held.set()
                    assert release.wait(15), 'Sampler not released'
            return result
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(writer if writer_first else sampler)
        try:
            assert held.wait(10), 'First transaction never held actor lock'
            second = pool.submit(sampler if writer_first else writer)
            assert waiting.wait(10), 'Second transaction never attempted actor lock'
            assert pids['writer'] != pids['sampler'] != _pid()
            _observe_wait(pids['sampler' if writer_first else 'writer'], pids['writer' if writer_first else 'sampler'])
        finally:
            release.set()
        results = (first.result(20), second.result(20))
    assert set(results) == {1, 'not_authenticated' if writer_first else 'sampled'}
    assert IdentitySecurity.objects.get(user=user).auth_epoch == 1
    assert IdentitySecurity.objects.filter(user=user).count() == 1


def test_epoch_revocation_committed_before_actor_wait_sample_is_denied(authority_actor):
    _identity_order(authority_actor, create=False, writer_first=True)


def test_first_profile_committed_before_actor_wait_sample_is_denied(authority_actor):
    _identity_order(authority_actor, create=True, writer_first=True)


def test_epoch_revocation_waits_for_prior_authority_sample(authority_actor):
    _identity_order(authority_actor, create=False, writer_first=False)


def test_missing_profile_sample_does_not_create_and_first_writer_waits(authority_actor):
    _identity_order(authority_actor, create=True, writer_first=False)
