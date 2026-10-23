# Network access control — design proposal, not an implemented feature

Status: planning draft. No new API/model/command/edge configuration is delivered by this document. Next implementer must freeze the exact OpenAPI/page/action/permission/failure/state/test contract before code. Read HMS.md, plan.md Task03, ledger and current usage checkpoint first. Existing preview47b3618 remains unchanged.

## Owner requirement and architectural decision

Only approved IPs must be able to open the app when whitelist-only mode is selected. Blocking API calls alone does not meet full portal coverage: the HTML shell, SPA paths, assets and future private files also need the network guard. Previously downloaded public assets cannot be erased remotely; protected future requests remain denied.

Coordinator ruling following independent design review: add one deployment-wide database overlay, always ANDed with the existing environment policy ceiling. Post-auth organisation policy alone cannot protect login. Rules do not change trusted proxies, public origin exposure or environment variables. No visitor is automatically whitelisted. The explicit Allow my current IP action adds the server-verified address to an unsaved draft only.

## Authority

- HMS_SECURITY_ORGANISATION_ID explicitly binds installation ownership. Never infer the first organisation. Missing/mismatched owner configuration disables management, while stored restrictions continue to be enforced.
- Require active identity/current session epoch, active master membership in the configured owner organisation, and separately provisioned active NetworkOperator entitlement for that user/organisation. Ordinary staff creation or granting master_admin does not create this entitlement.
- Compute platform.security.manage only from current entitlement plus owner membership, not a generic master-role grant. Direct services recheck the same authority. Enrollment and factor proof no older than15minutes are mandatory for this capability even in development; existing require_platform opt-out alone is insufficient.
- Local OS-authorised commands provision/revoke operator entitlement with reasons/audit. No UI entitlement grant or hidden unauthenticated recovery endpoint. Owner transfer needs an explicit audited out-of-band operation, invalidates previews/pending changes and never silently transfers entitlements.

## Durable state and policy semantics

Proposed models: NetworkPolicyState singleton1 with bound owner, monotonic revision, confirmed snapshot and pending change; NetworkPolicyChange with immutable candidate/fallback and activation/deadline/outcome; NetworkPolicyPreview with actor/session/epoch/verified-IP/base-revision/environment bindings and expiry/result pointer; NetworkOperator with user/owner/active/version metadata.

Migration inserts singleton1 with an unrestricted overlay (empty allow/block and whitelist-only false). Environment restrictions still apply. No request/GET creates missing state. Missing singleton, unavailable database or invalid stored policy returns503network_policy_unavailable; no stale permissive cache/fallback. Binding-management absence never disables enforcement. Test migration compatibility from the existing schema and account for transaction-test flushes using test fixtures, not request-time repair.

Canonicalise IPv4/IPv6/exact-IP/CIDR rules using existing resolver semantics, including mapped IPv6. Deny overrides allow within each ceiling. Whitelist-only requires an allow match. Bound rule counts/lengths, deduplicate and reject unknown fields; show host-bit normalisation in preview. Rule-specific enable/expiry can be a deliberately deferred extension; if included, evaluate expiry on every request and show loss of the operator's sole allow path. Do not hide it behind a scheduler.

## Preview, activation and rollback

1. Authorised POST validates a whole candidate, current effective path and expected revision; saves a preview valid five minutes. Bind actor, session, auth epoch, verified IP, environment fingerprint and candidate/base fingerprints.
2. Activation consumes that preview atomically, rejects a competing pending change and applies the candidate temporarily for a fixed five-minute rollback window. Client cannot replace the saved candidate in activation payload.
3. A separate confirmation must arrive through the candidate before the deadline, with matching identity/session/IP/revision/environment and current authority/fresh MFA. It promotes the candidate to confirmed baseline.
4. Explicit revert restores the saved baseline and advances revision. A stale revert cannot overwrite a newer change.
5. Every request selects fallback when now>=rollback deadline, even with no worker. Optional reconciliation command materialises expiry/audit idempotently; enforcement never depends on it. Retries cannot extend preview or rollback deadlines.

