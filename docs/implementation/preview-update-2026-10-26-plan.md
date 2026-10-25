# Restricted preview update implementation plan — 26 October 2026

> **For agentic workers:** coordinator executes this operational plan using executing-plans; independent specialists review disjoint facts. Coordinator alone changes Git/VPS. **COORDINATOR APPROVED FOR GATED EXECUTION — coordinator accepted the bounded design and selected socket model; runtime gates remain pending.** No checkbox below is deployment evidence.

**Goal:** update the existing synthetic, Basic-protected preview at `https://hms.praritsidana.com` from recorded runtime `47b3618` to published checkpoint `3634a98` (application source `66bfa10160eae5342b0b64a601ad05b992d40753`), with implemented API/session/MFA/network capabilities, preserving other VPS apps.

**Architecture:** retain `/opt/hms`, its dedicated database, existing two-worker loopback Gunicorn and shared Nginx. Add the reviewed network auth_request and private Unix static upstream; intersect durable policy with unchanged approved environment policy. Use a maintenance interval for backed-up migration and a coherent backend/static/config switch.

**Tech stack:** Python3.12/Django5.2.18/Gunicorn26.2.0, PostgreSQL17.11 TLS, existing Nginx auth_request/SSL, built React. Install only reviewed candidate-pinned dependencies in a separate immutable candidate venv; no live/shared venv upgrade, paid provisioning or whole-hospital release.

**Spec:** `hostinger-preview-plan.md`, `network-access-contract.md` (especially §10/OOB/StageE), `network-acceptance-2026-10-24.md`, `network-edge-validation-plan.md`, `HMS.md`, `plan.md`, ledger and latest owner instruction.

## Global constraints and known facts

- Owner authorised the latest implemented code rollout and requires verified push → reviewed/tested preview deployment → live verification → MD records. Documentation-only checkpoints do not restart an unchanged app.
- Resume was supplied by coordinator at `2026-10-25T22:00:14Z`, primary99%/weekly53% remaining. Coordinator checks usage at bounded boundaries; future fresh≤10% stops require checkpoint+330minutes.
- Root read-only inventory at approximately22:01UTC reports `/opt/hms/current` → `/opt/hms/releases/preview-20261023`, active `hms-preview`, old dedicated Basic/static/API site and no `/opt/hms/run`. Installed venv has Django5.2.18/Gunicorn26.2.0.
- Further coordinator inventory confirms global worker UID/group `www-data`; `/opt/hms`, static and logs root-owned0755; secrets root:www-data0710 and app.env root0600. Preview DB has only core0001 applied; one organisation `2c3f0af0-0655-4dc4-b7be-ffb3e27c627d`, intended master user1. Coordinator reports exact checkpoint3634a98 CI all three jobs green,1276PostgreSQL/132frontend tests; full SHA/run provenance belongs in final coordinator evidence.
- Candidate requires pinned PyOTP/cryptography absent from live venv. Provision `/opt/hms/releases/venv-20261026` after collision check from reviewed requirements, root-owned and nonwritable by app workers. An existing validation venv can be copied only after dependency/hash/ownership verification; never symlink a writable test venv or mutate `/opt/hms/venv`. HMS service ExecStart and ReadOnlyPaths must point to the frozen candidate venv together; retain old unit/venv for rollback.
- Coordinator accepts exact unchanged source CI1276PostgreSQL/all three jobs green and reports new local frontend build24modules/1.41seconds. These are source/build evidence, not deployed acceptance. Logical deadline fallback needs no scheduled worker; evaluation selects fallback at expiry independently of reconciliation.
- Existing app.env has environment/secret/host/origin/DB/trusted-proxy/IP mode settings; no MFA keyring, security owner or probe peers. Do not copy source into service before preparing these.
- All deployment identifiers, target SHA, baseline migration state, worker UID/GID, config hashes, available disk/RAM and backup/restore results must be captured from actual inventory. Historical documentation is not fresh runtime attestation.
- Existing Basic credentials, Django secret, database credentials/TLS, user memberships and current approved network ceiling remain private and preserved. No real patient/lead data; no arbitrary policy/role creation, silent clinical privilege, shared HBA/firewall edits or other-app restarts.
- New document tables are dormant source foundation; no document upload/ready/download/scanner/storage/API is delivered. B2a metadata admission remains DRAFT and is excluded.

## Review focus

