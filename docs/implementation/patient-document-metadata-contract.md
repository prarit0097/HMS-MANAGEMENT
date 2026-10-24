# Patient document metadata — next bounded contract

24 October 2026. **DRAFT / DESIGN ONLY / UNFROZEN; coordinator fresh review required.** Applies after the dormant foundation at source `5aee4d29939161e09f53e862f407325daad02589`. Reported foundation evidence is 658 actual PostgreSQL tests/168 subtests in47.16s; this document adds no test result. Read with [foundation](patient-document-foundation-contract.md), [lock proposal](patient-document-metadata-lock-design.md), [architecture](patient-documents-design.md), [UI proposal](patient-documents-ui-plan.md), [security proposal](patient-documents-security-review.md), [independent review](patient-documents-independent-review.md), [HMS](../../HMS.md), [plan](../../plan.md) and [ledger](ledger.md). This draft supersedes conflicting earlier metadata proposals only if frozen. No OpenAPI/page-map, source, grant, UI, storage or deployment change accompanies it.

## Boundary and engineering rulings

The proposed next implementation unit is four registration-only metadata APIs plus services/permissions/transport tests; no bytes/content route, encounter, clinical category, PDF, scan work, storage, ready/download state or dependency installation. Existing foundation models/migration remain the persistence contract. An intent is a declaration, never evidence a file was received.

Approaches considered: require storage/scanner for every metadata operation (prevents independent safe source work); expose working uploads from metadata alone (misrepresents availability); or source-test metadata independently while runtime file ingestion remains disabled. Recommend the third. Exact runtime policy: one deployment-owned `HMS_DOCUMENT_METADATA_ENABLED` boolean defaults false; disabled document routes return generic503 after session/action checks, without object lookup/projection or writes. No visitor-controlled activation. When explicitly enabled for reviewed synthetic acceptance, metadata commands may succeed without storage/scanner because they accept no bytes. They must never probe a permissive scanner fallback. Real-record runtime activation remains a separate reviewed rollout/security/dataops decision. Missing metadata DB/audit/authority/network dependencies always fail503.

`can_upload=false`, `can_download=false`, `upload_categories=[]` in every response; no URL, content route, storage locator or accepted-byte receipt. Metadata read/withdraw remains possible after future ingestion dependency failure under this contract; new byte admission is never implied. Production usable uploads require a later frozen private storage/encryption/parser/scanner/key/worker contract and actual evidence. This deliberate source/runtime distinction costs an extra slice before staff can attach a file.

## Authority and CurrentUser

Proposed static role additions: only `reception` gains `documents.registration.read` and `documents.registration.write`. CurrentUser existing `permissions` union and `branch_permissions[branch_uuid]` arrays gain these strings under their existing shapes. UI/action checks use the patient's exact branch array; global union is navigation context only. No custom grant administration, membership creation, default master grant or fifth discovery endpoint.

| Action | Current authority, all at patient registration branch |
|---|---|
| List/detail | `patients.read` AND `documents.registration.read` |
| Create/withdraw/replays | Both read grants AND `patients.write` AND `documents.registration.write` |
| First withdrawal | Above AND actor is creator AND version matches AND selected time strictly before expiry AND stored state pending |

Master-only, doctor-only, nurse-only, other roles and unassigned users get neither document grant. A multi-role user qualifies only through active reception membership in the exact branch; reception-B plus doctor-A does not authorise documents-A. Active identity/current captured session epoch/effective environment AND overlay IP policy are required. No new privileged MFA requirement for reception; existing challenge/stale-session rejection remains. Retain existing epoch0 compatibility under locked User when IdentitySecurity is absent; do not create security rows as a read side effect. Existing MFA/profile services must serialize first-profile creation on that User lock.

No action grant anywhere:403 before patient/document lookup. Missing/foreign/inaccessible patient or mismatched document: identical404, including after a lock wait or replay. Withdrawal of another creator's visible intent:403 without receipt/event. A replay must independently reauthorise current scope before resolving/disclosing its result. Direct-service callers require server-minted captured session/epoch/network context; no public helper accepting arbitrary actor ID/trusted boolean. MCP/jobs get no extra route or authority.

## Exact HTTP surface

