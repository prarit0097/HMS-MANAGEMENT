# Document metadata rate schema implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use installed `executing-plans` or coordinator-selected `subagent-driven-development` task-by-task. Coordinator alone assigns, freezes, commits/pushes and deploys. Checkboxes record evidence only.

**Status:** FROZEN B2a-S ONLY / PRE-CODE GATES SATISFIED, 26 October 2026. This document proposes the independently testable **B2a-S** dormant schema subset. Parent B2a admission and B2 service contracts remain DRAFT. No code, test execution, schema migration or deployment is established by this plan.

**Goal:** Persist one structurally valid, finite UTC-minute rate-window row per actor without introducing any runtime capability or allowance consumption.

**Architecture:** Extend the existing `core` model discovery with one model and a permanently importable Boolean expression. Add migration0009 with a last-forward/first-reverse empty-table guard. Existing document metadata service interfaces later consume these exact fields without a replacement schema or migration-expression move.

**Tech stack:** Existing pinned Django5.2.18, pytest/pytest-django, SQLite portable-schema tests and coordinator-controlled actual PostgreSQL17. No dependencies or providers are added.

**Spec:** [admission contract](patient-document-metadata-admission-contract.md), [service plan](patient-document-metadata-service-plan.md), [independent service review](patient-document-metadata-service-review.md), [metadata contract](patient-document-metadata-contract.md), [HMS](../../HMS.md), [project plan](../../plan.md).

## Scope and choices

The admission contract already chooses the actor OneToOne row, required timestamp/count and portable custom CHECK. B2a-S separates its dormant schema from unfinished authentication, grants, feature flag, limiter algorithm and admission transactions. This separation permits schema approval without implying that the admission contract is frozen or functional.

Use the specified custom Boolean `Func`, rather than ordinary `TruncMinute`/`ExtractSecond` (timezone/precision ambiguity), a PG-only raw constraint (loses promised SQLite schema support), or an application-only validator (raw SQL bypass). Bare equality is rejected because SQL CHECK accepts UNKNOWN; the outer `IS TRUE` is mandatory. The finite predicate additionally rejects PostgreSQL infinities.

No new role/grant/setting, manager/service, API/URL/OpenAPI/page action, UI/navigation, clock/default, quota, cleanup/retention task, actor locking, audit/event, session/network behavior, upload/storage/scanner/download or deployment automation. No production row is written by this slice. Existing50 catalogued/46 implemented HTTP operations remain unchanged; four metadata operations stay planned. API-first contracts already cover the future capability; this dormant internal schema adds no user action or callable mutation route. No API/UI acceptance is inferred from database tests.

Coordinator-supplied starting context: HEAD1edab14, application source66bfa, restricted preview release522f00d with core0008 applied. These are context, not fresh Git/VPS attestations by this document's author. Do not repeat the completed deployment; only a subsequent completed code change triggers a new reviewed rollout under the standing owner rule.

## Exact file boundary

| File | Allowed responsibility |
|---|---|
| `backend/apps/core/document_models.py` | Add `DocumentMetadataMinuteAligned` and `DocumentMetadataRateWindow`; preserve existing three models and helpers |
| `backend/apps/core/models.py` | Append `DocumentMetadataRateWindow` to the existing `.document_models` import only |
| `backend/apps/core/migrations/0009_document_metadata_rate_window.py` | Create model/CHECKs; final forward no-op with historical reverse guard |
| `backend/tests/test_document_metadata_rate_window.py` | New isolated schema/compiler/serialization/migration tests |
| `backend/tests/test_patient_document_models.py` | Required narrow fixture amendment: in `test_foundation_reverse_refuses_rows_before_any_drop`, capture actual graph leaves before reversal and restore them in `finally`; preserve original0007 target and all existing assertions. The pristine-round-trip test already restores leaves; the refusal test does not |
| `HMS.md`, `plan.md`, `docs/implementation/ledger.md` and bounded evidence/runbook records | Coordinator's accurate source/test/publication/deployment records in completed change set |

No previous migration edits. Recheck actual leaf and file existence before freeze; a changed leaf requires explicit coordinator reconciliation, never renaming over another assigned migration. No new app, export module, utility file or public helper.

## Frozen candidate model and expression interface

