"""Explicit test-only replacement for migration seed lost by transaction-test flush.

This runs once before DB tests, never while handling a request. Tests may delete
the singleton afterwards to verify fail-closed missing-state behavior.
"""
import pytest


@pytest.fixture(autouse=True)
def network_migration_baseline(request):
    if request.node.get_closest_marker('network_owns_baseline'):
        return
    if request.node.get_closest_marker('django_db') or any(name in request.fixturenames for name in ('db', 'transactional_db')):
        request.getfixturevalue('db')
        from apps.core.models import NetworkPolicyState
        from apps.security.network_policy import policy_digest
        policy = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
        if not NetworkPolicyState.objects.filter(pk=1).exists():
            NetworkPolicyState.objects.create(pk=1, revision=1, confirmed_policy=policy, confirmed_policy_digest=policy_digest(policy))