`P=/api/v1/patients/{patient_id}/documents/`. All path UUIDs and Idempotency-Key use lowercase canonical hyphenated UUID textual form; accept no braces, URN, whitespace or uppercase aliases. Malformed path UUID concealed404; malformed/missing required key400. UUID keys identify commands, never grant scope. Only listed methods exist; HEAD/OPTIONS/PUT/PATCH/DELETE return405 with no metadata, implicit DRF metadata/HEAD disabled. No content subpath is registered.

| Method/path | operationId | Exact input | Success |
|---|---|---|---|
| GET P | `listPatientDocumentIntents` | Optional `limit` decimal integer1..100 default25; optional `cursor` below; optional `category=registration`. No body. |200 List |
| POST P | `createPatientDocumentIntent` | Required Idempotency-Key; Create JSON below; empty query |201 Result, including exact replay |
| GET P{document_id}/ | `getPatientDocumentIntent` | Empty query/body |200 Result |
| POST P{document_id}/withdraw/ | `withdrawPatientDocumentIntent` | Required Idempotency-Key; Withdraw JSON below; empty query |200 Result, including exact replay |

Unknown/duplicate query keys400. No offset/count/search/sort/branch/org query. Reject nonempty GET bodies400 with bounded inspection, never an unbounded parser read. Every response, including failures/405, is private `Cache-Control: no-store`, `Vary: Cookie`, nosniff; no ETag/Last-Modified. Conditional request headers ignored, never304. Range unsupported400 `validation_error`; no metadata-specific416/content semantics. Size bounds apply irrespective of false/missing Content-Length or transfer framing; no blanket trusting declared length.

List order `created_at DESC,id DESC`. Keyset cursor is unpadded base64url of compact UTF-8 JSON exact keys `{v:1,patient_id,category:"registration",created_at,id}`; canonical UUIDs, UTC timestamp grammar below, max512 ASCII characters, no duplicate keys/noncanonical encoding/extra fields. Cursor tuple must follow strict older-than comparison; patient/category must equal path/filter or400 `validation_error`. Cursor is a position, not an authorisation token. Select <=101 IDs, return<=limit, private sentinel determines has_more. No total COUNT. New inserts appear on explicit first-page refresh; immutable ordering prevents duplicates caused by state changes. Each page has its own selection instant, not a multi-request frozen snapshot.

Create exact required fields, no extras: `{category,filename,media_type,size_bytes,sha256}`. category exactly `registration`; media_type exactly `image/jpeg` or `image/png`; size_bytes actual JSON integer (not bool/float/string), inclusive1..10485760; sha256 exact64 lowercase ASCII hex; filename string trimmed at outer whitespace,1..120 Unicode code points after trim, reject C0/C1 controls, DEL, bidi formatting controls, slash/backslash, NUL, `.`/`..`, all-whitespace. No Unicode normalization beyond trim; render text only. These are declarations; do not claim extension/signature/byte validation. No creator, status, version, time, branch, encounter, scanner or storage input.

Withdraw exact required fields `{expected_version,reason}`; version actual integer1..2147483647; reason string trimmed,10..500 code points, reject C0/C1/DEL/bidi controls. New-key attempt against expired/withdrawn intent409 `intent_state_conflict`; stale version409 `version_conflict`; version2147483647 cannot increment and returns409 `version_conflict`. No restore/unwithdraw/delete.

POST Content-Type exactly application/json with optional UTF-8 charset; no multipart, file field, content encoding or alternate media type. Capture at most4097 original bytes before any installed DRF authentication/CSRF/parser may consume the stream, fail413 above4096; preserve exact bounded bytes for ordinary session authentication/real CSRF and strict handler parsing. Do not copy network-specific transport code blindly. Strict UTF-8 object JSON, no BOM, duplicate keys at any depth, nonfinite values, scalar/array root, unknown fields or coercion. Enforce maximum nesting depth8 (root depth1) and reject deeper input400; trap parser RecursionError at the actual pre-handler/CSRF boundary with generic400. Valid real-CSRF JSON at exactly4096 must succeed when remaining fields are valid; oversize must never reach an unbounded framework read. No disabling/bypassing CSRF, global parser replacement or shared unrelated endpoint behavior change.

## Closed response and error schemas

All objects below reject additional properties in future OpenAPI; fields listed are required. IDs are canonical UUID; timestamps UTC RFC3339 `YYYY-MM-DDTHH:mm:ss.ffffffZ` (exact6fraction digits). Boolean fields must be actual booleans. Serialise detached scalar values only; complete encoded response <=256KiB, fail503 before disclosure if exceeded.

