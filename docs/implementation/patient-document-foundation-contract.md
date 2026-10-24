# Patient document foundation — frozen schema-only contract

24 October 2026. **FROZEN by coordinator after fresh independent scenario/threat/test review; implementation not yet started.** Narrows [architecture proposal](patient-documents-design.md) after [security](patient-documents-security-review.md) and [UI](patient-documents-ui-plan.md) review. This contract takes precedence for the proposed next unit only. Full upload/document APIs remain proposals, not a frozen delivery requirement.

## Exact scope and choice

Add three dormant persistence models and their migration/constraint tests only: `PatientDocumentIntent`, `DocumentIntentReceipt`, `DocumentAccessEvent` in the existing core app. No endpoint, URL, role/grant, current-user capability, page action, frontend, service mutation API, storage/scanner runtime, dependency install or deployment. No durable scan work/outbox yet. No upload/download success, ready state or document UI is introduced. No existing patient/check-in/Encounter code is redesigned.

Two choices were reviewed: (A) persist only the two intent states actually represented by this schema; (B) preallocate ready/scan states and provider fields for future ingestion. Recommend A: dormant rows cannot represent a falsely clean/available file and future ingestion receives its own reviewed migration. The cost is another additive migration later; compatibility is maintained by stable UUID identity, version and protected parent references, not speculative nullable provider fields. All exact choices below are engineering proposals rather than owner policy decisions.

## PatientDocumentIntent

| Field | Exact proposed definition |
|---|---|
| id | UUID primary key, server default UUID4 |
| patient | FK core.Patient, required, PROTECT |
| created_by | FK configured auth User, required, PROTECT |
| category | string max32, only `registration`, required, no permissive default |
| declared_filename | string max120, required; display metadata only, never a filesystem path |
| declared_media_type | string max32, only `image/jpeg` or `image/png`, required |
| declared_size_bytes | positive bigint, inclusive1..10485760 |
| declared_sha256 | string64, required, lowercase ASCII hexadecimal exactly64 |
| status | string max16, only `pending` or `withdrawn`, default pending |
| version | positive integer default1, inclusive1..2147483647 |
| created_at | required timezone-aware timestamp, server default timezone.now, never editable through a future caller payload |
| expires_at | required timestamp, exactly created_at+30minutes |
| withdrawn_at | nullable timestamp, no default |
| withdrawn_by | nullable FK User PROTECT, no default |
| withdrawal_reason | string max500, blank default empty |

Do **not** add branch/organisation/encounter columns: branch and organisation derive through the immutable `Patient.branch` and Branch.organisation chain. This avoids storing a conflicting scope tuple. Existing patient API forbids branch changes; future services must preserve that invariant and separately freeze any patient merge/transfer design. No storage IDs, scan verdicts, bytes, accepted generation, ready state, receipt of content or encrypted content key in this unit.

DB constraints, not only model choices: category equality; media allowlist; declared size/version range; status allowlist; digest length and lowercase hex shape using a migration-tested expression supported by both configured SQLite test DB and production PostgreSQL; filename length1..120; expiry equality to created_at+fixed30minutes using a backend-supported Django expression; pending requires all withdrawal fields absent/empty; withdrawn requires withdrawn_at/by plus reason length10..500 and withdrawn_at>=created_at. If portable expression validation reveals a backend gap, report it before freeze/code rather than silently omit a promised constraint. Database field max_length alone does not prove SQLite length enforcement.

Additional validation/service invariants (not claimed as ordinary SQL CHECK enforcement): reject filename controls, NUL, slash/backslash, dot paths, all-whitespace names; trim outer whitespace before storage; validate strings as exact scalar types without coercion; forbid declared fields/patient/category/creator/time changes after creation; withdrawal only by creator with current conjunctive grants and expected_version, current time strictly before expiry; increment version once on a future authorised withdrawal. Cross-table scope/authority is never inferred from a UUID or enforced by the model choice enum alone. No such service exists in this foundation.

