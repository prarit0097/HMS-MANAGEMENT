# Patient document foundation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development or executing-plans, with test-driven-development and fresh review. Coordinator alone owns Git.

**Goal:** Add a tested dormant schema for registration-document intent, metadata retry identity and protected disclosure accounting without introducing file access.

**Architecture:** Three core models with explicit database constraints and protected references; a guarded additive migration. Runtime service/API/permissions/storage/scanner/UI remain separate unfrozen work.

**Tech Stack:** Existing pinned Django/PostgreSQL, SQLite fast tests, pytest. No dependencies added.

**Spec:** [foundation contract](patient-document-foundation-contract.md), [review](patient-documents-independent-review.md), [plan](../../plan.md).

## Global constraints and review focus

Registration only; JPEG/PNG declarations only; no bytes/ready/encounter/duplicate scope. No APIs/page actions/capability advertisement. No public/private storage provision or production migration. Keep existing network singleton and all historical migration assertions. Supported reverse must refuse any nonempty new table before dropping anything. SQL CHECKs cannot enforce cross-table patient/document agreement; explicit model validation and later locked services are separate. Metadata audit schema alone does not establish audit-before-disclosure or immutable operations.

Ruling: continue in existing owner-directed shared checkout/feature branch, with file ownership and coordinator-only Git, preserving the running team rather than creating competing worktrees.

## Task 1 — independent pre-code freeze

- [x] Resolve Important foundation review findings and freeze exact fields/constraints/model validation/migration scope in contract.
- [x] Commit the reviewed contract/proposals, HMS/plan/ledger before production code; verify push SHA. No runtime claims from document checker.

## Task 2 — schema RED then implementation

**Create:** backend/tests/test_patient_document_models.py, backend/apps/core/document_models.py, backend/apps/core/migrations/0008_patient_document_foundation.py.
**Modify:** backend/apps/core/models.py discovery import only; backend/tests/test_network_policy_models.py migration finally restoration only.

- [x] Write dynamic model-discovery tests and schema boundary/PROTECT/receipt collision/event-shape/migration safety tests from contract. Use registered-model lookup so missing model assertion is the literal RED, not an import or runner failure.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_patient_document_models.py -q` from backend; capture RED before model code.
- [x] Implement the minimal three models, explicit constraints/indexes and same-patient model clean check. Generate/review0008, add reverse-first pristine guard, no seeded rows.
- [x] Preserve historical network migration test targets but restore actual graph leaf in finally. Run new tests plus existing network schema tests; system/migration drift checks.
- [x] Fresh spec/security/code-quality review and verified regression fixes if findings arise.

## Task 3 — verification and publication

- [x] Root inspect diff/review findings, run actual PostgreSQL suite including forward/pristine reverse/nonempty guard and retain durable evidence. Use existing private candidate validation only; no live schema or HBA changes. Revoke temporary test database creation privilege and verify disposable DB absent/old preview active.
- [x] Root schema/map/link/whitespace/credential checks. OpenAPI operation count46, URLset/roles/frontend unchanged. Do not repeat frontend/browser work for a schema-only change.
- [x] Update HMS/plan/ledger with actual counts/limits, commit/push and verify remote SHA. Inspect exact CI; distinguish source/migration test from deployment.

Next runtime work requires separately frozen metadata endpoints/OpenAPI/page actions/permissions/read audit/lock order, then byte/storage/parser/scanner contracts. Whole Task04 stays incomplete.

## Actual source verification —24October2026

Planningd8feaad committed/pushed/remote verified before code. Initial literalRED70failed6.31s from missing model discovery, followed by focusedGREEN. MissingFK regression1RED4.97s and cached-FK1RED2.33s fixed before acceptance; original independent cached probeRED1/5.70s recheckedGREEN with tracked relatedcases4passed1.92s. Final focused112passed17.72s (79foundation+33network), check0/nodrift. Root actualPostgreSQL658passed168subtests47.16s/check0/nodrift; candidate archive51c0558d356a6ba9975bcb7d31c649635ee87b1f178e55fe07c0df4aafa9168a, private durable log retained. Rootcleanup f/0/active confirms test privilege revoked/database absent/old preview active. No source migration deployed, no new API/grant/UI/file capability. Independent review has no remaining bounded finding. Publication/CI recorded by coordinator separately.

Source5aee4d29939161e09f53e862f407325daad02589 published and remote SHA verified, clean tree at publication. Exact GitHubCI40115929521 all3jobs successful, decoded658PG/168subtests54.36s/check0/no drift,132tracked frontend/typecheck/build24modules142ms,19root/15edge/OpenAPI/Compose/docs. Root candidate658PG/168subtests47.16s is distinct actual validation evidence. No source deployment.