1. A missing singleton/keyring/probe peer makes new enforcement unavailable: migrate/bootstrap/configure before exposing candidate, prove failure remains closed.
2. Mixed old/new workers or static bundles can bypass intended semantics: maintenance gates all public HMS routes during switch; verify exact new worker generation and release assets.
3. Shared Nginx workers need private socket traversal/connect rights: prove real identities and effective path permissions through reload/recreation, without changing shared worker identity.
4. Backing out after new security events cannot safely use reverse migrations or discard history: first fail closed, preserve post-change database, restore only under the explicit no-write rollback window.
5. Owner MFA enrollment has sensitive one-time outputs and session rotation: retain privately, verify recovery path and fresh sessions, never weaken MFA to make smoke tests pass.

## Task 1 — bind inventory, candidate and review evidence

**Files/resources:** read-only actual service, `/etc/nginx/sites-available/hms-preview`, enabled symlink, `/opt/hms/current`, static files, app.env key names only, database migration/table counts, dedicated backup unit/timer and external existing-site baseline. Source references: `infra/hostinger/{nginx.conf,proxy.conf,hms-preview.service,compose.yaml,backup.sh}`, `infra/edge/*.conf`.

- [ ] Confirm authenticated usage guard permits work; no existing conflicting deployment/team.
- [ ] Pin full target Git SHA and remote equality; inspect exact CI results for target. Record app-source SHA separately. Require expected source tree/archive digest, not an assumed short SHA.
- [ ] Record current release target, app/static/config/service hashes, DB migration leaves/counts, current worker identities/listeners, TLS/role restrictions, disk/RAM and other-app status/config hashes. Inspect only environment key names/nonsecret descriptors; do not print values.
- [ ] Reconcile candidate dependencies with installed venv. Build frontend and run candidate root/docs/edge checks, typecheck/build/frontend tests and actual PostgreSQL app suite using isolated DB only. Existing exact CI can substantiate unchanged source; record what was actually rerun separately.
- [ ] Review new candidate settings/migrations/edge/service behavior against scenario, permission and threat lists. Record reviewer disposition before mutations. Any new infra code/config behavior needs exact contract and executable RED→GREEN before implementation.

**Pass:** exact source and installed capabilities known; backup capacity present; host/port/path collisions absent; no unresolved Important/Critical rollout finding. Do not rerun first-install `prepare_host.py` against existing `/opt/hms`.

## Task 2 — freeze private socket and edge worker contract

**Selected minimal design for review:** use the existing root Nginx master and existing inspected worker identity (expected `www-data`), with the tracked sibling Unix static server. No extra service, user/group changes, global umask, module installation or shared Nginx restart is needed.

- [ ] Confirm the actual worker identity/group matches the selected group; otherwise stop and re-review exact rights.
- [ ] Root creates `/opt/hms/run` as a fresh real directory, root-owned0700 while staging. Refuse symlink/unowned existing content. Static root contains only built frontend files, no secrets/config/repo.
- [ ] Render HMS-only source includes with fixed socket `/opt/hms/run/edge-static.sock`, backend `127.0.0.1:8185` and actual hostname. Preserve all existing security headers and Basic. Outer public static locations proxy through Basic AND auth_request, no direct try_files; sibling static is UDS-only with only Host/Range forwarded. External probe remains404; ordinary API strips marker and alternate forwarded headers.
- [ ] Before opening preview, require socket owner root, group inspected Nginx worker group, mode0660, and parent root:same-group0750. Root alone can replace/chmod parent. Check real worker can connect; nonmember OS user cannot traverse/connect. No TCP static listener.
- [ ] Prove lifecycle in isolated root-master/`user www-data` configuration: initial start, graceful reload, stopped/recreated socket and recovery. At each stage actual www-data request must200 and `nobody` must fail traversal/connect; no new TCP listener/global restart. Parent remains root:www-data0750; record actual socket mode each time. A recreated socket may have broader inode mode under Nginx; the durable security invariant is **effective reachable principals limited to root and the existing Nginx group by the root-owned non-world-traversable parent**. Record0660 at rollout completion and after controlled reload. Coordinator selected this effective-principal model; no additional daemon/source change is needed if lifecycle evidence passes.
- [ ] Review explicitly: other applications running as the same shared Nginx UID/group are inside this existing OS trust boundary. This is no independent per-app UID security isolation. Root/Docker/admin compromise is out of scope; HTTP access remains guarded independently.
- [ ] Syntax-test isolated rendered config and actual same-worker HTTP guard/no304/range/HEAD/header/fault matrix before global reload. Use existing edge harness principles, never report its root-only0600 result as worker evidence. Do not restart global Nginx to test recreation.

**Pass:** actual worker/private path lifecycle and no direct-static bypass proven. If candidate socket guard fails after installation, maintenance stays closed; never solve by world-traversable parent or removing auth_request.