`MetadataCapabilities={can_create_intent:boolean,can_upload:false,can_download:false,upload_categories:[],allowed_media_types:["image/jpeg","image/png"],max_size_bytes:10485760,max_filename_characters:120}`. `can_create_intent` reflects current write conjunction AND enabled metadata policy; it does not promise ingestion. Shared static limits are declaration bounds, not upload availability. A disabled response is an error, never a success capability projection.

`Intent={id,patient_id,branch_id,category:"registration",filename,media_type,size_bytes,status,version,created_at,expires_at,is_creator,can_withdraw,can_upload:false,can_download:false}`. filename/media/size are declared values. `status` exactly pending|expired|withdrawn; version1..2147483647; `is_creator` boolean; can_withdraw derived from current grants/creator/state/version/time. No user display name/identifier, digest, withdrawal reason, withdrawn actor, storage information, patient demographics or scan text. Avoid an extra target-User lock for a display label.

`Result={server_time,document:Intent,capabilities:MetadataCapabilities}`. `List={server_time,results:Intent[0..100],has_more:boolean,next_cursor:string|null,capabilities:MetadataCapabilities}`. next_cursor nonnull iff has_more; no total/count beyond bounded result array. One server_time supplies all expiry/action projections in a response. Withdrawal reason persists only under foundation protection; not echoed in ordinary projections.

`Error={code,message,field_errors?,request_id?}`; no other properties. code enum below, message fixed server text<=200characters, request_id server UUID, field_errors optional object whose only keys are category,filename,media_type,size_bytes,sha256,expected_version,reason,limit,cursor,Idempotency-Key; each value1..3 fixed messages<=160characters. No supplied values, PHI, filename, body, exception or SQL echoed.

| HTTP/code | Plain message / rule |
|---|---|
|400 `validation_error` | `Check the highlighted details.` Malformed JSON/query/header, forbidden fields; optional safe field messages |
|403 `permission_denied` | `You do not have access to this action.` Existing unauthenticated SessionAuthentication challenge also remains403; distinguish through existing shell behavior, not a new401 promise |
|403 `csrf_failed` | `Refresh the page and try again.` Normal real-CSRF failure, no request data |
|404 `not_found` | `This record is unavailable.` Same missing/foreign/scope-mismatch envelope |
|405 `method_not_allowed` | `This action is unavailable.` No object disclosure |
|409 `idempotency_conflict` | `This request could not be repeated. Refresh before continuing.` Changed command under same actor+operation+key |
|409 `version_conflict` | `The record changed. Refresh before continuing.` Stale/max version |
|409 `intent_state_conflict` | `This request can no longer be withdrawn.` New command against terminal projection |
|413 `request_too_large` | `This request is too large.` Original JSON bytes exceeded |
|415 `unsupported_media_type` | `Use a supported request format.` Unsupported transport Content-Type/encoding |
|429 `rate_limited` | `Too many requests. Try again shortly.` Retry-After integer seconds1..3600 |
|503 `document_metadata_unavailable` | `Document details are unavailable. Try again later.` Disabled/dependency/audit/deadline/database/network-evaluation/clock/unknown-commit failure, no projection |

Effective network deny retains existing generic network403; unavailable evaluator503. Freeze exact mapping to existing error handler before implementation; local envelopes must not change other endpoints.

## State, replay, quotas and selection

Persist only pending or withdrawn. At one final coherent selected_at, pending projects expired when selected_at>=expires_at; withdrawn always remains withdrawn. No GET status write/version bump. created_at is server-captured creation time; expires_at exactly+30minutes forever. Replay never refreshes timestamps. A slow create can return an already-expired projection; it still creates no bytes.

Fingerprint before receipt: SHA256 over UTF-8 compact sorted-key JSON (`ensure_ascii=True`, separators comma/colon) of `{operation,patient_id,document_id,payload}`; create document_id=null, withdraw document_id=path UUID; payload uses validated normalized scalar fields including trimmed filename/reason. Reject invalid values before fingerprinting; no JSON floats. This makes JSON whitespace/key order and outer trim equivalent, but changed patient/digest/reason/version a conflict. DocumentIntentReceipt actor+operation+key namespace remains separate from reception IdempotencyRecord. Receipt stores only hash/result reference, never request JSON.

