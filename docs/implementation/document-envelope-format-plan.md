# S0 document envelope format implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development task-by-task. Track steps with checkboxes. Coordinator alone commits/pushes/deploys.

**Status:** FROZEN leaf-only, 11 November 2026, after independent security and scenario/test-design approval plus coordinator review. This does not approve parent ingestion or claim implementation/acceptance.

**Goal:** Provide deterministic binary encoders and strict envelope-shape checking over immutable bytes.

**Architecture:** One pure module, no callers or integration. Expected facts come from a future trusted caller; object headers never establish those facts. A successful shape check returns ciphertext/tag bytes without authenticating or decrypting them.

**Tech stack:** Python standard library only; production imports limited to uuid, re, struct and hashlib. Tests use unittest.

**Spec:** [Sealing draft](document-ingestion-sealing-contract.md), binary AAD/header paragraphs and coordinator alignment. The remaining sealing/storage/recovery protocol stays DRAFT.

## Scope and review gates

Affected pages, actions, APIs, permissions, data models and migrations: **none**. No new user capability exists, so no HTTP operation is required. No caller, Django import, setting, dependency, encryption/decryption/key wrapping, random generation, filesystem/network/process I/O, claim, worker, scanner, policy or capability change. Existing 50 HTTP operations and disabled ingestion flags remain unchanged.

New production file: `backend/apps/core/document_envelope_format.py`.
New test file: `backend/tests/test_document_envelope_format.py`.
Coordinator documentation updates: HMS.md, plan.md and ledger.md with actual evidence.

Review focus: exact offsets/endianness; bool/coercion rejection; Unicode key-ID ambiguity; mutable-buffer races; treating valid shape as authenticated content. Each is pinned by the tests below. Caller authority and cryptographic integrity are deliberately absent, not implicitly satisfied.

## Exact interfaces

All arguments after the first positional envelope are keyword-only. UUID means `uuid.UUID`. No facts are inferred from the envelope.

```python
encode_aad(*, organisation_id: UUID, patient_id: UUID, intent_id: UUID, generation_id: UUID, size_bytes: int, sha256: bytes, media_type: str, seal_key_id: str) -> bytes
encode_header(*, organisation_id: UUID, patient_id: UUID, intent_id: UUID, generation_id: UUID, size_bytes: int, sha256: bytes, media_type: str, seal_key_id: str, nonce: bytes) -> bytes
validate_envelope_shape(envelope: bytes, *, organisation_id: UUID, patient_id: UUID, intent_id: UUID, generation_id: UUID, size_bytes: int, sha256: bytes, media_type: str, seal_key_id: str, nonce: bytes) -> memoryview
```

Every encoder/checker applies identical fact validation. Require exact runtime types: UUID fields `type(value) is UUID`, size `type(value) is int`, binary fields `type(value) is bytes`, text fields `type(value) is str`; reject subclasses/coercions, including bool, UUID strings, bytearray and memoryview. UUID version/variant is unrestricted; generation randomness belongs to future callers. Size is 1..10485760 inclusive; digest exactly32 bytes; nonce exactly12 bytes. Media is exactly `image/jpeg` or `image/png`. Seal key ID full-matches ASCII `[A-Za-z0-9_-]{1,64}`, without trimming, case folding or normalisation.

Every invalid type, bound, value, header or envelope length raises `ValueError("Invalid document envelope format.")`; fixed text, no supplied values. No exception wrapping of unrelated runtime failures. No error-code taxonomy or HTTP mapping.

## Binary contract

AAD is exactly180 bytes, equivalent to big-endian struct `>8sH16s16s16s16sQ32sBB64s`: `HMSDOC01`, version1, organisation/patient/intent/generation UUID `.bytes`, size, raw digest, media JPEG1/PNG2, key-ID ASCII byte length, key-ID padded on the right with zero bytes to64. Padding is deterministic; no JSON, UUID text or digest hex.

Header is exactly78 bytes, equivalent to `>8sH16s12sQ32s`: `HMSENC01`, version1, expected generation, DB-supplied expected nonce, expected size, SHA256 of independently encoded expected AAD. It contains no wrapped key.

Shape validation checks immutable envelope type and exact total length `78 + size_bytes + 16`, reconstructs the expected header from validated trusted facts, and requires exact equality of the first78 bytes. Reject truncation, trailing bytes and every header mismatch. Return `memoryview(envelope)[78:]`, readonly and sharing the original immutable buffer; include the16-byte tag. Do not return parsed identity or plaintext, hash ciphertext, interpret a tag, or call this result authenticated. Correctly shaped arbitrary ciphertext/tag is deliberately accepted here; later AEAD verification is mandatory before disclosure.

## Task S0: format helpers

- [x] Complete coordinator scope/scenario/threat/test review, obtain independent approval and record leaf-only freeze before production code. Parent remains DRAFT.
- [ ] Write unittest cases importing the absent module; run from backend using an explicitly recorded interpreter: `python -m unittest discover -s tests -p test_document_envelope_format.py -v`. Record missing-module RED; no Django setup or dependency repair is needed for this portable leaf.
- [ ] Add independent literal offset/hex vectors for both media codes and 1/10485760-byte declarations; assert180/78 lengths and all fields. Expected vectors must not call the implementation or mirror its struct format.
- [ ] Test each UUID changed independently, digest/media/key-ID/nonce/size swaps, both magics/versions, every header-byte mutation, truncated0..77-byte headers, body/tag truncation and one extra byte. Check size0/+1, negative/huge/bool/float; wrong-length binary values; wrong types; empty/65-character/non-ASCII/path/newline/NUL key IDs; exact1/64-character valid IDs; media aliases/parameters rejected.
- [ ] Test readonly shared ciphertext memoryview and rejection of mutable/view envelope inputs. Show valid-shape garbage ciphertext passes without authentication; altered expected facts fail. Keep maximum-size buffers bounded and fixtures synthetic.
- [ ] Implement only the three helpers with minimal shared validation. Run the portable suite GREEN, preserving initial RED and final case counts. Inspect imports/no callers/no side effects; fresh independent source/test review must verify vectors and boundary coverage.
- [ ] Coordinator runs full backend actual PostgreSQL regression/check/no-migration-drift using source-compatible pinned environment, required repository/schema checks and exact pushed-SHA CI. Pure-leaf results do not substitute for these gates or become ingestion/PG feature tests.
- [ ] Following owner policy, coordinator performs reviewed source-only preview rollout/live preservation verification, backup/rollback checks and same-change documentation. No migration, ingestion call, scanner or flag activation. Record verified remote SHA, live source and unfinished parent gates before declaring S0 complete; doc-only plan publication does not restart the app.

## Self-review and disposition

All interfaces, bytes, failure behavior and scope exclusions are specified. Proposed choices needing coordinator/independent approval are exact-type rejection, one fixed ValueError, explicit-facts signatures and immutable bytes-only envelope input. No unresolved encoding choice remains in this candidate. No code or test was written/run for this plan; existing primitive feasibility is not format-helper evidence.

Coordinator approves these four choices: they avoid coercion and mutable-buffer races while keeping expected identity independent of stored headers. Cost: future callers must provide exact canonical Python facts, not serializer values directly. Independent security review and separate scenario/test review found no leaf blocker. Execution must instantiate the full invalid-input matrix for all three functions, assert `view.obj is envelope` and readonly, and distinguish header tamper rejection from intentionally accepted ciphertext/tag mutation. Maximum valid envelope is10,485,854bytes. These reviews ran no executable tests. No parent storage/scanner/recovery/resource/authority decision is frozen.