## Task 3 — backup, restore rehearsal and immutable staging

**Resources:** unique `/opt/hms/releases/preview-20261026-<target-shortsha>`, staged frontend directory, private deployment receipt and rollback copies under `/opt/hms`; dedicated backup directory. Coordinator freezes exact unique names after collision check.

- [ ] Stage only committed archive plus built frontend; verify archive/build hashes, ownership/read permissions and no credentials. Do not overwrite current release, live static or installed venv.
- [ ] Copy current HMS site/includes/service/env and release/static target metadata to root-only rollback storage; preserve secret copies privately, never in Git. Record SHA256 of nonsecret artifacts and encrypted/private retention location of key material.
- [ ] Run existing dedicated `backup.sh`/service, verify dump nonempty, checksum and `pg_restore --list`. Coordinator selected the existing label/receipt-verified ephemeral PostgreSQL helper at fixedloopback15549 for restore rehearsal, with no shared HBA change. Restore through its reviewed app/admin boundary into its exact owned DB; verify baseline counts/migrations, run candidate migrations/check and owner-bind/operator dry fixture there. Preserve lifecycle receipt and clean up only helper-owned resources by verified IDs/labels. No app CREATEDB left enabled. The edge HTTP runner requires an empty DB and must not be invoked against the populated restored DB; fresh lifecycle is required for that separate matrix.
- [ ] Inspect actual `showmigrations` and `migrate --plan`. Expected new graph ends at core0008: staff/idempotency/config/identity/audit-index/network/dormant-document migrations as applicable; do not assume baseline has only0001 or rerun seed_demo against existing data.
- [ ] Record a tested restore command/role/TLS connection path using private input and exact database identity. Backup must cover data, old source/static/config, Django secret and new MFA keys; DB-only restore cannot decrypt MFA without matching keys.

**Pass:** isolated restore and upgrade rehearsal actually succeed; restore can recover old baseline without touching other DBs. Existing old smoke script assumes password-only semantics; do not blindly run it after MFA activation.

## Task 4 — private identity/network configuration and maintenance migration

**Interfaces:** candidate `settings.py`; `manage.py network_policy inspect|bind-owner|recover|reconcile`; `manage.py network_operator grant|revoke`; existing Account security HTTP contracts. No fabricated HTTP superuser or direct DB operator grant.

- [ ] Identify existing preview organisation UUID and active intended owner's explicit master_admin membership/user ID. Owner context is explicit, never first-row/default discovery. Freeze these IDs privately in deployment receipt. No new clinical permissions.
- [ ] Create one cryptographically generated Fernet key privately for `HMS_MFA_ENCRYPTION_KEYS` only if no existing keyring/enrollments exist; preserve any existing decrypting keys/ordering. Set `HMS_REQUIRE_ADMIN_MFA=1`, `HMS_SECURITY_ORGANISATION_ID=<existing owner UUID>`, `HMS_NETWORK_PROBE_PEERS=127.0.0.1`, `HMS_TRUSTED_PROXIES=127.0.0.1/32` (reconcile equivalent current canonical setting). Preserve exact approved environment allow/block policy and host/origin/secret/DB TLS; no visitor IP auto-enrollment. All workers consume same env fingerprint.
- [ ] Keep verified OS/SSH recovery available before applying full edge enforcement. Binding and operator provisioning do not bypass environment denial; OOB cannot repair a wrong environment ceiling automatically.
- [ ] Put only HMS public HTTPS routes into reviewed maintenance denial, including shell/assets/API/probe; ACME remains as previously scoped. Syntax-test and graceful reload; verify closed externally. Stop only hms-preview; verify no old workers remain and freeze synthetic writes. Record maintenance UTC and final pre-migration backup.
- [ ] Run candidate `migrate --noinput` through dedicated app environment against exact preview DB, then `check`/migration drift check. No reverse-migration shortcut. Inspect singleton1: migration0007 starts revision1, unbound owner, unrestricted overlay and no pending; it never relaxes environment ceiling. If already populated, preserve state and inspect rather than reset.
- [ ] Run `network_policy inspect --os-actor <auditable-label> --reason <10..500 printable reason>`. If unbound pristine state, `bind-owner --organisation <UUID> --expected-revision <observed> --os-actor ... --reason ...` is an immediate audited mutation (NO --apply flag). Then inspect again.
- [ ] Explicitly grant intended existing master with `network_operator grant --organisation <UUID> --user-id <ID> --expected-version <observed,0 only if absent> --expected-revision <observed> --os-actor ... --reason ...`. Grant changes entitlement version, not singleton revision; reread actual results rather than assume increments. Never repeat commands blindly.
- [ ] Start new backend with coherent release/env; verify two new workers and direct trusted-loopback probe204/empty/no-store, invalid context404, anonymous API/auth semantics and secure scheme. Unavailable state must503; private management requires MFA even if initial user has not enrolled.