Replay checks current action/scope, exact fingerprint and referenced patient/document before projection. Same key returns current pending/expired/withdrawn state and one NEW successful-disclosure event; no duplicate intent/receipt/version bump. Create replay remains201, withdraw replay200, including after expiry. New key cannot rewithdraw. Changed fingerprint409 has no result echo/event. Ambiguous commit never sends success; same-key later retry either observes committed receipt/result or safely performs missing command after current authorisation.

Proposed bounded quotas (engineering policy, not hospital capacity): <=20 simultaneously pending AND unexpired intents per patient; <=1000 new intents per organisation in rolling3600seconds. Threshold checks under the org/patient gate at creation, SQL existence threshold via bounded IDs rather than unbounded COUNT; withdrawn/expired do not consume active quota, but creation history still consumes rolling quota. At threshold429 with Retry-After until earliest applicable expiry/window exit, rounded up1..3600. Replay and withdrawal are exempt from new-intent quotas, never from authority/audit. No deletion to free quota.

All four routes additionally share60requests/60seconds per actor across document metadata operations using server-configured shared atomic limiter; retry-after to window end. It runs after authentication/action validation and before PHI lookup; limiter unavailable503. No successful audit sampling or dropping to meet load. Exact configured shared backend/algorithm and threshold concurrency must be frozen before code; local-process cache is insufficient. Quotas do not cap total retained metadata/audit history; durable capacity monitoring/retention and real-record activation remain release gates. No storage quota is advertised: no bytes are accepted.

## Lock, audit and transaction gate

Adopt the [lock proposal](patient-document-metadata-lock-design.md) with NO KEY UPDATE actor User -> existing IdentitySecurity lock -> single patient Organisation NO KEY UPDATE -> current actor exact-branch Memberships (if explicit locks, ordered branch/role/id) -> existing document Receipt NO KEY UPDATE (commands only) -> Patient NO KEY UPDATE -> addressed intent or selected page intent locks NO KEY UPDATE in UUID order. No target creator User/StaffAccessRevision, Bed, Appointment, Encounter or network-operator lock. `of=('self',)` prevents incidental joined locks. Actor User serializes absent same-key receipts; unique constraint is backstop. All supported metadata writers use org/patient gate. Recheck resolved patient/branch/org after waits, never follow mismatch into a second organisation lock.

Capture actor/session epoch/network descriptor at entry; reject stale epoch rather than refreshing captured proof. Recheck active identity, current exact-branch conjunction and immutable patient scope after all waits. Insert receipt/transition and required DocumentAccessEvent atomically; force relevant deferred constraints before final selection. Then select one server_time after potentially blocking inserts/checks, recheck current authority/effective network and withdrawal deadline; clock moving backward from start503. Revalidate after any later forced wait. Withdraw crossed expiry rolls back transition/receipt/event. No promise of instant revocation after selected result; network policy may change after pure final snapshot.

Each successful list (including empty) logs intent.list/document=null/count actual0..100; detail logs intent.detail/count1; create/replay intent.create_result/count1; withdraw/replay intent.withdraw_result/count1. projection_sha256 is SHA256 of UTF-8 compact JSON sorted canonical returned UUID strings, e.g. empty `[]`. correlation UUID server generated. Event contains no filename/reason/payload. No generic admin-history union or audit browse API. Failure to commit event prevents metadata/capability/cursor disclosure. On denied/error responses do not fabricate a document event referring to an inaccessible patient.

Public services must own outermost commit: reject an ambient transaction before processing, use durable atomic boundary, return only detached primitives after successful commit. No on_commit audit, generator, model, lazy queryset or serializer query after release. Unknown commit outcome503 without projection; later keyed retry reconciles. Exceptions handled only after atomic exits, not inside a broken transaction.

**Unresolved implementation gate:** proposed lock_timeout2s/statement_timeout3s/service5s are targets, not proven COMMIT bounds. Before freeze, choose and test pinned Django/driver/server strategy for forcing deferred constraints, bounding COMMIT including connection loss, rejecting ambient transactions and ensuring connection cleanup. Clock checks do not interrupt hung COMMIT; statement_timeout alone is not an asserted whole-operation guarantee. No new driver/server dependency/provisioning authorised by this draft. If installed stack cannot deliver measured bounds, narrow and document the claim before code rather than promise impossible deadline/rollback semantics. No automatic in-request transaction retry loop.

## R04 page/actions before any UI implementation

