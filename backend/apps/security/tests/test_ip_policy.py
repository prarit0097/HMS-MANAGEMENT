"""Hand-checked threat cases for the resolver and effective IP policy."""

import unittest

from apps.security import evaluate_ip, normalise_client_ip


class ClientIPTests(unittest.TestCase):
    def test_direct_peer_ignores_spoofed_forwarded_header(self):
        self.assertEqual(
            normalise_client_ip("203.0.113.5", "192.0.2.1", ("10.0.0.0/8",)),
            "203.0.113.5",
        )

    def test_direct_peer_ignores_even_malformed_untrusted_header(self):
        self.assertEqual(normalise_client_ip("203.0.113.5", "spoof,,", ()), "203.0.113.5")

    def test_trusted_proxy_uses_client_address(self):
        self.assertEqual(
            normalise_client_ip("10.0.0.4", " 203.0.113.5 ", ("10.0.0.0/8",)),
            "203.0.113.5",
        )

    def test_trusted_proxy_strips_chain_from_right_not_spoofable_left(self):
        self.assertEqual(
            normalise_client_ip(
                "10.0.0.4", "192.0.2.77, 203.0.113.5, 10.0.0.3", ("10.0.0.0/8",)
            ),
            "203.0.113.5",
        )

    def test_untrusted_intermediate_ends_trust_even_if_left_client_is_allowed(self):
        self.assertEqual(
            normalise_client_ip("10.0.0.4", "192.0.2.77, 198.51.100.9", ("10.0.0.0/8",)),
            "198.51.100.9",
        )

    def test_ipv6_chain_and_exact_proxy_address(self):
        self.assertEqual(
            normalise_client_ip("2001:db8:1::2", "2001:0db8:2::0005", ("2001:db8:1::2",)),
            "2001:db8:2::5",
        )

    def test_ipv4_mapped_peer_and_proxy_rule_use_ipv4_identity(self):
        self.assertEqual(
            normalise_client_ip("::ffff:10.0.0.4", "::ffff:203.0.113.5", ("::ffff:10.0.0.0/104",)),
            "203.0.113.5",
        )

    def test_all_trusted_hops_return_leftmost_address(self):
        self.assertEqual(
            normalise_client_ip("10.0.0.4", "10.0.0.1, 10.0.0.3", ("10.0.0.0/8",)),
            "10.0.0.1",
        )

    def test_missing_header_uses_actual_peer_without_inventing_client(self):
        self.assertEqual(normalise_client_ip("10.0.0.4", None, ("10.0.0.0/8",)), "10.0.0.4")

    def test_malformed_trusted_chain_is_rejected_in_entirety(self):
        for forwarded in ("", "unknown", "203.0.113.5,", ",203.0.113.5", "invalid, 203.0.113.5", "[::1]:80", "203.0.113.5:80", "fe80::1%eth0", "203.0.113.5\r\n"):
            with self.subTest(forwarded=forwarded), self.assertRaises(ValueError):
                normalise_client_ip("10.0.0.4", forwarded, ("10.0.0.0/8",))

    def test_malformed_peer_and_proxy_configuration_are_rejected(self):
        for peer in ("", "unknown", "127.1", "010.0.0.1", "203.0.113.5:80", "fe80::1%eth0"):
            with self.subTest(peer=peer), self.assertRaises(ValueError):
                normalise_client_ip(peer, None, ())
        with self.assertRaises(ValueError):
            normalise_client_ip("203.0.113.5", None, ("not-an-address",))

    def test_oversized_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_client_ip("10.0.0.4", ",".join(["203.0.113.5"] * 65), ("10.0.0.0/8",))


class IPPolicyTests(unittest.TestCase):
    def test_authenticated_mode_allows_unlisted_valid_address(self):
        self.assertIs(evaluate_ip("203.0.113.5", [], [], False), True)

    def test_allowlist_only_fails_closed_with_empty_allowlist(self):
        self.assertIs(evaluate_ip("203.0.113.5", [], [], True), False)

    def test_exact_allowlist_and_cidr_boundaries(self):
        for address, expected in (("192.0.2.7", True), ("192.0.2.8", False), ("192.0.2.0", True), ("192.0.2.6", True)):
            with self.subTest(address=address):
                self.assertIs(evaluate_ip(address, ["192.0.2.0/29"], [], True), expected)
        self.assertIs(evaluate_ip("203.0.113.5", ["203.0.113.5"], [], True), True)
        self.assertIs(evaluate_ip("203.0.113.6", ["203.0.113.5"], [], True), False)

    def test_blocklist_overrides_allowlist(self):
        self.assertIs(evaluate_ip("203.0.113.5", ["203.0.113.0/24"], ["203.0.113.5"], True), False)
        self.assertIs(evaluate_ip("203.0.113.5", [], ["203.0.113.0/24"], False), False)

    def test_ipv6_network_and_family_mismatch(self):
        self.assertIs(evaluate_ip("2001:0db8:1::5", ["2001:db8:1::/64"], [], True), True)
        self.assertIs(evaluate_ip("2001:db8:2::5", ["2001:db8:1::/64"], [], True), False)
        self.assertIs(evaluate_ip("203.0.113.5", ["2001:db8::/32"], [], True), False)

    def test_ipv4_mapped_ipv6_cannot_evade_ipv4_deny(self):
        self.assertIs(evaluate_ip("::ffff:203.0.113.5", ["0.0.0.0/0"], ["203.0.113.0/24"], True), False)

    def test_mapped_allow_and_deny_rules_match_ipv4_clients(self):
        self.assertIs(evaluate_ip("203.0.113.5", ["::ffff:203.0.113.0/120"], [], True), True)
        self.assertIs(evaluate_ip("203.0.113.5", [], ["::ffff:203.0.113.5"], False), False)

    def test_invalid_policy_entry_fails_closed_even_if_later_rule_matches(self):
        self.assertIs(evaluate_ip("203.0.113.5", ["203.0.113.5", "broken"], [], True), False)
        self.assertIs(evaluate_ip("203.0.113.5", [], ["broken"], False), False)
        self.assertIs(evaluate_ip("203.0.113.5", ["broken"], [], False), False)

    def test_malformed_address_is_denied_without_raising(self):
        for address in ("", "invalid", "203.0.113.5:80", "fe80::1%eth0", "203.0.113.5\n", "010.0.0.1"):
            with self.subTest(address=address):
                self.assertIs(evaluate_ip(address, ["0.0.0.0/0", "::/0"], [], False), False)

    def test_host_bits_in_configured_cidr_are_normalised(self):
        self.assertIs(evaluate_ip("203.0.113.200", ["203.0.113.5/24"], [], True), True)


if __name__ == "__main__":
    unittest.main()
