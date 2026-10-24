"""Breaks caught: missing durable overlay/intersection, owner-coupled admission and stale bindings."""
import importlib.util
import pytest
from django.test import override_settings
from django.utils import timezone
from apps.core.models import NetworkPolicyState

if importlib.util.find_spec('apps.core.network_environment'):
    from apps.core import network_environment as service
else:
    service = None

pytestmark = pytest.mark.django_db


def test_durable_network_decision_service_exists():
    assert service is not None, 'Environment AND durable overlay decision is missing'


@pytest.mark.parametrize('owner', ['', 'invalid-owner'])
def test_enforcement_works_without_management_owner(settings, owner):
    assert service is not None, 'Environment AND durable overlay decision is missing'
    settings.HMS_SECURITY_ORGANISATION_ID = owner
    decision = service.network_decision('198.51.100.1', None)
    assert decision.allowed is True
    assert decision.verified_ip == '198.51.100.1'


def test_overlay_block_intersects_environment(settings):
    assert service is not None, 'Environment AND durable overlay decision is missing'
    from apps.security.network_policy import policy_digest
    policy = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['198.51.100.0/24']}
    NetworkPolicyState.objects.filter(pk=1).update(confirmed_policy=policy, confirmed_policy_digest=policy_digest(policy))
    assert service.network_decision('198.51.100.1', None).allowed is False
    assert service.network_decision('203.0.113.1', None).allowed is True


def test_missing_state_is_unavailable_and_never_repaired():
    assert service is not None, 'Environment AND durable overlay decision is missing'
    from apps.core.network_snapshot import NetworkStateUnavailable
    NetworkPolicyState.objects.all().delete()
    with pytest.raises(NetworkStateUnavailable):
        service.network_decision('198.51.100.1', None)
    assert not NetworkPolicyState.objects.exists()


def test_owner_and_proxy_drift_change_fingerprint(settings):
    assert service is not None, 'Environment binding fingerprint is missing'
    settings.HMS_SECURITY_ORGANISATION_ID = ''
    settings.HMS_TRUSTED_PROXIES = ()
    original = service.environment_snapshot().digest
    settings.HMS_SECURITY_ORGANISATION_ID = 'invalid-owner'
    assert service.environment_snapshot().digest != original
    owner_digest = service.environment_snapshot().digest
    settings.HMS_TRUSTED_PROXIES = ('127.0.0.1/32',)
    assert service.environment_snapshot().digest != owner_digest
