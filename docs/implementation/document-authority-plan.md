# Document metadata authority foundation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use installed `executing-plans` or coordinator-selected `subagent-driven-development` task-by-task, with RED-first and verification/review skills. Coordinator alone freezes, assigns, commits/pushes and deploys shared-checkout work.

**Status:** 28 October 2026, **B2a-A IMPLEMENTED / SOURCE VERIFIED / PREVIEW ROLLOUT PENDING** after coordinator reconciliation and independent scenario/security review. Later B2a-L durable admission remains DRAFT. This design claims no implementation, test or deployment result.

**Goal:** Supply a narrowly scoped, read-only session/context/global-action authority boundary and immutable final network/time evaluation for future document services.

**Architecture:** Validate genuine existing database sessions independently of cached authentication, mint a process-private context, and materialise detached authority/network samples. A pure final selector checks those samples at an explicit caller-selected instant. Reception receives only the already planned document permission strings; no document action becomes callable through HTTP.

**Tech stack:** Existing Django5.2.18, configured default User/ModelBackend, database SessionStore, pytest/pytest-django; SQLite read-only tests and coordinator-owned isolated PostgreSQL17 verification. No dependency installation.

**Spec:** [admission contract](patient-document-metadata-admission-contract.md), [parent metadata contract](patient-document-metadata-contract.md), [service review](patient-document-metadata-service-review.md), [service plan](patient-document-metadata-service-plan.md), [HMS](../../HMS.md), [project plan](../../plan.md), [ledger](ledger.md). Proposed rulings here require coordinator propagation where parent wording differs.

## Global constraints and completed inputs

- B1 `document_contracts.py` is complete at66bfa10160eae5342b0b64a601ad05b992d40753 and is unchanged. This subset performs no command/body/query parsing.
- Coordinator records deployed source3dd803f844b47aaa67fbd0cdc6be22185bba344c/core0009 and completed B2a-S evidence. Consume that schema unchanged; no rate-model, discovery, migration or historical schema-test edits and no new schema gate.
- No limiter row reads/writes, feature setting, admission/result factory, patient/document/receipt/event lookup, audit write, business service, HTTP/URL/OpenAPI/page-action, UI or storage work. Four metadata operations stay planned;46 existing HTTP operations stay implemented. No public function accepts an actor ID or trusted boolean in place of captured authentication.
- No session/profile creation or mutation, global logout change, privileged platform/network authority, network repair/reconciliation, new lock class or provider. Existing middleware semantics remain unchanged.
- Default-disabled behavior and shared five-second cooperative monotonic orchestration belong to B2a-L. Pure selection below never reads a clock or performs I/O. This subset may capture the existing proposed monotonic start scalar for its later consumer, but does not enforce an admission budget.
- Every completed code change requires verified push, reviewed restricted-preview rollout, live verification and accurate MD records under the owner's standing rule. No runtime document activation or hospital-release claim follows from this authority subset.

## File ownership

| File | Allowed change |
|---|---|
| `backend/apps/core/document_authority.py` | NEW fixed errors, private mint, read-only session/global checks, detached samples, pure final selection |
| `backend/apps/core/authorization.py` | Add only `documents.registration.read` and `documents.registration.write` to `ROLE_PERMISSIONS['reception']` |
| `backend/tests/test_document_metadata_authority.py` | NEW genuine-session, permission, representation, immutability and network/time tests |
| `backend/tests/test_document_metadata_authority_pg.py` | NEW disjoint actual-PG authority identity/first-profile lock and session/network visibility tests; no limiter tests |
| `backend/tests/test_document_metadata_grants.py` | NEW disjoint exact CurrentUser/reception-only grant ceiling tests |
| HMS.md, plan.md, ledger and source/live evidence | Coordinator publication only; not implementer ownership |

No `document_access.py`, settings, models, prior tests or network/identity/auth modules change. If existing behavior blocks a requirement, report it for a separately reviewed scope amendment rather than expanding this file list.

## Exact proposed interfaces and values

All classes/functions live in `apps.core.document_authority`. Operations are exactly `intent.list`, `intent.detail`, `intent.create`, `intent.withdraw`. Unknown operation or invalid/foreign/directly constructed context fails generic unavailable503 before authority is granted. Invalid authentication is401; authenticated absence of global same-branch action is403. An exported class is not a trusted factory: helpers check a process-private mint identity, exact issued-object identity and context identity bindings. Each context and each sample has a distinct private proof bound through weakref to the exact object issued by its legitimate helper; validation requires proof.target() is that object. A copied/replaced dataclass retains proof bound to its original, so is rejected503, including changed actor/expiry/branch/policy or an otherwise equal clone. Proof creation is internal; direct constructors, dataclasses.replace and copy.copy are never issuing factories. No global strong registry retains request/sample history. Trusted Python holding session secrets is outside this token's protection.

