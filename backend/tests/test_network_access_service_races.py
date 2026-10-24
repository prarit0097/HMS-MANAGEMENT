"""Remaining bounded PostgreSQL service races, with observed database wait edges."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, local
from time import monotonic
from datetime import timedelta
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections
from django.db.models.query import QuerySet
from rest_framework.test import APIClient

from apps.core.models import Organisation, Branch, Membership, IdentitySecurity, StaffAccessRevision, AuditEvent, NetworkOperator, NetworkPolicyState, NetworkPolicyPreview, NetworkPolicyChange, NetworkPolicyEvent
from tests.test_network_access_concurrency import race_actor, _issued, ROOT

pytestmark = pytest.mark.django_db(transaction=True)


def _pid():
    connection.ensure_connection()
    raw = connection.connection
    return raw.info.backend_pid if hasattr(raw, 'info') else raw.get_backend_pid()


def _assert_database_wait(worker_pid, blocker_pid):
    # Observe actual PG lock waiting, rather than infer it from a hook before SQL.
    expires = monotonic()+10
    while monotonic() < expires:
        with connection.cursor() as cursor:
            cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [blocker_pid, worker_pid])
            if cursor.fetchone()[0]:
                return
    pytest.fail('Expected PostgreSQL lock wait was not observed before release')


def _client_post(cookies, path, data, key=None):
    client = APIClient()
    client.cookies = cookies.copy()
    headers = {'HTTP_IDEMPOTENCY_KEY': str(key)} if key else {}
    response = client.post(path, data, format='json', **headers)
    assert response.get('Content-Type', '').startswith('application/json'), f'Unexpected status {response.status_code}'
    return response.status_code, response.json()


def _preview_payload():
    return {'expected_revision': 1, 'policy': {'allowlist_only': False, 'allowlist': [], 'blocklist': []}, 'reason': 'Synthetic service lock race'}


def test_staff_service_revocation_wins_organisation_wait_without_target_user_deadlock(race_actor, monkeypatch, settings):
    actor, cookies = race_actor
    owner = NetworkOperator.objects.get(user=actor).organisation
    branch = Branch.objects.get(organisation=owner)
    staff_actor = get_user_model().objects.create(username='synthetic-staff-revoker')
    Membership.objects.create(user=staff_actor, branch=branch, role='master_admin')
    IdentitySecurity.objects.create(user=staff_actor)
    settings.HMS_REQUIRE_ADMIN_MFA = False
    phase = local()
    held, waiting, release = Event(), Event(), Event()
    pids = {}
    original_get = QuerySet.get
    def observed_get(queryset, *args, **kwargs):
        role = getattr(phase, 'role', None)
        locked_org = queryset.model is Organisation and queryset.query.select_for_update
        if locked_org and role == 'network':
            pids['network'] = _pid()
            waiting.set()
        row = original_get(queryset, *args, **kwargs)
        if locked_org and role == 'staff':
            pids['staff'] = _pid()
            held.set()
            assert release.wait(15), 'Staff writer was never released'
        return row
    monkeypatch.setattr(QuerySet, 'get', observed_get)
    def staff_write():
        close_old_connections()
        phase.role = 'staff'
        try:
            from apps.core.staff_access import change_staff
            fresh = get_user_model().objects.get(pk=staff_actor.pk)
            return change_staff(fresh, owner.pk, actor.pk, {'expected_version': 0, 'status': 'suspended'})
        finally:
            close_old_connections()
    def network_write():
        close_old_connections()
        phase.role = 'network'
        try:
            return _client_post(cookies, ROOT+'previews/', _preview_payload(), uuid.uuid4())
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        staff = pool.submit(staff_write)
        try:
            assert held.wait(10), 'Staff service never acquired organisation'
            network = pool.submit(network_write)
            assert waiting.wait(10), 'Network writer never reached organisation lock'
            _assert_database_wait(pids['network'], pids['staff'])
        finally:
            release.set()
        result = staff.result(15)
        status, data = network.result(15)
    assert result['status'] == 'suspended'
    assert status == 403 and data['code'] == 'permission_denied'
    assert AuditEvent.objects.filter(action='staff.changed').count() == 1
    assert StaffAccessRevision.objects.get(user=actor, organisation=owner).version == 1
    assert not NetworkPolicyPreview.objects.exists() and not NetworkPolicyEvent.objects.exists()


def test_os_operator_revoke_wins_actor_wait_without_lost_version(race_actor, monkeypatch):
    actor, cookies = race_actor
    operator = NetworkOperator.objects.get(user=actor)
    phase = local()
    held, waiting, release = Event(), Event(), Event()
    pids = {}
    original_get = QuerySet.get
    def observed_get(queryset, *args, **kwargs):
        role = getattr(phase, 'role', None)
        locked_user = queryset.model is get_user_model() and queryset.query.select_for_update
        if locked_user and role == 'network':
            pids['network'] = _pid()
            waiting.set()
        row = original_get(queryset, *args, **kwargs)
        if locked_user and role == 'operator':
            pids['operator'] = _pid()
            held.set()
            assert release.wait(15), 'Operator writer was never released'
        return row
    monkeypatch.setattr(QuerySet, 'get', observed_get)
    def revoke():
        close_old_connections()
        phase.role = 'operator'
        try:
            from apps.core.network_oob import OutOfBandContext, change_operator
            return change_operator(OutOfBandContext('Synthetic console', 'Synthetic service revoke'), str(operator.organisation_id), actor.pk, 1, 1, 'revoke')
        finally:
            close_old_connections()
    def network_write():
        close_old_connections()
        phase.role = 'network'
        try:
            return _client_post(cookies, ROOT+'previews/', _preview_payload(), uuid.uuid4())
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        revoked = pool.submit(revoke)
        try:
            assert held.wait(10), 'OS operator service never acquired target User'
            network = pool.submit(network_write)
            assert waiting.wait(10), 'Network writer never reached User lock'
            _assert_database_wait(pids['network'], pids['operator'])
        finally:
            release.set()
        result = revoked.result(15)
        status, data = network.result(15)
    operator.refresh_from_db()
    assert result['version'] == 2 and not operator.active and operator.version == 2
    assert status == 403 and data['code'] == 'permission_denied'
    assert NetworkPolicyState.objects.get(pk=1).revision == 1
    assert NetworkPolicyEvent.objects.filter(action='operator.revoked').count() == 1
    assert not NetworkPolicyPreview.objects.exists()


def test_os_owner_transfer_invalidates_http_waiter_and_does_not_copy_entitlement(race_actor, monkeypatch, settings):
    actor, cookies = race_actor
    operator = NetworkOperator.objects.get(user=actor)
    old_id = operator.organisation_id
    target = Organisation.objects.create(name='Synthetic race replacement owner')
    issued = _issued(cookies)
    status, activated = _client_post(cookies, ROOT+f"previews/{issued['preview_id']}/activate/", {'expected_revision': 1})
    assert status == 200
    phase = local()
    held, waiting, release = Event(), Event(), Event()
    pids = {}
    original_get = QuerySet.get
    def observed_get(queryset, *args, **kwargs):
        role = getattr(phase, 'role', None)
        locked_org = queryset.model is Organisation and queryset.query.select_for_update
        if locked_org and role == 'network':
            pids['network'] = _pid()
            waiting.set()
        row = original_get(queryset, *args, **kwargs)
        # Both transfer organisations must be locked before starting the HTTP waiter.
        if locked_org and role == 'transfer' and row.pk == max(old_id, target.pk):
            pids['transfer'] = _pid()
            held.set()
            assert release.wait(15), 'Owner transfer was never released'
        return row
    monkeypatch.setattr(QuerySet, 'get', observed_get)
    def transfer():
        close_old_connections()
        phase.role = 'transfer'
        try:
            from apps.core.network_oob import OutOfBandContext, transfer_owner
            return transfer_owner(OutOfBandContext('Synthetic console', 'Synthetic waiting owner transfer'), str(old_id), str(target.pk), 2, apply=True)
        finally:
            close_old_connections()
    def network_write():
        close_old_connections()
        phase.role = 'network'
        try:
            return _client_post(cookies, ROOT+f"changes/{activated['change_id']}/confirm/", {'expected_revision': 2})
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        transferred = pool.submit(transfer)
        try:
            assert held.wait(10), 'Transfer never acquired sorted organisations'
            network = pool.submit(network_write)
            assert waiting.wait(10), 'Network writer never reached old owner organisation'
            _assert_database_wait(pids['network'], pids['transfer'])
            settings.HMS_SECURITY_ORGANISATION_ID = str(target.pk)
        finally:
            release.set()
        result = transferred.result(15)
        status, data = network.result(15)
    assert result['revision'] == 3 and result['entitlements_copied'] is False
    assert status in (403, 409, 503)
    assert data['code'] in ('permission_denied', 'network_preview_invalidated', 'network_owner_unavailable')
    state = NetworkPolicyState.objects.get(pk=1)
    assert state.bound_owner_id == target.pk and state.revision == 3 and state.pending_change_id is None
    assert NetworkPolicyChange.objects.get(pk=activated['change_id']).status == 'owner_transferred'
    assert not NetworkOperator.objects.filter(organisation=target).exists()
    assert NetworkPolicyEvent.objects.filter(action='owner.transferred').count() == 1
    assert not NetworkPolicyEvent.objects.filter(action='policy.confirmed').exists()


def test_activation_event_unique_wait_crossing_preview_expiry_rolls_back_all_business_writes(race_actor, monkeypatch):
    actor, cookies = race_actor
    issued = _issued(cookies)
    preview = NetworkPolicyPreview.objects.get(pk=issued['preview_id'])
    owner = NetworkOperator.objects.get(user=actor).organisation
    collision = uuid.uuid4()
    waiting = Event()
    pids = {}
    from django.utils import timezone
    from django.db import transaction
    clock = [timezone.now()]
    monkeypatch.setattr(timezone, 'now', lambda: clock[0])
    original_create = QuerySet.create
    def create(queryset, **kwargs):
        if queryset.model is NetworkPolicyEvent and kwargs.get('action') == 'policy.activated':
            kwargs['id'] = collision
            pids['network'] = _pid()
            waiting.set()
        return original_create(queryset, **kwargs)
    monkeypatch.setattr(QuerySet, 'create', create)
    def network_write():
        close_old_connections()
        try:
            return _client_post(cookies, ROOT+f"previews/{preview.pk}/activate/", {'expected_revision': 1})
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            NetworkPolicyEvent.objects.create(id=collision, owner=owner, action='owner.bound', outcome='bound', revision=1, reason='Synthetic unique event holder', created_at=clock[0])
            holder_pid = _pid()
            future = pool.submit(network_write)
            assert waiting.wait(10), 'Activation never reached event INSERT'
            _assert_database_wait(pids['network'], holder_pid)
            clock[0] = preview.expires_at
            transaction.set_rollback(True)
        status, data = future.result(15)
    assert status == 409 and data['code'] == 'network_preview_expired'
    state = NetworkPolicyState.objects.get(pk=1)
    preview.refresh_from_db()
    assert state.revision == 1 and state.pending_change_id is None and preview.result_change_id is None
    assert not NetworkPolicyChange.objects.exists() and not NetworkPolicyEvent.objects.exists()


@pytest.mark.parametrize('following', ['staff', 'operator', 'transfer'])
def test_network_activation_wins_before_real_service_revocation_or_transfer(race_actor, monkeypatch, settings, following):
    actor, cookies = race_actor
    operator = NetworkOperator.objects.get(user=actor)
    owner = operator.organisation
    branch = Branch.objects.get(organisation=owner)
    staff_actor = get_user_model().objects.create(username='synthetic-following-staff')
    Membership.objects.create(user=staff_actor, branch=branch, role='master_admin')
    IdentitySecurity.objects.create(user=staff_actor)
    target = Organisation.objects.create(name='Synthetic following owner')
    settings.HMS_REQUIRE_ADMIN_MFA = False
    issued = _issued(cookies)
    saved_preview = NetworkPolicyPreview.objects.get(pk=issued['preview_id'])
    original_preview_times = (saved_preview.created_at, saved_preview.expires_at)
    phase = local()
    held, waiting, release = Event(), Event(), Event()
    pids = {}
    original_get = QuerySet.get
    lock_model = get_user_model() if following == 'operator' else Organisation
    def observed_get(queryset, *args, **kwargs):
        role = getattr(phase, 'role', None)
        matching = queryset.model is lock_model and queryset.query.select_for_update
        owner_lock = following != 'transfer' or kwargs.get('pk') == owner.pk
        if matching and owner_lock and role == 'following':
            pids['following'] = _pid()
            waiting.set()
        row = original_get(queryset, *args, **kwargs)
        if matching and role == 'network' and not held.is_set():
            pids['network'] = _pid()
            held.set()
            assert release.wait(15), 'Network writer was never released'
        if queryset.model is Organisation and queryset.query.select_for_update and role == 'following' and following == 'transfer' and row.pk == max(owner.pk, target.pk):
            # Change all worker configuration only after the old-owner HTTP
            # transaction has committed and transfer owns BOTH organisations.
            settings.HMS_SECURITY_ORGANISATION_ID = str(target.pk)
        return row
    monkeypatch.setattr(QuerySet, 'get', observed_get)
    def network_write():
        close_old_connections()
        phase.role = 'network'
        try:
            return _client_post(cookies, ROOT+f"previews/{saved_preview.pk}/activate/", {'expected_revision': 1})
        finally:
            close_old_connections()
    def following_write():
        close_old_connections()
        phase.role = 'following'
        try:
            from apps.core.network_oob import OutOfBandContext, change_operator, transfer_owner
            if following == 'staff':
                from apps.core.staff_access import change_staff
                return change_staff(get_user_model().objects.get(pk=staff_actor.pk), owner.pk, actor.pk, {'expected_version': 0, 'status': 'suspended'})
            context = OutOfBandContext('Synthetic console', 'Synthetic following service change')
            if following == 'operator':
                return change_operator(context, str(owner.pk), actor.pk, 1, 2, 'revoke')
            return transfer_owner(context, str(owner.pk), str(target.pk), 2, apply=True)
        finally:
            close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        network = pool.submit(network_write)
        try:
            assert held.wait(10), 'Network writer never acquired its shared lock'
            followed = pool.submit(following_write)
            assert waiting.wait(10), 'Following service never reached the held lock'
            _assert_database_wait(pids['following'], pids['network'])
        finally:
            release.set()
        status, data = network.result(15)
        result = followed.result(15)
    assert status == 200 and data['outcome'] == 'pending' and data['revision'] == 2
    change = NetworkPolicyChange.objects.get(pk=data['change_id'])
    state = NetworkPolicyState.objects.get(pk=1)
    saved_preview.refresh_from_db()
    assert saved_preview.result_change_id == change.pk
    assert (saved_preview.created_at, saved_preview.expires_at) == original_preview_times
    assert change.rollback_at == change.activated_at+timedelta(seconds=300)
    assert NetworkPolicyEvent.objects.filter(action='policy.activated').count() == 1
    if following == 'staff':
        assert result['status'] == 'suspended'
        assert AuditEvent.objects.filter(action='staff.changed').count() == 1
        assert state.revision == 2 and state.pending_change_id == change.pk and change.status == 'pending'
    elif following == 'operator':
        operator.refresh_from_db()
        assert result['version'] == 2 and not operator.active and operator.version == 2
        assert NetworkPolicyEvent.objects.filter(action='operator.revoked').count() == 1
        assert state.revision == 2 and state.pending_change_id == change.pk and change.status == 'pending'
    else:
        assert result['revision'] == 3 and result['entitlements_copied'] is False
        assert state.bound_owner_id == target.pk and state.pending_change_id is None and change.status == 'owner_transferred'
        assert not NetworkOperator.objects.filter(organisation=target).exists()
        assert NetworkPolicyEvent.objects.filter(action='owner.transferred').count() == 1
    # Current authority is gone; the old actor cannot adopt or confirm its change.
    denied_status, denied = _client_post(cookies, ROOT+f"changes/{change.pk}/confirm/", {'expected_revision': 2})
    assert denied_status in (403, 409, 503)
    assert denied['code'] in ('permission_denied', 'network_preview_invalidated', 'network_owner_unavailable')
    assert not NetworkPolicyEvent.objects.filter(action='policy.confirmed').exists()
