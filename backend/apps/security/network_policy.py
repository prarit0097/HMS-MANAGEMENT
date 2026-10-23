"""Pure bounded policy parsing and immutable saved-snapshot validation.

These helpers do not select effective policy or activate request enforcement.
Invalid input or saved state raises ValueError; callers map that failure at
their own boundary. Network parsing deliberately reuses the resolver's mapped
IPv6 semantics without changing the existing runtime evaluator.
"""

from hashlib import sha256
from hmac import compare_digest
import json

from .ip_policy import _network


def _canonical_rules(value: object) -> list[str]:
    if type(value) is not list or len(value) > 100:
        raise ValueError("Policy rules must be a list of at most 100 entries")
    networks = set()
    for raw in value:
        if type(raw) is not str or not 1 <= len(raw) <= 64:
            raise ValueError("Policy rule must contain 1 to 64 ASCII characters")
        if any(not (32 <= ord(char) <= 126 or char == "\t") for char in raw):
            raise ValueError("Policy rule contains invalid characters")
        rule = raw.strip(" \t")
        if not rule:
            raise ValueError("Policy rule cannot be empty")
        if "/" in rule:
            prefix = rule.split("/", 1)[1]
            if not 1 <= len(prefix) <= 3 or any(char not in "0123456789" for char in prefix):
                raise ValueError("CIDR prefix must contain 1 to 3 ASCII digits")
        networks.add(_network(rule))
    ordered = sorted(networks, key=lambda item: (item.version, int(item.network_address), item.prefixlen))
    return [str(network) for network in ordered]


def canonical_policy(value: object) -> dict:
    """Validate an input policy and return detached canonical JSON data."""
    if type(value) is not dict or set(value) != {"allowlist_only", "allowlist", "blocklist"}:
        raise ValueError("Policy must contain exactly allowlist_only, allowlist and blocklist")
    if type(value["allowlist_only"]) is not bool:
        raise ValueError("allowlist_only must be a boolean")
    allowed = _canonical_rules(value["allowlist"])
    blocked = _canonical_rules(value["blocklist"])
    if value["allowlist_only"] and not allowed:
        raise ValueError("Allowlist-only policy requires an allowed network")
    return {"allowlist_only": value["allowlist_only"], "allowlist": allowed, "blocklist": blocked}


def _require_canonical(value: object) -> dict:
    result = canonical_policy(value)
    if result != value:
        raise ValueError("Saved policy must already be canonical")
    return result


def _digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def policy_digest(canonical_policy: dict) -> str:
    """Hash strict canonical policy, refusing to silently repair stored data."""
    return _digest(_require_canonical(canonical_policy))


def validate_saved_policy(value: object, digest: str) -> dict:
    """Return a detached validated canonical snapshot with matching SHA256."""
    if type(digest) is not str or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("Policy digest must be 64 lowercase hexadecimal characters")
    result = _require_canonical(value)
    if not compare_digest(_digest(result), digest):
        raise ValueError("Policy digest does not match saved policy")
    return result
