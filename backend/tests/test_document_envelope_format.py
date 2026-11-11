"""Portable S0 shape-only contract; synthetic vectors, no Django or cryptography."""

import unittest
from uuid import UUID

from apps.core.document_envelope_format import (
    encode_aad,
    encode_header,
    validate_envelope_shape,
)


ERROR = "Invalid document envelope format."
MAX_SIZE = 10485760
FACTS = {
    "organisation_id": UUID("00112233-4455-6677-8899-aabbccddeeff"),
    "patient_id": UUID("10213243-5465-7687-98a9-bacbdcedfe0f"),
    "intent_id": UUID("20314253-6475-8697-a8b9-cadbecfd0e1f"),
    "generation_id": UUID("30415263-7485-96a7-b8c9-daebfc0d1e2f"),
    "size_bytes": 1,
    "sha256": bytes(range(32)),
    "media_type": "image/jpeg",
    "seal_key_id": "K_9-",
}
NONCE = bytes(range(12))

# Hand-laid fields in wire order, without struct or production helpers. The
# four SHA256 results in HEADERS are literal known answers, not runtime oracles.
AAD_PREFIX = bytes.fromhex(
    "484d53444f4330310001"
    "00112233445566778899aabbccddeeff"
    "102132435465768798a9bacbdcedfe0f"
    "2031425364758697a8b9cadbecfd0e1f"
    "30415263748596a7b8c9daebfc0d1e2f"
)
DIGEST_HEX = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
KEY_PAD = bytes.fromhex(
    "4b5f392d"
    "0000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000"
)
SIZE_WIRE = {1: bytes.fromhex("0000000000000001"), MAX_SIZE: bytes.fromhex("0000000000a00000")}
MEDIA_WIRE = {"image/jpeg": b"\x01\x04", "image/png": b"\x02\x04"}
HEADERS = {
    ("image/jpeg", 1): bytes.fromhex(
        "484d53454e433031000130415263748596a7b8c9daebfc0d1e2f"
        "000102030405060708090a0b0000000000000001"
        "3a9fafc2037f9699ee861eb502c570bbbf2b2920e5132816e07a5fb23e318142"
    ),
    ("image/jpeg", MAX_SIZE): bytes.fromhex(
        "484d53454e433031000130415263748596a7b8c9daebfc0d1e2f"
        "000102030405060708090a0b0000000000a00000"
        "81969c89fb43a6b158af49008827711044cbde9ecda3f19f39e9a33b98f2ae96"
    ),
    ("image/png", 1): bytes.fromhex(
        "484d53454e433031000130415263748596a7b8c9daebfc0d1e2f"
        "000102030405060708090a0b0000000000000001"
        "5d741d833bc4995095acf95904aabe66baa0f41f6bcb33e5062be5369009ed5e"
    ),
    ("image/png", MAX_SIZE): bytes.fromhex(
        "484d53454e433031000130415263748596a7b8c9daebfc0d1e2f"
        "000102030405060708090a0b0000000000a00000"
        "7bba75e7312756d61d55235e1567eb42adc3bbb9a1580124bc36bf81942306a6"
    ),
}
HEADER = HEADERS[("image/jpeg", 1)]
ENVELOPE = HEADER + b"\x91" + b"\xa5" * 16


class IntSubclass(int):
    pass


class BytesSubclass(bytes):
    pass


class StrSubclass(str):
    pass


class UUIDSubclass(UUID):
    pass


class Coercible:
    def __int__(self):
        raise AssertionError("must not coerce integers")

    def __bytes__(self):
        raise AssertionError("must not coerce bytes")

    def __str__(self):
        raise AssertionError("must not coerce strings")


