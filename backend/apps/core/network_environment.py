"""Current OS environment ceiling intersected with the coherent durable overlay."""
from dataclasses import dataclass
import hashlib
import json
from uuid import UUID
from django.conf import settings
from django.utils import timezone
from apps.security.ip_policy import normalise_client_ip, evaluate_ip, _network
from .network_snapshot import load_network_snapshot, NetworkStateUnavailable


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def configured_owner():
    value = getattr(settings, 'HMS_SECURITY_ORGANISATION_ID', '')
    try:
        return UUID(value) if isinstance(value, str) and value else None
    except (ValueError, AttributeError):
        return None


def _rules(values):
    if not isinstance(values, (list, tuple)) or any(not isinstance(value, str) for value in values):
        raise ValueError('Invalid environment network rules')
    networks = {_network(value) for value in values}
    return tuple(str(network) for network in sorted(networks, key=lambda n: (n.version, int(n.network_address), n.prefixlen)))


@dataclass(frozen=True)
class EnvironmentSnapshot:
    allowlist_only: bool
    allowlist: tuple
    blocklist: tuple
    trusted_proxies: tuple
    digest: str

    def allows(self, ip):
        return evaluate_ip(ip, self.allowlist, self.blocklist, self.allowlist_only)


def environment_snapshot():
    try:
        mode = settings.HMS_IP_ALLOWLIST_ONLY
        if type(mode) is not bool:
            raise ValueError()
        allowlist = _rules(settings.HMS_IP_ALLOWLIST)
        blocklist = _rules(settings.HMS_IP_BLOCKLIST)
        proxies = _rules(settings.HMS_TRUSTED_PROXIES)
        raw_owner = getattr(settings, 'HMS_SECURITY_ORGANISATION_ID', '')
        owner = configured_owner()
        descriptor = {'status': 'valid', 'value': str(owner)} if owner else {'status': 'missing'} if raw_owner == '' else {'status': 'invalid', 'value_digest': hashlib.sha256(str(raw_owner).encode()).hexdigest()}
        fingerprint = digest({'allowlist_only': mode, 'allowlist': allowlist, 'blocklist': blocklist, 'trusted_proxies': proxies, 'owner': descriptor})
        return EnvironmentSnapshot(mode, allowlist, blocklist, proxies, fingerprint)
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise NetworkStateUnavailable() from None


def overlay_allows(policy, ip):
    return evaluate_ip(ip, policy['allowlist'], policy['blocklist'], policy['allowlist_only'])


@dataclass(frozen=True)
class NetworkDecision:
    verified_ip: str | None
    allowed: bool
    environment_allows: bool
    environment_digest: str


def network_decision(remote_addr, forwarded_for, now=None):
    environment = environment_snapshot()
    try:
        ip = normalise_client_ip(remote_addr, forwarded_for, environment.trusted_proxies)
    except (ValueError, TypeError):
        return NetworkDecision(None, False, False, environment.digest)
    if not environment.allows(ip):
        return NetworkDecision(ip, False, False, environment.digest)
    snapshot = load_network_snapshot(now or timezone.now())
    return NetworkDecision(ip, overlay_allows(snapshot.effective_policy, ip), True, environment.digest)
