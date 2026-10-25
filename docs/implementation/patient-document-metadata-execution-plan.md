# Patient document metadata B1 pure contract helpers implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for the assigned implementation task; coordinator arranges independent review. Steps use checkbox (`- [x]`) syntax. Coordinator alone commits/pushes the shared checkout.

**Status:** 25 October 2026, FROZEN B1 after independent review; root verifies/publishes catalogue before authorising RED-first helper implementation.

**Goal:** Implement independently executable, deterministic declaration/query/cursor/fingerprint rules without exposing any new capability.

**Architecture:** One standard-library-only pure module validates original bounded byte inputs and trusted explicit scalar parameters. It never opens a stream, authenticates a caller, queries a database or constructs an HTTP response. Database-backed admission/services are B2; real HTTP/CSRF/transport and role integration are B3, each requiring its own freeze and RED gate.

**Tech Stack:** Existing Python/pytest environment; no dependency installation or provisioning. Existing Django5.2.18/DRF3.16.1/psycopg3.2.12 are unchanged and unnecessary imports in this module.

**Spec:** [metadata contract](patient-document-metadata-contract.md), [transaction review](patient-document-metadata-transaction-review.md), coordinator's bounded B1 instruction, [foundation](patient-document-foundation-contract.md). This plan narrows implementation scope; any conflicting unfrozen broad proposal is not authority to build B2/B3.

## Global constraints and ownership

- Only production file created by B1: `backend/apps/core/document_contracts.py`; tests: `backend/tests/test_patient_document_contracts.py`.
- No model/migration/database/rate limiter/permission/current-user/route/view/serializer/frontend/deployment changes. No stream readers, Request objects, CSRF/auth/network helpers or document projections. No new connection options or worker timers.
- No raw input in exception messages, logs or test failure diagnostics intended for production. Tests use synthetic declarations only.
- Coordinator owns OpenAPI/page-action catalogue freeze, HMS.md/plan.md/ledger updates, integration review and every commit/push. Before code, catalogue describes50 operations (46implemented+4planned); B1 implements zero HTTP operations.
- B2 later freezes accepted fixed UTC-minute actor allowance60 (minute-edge bursts explicit), separately committed limiter admission, audited durable business phase and cooperative5second work budget with no COMMIT-acknowledgement SLA. B1 neither implements nor verifies those rules.
- No parallel ownership of this module/test file; implementer writes RED then minimal GREEN sequentially. Independent reviewer reviews after recorded evidence; coordinator alone integrates approved work.

## Frozen public interface

All functions are synchronous, deterministic and side-effect free. They return fresh ordinary dicts/strings with no lazy values. No import from Django, DRF, app models/settings/services, filesystem, socket or time-dependent code. Public functions validate their explicit inputs; no implicit str()/int() coercion.

| Interface | Return/behavior |
|---|---|
| `class DocumentContractError(Exception)` | Constructor `DocumentContractError(code: str, status: int, message: str)`; public attributes code/status/message; str(error)==message. This module raises only the fixed combinations below. No user values or nested parser exception text. |
| `parse_create(body: bytes) -> dict` | Exact normalized required keys category,filename,media_type,size_bytes,sha256, with their original scalar types. |
| `parse_withdraw(body: bytes) -> dict` | Exact normalized required keys expected_version,reason. |
| `canonical_uuid(value: str) -> str` | Accepts exact lowercase canonical hyphenated UUID text, returns identical text; rejects all aliases. Invalid input raises generic400, including malformed path-like values. Later HTTP path adapter must separately conceal malformed paths as404; B1 cannot decide HTTP path authority. |
| `parse_list_query(pairs: list[tuple[str,str]] | tuple[tuple[str,str],...], patient_id: str) -> dict` | Returns exactly `{limit: int, category: 'registration', cursor: dict | None}`. Cursor dict has exactly v,patient_id,category,created_at,id. Validate patient_id even without cursor. |
| `encode_cursor(patient_id: str, created_at: str, document_id: str) -> str` | Validates canonical IDs/timestamp; returns canonical unpadded base64url cursor described below. |
| `command_fingerprint(operation: str, patient_id: str, document_id: str | None, payload: dict) -> str` | Revalidates and normalizes exact matching payload; returns64 lowercase SHA256 hex. Does not mutate caller's payload. |