### Context and sample shapes

All three dataclasses are frozen, and all returned nested collections are immutable detached copies. No model, queryset, lazy relation, SessionStore, raw session key, auth hash or mutable policy graph is a public returned field. Private fields are excluded from repr/comparison. Dataclass freezing does not freeze the private live request graph.

| Type | Exact fields |
|---|---|
| `DocumentContext` | `actor_id: int`; `captured_epoch: int | None`; `operation: str`; `session_digest: str`; `remote_addr: str`; `forwarded_for: str | None`; `verified_ip: str`; `environment_digest: str`; `operation_started_at: datetime`; `monotonic_started_at: float`; private `_request: HttpRequest`, `_mint: object` |
| `DocumentAuthoritySample` | `actor_id: int`; `captured_epoch: int | None`; `operation: str`; `expires_at: datetime`; `eligible_branches: frozenset[UUID]`; `sampled_at: datetime`; private `_context: DocumentContext`, `_mint: object` |
| `DocumentNetworkSample` | `environment_digest: str`; `verified_ip: str`; `environment_policy: PolicyRules`; `confirmed_policy: PolicyRules`; `candidate_policy: PolicyRules | None`; `pending_change_id: UUID | None`; `activated_at: datetime | None`; `rollback_at: datetime | None`; `sampled_at: datetime`; private `_context: DocumentContext`, `_mint: object` |

`PolicyRules` is an immutable tuple shape `(allowlist_only: bool, allowlist: tuple[str, ...], blocklist: tuple[str, ...])`, copied from already validated existing environment/policy values. It is internal data, not a new authority factory. Evaluate its rules without exposing a mutable original dictionary. All session/network descriptors (`session_digest`, remote/header/IP/digests/policies, including nested network fields) use `repr=False`. Context actor/operation/time fields may be represented. Raw key/auth hashes never enter any dataclass.

`sampled_at` on authority is a fresh aware server time captured after its materialisation; on network it is the explicit aware `now` supplied to its existing loader. The latter is a pre-read sample time, not a claim that it was captured after the SELECT. Every sample must bind the exact context object and operation; selection rejects cross-context, forged or foreign-mint samples even when actor IDs coincide.

### Fixed safe errors

`DocumentServiceError(code: str, status: int, message: str, retry_after: int | None = None)` exposes only fixed values, with no original exception/input/database/network details. This subset emits no429; `retry_after` is always None.

| Code/status | Exact message |
|---|---|
| `not_authenticated`401 | `Your session ended. Sign in again.` |
| `permission_denied`403 | `You do not have access to this action.` |
| `network_denied`403 | `Access is not available from this network. Contact your administrator.` |
| `document_metadata_unavailable`503 | `Document details are unavailable. Try again later.` |

The constructor accepts only the four exact code/status/message tuples above and retry_after=None for this subset; any unknown code, mismatched status or arbitrary message is rejected without retaining the supplied value. Implementers may use a private fixed-code factory; no raw exception text is exposed. These are internal service errors. Preserve existing pre-view HTTP authentication/CSRF/network responses; this subset adds no adapter or error-response mapping.

### Capture and read-only session algorithm

`capture_document_context(request: HttpRequest, operation: str) -> DocumentContext` rejects an ambient atomic block OR manual `autocommit=False` before DB reads. Capture aware wall start and monotonic start once before preliminary reads. It does preliminary unlocked authentication/global-action checks, current environment snapshot and trusted socket/header IP normalisation; it does not read the durable network graph. Environment denial is generic403, malformed/unavailable environment or normalisation failure is unavailable503. Durable overlay acceptance is not implied by a minted context.

Supported configuration is exactly `django.contrib.sessions.backends.db` and `AUTHENTICATION_BACKENDS == ['django.contrib.auth.backends.ModelBackend']`; unsupported engine/backend is503. Require `type(request.session) is django.contrib.sessions.backends.db.SessionStore`, checking exact type before any potentially overridden property; a subclass is rejected. Require an existing syntactically valid key and a raw Django HttpRequest. No plain dict/session substitute or DRF wrapper is accepted. The later adapter unwraps its raw request after ordinary authentication/CSRF.

