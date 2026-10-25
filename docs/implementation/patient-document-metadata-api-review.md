# Patient document metadata API contract review

25 October 2026. Independent bounded design review of the **DRAFT / UNFROZEN** [metadata contract](patient-document-metadata-contract.md), read with HMS.md, plan.md, ledger.md, the frozen foundation contract and current API/authentication/authorization/middleware/model source. This report changes no production code, grant, OpenAPI operation, deployment or database. The catalogue remains 46 implemented operations; the four proposed operations are not implemented or accepted.

## Ruling

Do not freeze the present draft verbatim. Its registration-only permissions, current-state replay, expiry projection, omitted content/digest/reason fields and bounded patient-local cursor are coherent with the dormant models. The concrete transport/error contradictions below need explicit decisions before OpenAPI/service freeze. Existing COMMIT bounds and shared-limiter choices remain independent open gates already acknowledged by the draft; this review does not resolve or repeat their implementation work.

## Blocking contract contradictions and smallest corrections

### 1. The closed error table cannot describe the installed authentication and middleware paths

The draft gives unauthenticated SessionAuthentication a 403 `permission_denied` entry and restricts error codes to its table. Installed DRF actually produces **403 `not_authenticated`**, message `Authentication credentials were not provided.` IdentitySessionMiddleware additionally returns **401 `not_authenticated`**, message `Your session ended. Sign in again.`, before a document view can normalize anything when a captured session epoch is stale. The existing service `require_session` also raises SecurityError `not_authenticated` with status401. These are distinct paths and neither is the table's fixed403 envelope.

NetworkPolicyMiddleware runs before sessions/views and can directly return403 `network_denied` or503 `network_policy_unavailable`. The draft expressly retains the former but does not add either code/message to the otherwise closed error schema; its generic503 `document_metadata_unavailable` promise cannot currently replace an earlier middleware response. This is a schema/behavior mismatch, not evidence that an unauthorised document is disclosed.

**Smallest correction:** explicitly distinguish unchanged pre-view network/session errors in the operation schemas and UI settlement matrix, including the existing401 path. For errors raised inside document adapters/services, freeze one local mapping: unauthenticated/stale-session behavior; plain permission403; real-CSRF403; document validation400; operational503. Do not change the shared handler or global identity/network response contracts as an incidental document fix. If a single universal document envelope is required instead, separately design and test a path-scoped middleware boundary that also covers short-circuited requests; a view-only handler cannot deliver it. No platform-MFA-specific document grant is needed: the platform-prefix MFA middleware does not target the proposed patient paths.

Source: `backend/apps/core/api.py:35`, `backend/apps/core/middleware.py:8,58`, `backend/apps/core/identity_security.py:83`, pinned DRF `views.APIView.handle_exception` and `authentication.SessionAuthentication`.

### 2. Content negotiation can escape the closed surface before action checks

Pinned APIView.initial negotiates the renderer before authentication/permissions. An otherwise ordinary anonymous GET with `Accept: application/xml` returns **406 `not_acceptable`**; `?format=xml` returns **404 `request_failed`**. `format` is DRF's default URL format override, so an unknown query key can bypass the draft's required400 query rejection. `Accept: application/json; indent=8` also selects renderer formatting parameters, which should not accidentally undermine a bound defined over exact encoded bytes. Merely choosing JSONRenderer or parsing strict handler JSON does not disable these features.

**Smallest correction:** freeze a document-local content negotiator that always selects the fixed JSON renderer/media type, ignores formatting parameters, and does not interpret `format`; normal closed query validation then rejects `format` with400 after the specified checks. Explicitly document that Accept does not select another representation. Alternatively add406 and its precedence, but the format override still needs removal to uphold unknown-query400. Test authenticated and anonymous requests so precedence is intentional. Do not alter global DRF settings.

Source: pinned `rest_framework/views.py` APIView.initial, `negotiation.py:35`, `settings.py:98`.

### 3. Malformed UUIDs routed through Django's UUID converter do not receive the promised JSON404

The installed UUIDConverter already restricts lowercase canonical hyphenated spelling, but uppercase/malformed segments fail URL resolution **before APIView**. The ordinary Django404 response is not the draft's fixed `{code,message}` document envelope. Existing patient routes use `<uuid:pk>`; blindly extending that pattern would inherit this mismatch. Conversely, `<str:...>` plus Python `UUID()` alone accepts aliases forbidden by the draft.

