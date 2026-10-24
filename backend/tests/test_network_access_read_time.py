"""Management read time must select the very snapshot returned to the caller."""
from datetime import timedelta
import pytest
from django.utils import timezone
from apps.core import network_access
from apps.core.models import NetworkPolicyState, NetworkPolicyChange, NetworkPolicyPreview, NetworkPolicyEvent, IdentitySecurity
from tests.test_network_access_api import manager, preview, ROOT, OPEN

pytestmark = pytest.mark.django_db


@pytest.fixture
def pending_read(manager):
    client, *_ = manager
    issued = preview(client)
    assert issued.status_code == 201
    response = client.post(ROOT+f"previews/{issued.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json')
    assert response.status_code == 200
    change = NetworkPolicyChange.objects.get(pk=response.json()['change_id'])
    return client, change


def image():
    return {model._meta.label: list(model.objects.order_by('pk').values()) for model in (NetworkPolicyState, NetworkPolicyChange, NetworkPolicyPreview, NetworkPolicyEvent, IdentitySecurity)}


def utc(value):
    return value.isoformat().replace('+00:00', 'Z')


@pytest.mark.parametrize('microseconds,status,effective', [
    (-1, 'pending', {'allowlist_only': True, 'allowlist': ['127.0.0.1/32'], 'blocklist': []}),
    (0, 'expired_unreconciled', OPEN),
    (1, 'expired_unreconciled', OPEN),
])
def test_read_crossing_deadline_uses_final_authorised_snapshot_and_same_server_time(pending_read, monkeypatch, microseconds, status, effective):
    client, change = pending_read
    started = change.rollback_at-timedelta(microseconds=2)
    selected = change.rollback_at+timedelta(microseconds=microseconds)
    clock = [started]
    monkeypatch.setattr(timezone, 'now', lambda: clock[0])
    original = network_access.require_network_operator
    calls = []
    def advance_after_initial_authority(context, *args, **kwargs):
        result = original(context, *args, **kwargs)
        calls.append(True)
        if len(calls) == 1:
            clock[0] = selected
        return result
    monkeypatch.setattr(network_access, 'require_network_operator', advance_after_initial_authority)
    before = image()
    response = client.get(ROOT)
    assert response.status_code == 200
    data = response.json()
    assert data['server_time'] == utc(selected)
    assert data['pending']['status'] == status
    assert data['effective_policy'] == effective
    assert data['revision'] == 2
    assert data['pending']['change_id'] == str(change.pk)
    assert image() == before


@pytest.mark.parametrize('before_activation', [False, True])
def test_clock_moving_backwards_during_read_is_unavailable_without_writes(pending_read, monkeypatch, before_activation):
    client, change = pending_read
    started = change.activated_at+timedelta(seconds=1)
    regressed = change.activated_at-timedelta(microseconds=1) if before_activation else started-timedelta(microseconds=1)
    clock = [started]
    monkeypatch.setattr(timezone, 'now', lambda: clock[0])
    original = network_access.require_network_operator
    calls = []
    def regress_after_initial_authority(context, *args, **kwargs):
        result = original(context, *args, **kwargs)
        calls.append(True)
        if len(calls) == 1:
            clock[0] = regressed
        return result
    monkeypatch.setattr(network_access, 'require_network_operator', regress_after_initial_authority)
    before = image()
    response = client.get(ROOT)
    assert response.status_code == 503
    assert response.json()['code'] == 'network_policy_unavailable'
    assert 'effective_policy' not in response.json()
    assert image() == before


def test_final_authority_returns_new_coherent_revision_after_expiry_reconciliation(pending_read, monkeypatch):
    client, change = pending_read
    clock = [change.rollback_at-timedelta(microseconds=1)]
    monkeypatch.setattr(timezone, 'now', lambda: clock[0])
    original = network_access.require_network_operator
    calls = []
    def reconcile_after_initial_authority(context, *args, **kwargs):
        result = original(context, *args, **kwargs)
        calls.append(True)
        if len(calls) == 1:
            from apps.core.network_oob import OutOfBandContext
            clock[0] = change.rollback_at
            network_access.reconcile_expired_policy(OutOfBandContext('Synthetic read race', 'Synthetic independent expiry'))
        return result
    monkeypatch.setattr(network_access, 'require_network_operator', reconcile_after_initial_authority)
    response = client.get(ROOT)
    assert response.status_code == 200
    data = response.json()
    assert data['revision'] == 3 and data['pending'] is None
    assert data['confirmed_policy'] == OPEN and data['effective_policy'] == OPEN
    assert data['server_time'] == utc(change.rollback_at)
    assert NetworkPolicyEvent.objects.filter(action='policy.expired').count() == 1


def test_no_pending_state_keeps_exact_selection_time_and_no_write(manager, monkeypatch):
    client, *_ = manager
    selected = timezone.now()
    monkeypatch.setattr(timezone, 'now', lambda: selected)
    before = image()
    response = client.get(ROOT)
    assert response.status_code == 200
    assert response.json()['server_time'] == utc(selected)
    assert response.json()['revision'] == 1 and response.json()['pending'] is None
    assert response.json()['confirmed_policy'] == OPEN and response.json()['effective_policy'] == OPEN
    assert image() == before
