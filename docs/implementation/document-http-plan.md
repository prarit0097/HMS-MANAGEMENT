# Document metadata HTTP transport implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: coordinator uses subagent-driven-development or executing-plans, test-driven-development, review and verification task by task. Root alone Git/VPS. Disjoint tests may run in batches within available slots; no duplicate team.

**Status:** 3 November2026, FROZEN B3 implementation contract after three independent contract/security/test reviews, scoped parser/precedence/schema review and concrete ingress-design review. Root chose the bounded rules below. Full schema CI, executable RED, implementation and actual runtime acceptance remain pending; no HTTP capability is delivered by this freeze.

**Goal:** Expose the four already-catalogued registration metadata operations through strict authorised HTTP adapters over completed B1/B2a/B2b, without UI, bytes, storage or activation.

**Architecture:** A document-local DRF adapter bounds raw bytes before ordinary session/CSRF processing, mints exactly one original context after authentication, calls exactly one existing raw-input business service and returns its committed JSON bytes directly. Fixed negotiation/errors/headers remain local. Trusted HTTP framing is a separate edge/server gate; a bounded Django stream cannot reveal inaccessible trailing bytes.

**Tech stack:** Retain Django5.2.18/DRF3.16.1/psycopg3.2.12/PostgreSQL>=17/Gunicorn26.2.0/Nginx1.24 and current dependencies. No schema/grant/setting/defaultFalse change.

**Spec:** [parent contract](patient-document-metadata-contract.md), [completed business plan](document-business-plan.md), [authority](document-authority-plan.md), [admission](document-admission-plan.md), [OpenAPI](../api/openapi-v1.yaml), [page actions](../api/page-actions-v1.json), [HMS](../../HMS.md), [plan](../../plan.md), [ledger](ledger.md), [current source/runtime receipt](../operations/document-business-preview-evidence-2026-11-03.json).

## Intent, choices and boundary

Existing services already own validation, admission, current exact-branch scope, quota/replay/state, mandatory disclosure audit, transactions and known-commit detached results. Options: use generic DRF serializers/rendering/global exceptions (changes original bytes and violates closed failure handling); duplicate services inside views (diverges authority/commit paths); or narrow local adapters. Coordinator chooses adapters under existing owner-authorised scope. Routine technical decisions below require no new product/activation decision. This draft does not waive the planning/security gates.

Current restricted preview260eeb9/core0009/False remains separate. B1/B2a/B2b and its tests, schema, grants, environment, middleware, existing endpoint behavior and frontend are consumed unchanged. No encounter/clinical/file/content/upload/download routes, new membership discovery, MCP bypass, new dependencies or paid provisioning. Registration intent remains a declaration, not proof of received bytes. R04 document UI stays deferred until useful ingestion and its acceptance.

## File ownership and pinned interfaces

- NEW `backend/apps/core/document_api.py`: `DocumentTransportError`, `_capture_body(raw_request) -> bytes`, `_document_response(body: bytes, status: int) -> HttpResponse`; document-local opaque parser, negotiator, session authentication and common `DocumentView`; `DocumentCollectionView`, `DocumentDetailView`, `DocumentWithdrawView`.
- MODIFY `backend/hms/urls.py`: three string-segment patterns only, exposing four operations. Do not use UUID converters or register format/content suffixes.
- NEW `backend/tests/document_http_fixtures.py`: synthetic real DBSession/CSRF factories; no adapter import at collection. One owner writes shared fixtures before dependent test files.
- NEW `backend/tests/test_document_metadata_http_contract.py`: route/method/query/header/response/expected-error boundaries.
- NEW `backend/tests/test_document_metadata_http_csrf.py`: actual CSRF plus opaque parser, original byte bounds/replay and stream evidence.
- NEW `backend/tests/test_document_metadata_http_pg.py`: genuine full-middleware HTTP lifecycle/scopes/replays/audit/disabled/fault effects, transaction=True and actualPG only.
- NEW `infra/edge/tests/validate_document_framing.py`: root-owned isolated HTTP framing runner described below; no live deployment capability. NEW `infra/edge/tests/test_document_framing_source.py`: literal RED safety/config/renderer/process ownership contracts before that runner.
- Coordinator updates parent/OpenAPI/page-action disposition, exact schemas/statuses, records and reviewed isolated framing/preview procedure. Concrete harness ownership is frozen below; no ad hoc live proxy changes.

