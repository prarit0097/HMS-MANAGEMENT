# Network edge validation implementation plan — 24 October 2026

> Execution: the assigned edge specialist implements this plan inline after coordinator review, using the executing-plans and test-driven-development skills. Coordinator alone runs VPS helpers and commits/pushes shared changes. No additional agent is required.

**Goal:** produce reusable Nginx guard source and actual isolated HTTP evidence for the frozen network-access contract §10, without changing the running preview.

**Architecture:** standalone Nginx TLS gateway on `127.0.0.1:18186`, source Django through actual non-DEBUG Gunicorn on `127.0.0.1:18185`, and a disposable TLS PostgreSQL database. A fixed private `auth_request` performs network evaluation independently of Basic authentication and application sessions. Ordinary API paths retain backend enforcement.

**Tech stack:** installed Ubuntu Nginx 1.24.0 with compiled auth_request/SSL modules (coordinator preflight), Python standard-library harness, existing candidate virtualenv with pinned Gunicorn 26.2.0 installed only there, Django source and private PostgreSQL.

**Spec:** `docs/implementation/network-access-contract.md` §10, `network-integration-plan.md`, `AGENTS.md`, HMS network status, plan Task03 and implementation ledger. All below are planned checks, not passed evidence.

**Checkpoint — coordinator bounded stop, 24 October 2026:** source is WIP and not deployable. Planning unit frozen/pushed at `c9c9eecdaa9434e0fd488b18605520cac2d40544` before CODEGATE; subsequent edge implementation remains coordinator-owned publication work. Local four source assertions failed for intended missing protections, then passed. Two runner safety/render assertions failed before runner implementation, then passed. Cleanup regression had one Windows mocking setup error, corrected to meaningful RED before fix; final seven tests passed in0.198seconds and Python compilation passed. Coordinator actual runner preflight stopped with `OperationalError`, independently classified HBA rejection (not password failure or missing DB); no HTTP/Nginx process started. Coordinator owns exact disposable DB/config cleanup. No actual Nginx parse, scheme, HTTP/cache, timeout, DB failure or fallback acceptance passed.

