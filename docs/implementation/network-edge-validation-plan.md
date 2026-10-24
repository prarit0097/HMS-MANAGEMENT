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

## Proposed amendment D2 — isolated PG and strict no304 (research/design only)

Status24October2026 after coordinator resume11:07:26UTC: **FROZEN by coordinator after independent design review; code/runtime verification pending.** This section supersedes the old shared-PG connection approach only after approval. Existing source remains WIP, not deployable. Scope is exactly the two unresolved edge gates; no backend/frontend feature, shared HBA change, module installation or production rollout. All original private-probe, Basic AND policy, no-store/security-header, failclosed and cleanup requirements remain binding.

### No304 options and recommendation

| Option | Exact behavior | Tradeoff and decision |
|---|---|---|
| A — stock Nginx private Unix static server | Every public static route becomes a noncached proxy after its ordinary Basic+auth_request access phase. A sibling server in the same standalone Nginx process listens only on a protected Unix socket and owns static files/SPA fallback. Outer proxy forwards Host and Range only; no conditional/session/authorization/body headers enter static handling. | Recommended: no new dependency, TCP listener or static-serving process; existing Nginx MIME/range/HEAD/path behavior. Requires reviewed routing separation and Unix filesystem permissions. Actual wildcard/no304 test still mandatory. |
| B — Python standard-library Unix static responder | Same guarded noncached outer proxy; a separately managed Unix HTTP responder always produces fresh200/206 with no conditional304 support, rooted at the static directory. | No dependency/module, but adds an owned process and new code for URI decoding, traversal/symlinks, MIME, HEAD, suffix/multiple/invalid ranges, size bounds and socket lifecycle. Larger security/test surface for no current benefit; not selected. |