Pending coordinator freeze, exact model is `apps.core.document_models.DocumentMetadataRateWindow`, discovered as `apps.get_model('core', 'DocumentMetadataRateWindow')` through `core.models`. Default table is `core_documentmetadataratewindow`.

| Field | Definition/invariant |
|---|---|
| `actor` | `OneToOneField(settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.PROTECT, related_name='+')`; sole PK; no generated id, default, nullable actor or reverse accessor |
| `window_started_at` | `DateTimeField()`; required/non-null, no Python/database default or automatic clock; stores finite exact UTC-minute instant |
| `admitted_count` | `PositiveSmallIntegerField()`; required/non-null, no Python/database default; explicit inclusive1..60 CHECK |

`Meta.constraints` exactly: `doc_metadata_rate_count` with `Q(admitted_count__gte=1, admitted_count__lte=60)` and `doc_metadata_rate_minute` with `DocumentMetadataMinuteAligned(F('window_started_at'))`. No custom indexes, uniqueness/ordering, model methods, validation-only substitute or business writes. The OneToOne PK supplies actor uniqueness/index; database FK integrity and ORM PROTECT both require tests. PROTECT is a Django deletion contract; do not claim SQL uses an `ON DELETE PROTECT` clause. Database constraints also protect raw SQL independently.

Expression exact interface:

- Class `DocumentMetadataMinuteAligned(models.Func)` at stable path `apps.core.document_models.DocumentMetadataMinuteAligned`, `arity=1`, Boolean `output_field=models.BooleanField()`.
- Construct with one positional expression, e.g. `DocumentMetadataMinuteAligned(F('window_started_at'))`; inherit normal Func construction/deconstruction. Wrong arity rejects. No stored compiled SQL/connection, lambda, closure, `__main__` class or migration-local proxy.
- `as_postgresql(self, compiler, connection, **extra_context) -> (sql, params)` compiles its sole source expression once; emits `((isfinite(<sql>) AND <sql> = DATE_TRUNC('minute', <sql>, 'UTC')) IS TRUE)` with returned params repeated in occurrence order three times.
- `as_sqlite(self, compiler, connection, **extra_context) -> (sql, params)` compiles once; emits `((<sql> = django_datetime_trunc('minute', <sql>, 'UTC', 'UTC')) IS TRUE)` with params repeated twice in occurrence order.
- `as_sql(self, compiler, connection, **extra_context)` raises `django.db.utils.NotSupportedError` for unsupported backend/vendor; no generic permissive fallback. Vendor compilation dispatch handles the two supported vendors. Inputs/identifiers are compiler-produced; never interpolate caller values/field names. SQL constants above are fixed trusted syntax.
- Keep this import path and semantics available for the lifetime of migration0009, even if a future runtime model is moved/removed. A future change requiring altered constraint semantics is a new migration, not an edit to historical behavior. Full MigrationWriter reconstruction must import this path without special setup.

UTC is part of constraint semantics, not a connection-timezone assumption. An instant expressed with a timezone offset is accepted if its UTC instant is an exact minute. Service code later supplies an aware UTC floor; this schema does not validate request timezone syntax or implement that floor. SQLite's registered Django datetime function may return NULL for malformed input; `IS TRUE` makes that rejection fail closed. A safe database error also rejects malformed writes; never catch/normalize an error into success.

## Migration and rollback contract

Migration filename/class: `0009_document_metadata_rate_window.py` / `Migration`. Dependencies: `('core', '0008_patient_document_foundation')` and `migrations.swappable_dependency(settings.AUTH_USER_MODEL)`. Forward only creates this table and its count/minute constraints; existing rows/tables/grants/config remain intact. No data backfill/default/index/data cleanup.

Use generated serializable CreateModel/constraint operations followed by exactly `migrations.RunPython(migrations.RunPython.noop, reverse_empty_only)`. Whether Django renders constraints in CreateModel options or AddConstraint is allowed generator structure, provided all constraint DDL precedes the final guard and round-trip state has no drift.

