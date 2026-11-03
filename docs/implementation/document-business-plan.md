# Audited document metadata business services implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: coordinator-selected subagent-driven-development or executing-plans, TDD, systematic debugging, review and verification. Root alone assigns, freezes, commits/pushes and changes VPS. Shared-checkout ownership is explicit; no duplicate team.

**Status:** 2 November 2026, FROZEN B2b DESIGN after three independent contract/transaction/scenario-test reviews and coordinator reconciliation. Source verified3November:1683PG/7SQLite-skips/168subtests/check0/nodrift; exactCI/reviewedpreview still pending.

**Goal:** Implement four independently testable, audited metadata business services using completed B2a admission; no HTTP, UI, ingestion, storage or activation.

**Architecture:** Four raw-input public functions each call existing admission exactly once, then immediately consume its exact issued immutable command in a private phase-B executor. One outermost durable business transaction reacquires current authority/scope, serialises supported writers, commits the required disclosure event and releases only detached encoded bytes after known commit. Original context wall/monotonic budget spans both phases.

**Tech stack:** Existing Django5.2.18, psycopg3.2.12, PostgreSQL>=17/default alias only, current B1/B2a-S/A/L. No dependency, model, migration, settings, grants, route, frontend or OpenAPI change.

**Spec:** [metadata contract](patient-document-metadata-contract.md), [service review](patient-document-metadata-service-review.md), [completed admission](document-admission-plan.md), [authority](document-authority-plan.md), [source/runtime evidence](../operations/document-admission-preview-evidence-2026-11-01.json), HMS.md, plan.md and ledger. This child freeze supersedes conflicting parent remaining-service assignments, not completed B2a interfaces.

## Intent, approaches and coordinator choices

Reception staff need current registration metadata with explicit creation/withdrawal and traceable successful disclosure, without pretending a file was received. Existing versioned OpenAPI0.7.0 already defines exact fields and four planned operations. Alternatives: extend document_access.py with business code (mixes completed admission and new patient disclosure); duplicate admission/authority in each service (drifts lock/error rules); or a new document_services.py sharing one private business engine. Coordinator chooses the third, retaining tested B1/B2a unchanged except the narrow safe-error extension. Existing two-phase service scope was owner-authorised; these are technical reconciliation choices, not a new product or activation request. No human-only product decision remains in the reviewed bounded scope.

## Global constraints and file ownership

- NEW backend/apps/core/document_services.py: four public raw-input wrappers, frozen detached result, private locking/business/projection/encoding helpers. One assigned production implementer owns this file plus the safe-error extension only.
- MODIFY backend/apps/core/document_authority.py: add exactly three409 tuples and widen generic429 retry ceiling to3600; do not change context/session/grant/network/issuance behavior.
- CONSUME document_access.py/document_contracts.py/models/migrations/settings/authorization unchanged. A reproduced defect requires coordinator scope amendment and RED before edits.
- NEW tests/test_document_metadata_services.py and test_document_metadata_business_rules.py: service behavior, pure projection/decision and constructor amendment tests. Only existing constructor boundary expectations made obsolete by the explicit range extension may be amended deliberately.
- NEW tests/test_document_metadata_business_pg.py: actual service races on independent PostgreSQL connections.
- NEW tests/test_document_metadata_business_timeouts.py: phase-B fault/constraint/final-time/acknowledgement and actual server controls.
- NEW tests/test_document_metadata_business_queries.py: realistic retained-history quota/keyset EXPLAIN measurements, isolated PostgreSQL only.
- Root owns all records and isolated validation/runtime; tests never use real patient data or live admission. Current preview833ffc67/core0009/flagFalse stays separate until exact completed-source publication/CI and reviewed rollout gates.

## Public and private interfaces

Public imports are in apps.core.document_services:

- list_document_intents(context: DocumentContext, patient_id: str, query_pairs: list|tuple=()) -> DocumentServiceResult
- get_document_intent(context: DocumentContext, patient_id: str, document_id: str) -> DocumentServiceResult
- create_document_intent(context: DocumentContext, patient_id: str, key: str, body: bytes) -> DocumentServiceResult
- withdraw_document_intent(context: DocumentContext, patient_id: str, document_id: str, key: str, body: bytes) -> DocumentServiceResult

Each checks original operation binding, calls admit_document_command exactly once with its raw inputs, then private _execute(admission, expected_operation) with the operation fixed by that wrapper. The private executor derives context/command ONLY from admission, validates _validate_document_admission(admission, admission._context, expected_operation), dependency/budget and enabled state before patient access. There is no public accept-admission/prepared-dict/actor-ID path. Issuance is exact-object binding, not single-use, cryptographic replay prevention or a trusted-Python sandbox. Private internals remain trusted server code.