Fixed errors: validation failures use `(code='validation_error', status=400, message='Check the highlighted details.')`; original bytes over4096 use `(code='request_too_large', status=413, message='This request is too large.')`. Wrong body runtime type is400; check type before length. No other error code, field_errors, request ID, transport status or supplied data is emitted by B1. Trap JSON/UTF8/calendar/UUID/base64/recursion/value/overflow failures into these fixed errors; do not catch arbitrary programmer exceptions as successful validation.

## Shared bounded JSON and scalar rules

Accept exact bytes only, length<=4096 original bytes. At4097 fail413 before decoding;4096 itself is allowed when the complete payload is valid. Decode strict UTF8, reject BOM and invalid bytes, then parse an object root. Reject duplicate object keys at any depth, NaN/Infinity/-Infinity, scalar/array roots, excessive nesting, and escaped lone UTF16 surrogates in **any** JSON key/string value. Valid escaped surrogate pairs decode to their Unicode scalar and remain acceptable if other rules permit them. Reject RecursionError generically. Bounded helpers cannot prove that an upstream HTTP reader bounded original wire bytes; B3 must separately capture before auth/CSRF reads and preserve the original4096-byte boundary.

Maximum nesting is8 **containers**, root object at depth1; entering an object/array adds1, scalar leaves add0. A depth8 input may subsequently fail exact-field validation, but must parse safely; depth9 always400. A bounded input may still exceed Python's parser recursion threshold; map that failure400 without raw exception text. Duplicate detection occurs on decoded keys, so `filename` and its JSON escaped spelling are duplicates. A JSON integer with an excessive digit sequence must map to400 without bypassing Python's configured integer conversion protections.

For filename and reason, reject prohibited code points **before trim**, including edge tabs/newlines which str.strip() would otherwise erase: C0 U+0000..001F, DEL U+007F, C1 U+0080..009F, Unicode bidi formatting controls U+061C/U+200E/U+200F/U+202A..202E/U+2066..2069, and all U+D800..DFFF. Then apply Python Unicode str.strip() to outer whitespace and measure Python Unicode code points. No Unicode normalization or ASCII transliteration. Filename additionally rejects slash/backslash anywhere and trimmed `.`/`..`; allowed length1..120, no all-whitespace. Reason length10..500; slash/backslash have no special restriction for reason. Internal ordinary spaces remain unchanged. Validate exact strings, no bool/number/null/container coercion.

Create accepts exactly `{category,filename,media_type,size_bytes,sha256}`. category exactly`registration`; media_type exactly`image/jpeg` or`image/png`; size_bytes type exactly int excluding bool, inclusive1..10485760; sha256 exact64 ASCII lowercase hexadecimal characters (full-string match/length, no trailing newline). No extension/magic-byte/file reception claim. Withdraw accepts exactly `{expected_version,reason}`; expected_version type exactly int excluding bool, inclusive1..2147483647. Empty/missing/extra fields and differently cased keys reject400. Fingerprint revalidation uses the same scalar validators, without reserializing into a4096-byte body: a normalized scalar dict has no original wire-size meaning.

## Query and canonical cursor rules

pairs is an explicitly materialised list/tuple of two-element tuples with exact string key/value elements; reject mappings, string/bytes, generators, malformed pairs and wrong types400. Maximum3pairs; every key must be unique and one of limit,category,cursor. No default truthiness: present empty values reject. Absent limit defaults25; present limit is canonical ASCII decimal `[1-9][0-9]*` in1..100, rejecting leading zeros, sign, whitespace, floats, exponent notation and Unicode digits. Absent category defaultsregistration; present category exactlyregistration.

