# SDD ledger — plan: plan.md

## Reception reliability source delivered —23October2026

- Frozen contract and OpenAPI preceded code; backend33-case RED24failed/9passed, then error-array3failed, nested-error RED, and final37reliability cases GREEN. Backend local84passed/2PG-only skips; check/drift passed. Coordinator actual PostgreSQL pre-review86passed/25subtests; no production schema changed.
- Frontend5principal regressions RED, then20tests/typecheck/build GREEN: correction PATCH, versioned reschedule/conflict, patient pagination, globally filtered bed choices, stable UUID retry across three create forms. No secrets/payload in localStorage. Input length160aligned with backend during final root pass. Windows mixed encoding/line-ending edits repaired before final build; no source encoding claims without successful build.
- Fresh independent reviewer inspected foundation and slice with26isolated in-memory API probes. Two Important findings: nonobject JSON assumptions500 and keyed unexpected file causing fingerprint TypeError500. No auth/branch bypass found; one Minor frontend160/200mismatch. Declined full hospital/deployment/staff acceptance; those remain gates, no implied approval.
- Final: fixed both Important findings — tests/test_object_payloads.py37cases RED27failed/10passed; object guards, validation before fingerprint and patient-PATCH guard correction; targeted74passed. Root final actual PostgreSQL123passed/25subtests/0skips/0warnings in8.60s, migration drift clean, test DB removed/CREATEDB revoked. Final frontend20passed/typecheck/build, OpenAPI validator and source/map/link/whitespace checks passed. Bounded reviewer findings resolved, no re-review invented.
- Data: core0002IdempotencyRecord (actor+operation+UUID unique, SHA256 fingerprint/result UUID; no request/response PII); not applied to deployed preview. Replays reauthorise current scope, errors rollback claim; no expiry/legacy missing-key guarantee. Ruling: preserve optional-header compatibility and existing unversioned demographic writes, document residual duplication/lost-update risk; cost if unsuitable is later API/client migration, not hidden clinical signing safety.
- Existing Hostinger preview remains47b3618; candidate tests ran in separate /opt/hms/validation/reception-20261023 against temporary test_hms_preview only. No service redeploy/migration/real data cutover in this source slice. Next reviewed slice: scoped staff/branch/resource administration and security identity/MFA design before clinical workflows; full plan remains owner-authorised.

## General development resumed by owner —23October2026

- Latest owner explicitly requests further work now and cooldown adjustment. Authenticated primary76%remaining/weekly51%remaining at09:12:37Z, so minimum51% permits work. Old05:02checkpoint/10:32deadline archived and explicitly waived by owner; no reset credit; future <=10% creates fresh330minute deadline. Current local guard returns continue; existing heartbeat updated in place.
- Ruling: owner-resume instruction supersedes earlier deployment-only exception and saved deadline; cost if misread is lost cooldown protection, so both usage windows verified before any work. Generic future threshold rule unchanged.
- Active exact contract reception-reliability-contract.md; OpenAPI extensions precede code. Backend/frontend assigned exclusive ownership and RED-first tests; third specialist inspects actualGitHubCI. No duplicate still-running team; agent list initially root only.
- Ruling: optional create key preserves API clients while current frontend adopts stable logical-form keys; legacy missing-key callers retain duplicate risk. Fingerprint/result-only ledger, current scoped replay checks. Cost: cannot claim universal idempotentcreates until policy changes; no clinical/financial protection implied.
- Current source planning not delivery: deployed restricted preview remains47b3618. Full product/release gates remain open.

## Owner-authorised Hostinger preview — 23October2026

- Owner authorised isolated current-slice deployment and explicitly waived current cooldown for deployment only; general development deadline/future usage rule unchanged, no reset credit. Minimum52%remaining at bounded deployment check.
- Existing local SSH key succeeded; no root password requested/logged. Free /opt/hms/ports8185,5548, DNS, Docker/Nginx and valid original configuration established before mutation. Plan/threat review in hostinger-preview-plan.md. Frontend specialist >100-bed RED->GREEN; independent source reviewer found no Critical/Important blocker for restricted synthetic preview, not hospital release approval.
- Deployed /opt/hms, hms-preview user/service, static React/Nginx, loopback Gunicorn26.2.0, isolated TLS PostgreSQL17.11/hms_app non-superuser/NOCREATEDB, dedicated vhost/HTTPS/renewal hook/daily02:15UTC backup. Owner credentials generated/private, never inGit;120synthetic beds, initially0patients. No other application stack restarted; all original Nginx file checksums unchanged.
- Runtime corrections: package registry exposes Gunicorn26.2.0 rather than docs-mentioned26.2.2; explicit traversal modes corrected restrictive umask while retaining secret0600; TLS startup interruption required completing isolated new DB initialisation, no data deletion; custom hba rejects nonTLS; disabled optional Gunicorn control socket in read-only service. First pytest maintenance-db fallback/teardown warning fixed with empty postgres maintenance-db connectivity, then full suite reran clean.
- Actual final PostgreSQL48passed/25subtests/0skips/0warnings, including same-bed concurrency; temporary CREATEDB revoked/testDB removed. Production check --deploy/migrations passed; VPS frontend11passed/typecheck/build.7HTTPS smoke assertion groups passed for outer gate/static/headers, API anonymity/repository exposure, session/cookies/CSRF/logout, bed101+/branch denial and shared rate limit despite forgedXFF. Initial urllib harness lacked browser Origin and received expected403; corrected Origin and reran successfully.
- Initial backup checksum/restore to separateDB confirmed120beds/0patients; disposable restoreDB removed. Root-only plaintext local backups, no encrypted offsite recovery claim. DB sslmode=require encrypts but does not pin identity. Same password at edge/app is notMFA. Both8185/5548 listenersloopback; external Windows probes unreachable; HTTP301/unauthHTTPS401 intended.
- Other domains checked200(pdf/postzyo/riimshospitals/rezoom),307(nirogidhara); no comparison of prior HTTP contents claimed. Browser automation cannot handle HTTP Basic prompt (ERR_INVALID_AUTH_CREDENTIALS), so live authenticated browser/staff acceptance remains incomplete. Owner receives private ignored local access-file link.
- Remaining full identity/read-audit/recovery/load/staff gates and remaining product; return to saved development cooldown after deployment exception. No duplicate team or repeated deployment on heartbeat.
- Final DB probe confirmed actual connectionTLS, app nosuper/NOCREATEDB and120beds; nonTLS connection denied. Root scripts19tests passed; docs/API-map/local-link check and whitespace check passed. Independent reviewer source findings/limits incorporated in operations runbook.