Lock order: canonical actor User/security state, owner Organisation, entitlement, singleton, preview/change. Recheck authority, epoch, factor age, deadline, environment and verified current path after final waits and at the transaction's audit boundary. Idempotent activation/confirmation replays may return their existing result only after current reauthorisation and exact binding checks; no duplicate audit/deadline extension. Record authorisation at transactional decision points, not a universal post-commit wall-clock guarantee.

Proposed versioned operations (not yet catalogued): read network state; preview candidate; activate preview; confirm change; revert change; bounded privileged history; network-only guard probe. Freeze exact schemas/counts/endpoints before implementation. Ordinary audit-history APIs must not expose global network rules or operator data. New policy audit projections need their own permitted view.

## Full portal edge coverage

Use only the dedicated HMS Nginx vhost. An internal auth_request subrequest calls a fixed loopback backend network-only handler returning204 or403, using the same environment AND database evaluator as API middleware. No staff authentication or recursive Nginx request is needed. Verify module availability; auth_request is not built by default. Nginx accepts2xx, denies401/403, treats other outcomes as errors; a backend503/timeout must fail closed (external500 is acceptable unless deliberately mapped).

The exact check location is internal, has inherited auth_request/Basic disabled to prevent recursion, proxy body off and Content-Length empty. Strip cookies/Authorization there. On the current direct-edge topology overwrite X-Forwarded-For with $remote_addr, set the full approved Host/proto header set, never append visitor-supplied chains. Fixed upstream/path only. Actual app locations retain Basic plus network checks with satisfy all; neither alone grants access. Origin stays loopback-only; direct external check location is404. Backend independently enforces API policy.

Guard HTML, nested SPA routes, static regex/alias/named/try_files targets, assets, API, HEAD/range/conditional requests and future private routes. Only an exactly named minimal health path may be exempt. No guard403/5xx becomes a SPA200. Disable permissive decision caching/stale reuse; portal retrieval no-store if literal future-fetch restriction is required. Private files also need normal authenticated data permissions. Streams/WebSockets require guarded handshakes and bounded lifetime/revalidation before ongoing network revocation is claimed.

## Recovery, UI and validation gates

Network access UI should name deployment-wide scope, verified current IP, mode/rules, canonical preview and current-path result. Apply temporarily, Keep these settings and Restore previous settings are separate clear actions with a fixed countdown. Preserve drafts/conflict feedback and explain ambiguous saves without unsafe retry. Adding an app rule never overrides an environment denial. No new visual system is needed.

Audited OS-authorised recovery command may inspect/revert pending or restore a selected policy snapshot under an explicit narrow out-of-band context. Require actor/reason/revision; same validation/audit services, no arbitrary SQL/shell/URL adapter. Environment lockout needs OS environment/proxy recovery; database outage must be repaired before durable policy recovery. Do not promise recovery from unavailable state or use an app bypass flag.

Before source completion: RED tests for all authority combinations including development MFA, environment precedence, missing/corrupt DB state, forged headers/mapped IPs, stale/tampered/cross-session/IP previews, environment drift, exact deadline rollback without worker, retries and competing changes, proof/permission expiry after lock waits and real PostgreSQL races. Test operator commands, migration singleton, CSRF, malformed/oversized rules and privacy. UI tests cover draft current-IP action, preview/apply/confirm/revert/conflict/expiry/ambiguity.

Before any full-portal claim: isolated actual Nginx config/HTTP tests for shell/assets/SPA/API/internal denial/Basic-plus-network, forged headers, conditional/range/HEAD, DB failure and rollback boundary. Source infra templates are not deployment evidence. No existing VPS app/vhost/firewall/global package change is authorised merely by this draft; deployment remains separate.

Primary references verified during design: [auth_request module](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html), [internal locations](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal), [satisfy](https://nginx.org/en/docs/http/ngx_http_core_module.html#satisfy), [proxy headers](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header). Recommendations are engineering choices, not a security certification.