Next metadata backend slice does not introduce a staff-facing SHA256/declaration form. Creating a bare intent with no byte path is not a useful attachment workflow. Create API is independently testable now; its later page action is the internal first step of a working file chooser, under a separate ingestion/UI freeze. Keep Upload/Choose file/Download absent, not enticing disabled controls. CurrentUser permission strings alone must never display Upload. This narrows the earlier UI proposal and its PDF/doctor walkthroughs.

Proposed subsequent R04 metadata UI: Patients search -> existing single Patient details dialog -> View document details -> Documents -> Details or Withdraw request subview -> Back. No nested modal or new route. No eager metadata fetch/count on demographics. Entry requires exact branch read conjunction AND enabled metadata policy discovery through the successful list call; a503 shows plain unavailable text, never filename/count. Patient name/UHID/known DOB-or-age/phone and named branch remain visible from separately authorised patient data; unknown secondary identifiers say Not recorded. Never silently retarget pending work on patient/branch change.

| Page action/state | API and required result |
|---|---|
| Enter/Refresh documents | listPatientDocumentIntents; loading replaces old scope data, empty `No document requests to display.`; Next uses next_cursor, Refresh resets first page |
| Open Details / Refresh status | getPatientDocumentIntent; show declared name/type/size, requested time/deadline/status; no digest or creator label |
| Pending | `File not received. File upload is not available yet.`; Withdraw request only if can_withdraw |
| Expired | `Request expired. No file was received.`; no withdraw/upload/download |
| Withdrawn | `Request withdrawn. The record is retained.`; no undo/delete/upload/download |
| Withdraw request | Replace dialog body, retained identity, visible required Reason10..500, confirm Withdraw request / Back; exact version+fresh stable command UUID; no optimistic removal |
| Successful withdrawal | Authoritative Result only; status `Request withdrawn.`; clear reason/key after settled success; refresh current list on explicit return |
|400 | Focusable summary linked to inline fields, retain safe same-context reason; no raw server payload |
|403/404/session/network denial | Clear document state/keys/reason, stop actions; normal reauthentication/return path; no existence hint |
|409 | Retain safe same-context reason, require explicit fresh detail before new confirmation/key; never blind overwrite |
|429 | Plain retry feedback and Retry-After; no automatic writes |
|503/offline/read-malformed | Unavailable state, explicit Refresh; do not present stale data as current authority |
|Unknown POST outcome/unreadable success | `We could not confirm the request. Retry this request to check the result.` Retain identical payload/version/key in memory; explicit same-key retry only; detail alone cannot prove which command committed |
|Close/Escape/context/logout | Same safe closure behavior; invalidate request generation and clear PHI/reason/keys; reopening re-fetches, never reports cancellation of an unknown committed write |

Offline disables document reads/writes until reconnect AND explicit successful refresh; no automatic mutation/replay. All settlements bind patient/branch/session generation; late results cannot restore closed/foreign data or overwrite newer selection. No PHI/filenames/keys in URL, localStorage, sessionStorage, logs/analytics. Keyboard: single labelled dialog/focus loop; heading focus on subview entry, triggering button focus on Back, visible focus, text statuses/polite outcome announcements. At375/768/1024/1440px identity/actions remain readable; long names wrap. UI/UX Pro Max executed `form error keyboard --domain ux`: verified Focusable Error Summary, Error Messages and Submit Feedback support linked summary/inline errors and announced settlements; no visual-system redesign recommended.

## Pre-code scenario/threat/test matrix

All cases below are planned executable REDs, not run. First RED must fail on absent metadata route/service behavior, not broken dependencies. Source unit can be API-only; UI cases block any later UI completion claim. Freeze exact OpenAPI four operations and R04 mapping BEFORE production code, after independent review resolves gates.

