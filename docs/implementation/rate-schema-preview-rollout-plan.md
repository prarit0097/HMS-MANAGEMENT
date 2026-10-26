# Dormant document rate schema preview rollout design

**Status: COORDINATOR APPROVED FOR GATED EXECUTION / NOT YET DEPLOYED.** Coordinator review and exact candidate evidence are required before execution. This document does not establish implementation, test success, publication or deployment. Coordinator alone commits/pushes and changes the VPS; specialists may review disjoint evidence. No additional team is authorised by this document.

**Purpose:** satisfy the owner's completed-code sequence: verified Git push, reviewed/tested update of the existing restricted HMS preview, live verification, then accurate MD deployment records. Deploy only the frozen B2a-S dormant schema subset and its tests/fixture restoration fix. Parent B2a admission/services and document APIs remain unimplemented.

**Inputs:** [frozen schema plan](document-rate-schema-plan.md) (coordinator identifies freeze checkpoint `c53bdf8`; verify full committed identity before execution), [previous rollout plan](preview-update-2026-10-26-plan.md), [recorded live evidence](../operations/preview-update-evidence-2026-10-26.json), [HMS](../../HMS.md), [plan](../../plan.md), [ledger](ledger.md), and latest owner instructions. Historical first-rollout instructions are context, not a procedure to repeat.

## Baseline and bounded change

The recorded current preview is `https://hms.praritsidana.com`, release `522f00d184165249b522c0c3a89bb782458e45e6`, application source `66bfa10160eae5342b0b64a601ad05b992d40753`, at `/opt/hms/releases/preview-20261026-522f00d`. It uses `/opt/hms/releases/venv-20261026`, two Gunicorn workers, core0008, existing durable keyring/enrolled owner, explicit network operator, revision6/no pending candidate, Basic plus app-session/network protection, root:www-data0750 socket parent and final socket0660. These are recorded facts requiring fresh read-only attestation, not fresh live claims in this draft.

The old committed archive had195 verified files. That number is not the expected new archive size: derive the candidate manifest from its exact Git SHA, including new0009/test files, and verify every candidate file independently. Record application-change SHA separately from a documentation-only deployment-record SHA.

| Surface | Allowed change / invariant |
|---|---|
| Python source | Only frozen document model/expression, discovery import and0009; new schema tests and the existing0008 refusal-test true-leaf `finally` restoration fix |
| Database | Add `core_documentmetadataratewindow` with actor PK/FK and count/minute constraints; append0009 recorder entry; existing data and security state preserved; new table empty |
| Frontend/static | Existing real static directory and served bytes retained; no build replacement/collectstatic needed for this Python-only slice |
| Dependencies | Reuse verified immutable `/opt/hms/releases/venv-20261026`; requirements/lockfiles unchanged; no pip install or shared/live venv mutation |
| Configuration/security | Preserve app.env, keys, owner/operator memberships, Basic, approved environment policy, revision6/no pending state, service unit, proxy/includes, UDS path/rights, DB TLS/HBA and backup timer |
| Other VPS apps | Preserve48 recorded other Nginx configuration files and18 existing container identities; re-inventory if legitimate drift exists and reconcile before proceeding |

No bootstrap, owner bind/operator grant, MFA enrollment/rotation, policy apply/confirm/revert/recover, seed data, HTTP/API/UI/grant/setting change, first-install preparation, full prior rollout or production hospital release belongs here. New runtime dependencies, changed infra/static/config, another migration leaf or unexplained baseline drift require amended review before mutation.

## Approach and review choice

The proposed approach is a short HMS-only maintenance interval: quiesce workers, back up, apply additive0009 from the exact immutable candidate, switch `/opt/hms/current`, start the existing service and verify before reopening. Retain current venv, static and security configuration. This keeps source/database transitions observable and eliminates concurrent app writes during migration.

An online rolling change offers little benefit for an unused table and adds mixed-worker/version ambiguity; it is not selected. Rebuilding the venv, static delivery or network/MFA setup repeats completed work and enlarges the failure surface; it is outside this design. Application rollback may retain0009 only after actual compatibility rehearsal; database reverse/restore is not the normal rollback mechanism.

## Gate 1 — exact implementation, usage and publication