Timestamp text is exactly `YYYY-MM-DDTHH:mm:ss.ffffffZ`, ASCII digits and literal separators, valid Gregorian calendar/time, years0001..9999, no leap seconds, offsets, lowercase z, extra spaces, missing/variable fractions or datetime objects. Validate calendar after grammar; do not rely on platform-specific strftime formatting of years<1000.

Cursor canonical bytes are UTF8 of compact JSON with **fixed insertion/key order** `v,patient_id,category,created_at,id`, ensure_ascii=True and separators comma/colon. v is actual integer1, not bool or float; category exactlyregistration; all IDs canonical; created_at uses the timestamp grammar above. Encode with URL-safe base64 and strip all padding. Cursor input must be1..512 ASCII characters, only `[A-Za-z0-9_-]`, no padding/whitespace/standard-base64 aliases; strictly decode with computed padding, strict UTF8 and duplicate/nonfinite/surrogate checks. Require exact field set, types and values; patient_id must equal requested canonical patient. Re-encode validated fields with encode_cursor and require exact original cursor string, which rejects alternate JSON key order, spaces, escaped ASCII alternatives, noncanonical trailing base64 bits and encodings even when semantic JSON is equal. No signature, authorization, encryption, snapshot or existence claim is attached to the cursor.

## Fingerprint preimage

Only operations `intent.create` and `intent.withdraw` are accepted. patient_id is canonical UUID. Create requires document_id is None and exact create payload; withdraw requires canonical document_id and exact withdraw payload. payload is an exact ordinary dict with exact required fields and validated scalar values, normalized again through shared validators. Reject mismatched operation/document combination or extras, including caller-supplied operation/patient/document inside payload.

Hash UTF8 of `json.dumps({operation,patient_id,document_id,payload}, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)` with actual key/value dict entries and SHA256. Sorting applies recursively to payload. Input field order, JSON whitespace, escaped spelling and permitted outer ordinary whitespace produce identical normalized fingerprints; changed digest/patient/document/reason/version produce different hashes. No database/receipt lookup or claim of idempotent execution exists in this helper.

## Review focus

1. A prohibited edge control must not disappear during trimming; test every specified control family at string beginning/end.
2. JSON escaped aliases can hide duplicate keys or lone surrogates; test decoded equality and recursive strings/keys.
3. Equivalent JSON/base64 is not necessarily canonical cursor text; compare exact re-encoded bytes and test altered low padding bits.
4. bool is a Python int subclass; size/version/cursor-v tests require actual integers and reject bool/float.
5. Fingerprinting must not skip payload validation or reapply an unrelated wire-size rule; test direct forged dicts, ordinary whitespace normalization and maximal Unicode normalized values.

## Task1: RED pure contract tests

**Files:** Create `backend/tests/test_patient_document_contracts.py`; production module must still be absent when first RED executes. Test bodies use public interfaces; no Django database mark or fixtures.

- [x] Write import/discovery tests and the behavior matrix below. The first recorded RED must show absent module/public interface, with the installed pytest environment healthy; do not misreport dependency/configuration failure as valid RED.
- [x] Run from `E:/coding/HMS/backend`: `.venv/Scripts/python.exe -m pytest tests/test_patient_document_contracts.py -q`; retain actual failure output/time. Coordinator reviews RED before production code.

