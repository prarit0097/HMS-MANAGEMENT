"""Deterministic document envelope encoding and shape checks, without authentication."""

import hashlib
import re
import struct
from uuid import UUID


_ERROR = "Invalid document envelope format."
_KEY_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


def encode_aad(
    *,
    organisation_id: UUID,
    patient_id: UUID,
    intent_id: UUID,
    generation_id: UUID,
    size_bytes: int,
    sha256: bytes,
    media_type: str,
    seal_key_id: str,
) -> bytes:
    """Encode independently supplied canonical facts as the 180-byte AAD."""
    if (
        any(type(identity) is not UUID for identity in (
            organisation_id, patient_id, intent_id, generation_id
        ))
        or type(size_bytes) is not int
        or not 1 <= size_bytes <= 10485760
        or type(sha256) is not bytes
        or len(sha256) != 32
        or type(media_type) is not str
        or media_type not in ("image/jpeg", "image/png")
        or type(seal_key_id) is not str
        or _KEY_ID.fullmatch(seal_key_id) is None
    ):
        raise ValueError(_ERROR)

    key_id = seal_key_id.encode("ascii")
    return struct.pack(
        ">8sH16s16s16s16sQ32sBB64s",
        b"HMSDOC01",
        1,
        organisation_id.bytes,
        patient_id.bytes,
        intent_id.bytes,
        generation_id.bytes,
        size_bytes,
        sha256,
        1 if media_type == "image/jpeg" else 2,
        len(key_id),
        key_id,
    )


def encode_header(
    *,
    organisation_id: UUID,
    patient_id: UUID,
    intent_id: UUID,
    generation_id: UUID,
    size_bytes: int,
    sha256: bytes,
    media_type: str,
    seal_key_id: str,
    nonce: bytes,
) -> bytes:
    """Encode the 78-byte header from trusted facts and an expected nonce."""
    aad = encode_aad(
        organisation_id=organisation_id,
        patient_id=patient_id,
        intent_id=intent_id,
        generation_id=generation_id,
        size_bytes=size_bytes,
        sha256=sha256,
        media_type=media_type,
        seal_key_id=seal_key_id,
    )
    if type(nonce) is not bytes or len(nonce) != 12:
        raise ValueError(_ERROR)
    return struct.pack(
        ">8sH16s12sQ32s",
        b"HMSENC01",
        1,
        generation_id.bytes,
        nonce,
        size_bytes,
        hashlib.sha256(aad).digest(),
    )


def validate_envelope_shape(
    envelope: bytes,
    *,
    organisation_id: UUID,
    patient_id: UUID,
    intent_id: UUID,
    generation_id: UUID,
    size_bytes: int,
    sha256: bytes,
    media_type: str,
    seal_key_id: str,
    nonce: bytes,
) -> memoryview:
    """Return a shared ciphertext/tag view; shape does not establish integrity."""
    header = encode_header(
        organisation_id=organisation_id,
        patient_id=patient_id,
        intent_id=intent_id,
        generation_id=generation_id,
        size_bytes=size_bytes,
        sha256=sha256,
        media_type=media_type,
        seal_key_id=seal_key_id,
        nonce=nonce,
    )
    if (
        type(envelope) is not bytes
        or len(envelope) != 78 + size_bytes + 16
        or envelope[:78] != header
    ):
        raise ValueError(_ERROR)
    return memoryview(envelope)[78:]
