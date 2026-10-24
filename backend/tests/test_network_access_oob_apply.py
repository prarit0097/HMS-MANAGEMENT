"""Public OS wrappers reject boolean lookalikes before even expiry maintenance."""
import pytest
from django.utils import timezone
from apps.core.models import Organisation, NetworkPolicyState, NetworkPolicyChange, NetworkPolicyPreview, NetworkPolicyEvent, NetworkOperator, IdentitySecurity
from apps.core.network_oob import OutOfBandContext, recover_policy, transfer_owner
from apps.core.network_authority import NetworkError
from tests.test_network_access_api import manager, preview, ROOT

pytestmark = pytest.mark.django_db


def image():
    return {model._meta.label: list(model.objects.order_by('pk').values()) for model in (NetworkPolicyState, NetworkPolicyChange, NetworkPolicyPreview, NetworkPolicyEvent, NetworkOperator, IdentitySecurity)}


@pytest.fixture
def pending_apply(manager):
    client, _, owner, _ = manager
    issued = preview(client)
    assert issued.status_code == 201
    response = client.post(ROOT+f"previews/{issued.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json')
    assert response.status_code == 200
    return owner, NetworkPolicyChange.objects.get(pk=response.json()['change_id'])


def operation(action, owner, change, settings, apply):
    context = OutOfBandContext('Synthetic strict wrapper', 'Synthetic strict apply validation')
    if action == 'recover':
        return lambda: recover_policy(context, str(change.pk), 'fallback', 2, apply=apply)
    target = Organisation.objects.create(name='Synthetic strict apply target')
    settings.HMS_SECURITY_ORGANISATION_ID = str(target.pk)
    return lambda: transfer_owner(context, str(owner.pk), str(target.pk), 2, apply=apply)


@pytest.mark.parametrize('value', ['false', 1, 0, None, '', [], {}], ids=['text-false', 'one', 'zero', 'none', 'empty-text', 'list', 'object'])
@pytest.mark.parametrize('action', ['recover', 'transfer'])
@pytest.mark.parametrize('expired', [False, True], ids=['live', 'expired'])
def test_public_oob_apply_rejects_nonbooleans_before_any_write(pending_apply, settings, monkeypatch, value, action, expired):
    owner, change = pending_apply
    call = operation(action, owner, change, settings, value)
    if expired:
        monkeypatch.setattr(timezone, 'now', lambda: change.rollback_at)
    before = image()
    error = None
    try:
        call()
    except NetworkError as exc:
        error = exc
    assert image() == before, 'Invalid apply mutated policy, change, event, entitlement or identity records'
    assert error is not None and error.default_code == 'validation_error' and error.status_code == 400


@pytest.mark.parametrize('action', ['recover', 'transfer'])
def test_exact_boolean_false_is_pure_and_true_applies_once(pending_apply, settings, action):
    owner, change = pending_apply
    dry_run = operation(action, owner, change, settings, False)
    before = image()
    result = dry_run()
    assert result['applied'] is False and result['revision'] == 2
    assert image() == before
    if action == 'recover':
        result = recover_policy(OutOfBandContext('Synthetic strict wrapper', 'Synthetic explicit boolean apply'), str(change.pk), 'fallback', 2, apply=True)
    else:
        result = transfer_owner(OutOfBandContext('Synthetic strict wrapper', 'Synthetic explicit boolean apply'), str(owner.pk), settings.HMS_SECURITY_ORGANISATION_ID, 2, apply=True)
    assert result['applied'] is True and result['revision'] == 3
    assert NetworkPolicyState.objects.get(pk=1).revision == 3
    assert NetworkPolicyEvent.objects.count() == 2
