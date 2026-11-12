# Registration ingestion transport and discovery

**DRAFT — 11 November 2026.** Exact candidate for coordinator reconciliation and independent review, not a freeze, OpenAPI addition, implementation or activation. Baseline source1976cba/S0 is deployed; it provides no ingestion capability. Consume [persistence](document-ingestion-persistence-contract.md), [sealing](document-ingestion-sealing-contract.md), [runtime](document-ingestion-runtime-contract.md) and [R04 proposal](document-ingestion-ui-proposal.md). Preserve all four closed B3 contracts, receipts/events,30minute declarations and unchanged old admission. No operator/grant/retention API is introduced.

## One discovery shape and page actions

Add exactly this optional CurrentUser property; its presence requires explicit schema-version/page-map review before implementation:

```json
{"document_ingestion":{"version":1,"branches":{"00000000-0000-0000-0000-000000000001":{"available":true,"can_read":true,"can_receive":false,"categories":["registration"]}}}}
```

`document_ingestion` has only required version(integer1)/branches. Each canonical branch key has exactly required available/can_read/can_receive booleans and categories, either [] or ["registration"]. Include only current branches with patients.read AND documents.registration.read. available means deployed ingestion read/status interface enabled; can_read additionally reflects current scope. can_receive additionally requires both write grants, intake gate, fresh readiness and capacity. Scanner outage/full queue makes can_receive false, not available/can_read false. No scanner/provider/queue diagnostics or patient lookup. Missing/malformed/version mismatch/map/key/category denies entry; never use global permission union as fallback. Refresh CurrentUser on session/branch change and explicit service recovery; booleans remain advisory.

| R04 action | Current patient-dialog consumer contract |
|---|---|
| Documents | Require exact patient/selected/named-branch agreement, current branch read conjunction and valid available/can_read/registration discovery; lazily GET unified list. No competing metadata list or eager download. |
| Send image | Confirm visible patient/UHID/branch, hash one JPEG/PNG, retain logical keys in memory; existing B3 create once, then PUT new content endpoint. Metadata false upload booleans remain unchanged. |
| Refresh/check result | Explicit list/detail or exact same-key replay; no automatic mutation, polling, fresh key or inference that timeout rolled back. |
| Download | Fresh GET content; current server evidence/capability; attachment only. |
| Withdraw | Unbound eligible intent uses old B3 withdrawal/intent_version. Bound content uses new withdrawal/content_version, including after30minutes. |

Changing patient/branch/session/logout/closing invalidates pending response generations and clears sensitive memory. Leaving does not cancel accepted work. Reload loses keys: authorised list/detail can identify intent UUID/state; never identify a receipt by filename alone. Browser/keyboard/staff acceptance remains required.

## Five new operations

`I=/api/v1/patients/{patient_id}/document-ingestions/`. Canonical lowercase UUID string segments; malformed registered IDs concealed404 after authentication/global-action checks. Only these methods; no suffix/content negotiation override. Unknown paths remain ordinary404. List/detail/download use read conjunction; receive/withdraw additionally require patients.write AND documents.registration.write and current creator. No master-role exemption. Missing/foreign/mismatched patient/intent identical404; visible noncreator write403. Current session/epoch, effective trusted-origin network policy and current exact-branch grants are resampled after waits and at final selection.

| Method/path | operationId / service operation | Query/body | Success |
|---|---|---|---|
| GET I | listPatientDocumentIngestions / ingestion.list | Optional limit canonicalASCII1..100/default25; cursor existing canonical keyset encoding; category=registration |200 List |
| GET I{document_id}/ | getPatientDocumentIngestion / ingestion.detail | Empty |200 Result |
| PUT I{document_id}/content/ | receivePatientDocumentContent / content.receive | Empty query; raw image/header contract below |202 Result, including committed replay |
| GET I{document_id}/content/ | downloadPatientDocumentContent / content.download | Empty |200 attachment |
| POST I{document_id}/withdraw/ | withdrawPatientDocumentContent / content.withdraw | Empty query; strict JSON below |200 Result, including committed replay |

List cursor/order exactly B3 patient/category/created_at/id ascending-encoding/descending-selection rules, immutable intent ordering, results/has_more/next_cursor, no count/offset/search/state filter. Select intents and left-link at most one reservation/content; no second competing list. Unknown/repeated query keys400. All GET bodies forbidden (inspect at most one visible byte); Range presence400. Ignore If-* conditional headers; never304/206. HEAD/OPTIONS and other unsupported methods405 after mapped global action, before patient/media/query/admission; exact Allow collection/detail GET, content `GET, PUT`, withdrawal POST. HEAD body suppressed by HTTP semantics. Content unsupported methods use write global ceiling, avoiding implicit download.