**Pass:** migration graph, keyring, owner/operator ceiling and probe work with identical worker environment; no pending policy; old workers absent. Do not populate new document tables or introduce unimplemented metadata capabilities.

## Task 5 — coherent switch and live acceptance

- [ ] Switch release and frontend targets coherently while public HMS remains in maintenance; install only reviewed HMS site/includes. Verify current/static targets and candidate worker source, `nginx -t`, socket rights and private probes before removing maintenance. Graceful reload only; retain previous artifact copies.
- [ ] External no-Basic requests deny; valid Basic plus allowed policy reaches app login; wrong Basic still denies. HTTP redirect/TLS/security/no-store headers persist; private check/probe public paths404. Verify shell/index/nested SPA/assets, missing assets, HEAD/range and wildcard/combined conditional headers never304 or leaked body on denied access.
- [ ] Prove forged XFF/Forwarded/marker/cookies cannot change client IP/context. Backend8185, DB5548 and Unix static transport remain externally unavailable; actual outside-client probes plus listener/path inspection recorded. No shared config/HBA change.
- [ ] Use existing Account security API/UI to enroll the preview owner, verify TOTP and recovery codes privately, then new password+factor session login and fresh step-up. Keep one-time enrollment secret/recovery codes only in private owner handoff; never logs/screenshots/Git. No disabling MFA or direct ciphertext fixture provisioning to avoid the live flow.
- [ ] Verify missing session, missing CSRF, stale/missing MFA, ordinary staff and master-without-operator denials. Owner+explicit operator+fresh MFA can read/preview; current-user capability and Network access navigation agree. Preserve CSRF unchanged.
- [ ] Synthetic browser walkthrough: login/factor, Account security, reception search/register/detail and appointment/bed flow supported by implemented contracts; Network access current-IP draft is no-write, preview/apply/keep, history and keyboard/error steps. Use safe equivalent/unrestricted overlay or explicit approved bounded test rules; never invent owner allowlist. Prove apply→restore and fixed fallback without deliberate owner lockout; reconcile/terminalise pending test state and record final effective policy/revision.
- [ ] On live preview only, use bounded safe failure checks that do not alter global DB/proxy or unrelated apps. Destructive stop/timeout/DB-outage cases remain isolated candidate evidence unless coordinator freezes a brief maintenance fault test. Verify worker recovery and no stale allow/fallback-to-HTML.
- [ ] Verify dedicated backup timer/service after source switch and create post-migration dump/checksum. Recheck other-app status/config hashes and resource/listener inventory. Record any browser/staff limitations honestly; synthetic browser is not real-staff/hospital acceptance.

**Pass:** implemented capabilities usable within restricted synthetic preview, with final no-pending state, no security bypass and other apps preserved. Whole HMS, real patients, off-host encrypted recovery, clinical/financial/MCP/file delivery and production release remain open.

## Failure and rollback contract

1. On migration/config/probe/socket/identity/acceptance failure, close HMS with reviewed maintenance denial first; syntax-test/gracefully reload only as needed. Stop only candidate hms-preview if required. Keep SSH and other sites running. Operational default is failclosed HMS-only, with no old-code policy bypass. Never restore old direct-static/no-durable-guard exposure as a way to make a failed new security check appear healthy.
2. Before any rollback, preserve post-attempt DB dump plus current keyring, env/config/release identities and failure evidence. No silent history deletion; do not run0007 reverse after bind/operator/history exists or0008 reverse after document rows exist.
3. During the declared no-user-write maintenance migration window only, verified pre-change DB restore plus exact matching old source/static/env/site can recover the old restricted preview baseline. Coordinator verifies absence of accepted writes; otherwise the default is closed preview and forward repair. The rollback acceptance is the old preview's explicit limited security scope, not completed new network/MFA delivery; reviewer must approve reopening it.
4. If any new synthetic writes/security events/MFA enrollment have occurred, retain them and prefer forward repair/closed preview. Restoring pre-change DB would discard them and requires explicit owner disposition, preserved post-change dump and matching credential/key handling. An old source with a newer migrated DB is not assumed compatible merely because migrations are additive; rehearse before choosing it.
5. OOB policy recovery uses only an existing immutable change and selected candidate/fallback with observed revision: `network_policy recover --change <UUID> --snapshot fallback --expected-revision <N> --os-actor ... --reason ...` is dry-run; repeat with `--apply` only after review. It never bypasses environment policy or repairs DB corruption. No arbitrary SQL emergency policy rewrite.
6. Keep old releases/backups/private recovery materials. Cleanup only exact owned staged resources after verified success; no docker prune, shared PG stop/HBA edit, global proxy restart or recursive deletion outside verified HMS paths.

