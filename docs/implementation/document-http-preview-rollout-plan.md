# Document HTTP preview rollout amendment

> **For agentic workers:** use Superpowers executing-plans for coordinator-only operations, TDD for helper changes and fresh review/verification gates. No second Git/VPS operator.

**Status:** 5 November2026, coordinator-frozen bounded contract after independent read-only operations/scenario/security/test review. Actual isolated protocol acceptance passed98checks in [6November evidence](../operations/document-http-framing-evidence-2026-11-06.json); concrete helper copies/exact final CI/rollout remain unexecuted and require review. This document does not claim deployment.

**Goal:** publish accepted B3 HTTP source to the existing restricted synthetic preview, retaining effectiveFalse, all current data/security and other applications.

**Architecture:** inherit the completed [business rollout](document-business-preview-rollout-plan.md) backup, source-switch, worker/socket, rollback and preservation controls. Replace dated source identities and direct-service clone proofs with genuine HTTP proofs; replace obsolete live metadata GET404 probes with empty unsupported HEAD/OPTIONS. No new page/UI or feature activation.

**Tech stack:** existing Django5.2.18/DRF3.16.1/Gunicorn26.2.0/PostgreSQL17.11 TLS/Nginx1.24, current venv/static/env/keys/core0009. No installs/build/DDL.

**Spec:** [frozen B3 contract](document-http-plan.md), [metadata contract](patient-document-metadata-contract.md), [prior runtime evidence](../operations/document-business-preview-evidence-2026-11-03.json), [current validation](../operations/document-http-validation-2026-11-05.json), [HMS](../../HMS.md), [plan](../../plan.md), [ledger](ledger.md).

## Constraints, interfaces and review focus

- Recorded prior260eeb9a6ed3b1af8824ef821cfc23205bde4d2b at `/opt/hms/releases/preview-20261103-260eeb9`, core0009/effectiveFalse, must be freshly reconciled. Historical row/config/container counts never override actual owner activity.
- Expected application delta is document_api.py, three string URL patterns and the separately reproduced/frozen one-line absolute budget-deadline correction in document_access.py. Tests/isolated runner/contracts/records accompany it. No changed B1/admission/business/models/migrations/settings/grants/frontend/live proxy/dependencies without a separate reproduced defect and scope amendment.
- No supported live document GET/POST, admission/business invocation, flag enablement, bootstrap, recovery consumption, reenrollment, policy/grant change, shared HBA/proxy edit or older-dump overwrite. Preserve Basic AND network/session/CSRF/MFA security.
- Existing registration permissions, current organisation/branch authority and real session/CSRF apply. Master status creates no clinical rights. Only isolated clearly labelled synthetic fixtures may be written for rehearsal.
- Coordinator alone Git/VPS, authenticated usage at start/boundaries and mandatory fresh<=10 stop. No paid provisioning or real patient/lead data. Secrets stay in private root-owned files and never enter redacted receipts/Git.
- Source push does not establish runtime acceptance. Framing failure/inconclusive outcome blocks release; passing unit tests cannot substitute for actual Nginx/Gunicorn protocol/process cleanup.

Review risks and owning gates: old GET404 smoke invokes new disabled admission (Task3); owner limiter rows may legitimately exist (Task2 creates a separate actor); direct wrapper proofs miss CSRF/transport (Task2 HTTP only); rollback must retain nonempty new tables (Task2 prior260); source/runtime drift or inherited success booleans manufacture evidence (Tasks1/4 exact observed identities).

## Task1 — accepted source and recoverable baseline

**Files:** immutable committed candidate/manifest; reviewed new `.local/http_*` operation helper copies; fresh receipt under a unique collision-checked operations directory. Old business receipts/scripts are historical inputs, never overwritten.

**Interface:** accepted exact sourceSHA + actual current prior -> complete canonical archive/configuration/inventory/backup baseline consumed by Tasks2–4.

- [x] Require final337 actualPG HTTP/full backend/check/no drift, fresh adapter review, corrected framing safety review and actual isolated HTTP1.1/HTTP2/process/effect/cleanup gate on exact final bytes. Preserve labelled limitations and actual warnings/skips.
- [x] Normal push/remote fullSHA equality and exact successful CI head/allthreejobs before immutable preview candidate. Promote four OpenAPI/page-action source implementation dispositions after source and isolated-protocol acceptance; preview deployment verification, flag/UI/release status remain separate.
- [x] Build archive from committed canonical Git blobs, exact complete file set/hash manifest/archive checksum. Test archives from working-tree files or ignored test settings are never release artifacts.
- [x] Freshly attest prior/current symlink/workers/listeners/core0009, effective booleanFalse and provenance, default-only DB/no routers/PG floor/empty migration plan, all-table deterministic row receipts, security/password/recovery/operator/network state and actual retained factor decryption. Retain env/key/static/HBA/service/timer/config/other-app inventory. No migration execution or forced historical state.
- [x] Review exact new helper source/paths/cleanup ownership. Replace old identities/counts/CI claims. Unsafe helper behavior returns to literal RED/minimal fix/review before use.

## Task2 — restored-data HTTP and prior-source rehearsal

