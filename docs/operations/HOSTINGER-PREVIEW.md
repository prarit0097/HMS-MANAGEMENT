# Hostinger HMS preview

Status: deployed authenticated preview on23October2026; no hospital production cutover. URL: https://hms.praritsidana.com . Owner authorised this environment and expressly waived the active usage cooldown for deployment only.

## Access and scope

Use the generated owner details from the ignored local access file supplied in the coordinator handoff. The browser security prompt and HMS login use those same initial details. Root-only recovery copy: `/opt/hms/secrets/owner-access.json`. Never place passwords in GitHub, screenshots, command arguments, issue text or chat. The browser automation available in this session could not handle the HTTP Basic prompt; actual HTTPS/session/API checks passed through the verification script, but no authenticated live browser walkthrough is claimed.

This version contains login, dashboard, patient registration/search/detail, appointments/check-in, pageable bed listing/admission selection and nonclinical master summary. Other portals remain unavailable. UI prominently says INITIAL PREVIEW and synthetic data only. Initial owner has explicit master_admin and reception memberships, no clinical signing. The preview database initially has120synthetic beds, zero patients. Do not enter real hospital data until the remaining release gates are completed.

## Isolation and runtime

| Resource | Dedicated HMS value |
|---|---|
| Root/source | `/opt/hms`, `/opt/hms/releases/preview-20261023`, `/opt/hms/current` symlink |
| User/service | `hms-preview`, `hms-preview.service` |
| Backend | Python3.12 virtualenv `/opt/hms/venv`, Gunicorn26.2.0, two workers, loopback127.0.0.1:8185 |
| Static app | `/opt/hms/static`, React production build; no Vite/runserver exposure |
| Database | Compose project `hms-preview`, `postgres:17.11-bookworm`, loopback127.0.0.1:5548, `/opt/hms/data/postgres` |
| Database roles | Private container admin; hms_app is not superuser and has no CREATEDB after test runs |
| Database TLS | Server key owner999 mode0600; hostnossl rejects; Django sslmode=require; private self-signed DB certificate (transport encrypted, CA/hostname identity verification not yet enabled) |
| Nginx | Only `/etc/nginx/sites-available/hms-preview` + matching enabled symlink added; existing files unchanged |
| HTTPS | Let's Encrypt certificate expires21January2027, active certbot timer and hostname-conditional reload hook |
| Secrets | Root-owned `/opt/hms/secrets` and mode0600 env/access files; only htpasswd readable by www-data group |
| Backup | `/opt/hms/backups`, root-only dumps + SHA256; dedicated daily timer02:15UTC, retention/manual capacity review required |

The VPS OS, Docker engine and Nginx remain shared host dependencies. This is process/database/config isolation, not a separate VM security boundary. No existing application stack was restarted. All pre-existing Nginx file checksums remained unchanged; Nginx was syntax-checked and gracefully reloaded to add this host. Other checked domains returned200 or their existing redirect.

Nginx replaces X-Forwarded-For/Proto, clears alternative forwarded headers and inbound Authorization before proxying. Gunicorn trusts only loopback to establish HTTPS `wsgi.url_scheme`; Django does not globally trust arbitrary forwarded scheme headers. App trust for client-IP policy is loopback-only. Unique shared Nginx login rate zone uses actual peer IP. IP mode initially permits authenticated users from any network; configurable environment allow/block lists exist, master-admin IP editing/recovery UI is still planned. This is not a completed IP administration product.

## Verified evidence

- Backend on actual TLS PostgreSQL:48passed,25subtests, zero skipped/warnings on final run. Concurrent two-patient/same-bed allocation passes. Temporary app CREATEDB privilege revoked; isolated test database removed. First run warned about maintenance database access; explicit empty postgres maintenance database connection resolved teardown warning, then full suite reran clean.
- Remote frontend:11tests and production typecheck/build passed; regression selects a bed past100 via paged choices. Each picker page25; backend remains allocation authority. No API/schema migration change for this fix.
- `verify_preview.py`: outer authentication, HTTPS static content/security headers, anonymous API denial, no repository file serving, CSRF missing-token denial, application sign-in/logout, secure HttpOnly SameSite session cookie,120bed pagination/branch denial, shared edge login throttling despite forged IP variation passed.
- HTTP301 to HTTPS; HTTPS401 without preview credentials is intentional. Windows external socket checks could not reach backend8185 or database5548; both server listeners are127.0.0.1.
- Actual application connection reported TLS=true; application role superuser=false/createdb=false. Explicit nonTLS PostgreSQL connection was rejected. Root documentation/usage-guard suite19tests passed; source/API-map/local-link checker passed.
- Initial database dump checksum verified; restored to separate hms_restore_check,120beds/zero patients confirmed, disposable restore DB removed. Daily backup timer enabled. This is a database restore smoke, not full encrypted off-host recovery or portal-scoped restore.
- Nginx syntax passed and all original configuration checksums passed. Checked pdf.praritsidana.com/postzyo.com/riimshospitals.com/rezoom.praritsidana.com returned200, nirogidhara.com307.

## Operations and rollback

Templates and runtime smoke script: [Hostinger infrastructure](../../infra/hostinger/). First-install `prepare_host.py` refuses an existing destination/user; review free ports, host packages and TLS image UID before using on another host. Source upload/install/ACME steps performed by coordinator are summarised here, not a blind one-command installer.

Linux deployment templates/shell scripts use enforced LF line endings through .gitattributes; release source is published from the committed Git archive, excluding all ignored runtime/credential files.

```sh
systemctl status hms-preview --no-pager
journalctl -u hms-preview -n 50 --no-pager
docker compose -p hms-preview -f /opt/hms/current/infra/hostinger/compose.yaml ps
systemctl list-timers --all hms-preview-backup.timer
systemctl start hms-preview-backup.service
python3 /opt/hms/current/infra/hostinger/verify_preview.py
```

The smoke script intentionally consumes login rate budget. Do not repeatedly run it during an owner login. It reads private credentials locally and prints only assertions. Owner account management/MFA is unfinished; administrative credential rotation must update app and edge deliberately, with no shared/default password in source.

Rollback to unavailable preview without affecting other sites: stop only hms-preview.service, unlink only `/etc/nginx/sites-enabled/hms-preview`, run `nginx -t`, then reload nginx if valid. Preserve all `/opt/hms` data/secrets/releases/backups. Do not run Docker prune, stop the global proxy, or delete database volumes. Certificate/backup timers are dedicated; disable only their HMS-specific schedule if preview is retired.

Remaining gates: authenticated live browser/staff walkthrough, broader independent security review, MFA, sensitive-read audit/monitoring, distributed application abuse controls beyond the shared edge, clinical/financial workflows, idempotency and exclusive allocation rules, encrypted off-host backups and full recovery drills, load testing and hospital cutover approval. General development cooldown deadline remains governed by USAGE-CHECKPOINT.md after the authorised deployment exception completes.