`reverse_empty_only(apps, schema_editor) -> None` lives in0009. It obtains historical `apps.get_model('core', 'DocumentMetadataRateWindow')`, reads `.objects.using(schema_editor.connection.alias).exists()`, and raises `RuntimeError('Document metadata rate reversal requires an empty table; preserve limiter state.')` on any row. It performs no deletion/write and imports no runtime model. Last-forward means first-reverse: guard refusal must occur before any constraint/table DDL. Empty0009->0008->0009 is supported; nonempty reversal is refused regardless of actor/count/minute, with table, constraints, rows and migration recorder preserved. Existing0008 reversal guard is unchanged.

Reversal is supported only with writers quiesced and reviewed; an existence check is not protection against concurrent insertion after the check. No live-race/online rollback guarantee, purge switch or data-loss escape. Operational application rollback normally retains additive0009; reverse migration is a separately reviewed quiesced procedure. Backup/restore validation is required before rollout; avoid reversing populated limiter state to restore an older application.

## Scenario, permission and threat review before code

- Schema has no permission or global actor-read API: no path exposes cross-organisation actors or discloses limiter state. No grants, CurrentUser behavior, feature availability or clinical rights change. Its global actor key intentionally matches the future cross-route/branch limiter contract; this slice alone does not limit requests.
- A caller bypassing model validation must still be unable to store count0/61, duplicate/missing actor, null/misaligned/nonfinite minute. Test raw SQL as well as ORM; do not let Python DateTime conversion substitute for the PG infinity test.
- A malformed SQLite timestamp can yield UNKNOWN. Pin outer `IS TRUE`, not just normal aligned/seconds cases. Unsupported vendor must fail during compilation instead of installing an unenforced CHECK.
- Parameter-bearing source expressions reveal placeholder/parameter duplication mistakes that `F()` with no params would miss. Pin both tuple order and actual compiler source-call count.
- Historical migration replay must remain importable without current model assumptions; reverse guard must use supplied historical registry and database alias. Refused0009 reverse must preserve old document/history and network/identity rows as well as the new row. Existing0008 refusal tests target0007: with an empty0009 table, reversal may successfully remove0009 before0008 refuses on populated document history, so their `finally` must restore the captured current leaves even when the expected RuntimeError occurs. Preserve the historical refusal target; do not weaken it to0008.

## Acceptance and executable test design

Create the following named tests in `backend/tests/test_document_metadata_rate_window.py` (parameterization is expected). Use synthetic actors and existing test settings. Each rejected DB write uses a bounded savepoint/transaction so later assertions verify actual usable state. PG-specific cases must be explicitly marked/skipped on SQLite and then executed on actual PG17; a SQLite pass cannot close PG gates.

| Test name | Required evidence |
|---|---|
| `test_rate_window_model_is_discovered_with_exact_fields` | Registry resolution; class module; exactly three fields/no id; required/default absence including db_default; PK/OneToOne/PROTECT/related_name; exact constraint names and no custom indexes |
| `test_rate_window_valid_counts_and_unique_actor` |1 and60 allowed, distinct actor allowed, duplicate actor rejected by DB; row count preserved |
| `test_rate_window_database_rejects_invalid_count_or_null` | ORM and raw SQL rejection of0,-1,61,32768; NULL timestamp/count/actor; missing required values; no reliance on full_clean |
| `test_rate_window_actor_integrity_and_protection` | ORM actor.delete raises ProtectedError with row preserved; nonexistent raw actor FK fails at enforced constraint/commit; raw actor deletion fails rather than orphaning row |
| `test_rate_window_minute_constraint_rejects_precision` | Aligned instants accepted including offset-equivalent UTC minute and minute-boundary; second1/59, microsecond1/999999 and59.999999 rejected; update path as well as insert |
| `test_minute_expression_compiles_with_repeated_params` | Parameter-bearing DateTime Value/source expression; compiler called once, PG params3 copies/SQLite2 copies, exact placeholder order/constants and Boolean result; no literal user value in SQL |
| `test_minute_expression_rejects_unsupported_vendor_and_wrong_arity` | NotSupportedError for unsupported vendor; zero/two positional arguments rejected |
| `test_minute_expression_is_true_rejects_unknown` | Parameterized NULL expression returns false on each actual supported DB, not UNKNOWN; independent of column NOT NULL; generated constraint includes IS TRUE |
| `test_sqlite_minute_constraint_rejects_malformed_raw_values` | SQLite direct SQL insert and UPDATE: `not-a-date`, empty string, `infinity`, `-infinity`, impossible2026-02-30 rejected through constraint or safe DB error; no persisted invalid row |
| `test_postgresql_minute_constraint_is_finite_and_timezone_independent` | Actual PG17 inserts/updates under session UTC and Asia/Kolkata; aligned/seconds/microseconds matrix and direct SQL +/-infinity rejection; restore session timezone in finally; inspect generated/installed constraint finite+3arg UTC+IS TRUE |
| `test_minute_expression_migration_serialization_replays_stable_path` | deconstruct returns permanent path plus positional F; MigrationWriter serialized migration imports real path, reconstructs and compiles both dialects; no __main__/temporary import; repeat from fresh interpreter/environment |
| `test_rate_migration_forward_preserves_existing_rows` | Start0008 with non-vacuous synthetic actor/patient/appointment/encounter/document/network/identity rows; forward0009 creates only intended schema, old rows/values preserved, new table empty; generated SQL/state match model |
| `test_rate_migration_empty_reverse_forward_round_trip` | Actual MigrationExecutor0009->0008->0009, absent/present table and recorder checks; constraints work after replay; finally restore actual full graph leaves |
| `test_rate_migration_nonempty_reverse_refuses_before_ddl` | Actual nonempty reverse raises fixed error, execute wrapper records no DROP/ALTER DDL, table/constraints/row/recorder unchanged; existing rows preserved; clean only test-owned row then restore actual leaves in finally |
| `test_rate_reverse_guard_uses_historical_registry_and_alias` | Supplied historical registry/nondefault alias used; empty returns/no writes; nonempty raises; final operation identity is this reverse function; no runtime model access |