## Task 6 — evidence, publication and status

- [ ] Coordinator records exact source/runtime SHA/archive hash, maintenance/switch times, migrations, config descriptors, worker/socket identity, keyring custody (no secrets), owner/operator audit outcomes, final revision/policy/no pending, external/live/browser/backup results and other-app preservation.
- [ ] Update `HMS.md`, `plan.md`, ledger and operations runbook together; distinguish planned/implemented/source-tested/live-verified/deployed. Retain historical47b3618 evidence and explicit remaining limits. Correct stale runbook claims that MFA/IP administration are entirely planned only where actual deployment evidence exists.
- [ ] Run `python scripts/check_project_docs.py`, relevant root documentation tests and whitespace/secrets/diff review. Coordinator alone commits/pushes, verifies remote full SHA and observes exact CI. If code/config source changed, pin that final application source and deploy/verify it under the same owner rule; documentation-only evidence commit does not restart unchanged runtime.

## Blocking inputs and coordinator review rulings

- Exact full target/remote/CI provenance and table counts remain evidence inputs. Coordinator reports source3634a98 green and baseline core0001; reconcile full identifiers before execution.
- Global worker identity and effective-principal model are coordinator-selected as above; isolated same-identity socket lifecycle proof remains mandatory before installation. If it fails, re-review rather than ad-hoc permissions.
- Owner UUID/user ID are bound from inventory above; no existing policy/identity tables exist at core0001. Confirm no concurrent migration before Task4, bind new state through supported commands and preserve current environment ceiling/private recovery custody. No new owner setting decision is required.
- Browser/TOTP/private handoff availability may require owner participation for their own authenticator. Complete candidate/security/migration preparation first; never treat unavailable human enrollment as permission to disable MFA. A clearly recorded closed/staged deployment is preferable to an unverifiable live login.

**Coordinator review:** root accepted this bounded plan, shared root-master/www-data private-parent invariant, separate candidate venv and failclosed HMS-only rollback. Before live maintenance, coordinator will run backup/restore/candidate migrations/control/owner-operator fixtures through the verified ephemeral helper and isolated actual-worker socket lifecycle. Acceptance is design approval; none of those runtime gates is marked run or passed here.

**Authoring evidence:** repository source/contracts were inspected and coordinator inventory/rulings incorporated; no VPS/Git/dependency/product-source mutations or runtime tests were performed by this drafting specialist. Documentation checker and whitespace check passed. READY FOR COORDINATOR EXECUTION REVIEW; remaining runtime gates and final operational evidence belong to coordinator.

## Coordinator execution ruling —26 October2026

Accepted bounded source/security review and this operational plan. Exact source3634a98 CI40230849210 all3jobs verified; existing single previeworg2c3f0af0-0655-4dc4-b7be-ffb3e27c627d/master1/core0001 bound by read-only inventory. No new worker is required: deadline fallback is intrinsic. Isolated root-master/www-data lifecycle actually passed10checks: unsafe0755 parent admitted nobody, root:www-data0750 denied nobody while www-data worked through fresh/reload/recreated socket; recreated socket0666 remained protected by parent; final0660 accepted. No TCP/globalNginx change. This resolves worker permission design gate, explicitly retaining shared www-data OS trust. Candidate restore/migration/config/edge acceptance and backup gates must pass BEFORE live switch. Root selected real static directories (no symlink at static root with disable_symlinks), separate release venv and failclosed default rollback. Further production code changes require fresh scoped design/RED/review; this approval covers deploying existing code/templates only.

## Actual execution disposition —26 October2026

Tasks1–4 candidate/inventory/socket/restore/configuration and maintenance migration/bootstrap executed and verified; source unchanged and CI exact3634a98, runtime release522f00d. Task5 HTTPS/API/MFA/CSRF/static/network equivalent confirm/revert/history/logout and external-origin checks passed;48other configuration hashes/18container IDs preserved, post-change backup/key restore passed. All livebrowser/keyboard/representative staff/authenticator-import checks stay open. Destructive runtime faults/deadline/denied-network matrix is actual isolated evidence only. Task6 evidence is saved; final docs push/remoteSHA and new CI are publication steps, not already assumed passed. See redacted operations evidence. Checkboxes remain detailed acceptance targets; this disposition, not a blanket all-box tick, records actual scope.
