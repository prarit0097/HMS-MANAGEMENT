# Isolated network edge validation

This is Stage D source validation, not production deployment. Read the [frozen plan](../implementation/network-edge-validation-plan.md) and [network contract §10](../implementation/network-access-contract.md#10-full-portal-edge-contract-and-probe-circularity). The coordinator runs the VPS commands; specialists do not SSH. Keep live Nginx, services, application environment, DB/schema and policy unchanged.

**Current D2 source: WIP, not deployable.** Eleven source/safety/ownership checks and both Python compilations pass. The earlier candidate failed at shared PostgreSQL HBA rejection before HTTP launch; its exact disposable DB/config were removed. Frozen D2 now supplies a dedicated TLS PostgreSQL container and guarded noncached Unix static proxy. Installed runtime/no304 acceptance remains pending. The runner deliberately reproduces old direct-static wildcard304 first, then keeps the strict no304 assertion for D2. Never install into the live preview or describe source checks as runtime verification.

## Prerequisites and private input

Coordinator verifies installed Nginx auth_request/SSL support, Docker>=28, reviewed local imageID, available memory and free loopback ports15549/18185/18186, reviews source, then transfers source only to `/opt/hms/validation/network-edge-source-20261024`. Web runtime directory `/opt/hms/validation/network-edge-20261024` and PG runtime `/opt/hms/validation/network-edge-pg-20261024` must not exist; existing resources require reviewed recovery, not blind deletion. Existing pinned Gunicorn26.2.0 stays only in `/opt/hms/validation/identity-20261023/venv`. Root-only `prepare_isolated_pg.py up` provisions the dedicated labelled container/network, TLS/app role/empty DB and writes private app config. It never touches shared HBA/PG data, pulls images or provisions paid resources. Never grant the web runner an admin connection.

Create a private root-owned mode0600 JSON file outside source with this schema. Values below are placeholders, not credentials:

```json
{
  "venv": "/opt/hms/validation/identity-20261023/venv",
  "database": {
    "NAME": "hms_edge_validation_20261024",
    "USER": "hms_edge_app",
    "PASSWORD": "PRIVATE_VALUE",
    "HOST": "127.0.0.1",
    "PORT": "15549",
    "OPTIONS": {"sslmode": "require"}
  }
}
```

The runner refuses extra keys, another DB/venv, non-TLS settings, populated public schema, wrong source path, existing runtime prefix or occupied candidate ports. It never installs packages, creates/drops a DB, kills unmanaged DB sessions, changes global Nginx, restarts services or edits shared config. Private DB password is passed via child environment, not CLI/URL/stdout. Generated Basic password goes to OpenSSL stdin, not arguments. No real patient/lead data is needed.

## Commands and evidence

Local supplementary checks:

```powershell
python -m unittest discover -s infra/edge/tests -p test_*.py -v
python -m py_compile infra/edge/tests/validate_isolated.py infra/edge/tests/prepare_isolated_pg.py
```

Coordinator-only candidate sequence after source review; only fixed resources in the frozen plan are mutable:

```sh
/opt/hms/validation/identity-20261023/venv/bin/python /opt/hms/validation/network-edge-source-20261024/infra/edge/tests/prepare_isolated_pg.py up
/opt/hms/validation/identity-20261023/venv/bin/python /opt/hms/validation/network-edge-source-20261024/infra/edge/tests/validate_isolated.py --config /opt/hms/validation/network-edge-pg-20261024/runner-config.json
/opt/hms/validation/identity-20261023/venv/bin/python /opt/hms/validation/network-edge-source-20261024/infra/edge/tests/prepare_isolated_pg.py down
```

Runner migrates only the verified empty disposable DB and generates synthetic organisation/master membership/operator, encrypted MFA enrollment and session fixtures. All are test fixtures, not a UI or production provisioning path. It renders reviewed source with exact candidate paths and launches actual non-DEBUG source Gunicorn plus standalone Nginx. First the old direct-static topology must produce actual wildcard304 RED; then only the owned Nginx process restarts into the private Unix static topology. The outer Basic+auth_request guard remains on all public routes; no-store/security headers are inherited there. Only Host/Range enter private static handling; private socket0600 and prefix0700 are checked, including unprivileged connection denial. A synthetic shell/asset tests this routing, not real frontend usability. No mocked evaluator or stub HTTP backend supplies acceptance results.

The redacted JSON report at `/opt/hms/validation/network-edge-20261024/report.json` and stdout includes named checks, statuses, Nginx version/module flags, pass/failure and cleanup outcomes. Exit0 means the implemented matrix passed and listener cleanup passed; nonzero means failure. A generic failure stage/type avoids accidentally printing framework/DB secrets. Logs remain private under prefix for coordinator inspection, and must not be blindly copied into chat/Git. Source tests and `nginx -t` cannot substitute this report.

The actual matrix covers allowed127.0.0.1/denied127.0.0.2 socket-bound TLS requests, Basic AND policy, shell/index/SPA/assets/API/login, valid synthetic operator/session authority, spoofed IP/marker/cookies, direct private probe with actual Gunicorn HTTPS scheme, valid HEAD204/unsupported POST405 and invalid context404, no-store/HEAD/range/conditional responses plus retained security headers. It exercises managed backend stop, paused-worker read timeout, wrong-port disposable DB connection failure and health restoration. A full valid stored candidate/fallback graph has a fixed deadline three seconds ahead with exact300second intervals; before/after requests verify fallback without GET reconciliation. Precise deadline equality and transaction races belong to backend tests.

Coordinator separately verifies all15549/18185/18186 are inaccessible from an external client while active; local binding/version inspection is insufficient evidence. Preserve exact source/tar digest, versions, redacted report, baseline RED and external results. No real portal deployment, production DB protection, private files, MCP, streams, staff usability or full HMS release is implied.

## Cleanup and recovery

Runner owns only process groups created with `start_new_session=True`. In `finally`, it resumes paused owned groups before bounded terminate/kill/reap, removes generated htpasswd/private TLS key and verifies candidate ports closed. It never uses `pkill`, global reload or service restart. A cleanup failure makes the report fail; coordinator inspects the exact owned candidate resources and preserves recoverability.

After the web runner exits/closes ORM connections, coordinator runs helper `down`: exact receipt IDs, unique run labels, image, mounts, network and port are verified before removal of only the owned container/network/private PG prefix. Partial creation recovers only matching journaled resources; stale/mismatched receipts refuse cleanup. No shared SQL DROP/connection termination, Docker prune or global service action occurs. Preserve approved redacted report before deleting remaining web logs/TLS/config through verified exact literal paths. Re-run needs fresh empty isolated DB and absent web prefix. Production Stage E requires separate owner authorization and a reviewed rollout/recovery plan; worker/socket identity permissions are not resolved by this root-only test.

Official references: [Nginx auth_request](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html), [proxy headers](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header), [header inheritance](https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header). Installed1.24 lacks newer `add_header_inherit`; Cache-Control is intentionally declared at the same server context as existing security headers.