For SQL NULL expression test, use typed DateTime NULL where PG needs type resolution; NOT NULL alone cannot establish the `IS TRUE` behavior. For raw infinity/invalid text use bound parameters with explicit dialect-appropriate timestamp conversion, never Django's Python read adapter as the assertion. Observe rejected writes at DB constraint execution/forced constraints/commit as appropriate. PG FK may be deferred: test the actual enforcement point rather than expecting every statement to raise immediately.

Schema B2a-S acceptance does not include first-row concurrency,60 admissions/61st429, reset/backward-clock behavior, User lock ordering, disabled503 retention, session/network samples, transaction timeouts, unknown COMMIT, audit/quota or HTTP/CSRF. Those remain parent B2a/B2b/B2c/B3 tests; do not mark them passed or duplicate their implementation here.

## Task1: Close design feasibility and freeze only B2a-S

- [ ] Coordinator checks authenticated usage and existing active work, actual migration leaf/file conflicts, latest admission/service amendments and this scope.
- [ ] Independent scenario/permission and threat/abuse review accepts schema/test/reverse boundaries; record findings/rulings. Parent B2a remains DRAFT.
- [ ] Coordinator runs an ignored, isolated design prototype on actual PG17 before production code: compile/execute the candidate isfinite+UTC+IS TRUE expression, timezone/precision/infinity/NULL cases and SQLite malformed/UNKNOWN/parameter cases. No shared/live DB mutation. Record exact source hash/versions/commands/results and cleanup. Prototype success is feasibility, not production acceptance.
- [ ] Coordinator records exact stable-path/serialization verification method and approves this narrow file/function/schema/test freeze. A prototype may mirror the intended import path inside its isolated root; it cannot establish that a not-yet-written production class exists. Real production-path replay remains mandatory after GREEN. No production code until the schema feasibility and independent freeze gates close.

## Task2: Literal RED, then minimal dormant schema

**Files:** the bounded production/test files above. **Consumes:** configured User and existing core0008. **Produces:** discovered model, permanent expression and additive0009 only; future B2a interfaces/field names remain unchanged.