## Request transport and ordering

PUT requires Idempotency-Key canonicalUUID, X-Document-Intent-Version canonical decimal1..2147483647, Content-Type exactly image/jpeg or image/png (case-sensitive value, no parameters), Content-Length matching declaration1..10485760. Content-Length accepts only server-delivered ASCII digits (leading zeros allowed); missing/malformed400, >10MiB413, valid unequal declaration422. Reject nonempty Content-Encoding415. No multipart/base64/client path/Content-Disposition/file fields. Do not read the body to determine authority.

POST requires canonicalUUID Idempotency-Key; application/json with B3 optional UTF-8 charset grammar; exact `{expected_content_version:integer1..2147483647,reason:string10..500}`. B3 Unicode/control/trim/no-extra/no-coercion/UTF8/object/duplicate-key/depth8 rules apply. Only this small command uses4096-byte JSON capture. Receive uses a separate bounded raw reader, never B3's JSON parser/body budget.

Order: trusted ingress network/framing safety → narrow missing/malformed/oversize Content-Length resource checks without body → genuine database session/ordinary header-cookie-Origin real CSRF → global action authorisation → capture original ingestion context once → other header/scalar validation → new actor admission → all-operation deployed API/active-guard gates → scoped target/creator and actor-key receipt/reservation lookup → select replay or first-reservation path → bounded body I/O outside locks → observed-byte verification → fresh authority/fence/state/final transaction → acknowledged detached response. A known bound matching replay acquires bounded transfer capacity after the already charged actor allowance; it does not require intake_open/intake_ready/free object-storage/queue/current write-key eligibility and reserves no new object/storage/scan. A first reservation additionally requires all those intake gates and its transfer/storage reservation before body receipt. Current API/guard closure and authority denial always win on both paths. Only framing400/413 is a local pre-auth exception; key/media/query details follow authentication/action. POST may retain B3-style bounded4097-byte pre-auth capture; PUT may not prebuffer10MiB before authority. Opaque document-local parser reads zero bytes; body csrfmiddlewaretoken never substitutes for header. No CSRF bypass/global parser change. Existing middleware denial may precede local handling.

Receive reads exactly the canonical delivered declaration length into <=10MiB plaintext; reject visible truncation400, visible excess413, digest/type/declaration mismatch422. No stream unwrapping/private WSGI reads or read beyond server-defined entity. WSGI LimitedStream can hide bytes behind missing/short framing; valid first framed entity may commit. Trusted actual HTTP1.1/H2/TE-CL/duplicate-length/missing-length/disconnect gates must establish delivered-entity behavior; replaced test streams cannot prove edge safety. No hidden-byte rollback guarantee. Resource/timeout/disconnect failures after reservation preserve durable uncertainty/terminal rules, not successful receipt.

## Receipt identity, time and capacity

Fingerprint SHA256 uses compact sorted-key ensure_ascii JSON `{operation:"content.receive",patient_id,document_id,intent_version,media_type,size_bytes,sha256}` from trusted declaration and matching headers; body must subsequently match observed values. Actor+receive-key reservation is durable before reading. Changed valid fingerprint409; another key for already reserved intent409. First binding requires pending/unexpired/matching version, strict original cutoff=min(post-auth-real-CSRF context origin+60s,intent.expires_at), local monotonic guard and final precommit checks. No context remint/extension, no old five-second byte budget. Socket/proxy no-progress10s and configured absolute limits supplement the original cutoff; no whole HTTP/COMMIT/delivery SLA.

Known committed replay still pays rate/transfer capacity and verifies supplied body in memory, resolves current authorised receipt/status after expiry, creates no object/generation/encryption/work/version. Unbound interrupted sealing never encrypts again; only authenticated complete final reconciliation before original cutoff is eligible after former-writer termination. Unknown commit503 requires authoritative lookup; no deletion, replacement key or rollback claim. A same-key replay has a fresh60s body-reading deadline, never a fresh first-binding cutoff.

Withdrawal fingerprint uses operation/content.withdraw,patient_id,document_id and normalised expected_content_version/reason in the same canonical format. Resolve matching receipt after current scope/creator checks; replay bypasses version/transition deadline, never authority. New withdrawal requires bound nonwithdrawn content/current version<2147483647, increments exactly once and durably suppresses promotion/download. Historical acceptance remains. Existing intent withdrawal also suppresses content; it does not create new-content side effects.