- [ ] Coordinator checks authenticated usage, latest checkpoint/deadline and active work. All applicable windows must be available and above10%; a fresh at-or-below10% reading invokes the owner's checkpoint/cooldown rule. Do not enter live maintenance without enough bounded capacity or a safe closeout path.
- [ ] Confirm schema RED preceded production code; frozen scope, permanent expression import, SQLite GREEN, actual PostgreSQL17 timezone/finite/raw-SQL cases, fresh-process serialization/replay, migration round-trip/refusal and exact0008 fixture restoration have implementation evidence. Isolated feasibility output is not production acceptance.
- [ ] Fresh independent source/security review closes material findings. Full actual PostgreSQL regression, Django `check`, migration-drift check, root/schema/docs/OpenAPI/link checks and required exact CI jobs pass for the code candidate. Record exact commands/counts/skips/times, run ID and full SHA; do not reuse historical1276 counts as new evidence. Unchanged frontend CI evidence may be recorded without inventing a new local browser run.
- [ ] Coordinator publishes the completed bounded change with required HMS/plan/ledger updates, verifies full remote SHA equality and exact successful CI. Stage a committed archive from that exact SHA; no working-tree copy or uncommitted hotfix. Compare requirements, frontend, infra and historical migration hashes against live baseline; expected production delta is only the frozen files. Review unexpected diff before continuing.

**Pass condition:** reviewed exact pushed candidate, fullPG/no drift, successful exactCI and immutable manifest/digests. Code publication alone is not rollout completion.

## Gate 2 — fresh inventory and private recovery receipt

- [ ] Read-only attest actual current symlink/release,195-file baseline manifest, worker generation/listeners, service/static/env/config/keyring descriptors and permissions, core migration graph, backup timer and app DB role restrictions. Inspect private values privately; publish no secrets, MFA material, session/Basic credentials or credential-bearing commands.
- [ ] Record prechange table counts and privacy-safe deterministic comparison receipts for existing data, including document/history, actor/membership/operator, identity and durable network tables. Separate security/session rows expected to change during later authentication probes from rows that must remain unchanged during the migration itself. Verify one org/120beds/zero patients only if still true; unexplained difference is a stop, not permission to overwrite.
- [ ] Confirm actual network revision6, effective policy fingerprint, owner/operator identity/version and no pending candidate. Record existing MFA enrollment/key identifiers without secret/ciphertext disclosure. Any legitimate drift requires an explicit revised baseline; do not reset to revision6.
- [ ] Capture other48 configuration file hashes,18 existing container IDs, shared HBA hash, other-site reachability and resource capacity. Keep the exact baseline list private/redacted as appropriate. A200 proves reachability, not response-body equality.
- [ ] Create a root-only deployment receipt containing full candidate/baseline SHA, manifest/archive digests, old/new release paths, static path/hashes, unchanged venv, service/config/env/keyring custody, migration plan, maintenance/recovery commands and backup identities. Verify unique release/staging paths are real HMS-owned paths with no collision/symlink escape; do not overwrite baseline artifacts.

**Pass condition:** fresh baseline matches reviewed expectations; private recovery materials and tested access remain available. No secret output enters Git or public logs.

## Gate 3 — actual core0008 restore and candidate rehearsal

- [ ] Obtain a fresh existing-preview backup after MFA enrollment and final revision6 state. Use the existing dedicated backup mechanism; verify nonempty dump, SHA256 and `pg_restore --list`. Preserve matching keyring/env separately with private access controls. The old core0001 backup is insufficient for this rehearsal.
- [ ] Restore into a uniquely receipt-owned isolated TLS PostgreSQL database/helper using the established reviewed lifecycle. Verify exact target DB/labels/IDs before restore or cleanup; no shared HBA/firewall change, live test connection, shared PG restart or lingering app CREATEDB. Record isolation/cleanup proof.
- [ ] Before migration, assert restored core0008, all baseline counts and selected old-row values, policy/revision6/no pending, owner/operator memberships/version, enrolled-secret decryption using retained private keys, password hash and recovery-code hashes/count. Do not disclose secret plaintext or consume recovery codes.
- [ ] With the exact candidate archive and retained venv, inspect `migrate --plan`: only0009 is new. Apply0009 to restored DB, run `check` and no-drift check; verify exact table/columns/PK/FK/count+finite-UTC-minute constraints/recorder and zero new rows. Compare all pre-existing table counts/selected values and identity/network/key-decryption receipts before any login test changes them.
- [ ] Run actual candidate targeted schema tests separately in their own disposable test DB, not in the populated restore. Rehearse empty0009 reverse/forward and nonempty reverse refusal only in isolated test resources. Nonempty guard must refuse before DDL and retain row/constraints/recorder. No artificial rate-window row or reverse test on live preview.
- [ ] Rehearse previous application source against the upgraded restored DB using retained venv/config equivalents and guarded synthetic auth/read smoke checks. This is required before choosing a symlink-back rollback that retains0009; additive DDL alone is not compatibility proof. Keep permanent expression source available in candidate/recovery artifacts for historical replay; old code must not execute migration commands against unknown0009 history.
- [ ] Stage the exact immutable release from committed archive, root-owned/nonwritable by workers; verify every candidate manifest file/digest and absence of secret/test output. Compare retained built/static hashes to live served baseline: CSS `e326cb9299958b870c1d1aa243363203c753037ae1105fee7cd9bc628dc1e4a2`, JS `b5208f46e869bb4f7dbc26d406ab31424b5fb50952c32387000717d9c72c14ad`. Record any HTML/remaining assets in a complete static manifest too.

