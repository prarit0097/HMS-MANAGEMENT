"""Frozen S1 facts-only contract; synthetic fixtures, no Django or IO."""

import dataclasses
import json
import traceback
import unittest
from datetime import datetime, timezone
from uuid import UUID

from apps.core.document_guard_record import GuardRecordFacts, parse_guard_record


VALID = (
    b'{"version":1,"installation_id":"12345678-1234-1234-1234-123456789abc",'
    b'"epoch":"00000000-0000-0000-0000-000000000000","mode":"active",'
    b'"reason":"fresh","recorded_at":"2026-11-13T08:09:10.123456Z",'
    b'"manifest_sha256":null}'
)
HASH = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


class BytesSubclass(bytes):
    pass


class StrSubclass(str):
    pass


class GuardRecordTests(unittest.TestCase):
    def altered(self, **changes):
        fields = json.loads(VALID)
        fields.update(changes)
        return json.dumps(fields, separators=(",", ":")).encode("utf-8")

    def invalid(self, raw):
        try:
            parse_guard_record(raw)
        except ValueError as error:
            self.assertIs(type(error), ValueError)
            self.assertEqual(error.args, ("Invalid guard record.",))
            self.assertIsNone(error.__cause__)
            self.assertTrue(error.__context__ is None or error.__suppress_context__)
            rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            self.assertNotIn("During handling of the above exception", rendered)
            self.assertNotIn("direct cause of the following exception", rendered)
        else:
            self.fail("Invalid input accepted")

    def test_literal_fixture_returns_typed_immutable_facts(self):
        facts = parse_guard_record(VALID)
        self.assertIs(type(facts), GuardRecordFacts)
        self.assertEqual(facts.version, 1)
        self.assertIs(type(facts.version), int)
        self.assertEqual(facts.installation_id, UUID("12345678-1234-1234-1234-123456789abc"))
        self.assertEqual(facts.epoch, UUID("00000000-0000-0000-0000-000000000000"))
        self.assertIs(type(facts.installation_id), UUID)
        self.assertIs(type(facts.epoch), UUID)
        self.assertEqual(facts.mode, "active")
        self.assertEqual(facts.reason, "fresh")
        self.assertEqual(facts.recorded_at, datetime(2026, 11, 13, 8, 9, 10, 123456, tzinfo=timezone.utc))
        self.assertIs(facts.recorded_at.tzinfo, timezone.utc)
        self.assertIsNone(facts.manifest_sha256)
        self.assertEqual(
            [field.name for field in dataclasses.fields(facts)],
            ["version", "installation_id", "epoch", "mode", "reason", "recorded_at", "manifest_sha256"],
        )
        for field in dataclasses.fields(facts):
            with self.subTest(field=field.name), self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(facts, field.name, None)

    def test_all_six_modes_and_both_manifest_shapes_are_facts_only(self):
        for mode in ("active", "closed"):
            for reason in ("fresh", "maintenance", "restore"):
                for manifest in (None, HASH):
                    with self.subTest(mode=mode, reason=reason, manifest=manifest):
                        facts = parse_guard_record(self.altered(mode=mode, reason=reason, manifest_sha256=manifest))
                        self.assertEqual((facts.mode, facts.reason, facts.manifest_sha256), (mode, reason, manifest))
                        self.assertFalse(hasattr(facts, "allowed"))
                        self.assertFalse(hasattr(facts, "authorize"))
                        self.assertFalse(hasattr(facts, "invocation_id"))
        direct = GuardRecordFacts(1, UUID(int=0), UUID(int=0), "active", "restore", datetime(1, 1, 1, tzinfo=timezone.utc), None)
        self.assertFalse(hasattr(direct, "allowed"))

    def test_json_whitespace_reordering_and_escaped_keys_and_values_are_allowed(self):
        raw = (
            b' \r\n\t{"manifest_sha256":null,"recorded_at":"2026-11-13T08:09:10.123456Z",'
            b'"reason":"fr\\u0065sh","mode":"act\\u0069ve",'
            b'"epoch":"00000000-0000-0000-0000-000000000000",'
            b'"installation_id":"12345678-1234-1234-1234-123456789abc","ver\\u0073ion":1} \r\n\t'
        )
        self.assertEqual(parse_guard_record(raw), parse_guard_record(VALID))

    def test_exact_byte_size_boundaries(self):
        self.invalid(b"")
        self.invalid(b"1")  # One byte passes the length gate, fails the object contract.
        self.assertEqual(parse_guard_record(VALID + b" " * (4096 - len(VALID))), parse_guard_record(VALID))
        self.invalid(VALID + b" " * (4097 - len(VALID)))
        unicode_raw = self.altered(manifest_sha256="é" * 2000)
        # json.dumps defaults to escapes; construct actual multibyte UTF-8 deliberately.
        unicode_raw = unicode_raw.replace(b"\\u00e9", "é".encode("utf-8"))
        self.assertLess(len(unicode_raw.decode("utf-8")), 4096)
        self.assertGreater(len(unicode_raw), 4096)
        self.invalid(unicode_raw)

    def test_raw_input_requires_exact_bytes_without_coercion(self):
        for raw in (None, True, 1, 1.0, VALID.decode(), StrSubclass(VALID.decode()), bytearray(VALID), memoryview(VALID), BytesSubclass(VALID), [], {}, (VALID,)):
            with self.subTest(raw_type=type(raw).__name__):
                self.invalid(raw)

    def test_invalid_encoding_syntax_and_trailing_data(self):
        for raw in (b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xef\xbb\xbf" + VALID, b"{", VALID[:-1], VALID + b"{}", VALID + b"x", VALID + b"\x00", b'{"version":01}', b'{"version":1,}', VALID.replace(b'"active"', b'"act\nive"')):
            with self.subTest(raw=raw[:24]):
                self.invalid(raw)

    def test_nonobject_roots(self):
        for raw in (b"null", b"true", b"false", b"1", b"1.0", b'"text"', b"[]", b"[{}]"):
            with self.subTest(raw=raw):
                self.invalid(raw)

    def test_every_member_is_required_and_extra_member_is_rejected(self):
        original = json.loads(VALID)
        for key in original:
            fields = dict(original)
            del fields[key]
            with self.subTest(missing=key):
                self.invalid(json.dumps(fields).encode())
        self.invalid(self.altered(extra="synthetic-marker"))

    def test_duplicate_keys_are_rejected_including_escaped_and_nested_keys(self):
        for suffix in (b',"version":1}', b',"ver\\u0073ion":1}', b',"mode":"closed"}'):
            with self.subTest(suffix=suffix):
                self.invalid(VALID[:-1] + suffix)
        for nested in (b'{"x":1,"x":2}', b'{"x":1,"\\u0078":2}', b'[{"x":1,"x":2}]'):
            self.invalid(VALID.replace(b'"manifest_sha256":null', b'"manifest_sha256":' + nested))

    def test_bounded_deep_json_is_normalized(self):
        for depth in (1100, 1900):
            raw = b"[" * depth + b"0" + b"]" * depth
            self.assertLessEqual(len(raw), 4096)
            self.invalid(raw)

    def test_decoded_fields_never_coerce_wrong_json_types(self):
        for field in json.loads(VALID):
            for value in (True, False, 0, 1, 1.0, None, [], {}, ["active"], {"x": "active"}):
                if field == "version" and type(value) is int and value == 1:
                    continue
                if field == "manifest_sha256" and value is None:
                    continue
                with self.subTest(field=field, value=value):
                    self.invalid(self.altered(**{field: value}))

    def test_only_integer_version_one_is_accepted(self):
        for value in (0, 2, -1, 1.0, True, "1", 10**100):
            with self.subTest(value=value):
                self.invalid(self.altered(version=value))

    def test_nonfinite_constants_and_overflow_numbers_are_rejected_in_every_field(self):
        for field in json.loads(VALID):
            for token in (b"NaN", b"Infinity", b"-Infinity", b"1e9999", b"-1e9999"):
                raw = self.altered(**{field: "TOKEN"}).replace(b'"TOKEN"', token)
                with self.subTest(field=field, token=token):
                    self.invalid(raw)

    def test_uuids_require_canonical_decoded_spelling_without_version_restriction(self):
        for field in ("installation_id", "epoch"):
            for value in ("12345678-1234-1234-1234-123456789ABC", "12345678123412341234123456789abc", "{12345678-1234-1234-1234-123456789abc}", "urn:uuid:12345678-1234-1234-1234-123456789abc", " 12345678-1234-1234-1234-123456789abc", "12345678-1234-1234-1234-123456789abc\n", "12345678-1234-1234-1234-123456789abg", "", "é" * 36):
                with self.subTest(field=field, value=value):
                    self.invalid(self.altered(**{field: value}))
            facts = parse_guard_record(self.altered(**{field: "ffffffff-ffff-ffff-ffff-ffffffffffff"}))
            self.assertEqual(getattr(facts, field), UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))

    def test_mode_and_reason_require_exact_enums(self):
        for field, values in (("mode", ("ACTIVE", "Active", "closed ", "", "restore", "active\n")), ("reason", ("Fresh", "RESTORE", "maintenance ", "", "active", "fresh\n"))):
            for value in values:
                with self.subTest(field=field, value=value):
                    self.invalid(self.altered(**{field: value}))

    def test_timestamp_accepts_gregorian_extremes_and_leap_day(self):
        for value, expected in (
            ("0001-01-01T00:00:00.000000Z", datetime(1, 1, 1, tzinfo=timezone.utc)),
            ("9999-12-31T23:59:59.999999Z", datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)),
            ("2000-02-29T12:34:56.000001Z", datetime(2000, 2, 29, 12, 34, 56, 1, tzinfo=timezone.utc)),
        ):
            with self.subTest(value=value):
                self.assertEqual(parse_guard_record(self.altered(recorded_at=value)).recorded_at, expected)

    def test_timestamp_requires_ascii_six_fraction_utc_and_real_calendar(self):
        for value in (
            "0000-01-01T00:00:00.000000Z", "10000-01-01T00:00:00.000000Z",
            "1900-02-29T00:00:00.000000Z", "2026-02-29T00:00:00.000000Z",
            "2026-04-31T00:00:00.000000Z", "2026-00-01T00:00:00.000000Z",
            "2026-13-01T00:00:00.000000Z", "2026-01-00T00:00:00.000000Z",
            "2026-01-01T24:00:00.000000Z", "2026-01-01T00:60:00.000000Z",
            "2026-01-01T00:00:60.000000Z", "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00.0Z", "2026-01-01T00:00:00.00000Z",
            "2026-01-01T00:00:00.0000000Z", "2026-01-01T00:00:00.000000z",
            "2026-01-01T00:00:00.000000+00:00", "2026-01-01T00:00:00.000000+01:00",
            "2026-01-01 00:00:00.000000Z", "2026-01-01t00:00:00.000000Z",
            "2026-1-01T00:00:00.000000Z", "2026-01-01T00:00:00,000000Z",
            "２０２６-01-01T00:00:00.000000Z", "2026-01-01T00:00:00.٠٠٠٠٠٠Z",
            "2026-01-01T00:00:00.000000Z\n", " 2026-01-01T00:00:00.000000Z", "",
        ):
            with self.subTest(value=value):
                self.invalid(self.altered(recorded_at=value))

    def test_manifest_requires_64_lowercase_ascii_hex_or_null(self):
        for value in (HASH.upper(), HASH[:-1], HASH + "0", "g" * 64, "é" * 64, "０" * 64, HASH + "\n", " " + HASH, ""):
            with self.subTest(value=value):
                self.invalid(self.altered(manifest_sha256=value))


if __name__ == "__main__":
    unittest.main()