All five new operations, including replays, charge separate actor60/fixedUTCminute; known committed admission is never refunded. Malformed/global-auth denial consumes none; valid disabled call consumes then503 without patient lookup. Receive/download acquire one peractor and at most two installation slots of each kind; scan limitone. Receive first reservations reserve persistence formula/global1GiB synthetic store and bounded pending queue; no org60/hour throttle. Expiry alone never frees writer slots/bytes. Proposed limits are not hospital capacity evidence.

Download acquires slot, completely decrypts/authenticates/size-hashes exact <=10MiB generation outside locks, then final current authority/no-withdrawal/current-epoch-clearance checks and committed audit before first byte. Send only that checked memory; no IO under business locks, public redirect or bearer URL. Proposed30s transfer/10s no-progress, no per-chunk database reauthorisation. Later revocation/disconnect cannot recall selected/buffered/transmitted bytes; audit means authorised disclosure attempt, not successful save.

## Closed successful projections

All fields required/additionalProperties=false, UTC timestamps exact six fractional digits/Z; UUIDs canonical; versions actualintegers. JSON <=262144 bytes, encoded before audit commit; no lazy model/query escape. Fields contain no digest, key, locator, scanner details, actorID or patient demographics.

```text
Capabilities={available:bool,can_read:bool,can_create_intent:bool,can_receive:bool,
 upload_categories:[]|[registration],allowed_media_types:[image/jpeg,image/png],
 max_size_bytes:10485760,max_filename_characters:120}
Ingestion={document_id,patient_id,branch_id,category:registration,filename,media_type,
 size_bytes,created_at,expires_at,declaration_status:pending|expired|withdrawn,
 intent_version,content_version:null|int,received_at:null|timestamp,
 state:awaiting_file|receiving|expired|processing|ready|rejected|unavailable|withdrawn,
 is_creator:bool,can_receive:bool,can_download:bool,can_withdraw:bool,
 withdraw_action:null|intent|content}
Result={server_time,document:Ingestion,capabilities:Capabilities}
List={server_time,results:Ingestion[0..100],has_more:bool,next_cursor:null|string,
 capabilities:Capabilities}
```

available/can_read use deployed read gate; can_create_intent requires current write conjunction+old metadata enablement+new intake readiness; can_receive additionally includes current capacity. Perrow actions additionally check creator/state/version/time. No capability replaces current operation checks. upload_categories lists registration only when receive permitted. Public filename/media/size remain declared values; received matching evidence is separate.

| Selected facts at one server_time | state/action projection |
|---|---|
| Old intent OR content withdrawn | withdrawn; all actions false/null |
| Bound pending scan | processing; no download; creator eligible content withdrawal |
| Accepted current-epoch evidence and no known key/storage/security/serving denial | ready; authorised reader download capability; creator content withdrawal |
| Rejected checks | rejected; no download; creator content withdrawal |
| Held terminal reservation/security hold/missing clearance/exhausted or unavailable dependency | unavailable; no download; bound creator may withdraw |
| Unbound active reservation/sealing before cutoff | receiving; no duplicate receive; explicit Check result |
| No reservation/content; declaration before expiry | awaiting_file; creator may send/old intent-withdraw |
| Unbound expired declaration/cutoff | expired, unless terminal hold above; no send/download |

Routine scanner outage/full queue does not change accepted ready evidence or disable eligible withdrawal. Declaration expired does not expire bound accepted content. Perrequest unavailable storage/integrity safely suppresses download; no fabricated ready claim. Successful list/detail/replay each commits a new disclosure event; receive/withdraw receipt+mutation+audit atomic. Audit failure/unknown ACK gives503/no projection/disclosure.

For any unbound pending declaration, including held-terminal reservations, eligible creator withdrawal still uses old intent rules before30minute expiry; it does not purge storage. Bound rows use content rules. List/detail materialise known evidence, not full-object decryption for every row; download capability is advisory and actual attachment always performs complete fresh verification.

## Responses and fixed errors

Local JSON application/json; no Accept/indent-controlled renderer, no406 negotiation branch. Every local success/error/405: Cache-Control:no-store, merged Vary:Cookie, X-Content-Type-Options:nosniff; no ETag/Last-Modified. Existing middleware response/header exceptions remain explicit. Attachment additionally exact verified Content-Length/Content-Type and `Content-Disposition: attachment; filename="registration-image.jpg"` (PNG→.png), optional safely encoded filename* using declared safe name. Never echo raw header input. No partial plaintext before full verification.