**Pass condition:** actual post-MFA core0008 restore upgrades cleanly, old data/security state and keys survive, new table empty, exact source/static verified, rollback compatibility known. A failed rehearsal blocks live migration.

## Gate 4 — short HMS-only maintenance and coherent source switch

- [ ] Recheck usage, exact candidate/CI, live no-drift/no-pending and resources immediately before maintenance. Freeze the command sequence/timeouts and last safe reopen decision in the receipt. Only coordinator mutates VPS.
- [ ] Close only HMS using the established reviewed maintenance mechanism; verify shell/assets/API are denied externally and no bypass/private route is exposed. If its established mechanism needs temporary HMS-only config, capture/restore exact bytes, syntax-test and graceful reload; do not redesign or change global proxy behavior. Preserve SSH recovery and other apps.
- [ ] Stop only `hms-preview`; confirm old workers are gone and no HMS writers/jobs are active. Take the final quiesced pre-migration backup/checksum/list and capture exact0008 counts/security fingerprint. If state changed since rehearsal, reconcile or stop before DDL.
- [ ] Execute candidate migrations with the existing private app environment/TLS/role against the explicitly verified preview DB using `/opt/hms/releases/venv-20261026`. Confirm plan only0009; migrate once, then check0/no drift, recorder/constraints and empty rate table. Compare existing data/counts, revision6/no pending, owner/operator and MFA/key metadata before reopening. No bootstrap/policy write or default filling.
- [ ] While closed, atomically switch `/opt/hms/current` to the unique verified candidate. Preserve real static directory, venv, env, service unit and proxy includes. Start existing service; wait boundedly for two new healthy workers with correct candidate source paths/hashes, old worker absence and expected loopback listeners. A reload/start return code alone is not readiness.
- [ ] Verify existing trusted-loopback probe semantics, private external404, backend API readiness and static UDS owner/mode/parent traversal (root:www-data0750; final socket0660). Socket appearance is asynchronous: wait within the receipt deadline while maintenance stays closed; never relax path rights to obtain readiness. Verify no new public listener and config/env/static hashes unchanged.
- [ ] Remove only the temporary HMS maintenance gate after all checks pass, restore exact expected proxy bytes and verify readiness externally. Record maintenance start/end and switch UTC, current target and actual process release/source SHA.

**Pass condition:** coherent exact candidate source and0009 run with unchanged security/static/runtime configuration; no mixed old workers; no user exposure before readiness.

## Gate 5 — live positive/security/read verification without policy drift

- [ ] Verify no-Basic/wrong-Basic denial; Basic alone does not confer app session. Allowed-policy login/shell/assets work with no-store/security headers. HEAD/range/conditional/wildcard static behavior and hashes remain correct; private probe/check paths remain404 externally, including spoofed Forwarded/XFF/marker headers.
- [ ] Use existing enrolled owner credentials privately: fresh password+TOTP challenge, pending-challenge denial, verified session/me and authorised network read/history. Verify secure cookies and missing-CSRF mutation denial with a valid otherwise-authorised context so failure is meaningful. Use valid CSRF on supported safe operations; no equivalent-policy apply/confirm/revert loop, MFA reenrollment or recovery-code consumption.
- [ ] Verify ordinary reception reads, bed101+ pagination and representative existing scope denial; logout and prove session invalidation. Use synthetic existing scope only. Document expected session/last-login/security-audit deltas from these checks separately; the migration itself must not have caused them.
- [ ] Re-read network effective fingerprint/revision6/no pending and operator state, confirm rate table remains empty after normal traffic, and confirm four metadata operations remain planned/unavailable through their existing contracts. Dormant schema is not a limiter/admission/API or permission capability.
- [ ] Recheck external blocked backend/DB/helper ports against current inventory, UDS path/listeners, other-app48 configuration hashes/18 existing container IDs, shared HBA and site reachability. No deliberate live outage/lockout or destructive matrix rerun; prior isolated edge/lifecycle proof plus unchanged code/config does not become a new live fault claim.
- [ ] Preserve existing open actual browser/Basic-prompt/keyboard/staff walkthrough and owner authenticator-import gates unless actually performed with new evidence. API/byte success cannot close them. A detected UI regression blocks acceptance; unrelated pre-existing open hospital-release gates remain explicit limitations of restricted synthetic preview.