**Files:** fresh dump/checksum/restore list, verified receipt-owned isolated TLS targets and HTTP-specific clone helper. Consume Task1 exact source/prior/baseline; produce HTTP/current-data/key/rollback evidence.

- [x] Restore fresh snapshot into a verified owned isolated target; positively assert DB name/user/host/port/TLS/ownership before writes. Verify pristine all-table equality/current factor-key decryption/core0009 before fixtures/auth. Inconsistent snapshot/dump requires a new consistent pair.
- [x] Disabled clone uses separate ordinary synthetic reception actor/session, genuine full middleware/CSRF and exact candidate routes. One valid collection GET under effectiveFalse returns fixed503 and persists exactly one allowance, independently observed. Capture SQL/all-row state around this call: no patient/intent/receipt/event/audit access/change; distinguish fixture/login effects. Do not require retained owner rate rows absent or delete them.
- [x] Separate fresh enabled clone, verified pristine/key first; ordinary synthetic reception actor with genuine authenticated session/current branch grants/real CSRF, True only in child process. Genuine HTTP initial list/create/create replay/detail/withdraw/withdraw replay/final list with original bytes/idempotency headers/realCSRF. Require one intent/two receipts/seven linked disclosure events, per-call minute-safe admission, frozen projections/attribution and unrelated-row preservation. Direct services are not substitute transport evidence.
- [x] Exit enabled process, run exact prior260eeb9/False over the same retained nonempty clone. Real password/TOTP/session/scoped reads/logout, all four metadata tables identical before and after logout, narrowly explained auth effects. No reverse migration or row purge.

## Task3 — protected source-only switch and safe live verification

**Files:** reviewed HTTP-specific maintenance/switch/open/live-acceptance helpers and fresh quiesced receipts; consume successful Tasks1/2 and current usage; produce actual source/runtime/live preservation evidence.

- [x] Recheck no intervening operator/source change; close only HMS with established maintenance controls, stop HMS writers, quiesced backup/row snapshot, switch only accepted source. Verify canonical files/two workers/no old workers, socket ownership/principals, actualFalse/core0009 and zero table-row change before auth. Preserve other applications/env/keys/HBA/static/venv/security.
- [x] Reopen under retained protection and run existing Basic/MFA/CSRF/scoped read/logout/network/static/private-spoof checks with current owner state preserved.
- [x] Replace the old live metadata GET404 loop completely. Authenticated empty HEAD and OPTIONS only, on canonical synthetic UUID strings, after successful global action authority; fixed405, exactAllow and no admission/object lookup:

| Shape | Authority | Allow |
|---|---|---|
| `/api/v1/patients/{uuid}/documents/` | intent.list | GET, POST |
| collection + `{uuid}/` | intent.detail | GET |
| detail + `withdraw/` | intent.withdraw (write permission) | POST |

  OPTIONS fixedJSON method_not_allowed; HEAD empty wire body. Require no-store/VaryCookie/nosniff. Verify HTTP route availability without supported command paths.
- [x] Exactly compare all four live metadata tables with quiesced baseline, separate expected auth row/field deltas; other data unchanged. Any failed post-reopen probe or unexplained data/security delta immediately re-closes HMS only, preserves post-attempt evidence and enters rehearsed rollback/recovery. Unknown state stays closed; never blanket auth-table exclusions.

Rollback selects only rehearsed prior260eeb9, retaining0009/all current rows and repeating existing worker/auth/security/preservation checks. Never restore an older dump over subsequent legitimate activity. Uncertain state stays protected/closed for recovery.

## Task4 — recovery, cleanup and truthful records

- [x] Fresh postchange backup/checksum/list, pristine owned restore, exact all-table/current key/password/recovery/operator/network checks; clean only receipt-owned helpers and verify process/listener absence. Independently compare other apps/configs/containers/HBA/env/static/keys.
- [x] Record actual deployed fullSHA/file hashes/time/protocol/clone/live/restore evidence in HMS/plan/ledger/operations; verify normal push/remoteSHA. No invented inherited booleans. Documentation-only publication does not restart unchanged runtime.
- [x] Keep browser/keyboard/staff/phone import, useful ingestion/storage/scanning/UI and remaining clinical/finance/MCP/dataops/full-release gates explicitly open. Synthetic preview is not hospital real-data release.

## Concrete helper amendment map

Old `.local/business_live_acceptance.py` metadata GET loop must disappear in the new copy. Old `business_db_ops.py` direct disabled/enabled service proofs become HTTP clone proofs; prior compatibility comparisons through logout remain, repinned260eeb9. Build/stage/preclose/close/switch/open/grants/finish copies need fresh literal identities and evidence, not replayed dated scripts or truthy old success claims. Root reviews these concrete copies before any state-changing rollout action.

## Execution closed —6 November2026

Exactbdbe8c6 sourceCI42234437948 allthreeSUCCESS; final251canonicalfile/98actualprotocol acceptance, reviewed concrete HTTP clones/prior260, protected live switch/safe405 probes/no live admission/business,34tablepostrestore/currentkey and other52configs21containers preservation verified. See [measured rollout](../operations/document-http-preview-evidence-2026-11-06.json). Historical pending statements above describe their dated phase; this execution result supersedes them. MetadataFalse, UI/ingestion/browser/staff/phone/fullrelease remainopen.