**Smallest correction:** route the four document shapes with string segments, enforce exact ASCII lowercase canonical UUID grammar in the scoped adapter, and normalize concealed404 locally after the chosen session/action precedence. Explicitly distinguish an unregistered content/unknown route404 from a malformed identifier in a registered document shape, or freeze a scoped fallback response if both must share the JSON contract. No content endpoint should be introduced to provide a prettier error.

Source: `backend/hms/urls.py`; pinned `django/urls/converters.py:28`. Database-free resolution probe confirmed uppercase fails resolution while lowercase resolves.

### 4. Generic DRF exception handling does not enforce the fixed safe messages/codes

Actual `safe_exception_handler` keeps exception default codes and string details. Database-free probes returned400 `invalid` for ValidationError,400 `parse_error` for ParseError,403 `permission_denied` with `CSRF Failed: CSRF cookie not set.`,405 with the supplied method in the message, and415 with the supplied media type in the message. ValidationError field messages are recursively flattened without the draft's field-key/message-count/message-length allowlist. Therefore subclassing APIView and relying on the shared handler violates the proposed fixed codes/messages and no-input-echo rule, even if successful projections are perfectly closed.

**Smallest correction:** a document-only exception/error builder with an explicit allowlist of codes, fixed message strings, bounded safe field messages and field keys; recognize actual CSRF failures separately; map parser recursion/parse errors at the real pre-handler boundary; convert relevant backend failures only after atomic exit. Do not forward arbitrary `str(exc.detail)` or generic serializer error text. Preserve existing ordinary session/CSRF checks. Closed schemas should describe actual normalized responses rather than the shared handler's current defaults.

Source: `backend/apps/core/api.py:35`; existing network-specific normalization at `network_api.py:71,88` is useful evidence but has different body bounds/messages and is not a drop-in document implementation.

### 5. Accepted JSON strings can contain lone surrogates that cannot be persisted/encoded

The filename/reason grammar rejects controls and bidi controls, but does not reject Unicode surrogate code points. Strict UTF-8 input containing JSON escape `\ud800` is legal byte input to Python's JSON parser; it becomes a length1 Python string, survives strip and all listed character restrictions, then raises UnicodeEncodeError when encoded as UTF-8. Fingerprint `ensure_ascii=True` would not catch this first. This makes a supposedly valid declaration fail later in PostgreSQL adaptation or result encoding rather than receive deterministic400.

**Smallest correction:** define accepted strings as Unicode scalar values and explicitly reject U+D800..U+DFFF in filename/reason after JSON decoding. Valid surrogate-pair escapes decoding to a single scalar remain acceptable if all other rules pass. Add lone-high/lone-low/pair tests across create/withdraw; keep the existing code-point length and no-normalization choices. Do not silently strip or replace invalid values.

Evidence: actual pinned-environment Python JSON probe decoded `{"filename":"\\ud800"}` to U+D800; length1, unchanged by strip; UTF-8 encode raised UnicodeEncodeError. This was a parser/encoding probe, not a database test.

## Further freeze precision