Inspect request state without evaluating an unresolved `SimpleLazyObject`: an unresolved `_wrapped` sentinel denies401; an already-resolved wrapper may supply its wrapped configured User instance. A concrete configured User instance is also accepted. That actor is a binding comparison, never durable authentication proof. Do not call `bool`, `is_authenticated` or another proxy attribute before checking unresolved state.

Read SessionStore's already-present `_session_cache` directly from its instance dictionary for the live `auth_epoch`. Missing/non-dict cache denies401; never access a property/getter that triggers SessionStore.load. This is appropriate to the configured ordinary authenticated middleware path, which has already loaded the session. Require session-key digest, actor and cached epoch to remain bound on every revalidation. Session cache/hash values do not replace fresh persisted authentication.

Fetch the existing Session row by key without a lock and decode `session_data` directly through the genuine installed store's signed `decode` semantics, including configured signing fallback keys. Require aware expiry later than the sample time; missing/corrupt/expired session or partial challenge denies401. Require persisted `_auth_user_id`, exact `_auth_user_backend`, `_auth_user_hash`; convert ID through the configured User PK field, obtain current active user via the pinned ModelBackend.get_user, and constant-time compare hash against fresh current and configured fallback session-auth hashes. Never call auth.get_user(request), store.load/save/create/cycle_key/flush, identity_security.session_hash or lock_identity.

Persisted and live cached epoch must each have exact type int and value>=0, or legacy missing None; reject bool/negative/string. They must equal the originally captured epoch; authoritative IdentitySecurity.auth_epoch must match (or authoritative0 when no row). Legacy None passes only authoritative0. Reads never create IdentitySecurity. Session decoding may invoke existing library logging of generic corruption; no code in this subset logs its raw input, key/hash or private descriptor.

Global authority reads current active Membership roles and ROLE_PERMISSIONS directly. List/detail require intersection of branch sets for `patients.read` AND `documents.registration.read`; create/withdraw also require `patients.write` AND `documents.registration.write` at that same branch. Return the nonempty intersection. No global union or cached CurrentUser is authority. Global403 precedes future detailed input/target validation; no patient is consulted here. Reception-only grants are independent of the later flag and grant no clinical-signing right.

An absent `auth_epoch` key alone represents legacy None; an explicitly present null is invalid401 in persisted data or live cache. Tests distinguish missing/null independently in both. A key is legacy only when absent; explicit None never passes.

### Locked authority materialisation

`sample_document_authority(context: DocumentContext, operation: str) -> DocumentAuthoritySample` requires a valid mint/binding and an already open caller-owned transaction. Trusted caller precondition: actor User is already locked NO KEY UPDATE with `of=('self',)`, then existing IdentitySecurity row, if present, is locked; no missing profile is created. The function checks transaction presence, but does not pretend to prove another function's lock ownership through a boolean/token or database introspection. The later B2a-L caller owns correct lock acquisition/timeouts.

Re-read current active user, persisted session, existing epoch and current global same-branch grants, retaining original capture. Return scalar expiry/eligible branches and fresh aware sampled_at after these reads. Reject backward time before operation start. Acquire no extra User, Membership, StaffAccessRevision, Organisation, patient, session or network lock. Current staff/identity locking conventions remain unchanged. A committed deletion/update visible before the final session sample denies; another request's logout after that sample may coexist with the selected result. No immediate logout cancellation is claimed.

### Network materialisation and pure final selection

`sample_document_network(context: DocumentContext, now: datetime) -> DocumentNetworkSample` checks mint/live binding and aware now>=operation start. Recompute environment_snapshot and normalise captured remote/header using its explicitly trusted proxies; require matching digest/verified IP. Drift/unavailable/corrupt state is503. Valid environment denial is403. Read one `load_network_snapshot(now)` using existing validated fields, no repair or lock; copy confirmed/candidate graph into immutable values. Preserve pending fields even for expired_unreconciled. Do not trust `effective_policy` or `pending_status` as final-time selection. Existing loader can conservatively reject a newly activated graph newer than pre-read now; no retry loop.

`validate_document_selection(context: DocumentContext, authority_sample: DocumentAuthoritySample, network_sample: DocumentNetworkSample, selected_at: datetime) -> None` is pure: validate types/mints/exact context identity/operation, immutable shape, aware selected_at>=operation_started_at and both sampled_at values, nonempty eligible branches, and strict selected_at<expires_at. Expiry equality denies401; backward/unavailable shape denies503. No clock lookup, request/session access, SQL, locks or monotonic budget check occurs here.