Service wrappers stay `list_document_intents(context,patient_id,query_pairs)`, `get_document_intent(context,patient_id,document_id)`, `create_document_intent(context,patient_id,key,body)`, `withdraw_document_intent(context,patient_id,document_id,key,body)`. No public prepared/admission/actor-ID shortcut. Import errors must not cause test collection failures in literal RED.

## Routes, methods and operation authority

Let P=`/api/v1/patients/{patient_id}/documents/`.

| Registered shape | Supported methods/service operation | Unsupported-method authority | Exact Allow |
|---|---|---|---|
| P | GET intent.list; POST intent.create | intent.list | GET, POST |
| P{document_id}/ | GET intent.detail | intent.detail | GET |
| P{document_id}/withdraw/ | POST intent.withdraw | intent.withdraw | POST |

Set http_method_names to get/post as appropriate; explicitly reject HEAD/OPTIONS/PUT/PATCH/DELETE after the mapped global authority without service/admission/object lookup. No automatic HEAD-to-GET or metadata OPTIONS execution. HEAD has405 status/headers and no wire body by HTTP semantics, not JSON-body-on-wire acceptance. Wrong/unregistered shapes, including P{UUID}/content/, remain ordinary Django404 outside the local envelope. Parent's exact path/key canonical grammar remains enforced by B1/service; registered malformed path UUID gets local concealed404 after auth/global checks.

## Ordered local pipeline and clock boundary

1. Existing outer network/session middleware short-circuits retain their current envelopes/headers. No new universal Vary promise applies to pre-view failures.
2. Bounded raw capture before DRF authentication/parser. Safety exceptions400 malformed/missing-required framing and413 declared/observed oversize may precede authentication/action denial. This explicit exception supersedes blanket action-first wording only for local raw framing/resource safety; it never performs object lookup or admission.
3. Fixed document-only negotiation, ordinary SessionAuthentication with real CSRF and IsAuthenticated. Local anonymous403 `not_authenticated: Sign in to continue.`; genuine stale service context401 and preserved stale-session middleware401 keep the existing ended-session message. Ordinary CSRF can precede action denial for unsafe methods.
4. Mint one `capture_document_context(raw_request, operation)` under the route table before dispatch. This starts the existing cooperative budget AFTER bounded capture/session/CSRF, not at socket entry. Pass that same context once; no remint/reset. No five-second whole-HTTP/COMMIT/delivery promise.
5. Unsupported method returns local405 immediately; do not validate target/media/query/domain for those methods after authority. Supported handlers enforce transport restrictions, then call exactly one public service with original raw inputs.
6. Return `HttpResponse(result.body, status=result.status, content_type='application/json')`. Do not parse, decode, render or query after service return. Validate only trusted result type/expected status200/201/type bytes/<=262144; malformed results fail503, no projection. Client disconnect may lose a committed reply; existing explicit same-key reconciliation remains, not rollback/delivery assurance.

## Body, framing and real CSRF

POST requires one server-delivered CONTENT_LENGTH ASCII decimal string; missing/empty, negative/sign/nonASCII/comma/malformed values400. Leading zeros are permitted for this transport count, not for list limit. Declared size>4096 returns413 without reading. Independently request at most4097 visible original bytes; observed>4096 returns413 even if a test stream has false declared length. Existing `_body` must be exact bytes<=4096; no consumption of an already-read stream without a complete body cache. RequestDataTooBig maps413; expected malformed/read-state failure400, dependency/read I/O failure503; never unbounded reads/readline or trusting declared count alone. Non-POST methods also bound capture when needed for ordinary CSRF; supported empty GET inspects at most1 byte, then rejects nonempty400 AFTER context and before service. Unsupported HEAD/OPTIONS do not run GET validation or disclosure.

Replay only accepted bounded bytes via raw `_body` and BytesIO stream. NEW document-local opaque BaseParser with media_type=`*/*` returns `{}` and performs ZERO read/readline/decoding calls; it grants no command validity. SessionAuthentication subclass calls ordinary `super().enforce_csrf()` and converts only that call's PermissionDenied into typed local csrf_failed. Cookie/header token and Origin/Referer checks remain real. A form-body csrfmiddlewaretoken is not a substitute for the required header. Multipart/file parsing never executes; valid header may proceed to415, missing/wrong CSRF remains403. Handler never reads `request.data` as command input; strict B1 validation consumes captured original bytes inside the single service.

POST media grammar: case-insensitive ASCII application/json with optional SINGLE charset=UTF-8 (quoted or unquoted); ASCII spaces/tabs around separators/outer value accepted; no other/empty/duplicate parameters or charset aliases. Nonempty Content-Encoding rejects415. Empty GET needs no Content-Type. Range header presence rejects400 for supported handlers. No user header value appears in errors.