Errors exactly `{code,message}`; no supplied values/exception/internal text. Preserve B3 fixed tuples for400 validation_error;401 ended-session not_authenticated;403 anonymous not_authenticated/permission_denied/csrf_failed/network_denied;404 not_found;405 method_not_allowed;409 idempotency_conflict/version_conflict;413 request_too_large;415 unsupported_media_type;429 rate_limited/Retry-After1..60. Existing middleware network_policy_unavailable503 preserved. New409 content_state_conflict=`This file is no longer available for this action.`;422 content_mismatch=`The file does not match its declaration. Select the file again.`;503 document_ingestion_unavailable=`Documents are temporarily unavailable. Try again later.` Capacity/backpressure/disabled/dependency/clock/uncertain commit use503; no Retry-After promise. Fixed validation/capacity choices prevent exposing infrastructure state.

**Cross-contract review before freeze:** approve receiving/withdraw_action/created_at closed fields and discovery semantics; distinguish budget-selected-before-COMMIT from literal physical-commit cutoff; align error/backpressure and queue limits; integrate exact page-action/OpenAPI55 candidate without claiming five implemented operations. Recovery execution, purge/hold authority and rewrap remain deferred; runtime isolation/public-TLS spill gates still block byte activation. Scenario/threat/test review must cover real CSRF/framing, all replay/authority/ACK/cutoff races, actual storage/scanner failures and useful R04 staff/keyboard flow. No tests or app changes were performed for this draft.

## Coordinator cross-contract alignment —11 November2026; still DRAFT

Independent review found four concrete mismatches. This candidate selects the following directions; the parent remains unfrozen and requires fresh review of the complete schemas/implementation plan before RED/code.

1. The retention draft now grants a narrowly typed readonly OS group access to root-controlled guard metadata, fresh opens at every mandatory check, never a startup cache or write access. Runtime grouping must carry this one exception. No guard reader or provisioning exists.
2. For HTTP the original context is captured once after genuine authentication, real CSRF and successful global-action authorisation, before scalar validation/admission/reservation/body. Every subsequent validation, admission/target/receipt lock wait, transfer and final precommit check consumes that origin's budget; waits never mint a replacement. Authentication/global denial precedes it. Ingress/header/no-progress bounds apply independently before capture. Future direct-service adapters must supply equivalent authenticated scoped authority through a separately frozen typed factory; HTTP still enforces real CSRF and no caller boolean bypass is introduced. Existing B3 contexts are neither reused nor extended.
3. Separate all-operation gates (deployed API/control/valid active external guard, current session/epoch/network/global+branch+creator authority and charged new actor allowance) from first-reservation-only gates. Resolve the actor/key receipt/reservation before deciding which path applies. Known bound matching replay then needs bounded upload-transfer/rate capacity and matching observed body, but not intake_open/intake_ready/free object-storage/queue/current write-key eligibility; it allocates no generation/object/scan/charge. First reservations require those intake gates before reserving/body. API/guard closure or authority denial always wins, including replay. `can_receive` advertises a new first binding, not authority to replay a retained key; status/detail remains the preferred reconciliation flow. Replays never bypass memory-transfer limits or current scope.
4. An unbound held_terminal intent remains unavailable/can_receive=false/can_download=false. Eligible current creator may logically withdraw through the unchanged old B3 route only when its exact existing gate/grants/pending/unexpired/version rules allow it: can_withdraw=true and withdraw_action=intent. Otherwise both are false/null; no intake/scanner readiness requirement is added. This supersedes the API proposal's10November can_withdraw=false direction for held_terminal only. Bound content uses its new withdrawal route/version independently of declaration expiry and old metadata enablement, while old parent withdrawal always wins visibility. All bytes/history/storage charges remain retained. Unexpected purging/purged states remain fail-closed first-slice corruption, not permission to act.

Retention-first-slice selection is retain-all: no destructive purge/refund, restore-purpose claim/re-enable, rewrap or key retirement. Storage and intake exhaustion deliberately do not revoke eligible accepted download/status/withdrawal; they do refuse new reservations. These are synthetic bounded parameters, not a capacity/recovery claim for the operating hospital. Exact OS reader layout, transport/framing, API/error/current-user schema, persistence constraints and resource acceptance remain open before freeze.
