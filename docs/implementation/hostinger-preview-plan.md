# Hostinger controlled preview deployment plan

Owner explicitly authorised deployment of the existing slice to hms.praritsidana.com on23October2026 and waived the current cooldown for this deployment only. General future usage stops remain applicable. This is an incomplete authenticated preview using synthetic test records, not hospital production cutover.

## Boundaries and preflight

- Separate /opt/hms directory, dedicated hms-preview system user, hms-preview systemd service and Docker Compose project hms-preview. Never restart/replace other application stacks or global Nginx configuration.
- Existing Nginx routes only this hostname; HTTP ACME challenge followed by dedicated HTTPS server block. Syntax-test before graceful reload; retain pre-existing configuration checksum inventory for comparison.
- Build React static assets; use Gunicorn with loopback-only127.0.0.1:8185, two workers. Nginx replaces forwarded headers, Gunicorn trusts only loopback for HTTPS, backend trusts only loopback for client-IP resolution.
- Separate PostgreSQL17 container, private loopback127.0.0.1:5548, persisted data under /opt/hms/data. TLS with restricted private key; separate non-superuser application login; TLS required by Django. No existing database/schema reuse.
- Production-mode Django: DEBUG false, explicit host/origin/secret, secure session/CSRF cookies. Edge HTTP Basic authentication for this preview plus individual application session login. Same generated owner credentials may be used at both prompts; no credentials in Git/logs. Login rate limited at shared Nginx edge. IP mode initially authenticated access; no automatic IP enrolment.
- No real patient/lead information. Dedicated preview organisation/branch, synthetic beds only, owner login with explicit master_admin+reception roles (no clinical signing). Store owner access instructions in ignored local file, root-only server bootstrap file.

## Execution and acceptance

- [x] Authenticated SSH and read-only inventory: existing Docker/Nginx apps present; proposed folder/ports free; domain A points at VPS; existing Nginx syntax passes.
- [x] Write/run tests for >100-bed admission selector before fix; review proxy/auth/DB deployment threats and failure scenarios before runtime changes.
- [x] Prepare dedicated tracked service/proxy/Compose/bootstrap templates and dependencies; archive only tracked/nonignored source, never local DB or credentials.
- [x] Create dedicated directories/user/DB; actual PostgreSQL48tests/25subtests passed before handoff (loopback backend activated before this validation, preview restricted by outer gate).
- [x] Install built frontend, create explicit synthetic preview owner context, migrate; configure HTTPS certificate with webroot-only ACME, no edits to unrelated sites.
- [ ] Verify HTTP redirect, TLS, outer authentication, session/CSRF success/failure, protected API denial, headers, forged forwarded headers, process/socket isolation, app login/browser journey, initial backup+restore smoke and existing sites/config preservation.
- [ ] Record exact evidence/remaining limits in HMS.md/plan.md/ledger; commit/push and verify SHA; preserve rollback instructions.

HTTPS/API/session/CSRF/cookie/throttle/isolation/restore checks passed; original Nginx files unchanged. Authenticated browser walkthrough remains unchecked because automation cannot handle the Basic prompt. Exact corrections/evidence/remaining limits are in the ledger and operations runbook. Reviewer found no Critical/Important blocker for restricted synthetic preview, not whole-product approval. Publication SHA is reported at handoff.

## Failure and rollback

Stop on name/port/path collision, DNS mismatch, unhealthy database, failed tests or Nginx syntax error. Leave current sites running. Before publishing keep new hostname unavailable rather than expose a development server. Rollback disables only hms-preview site and service, tests/reloads Nginx, and preserves its database/secrets/source for recovery. No destructive cleanup or existing-app upgrades.

## References

Gunicorn trusted proxy configuration: https://gunicorn.org/reference/settings/ . PostgreSQL TLS/key permissions: https://www.postgresql.org/docs/current/ssl-tcp.html . These references informed the implementation; runtime checks remain required.