## Owner-authorised execution — 23 October 2026

- Branch: feat/hms-foundation; starting commit efb967ee2382396aeb1f4423981262f1bf18a259.
- Read HMS.md, plan.md, AGENTS.md; first bounded contract is phase-a-contract.md.
- Team: backend, frontend, security, platform/dataops/MCP, independent reviewer in batches; coordinator integrates/commits.
- Usage baseline: primary34% used (66% remaining), weekly35% used (65% remaining). No reset credit consumed.
- Native heartbeat created: continue-hms-after-usage-cooldown, active, 330-minute interval. Exact wake is best effort; checkpoint deadline prevents early resumption. PC/app must stay available.
- Ruling: shared current checkout on isolated feature branch; no new worktree without owner preference. No initial runtime baseline existed, so no application test pass is claimed.
- Preflight interface scan and rulings: docs/implementation/phase-a-contract.md.
- Remaining: implement/review/test Phase A, then continue subsequent planned slices until completion or usage stop.

## Completed bounded units

- Usage guard:8 subprocess behaviour tests RED->GREEN; root commit e4a25b3 pushed/remote verified. Native heartbeat active, no cooldown triggered at last48% minimum remaining.
- Security primitives:22 tests/25subtests rerun GREEN; module only, request/edge integration pending. Security engineer's integrated threat notes sent to backend: strict boolean config, frame header middleware, CSRF/login/branch isolation, proxy boundary. Full runtime initially404 while in progress; not a shipped pass.
- Platform-agent scripts tests observed in RED while their checker did not yet exist; kept out of the security-primitives commit. Do not mistake a shared in-progress test discovery for final integrated results.

## Usage stop / preserved Phase A — 23 October2026

- Native guard recorded6%remaining at2026-10-23T05:02:15.039512Z and earliest resume2026-10-23T10:32:15.039512Z. Stop messages sent to all active specialists; no new implementation after that boundary. Follow-up Continue at08:34Z found55%usage recovered; only checkpoint work performed because deadline remains active.
- Backend delivered session/CSRF/scoped APIs, models/migrations/seed, initial admission constraints. Agent final47passed1PGskip25subtests; check/migrate/no-drift passed. Local Django server session50029 was started on127.0.0.1:8000 with synthetic-only visual-review account; no credentials in Git.
- Frontend delivered login/dashboard/patients/appointments/beds/admission/master inventory. Agent8tests/typecheck/build passed; Vite session9514 started on127.0.0.1:5173. Browser synthetic login/dashboard succeeded; do not assume local process sessions survive a future app restart.
- Platform source delivered OpenAPI18operations/page map, CI, Compose/Dockerfiles and docchecker. Coordinator16root tests passed earlier; Docker/remoteCI unverified. Native MCP/backup implementations deferred, not faked.
- Fifth reviewer stopped promptly and reported Important: admission choices read first100beds only in frontend/src/pages.tsx. No full approval. Explicit device-local appointment input was not treated as a standalone blocker. No tests run by reviewer.
- First resume: regression >100beds -> fix pageable admission selection -> affected UI/API checks; finish independent review; inspect/repair actual GitHubCI/PostgreSQL; reconcile contract/UI parity and continue next planned slice.
- Ruling: checkpoint source is WIP on feature branch, not main/production. Preserve incomplete but recoverable work with honest evidence; do not make a security or capacity claim from code presence.
- Coordinator checkpoint rerun: backend47passed1PGskip25subtests (56.72s); frontend typecheck,8tests,build passed. Source/API-map/local-link checker passed. Targeted credential-pattern scan60files passed. No full runtime review, PostgreSQL race or container execution claim.