class DocumentEnvelopeFormatTests(unittest.TestCase):
    def assert_invalid(self, function, *args, **kwargs):
        with self.assertRaises(ValueError) as caught:
            function(*args, **kwargs)
        self.assertEqual(str(caught.exception), ERROR)

    def assert_invalid_fact(self, field, value):
        facts = {**FACTS, field: value}
        for function in (encode_aad, encode_header, validate_envelope_shape):
            with self.subTest(field=field, value_type=type(value).__name__, function=function.__name__):
                if function is encode_aad:
                    self.assert_invalid(function, **facts)
                elif function is encode_header:
                    self.assert_invalid(function, **facts, nonce=NONCE)
                else:
                    self.assert_invalid(function, ENVELOPE, **facts, nonce=NONCE)

    def test_literal_aad_vectors_pin_every_offset_and_both_media_size_boundaries(self):
        for media in MEDIA_WIRE:
            for size in SIZE_WIRE:
                with self.subTest(media=media, size=size):
                    expected = AAD_PREFIX + SIZE_WIRE[size] + bytes.fromhex(DIGEST_HEX) + MEDIA_WIRE[media] + KEY_PAD
                    actual = encode_aad(**{**FACTS, "media_type": media, "size_bytes": size})
                    self.assertIs(type(actual), bytes)
                    self.assertEqual(len(actual), 180)
                    self.assertEqual(actual, expected)
                    self.assertEqual(actual[:10], b"HMSDOC01\x00\x01")
                    self.assertEqual(actual[74:82], SIZE_WIRE[size])
                    self.assertEqual(actual[114:116], MEDIA_WIRE[media])
                    self.assertEqual(actual[116:], KEY_PAD)

    def test_literal_header_vectors_pin_nonce_generation_size_and_aad_digest(self):
        for (media, size), expected in HEADERS.items():
            with self.subTest(media=media, size=size):
                actual = encode_header(**{**FACTS, "media_type": media, "size_bytes": size}, nonce=NONCE)
                self.assertIs(type(actual), bytes)
                self.assertEqual(len(actual), 78)
                self.assertEqual(actual, expected)
                self.assertEqual(actual[:10], b"HMSENC01\x00\x01")
                self.assertEqual(actual[10:26], FACTS["generation_id"].bytes)
                self.assertEqual(actual[26:38], NONCE)
                self.assertEqual(actual[38:46], SIZE_WIRE[size])

    def test_shape_accepts_both_media_at_minimum_and_maximum_with_shared_readonly_view(self):
        for (media, size), header in HEADERS.items():
            with self.subTest(media=media, size=size):
                envelope = header + b"\x00" * (size + 16)
                view = validate_envelope_shape(envelope, **{**FACTS, "media_type": media, "size_bytes": size}, nonce=NONCE)
                self.assertIs(type(view), memoryview)
                self.assertIs(view.obj, envelope)
                self.assertTrue(view.readonly)
                self.assertEqual(len(view), size + 16)
                self.assertEqual(view[0], 0)
                self.assertEqual(view[-1], 0)
                with self.assertRaises(TypeError):
                    view[0] = 1

    def test_returned_view_contains_ciphertext_and_entire_tag(self):
        view = validate_envelope_shape(ENVELOPE, **FACTS, nonce=NONCE)
        self.assertEqual(view.tobytes(), b"\x91" + b"\xa5" * 16)
        self.assertIs(view.obj, ENVELOPE)
        self.assertTrue(view.readonly)

    def test_uuid_type_rejection_applies_to_each_identity_and_all_helpers(self):
        for field in ("organisation_id", "patient_id", "intent_id", "generation_id"):
            for value in (None, str(FACTS[field]), FACTS[field].bytes, 1, True, UUIDSubclass(int=1), Coercible()):
                self.assert_invalid_fact(field, value)

    def test_size_requires_exact_integer_and_closed_bounds(self):
        for value in (0, -1, MAX_SIZE + 1, 2**100, True, False, 1.0, "1", None, IntSubclass(1), Coercible()):
            self.assert_invalid_fact("size_bytes", value)

    def test_digest_requires_exact_immutable_32_bytes(self):
        for value in (b"", b"x" * 31, b"x" * 33, "x" * 32, None, 32, bytearray(32), memoryview(bytes(32)), BytesSubclass(bytes(32)), Coercible()):
            self.assert_invalid_fact("sha256", value)

    def test_nonce_requires_exact_immutable_12_bytes(self):
        for value in (b"", b"x" * 11, b"x" * 13, "x" * 12, None, 12, bytearray(12), memoryview(bytes(12)), BytesSubclass(bytes(12)), Coercible()):
            for function in (encode_header, validate_envelope_shape):
                with self.subTest(value_type=type(value).__name__, function=function.__name__):
                    args = (ENVELOPE,) if function is validate_envelope_shape else ()
                    self.assert_invalid(function, *args, **FACTS, nonce=value)

    def test_media_rejects_aliases_parameters_case_and_subclasses(self):
        for value in ("image/jpg", "IMAGE/JPEG", "image/JPEG", "image/png; charset=binary", " image/png", "image/png\n", "image/png\x00", "application/pdf", "", None, b"image/png", StrSubclass("image/png"), Coercible()):
            self.assert_invalid_fact("media_type", value)

    def test_key_id_rejects_empty_oversize_unicode_paths_controls_and_subclasses(self):
        for value in ("", "a" * 65, "é", "Ｋ", "a/b", "a\\b", ".", "..", "a b", " a", "a ", "a\n", "a\r", "a\t", "a\x00", "a=", "a+", "a:", None, b"a", StrSubclass("a"), Coercible()):
            self.assert_invalid_fact("seal_key_id", value)

    def test_every_ascii_key_character_has_exact_membership(self):
        allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
        for code in range(128):
            char = chr(code)
            with self.subTest(code=code):
                if char not in allowed:
                    self.assert_invalid_fact("seal_key_id", char)
                else:
                    facts = {**FACTS, "seal_key_id": char}
                    aad = encode_aad(**facts)
                    self.assertEqual(aad[115], 1)
                    self.assertEqual(aad[116:], char.encode("ascii") + bytes(63))
                    header = encode_header(**facts, nonce=NONCE)
                    validate_envelope_shape(header + ENVELOPE[78:], **facts, nonce=NONCE)

    def test_maximum_key_id_has_no_padding_or_normalisation(self):
        key_id = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
        facts = {**FACTS, "seal_key_id": key_id}
        aad = encode_aad(**facts)
        self.assertEqual(len(aad), 180)
        self.assertEqual(aad[115], 64)
        self.assertEqual(aad[116:], key_id.encode("ascii"))
        header = encode_header(**facts, nonce=NONCE)
        validate_envelope_shape(header + ENVELOPE[78:], **facts, nonce=NONCE)

    def test_uuid_version_variant_and_zero_are_not_authority_constraints(self):
        for identity in (UUID(int=0), UUID(int=(1 << 128) - 1)):
            facts = {**FACTS, **{field: identity for field in ("organisation_id", "patient_id", "intent_id", "generation_id")}}
            aad = encode_aad(**facts)
            self.assertEqual(aad[10:74], identity.bytes * 4)
            header = encode_header(**facts, nonce=NONCE)
            validate_envelope_shape(header + ENVELOPE[78:], **facts, nonce=NONCE)

    def test_each_trusted_fact_swap_rejects_the_original_header(self):
        swaps = {field: UUID(int=1) for field in ("organisation_id", "patient_id", "intent_id", "generation_id")}
        swaps.update(size_bytes=2, sha256=b"\xff" * 32, media_type="image/png", seal_key_id="k_9-")
        for field, value in swaps.items():
            with self.subTest(field=field):
                facts = {**FACTS, field: value}
                self.assertNotEqual(encode_aad(**facts), encode_aad(**FACTS))
                self.assertNotEqual(encode_header(**facts, nonce=NONCE), HEADER)
                # Keep length valid for changed size so header equality is tested.
                envelope = HEADER + b"\x00" * (facts["size_bytes"] + 16)
                self.assert_invalid(validate_envelope_shape, envelope, **facts, nonce=NONCE)
        self.assert_invalid(validate_envelope_shape, ENVELOPE, **FACTS, nonce=b"\xff" * 12)
        self.assertNotEqual(encode_header(**FACTS, nonce=b"\xff" * 12), HEADER)

    def test_every_header_byte_mutation_is_rejected(self):
        for offset in range(78):
            with self.subTest(offset=offset):
                mutated = ENVELOPE[:offset] + bytes([ENVELOPE[offset] ^ 1]) + ENVELOPE[offset + 1:]
                self.assert_invalid(validate_envelope_shape, mutated, **FACTS, nonce=NONCE)

    def test_every_truncated_header_is_rejected(self):
        for length in range(78):
            with self.subTest(length=length):
                self.assert_invalid(validate_envelope_shape, ENVELOPE[:length], **FACTS, nonce=NONCE)

    def test_missing_body_tag_bytes_and_trailing_bytes_are_rejected(self):
        for length in range(78, len(ENVELOPE)):
            with self.subTest(length=length):
                self.assert_invalid(validate_envelope_shape, ENVELOPE[:length], **FACTS, nonce=NONCE)
        for suffix in (b"\x00", b"\x01", b"trailing"):
            self.assert_invalid(validate_envelope_shape, ENVELOPE + suffix, **FACTS, nonce=NONCE)

    def test_mutable_view_and_subclass_envelopes_are_rejected(self):
        for envelope in (bytearray(ENVELOPE), memoryview(ENVELOPE), memoryview(bytearray(ENVELOPE)), BytesSubclass(ENVELOPE), None, len(ENVELOPE), ENVELOPE.hex(), Coercible()):
            with self.subTest(value_type=type(envelope).__name__):
                self.assert_invalid(validate_envelope_shape, envelope, **FACTS, nonce=NONCE)

    def test_garbage_ciphertext_and_every_tag_mutation_are_intentionally_accepted(self):
        # Shape validity conveys no GCM integrity; there is no real key or AEAD.
        for offset in range(78, len(ENVELOPE)):
            with self.subTest(offset=offset):
                mutated = ENVELOPE[:offset] + bytes([ENVELOPE[offset] ^ 255]) + ENVELOPE[offset + 1:]
                view = validate_envelope_shape(mutated, **FACTS, nonce=NONCE)
                self.assertEqual(view.tobytes(), mutated[78:])
                self.assertIs(view.obj, mutated)
                self.assertTrue(view.readonly)


if __name__ == "__main__":
    unittest.main()