No pending change selects confirmed policy. A validated pending graph selects candidate iff activated_at<=selected_at<rollback_at; equality/after rollback selects confirmed even when the graph remains expired_unreconciled. Before activation denies503. Apply environment AND selected overlay; a valid denial is generic403. A policy commit visible before the sampled SELECT must affect that sample; one after its statement snapshot may coexist with selection. Any later I/O/wait in an orchestrator requires fresh authority/network samples and a new selected_at. These helpers confer no patient scope, disclosure permission, admission or audit success.

## Review Focus

1. Lazy user or uncached session access must not indirectly rotate/flush/create a session; exact unresolved/fallback/cached-epoch cases belong to Task1.
2. A forged or cross-context immutable sample must not become proof; Task1 checks sample/context identity, repr secrecy and nested immutability.
3. Split branch grants and flag-independent CurrentUser strings must not widen patient scope or reveal readiness; Task1 tests same-branch intersections and unchanged other roles.
4. Session expiry/logout and network deadline crossing must use honest sampled semantics; Task1 tests equality, both visibility orders and no read-side repair.
5. Caller-owned lock preconditions must remain distinct from actual service locking evidence; Task1 uses explicit isolated PG locks and does not claim B2a-L limiter/deferred-write/timeout acceptance.

## Task 1: read-only authority boundary and reception permission ceilings

**Files:** create document_authority.py and test_document_metadata_authority.py; modify only reception permissions in authorization.py as listed above.

**Consumes:** existing Session/User/IdentitySecurity/Membership, ROLE_PERMISSIONS, environment_snapshot, normalise_client_ip, load_network_snapshot and pure evaluate_ip. No business/schema helper is written or repeated.

**Produces:** the three exact frozen types and four function signatures above, plus fixed DocumentServiceError. These are consumed later by B2a-L/B2b under their independently frozen orchestration contracts.

- [ ] Coordinator reconciles parent contracts, exact names/shape/copy/error/configuration rules and file ownership, obtains fresh independent scenario/permission and threat/abuse review, and freezes this subset before tests/production code. Resolve absent-cache401 as the deliberate ceiling for direct callers; later adapters may not bypass it with fabricated authentication.
- [ ] Write genuine signed DB-session fixture tests using installed Django login/session facilities, then pass a raw request with deliberately resolved or unresolved actor/cache. No force_authenticate shortcut as session proof. Do not evaluate lazy request.user while preparing the unresolved test. Import the absent new production module within tests so failures are executable missing-feature failures rather than a collection/dependency failure.
- [ ] Add named RED groups: `test_capture_rejects_ambient_before_reads`, `test_genuine_session_capture_is_read_only`, `test_unresolved_actor_never_evaluates`, `test_missing_cache_never_loads`, `test_fallback_hash_acceptance_without_rotation`, `test_session_and_epoch_failures`, `test_role_branch_conjunction_and_current_user`, `test_foreign_mint_and_sample_rejected`, `test_policy_sample_detached_and_repr_safe`, `test_selection_expiry_and_rollback_equalities`, `test_session_visibility_orders`, `test_network_visibility_orders`. Parameterise operation/role/epoch/session/configuration cases; pin exact errors from the table.
- [ ] RED assertions include expired/deleted/tampered/partial-challenge/backend/hash/inactive sessions, signing+auth fallback keys, actor/key/cache changes, bool/negative/string/legacy0 epochs, unsupported engine/backend503, direct construction, absent profile without creation and same-request flush before materialisation. Patch forbidden mutators and SessionStore.load to fail if called; compare persisted session rows and IdentitySecurity state before/after. Assert no Patient/intent/receipt/event/rate-window query, including denial paths.
- [ ] Permission REDs pin exactly two added reception strings under existing CurrentUser shapes; master/doctor/nurse/other roles unchanged, mixed reception-B/doctor-A cannot authorise A, split required branch sets have empty intersection. Neither CurrentUser nor backend authority adds readiness/navigation/HTTP behavior.
- [ ] Network/time REDs cover confirmed/pending/expired_unreconciled; selected_at immediately before/equal/after rollback; preactivation/backward/naive clocks; trusted-proxy spoof/environment drift/corrupt graph; session expiry equality; policy-rule copying and immutable tuples. Pure-selector spies fail on clock, DB, request/session or repair access. Foreign context with same actor is rejected.
- [ ] Run from backend: `python -m pytest tests/test_document_metadata_authority.py -q`. Expected: literal failures on absent module/new grants, with valid fixtures/dependencies. Preserve exact failures/count/time before production edits; no pass is claimed by this draft.
- [ ] Implement the smallest production changes in the owned files, using the frozen interfaces and existing pure rule evaluator. Do not add a privileged/auth-framework abstraction or admission scaffolding.
- [ ] Re-run the authority command on SQLite. Expected: all portable authority tests pass; explicit PG-only cases skip with named reason. Run `python manage.py check` and `python manage.py makemigrations --check --dry-run`; expected0 issues/no changes. Confirm original B1/schema source hashes unchanged.
- [ ] Coordinator runs the same authority tests and existing relevant identity/staff/network regressions on receipt-owned isolated PG17, never live preview DB. Explicit transaction tests acquire actor NO KEY UPDATE then existing IdentitySecurity and invoke the sampler; verify no implicit lock expansion. Separate-connection identity epoch/first-profile-before-and-after-actor-wait cases must observe real blocking with pg_blocking_pids/barriers, both serial orders, no40P01; absent-profile read never creates it. Session deletion and policy commit visibility cases demonstrate sampled outcomes without pretending the actor lock serialises ordinary logout or network policy. No limiter/admission success or LOCAL-timeout behavior is claimed.
- [ ] Fresh independent source/security review checks genuine-session forgery ceiling, Django fallback paths, exact query/lock scope, detached representations and stated races. Material findings get reproducing RED then minimal GREEN. Run appropriate existing auth/network/migration/CurrentUser regression suites and coordinator full actual-PG backend checks/check/nodrift; preserve exact commands and outcomes.
- [ ] Coordinator reviews diff/secrets/whitespace and updates HMS.md/plan.md/ledger in the completed code commit. Push normally and verify remote full SHA/exact CI. Review/test restricted-preview update for this Python-only change, preserve existing venv/static/security/core0009 and empty rate table, verify actual live MFA/session/network/reception/logout plus CurrentUser document strings and absence of metadata routes/UI. No new setting or document feature activation occurs. Save deployment/backup/preservation evidence and update MD deployment records; documentation-only publication does not restart unchanged code.