Indexes: `(patient, -created_at, -id)` for bounded patient-local newest-first reads; `(status, expires_at, id)` for a future bounded maintenance selector. Ordering `-created_at,-id`. Do not add a global filename/digest search index, shared-content uniqueness or tenant-crossing deduplication.

Expiry is a future pure projection: pending at selected server_time>=expires_at presents expired; no expired DB state, version bump, deadline extension or read-time repair. Withdrawn remains withdrawn. Exact equality belongs to tests, and does not imply a cleanup job. No deletion/retention duration is approved.

## DocumentIntentReceipt

This is **metadata command idempotency**, not an accepted-byte upload receipt. The future immutable upload receipt (original version+generation+digest) needs a separately reviewed ingestion schema; do not conflate them.

Fields: UUID id/default UUID4; required `actor` User FK PROTECT; `operation` string max32 exactly `intent.create` or `intent.withdraw`; `key` UUID required; `fingerprint` string64 exact lowercase SHA256; `result` required FK PatientDocumentIntent PROTECT; `created_at` timestamp default timezone.now. Unique `(actor,operation,key)`; fingerprint shape and operation enum DB constraints. No request/response JSON, filename, clinical content, expiry or credentials. The unique index is the only additional required index; no speculative retention sweep.

Future service invariant: claim, intent mutation, result binding and required result disclosure event commit in one transaction. Required result FK permits no committed incomplete claim; a future implementation may insert after acquiring authority locks and use a savepoint/unique collision protocol, which must be designed/tested before endpoints. Replays reauthorise current patient/category scope and return current terminal projection; altered fingerprint409. Replay never creates a new intent, extends expiry or withdraws twice. This unit adds no helper/service and does not alter existing IdempotencyRecord/reception semantics.

## DocumentAccessEvent

Dedicated bounded disclosure accounting, not a new generic administrative feed. Fields: UUID id/default UUID4; required `actor` User FK PROTECT; required `patient` Patient FK PROTECT; nullable `document` PatientDocumentIntent FK PROTECT; `operation` string max32 enum `intent.list`, `intent.detail`, `intent.create_result`, `intent.withdraw_result`; `result_count` positive small integer inclusive0..100; `projection_sha256` string64 lowercase SHA256; `correlation_id` UUID required server generated; `created_at` timestamp default timezone.now.

No filename, document title, file bytes, patient name, request query/body, arbitrary details JSON, free-form reason, scanner text, browser/device/IP or secret is stored. Patient derives branch/org; when document is present it must belong to the same patient (future service/model validation invariant, not cross-table CHECK). Projection digest binds a canonical sorted list of disclosed UUIDs without storing an unbounded list. For list document=null and result_count0..100. For every other operation document is required and result_count=1. DB CHECK enforces this shape plus enum/count/digest shape. `projection_sha256` is audit integrity metadata, not a content hash or a claim of tamper-proof logging.

Indexes `(patient,-created_at,-id)` and `(actor,-created_at,-id)` only. Append-only service policy and least-privilege privileges belong to later runtime/operations contracts; this model does not make DB administrators unable to alter rows. Existing generic AuditEvent/history projections must remain untouched and must not union this table. No access-event endpoint/admin registration is added. Future reads/replays must fail503 without disclosure if their event cannot commit; schema-only tests cannot prove that runtime guarantee.

## Migration, protection and scope

Source migration directory currently ends at `0007_network_policy`; proposed next migration depends on that migration, with the graph rechecked before implementation in case concurrent work adds one. Create only these tables/constraints/indexes; no existing data rewrites, role grants, fixtures containing records, global settings or schema deployment. Creator/patient/result/event FKs all PROTECT; demonstrate protected references on deletion. No cascade removes intent/audit/retry history. Operational retention/purge/legal hold policy and privileged backup dependencies remain deferred.