Malformed/duplicate nested JSON/nonfinite/BOM/UTF8/surrogate/depth remain B1 responsibilities proven through real CSRF transport. Duplicate query pairs use flattened `.lists()`, never collapsed `.items()`. Only list accepts existing limit/category/cursor grammar; all other operations require empty query. `?format=xml` is ordinary unknown query400 after auth, never negotiation404. Duplicate physical headers hidden/normalized by the server are an ingress concern; an exposed comma/multiple UUID key string fails canonical400.

### Framework feasibility and ingress release gate

Actual installed Django5.2.18 WSGIRequest probe with4097 underlying bytes and read(4097) observed missing length0, declared8 length8, correct4097 length4097. It did not replace `_stream`. [Django primary source](https://raw.githubusercontent.com/django/django/stable/5.2.x/django/core/handlers/wsgi.py) confirms LimitedStream uses delivered Content-Length; [Gunicorn26.2.0 source](https://raw.githubusercontent.com/benoitc/gunicorn/26.2.0/gunicorn/http/wsgi.py) supplies WSGI input. Consequently, the adapter cannot detect bytes already hidden by false/missing WSGI framing, and must not unwrap private stream internals or read past the server-defined entity. Direct-origin transport remains private.

[Nginx request buffering documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_request_buffering) documents buffering before proxy forwarding. Existing HMS edge bound64KiB is not a4KiB document entity guarantee. Actual isolated Nginx/Gunicorn chunked forwarding/rejection, missing/short/oversized length, duplicate/conflicting Content-Length and TE/CL handling must be tested before B3 deployment/framing acceptance. Valid server-delivered body4096 success/4097 rejection and no admission on malformed entities must be observed through the actual route. Chunked support is NOT promised: if the trusted stack supplies canonical CONTENT_LENGTH, apply the normal bound; if absent, the fixed POST400/no-admission rule applies. Test-client stream instrumentation proves only bounded adapter requests, not trusted framing. No current source/live edge attestation is inferred. Unexpected ambiguous-framing acceptance blocks release; it never silently authorises a proxy amendment.

### Exact isolated harness design

Runner accepts ONLY `--config /opt/hms/validation/network-edge-pg-20261024/runner-config.json`, root-owned regular0600 with safe ancestry and exact existing helper shape/default-only TLS database hms_edge_validation_20261024/hms_edge_app/127.0.0.1:15549. Verify actual server/user/IP/PG>=17 and empty disposable DB before fixtures. Existing receipt/label/image/mount/port-validated `prepare_isolated_pg.py up/down` owns database lifecycle; root runs cleanup even on interruption. No live/shared HBA, role, DB, service, firewall, proxy, dependency or paid-resource changes.

Fixed new SOURCE=`/opt/hms/validation/document-http-source-20261103`, runtime PREFIX=`/opt/hms/validation/document-http-edge-20261103`, existing venv=`/opt/hms/validation/identity-20261023/venv`; Gunicorn127.0.0.1:18185 and standalone Nginx HTTPS127.0.0.1:18186. Reject preexisting runtime/source collision, symlinked ancestry, busy ports, wrong binary/package versions/config shape and unverifiable candidate manifest. Candidate source is staged once by root with complete canonical manifest; reruns inspect/reuse only verified immutable source, never overwrite an unknown directory. Private runtime created by this run is0700; credentials/config/TLS/logs/report0600. No stdout credentials/body/exception detail.

Consume existing `validate_config` and `render_nginx(SOURCE,baseline=False)` as pure utilities ONLY. Replace every old runtime PREFIX literal in rendered text with this new PREFIX; assert old source/runtime and live `/opt/hms/current`/`/etc/letsencrypt` paths absent; verify every included source file against the candidate manifest. Do NOT call old Validation.prepare/launch/stop or mutate its module globals. It would repeat old wildcard304/outage/privileged tests and use different ownership. Copy only reviewed owned-process mechanics into the new runner under its own constants and executable safety tests.

Record isolated deviations explicitly: client_body_timeout2s for incomplete-body experiments; TLS listener retains the production HTTP2 capability for normal protocol checks. These do not change live settings or prove an SLA. Socket timeout6s and whole-case monotonic deadline10s exceed the2s server body timeout. Launch only returned Popen handles with start_new_session=True; register groups immediately, bounded TERM/KILL/reap, listener checks and ORM closure before helper down. Interrupts follow the same cleanup. No pkill/global Nginx reload/service start/reverse/bootstrap. Preserve a redacted report before literal owned-runtime removal; candidate source stays for root recovery.

Harness-only WSGI wrapper delegates unchanged `hms.wsgi.application`; records only FIXED-ENUM scenario ID, numeric/absent/invalid length class, enumerated TE class and response status/app-reached flag. Zero input reads/replacement, no command implementations, cookie/Origin/body/header logging or response mutation. Synthetic network owner may exist solely for the required existing overlay; use a separate ordinary reception user/branch/patient for B3. Real password login/session/CSRF over actual TLS; metadata True only in isolated child env. Test clients never receive real owner credentials or invoke live services.

Raw HTTP1.1 sender uses ssl sockets and exact literal framing, bounded response memory and deadlines; no library normalization for malformed headers. Each case snapshots allowance/intent/receipt/event state before/after; genuine normal lifecycle proves all four operations. Valid finite create/withdraw4096 succeeds,4097→413/no allowance; nonempty GET400/no effects; missing length400 or observed edge protocol rejection/no effects; truncated declared JSON400/no effects; longer-than-supplied incomplete entity must yield an observed protocol rejection/408/confirmed close and zero effects, not a client timeout accepted as success. Duplicate identical/conflicting CL and TE+CL MUST reject without admission; unexpected acceptance blocks rollout. Invalid chunk sizes/terminal/conflicting TE similarly require explicit rejection. Valid chunked4096 follows observed delivered-length rule above;4097 never admits. Wrong-body cases run through collection POST and withdrawal POST; normal GET collection/detail complete the route matrix.

A short declared entity that itself contains valid JSON followed by extra bytes may be a valid first request plus another malformed/pipelined request. The first command may commit. Record this separate observed case; never promise zero allowance or rollback for inaccessible trailing bytes outside the server-defined first entity. Finite HTTP2 GET/POST4096/4097 and missing/mismatched Content-Length cases use existing HTTP2-capable curl with private0600 config/body/cookie files and verify negotiated version2. Missing HTTP2 tooling or inconclusive outcomes leave that acceptance gate open; no dependency install. This matrix is scoped compatibility/framing evidence, not complete HTTP2/request-smuggling certification.

## Local response and failure contract

Fixed local JSON negotiation ignores Accept/indent; disable format-suffix/URL-format negotiation and metadata, not strict query validation. Error builder emits only code/message, a permitted minimal subset of optional parent fields; no arbitrary detail/serializer/input/PHI/SQL. No field_errors/request_id is emitted in B3. Preserve existing fixed service vocabulary/status/messages; transport additions use parent csrf_failed403 `Refresh the page and try again.`, method_not_allowed405 `This action is unavailable.`, unsupported_media_type415 `Use a supported request format.`. Separate anonymous403 schema from ended-session401; do not silently widen their messages.

Expected DocumentServiceError tuples are revalidated against the fixed vocabulary; malformed tuples or unknown dependency/security exceptions yield fixed document_metadata_unavailable503 after service unwinding. Typed local CSRF failure never requires substring matching or forwarding exception details. Parse/recursion/known input-validation errors400; declared/observed oversize413. Retry-After appears only for rate_limited429 exact int1..3600 (actor emission still1..60); no arbitrary retry header. Unknown exceptions failclosed503 without rendering traceback/detail; preserve normal process-control exceptions.

Every LOCAL success/error/initial/405 response: Cache-Control no-store, merged Vary containing Cookie, nosniff; fixed application/json; no ETag/Last-Modified, never304. Allow is route-specific table above. Outer Security/Session middleware may add ordinary cookies/Vary; preserve existing pre-view exceptions.

## Review focus and test design

1. Default DRF negotiation/JSON/HEAD/OPTIONS must not precede intended authority or parse original bytes away.
2. Resource safety precedes auth only by explicit bounded-framing exception; GET/header/query rejection cannot consume service allowance or audit.
3. Genuine resolved DBSession+real CSRF is required; force_authenticate/injected contexts do not prove it.
4. Committed bytes must not be re-rendered, and a failure must never leak a partial/sensitive success.
5. A replaced stream cannot close the real WSGI/ingress framing gate; missing/short hidden bytes remain an explicit limitation until actual cross-layer evidence.

### Task1 — complete contract and framing design gate

- [x] Root reconciles independent review rulings, actual local WSGI probe and exact ingress harness/config/path/process/resource/cleanup ownership above before final freeze.
- [x] Amend parent/OpenAPI/page map to completed internal-service status, four HTTP operations STILL planned, separate anonymous403 schema, framing/auth/method/clock rules. Local JSON/semantic/map/link checks precede publication; full OpenAPI validator CI must pass before production code. No false source/runtime status.
- [x] Fresh scoped contract/security review closed the reported framing/precedence/schema design issues; concrete ingress design received read-only material review. Root records final choices including protocol limits; no runtime acceptance inferred.

### Task2 — literal executable RED before production

- [ ] Shared synthetic fixtures use genuine persisted DBSession via force_login plus auth_epoch and GET auth/csrf; APIClient(enforce_csrf_checks=True). Include one real password login path. No real data, platform-owner fixtures or production activation.
- [ ] Disjoint HTTP contract tests: all shapes/methods/authority ceilings, canonical path/query/key, anonymous403/stale401, fixed Accept/format/Allow/header/no304/error mappings and exact service-byte handoff. Missing route fails assertions, not collection/setup.
- [ ] Real-CSRF tests: cookie/header/Origin/body-token rejection, zero-read opaque parser, no multipart uploads, valid4095/4096/4097 payloads, raw duplicate/depth/UTF8/nonfinite and GET body, instrument read AND readline. Label framework-stream versus actual ingress evidence.
- [ ] ActualPG HTTP tests: four-operation lifecycle/replay/current exact-branch scope/cursor/creator/version/quota representative; each valid success one allowance/event; defaultFalse valid503 retained allowance/no business access; malformed/CSRF/405 no allowance; genuine event-insert failure/labelled lost-ACK503 plus explicit keyed reconciliation. Consume existing full business races, do not duplicate them.
- [ ] Root runs portable and actual isolatedPG RED and saves exact results before production. Freeze test seams; no stub success or SQLite business-success fallback.

### Task3 — minimal adapters and source acceptance

- [ ] Implement only document_api.py and three URL patterns. B1/B2a/B2b/middleware/other endpoints untouched; reproduced shared defects need their own scope amendment/RED.
- [ ] Targeted portable/actualPG GREEN, independent source/spec/security review; each material defect gets reproducing RED then minimal correction.
- [ ] Root full actualPG backend/check/no drift, contract/schema/map/docs/root checks; exact source manifests; representative unchanged endpoint regressions. Do not claim frontend/browser/staff acceptance from backend tests.

### Task4 — runtime/framing and publication

- [ ] Actual isolated Nginx/Gunicorn framing acceptance under frozen harness passes on exact final source; retain raw protocol/status/allowance effects without credentials/payload logging. This remains a release gate, not a unit-test inference.
- [ ] Update OpenAPI/page map implemented status only for source-accepted operations, separately list runtime flagFalse and UI deferred. Source-verified normal push/remoteSHA and exact successful CI before immutable preview candidate.
- [ ] Freeze reviewed HMS-only source rollout amendment: fresh backup/key/inventory/state, isolated disabled HTTP request allowance retention proof and prior260 source compatibility with all rows retained; no live admission/business invocation or flag enablement. Verify existing live behavior plus new safe route availability/failure boundaries without invoking live command paths. No DDL/bootstrap/policy/other-app change.
- [ ] Reviewed rollout/live preservation/postbackup restore/key/cleanup, explicit source/deployed distinction and final HMS/plan/ledger/evidence push/remote verification. Code cannot be declared completed/deployed until these gates pass. Browser/staff/phone, useful ingestion/UI/full release stay open.

## Draft disposition

This root freeze reconciles existing owner-authorised four-operation scope. Three initial reviews plus scoped parser/authority/schema and concrete ingress reviews resolved the reported design gaps. The added HTTP2 normal-client gate and precise short-entity limitation are coordinator choices; failure blocks release rather than weakening transport. No production/test module, route, service, runtime or deployment was changed by this plan. Contract CI/executable RED and all runtime gates still precede their corresponding code/release claims. Do not repeat completed foundation/business slices.

## Initial executable RED disposition —3 November2026

Plan64e5234 exactCI41607310566all3success includesfullOpenAPIvalidator; schema/map/linkchecksclosed. [Initial39case receipt](../operations/document-http-initial-red-2026-11-03.json):32portableFAIL/1pass/6PGskip and38actualPGFAIL/1pass/0errors8.16s, allabsentroutes. Task2fullmatrix/fixture-review/rawCSRF/harnesssafety tests remainincomplete. Lifecyclecumulativeallowance requires per-call/minute-boundary precision before GREEN. No production source/route/harness is implemented; do not treat thischeckpoint as deployable or source-complete.