DocumentServiceResult is frozen status:int/body:bytes, body excluded from repr. Exact statuses list/detail/withdraw200, create201, including replay. Complete UTF8 JSON is encoded inside phaseB, ensure_ascii=True, separators comma/colon, allow_nan=False, length<=262144; no model/queryset/Response/serializer/callback escapes. No query or deferred projection after return.

Private pure helpers frozen for independent portable testing:

- _capabilities(can_write: bool) -> dict, exact existing closed capability schema; upload/download false, upload_categories=[], allowed_media_types image/jpeg,image/png, max_size_bytes10485760/max_filename_characters120.
- _project_intent(record: dict, patient_id: str, branch_id: str, actor_id: int, can_write: bool, selected_at: datetime) -> dict. record is a fully materialised dictionary with exact keys id,created_by_id,declared_filename,declared_media_type,declared_size_bytes,status,version,created_at,expires_at, not a model/queryset. Exact Intent schema; no digest/reason/actor identity/storage/patient demographics. UTC timestamp formatting uses exactly six fractional digits. Pending projects expired at selected_at>=expires_at; withdrawn remains withdrawn. can_withdraw requires write conjunction, creator, stored pending, strict expiry and version<2147483647.
- _quota_retry(active_expiries: list, organisation_created: list, now: datetime) -> int|None. Inputs are bounded SQL-filtered/order-selected snapshots, maximum20 and1000 respectively. At threshold return max limiting wait, ceil/clamp1..3600; otherwise None. No query in this helper.

- _encode_document_body(payload: dict) -> bytes: compact UTF8 ensure_ascii=True/separators comma-colon/allow_nan=False; exact262144byte bound, serialisation/oversize fixed503. This private pure seam permits artificial exact-size tests and labelled post-encoding budget interception without widening accepted metadata.

These helper outputs have no authority by themselves; public calls derive all booleans/scalars from current locked scope.

## Safe error amendment and precedence

Preserve the existing exact error vocabulary; add only:

| code/status | message |
|---|---|
| idempotency_conflict409 | This request could not be repeated. Refresh before continuing. |
| version_conflict409 | The record changed. Refresh before continuing. |
| intent_state_conflict409 | This request can no longer be withdrawn. |

Generic rate_limited constructor permits exact int1..3600; bool/zero/negative/3601 rejected. Actor limiter's actual emission remains1..60, with unchanged tests for saturation/reset. Other errors forbid retry_after. No arbitrary exception/PHI/SQL/body retention; fixed503 for dependency/uncertain errors.

Before admission use completed global action, original context and B1 validation precedence. After admission: current global action403 before patient lookup; globally entitled missing/foreign/inaccessible patient and mismatched document all404. Scope established before creator-only withdrawal403. Then receipt fingerprint mismatch409 BEFORE dereferencing its result; matching fingerprint with corrupt/mismatched result linkage503. This pins changed-patient commands as409 after current target scope, rather than treating ordinary changed input as receipt corruption. Matching replay bypasses transition/quota/deadline/version checks, never scope/creator/current authority. New withdrawal: terminal/expired409 intent_state_conflict before stale/max409 version_conflict. No error projects metadata or fabricates inaccessible-patient events. Errors roll back phaseB and retain known phaseA allowance.

## Phase-B transaction and locks

Require default-only PostgreSQL>=17/no routers, autocommit and no ambient atomic block. Reuse original cooperative5s budget; never remint context or reset starts. At phaseB entry actual bool flag must beTrue; false/invalid503 before patient access (admission remains). atomic(durable=True) sets LOCAL lock_timeout2s/statement_timeout3s/transaction_timeout5s before business locks.

Lock sequence: actor User NO KEY UPDATE -> existing IdentitySecurity -> tentative patient descriptor restricted to action-eligible branches -> one Organisation NO KEY UPDATE -> exact-branch Membership observation -> existing actor/operation/key Receipt NO KEY UPDATE -> Patient NO KEY UPDATE -> addressed/returned intents NO KEY UPDATE in UUID order. Explicit of=(self,) on every joined locking query. No Membership/StaffAccessRevision/Branch/creator User/Bed/Encounter/network-owner locks. Missing profile stays missing. Do not follow changed scope into another organisation; fresh patient->branch->org mismatch fails closed.

Read-operation authority proves read only. Privately observe active exact-branch Membership roles under held org/identity gates, derive read and write conjunctions from ROLE_PERMISSIONS, and refresh before final selection. No CurrentUser union, cross-branch grant composition or cross-operation context sample. Final issued authority sample still validates only the original operation.