Forward migration must work against existing synthetic organisation/patient/user rows without changing them. Reverse is structurally the exact removal of new tables/constraints/indexes in reverse dependency order, with an explicit data-protection gate: reversal may execute automatically only while all three tables are empty; any rows cause a deliberate migration error before dropping any table. Implement this as a reverse-first guard in migration operation ordering and prove it transactionally on PostgreSQL. No automatic export/purge or destructive force option. Future production recovery requires reviewed backup/restore/rollback procedure; an empty schema reverse test is not a recovery drill.

Integration gate: existing `backend/tests/test_network_policy_models.py` migration tests hardcode latest0007 and restore0007 in finally. Adding the foundation migration requires restoring to the **actual current graph leaf** before subsequent tests, while retaining the original tested historical network migration boundary. Change fixture restoration only as necessary; do not weaken network singleton assertions. Foundation forward/pristine reverse/refusal tests must confirm existing network singleton/configuration rows remain unchanged. Exercise the nonempty guard for each of the three tables and assert refusal occurs before any reverse DDL, receipt refusal with a valid parent and a directly isolated historical-manager guard-branch test where necessary (never disable FK integrity to fabricate a dependent-only state). Do not claim this reversal guard prevents DB administrators from dropping tables; it protects the supported migration path.

## Pre-code review and RED matrix

Scenario review: dormant pending metadata; withdrawn metadata completeness; expiry equality; no encounter, clinical category or ready file; no branch tuple inconsistency; receipt collision; event minimality; protected reverse. Threat review: model choices bypass via direct ORM/bulk create; max_length not enforced on SQLite; digest coercion; partial receipt; dangling event; cross-patient event; accidental generic admin feed; destructive downgrade; claims of actual scanning/delivery from schema presence.

Executable foundation tests must first fail because the three models/migration are absent, not because the runner/dependencies are broken. Then verify:

1. Valid pending/withdrawn synthetic rows and protected relations; existing patient/appointment/Encounter records unchanged.
2. Direct DB rejection of category clinical_reference, unknown media/PDF, size0/over10MiB, version0, malformed/uppercase/short digest, empty/overlength filename, wrong expiry, unknown/ready state and every invalid withdrawal-state combination; valid boundary values succeed.
3. Duplicate `(actor,operation,key)` rejected even with different fingerprint/result; distinct actor/operation/key allowed; invalid operation/fingerprint rejected; result required and protected.
4. Event operation/count/document-shape and digest constraints, invalid blank/missing required fields rejected; model validation rejects document from another patient. Record plainly that direct SQL cross-patient relation is service-constrained until a trigger/composite-FK contract is explicitly chosen; do not claim SQL isolation from this table alone.
5. Migration forward/back/forward on an empty synthetic DB; reverse with any intent, receipt or event row raises before drops and preserves every row/table. PostgreSQL verifies actual constraint/index definitions and transactional preservation; SQLite fast tests alone do not prove production SQL parity.
6. `makemigrations --check --dry-run`, Django system checks and existing relevant backend suite. OpenAPI operation count, URL set, role map, CurrentUser and frontend remain unchanged. No source install/deployment/byte integration/browser result is claimed.

After root freeze: tests/schema implementation may proceed under assigned ownership. Required documentation updates and commits/push remain coordinator-only. This draft has no executed runtime tests or migration evidence.

## Freeze precision and review ruling

Fresh independent reviewer found no Important schema-only contradiction. All three SHA256 fields require explicit Length=64 AND lowercase-hex shape (including trailing-newline rejection); do not rely on regex end anchors alone. Guard is last forward operation/first reverse, uses historical models and migration alias. Receipt reverse test keeps its valid parent; use isolated manager probe to exercise the receipt-only guard branch without disabling FKs. A future runtime rollback must quiesce writers or separately freeze locking; this dormant schema reversal is not a concurrent operational rollback guarantee. Existing active shared checkout/branch is retained under owner instructions/coordinator Git ownership.
