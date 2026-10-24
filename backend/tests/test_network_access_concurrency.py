"""Real PostgreSQL API races; SQLite skips are not lock-safety evidence."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from datetime import timedelta
import uuid
import pytest
from django.db import connection, close_old_connections, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.core.models import Organisation, Branch, Membership, IdentitySecurity, NetworkOperator, NetworkPolicyState, NetworkPolicyPreview, NetworkPolicyChange, NetworkPolicyEvent

pytestmark = pytest.mark.django_db(transaction=True)
ROOT = '/api/v1/platform/network-policy/'


@pytest.fixture
def race_actor(settings):
    if connection.vendor != 'postgresql':
        pytest.skip('Actual PostgreSQL row/FK locks required.')
    owner = Organisation.objects.create(name='Synthetic concurrent owner')
    branch = Branch.objects.create(organisation=owner, name='Synthetic race', code='N-RACE')
    actor = get_user_model().objects.create(username='synthetic-network-race')
    Membership.objects.create(user=actor, branch=branch, role='master_admin')
    IdentitySecurity.objects.create(user=actor, active_ciphertext='synthetic-marker')
    NetworkOperator.objects.create(user=actor, organisation=owner)
    NetworkPolicyState.objects.filter(pk=1).update(bound_owner=owner)
    settings.HMS_SECURITY_ORGANISATION_ID = str(owner.pk)
    client = APIClient()
    client.force_login(actor)
    session = client.session
    session['auth_epoch'] = 0
    session['factor_verified_at'] = timezone.now().timestamp()
    session.save()
    return actor, client.cookies.copy()


def request_in_thread(cookies, method, path, data=None, key=None):
    close_old_connections()
    try:
        client = APIClient()
        client.cookies = cookies.copy()
        headers = {'HTTP_IDEMPOTENCY_KEY': str(key)} if key else {}
        response = getattr(client, method)(path, data, format='json', **headers)
        assert response.get('Content-Type', '').startswith('application/json'), f'Expected JSON from {path}; got status {response.status_code}'
        return response.status_code, response.json()
    finally:
        close_old_connections()


def test_same_key_preview_race_preserves_single_fixed_preview(race_actor):
    actor, cookies = race_actor
    key = uuid.uuid4()
    barrier = Barrier(2)
    payload = {'expected_revision': 1, 'policy': {'allowlist_only': False, 'allowlist': [], 'blocklist': []}, 'reason': 'Synthetic concurrent preview'}
    def run(_):
        barrier.wait(10)
        return request_in_thread(cookies, 'post', ROOT+'previews/', payload, key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert sorted(status for status, _ in results) == [200, 201]
    assert len({data['preview_id'] for _, data in results}) == 1
    assert len({data['expires_at'] for _, data in results}) == 1
    assert NetworkPolicyPreview.objects.count() == 1


def test_actor_revoked_during_user_lock_wait_cannot_preview(race_actor, monkeypatch):
    actor, cookies = race_actor
    waiting = Event()
    from django.db.models.query import QuerySet
    original = QuerySet.get
    def observed(queryset, *args, **kwargs):
        if queryset.model is get_user_model() and queryset.query.select_for_update:
            waiting.set()
        return original(queryset, *args, **kwargs)
    monkeypatch.setattr(QuerySet, 'get', observed)
    payload = {'expected_revision': 1, 'policy': {'allowlist_only': False, 'allowlist': [], 'blocklist': []}, 'reason': 'Synthetic revoked actor'}
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            locked = get_user_model().objects.select_for_update(no_key=True).get(pk=actor.pk)
            waiting.clear()
            future = pool.submit(request_in_thread, cookies, 'post', ROOT+'previews/', payload, uuid.uuid4())
            assert waiting.wait(10), 'Network writer did not reach the actor lock'
            locked.is_active = False
            locked.save(update_fields=['is_active'])
        status, data = future.result(10)
    assert status == 401 and data['code'] == 'not_authenticated'
    assert not NetworkPolicyPreview.objects.exists() and not NetworkPolicyEvent.objects.exists()


def _issued(cookies):
    status, data = request_in_thread(cookies, 'post', ROOT+'previews/', {'expected_revision': 1, 'policy': {'allowlist_only': False, 'allowlist': [], 'blocklist': []}, 'reason': 'Synthetic concurrent preview'}, uuid.uuid4())
    assert status == 201
    return data


def _activated(cookies):
    issued = _issued(cookies)
    status, data = request_in_thread(cookies, 'post', ROOT+f"previews/{issued['preview_id']}/activate/", {'expected_revision': 1})
    assert status == 200
    return data


def test_two_distinct_actor_previews_cannot_both_activate_same_revision(race_actor):
    actor, cookies = race_actor
    owner = NetworkOperator.objects.get(user=actor).organisation
    branch = Branch.objects.get(organisation=owner)
    second = get_user_model().objects.create(username='synthetic-second-network-race')
    Membership.objects.create(user=second, branch=branch, role='master_admin')
    IdentitySecurity.objects.create(user=second, active_ciphertext='synthetic-marker')
    NetworkOperator.objects.create(user=second, organisation=owner)
    other = APIClient()
    other.force_login(second)
    session = other.session
    session['auth_epoch'] = 0
    session['factor_verified_at'] = timezone.now().timestamp()
    session.save()
    clients = [cookies, other.cookies.copy()]
    previews = [_issued(item) for item in clients]
    barrier = Barrier(2)
    def activate(index):
        barrier.wait(10)
        return request_in_thread(clients[index], 'post', ROOT+f"previews/{previews[index]['preview_id']}/activate/", {'expected_revision': 1})
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(activate, range(2)))
    assert sorted(status for status, _ in outcomes) == [200, 409]
    assert NetworkPolicyChange.objects.count() == 1
    assert NetworkPolicyEvent.objects.filter(action='policy.activated').count() == 1
    assert NetworkPolicyState.objects.get(pk=1).revision == 2


def test_confirm_vs_revert_has_one_terminal_event(race_actor):
    _, cookies = race_actor
    activated = _activated(cookies)
    barrier = Barrier(2)
    def finish(action):
        barrier.wait(10)
        return request_in_thread(cookies, 'post', ROOT+f"changes/{activated['change_id']}/{action}/", {'expected_revision': 2})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(finish, ['confirm', 'revert']))
    assert sorted(status for status, _ in results) == [200, 409]
    assert NetworkPolicyEvent.objects.count() == 2
    assert NetworkPolicyState.objects.get(pk=1).revision == 3


@pytest.mark.parametrize('boundary', ['security', 'organisation', 'operator', 'singleton', 'change'])
def test_authority_or_path_revocation_after_each_database_wait(race_actor, monkeypatch, boundary):
    actor, cookies = race_actor
    activated = _activated(cookies)
    operator = NetworkOperator.objects.get(user=actor)
    model, pk = {'security': (IdentitySecurity, actor.pk), 'organisation': (Organisation, operator.organisation_id), 'operator': (NetworkOperator, operator.pk), 'singleton': (NetworkPolicyState, 1), 'change': (NetworkPolicyChange, activated['change_id'])}[boundary]
    waiting = Event()
    original_time = timezone.now()
    clock = [original_time]
    monkeypatch.setattr('django.utils.timezone.now', lambda: clock[0])
    def run():
        close_old_connections()
        def observe(execute, sql, params, many, context):
            if model._meta.db_table in sql and 'SELECT' in sql and ('FOR UPDATE' in sql or 'FOR NO KEY UPDATE' in sql):
                waiting.set()
            return execute(sql, params, many, context)
        try:
            with connection.execute_wrapper(observe):
                return request_in_thread(cookies, 'post', ROOT+f"changes/{activated['change_id']}/confirm/", {'expected_revision': 2})
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            row = model.objects.select_for_update().get(pk=pk)
            future = pool.submit(run)
            assert waiting.wait(10), f'Writer never reached {boundary} lock'
            if boundary == 'security':
                row.auth_epoch += 1
                row.save(update_fields=['auth_epoch'])
            elif boundary == 'operator':
                row.active = False
                row.version += 1
                row.save(update_fields=['active', 'version'])
            elif boundary == 'organisation':
                Membership.objects.filter(user=actor).update(is_active=False)
            elif boundary == 'singleton':
                from apps.security.network_policy import policy_digest
                policy = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['127.0.0.1/32']}
                # Simulate an already committed administrative network revoke with a consistent no-pending state.
                row.pending_change = None
                row.confirmed_policy = policy
                row.confirmed_policy_digest = policy_digest(policy)
                row.revision = 3
                row.save()
            else:
                clock[0] = original_time+timedelta(seconds=901)
        status, data = future.result(10)
    assert status in (401, 403)
    assert NetworkPolicyEvent.objects.filter(action='policy.confirmed').count() == 0


@pytest.mark.parametrize('expiry', ['rollback', 'factor'])
def test_event_insert_unique_wait_rechecks_deadline_and_factor(race_actor, monkeypatch, expiry):
    actor, cookies = race_actor
    activated = _activated(cookies)
    change = NetworkPolicyChange.objects.get(pk=activated['change_id'])
    owner = NetworkOperator.objects.get(user=actor).organisation
    collision = uuid.uuid4()
    waiting = Event()
    now = timezone.now()
    clock = [now]
    monkeypatch.setattr('django.utils.timezone.now', lambda: clock[0])
    from django.db.models.query import QuerySet
    original_create = QuerySet.create
    def insert(queryset, **kwargs):
        if queryset.model is NetworkPolicyEvent and kwargs.get('action') == 'policy.confirmed':
            kwargs['id'] = collision
            waiting.set()
        return original_create(queryset, **kwargs)
    monkeypatch.setattr(QuerySet, 'create', insert)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            NetworkPolicyEvent.objects.create(id=collision, owner=owner, action='owner.bound', outcome='bound', revision=1, reason='Synthetic unique holder', created_at=now)
            future = pool.submit(request_in_thread, cookies, 'post', ROOT+f"changes/{change.pk}/confirm/", {'expected_revision': 2})
            assert waiting.wait(10), 'Writer never reached final event INSERT'
            clock[0] = change.rollback_at if expiry == 'rollback' else now+timedelta(seconds=901)
            transaction.set_rollback(True)
        status, data = future.result(15)
    assert status == (409 if expiry == 'rollback' else 403)
    assert data['code'] == ('network_change_expired' if expiry == 'rollback' else 'mfa_step_up_required')
    assert not NetworkPolicyEvent.objects.filter(action='policy.confirmed').exists()
    state = NetworkPolicyState.objects.get(pk=1)
    assert state.revision == (3 if expiry == 'rollback' else 2)
    assert NetworkPolicyEvent.objects.filter(action='policy.expired').count() == (1 if expiry == 'rollback' else 0)


def test_two_reconcilers_materialise_expiry_once(race_actor, monkeypatch):
    _, cookies = race_actor
    activated = _activated(cookies)
    change = NetworkPolicyChange.objects.get(pk=activated['change_id'])
    monkeypatch.setattr('django.utils.timezone.now', lambda: change.rollback_at)
    barrier = Barrier(2)
    def reconcile(_):
        close_old_connections()
        try:
            from apps.core.network_access import reconcile_expired_policy
            from apps.core.network_oob import OutOfBandContext
            barrier.wait(10)
            return reconcile_expired_policy(OutOfBandContext('Synthetic reconciler', 'Synthetic concurrent expiry'))
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reconcile, range(2)))
    assert sorted(result['changed'] for result in results) == [False, True]
    assert NetworkPolicyEvent.objects.filter(action='policy.expired').count() == 1
    assert NetworkPolicyState.objects.get(pk=1).revision == 3