- [ ] Write model/compiler/schema/migration tests first, including the exact existing0008 refusal-test `finally` amendment above. New tests must request the absent model/class/migration and fail for those specific missing features, not unrelated environment errors. Do not add production scaffolding to manufacture RED.
- [ ] From `E:/coding/HMS/backend`, run `.venv/Scripts/python.exe -m pytest tests/test_document_metadata_rate_window.py -q`; preserve literal failing output/count/source. Coordinator confirms production model/expression/migration are absent before permitting GREEN. PG RED runs through the coordinator's authorised isolated runner where required.
- [ ] Add minimal expression/model and discovery import; generate0009 using existing interpreter, inspect generated schema and add the final reverse guard. No unrelated formatting or existing migration edit.
- [ ] Run targeted SQLite tests to GREEN and inspect generated SQLite SQL. Run `manage.py check` and `manage.py makemigrations --check --dry-run`; expected check0/no drift, record actual results only.
- [ ] Coordinator executes all targeted actualPG17 tests, generated SQL, fresh migration from scratch, existing0008 forward and round-trip/reverse refusal with the real production stable import. Re-run fresh-process MigrationWriter replay. Do not close PG acceptance using mocks or design-probe output.

## Task3: Independent review, regression and publication

- [ ] Fresh independent source/security review checks exact SQL/parameter paths, permanence, no new authority, guard order/alias, no runtime capability or broadened scope. Resolve material findings and rerun affected tests.
- [ ] Run targeted new tests plus `tests/test_patient_document_models.py` and `tests/test_patient_document_contracts.py`; coordinator runs full backend actualPG/check0/no drift and required root docs/OpenAPI/link checks. Existing frontend is unchanged; browser coverage is not inferred. Record backend, commands, counts/skips/times; migration tests restore graph leaves even after failure.
- [ ] Coordinator updates HMS/plan/ledger with detailed affected data/interfaces/security decisions and planned/implemented/verified distinctions, actual RED/GREEN/review evidence, remaining parent gates. Commit bounded source/tests/docs, normal push, verify remote SHA and exact CI; no force push or unrelated files.
- [ ] Under the standing completed-code rule, coordinator prepares and reviews a *new* bounded preview update for this changed source: exact successful CI/candidate, backup/restore, additive0009/empty-table validation, config/security/other-app preservation, rollback that retains schema, live HTTPS/API/security/regression verification and actual runtime/source SHA. Preserve existing preview release until gates pass; do not re-bootstrap or repeat initial deployment. A successful source push is not deployment evidence.
- [ ] Coordinator records verified deployment/live evidence and outstanding browser/staff/ingestion/real-data gates in MD records and publishes those records with verified remote SHA. A docs-only plan publication requires no app restart. Failed/blocked rollout remains accurately unfinished; preserve recoverable work/state.

## Remaining freeze gates and evidence limits

Only narrow coordinator/reviewer acceptance and isolated actualPG feasibility remain before B2a-S freeze; the requested field names, SQL shapes, stable path, rejection semantics and file boundary are specified here. No owner product choice is required by this draft. If PG/SQLite/migration feasibility contradicts these rules, stop and amend the design rather than weaken constraints or silently require UTC sessions.

This author's actions were local source/document reads and creation of this document only. No executable tests/prototype, dependency install, code/migration change, Git action or VPS access was performed. The coordinator's production-path replay, executable RED/GREEN, independent implementation review, actualPG acceptance, publication and changed-code rollout remain unchecked. No parent admission/service/API/UI completion claim follows from approval or completion of this schema subset.

## Coordinator freeze and review —26 October2026

Freeze ONLY B2a-S exact file/interface/schema/test boundary above; parent B2a authority/admission/business/HTTP remain DRAFT/unimplemented. Independent scenario/threat reviewer accepted boundaries and required the existing0008 refusal-test true-leaf finally fix; included. Initial SQLite probe failed its raw count1 fixture because a raw aware datetime bypassed Django's canonical UTC adapter. Corrected only valid datetime fixture preparation; invalid strings remain direct SQL. Coordinator re-executed SQLite25cases plus duplicate/replay and actual TLS PostgreSQL17.11 two connection timezones25cases each plus duplicate/replay. Imported prototype MigrationWriter serialization/generated DDL/forward/reverse/replay/parameter repetition all passed; temporary resources removed and live preview active. See [feasibility](../operations/document-rate-schema-feasibility-2026-10-26.json). This closes BOTH SQLite and PostgreSQL design feasibility, not production stable-path/model acceptance. Real permanent import, model/migration tests and full regressions remain RED/GREEN/post-code gates. Existing clean shared feature checkout is retained under owner-authorised shared-checkout coordination; no additional worktree or duplicated implementation.