New create: quota_now captured under gates, bounded select20 pending with expires_at>quota_now ordered expiry/id; bounded select1000 organisation creations with created_at>quota_now-3600s ordered created_at/id via patient/branch scope. Withdrawn/expired creation history still counts rolling quota. If both limited use max waits. Replay/withdraw exempt only from new-create quotas. At allowed create, created_at=quota_now/expires_at=quota_now+30minutes exactly. No history purge or capacity guarantee.

Withdrawal persists one version increment and private reason/actor/time; stored withdrawn_at may precede selected_at. For a genuinely new withdrawal, preserve pretransition state/version for final checks; strict expiry crossing rolls back transition/receipt/event. Matching replay returns current terminal projection without reapplying transition expiry/version guards. Matching replay returns current state without timestamp/version mutation. Actor lock protects absent receipts; unique is backstop, not permission to auto-retry an IntegrityError.

List selects <=limit+1 IDs (max101) by immutable descending created_at/id keyset, then locks only returned<=100 IDs in UUID order and restores display ordering. Sentinel excluded from body/event/digest. next_cursor iff has_more, derived from last returned row; no total COUNT. Cursor is a position, not a cross-request snapshot, and does not require an extant anchor row.

## Audit, final selection and commit

Every successful empty/list/detail/create/withdraw/replay inserts exactly one required DocumentAccessEvent. Existing names intent.list/detail/create_result/withdraw_result; list documentnull/count0..100, others exactdocument/count1. Digest SHA256 of UTF8 compact JSON of sorted canonical RETURNED UUID strings (empty=[]), server-generated correlation UUID. Establish event patient/document linkage explicitly from locked scoped objects; ORM create does not call clean and database constraints do not enforce this equality. No generic AuditEvent or request/payload/filename/reason/proof disclosure.

Finish all mutation/receipt/event writes, force SET CONSTRAINTS ALL IMMEDIATE, then make no more writes. Freshly materialise identity/session, exact branch/scope/write conjunction and one coherent network snapshot, then choose one selected_at. Only pure final authority/network selection, expiry/version checks, capability/projection and bounded encoding follow. Any additional blocking read requires repeating final materialisation/selection. Pending candidate applies iff activated_at<=selected_at<rollback_at; equality selects confirmed fallback, environment AND overlay. Sampling guarantee: changes visible before final statement snapshots deny; changes after those snapshots may coexist with selected result. No immediate logout or policy cancellation promise.

Flag is exactTrue at entry, after final materialisation/precommit and after known commit. Any false/invalid before commit rolls back business/event; after commit withholds result503 while retaining committed business/event and allowance. Shared budget checked after encoding and after commit; postcommit budget failure similarly withholds without compensation. No later flags/budget check can retract a result already returned.

Before marking body_completed, reject connection.needs_rollback/closed_in_transaction. Only normal outermost exit followed by acknowledged usable commit releases bytes. Catch failures after atomic exits; known rollback has no phaseB rows, retained allowance. Uncertain COMMIT/rollback closes suspect connection, fixed503/no result/refund/automatic retry; explicit later same-key retry reconciles actual persisted receipt/result. Tests label real commit then simulated lost ACK separately. LOCAL controls are not a5s COMMIT or HTTP SLA.

## Review focus and executable acceptance

1. Reused valid proof must not become a public free business path; wrapper tests observe one fresh admission per successful/replayed call.
2. Read permission must not imply write capabilities; mixed branch/roles and grant changes are tested through actual services.
3. Fingerprint mismatch versus corrupt linkage, creator/state/version and quota precedence must not disclose old/foreign metadata.
4. Event/constraints/final reads can cross expiry/session/network deadlines; prove rollback/read projection at exact equality without later writes.
5. Normal atomic rollback-only exit and lost acknowledgement must never release detached success bytes.

### Task1 — literal RED for service interfaces, errors and pure rules

- [x] Write constructor tests for three409 tuples/retry3600 and rejection, pure capability/projection/expiry/version/quota decisions, forged/wrong-op/ambient/defaultDB service boundaries.
- [x] Write PostgreSQL genuine-session service success/audit/scope/receipt/replay/state/cursor/quota and retained-admission failures before production code. Imports inside tests produce missing-service RED, not collection errors.
- [x] Root runs portable RED and actual isolated PostgreSQL RED; record exact failures before implementation. No SQLite service-success fallback.

### Task2 — minimal coherent engine

- [x] Implement the four wrappers/private phaseB engine and pure helpers plus exact error amendment. Consume completed B1/B2a unchanged. Run targeted GREEN/check/no drift.
- [x] Independent source/scenario/security review; material findings get reproducing RED before fixes.

### Task3 — actual service acceptance (B2c gate)