**Known blocker requiring explicit next design amendment:** current `etag off` plus `if_modified_since off` cannot suppress standalone `If-None-Match: *`304 on stock Nginx1.24 static responses. Official version-pinned [filter source](https://raw.githubusercontent.com/nginx/nginx/release-1.24.0/src/http/modules/ngx_http_not_modified_filter_module.c) tests wildcard before absence of ETag and emits304. Harness deliberately keeps its no304 assertion; do not weaken the frozen requirement or claim the current source verified. A future reviewed solution must preserve the access phase, guard inheritance, security headers and fixed isolation scope; no rewrite-time return that bypasses the guard. HBA rejection requires a future independently isolated PostgreSQL plan, not shared/live HBA mutation. No further implementation unit is authorized at this checkpoint.

## Scope, ownership and exact files

- Create `infra/edge/network-guard.conf`: server-context auth_request/satisfy-all/no-store/static conditional-cache directives plus exact internal check and external probe blocker. Fixed production backend 127.0.0.1:8185; isolated renderer changes only this fixed endpoint to 18185.
- Modify `infra/hostinger/nginx.conf`: include guard at protected TLS server level, retaining Basic, CSP/HSTS and all security headers. No live installation is implied.
- Modify `infra/hostinger/proxy.conf`: explicitly erase inbound X-HMS-Network-Probe on ordinary API requests; preserve direct-edge XFF overwrite and TLS scheme handling.
- Create `infra/edge/tests/test_source_contract.py`: executable pre-code assertions for guard integration, private probe/header stripping, failclosed settings, no-store/cache behavior and security-header inheritance. Run RED before template edits.
- Create `infra/edge/tests/validate_isolated.py`: coordinator-executed isolated runner, fixture lifecycle, source-config rendering, actual HTTPS matrix and redacted JSON report. CLI requires private config path; refuses unsafe prefix/ports/DB identifiers. Source checks are supplementary; runtime requests are acceptance evidence.
- Create `docs/operations/NETWORK-EDGE-VALIDATION.md`: invocation/config schema, evidence, process cleanup and future rollout boundary. No production rollout instruction is executable by this harness.
- Backend/frontend/API contracts, Git, HMS/plan/ledger/usage records remain coordinator/other-specialist ownership. Any necessary fixture must live inside the edge test harness, never a product bypass.

## Isolation and private input contract

Dedicated runtime prefix exactly `/opt/hms/validation/network-edge-20261024`; reviewed source is extracted separately to `/opt/hms/validation/network-edge-source-20261024`. Root-owned private JSON input outside tracked source supplies only `venv` and `database`: exact `NAME=hms_edge_validation_20261024`, `USER`, `PASSWORD`, `HOST`, `PORT`, `OPTIONS.sslmode=require`. Source root derives from runner location and must match that exact source folder. No admin DB credentials enter the runner. Do not print connection strings, passwords, MFA secrets, Basic credentials, session cookies or private config contents. Fixtures generate synthetic organisation/master/operator/password/MFA/Basic credentials privately and do not use real patient/lead data. Basic htpasswd, temporary TLS key/certificate, PID/log/temp/static and redacted report all stay under prefix with restrictive permissions.

Coordinator alone creates, verifies empty, and drops the disposable DB. Runner consumes the verified empty DB and must never create/drop any DB or terminate unmanaged DB connections. Runner rejects a pre-existing unmanaged prefix/process/listener or unexpected DB name; no live `.env`, schema, policy or operator edits. Migrate only the disposable DB, with environment assembled from private config and source settings. Coordinator alone installs pinned Gunicorn26.2.0 in the existing candidate virtualenv. Runner never installs packages or changes the live virtualenv. Bind both listeners IPv4 loopback only. Nginx is launched with explicit `-p PREFIX/ -c PREFIX/nginx.conf`, independent PID/log/temp paths and managed foreground process. Never `/etc/nginx`, global reload/restart, systemd changes, firewall changes, production DB, other apps/ports or paid resources.

Gunicorn uses source `hms.wsgi:application`, `DEBUG=false`, fixed allowed host, production secure-redirect setting and `--forwarded-allow-ips=127.0.0.1`. No broad Django forwarded-proto override. Nginx probe must strip all incoming headers/body and send only frozen Host, real socket IP/XFF, HTTPS scheme and marker. Probe fixed URI has no query. No health path revealing data is added; exact existing health can remain Basic protected/network exempt only if deliberately configured and tested.

## Pre-code scenario, permission and threat checks

1. Network allow grants no staff authority: valid Basic plus allowed socket IP reaches application authentication, anonymous API remains 401/403. Invalid/missing Basic denies even when network allows; valid Basic cannot overcome network denial (`satisfy all`).
2. Visitor marker, XFF, Forwarded, cookies and Authorization cannot select private context or rewrite the socket identity. `127.0.0.1` is allowed client and socket-bound `127.0.0.2` denied client; requests use real HTTPS sockets, not a spoofed header simulation.
3. All app-serving locations inherit the guard, including internal SPA redirect to index. Exact internal location is inaccessible externally and breaks auth recursion. Public exact probe returns404; query/body/marker/peer invalid contexts remain404 at backend. Valid HEAD may mirror GET204 with empty body; unsupported POST returns405 per frozen parent §37. Nginx always sends fixed GET.
4. Probe DB failure/timeout fails closed, never stale allow or HTML200. Backend API still evaluates independently after edge allow. No error_page converts denial/unavailable into SPA success.
5. No-store must coexist with all existing security headers: put Cache-Control at the same server context as existing add_header directives, and remove conditional304/etag behavior for protected static content. Test range and HEAD rather than assuming caching directives prove access control. Already downloaded bytes are outside revocation guarantees.

## Executable acceptance matrix

Every row records observed status plus bounded header/body assertions. Reports omit credentials/request payloads. Test failures exit nonzero and still clean up.

| Requests/state | Expected evidence |
|---|---|
| Direct trusted-peer probe GET, marker1, HTTPS forwarded by actual Gunicorn | Empty204, no Location/Set-Cookie/WWW-Authenticate; no redirect loop |
| Direct probe denied policy / missing or unavailable state | Empty403 /503, no-store; no session work (backend specialist independently tests session mutation) |
| Direct probe wrong marker, absent marker, body or query; valid HEAD/unsupported POST; untrusted peer |404 for invalid context; valid HEAD204(empty), unsupported POST405; secure redirect may precede probe for untrusted HTTP peer; forged XFP must not create HTTPS state |
| Allowed Basic client HTML `/`, `/index.html`, nested SPA, asset, API, login GET | App HTML/assets200; anonymous protected API401/403 distinguished from edge block, login GET contract status rather than invented success |
| Same paths from denied socket client with valid Basic |403 and no protected body, including nested SPA redirect/index and missing asset |
| Missing/wrong Basic from allowed/denied socket |401/403; no protected content; explicitly prove Basic AND network |
| HEAD, byte range and matching If-Modified-Since/If-None-Match on shell/assets | Allowed expected200/206, HEAD empty; no304; denied403; Cache-Control no-store and existing CSP/HSTS/security headers retained |
| External `/_hms_network_check` and exact public probe |404 for both clients, never upstream probe success |
| Forged XFF, Forwarded, X-Real-IP, X-HMS-Network-Probe1, Cookie/Authorization | Denied socket remains403; allowed ordinary API remains application-auth protected |
| Dotfile and absent paths | Dotfiles deny; absent asset404 for allowed client; absent nested SPA may200 only while allowed; denied remains403 |
| Stop candidate backend / hold all candidate workers past3s | Edge5xx within bounded timeout, never200/redirect/SPA body; restore backend and verify same policy again |
| Disposable DB unavailable state using candidate-only fault configuration | Direct probe503 and protected edge5xx; restore and verify healthy allowed204/HTML200 and denied403 |
| Temporary candidate excludes127.0.0.2, fallback allows it; fixed persisted rollback deadline2–3seconds ahead with exact300second creation/activation intervals | Before deadline403; at/after deadline200 on protected shell, using controlled fixture deadline with full valid immutable graph; GET does not persist reconciliation |
| External connection to candidate loopback/backend | Coordinator separately verifies origin unreachable externally; local bind inspection is supplemental and cannot substitute external reachability |

Rollback fixture uses source services/models only for generated test data; no monkeypatch of production evaluator. Precise equality/clock service behavior remains backend tests; actual edge observes before/after persisted deadline without a five-minute sleep. Fault tests act only on managed candidate processes or disposable DB connection configuration and always verify restored health.

## Tasks and gates

- [x] Coordinator reviewed plan and accepted with precisions before code: exact DB/no admin credentials; separate source/runtime paths; coordinator-only DB lifecycle/package install; owned process-group cleanup; actual2–3second rollback fixture; wrong-port owned-backend DB failure. Coordinator froze/pushed planning unit then cleared CODEGATE.
- [x] Write `test_source_contract.py`, run it against current source, retain exact RED failures. Missing guard/integration failed for intended reasons rather than environment collection errors.
- [ ] Implement minimal reusable guard and hostinger source integration; run source checks GREEN. Parse rendered actual Nginx config, retain `nginx -V`/`-t`; parsing is not runtime acceptance.
- [x] Implement private-input runner and synthetic fixtures after backend interfaces stabilize; fail closed on unsafe inputs. Local source/safety/regression checks seven GREEN and compilation passed; actual fixture execution blocked at DB connection preflight.
- [ ] Coordinator transfers reviewed source and invokes runner in exact prefix with disposable private TLS PG settings. No agent SSH/VPS mutation.
- [ ] Run actual non-DEBUG Gunicorn/Nginx HTTP matrix, record counts/status/headers, failure restoration, residual gaps and runtime versions.
- [ ] Coordinator/fresh reviewer reviews source and observed edge evidence. Coordinator alone incorporates accurate HMS/plan/ledger updates, commits/pushes and verifies remote SHA.

## Cleanup and rollback

`try/finally` uses dedicated managed process groups (`start_new_session=True`), sends SIGCONT before graceful termination if paused, then bounded wait/kill/reap only those owned groups. It verifies 18185/18186 no longer listening and records outcome. Runner never drops/creates databases or terminates unmanaged DB connections. Coordinator separately drops the exact disposable DB after runner cleanup; never stop the shared PG service. Delete generated htpasswd/private TLS/session fixtures and runtime secrets with literal paths verified under the exact prefix. Retain only redacted report/log evidence as coordinator directs; no recursive move/delete outside resolved prefix. On incomplete cleanup, report exact candidate resource needing cleanup, preserve recoverability and fail run. Existing live service/policy/schema must remain unchanged; coordinator can verify live service health separately without altering it.

Source rollback is a reviewed revert of these source files only. No live Nginx configuration was installed, so no global rollback/reload is necessary. Production deployment remains Stage E with separate owner authorization, concrete rollout/recovery plan and real staff acceptance; no private-file/MCP/stream/full-HMS release claim.

Official primary directive references: [auth_request](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html), [proxy_set_header](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header), [internal](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal), [satisfy](https://nginx.org/en/docs/http/ngx_http_core_module.html#satisfy). Coordinator reopened auth_request/proxy references during preflight; source specialist must verify exact directive semantics before implementation. No runtime check has been executed by writing this plan.
