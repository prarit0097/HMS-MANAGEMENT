# Supervisor readiness: database privilege boundary

**DRAFT — 15 November 2026, Asia/Calcutta.** Proposed design only: no role, grant, function, schema, runtime, API or credential is created. Read with [launch proof](document-ingestion-launch-proof-draft.md), [guard authority](document-ingestion-guard-authority-contract.md), [persistence](document-ingestion-persistence-contract.md) and [runtime](document-ingestion-runtime-contract.md). Parent ingestion is unfrozen; S1 facts do not establish OS authority.

## Existing source and smallest candidate

`backend/hms/settings.py` uses the configured default database identity for Django. `infra/hostinger/prepare_host.py` initially creates `hms_app` and makes it database owner; this source is not a fresh inspection of live ACLs. NOCREATEDB/NOCREATEROLE alone does not prove column/function isolation. Do not reuse the general application/migration credential for the supervisor or assume that a Python method limits arbitrary SQL permitted to its login.

This proposal isolates the **publisher credential**, not the entire existing application/database-owner blast radius. Compromise of a general owner/migration credential is outside that narrow guarantee and can invalidate wider database security/availability assumptions. Before activation, inventory actual ownership/membership/schema/default privileges and freeze how new protected ingestion objects are created outside runtime ownership. No existing role is silently downgraded or declared isolated here.

| Choice | Benefit | Missing protection |
|---|---|---|
| Readiness-column UPDATE grants only | Small ACL change; expected-launch and gate columns can remain excluded | Allows arbitrary permitted readiness values, bypassing intended tuple/expiry/transition predicates. Existing table-level or inherited grants defeat column exclusions. Does not authenticate OS process identity. |
| One typed SECURITY DEFINER publication function, no publisher table DML | Centralises the allowed conditional readiness mutation; direct writes to readiness, gates, accounting and expected launch are denied | Adds a tightly reviewed SQL security boundary. It still cannot authenticate launch descriptors, real scanner evidence or a Linux process from supplied SQL arguments. |

**Candidate:** the second choice for publication/renewal, with a fixed status lookup for unknown-ACK reconciliation, not a general SQL broker. No enable/install/restore/claim endpoint is included. Function signatures and actual SQL are a future frozen leaf, not supplied executable code.