| Required test names/groups | Exact assertions |
|---|---|
| `test_create_valid_normalizes_without_mutating` | JPEG/PNG, stripped ordinary Unicode whitespace, unchanged interior spaces,1and10MiB accepted, no extension requirement; fresh exact-key dict. |
| `test_body_boundaries` | Valid padded original JSON4095/4096 accepted,4097=>413; invalid UTF8/BOM=>400; wrong body types=>400. |
| `test_strict_json` | Duplicate top-level/nested/escaped-equal keys, nonfinite constants, scalar/array/null root, trailing tokens, bad escape, excessive integer digits=>fixed400. |
| `test_depth_and_surrogates` | Nested container depth8 safely parses then exact-field400, depth9/deeply nested<=4096=>400 never parser leak; escaped lone high/low in keys/values=>400; valid escaped pair in accepted filename/reason roundtrips to one Unicode scalar. |
| `test_create_shape_and_numbers` | Every required missing key, each forbidden extra, casing, null/array fields; size True/False/float/string/0/10485761 reject; sha wrong length/uppercase/nonhex/trailing newline reject; PDF/alternate category reject. |
| `test_filename_controls_before_trim` | Every C0/C1/DEL code point plus each listed bidi and representative surrogates reject at edges/interior; slash/backslash/dot paths/all whitespace reject; length120 accepted121rejected measured after trim; Unicode combining sequences preserved. |
| `test_withdraw_validation` | Exact fields; reason9/10/500/501; prohibited edge controls; integer version1/maxaccepted,0/max+1/bool/float/string rejected; slash in reason allowed. |
| `test_uuid_is_exact_canonical` | Canonical lower hyphenated accepted; uppercase/braces/URN/compact/whitespace/malformed/wrong type reject400; no version4-only restriction. |
| `test_query_bounds_and_types` | Defaults exactdict;1/100accept;0/101/01/+1/space/Unicode digits/exponent/emptyreject; duplicate/unknown keys,>3pairs, mapping/generator/malformedpairs/wrongtype reject; category exact. |
| `test_cursor_golden_vector` | Hard-coded expected cursor string for fixed synthetic UUIDs/timestamp; decoded bytes exact fixed key order; parse query returns exact canonical cursor dict and roundtrip. Expected vector independently constructed in test, not computed by helper under test. |
| `test_cursor_calendar_and_canonicality` | Leap year valid/invalid;0001year valid; bad month/day/time/leapsecond/fraction/offset/lowercasez reject; reordered/spaced/ASCIIescaped/duplicate/extra JSON keys, vbool/vfloat, foreignpatient, uppercaseUUID, padding,standardalphabet,whitespace,invalidUTF8,>512,noncanonicalpadbits reject. |
| `test_fingerprint_golden_vectors` | Hard-coded create/withdraw SHA256 expected independently from literal sorted compact ASCII preimages; output64lowerhex. Equivalent input order/ordinaryoutertrim equal; changedpatient/document/digest/reason/version unequal. |
| `test_fingerprint_revalidates` | Wrongoperation/createwithdoc/withdrawwithoutdoc/noncanonicalIDs/unknownpayload/missingfields/boolsize/version/control/surrogate reject; normalized maximalUnicode dict permitted even if ASCII escaped serialization exceeds4096; inputdict unchanged. |
| `test_fixed_errors_and_purity` | Every error exact code/status/message/str with no supplied secret marker/parser text; module functions operate without database access (pytest-django unmarked test guard), no Django/DRF/model/settings/IO imports; no routes/grants/schema change. |

## Task2: Minimal pure module GREEN

**Files:** Create `backend/apps/core/document_contracts.py`; update only owned test file for justified test corrections with explanation and retained original RED evidence.

- [x] After coordinator freeze and recorded RED approval, implement the public interfaces above using standard-library json/uuid/base64/datetime/hashlib and small shared validation helpers. Implement original-byte type/size check before decode; duplicate object_pairs_hook and parse_constant rejection; bounded nesting/surrogate walk; shared exact-payload validators; exact cursor re-encoding. No framework or transport code.
- [x] Run the same focused command; require all assertions pass and record actual totals/time. Test fixes cannot relax stated grammar or disguise RED.
- [x] Request fresh independent review of source/tests against the frozen matrix, concentrating on before-trim controls, canonical byte encodings, bool coercion and fingerprint revalidation. For any Important finding, add reproducing RED, minimally fix and rerun focused tests.