1. **Failure precedence:** state/version/creator checks can all fail together. Specify one order, including new-key expired+stale-version and another-creator terminal intent. A safe coherent choice is current scope -> creator -> valid existing replay/fingerprint -> new-command terminal state -> version/max-version -> mutation. Validate replay fingerprints/current scope before disclosing any result; successful original replay remains exempt from transition/deadline/version checks. State explicitly whether same-key changed payload checks precede referenced-result consistency failures.
2. **Methods:** default APIView gives HEAD the GET handler and OPTIONS a metadata response, both observed200 in the probe. Freeze per-resource `http_method_names` and local405 mapping; method rejection must not invoke the GET disclosure/event path. Decide whether authentication/action failure precedes405 on unsupported methods because APIView.initial precedes method dispatch. Existing global/network behavior is not proof of document405 behavior.
3. **Header ownership:** `Vary: Cookie` on every error cannot be guaranteed by SessionMiddleware alone: network denial returns before it runs. No-store is currently applied by NetworkPolicyMiddleware, and nosniff by outer SecurityMiddleware; document-view finalization cannot add headers to responses already short-circuited outside it. Freeze either scoped outer header handling or an explicit preserved-middleware exception. Test fully rendered responses through the whole middleware stack, not only APIRequestFactory.
4. **Cursor/query canonical grammar:** QueryDict.items collapses duplicates (observed `limit=25&limit=50` exposes only50), so inspect getlist/lists. State exact ASCII limit grammar (including leading zero policy), cursor integer `v` type (reject bool), canonical JSON field order/serialization policy if re-encoding equality is required, and canonical base64url round-trip. Require a valid actual UTC datetime, not regex shape alone. Cursor position need not refer to an existing row; authorisation is independently rechecked.
5. **Original-byte transport:** the draft correctly anticipates the installed real-CSRF JSON parser behavior. Django CSRF's token check accesses DRF Request.POST before the header fallback; installed JSONParser uses json.load, and ParseError/RecursionError can occur before the handler. Keep capture/replay before super.initial and preserve real-CSRF tests. A plain Content-Length check or strict handler-only parser is insufficient. This review did not rerun the existing network suite or prove new document bounds.

## Permission, expiry, replay and disclosure review

No additional model change is needed merely to express the four proposed contracts. The foundation already bounds metadata states/version/expiry and stores receipt/result pointers and dedicated audit events. Existing ROLE_PERMISSIONS and current_user branch_permissions shapes can express the proposed reception-only grants; documents-A must still test the conjunction in A, not the global permission union or a union across branches. The proposed master exclusion is consistent with today's map. The current generic branch_ids helper checks a single action, so future code must explicitly intersect all required current exact-branch actions and recheck after waits.

Pure pending-to-expired projection at selected_at>=expires_at, immutable create timestamps and current-state replay are consistent. Keeping withdrawn terminal and replaying the already-successful withdrawal after expiry avoids a false second transition. Detail/list replay disclosure still requires a new committed event. Failure responses must never expose original receipt result pointers, filenames, creator identifiers, reason or content hash. The receipt table's actor+operation+key unique constraint supports the specified namespace, but does not by itself prove safe concurrent claims or reauthorisation; those remain planned service/race tests.

The unsigned cursor is appropriate as a bounded position, provided patient/category/canonical parsing are checked and current scope is re-authorized; signing is not required merely to conceal values already disclosed by the same authorised list. IDs-only event digest intentionally binds disclosed identity/count, not every changing projection field; do not describe it as a digest of complete response content. All flags remain upload/download false, and no byte-receipt, content, clinical or ready behavior is accepted by this review.

## Evidence actually executed and limits

Executed one database-free Python heredoc using `backend/.venv/Scripts/python.exe`, setting only DJANGO_SETTINGS_MODULE and Python module path. Confirmed **Django5.2.18 / DRF3.16.1**, matching requirements. APIRequestFactory created minimal temporary in-memory APIView classes with the installed project settings/error handler; no URL/service/model production edits, sessions persisted, database access, network requests or migrations were used. Observed:

| Probe | Observed result |
|---|---|
| Anonymous GET |403 `not_authenticated` |
| Anonymous GET Accept XML |406 `not_acceptable` before auth |
| Anonymous GET format=xml |404 `request_failed` before auth |
| Default public OPTIONS / HEAD |200 metadata /200 GET data |
| Session-authenticated POST, missing CSRF cookie |403 `permission_denied`, framework CSRF reason |
| Shared ValidationError / ParseError |400 `invalid` /400 `parse_error` |
| Shared MethodNotAllowed / UnsupportedMediaType |405/415, supplied method/media in message |
| UUID converter lowercase / uppercase |resolves /Resolver404 |
| QueryDict duplicate limit |items collapses to last value; lists retains both |
| Escaped lone surrogate |decoded, then UTF-8 encode fails |

Source inspection additionally covered actual pinned framework auth/negotiation/CSRF/parser/UUID code and current project role map, middleware, session epoch services, URL registration and three foundation models. Middleware401/network short circuits are source-confirmed, not end-to-end probe claims. No product tests, PostgreSQL race, full suite, browser task, runtime activation, storage/scanner test, COMMIT-deadline measurement or release acceptance was run. Coordinator owns contract corrections, HMS/plan/ledger integration and Git publication.