**Pass condition:** actual deployed bytes/auth/network/read/logout behavior verified, no unauthorised capability, no policy drift and no other-app change.

## Gate 6 — post-change recovery evidence and publication

- [ ] Verify existing backup timer remains enabled; create post-change dump/checksum/list. Restore that dump into a new receipt-owned isolated TLS database, verify0009/empty table, old data/counts and final security policy, password/recovery hashes and actual MFA-secret decryption with retained keyring. Record expected auth-test audit/session changes; clean only verified owned resources and verify live app role NOCREATEDB.
- [ ] Save redacted operations evidence with baseline/candidate/full pushed SHA, exactCI/actualPG provenance, archive/file/static digests, actual deployed path/process SHA,0008→0009, checks/timestamps/results, backup restore/key checks, policy baseline/final, other-app preservation and cleanup. No private values in artifacts.
- [ ] Coordinator updates HMS.md, plan.md and ledger together with detailed implementation/verified/deployed distinctions and a new change record. Record all unfinished checks and failure dispositions accurately. Run docs/link/root checks and whitespace/secrets/diff review, commit/push normally and verify remote full SHA. A documentation-only record commit does not restart unchanged verified code. Any code fix needs its own exactCI/push and reviewed candidate update before completion.

## Failure decisions and rollback boundary

| Failure point | Required decision |
|---|---|
| ExactCI/review/baseline/restore/staging fails before maintenance | Leave live522f00d unchanged; preserve evidence; repair candidate or amend scope. No live migration |
| Maintenance cannot be proven closed / old writers remain | Do not migrate or switch; restore known gate state and investigate |
| Migration fails or commit outcome is uncertain | Keep HMS closed; inspect actual DB recorder/table/constraints and preserve attempt backup/logs. Do not blindly retry, reverse or declare rollback |
|0009 succeeds but source/readiness/live acceptance fails | Close/retain maintenance; preserve post-attempt DB/env/keys/artifacts. Prefer bounded forward repair. Symlink back only to rehearsed-compatible prior app with0009 retained, then verify the same security/readiness gates before reopening |
| Old app compatibility not proven / preservation differs | Keep HMS closed and preserve evidence; obtain reviewed forward repair. Never remove guard/MFA/Basic, relax network policy or silently discard state |
| Usage stop during work | Coordinator checkpoints safely; if healthy verified baseline can be reopened without further implementation, record actual state; otherwise keep HMS closed with explicit recovery receipt. Follow owner's330minute rule and existing heartbeat; no duplicate automation/team |

Reverse0009 is not the deployment rollback plan. Its empty-table guard is not a concurrency lock; reversal requires independently reviewed quiescence and remains isolated evidence here. Never reverse0008/0007 to obtain rollback, delete limiter rows, restore a pre-MFA dump or overwrite newer audit/session/security history. Restoring a prechange DB is an exceptional separately reviewed recovery with preserved post-attempt state and explicit accepted-write disposition, not an automatic fallback. No forced Git push, shared configuration overwrite, global proxy/PG restart, docker prune or cleanup of unverified paths.

## Draft disposition

This author inspected repository plans and recorded operations evidence and wrote this design only. No code/dependency/migration/Git/VPS mutation, runtime test, authenticated usage check or live attestation was performed by this specialist. All execution checkboxes remain unchecked. The coordinator must review/freeze the bounded rollout against the actual final implementation and supply runtime evidence before marking any gate complete.

## Coordinator review disposition

Independent source reviewer accepted bounded deployment design and test-only timezone correction; root actual fullPG1320/168subtests passed with5explicitSQLite-onlyskips andone documented maintenance warning, check0/nodrift. Exact sourceCI, fresh existing-preview baseline/restore and final backup remain mandatory before live migration. Source/control/config/static scope stays frozen; no initial bootstrap or policy mutation.