| Test group | Concrete required assertions |
|---|---|
|Role/scope | reception exact-branch200/201; master/doctor/nurse403; doctor-A+reception-B cannot accessA; inactive membership/identity/stale captured epoch/challenge deny; foreign/missing patient and wrong patient/document same404; replay after revoke no event/result; no automatic clinical grant |
|Transport/CSRF | actual APIClient(enforce_csrf_checks=True) valid/missing/incorrect CSRF; original bytes4095/4096/4097 with valid padded JSON; false/missing length and instrumented reader never unbounded; duplicate nested keys, root scalar/array, nonfinite, UTF8/BOM, depth8/9 and deeply nested body through real CSRF400 not500; unknown fields/query/duplicate params; HEAD/OPTIONS405 no event; no content route |
|Declarations | exact lower UUID/key grammar; filename trimmed boundary/control/bidi/path; media JPEG/PNG only PDF denied; size bool/float/string/0/10MiB+1 rejected; digest shape; encounter/branch/status/time/scanner input rejected; raw values absent from error |
|Read/time | one selected_at across list100including equality expiry; no status/version writes; backward time503; UTC precision; list cursor malformed/wrongpatient/duplicatekeys/limit bounds; sentinel not audited/disclosed; new insert does not duplicate immutable pages |
|Replay/state | create same normalized command sameID201/current terminal projection/new event; changed patient/digest key409; withdraw samekey200increment once/new event; changed reason/version409; newkey expired/withdrawn409; maxversion409; receipt namespace does not alter reception behavior |
|Audit/commit | empty list event; exact sorted-ID digest/count; per-result events; insert/deferredcheck/COMMIT failures no projection; rollbacks no partial transition/receipt; unknown commit later keyed retry; ambient atomic rejection; no lazy serialization queries; generic admin history contains no document events |
|Quotas/dependencies | active19->20allowed/next429; expiry/withdraw free active quota; rolling999->1000allowed/next429; replay/withdraw still work at create threshold; concurrent quota no overshoot; shared limiter60/next429acrossworkers; limiter outage503; disabled metadata503 no lookup; enabled synthetic metadata succeeds with absent storage/scanner while every upload/download flag false |
|API parity | all positives independently of UI; exact closed schemas/error codes/no-store/never304;256KiB envelope; content PUT/GET denied/absent; CurrentUser branch grants exact; no new grant to other roles |
|Future UI/browser | list/detail/empty/unavailable/error/expiry/ownwithdraw; keyboard error summary/Back/focus/close; unknown POST samekey retry; offline refresh; late settlements/context changes; long names/mobile widths; no file chooser/download or SHA256 form; representative synthetic reception task confirms no claim file received |

Actual PostgreSQL race tests use separate connections/barriers and observed pg_blocking_pids()/lock evidence, both serial winners, bounded completion/no40P01; SQLite not evidence:

1. StaffA membership replacement/suspension versus actorB list/detail/create/replay/withdraw. Include replacement Membership FK KEY SHARE against B User NO KEY UPDATE: staff-first denied after wait; document-first committed audited selection then subsequent denial. No target User/org cycle.
2. Identity revoke/disable/epoch bump and initially absent security-profile creation versus B operation: original captured epoch retained, no read-side profile creation, real User lock wait both orders.
3. Same actor/key creates identical versus changed fingerprints, cross-patient/org key reuse; one intent/receipt, one event per successful disclosure. Same/different-key withdrawals increment once; foreign-scope replay never returns original metadata.
4. Withdraw versus detail/list/create-replay, exact expiry crossed during audit INSERT/deferred FK wait, backward clock, version max; terminal projections coherent and failed withdrawal leaves no receipt/event/transition.
5. Different actor creates at patient/org quota threshold: prove gate wait and no overshoot; list<=100intentlocks with concurrent insert; page immutability; no global staff/patient scan locks.
6. Patient PATCH and reception allocation versus metadata: actual Patient wait both orders, no Bed/org cycle; detached patient/document scope snapshot, no later lazy reads.
7. Network allow->deny before final selection rolls back; selected-first may return only already-audited selection. This pair proves ordering, not a fictitious policy-write blocking claim.
8. Forced event/constraint/commit failure/connection loss/ambient transaction misuse: no precommit metadata escape; assert connection recovery and later exact-key reconciliation. Timeout gates require actual installed-driver evidence before a bound is claimed.

## Open freeze decisions and evidence required

Coordinator fresh review must settle (1) measured deferred-check/COMMIT/driver deadline policy, (2) concrete shared limiter backend/algorithm and durable quota query/index performance, (3) metadata runtime activation ownership/discovery wording and whether R04 metadata-only visibility is useful before ingestion, and (4) exact local error normalization against installed DRF/auth/network paths. Numeric quotas and default-disabled deployment flag are proposed engineering rulings, not recorded owner policy. Retention and real-record rollout remain separate release work.

No product tests, PostgreSQL races, browser tasks, deployment or upload safety verification were run for this document. Only the local UI guidance query was executed. Coordinator owns fresh review, HMS/plan/ledger integration and any Git publication. Until freeze, OpenAPI remains46 implemented operations; four proposed operations must not be counted delivered.