PostgreSQL permits column privileges, but a table grant still applies when a column grant is revoked. This rules out subtractive column restrictions on an already privileged login. [PostgreSQL 17 GRANT](https://www.postgresql.org/docs/17/sql-grant.html). Ownership also carries rights that ordinary revocation cannot permanently remove; publisher must not own protected objects. [PostgreSQL 17 privileges](https://www.postgresql.org/docs/17/ddl-priv.html).

## Proposed identities and object ownership

Names below are candidate labels, not provisioned accounts. All dedicated service logins are NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS, without grant options or membership/SET ROLE paths into privileged roles.

| Identity | Ceiling |
|---|---|
| Non-login ingestion schema owner | Owns new protected Control/functions/schema. Accessible only through a separately reviewed migration/maintenance path; no runtime service inherits it. Existing preview object ownership is unchanged by this draft. |
| Non-login readiness-function owner | Only required bounded SELECT and UPDATE of readiness columns, not expected launch, gates, epoch, accounting or patient data. No CREATE on schema, ownership of Control, role administration or broad inherited privileges. Owns only the fixed publication/status functions. |
| Dedicated supervisor publisher login | CONNECT, USAGE of fixed protected schema, EXECUTE on exact function signatures only. No Control DML, table ownership, schema CREATE, patient-table access, application-role membership or key/administration privilege. Credential held only by the approved supervisor process; excluded from scanner/decoder/updater/ordinary app. |
| Root-controlled maintenance identity | Separately protected authority installs/replaces expected launch and gates under the reviewed maintenance procedure. Never placed in publisher environment/child handles. Its eventual credential delivery and full capability contract remain open. |

Function creation, PUBLIC-execute revocation and exact publisher grant occur in one future migration transaction. Use fixed schema-qualified objects/operators, fixed trusted `search_path` with `pg_temp` last, no dynamic SQL, arbitrary identifiers, search paths, URLs, files or commands. Default privileges and inherited grants need explicit verification. PostgreSQL warns that SECURITY DEFINER executes as its owner and documents both safe search-path handling and default PUBLIC EXECUTE. [PostgreSQL 17 CREATE FUNCTION](https://www.postgresql.org/docs/17/sql-createfunction.html).

## Typed business contract to freeze

Publication accepts only a closed tuple: installation/epoch, exact supervisor launch instance/context, independently named scanner generation, fixed manifest/policy/signature hashes, bounded observation timestamps, and one proposed publication UUID. No gate/accounting/expected-launch assignment, raw JSON expansion, actor ID, dynamic object name or SQL text is accepted. Exact scalar types/ranges and the final generation-name mapping must be reconciled with the generation draft before freeze.

The trusted supervisor service takes fresh guard/process/scanner observations **outside** every database transaction. The database primitive receives detached immutable values; SQL does not perform filesystem, network, key, scanner or process I/O. It locks only Control, skipping earlier untouched rows in the common lock order. Caller must not acquire earlier-order User/IdentitySecurity/Actor locks after this call within the same transaction. Maintenance takes the same Control lock; no process stop/start under that lock.

While locked, require the singleton to exist and be valid, installation/epoch and complete expected launch equality, API enabled, correct current scanner generation/manifest/policy, and the database portion of first-slice authority. Non-restore external guard/process provenance must already be independently checked by the trusted service outside locks; this SQL comparison cannot authenticate it or detect a restored matching snapshot by itself. Missing/corrupt state fails closed. Require actual evidence ages and a server-checked validity cap no later than the permitted observation expiry and 60-second readiness bound; a caller timestamp cannot extend age by replacing the original observation. The function changes only the complete readiness tuple and linked launch/scanner identities, never any gate or expected identity. Fixed denials expose no patient data or raw scanner signatures.

**OPEN bootstrap/restart gate:** the authoritative current scanner generation is a precondition, not a readiness field the publisher may install. The root expected-launch installation above does not yet specify who registers/replaces scanner generation after initial start, daemon restart or signature change. A separately frozen typed scanner-registration transition must define its owning principal/function privilege, expected-launch binding, old-generation invalidation/readiness clearing, cessation and known-ACK ordering before this candidate can operate. Until that path is designed and verified, missing/mismatching scanner generation denies publication; never let renewal adopt a caller-proposed generation or expand the readiness-function owner's privileges implicitly.

Function success inside a transaction is not known COMMIT. Do not advertise readiness until the outer transaction has known commit and a new outside-lock guard/process check succeeds. No SQL function creates an atomic OS/DB view or instant revocation. Dedicated process credentials plus trusted code/descriptor custody are still required; a caller possessing the publisher credential could invoke the narrow function with fabricated evidence matching readable identity values. This candidate contains that credential to readiness operations; it does **not** prove evidence truth or resist arbitrary execution in the approved supervisor.

For a lost COMMIT ACK, remain locally unready. Reconnect using the same publication UUID and exact immutable evidence fingerprint; fixed status lookup under current Control may confirm that exact tuple only. A replaced launch/generation, closed API, expired evidence, mismatched token/fingerprint or unresolved status never implies permission. Do not generate a fresh observation time/token to conceal uncertainty, reopen gates, or assume old readiness disappeared. Once uncertainty resolves, a genuinely new observation is a separate normal renewal, with its own current authority checks. Exact idempotency storage and status return shape remain schema/API acceptance gates.

Root install/replacement requires ingress and ordinary callers stopped, previous launch fenced, readiness cleared, old-process cessation proved outside locks, and a known committed expected tuple before publication. Failed cessation or unknown expected-install ACK blocks replacement. Restore retains external epoch authority and closed gates; copied expected/readiness fields cannot activate this first slice. No function is authorised to install an epoch or re-enable restore.

## Required literal tests before implementation

- Direct publisher INSERT/UPDATE/DELETE/TRUNCATE/ALTER/GRANT against Control, expected-launch/gate/accounting columns and patient tables fail; allowed EXECUTE alone succeeds only under its typed preconditions.
- App/worker/scanner/decoder/guard-reader credentials cannot execute publisher functions or assume their owner. Test indirect memberships, inherited table grants, PUBLIC privileges and writable schema/temp-object shadowing.
- A paused publisher cannot renew after API close, launch replacement, scanner replacement or epoch change while awaiting Control; no forbidden column changes occur on success, denial or exception.
- Lost publication/install ACK tests preserve original UUID/fingerprint/times and independently inspect durable state; late ACK/expiry remains locally unavailable and never flips gates.
- No OS/scanner/key/process I/O under Control locks; failed postcommit guard/process observation suppresses advertisement. Malformed tuple/hash/expiry and nonexistent/corrupt singleton deny safely.
- Fixed-function owner is non-login, non-superuser and cannot replace expected tuple or gates; hostile search_path/temp objects cannot redirect any query; migration grants are atomic and have exact overload signatures.

No executable tests were run for this proposal. Freeze remains blocked on exact SQL/signatures, new protected schema ownership and migration strategy, credential custody, generation mapping, launch provenance, immutable publication receipt/status storage, lock/time budgets and actual isolated PostgreSQL/LINUX acceptance. No current source/runtime/preview capability changes.
