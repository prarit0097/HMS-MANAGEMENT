# Isolated network edge validation

This is Stage D source validation, not production deployment. Read the [frozen plan](../implementation/network-edge-validation-plan.md) and [network contract §10](../implementation/network-access-contract.md#10-full-portal-edge-contract-and-probe-circularity). The coordinator runs the VPS commands; specialists do not SSH. Keep live Nginx, services, application environment, DB/schema and policy unchanged.

**Current checkpoint: WIP, not deployable.** Local seven source/safety checks and Python compilation pass. Actual candidate run stopped at disposable PostgreSQL HBA rejection before HTTP/Nginx launch. Separately, the current static directives do not suppress wildcard `If-None-Match: *`304 on Nginx1.24; the runner keeps its failing acceptance expectation rather than weakening the contract. Both require reviewed follow-up design. Do not install this guard into the live preview or describe source checks as runtime verification. Coordinator owns cleanup of the exact disposable DB/private config.

## Prerequisites and private input

Coordinator verifies installed Nginx auth_request/SSL support and free loopback ports18185/18186, reviews source, then transfers source only to `/opt/hms/validation/network-edge-source-20261024`. Runtime directory `/opt/hms/validation/network-edge-20261024` must not exist; an existing directory is a deliberate refusal, not permission to delete it. Coordinator installs pinned Gunicorn26.2.0 only in `/opt/hms/validation/identity-20261023/venv` and creates/verifies an empty disposable TLS PostgreSQL DB named exactly `hms_edge_validation_20261024`. Never grant the runner an admin connection or use production DB as its input.

Create a private root-owned mode0600 JSON file outside source with this schema. Values below are placeholders, not credentials:

```json
{
  "venv": "/opt/hms/validation/identity-20261023/venv",
  "database": {
    "NAME": "hms_edge_validation_20261024",
    "USER": "PRIVATE_DISPOSABLE_DB_ROLE",
    "PASSWORD": "PRIVATE_VALUE",
    "HOST": "PRIVATE_TLS_PG_HOST",
    "PORT": "PRIVATE_TLS_PG_PORT",
    "OPTIONS": {"sslmode": "require"}
  }
}
```

The runner refuses extra keys, another DB/venv, non-TLS settings, populated public schema, wrong source path, existing runtime prefix or occupied candidate ports. It never installs packages, creates/drops a DB, kills unmanaged DB sessions, changes global Nginx, restarts services or edits shared config. Private DB password is passed via child environment, not CLI/URL/stdout. Generated Basic password goes to OpenSSL stdin, not arguments. No real patient/lead data is needed.

## Commands and evidence

Local supplementary checks:

```powershell
python -m unittest discover -s infra/edge/tests -p test_source_contract.py -v
python -m py_compile infra/edge/tests/validate_isolated.py
```

Coordinator-only candidate invocation (substitute the private config pathname):

```sh
/opt/hms/validation/identity-20261023/venv/bin/python /opt/hms/validation/network-edge-source-20261024/infra/edge/tests/validate_isolated.py --config /absolute/private-config.json
```

Runner migrates only the verified empty disposable DB and generates synthetic organisation/master membership/operator, encrypted MFA enrollment and session fixtures. All are test fixtures, not a UI or production provisioning path. It renders the reviewed Hostinger TLS server by replacing only known live paths/listeners and inlining reviewed guard/proxy source. A synthetic static shell/asset exercises the same location routing, internal index redirects and guard inheritance; it does not establish real frontend usability. It launches actual non-DEBUG source Gunicorn with secure redirect and the exact127.0.0.1 trusted forwarder, and standalone foreground Nginx with private PID/temp/log/TLS paths. No mocked evaluator or stub HTTP backend supplies acceptance results.

The redacted JSON report at `/opt/hms/validation/network-edge-20261024/report.json` and stdout includes named checks, statuses, Nginx version/module flags, pass/failure and cleanup outcomes. Exit0 means the implemented matrix passed and listener cleanup passed; nonzero means failure. A generic failure stage/type avoids accidentally printing framework/DB secrets. Logs remain private under prefix for coordinator inspection, and must not be blindly copied into chat/Git. Source tests and `nginx -t` cannot substitute this report.

The actual matrix covers allowed127.0.0.1/denied127.0.0.2 socket-bound TLS requests, Basic AND policy, shell/index/SPA/assets/API/login, valid synthetic operator/session authority, spoofed IP/marker/cookies, direct private probe with actual Gunicorn HTTPS scheme, valid HEAD204/unsupported POST405 and invalid context404, no-store/HEAD/range/conditional responses plus retained security headers. It exercises managed backend stop, paused-worker read timeout, wrong-port disposable DB connection failure and health restoration. A full valid stored candidate/fallback graph has a fixed deadline three seconds ahead with exact300second intervals; before/after requests verify fallback without GET reconciliation. Precise deadline equality and transaction races belong to backend tests.

Coordinator separately verifies candidate origin ports are inaccessible from an external client; report marks this as outstanding because local loopback inspection is insufficient external evidence. Keep exact source commit/tar digest, versions, report and this external result together. Do not claim real portal deployment, production DB protection, private files, MCP, streams, staff usability or full HMS release from this bounded synthetic static/source-backend check.

## Cleanup and recovery

Runner owns only process groups created with `start_new_session=True`. In `finally`, it resumes paused owned groups before bounded terminate/kill/reap, removes generated htpasswd/private TLS key and verifies candidate ports closed. It never uses `pkill`, global reload or service restart. A cleanup failure makes the report fail; coordinator inspects the exact owned candidate resources and preserves recoverability.

Coordinator alone drops `hms_edge_validation_20261024` after confirming managed processes stopped. Remove private config and sensitive candidate logs/temporary TLS certificate after preserving approved redacted evidence. Before any recursive cleanup, verify resolved literal source/runtime paths remain exactly the two named validation folders; never compute deletion paths from config or glob across `/opt/hms/validation`. Re-run needs a newly empty disposable DB and absent runtime prefix, so it cannot accidentally reuse earlier synthetic state. Live resources have no rollback step because none were changed. Production Stage E requires separate owner authorization and a reviewed rollout/recovery plan.

Official references: [Nginx auth_request](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html), [proxy headers](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header), [header inheritance](https://nginx.org/en/docs/http/ngx_http_headers_module.html#add_header). Installed1.24 lacks newer `add_header_inherit`; Cache-Control is intentionally declared at the same server context as existing security headers.
