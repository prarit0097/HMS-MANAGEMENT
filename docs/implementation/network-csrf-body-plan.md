# Network JSON body capture before session CSRF parsing

Status: FROZEN by coordinator after real source/scenario/threat/RED review, before production code. Existing network-access contract already requires working session-authenticated CSRF-protected POSTs, exact duplicate-key JSON rejection and an independent 32768-byte backend body limit. No endpoint/schema/permission/session/MFA/CSRF relaxation or deployment is proposed. Root alone approves production code, publishes living docs and runs actual PostgreSQL/browser/VPS checks.

## Root cause and observed RED

Actual installed DRF `SessionAuthentication.enforce_csrf` invokes Django's CSRF checker with the DRF Request. Django `_check_token` accesses `request.POST` even when X-CSRFToken is supplied. DRF Request.POST calls `_load_data_and_files` for JSON, and JSONParser consumes the stream before the network handler's strict `body()` reads it. That handler consequently reads EOF and returns400 for a valid request. The default JSON parser can also fail before the strict handler, yielding its own parse_error or parsing an oversized request first.

Portable real APIClient(enforce_csrf_checks=True) tests in `backend/tests/test_network_access_csrf.py` currently give3failed/3passed: correct cookie/header valid preview400 versus201; malformed JSON uses undeclared parse_error rather than validation_error;32769-byte body400 versus413. Wrong/missing CSRF remains403 and duplicate JSON currently400. These tests create only synthetic existing manager/session/proof fixtures and obtain the real CSRF cookie through the existing endpoint.

## Exact bounded correction

Change only `backend/apps/core/network_api.py` and focused tests. Extract one `bounded_body(raw_request)` byte reader from the existing strict body helper: validate declared Content-Length as currently required, reject declared length>32768, then read at most32769 bytes (or inspect a pre-existing bytes body cache without a new unbounded read), and reject actual captured length>32768. Missing/understated Content-Length does not increase the read allowance. Do not call unbounded `request.body`, accept request.data as authoritative, parse files before this boundary, or log raw body/token/cookies.

For listed POST management actions only, override `NetworkView.initial` INSIDE APIView.dispatch's normal try/exception boundary. Before calling `super().initial` (authentication/CSRF), capture the exact bounded raw bytes. Store them in a server-only request attribute and Django's bounded `_body` cache, and provide a BytesIO replay stream. DRF/Django may perform their ordinary CSRF parsing against this already bounded replay; SessionAuthentication and the real CSRF checker stay enabled and unchanged. Other routes/probe/GET/method behavior is unchanged.

After successful normal authentication/CSRF and existing current network authority, `body()` strictly decodes/parses ONLY the captured original byte string using the existing duplicate-key object_pairs_hook, parse-constant rejection, exact required fields and strict service validation. It never uses DRF's parsed data, even though the framework may have temporarily parsed a replay for CSRF. Duplicate JSON therefore remains invalid. Unsupported media remains415. Map early DRF ParseError to the frozen generic400 validation_error without echoing parser details. Size errors from capture remain413/no-store via the normal exception handler. Capture-limit errors may precede session authentication as a resource boundary; they reveal no ID, owner, policy or authority state and cause no writes.

Framework-private cache/stream use is local and justified by DRF/Django's installed request implementations; no global parser/authentication setting is changed. `_body` contains only an already size-checked bytes object, never an unbounded newly read body. No request attribute is accepted from JSON or HTTP headers.

## Scenarios, abuse and RED/GREEN verification

- Real positive cookie/header/session flow: preview201, activate200; exact original bytes survive CSRF parsing. Add confirm/revert coverage through fresh preview/change IDs where required.
- Missing/wrong CSRF cookie/header stays403 csrf_failed with no preview/change/event writes. Session/MFA/network authority is still enforced before any ID lookup or business mutation.
- Valid CSRF plus duplicate root or nested JSON keys remains400 validation_error; malformed syntax is generic400 with no raw malicious-input echo; non-object/unknown fields and files/unsupported media retain strict rejection.
- Declared32769 and actual32769 bytes reject413 before parsing. A request-stream fixture with missing/understated declared length supplies a real oversized stream and records bounded read size; assert no read exceeds32769 and no business writes. Exact32768 valid JSON plus whitespace is accepted under valid CSRF;32769 rejected.
- Preserve existing network API/body/authority tests, session-free probe behavior and all PostgreSQL races. New runtime changes are only the bounded body capture/replay and generic parse error adapter.

Run tracked positive/negative RED first (observed above), then root gate, minimum implementation, focused GREEN, full local backend/check/no migration drift. Freeze artifact for coordinator actual PostgreSQL and actual synthetic browser retry. No browser-success or post-fix PostgreSQL claim is made by this proposal.
