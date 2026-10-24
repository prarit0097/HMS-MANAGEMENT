"""OS workflows must be explicit, versioned, audited and dry-run by default."""
import io
import json
import uuid
from datetime import timedelta
import pytest
from django.core.management import call_command, get_commands
from django.contrib.auth import get_user_model
from apps.core.models import Organisation, Branch, Membership, NetworkPolicyState, NetworkPolicyEvent, NetworkOperator
from tests.test_network_access_api import manager, preview, ROOT, OPEN

pytestmark = pytest.mark.django_db


@pytest.fixture
def unbound(settings):
    owner = Organisation.objects.create(name='Synthetic OS owner')
    branch = Branch.objects.create(organisation=owner, name='Synthetic', code='OS')
    user = get_user_model().objects.create(username='os-target')
    Membership.objects.create(user=user, branch=branch, role='master_admin')
    settings.HMS_SECURITY_ORGANISATION_ID = str(owner.pk)
    return owner, user


def test_local_management_commands_exist():
    assert 'network_policy' in get_commands(), 'Audited OS policy command missing'
    assert 'network_operator' in get_commands(), 'Audited OS operator command missing'


def test_explicit_bind_grant_revoke_never_creates_master_or_copies_authority(unbound):
    assert 'network_policy' in get_commands(), 'Audited OS policy command missing'
    owner, user = unbound
    out = io.StringIO()
    call_command('network_policy', 'bind-owner', '--organisation', str(owner.pk), '--expected-revision', '1', '--os-actor', 'Synthetic console', '--reason', 'Synthetic explicit binding', stdout=out)
    state = NetworkPolicyState.objects.get(pk=1)
    assert state.bound_owner_id == owner.pk and state.revision == 2
    assert not NetworkOperator.objects.exists()
    call_command('network_operator', 'grant', '--organisation', str(owner.pk), '--user-id', str(user.pk), '--expected-version', '0', '--expected-revision', '2', '--os-actor', 'Synthetic console', '--reason', 'Synthetic explicit grant', stdout=out)
    operator = NetworkOperator.objects.get(user=user, organisation=owner)
    assert operator.active and operator.version == 1
    call_command('network_operator', 'revoke', '--organisation', str(owner.pk), '--user-id', str(user.pk), '--expected-version', '1', '--expected-revision', '2', '--os-actor', 'Synthetic console', '--reason', 'Synthetic explicit revoke', stdout=out)
    operator.refresh_from_db()
    assert not operator.active and operator.version == 2
    assert NetworkPolicyState.objects.get(pk=1).revision == 2
    assert NetworkPolicyEvent.objects.count() == 3
    assert Membership.objects.filter(user=user, role='master_admin').count() == 1


def test_recovery_dry_run_and_historical_snapshot_preserve_immutable_changes(manager):
    from apps.core.models import NetworkPolicyChange, NetworkPolicyPreview
    from apps.core.network_oob import OutOfBandContext, recover_policy
    client, *_ = manager
    first = preview(client)
    activated = client.post(ROOT+f"previews/{first.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json').json()
    assert client.post(ROOT+f"changes/{activated['change_id']}/confirm/", {'expected_revision': 2}, format='json').status_code == 200
    second = preview(client, policy=OPEN, revision=3)
    active2 = client.post(ROOT+f"previews/{second.json()['preview_id']}/activate/", {'expected_revision': 3}, format='json').json()
    before = list(NetworkPolicyChange.objects.order_by('pk').values())
    context = OutOfBandContext('Synthetic console', 'Synthetic snapshot recovery')
    dry = recover_policy(context, activated['change_id'], 'fallback', 4)
    assert dry['applied'] is False and dry['after'] == OPEN
    assert list(NetworkPolicyChange.objects.order_by('pk').values()) == before
    recovered = recover_policy(context, activated['change_id'], 'fallback', 4, apply=True)
    assert recovered['revision'] == 5
    old = NetworkPolicyChange.objects.get(pk=activated['change_id'])
    current = NetworkPolicyChange.objects.get(pk=active2['change_id'])
    assert old.status == 'confirmed' and old.terminal_revision == 3
    assert current.status == 'recovered' and current.terminal_revision == 5
    assert NetworkPolicyChange.objects.count() == 2
    assert NetworkPolicyPreview.objects.get(pk=first.json()['preview_id']).result_change_id == old.pk
    assert NetworkPolicyState.objects.get(pk=1).confirmed_policy == OPEN


def test_owner_transfer_dry_run_preserves_policy_and_never_copies_entitlements(manager, settings):
    from apps.core.models import NetworkPolicyChange
    from apps.core.network_oob import OutOfBandContext, transfer_owner, change_operator
    client, user, old, _ = manager
    issued = preview(client)
    active = client.post(ROOT+f"previews/{issued.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json').json()
    target = Organisation.objects.create(name='Synthetic replacement owner')
    branch = Branch.objects.create(organisation=target, name='Synthetic new owner branch', code='NEW-OWNER')
    Membership.objects.create(user=user, branch=branch, role='master_admin')
    settings.HMS_SECURITY_ORGANISATION_ID = str(target.pk)
    context = OutOfBandContext('Synthetic console', 'Synthetic explicit owner transfer')
    assert transfer_owner(context, str(old.pk), str(target.pk), 2)['applied'] is False
    assert NetworkPolicyState.objects.get(pk=1).bound_owner_id == old.pk
    result = transfer_owner(context, str(old.pk), str(target.pk), 2, apply=True)
    assert result['revision'] == 3 and result['entitlements_copied'] is False
    state = NetworkPolicyState.objects.get(pk=1)
    assert state.bound_owner_id == target.pk and state.confirmed_policy == OPEN and state.pending_change_id is None
    assert NetworkPolicyChange.objects.get(pk=active['change_id']).status == 'owner_transferred'
    assert not NetworkOperator.objects.filter(organisation=target).exists()
    assert client.get(ROOT).status_code == 403
    change_operator(context, str(target.pk), user.pk, 0, 3, 'grant')
    history = client.get(ROOT+'history/')
    assert history.status_code == 200
    assert {event['action'] for event in history.json()['results']} <= {'owner.transferred', 'operator.granted'}


def test_recovery_expired_pending_commits_expiry_before_revision_conflict(manager, monkeypatch):
    from apps.core.models import NetworkPolicyChange
    from apps.core.network_oob import OutOfBandContext, recover_policy
    from apps.core.network_authority import NetworkError
    client, *_ = manager
    issued = preview(client)
    active = client.post(ROOT+f"previews/{issued.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json').json()
    change = NetworkPolicyChange.objects.get(pk=active['change_id'])
    monkeypatch.setattr('django.utils.timezone.now', lambda: change.rollback_at)
    with pytest.raises(NetworkError) as error:
        recover_policy(OutOfBandContext('Synthetic console', 'Synthetic expired recovery'), str(change.pk), 'fallback', 2, apply=True)
    assert error.value.default_code == 'network_revision_conflict'
    assert NetworkPolicyState.objects.get(pk=1).revision == 3
    assert NetworkPolicyEvent.objects.filter(action='policy.expired').count() == 1
    assert not NetworkPolicyEvent.objects.filter(action='policy.recovered').exists()