The old direct-static `etag off`/`if_modified_since off` combination is insufficient: Nginx1.24 checks wildcard before checking whether an ETag exists and may emit304. The version-pinned [not-modified filter source](https://raw.githubusercontent.com/nginx/nginx/release-1.24.0/src/http/modules/ngx_http_not_modified_filter_module.c) also skips its conditional conversion when `disable_not_modified` is set. The [upstream source](https://raw.githubusercontent.com/nginx/nginx/release-1.24.0/src/http/ngx_http_upstream.c) zero-initializes upstream state (lines441–468), enters cache setup only when configured (lines523–560), and sets `r->disable_not_modified = !u->cacheable` after upstream headers (line2735). **Inference:** explicit noncached outer proxy disables the outer filter, while stripping conditional headers prevents the inner filter from producing304. This is a source-backed design argument, not installed-runtime proof.

Official [proxy documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass) supports Unix upstreams; [request-header settings](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass_request_headers) permit dropping original headers and explicitly supplying a bounded subset. No `proxy_cache` zone is created, no stale response is allowed, and no rewrite-time return or error-to-SPA mapping is used to manufacture success. The wildcard assertion stays200/206 with no304 for allowed clients and403 for denied clients.

### Exact proposed static files, routes and permissions

- New `infra/edge/static-upstream.conf`, **http-context**: named upstream `hms_private_static` with one Unix server and a sibling private static server. Template socket `/opt/hms/run/edge-static.sock`; isolated renderer substitutes only `/opt/hms/validation/network-edge-20261024/static.sock`. Private server root template `/opt/hms/static`, isolated root `PREFIX/static`. No TCP listen, autoindex, API upstream, hidden downloads or mutable upload mount. `disable_symlinks on`, `etag off`, `if_modified_since off`, relative redirects. Private `/assets/` uses file-or404; `/` keeps SPA/index fallback. Exact internal-check/probe paths and all `/api/` return404 privately; dotfiles deny. Explicit private auth_request/auth_basic off prevents recursion; it creates no visitor-facing exception.
- New `infra/edge/static-proxy.conf`, **public location-context**: fixed `proxy_pass http://hms_private_static` without URI substitution preserves normalized routing; explicit `proxy_cache off`, `proxy_store off`, `proxy_next_upstream off`, `proxy_intercept_errors off`, connect1s/read3s, `proxy_pass_request_body off` and `proxy_pass_request_headers off`. Explicit Host fixed to hospital domain, Range from `$http_range`, Content-Length empty. Every If-* header, If-Range, Cookie, Authorization, proxy marker, visitor forwarding header and Accept-Encoding is absent upstream. HEAD remains HEAD; no unconditional `proxy_method GET`. Hide upstream ETag and Last-Modified from outer responses. No location-level add_header, so public server Cache-Control no-store and CSP/HSTS/security headers remain inherited.
- Modify `infra/hostinger/nginx.conf` **source only**: include the new http-context upstream/private server file. Replace public `/assets/` and `/` direct try_files with the static proxy include. Explicit `/index.html` uses the same include. Public login/API remain on existing backend proxy; private probe blocker/check and dotfile denial remain as frozen. All three public static locations inherit server Basic+auth_request+satisfy-all. Public private-server URI is never introduced; socket is an OS address only.
- Modify `infra/edge/tests/validate_isolated.py`: render all reviewed static includes rather than synthesizing another routing policy; same one standalone Nginx process and owned Gunicorn group. Prefix remains0700 root-owned, isolated socket0600 root-owned; no symlinks at any parent/socket path. Apply/verify socket mode before accepting test traffic; no unprivileged OS user can traverse the prefix or connect directly. Verify ordinary unprivileged connection raises permission denial through a fixed no-secret child test. Root/OS-local access is an infrastructure boundary, never a replacement for the public guard.
- Add RED coverage in existing `infra/edge/tests/test_source_contract.py` before implementation: no direct public static try_files, all public locations guarded, strict private header allowlist/cache settings, no extra TCP listener, exact socket/private paths, retained server headers and no secret/config path in static root. Runtime checks, not string assertions, establish actual guard/no304 behavior.
- Update `docs/operations/NETWORK-EDGE-VALIDATION.md` and this plan after reviewed code/evidence. Existing `infra/edge/network-guard.conf`/`infra/hostinger/proxy.conf` need no conditional workaround; preserve fixed network probe and ordinary-marker stripping. Coordinator alone maintains HMS/plan/ledger, Git and publication.

For any future production deployment, the Unix socket directory/owner/group/mode requires a separately reviewed Stage E worker identity arrangement; proposed template `/opt/hms/run`0700/0750 and socket0600/0660 must match the actual Nginx process identity. This D2 test uses root-only standalone Nginx and0700/0600 exactly. Do not install source into live Nginx or silently broaden directory/socket permissions to solve production access.

### Dedicated ephemeral PostgreSQL boundary

New root-only lifecycle helper proposed at `infra/edge/tests/prepare_isolated_pg.py`, with fixed `up`/`down` actions and no arbitrary resource names/paths/SQL input. Root executes it only after the coordinator freezes this design. Edge specialist never SSHs or invokes Docker. No existing Compose project, HBA, role, DB or PostgreSQL service is altered.

| Resource | Exact proposed value/boundary |
|---|---|
| Existing image | `postgres:17.11-bookworm`, inspected locally first; use its recorded image ID, no pull/build/install, record actual server_version_num170011 |
| Container | `hms-edge-validation-pg-20261024`; exact receipt ID plus label `hms.validation=network-edge-20261024` required for cleanup |
| Network | New dedicated bridge `hms-edge-validation-20261024`; no other container attached, no change to existing network/daemon rules |
| Host PG port | Only `127.0.0.1:15549` to container5432; no IPv6/wildcard publishing; preflight must prove free |
| PG runtime path | `/opt/hms/validation/network-edge-pg-20261024`; distinct from source and web prefix; root0700, no symlink or pre-existing unmanaged resource |
| Data | `PG_PREFIX/data` owned by the inspected existing image PostgreSQL UID/GID, mode0700; mounted only to this container's PGDATA |
| TLS | Fresh synthetic server key/cert in `PG_PREFIX/tls`, directory0750 root:PG_GID, key0600 PG_UID:PG_GID, cert0640 root:PG_GID; read-only `/tls` mount; ssl=on and ssl_min_protocol_version=TLSv1.2 |
| App role/DB | `hms_edge_app` LOGIN, NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION; DB `hms_edge_validation_20261024` owned by app, initially empty |
| Admin | Independent synthetic `hms_edge_admin`; private generated password file passed with POSTGRES_PASSWORD_FILE path, never literal secret in argv/env/log; no admin secret in runner config |
| Private initialization | Generated `PG_PREFIX/init/10-edge.sql` and separate admin-password file; directories0750 root:PG_GID, files0600 PG_UID:PG_GID, mounted read-only; exact role/database creation only, no patient/lead data |
| HBA | New `PG_PREFIX/pg_hba.conf` only, mounted read-only; local exact admin trust in this isolated container, other local reject; all hostnossl reject; hostssl exact app+exact DB with SCRAM; remaining host reject |
| Limits | restart=no, memory384MiB, cpus0.5, pids128, max_connections20, shared_buffers32MB; refuse start if coordinator capacity/preflight cannot support these bounded values |
| Evidence/private config | Root-only `PG_PREFIX/receipt.json` stores container/network/image IDs, exact paths/ports/labels and lifecycle state only. `PG_PREFIX/runner-config.json`0600 contains app-only schema below; never print credentials or raw init/container logs |

New private runner database input is fixed to `HOST=127.0.0.1`, `PORT=15549`, `USER=hms_edge_app`, exact DB name and `OPTIONS.sslmode=require`; venv remains `/opt/hms/validation/identity-20261023/venv`. This deliberately tightens the former arbitrary host/port role acceptance. The old shared PG5548 path is rejected. Runner still has no admin secret, Docker action, DB create/drop operation or unmanaged-connection termination.

Coordinator preflights Docker Engine version, local image ID/actual version, free15549/18185/18186, absent exact container/network/path, memory, unchanged live preview and original HBA hash. Docker's [port-publishing documentation](https://docs.docker.com/engine/network/port-publishing/) records a pre28.0.0 localhost-publishing L2 exposure caveat: require Engine>=28 for this proposed published-loopback design, or stop and amend design; do not alter firewall/daemon or claim local inspection proves external unreachability. No default/publicly published DB port. A dedicated bridge isolates other managed app containers by membership; no claim that this configuration defeats OS/root or Docker-admin access.

The [PostgreSQL17 SSL documentation](https://www.postgresql.org/docs/17/ssl-tcp.html) defines TLS/key permissions; [HBA documentation](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html) defines TLS-only record selection. Allowing the exact app+DB from container-network addresses avoids assuming Docker's translated source equals127.0.0.1; SCRAM, unique generated password and network boundary remain mandatory. Role/db ceilings and explicit remaining rejects prevent an admin TCP path. `sslmode=require` matches the frozen application TLS contract; it does not claim CA/hostname verification.

Helper uses Docker argv arrays, credential file mounts and SQL-quoted generated secrets; no shell text interpolation/password arguments. The [official image entrypoint source](https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh) supports file-based environment secrets and first-initialization hooks; inspect the entrypoint of the **actual local image** before relying on its UID/init behavior. A partial operation journal is written before each owned resource creation so interrupted up can be recovered only after identity/labels/path verification. Never delete a pre-existing resource merely because its name matches.

### D2 test matrix and rollout/cleanup gate

All old actual-HTTP rows stay mandatory. Extend them as follows, and retain expected RED before implementing the source change:

| Check | Required outcome |
|---|---|
| Baseline wildcard conditional on current direct-static config | Actual allowed request demonstrates the unresolved304 as RED; no rewrite-time shortcut or relaxed assertion |
| GET/HEAD `/`, `/index.html`, nested SPA, assets with wildcard, quoted validator, IMS, combined validators | Allowed200 with fresh body/empty HEAD, no304; denied403 and missing Basic401/403; existing CSP/HSTS/no-store retained |
| Range bytes0-9, suffix and invalid range; Range+If-Range/wildcard | Actual206/correct bytes and Content-Range,416 when invalid; stripped If-Range cannot switch in cached bytes; denied403 before file serving; HEAD remains bodyless |
| Private transport/header boundary | No public/private static TCP listener; UDS mode0600/prefix0700; unprivileged direct connect denied; private access log records header-presence booleans only, proving conditional/cookie/auth/marker absent and Range preserved |
| API/probe routes on private static server and public external probe | Private404 and public frozen404; no SPA success, no backend/health data exposure |
| Dotfile, encoded traversal and generated symlink to synthetic sentinel outside static root | No sentinel/config content; allowed safe404/403/400 or legitimate SPA shell, denied paths remain denied; no autoindex |
| Stop/unlink only owned private static socket | Outer allowed HTML/asset5xx and no SPA success; restore same private service/socket permissions then verify healthy200 and denied403; network DB failure stays failclosed independently |
| Dedicated PG actual connection | server_version_num170011, pg_stat_ssl.ssl=true; app nosuper/nocreatedb/nocreaterole/noreplication; wrong password, nonTLS, wrong DB/role rejected; empty public schema before migrations |
| Guard/inheritance/fault matrix against dedicated PG | Full original actual Gunicorn/Nginx/synthetic policy/MFA/session matrix, source and versions pinned, no mocked policy; stop/pause/wrong-port failures restore health |
| External origin and cleanup | Coordinator external client cannot connect15549/18185/18186; local binding alone insufficient. Managed web groups stop/reap, Unix socket removed and three ports absent after exact container cleanup; live preview/HBA hash unchanged |

PG helper owns lifecycle separately from the web runner: root `up` provisions only the fresh dedicated container/network/path, waits bounded readiness, verifies app TLS/role restrictions and writes private app config. Runner consumes the verified empty database. After runner stops and closes ORM connections, root `down` verifies saved receipt IDs and labels, stops/removes only that container, removes only its now-empty dedicated network, then deletes generated secrets/data with resolved literal paths confined to PG_PREFIX. Never `docker prune`, broad rm/kill, shared SQL DROP/pg_terminate_backend or recursive deletion across validation siblings. Web runner never manages Docker and retains its owned-group finally path.

Root preserves redacted report/imageID/version/header-status/cleanup evidence before exact-path cleanup. On any mismatch or unowned pre-existing resource, stop and report; no destructive repair. Re-run requires root-reviewed removal of only prior owned resources and a newly empty isolated DB. Source rollback reverts D2 source only; all live deployment remains Stage E. Review/freeze this amendment before executable tests/template/helper code, then RED→GREEN→actual isolated acceptance→independent review. This research amendment runs no tests and establishes no runtime acceptance.

### D2 coordinator freeze and mandatory review precisions

FROZEN24October2026 after independent design review and coordinator source review. No identified Critical/Important architectural blocker; this is not source or runtime approval. Before executable implementation, bind these precisions:

- PG starts with POSTGRES_USER=hms_edge_admin, POSTGRES_DB=postgres, explicit PGDATA bind and postgres arguments hba_file to external read-only HBA, ssl=on, explicit /tls certificate/key, password_encryption=scram-sha-256. External HBA0640 root:actualPG_GID, separate from PGDATA/pg_hba.conf; local exactadmin trust permits postgres bootstrap DB. Actual local image entrypoint was read in a disposable read-only/network-none container and confirms file-secret/bootstrap-HBA/argument behavior; UID/GID999/999.
- Generate/journal unique run token BEFORE resources; both dedicated network/container carry that token label. Cleanup/recovery verify token, resource IDs, mounts, labels and exact resolved paths. Executable RED scenarios cover partial creation, stale/mismatched receipts and refusing unowned resources. Never remove an existing resource merely by matching its name.
- Socket unlink fault restoration restarts ONLY the owned standalone Nginx process, recreates exact socket, reapplies/verifies0600 and rechecks Basic AND network. No global nginx/service action. External probes separately check all15549/18185/18186; bind/version inspection is supplementary.
- Root read-only preflight: Docker29.3.0; actual local image sha256:858bb5e98eed02eb8cafbcdc007f9a65d1b613972028944a8ec2133ccaf80d27;15549/18185/18186free; available memory11519MiB before planned384MiB container. Existing preview/sharedPG/HBA unchanged. No runtime acceptance or paid provisioning.