Write/run these actual-service race/fault REDs before the corresponding production behavior; this is not test backfilling after GREEN.

- [x] Distinct-connection both-order staff replacement/suspension/identity epoch+deactivation/first-profile races, actual same-key command/withdraw/list-replay state races, final patient/org quota-slot contention and Patient PATCH/bed allocation lock order. Observe pg_blocking_pids, bounded no40P01 and committed rows/events.
- [x] Actual2s/3s/5s controls/reset, intent/receipt/event/deferred constraint rollback, final exact expiry/session/network waits and original-budget exhaustion; separately labelled true commit/rollback then simulated lost ACK, normal rollback-only exit, fresh connection/keyed reconciliation.
- [ ] PG17 EXPLAIN(ANALYZE,BUFFERS) on isolated synthetic3orgs/60patients-per-org/at least30000 retained intents including large expired history; bounded active20/org1000/keyset101 queries each under statement3s. Save dataset/plan/rows/buffers/timing, not a capacity claim. Timeout503 verified. No speculative index/denormalised ledger; observed failure requires reviewed schema amendment.
- [x] Full actual isolatedPG regressions/check/no drift, portable rules/boundaries and required contract/docs/root checks; no new frontend change implies no new UI acceptance.

### Task4 — publication and gated preview rollout

- [ ] Update HMS/plan/ledger same change with actual RED/GREEN/review/results and open distinctions; push normally/verify full remote SHA and exact successful CI.
- [ ] Freeze/review source-only preview procedure using actual source delta and retainedFalse environment; rehearse keys/backup/prior compatibility isolated. Never invoke live business/admission or enable flag for smoke. No schema/dependency/UI changes expected, but verify actual delta.
- [ ] Reviewed preview rollout/live existing behavior/rate+business preservation and postbackup restore; preserve other apps/security/owner state. Then documentation record push/remote verification. If usage<=10stop/checkpoint330minutes; no partial WIP deployment or false completed change.

B2b code is not B2 acceptance until Task3 passes;4 metadata HTTP operations stay planned through B2. B3 transport/CSRF/no-store/API acceptance, ingestion/UI, browser/staff/owner-phone/full hospital release remain separate.

## Coordinator freeze record —2 November2026

Three independent bounded reviews approved this exact reconciled design with no Critical/Important blocker. Routine pins adopted: fixed wrapper operation, preserved pretransition withdrawal state/version, exact pure-record keys, and race/fault RED before production. These are design approvals only. Owner CONTINUE authorises execution within existing scope; no new product/activation decision, dependencies or runtime change. Root alone publishes/deploys. Actual B2b/B2c tests, source review, CI and reviewed preview rollout remain open.

## Pre-code encoder seam precision —2 November2026

Coordinator added the private pure encoder signature above before production, solely to make exact size/post-encoding budget behavior executable without a fake service or unpinned monkeypatch target. Artificial dictionary boundary tests do not broaden the closed public response schema. Initial actualPG RED1 had128fail/10pass/1skip/2setup errors15.58s because query fixture imported the absent module at setup; fix to runtime import before data factory then repeat RED before code. This is not service/fault/query acceptance.

## Executable RED disposition —2 November2026

[RecordedRED2](../operations/document-business-red-evidence-2026-11-02.json):133expectedFAIL/10pass/1SQLite-onlyskip/noerrors12.08s. Moduleabsent andsafeconstructorred beforecode; rawfixture errorswerecorrectedfirst. Thisdoesnot tick actualGREEN/race/fault/EXPLAINacceptance. Rootpublished tests-onlycheckpoint separatelyfrom subsequentlyassignedproductionWIP; no completed change/deploymentclaim.

## Incomplete checkpoint —2 November2026

[WIP receipt](../operations/document-business-checkpoint-2026-11-02.json) records the fresh10percent stop/deadline, initialtargeted148PGpass/1fixturefail and4source-reviewREDs with unverifiedfixes. No implementation/review/actualfullsuite/CI/rolloutcheckbox isclosedbythischeckpoint. Startafterdeadline/allwindows>10with4regressionGREEN, scopedreview, correctedlostACK/full154suite+JUnitplans andfullregressions. Do notdeployWIP.

## Source verification disposition —3 November2026

[Measured evidence](../operations/document-business-source-evidence-2026-11-03.json):4review regressionsGREEN,153business/1SQLite-onlyskip,1683fullPG/7skips/168subtests/check0/nodrift. Fresh source/test review found no new Critical/Important issue. All four actual query properties retained/inspected, no capacity guarantee. ExactpublicationCI and reviewedpreview/live/restore records remain pending; no HTTP/activation/release completion inferred.