## Task3: Verification and coordinator publication

- [x] Run from backend: `.venv/Scripts/python.exe manage.py check`; expect no issues.
- [x] Run `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`; expect no changes.
- [x] Run `.venv/Scripts/python.exe -m pytest -q`; record actual result/skips/database backend honestly. SQLite cannot verify PostgreSQL races; this B1 introduces none and must not claim B2 lock/timeout/audit safety from this run.
- [x] Coordinator runs the repository's exact established OpenAPI/docs/root checks after planned catalogue updates. Confirm46implemented/4planned operation distinction, unchanged URL/grant/current-user sets, no migration drift and no frontend source changes. Do not invent a check command or claim a count before reading its actual output.
- [x] Coordinator updates HMS.md affected status/interfaces/evidence/new change record, plan.md B1status/B2-B3open, ledger and this plan's checked steps in the same completed change set. Clearly label B1helpers implemented/verified versus HTTP/services/UI planned and runtime undeployed.
- [ ] Coordinator commits only reviewed owned changes plus required integration docs, pushes normally and verifies remote SHA; retain exact CI state separately. No force push, live changes or unrelated files. Report unrun PostgreSQL/B2/B3/browser/real-record checks explicitly.

Self-review: every B1requirement maps to a public interface and named RED group. No product capability, shared limiter schema or full-network time claim is included. B1 does not close patient-document Task04. All boxes remain unchecked until observed evidence; this draft itself runs no executable tests.

## Observed B1 evidence

Added only backend/apps/core/document_contracts.py and tests/test_patient_document_contracts.py. Public interfaces parse_create/parse_withdraw/canonical_uuid/parse_list_query/encode_cursor/command_fingerprint and fixed DocumentContractError implement the frozen standard-library-only rules. Exact original-byte4096 limit, strict JSON/scalars/depth/decoded duplicates/nonfinite inputs, controls BEFORE trim, Gregorian UTC timestamps, canonical fixed-order cursor/base64 round-trip, and recursively sorted ASCII command fingerprints are independently executable. Fingerprints revalidate normalized payloads without incorrectly reapplying wire-size to ASCII escape expansion. No Django/DRF/DB/IO import or permission/route/schema/UI change; helper validation is not HTTP ingress, CSRF, authorisation, idempotent execution or file safety.

LiteralRED614module-missing errors26.20s preceded all production code; root verified module absent and approved GREEN. Final tracked618passed4.69s after strengthening four non-vacuous duplicate/cursor cases, no production relaxation. Fresh independent review found no Important/Critical source defect; root reran combined tracked+ignored probes717passed4.43s, moduleSHA256961c42ad69b41a2b6ccb3e13e415fd5a03b82e460b6979f982e60c7cdc2b6096 matched reviewed source. Root actualPostgreSQL1276passed/168subtests54.63s, Django check0/no migration drift. Candidate archive3cb84bdd5e18f8340969066ca0b7c57c5ef02760e9c2d1f4aec9ee46cff8b68b and private durable document-contracts-20261025.log bind actual validation. Cleanup independently appCREATEDB=f/testDBabsent0/previewactive. No unchanged frontend/browser suite rerun locally; publication CI remains separate until observed.

B1 complete within this bounded contract;50catalogued/46source-implemented HTTP operations remain unchanged. NextB2service plan is DESIGN ONLY until independent review/exact freeze: durable actor limiter/schema, current scoped context/epoch/grants, audited two-phase transactions, quota SQL plans and final time/policy projection need actual PostgreSQL races/timeout/COMMIT evidence. B3HTTP/real-CSRF/role/API acceptance and usable ingestion/UI remain planned. No source deployed to initial47b3618preview; no real records/resources or other VPS app changes.