## Separate unresolved admission ruling

Coordinator reconciliation selects a provisional saturated-count decision followed by the same final authority/network/expiry/budget checks as successful admission, then429 without growth if still authorised. This plan does not implement or verify that path. B2a-L owns monotonic budget enforcement, server LOCAL controls, outermost durable commit, uncertain acknowledgement, retained disabled-call count, postcommit exact-boolean flag reread and exact canonical command inputs. False or malformed flag after known commit returns503 while retaining the allowance.

## Draft self-review and handoff

The proposed subset covers authority/session/global grant/environment/IP mint, materialised durable network selection and pure final checks. Schema/B1, limiter/flag/transactions/business disclosure and transport remain outside ownership. Field names consistently use captured_epoch; samples bind context identity; mutable descriptors are copied and hidden from repr. Open coordinator decisions are explicit above, not inferred feature completion. Only source/spec inspection and this plan authoring were performed; all execution checkboxes remain unchecked.

## Pre-code review amendments —28 October2026

Independent acceptance review found no Critical/Important blocker subject to strict missing-versus-null epoch distinction, adopted above. Tests separately exercise signing fallback/authhash fallback, absentcache/unresolvedlazy/subclass refusal before overrides, no model/session writes or forbidden queries, zero-I/O selection and both exactdeadline directions. Five-second monotonic/limiter/flag/business/HTTP work stays outside this slice. Shared feature checkout is the owner-selected workspace; coordinator alone commits/pushes/VPS. Independent security review found replacement-clone proof ambiguity; per-issued-object weakref binding and explicit replace/copy negatives close it before freeze. Coordinator freezes this narrow plan; RED must run before production code.

Coordinator ruling: process-private sentinel alone cannot prove issuance after dataclasses.replace; exact per-object proof binding is required for contexts and both samples. This protects ordinary internal misuse, not trusted Python deliberately manufacturing private proof internals. Production remains pending; parent admission/service races and staff release are not delivered by this freeze.

Coordinator pre-RED ownership amendment: isolate actual-PG authority races in test_document_metadata_authority_pg.py so portable tests, PG tests and implementation review can work on disjoint paths. Both test modules import absent production functions inside tests for literal executable RED before production edits. This test-only decomposition does not widen production scope.

## Source execution disposition —28 October2026

Frozen source unit implemented after original RED; independent expanded coverage and real lazy-subclass RED→GREEN included. [Measured source evidence](../operations/document-authority-source-evidence-2026-10-28.json): final actualPG1445/5SQLite-skips/168subtests86.14s/check0/nodrift, portable117/8PGskips, fresh source/security approval. The original design checklist is retained historically; exactCI/push/reviewedpreview/live/MD remain completion gates. No limiter/flag/business/HTTP/UI or new schema.
