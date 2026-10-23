"""Pure Stage B1 policy grammar and immutable saved-snapshot checks."""

from copy import deepcopy
from hashlib import sha256
from importlib import import_module, util
import json
import unittest


class NetworkPolicyTests(unittest.TestCase):
    def setUp(self):
        # Fail as an assertion while the RED-first feature does not yet exist.
        self.assertIsNotNone(
            util.find_spec("apps.security.network_policy"),
            "Stage B1 network_policy helpers have not been implemented",
        )
        self.module = import_module("apps.security.network_policy")
        self.empty = {"allowlist_only": False, "allowlist": [], "blocklist": []}

    def test_empty_non_strict_policy_is_valid_and_returns_detached_data(self):
        result = self.module.canonical_policy(self.empty)
        self.assertEqual(result, self.empty)
        self.assertIsNot(result, self.empty)
        self.assertIsNot(result["allowlist"], self.empty["allowlist"])
        self.assertIsNot(result["blocklist"], self.empty["blocklist"])

    def test_exact_cidr_mapped_rules_sort_and_deduplicate_without_merging(self):
        value = {
            "allowlist_only": True,
            "allowlist": [
                "2001:0DB8::0001", "192.0.2.9/24", "::ffff:192.0.2.7/120",
                "192.0.2.1", "\t 192.0.2.1/32 \t", "192.0.2.0/25", "::1",
            ],
            "blocklist": ["::ffff:198.51.100.8", "198.51.100.8/32"],
        }
        original = deepcopy(value)
        self.assertEqual(self.module.canonical_policy(value), {
            "allowlist_only": True,
            "allowlist": ["192.0.2.0/24", "192.0.2.0/25", "192.0.2.1/32", "::1/128", "2001:db8::1/128"],
            "blocklist": ["198.51.100.8/32"],
        })
        self.assertEqual(value, original)

    def test_dual_family_wildcards_and_mapped_zero_prefix_are_valid(self):
        value = dict(self.empty, allowlist_only=True, allowlist=["::/0", "::ffff:0.0.0.0/96", "0.0.0.0/0"])
        self.assertEqual(self.module.canonical_policy(value)["allowlist"], ["0.0.0.0/0", "::/0"])

    def test_mapped_prefix_below_96_is_rejected_even_with_other_valid_rule(self):
        for rule in ("::ffff:192.0.2.1/95", "::ffff:c000:201/0"):
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                self.module.canonical_policy(dict(self.empty, blocklist=["192.0.2.1", rule]))

    def test_exact_object_shape_is_required(self):
        class DictSubclass(dict):
            pass

        for value in (None, [], (), "{}", 1, True, {}, {"allowlist_only": False},
                      dict(self.empty, extra=[]), DictSubclass(self.empty)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.canonical_policy(value)
        for key in self.empty:
            value = deepcopy(self.empty)
            del value[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.module.canonical_policy(value)

    def test_only_json_booleans_are_valid(self):
        for value in (0, 1, None, "false", "true", [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.canonical_policy(dict(self.empty, allowlist_only=value))

    def test_lists_and_string_entries_are_strict(self):
        for field in ("allowlist", "blocklist"):
            for value in (None, (), set(), "192.0.2.1", {}, 1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.module.canonical_policy(dict(self.empty, **{field: value}))
            for rule in (None, 123, True, [], {}, b"192.0.2.1"):
                with self.subTest(field=field, rule=rule), self.assertRaises(ValueError):
                    self.module.canonical_policy(dict(self.empty, **{field: [rule]}))

    def test_rule_count_is_bounded_before_deduplication_on_both_lists(self):
        for field in ("allowlist", "blocklist"):
            accepted = self.module.canonical_policy(dict(self.empty, **{field: ["192.0.2.1"] * 100}))
            self.assertEqual(accepted[field], ["192.0.2.1/32"])
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.module.canonical_policy(dict(self.empty, **{field: ["192.0.2.1"] * 101}))
        both = dict(self.empty, allowlist=[f"192.0.2.{n}" for n in range(100)], blocklist=[f"198.51.100.{n}" for n in range(100)])
        result = self.module.canonical_policy(both)
        self.assertEqual(len(result["allowlist"]), 100)
        self.assertEqual(len(result["blocklist"]), 100)

    def test_raw_rule_length_is_bounded_before_ascii_space_tab_trim(self):
        rule = "192.0.2.1"
        self.assertEqual(self.module.canonical_policy(dict(self.empty, allowlist=[rule + " " * (64 - len(rule))]))["allowlist"], ["192.0.2.1/32"])
        for value in ("", " ", "\t", " \t ", rule + " " * (65 - len(rule))):
            with self.subTest(rule=value), self.assertRaises(ValueError):
                self.module.canonical_policy(dict(self.empty, allowlist=[value]))

    def test_rule_controls_non_ascii_and_non_ip_forms_are_rejected(self):
        invalid = [
            "192.0.2.1\r", "192.0.2.1\n", "192.0.2.1\r\n", "192.0.2.\t1",
            "192.0.2.1\x00", "192.0.2.1\x1f", "192.0.2.1\x7f", "\v192.0.2.1",
            "\f192.0.2.1", "\u00a0192.0.2.1", "１９２.0.2.1", "fe80::1%eth0",
            "fe80::1%1/64", "192.0.2.1:443", "[::1]:443", "[::1]", "localhost",
            "192.0.2.1 #comment", "192.0.2.1,198.51.100.1", "127.1", "010.0.0.1",
            "192.0.2.1/33", "::1/129", "192.0.2.1//32", "192.0.2.1/ 32",
            "192.0.2.1/255.255.255.0", "192.0.2.1/0.0.0.255", "192.0.2.1/+24",
            "192.0.2.1/-1", "192.0.2.1/", "192.0.2.1/24/", "192.0.2.1/00024",
        ]
        for field in ("allowlist", "blocklist"):
            for rule in invalid:
                with self.subTest(field=field, rule=rule), self.assertRaises(ValueError):
                    self.module.canonical_policy(dict(self.empty, **{field: [rule]}))

    def test_one_to_three_ascii_prefix_digits_allow_leading_zeroes(self):
        value = dict(self.empty, allowlist=["192.0.2.1/024", "2001:db8::1/064"])
        self.assertEqual(self.module.canonical_policy(value)["allowlist"], ["192.0.2.0/24", "2001:db8::/64"])

    def test_strict_mode_requires_nonempty_allowlist(self):
        with self.assertRaises(ValueError):
            self.module.canonical_policy(dict(self.empty, allowlist_only=True, blocklist=["::/0"]))

    def test_digest_uses_exact_deterministic_json_bytes(self):
        expected = sha256(b'{"allowlist":[],"allowlist_only":false,"blocklist":[]}').hexdigest()
        self.assertEqual(self.module.policy_digest(self.empty), expected)
        reordered_keys = {"blocklist": [], "allowlist": [], "allowlist_only": False}
        self.assertEqual(self.module.policy_digest(reordered_keys), expected)

    def test_digest_refuses_noncanonical_or_invalid_policy(self):
        invalid = [
            dict(self.empty, allowlist=["192.0.2.1"]),
            dict(self.empty, allowlist=["192.0.2.9/24"]),
            dict(self.empty, allowlist=[" 192.0.2.1/32"]),
            dict(self.empty, allowlist=["::ffff:192.0.2.1/128"]),
            dict(self.empty, allowlist=["2001:0DB8::1/128"]),
            dict(self.empty, allowlist=["192.0.2.1/32", "192.0.2.1/32"]),
            dict(self.empty, allowlist=["::1/128", "192.0.2.1/32"]),
            dict(self.empty, allowlist_only=0),
            dict(self.empty, allowlist_only=True), None,
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.policy_digest(value)

    def test_saved_policy_validates_digest_and_returns_detached_snapshot(self):
        value = dict(self.empty, allowlist=["192.0.2.0/24"], blocklist=["192.0.2.1/32"])
        digest = self.module.policy_digest(value)
        result = self.module.validate_saved_policy(value, digest)
        self.assertEqual(result, value)
        result["blocklist"].clear()
        self.assertEqual(value["blocklist"], ["192.0.2.1/32"])

    def test_saved_policy_rejects_malformed_digest_and_tampered_rules(self):
        digest = self.module.policy_digest(self.empty)
        for value in (None, 1, b"a" * 64, "", "a" * 63, "a" * 65, "g" * 64, digest.upper(), digest + "\n", " " + digest):
            with self.subTest(digest=value), self.assertRaises(ValueError):
                self.module.validate_saved_policy(self.empty, value)
        with self.assertRaises(ValueError):
            self.module.validate_saved_policy(dict(self.empty, blocklist=["192.0.2.1/32"]), digest)

    def test_saved_policy_rejects_noncanonical_state_even_with_its_own_hash(self):
        values = [
            dict(self.empty, allowlist=["192.0.2.1"]),
            dict(self.empty, allowlist=["::ffff:192.0.2.1/128"]),
            dict(self.empty, allowlist=["192.0.2.1/32", "192.0.2.1/32"]),
            dict(self.empty, allowlist=["::1/128", "192.0.2.1/32"]),
            dict(self.empty, allowlist_only=0),
            dict(self.empty, allowlist=["192.0.2.1/32"] * 101),
        ]
        for value in values:
            # A hash alone must never make corrupt/noncanonical state valid.
            digest = sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.validate_saved_policy(value, digest)
