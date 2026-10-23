"""Strict, framework-independent client resolution and IP allow/deny rules.

The caller must deny requests when resolution raises ``ValueError``. This
module does not establish the edge firewall or make a proxy trustworthy:
trusted proxies must overwrite/append the actual peer at the edge boundary.
"""

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network

IPAddress = IPv4Address | IPv6Address
IPNetwork = IPv4Network | IPv6Network


def _address(value: str) -> IPAddress:
    if not isinstance(value, str) or "%" in value:
        raise ValueError("Invalid IP address")
    parsed = ip_address(value)
    if isinstance(parsed, IPv6Address) and parsed.ipv4_mapped is not None:
        return parsed.ipv4_mapped
    return parsed


def _network(value: str) -> IPNetwork:
    if not isinstance(value, str) or "%" in value:
        raise ValueError("Invalid network rule")
    parsed = ip_network(value, strict=False)
    if isinstance(parsed, IPv6Network):
        original = ip_address(value.split("/", 1)[0])
        if isinstance(original, IPv6Address) and original.ipv4_mapped is not None:
            if parsed.prefixlen < 96:
                raise ValueError("Mapped IPv6 network must have prefix length >= 96")
            return IPv4Network((int(parsed.network_address.ipv4_mapped), parsed.prefixlen - 96))
    return parsed


def normalise_client_ip(
    remote_addr: str, forwarded_for: str | None, trusted_proxies: tuple[str, ...]
) -> str:
    """Return the first untrusted peer from the right of a trusted chain.

    An untrusted socket peer cannot supply authoritative forwarded headers.
    With a trusted peer, malformed entries anywhere in the header deny rather
    than being skipped. A missing header uses the actual peer. Header work is
    bounded to 64 hops / 8192 characters; no address is automatically trusted.
    """
    peer = _address(remote_addr)
    trusted = tuple(_network(rule) for rule in trusted_proxies)
    if not any(peer in network for network in trusted) or forwarded_for is None:
        return str(peer)
    if not isinstance(forwarded_for, str) or len(forwarded_for) > 8192:
        raise ValueError("Invalid forwarded IP chain")
    if "\r" in forwarded_for or "\n" in forwarded_for:
        raise ValueError("Invalid forwarded IP chain")
    tokens = forwarded_for.split(",")
    if len(tokens) > 64:
        raise ValueError("Too many forwarded IP addresses")
    chain = [_address(token.strip(" \t")) for token in tokens]
    chain.append(peer)
    while len(chain) > 1 and any(chain[-1] in network for network in trusted):
        chain.pop()
    return str(chain[-1])


def evaluate_ip(
    address: str, allowlist: list[str], blocklist: list[str], allowlist_only: bool
) -> bool:
    """Evaluate a policy ceiling; malformed input or configuration denies.

    All rules are validated before a match is considered. IPv4-mapped IPv6
    addresses and mapped rules use their equivalent IPv4 identity, so a mapped
    representation cannot evade an IPv4 block. Native IPv6 rules match native
    IPv6; a dual-stack wildcard requires both IPv4 and IPv6 networks.
    """
    try:
        peer = _address(address)
        allowed = tuple(_network(rule) for rule in allowlist)
        blocked = tuple(_network(rule) for rule in blocklist)
    except (ValueError, TypeError):
        return False
    if any(peer in network for network in blocked):
        return False
    return not allowlist_only or any(peer in network for network in allowed)
