# The Circadian Rhythm Hospital — HMS living project reference

Document version: 1.2.0 | Updated: 23 October 2026, Asia/Calcutta
Repository: https://github.com/prarit0097/HMS-MANAGEMENT
Current state: **OWNER-AUTHORISED IMPLEMENTATION, PHASE A IN PROGRESS. No production service exists.** See the implementation ledger for verified versus in-progress work.

## 1. Read this first

This is the maintained source of truth for the product, approved decisions, architecture, security rules, implementation status and change history. Read it together with [plan.md](plan.md) before changing the project. [AGENTS.md](AGENTS.md) makes the maintenance workflow discoverable to developers and coding agents. Detailed research is indexed in [the consolidated baseline](docs/research/HMS_CONSOLIDATED_RESEARCH_BASELINE.md).

Every coherent project change, including a documentation/configuration/test-only change, must update this file in the same commit. Update the relevant detailed section and add a dated change record; a vague changelog entry alone is insufficient. Record added/changed/removed behaviour, affected pages/APIs/data/permissions, migrations, tests actually executed, operational impact and unresolved issues. Never claim a planned feature is implemented.

User instructions override proposed defaults. The latest owner clarification overrides older research: capacity can expand; call-center details are future scope; rented premises and fulfilment of regulatory/building norms are hospital-managed and are not development blockers.

## 2. What this application is and why it exists

A cloud-based hospital management system for The Circadian Rhythm Hospital, currently operating without software in Faridabad, Haryana. It connects reception, doctors, Ayurveda/Panchakarma therapy, inpatient care, pharmacy, accounts, insurance and central administration around the same authorised patient journey.

It exists to reduce repeated entry, missing handoffs, disputed stock/bills, incomplete care records and lost follow-up context. An approved clinical order should lead to departmental work, actual delivery and traceable financial events. Prescribed, scheduled, performed, dispensed, administered, invoiced and paid are deliberately different records.

Future branches should share appropriate patient identity while preserving branch-specific encounters, inventory, tariffs, permissions and financial records. Future call-center integration should let authorised agents follow referred-patient outcomes and relevant sales/collection information.

## 3. Established requirements and boundaries

| Requirement | Current decision/status |
|---|---|
| Hospital | Faridabad; already operational; no existing hospital software |
| Clinical orientation | Ayurveda/Panchakarma with OPD and IPD; other disciplines not yet specified |
| Scale inputs | 555+ OPD/day, 30+ admissions/day, 1,000,000+ enquiries/month |
| Capacity | 100-bed reference with room for expansion; never hard-code a 100-bed ceiling |
| Accommodation | General, semi-private, private, private luxury and villa |
| Prescriptions | Typed, uploaded, voice draft; doctor approval before actionable extracted orders |
| Treatment | Medicine-only, therapy-only or both |
| Coverage | Insurance/government/employer declaration, verified limits, AYUSH status, cashless/reimbursement |
| Cloud | Authorised remote access subject to authentication, permissions and configured network policy |
| Master admin | A panel above operational portals, governing configuration, access, security and operations |
| IP policies | Allowlist, blocklist and whitelist-only modes; exact IPv4/IPv6 and CIDR support |
| Backups/data movement | Full backups, portal-scoped logical backups, controlled restore, import/export |
| MCP | Secure capability-scoped connectivity for compatible ChatGPT/Claude/other clients |
| Call center | Integration-friendly foundation now; actual call-center integration deferred |
| Branches | Data model and permission scope prepared now; rollout timing unspecified |
| Development method | Planning -> multiple pre-code checks/tests -> coding -> post-code verification |
| Repository workflow | Update documentation, verify, commit and push every completed change set |
| Required skills | Superpowers and UI/UX Pro Max throughout applicable work |
| End-user experience | Simple, professional, consistent frontend with clear next actions; minimise confusion and verify with real staff task walkthroughs |
| API-first — highest architectural priority | Every application capability has an authenticated, documented, versioned backend API contract; all frontends/integrations use this contract and the same business/permission rules |

Baseline confirmed requirements C-01–C-20 remain covered in the research baseline and plan. Current owner requirements O-01–O-13 are mapped in plan.md; O-12/O-13 make simple professional UX and API-first architecture explicit non-negotiable priorities.

Premises rent is outside this product. Patient accommodation tariffs remain configurable hospital business data. No registration investigation is required to proceed with software planning. Automated clinical advice, autonomous prescriptions and unrestricted database/command execution through AI are not defined product capabilities.

## 4. How this differs from a generic HMS or CRM

These are intended combined capabilities, not claims of unique inventions or proof that competitors lack them:

- Ayurveda/Panchakarma courses, preparation, resources, session performance and materials connected with OPD/IPD and billing.
- Configurable shared/exclusive rooms and villas with physical bed integrity and expandable capacity.
- Distinct medicine prescription, pharmacy supply and nursing administration.
- Insurance visibility throughout the journey, with verification/authorisation/settlement kept distinct.
- Future referral-to-care-to-collection visibility for agents without automatically disclosing the clinical chart.
- Organisation/branch scope built into identity, data access and operations.
- One master-admin control plane for security policies, IP rules, audit, backups, imports/exports and MCP clients.
- MCP tools reuse the same authorisation/business rules as ordinary users; AI is an additional client, not a privileged bypass.

## 5. Technical direction and actual implementation

| Layer | Planned choice | Actual state |
|---|---|---|
| Backend language/framework | Python + Django | Not scaffolded |
| HTTP API | Django REST Framework; versioned `/api/v1/` | Not implemented |
| Frontend | React + TypeScript + Vite | Not scaffolded |
| Database | PostgreSQL | Not provisioned |
| Background work | Celery; durable broker, proposed RabbitMQ | Not configured |
| Disposable cache/rate limit | Redis where justified | Not configured |
| Files | Private cloud object storage, encrypted and access-controlled | Not provisioned |
| Runtime | Containerised services; production Linux; local Windows development supported | Not configured |
| Remote MCP | Authenticated HTTP endpoint with supported MCP transport/version | Not implemented |
| Cloud provider | Not selected; architecture must not assume public database/storage | No account/resources created |
| CI/testing | Proposed pytest, frontend component tests, Playwright, dependency/secret/security checks | No application checks exist yet |

The language direction is the current planning baseline from previous recommendations, not proof of delivered capacity. Supported mutually compatible versions will be pinned and recorded before scaffolding. Docker Compose is a proposed local integration tool, not an automatic production deployment architecture.

Why this direction: Django/DRF suit connected records, permissions and APIs; React/TypeScript suit interactive staff workflows; PostgreSQL supports relational integrity and transactions. Higher traffic requires measurements, correct indexes, bounded queries, connection budgets and worker isolation, not an automatic change of language.

## 6. Planned system structure

Start with a modular transactional core. Separate clinical, admission, therapy, stock, finance, coverage, identity, audit and platform responsibilities. Background ingestion/reporting must not consume all capacity needed for care. External systems use APIs/events, not direct writes into clinical tables.

**API-first is mandatory across the whole product.** Define and version OpenAPI contracts before implementing endpoints/pages: request/response schemas, authentication, permissions, errors, filtering/pagination, concurrency/idempotency and asynchronous job/download flows. Every user-visible capability, including master-admin, security, IP policies, backups, imports/exports and reporting, must be operable through its authorised API rather than depend on a hidden UI-only backend path. The browser is an API client; it never accesses the database or decides authoritative billing/clinical permissions. Important calculations and state transitions live in backend services.

MCP is a protocol adapter to those same capability contracts, permissions and services. It may reuse services in-process; API-first does not require wasteful internal HTTP loopbacks. Background jobs reuse those services under explicit service identities. No adapter, Django admin page or import may introduce an alternative privileged mutation path. Maintain API compatibility/versioning and test each released capability through its API independently of the frontend.

Browser / compatible MCP client -> cloud edge -> trusted proxy -> authenticated application -> authorised business services -> PostgreSQL/private files. Background jobs consume durable work with retries, deduplication and reconciliation. Private database/cache/broker endpoints are never generally internet-accessible.

Master admin is a permissioned application role, not a PostgreSQL superuser account exposed through a webpage. Clinical signing still requires an authorised clinician. Infrastructure administration and patient-chart access are separate privileges.

Planned repository ownership and function interfaces are in plan.md. Any changed implementation path/interface must be reflected there and here in the same change.

## 7. Identity, data and branch principles

- Organisation-wide patient UUID/UHID, source-qualified legacy/external identifiers and optional branch-local registration identifiers.
- Patient, contact, enquiry, lead, referral, encounter and admission are distinct entities. Shared phone numbers do not imply one person.
- Branch-scoped beds, stock, cashier shifts, tariffs and encounters; explicit sharing rules for identity and clinical history.
- UUID internal identifiers; human-readable document numbers separately configured and unique in their defined entity/series scope.
- Store timestamps in UTC, display Asia/Calcutta by default; preserve occurrence time and entry time.
- Represent money with fixed-precision decimals, explicit currency and rounding rules; never binary floating point for money.
- Represent quantities with explicit units/conversions, batch and location where relevant.
- Version signed notes, prescriptions, tariffs, packages, coverage snapshots and document templates.
- Preserve original financial/stock/clinical events; use authorised correction/reversal rather than silent deletion.
- Expand capacity through configuration. Reserve/occupy/block/clean states and exclusive-allocation restrictions must reconcile without false patient counts.
- Use database constraints and transaction/resource locking for concurrent allocation/dispensing/payment changes. UI checks alone are insufficient.

## 8. Portals and operational flows

| Portal | Responsibility |
|---|---|
| Master admin | Organisation/branch settings, users, grants, security/IP, audit, integrations, backups and jobs |
| Reception/admission | Patient search/intake, appointments/queue, therapy coordination, reservations and admissions |
| Doctor | Review history/vitals, document consultation/rounds, approve orders and discharge documents |
| Therapy | Resource calendar, readiness, actual session performance/materials, observations and escalation |
| Nursing | Ward census, due care/medication, administration, handover and discharge checklist |
| Pharmacy | Worklists, batch/location stock, actual issue, purchases/receipts and returns |
| Accounts | Estimates, package entitlements, running charges, deposits, invoices, collections/refunds and closing |
| Insurance desk | Eligibility evidence, pre-auth/query/enhancement, claim lines, deductions and settlement |
| Housekeeping/maintenance | Cleaning tasks, restrictions and readiness confirmation |
| Management | Authorised operational/financial reporting with defined metrics and drill-down |
| CRM/agent view | Future integration projection; current work defines IDs/events/permissions only |

OPD: identify -> check-in -> consultation -> approved orders -> worklists -> actual delivery -> charge/collection -> follow-up.

IPD: admission -> allocation -> nursing handover -> ongoing care -> running charges -> clinical/operational/financial discharge steps -> physical exit -> cleaning -> ready. Claims can remain open after discharge.

Therapy: order -> course -> resource booking -> readiness -> actual performance/stopped session -> materials/observations -> charge/package consumption -> review.

Finance: estimate, advance, charge, invoice, receipt, allocation, credit/refund and payer settlement are separate. A claim rejection does not automatically make the patient liable.

## 9. Security requirements and release policy

Security is a release-blocking engineering priority. No system can honestly guarantee that a breach is impossible; instead define verified controls, independent review, monitoring, patching, recovery and incident response. Never represent planned controls as deployed protection.

Required design controls:

1. Individual logins; MFA for master admins, security/backup operators and remote privileged access; no shared production accounts.
2. Deny-by-default permissions on every UI/API/MCP/file operation, scoped by role, organisation, branch, care relationship and data category as appropriate.
3. Separate view, create, amend, sign, cancel, discount, refund, export, restore and security-policy rights. Master-admin status does not automatically authorise clinical signing or disclosure.
4. Secure browser sessions in HttpOnly/Secure cookies, CSRF protection, bounded lifetimes, revocation and re-authentication for high-impact actions; OAuth token flows for remote MCP as specified.
5. TLS, protected encryption keys, private encrypted storage/backups and managed secrets; no credentials in Git/logs/browser local storage.
6. Validation, parameterised database access, safe HTML/output, upload type/signature/size controls, malware scanning/quarantine, download authorisation, SSRF/egress controls and resource limits.
7. Rate limits and abuse protection, dependency pinning/scanning, secret detection, secure cloud configuration and least-privilege service identities.
8. Audits for sensitive access, changes, grants, exports, restores, IP/MCP policy changes and integration calls; restricted immutable/tamper-evident retention where feasible. Avoid copying raw sensitive payloads/tokens into logs.
9. Automated permission/branch isolation tests, concurrent integrity tests, restore drills and security review. No unresolved critical/high findings for release without explicit risk disposition; never waive a known access bypass or data-loss defect.
10. Named incident response ownership, alerting, patch/rotation/recovery runbooks and tested support access.

The production exposure, hosting, legal retention and incident obligations are configured with the hospital; premises compliance remains outside this software assignment.

## 10. IP allowlist / blocklist / whitelist-only policy

Cloud hosting and IP restriction are compatible: users can connect remotely only when the effective network and identity policy allows it.

Planned modes: `allow_authenticated` (all network locations still require auth; blocklist applies) and `allowlist_only` (exact/CIDR match also required). Blocklist takes precedence over allowlist. Organisation policy is the ceiling; branch/portal/user policies can narrow it, never widen it. Effective access is the intersection of applicable allow rules minus applicable denies.

Support IPv4/IPv6 canonicalisation, exact addresses, CIDR, enabled flag, purpose, owner, expiry and change history. Resolve client IP only through an explicitly trusted proxy chain, overwrite untrusted forwarded headers and prevent direct-origin bypass. Re-evaluate on requests including long-lived session reconnects; downloaded private assets and API routes must not escape policy enforcement.

**Interpretation of the owner's 'app IP' request:** provide 'allow my verified current IP' for a master admin to add their current observed public address, and allow explicitly configured office/VPN egress addresses. Do not automatically whitelist every visitor. If the owner meant the cloud server's IP, distinguish it from the client's public egress address before applying a rule; it normally cannot identify a remote staff member.

Policy changes need preview, current-session validation, step-up MFA, audit and timed rollback/confirmation. A tested out-of-band recovery process uses cloud/VPN/identity controls; it is not a hidden unauthenticated URL. Never bypass a deny rule by silently adding a recovery exception.

Remote ChatGPT/Claude client egress may differ from the user's browser IP. Configure an explicit approved private gateway or narrow integration policy under the organisation's network ceiling. If a compatible network path cannot be established, MCP remains blocked; never silently disable whitelist-only mode to make a connector work.

## 11. MCP connectivity

Provide a secure remote MCP server for compatible clients, with explicit registration/connection, OAuth authorisation, user delegation, resource/audience validation, short-lived tokens, revocation and scoped tools. Pin supported protocol/SDK versions after compatibility checks. A client brand name alone is not proof that it can connect.

MCP uses the same business-service functions as the UI/API. Every call evaluates actor, scopes, branch/data permissions, IP policy and tool limits. Do not expose generic SQL, shell execution, arbitrary URLs or unrestricted file access.

Initial tool catalogue is in plan.md: bounded patient search/summary, appointments, bed availability, invoices/payments summaries where authorised, draft notes and operational tasks. Read operations still require permission and bounded results. Writes require idempotency, validation and audit. High-impact actions require a server-recorded preview/confirmation tied to actor, payload hash, expiry and state version; client-side confirmation hints alone are insufficient.

Clinical approval remains with authorised clinicians. Financial refunds, restores, access/IP changes and bulk exports must not be generic autonomous tools; start with UI-only controlled flows or narrowly defined approval workflows. Treat prompts, documents and tool results as untrusted data and prevent them from granting authority.

Export/AI disclosure controls and hospital-approved data-sharing policy determine what may leave the application. Log tool metadata/outcomes with redaction rather than full clinical payloads by default. MCP enablement must have per-client/per-tool kill switches.

## 12. Full backups, portal backups, restore, import/export

**Full backup:** consistent PostgreSQL backup plus required protected files, manifests, schema/app versions and recoverable configuration/key references. Use continuous recovery where selected, encryption, retention, access isolation and restore drills. Secrets/key material follow a separate secure recovery process, never an ordinary downloadable archive.

**Portal-wise backup:** a versioned logical module snapshot with explicit organisation/branch/date scope and dependency manifest. Portals share patients, orders and charges; a portal backup is not assumed to be an independently restorable database. Referenced shared records are included or resolved through verified references according to a documented ownership policy. Restricted clinical fields must not leak through dependency inclusion.

**Restore:** full restoration first into an isolated environment; verify checksums, versions, dependencies, counts and access before an approved maintenance-window cutover. Portal restores use staging, schema/dependency checks, ID mapping, collision/conflict preview and controlled reconciliation. Reject incompatible/incomplete archives; do not overwrite live shared data blindly. Require step-up privilege, audit and a pre-restore recovery point.

**Import:** downloadable versioned templates, sandbox/staging, file validation/scan, dry-run, row errors, duplicate detection, branch/unit/date mapping, authorised approval and atomic or explicitly chunked resumable commit. Raw imports cannot directly sign clinical orders, overwrite final invoices or bypass rules.

**Export:** scoped fields/rows and purpose, masking where configured, background job limits, spreadsheet formula-injection protection, audited expiring authorisation-checked downloads and deletion/retention policy. A data export is not automatically a recoverable backup.

## 13. UI/UX direction

**Owner priority: the end-user frontend must be simple and professional.** Each role sees its own relevant work and a clear next action. Use familiar hospital terms, consistent navigation/buttons, readable spacing and restrained styling. Show essential fields first and optional detail on demand; keep patient identity, clinical warnings, financial consequences and confirmations visible when needed. Do not simplify by hiding safety-critical information.

Use plain-language labels/help/errors and consistent status names; do not show framework, API or infrastructure jargon to hospital users unless it helps their task. Preserve context across steps and explain what succeeded, what needs correction and what comes next. Avoid competing primary actions and decorative complexity. Run representative reception/doctor/pharmacy/accounts staff through core journeys before release, record confusion/wrong turns and fix them; simplicity is a usability acceptance criterion, not a colour/theme choice or an untestable guarantee.

Use UI/UX Pro Max for relevant design/review. Its initial health query produced a marketing landing-page pattern and high-risk neumorphism, which were rejected for this staff application. A narrower enterprise query returned a suitable minimal/high-contrast direction; its marketing layout was still not adopted. No generated palette/font is an approved brand decision.

Plan functional clinical workspaces: consistent navigation, visible branch/user context, strong patient identification, focused task panels, readable tables, progressive forms, keyboard access, visible focus, error summaries, empty/loading/stale/offline/conflict/denied states, and motion reduction. Preserve the owner's green booked/occupied and red available bed colours with explicit text/icon differences; do not reuse those meanings blindly for generic success/error states. Plan responsive use and print layouts, with actual validation before release.

## 14. Development and documentation workflow

Owner authorised a five-specialist team to begin implementation after reading these documents. Execute specialist work in batches within the actual concurrency limit (currently three children plus coordinator). Coordinator alone integrates/commits/pushes. Current first-slice contracts and preflight rulings are in [Phase A contract](docs/implementation/phase-a-contract.md); progress is in [implementation ledger](docs/implementation/ledger.md). Work occurs on `feat/hms-foundation` in the current checkout, not directly on main. No separate worktree was requested.

### Usage stop and continuation rule

At start and bounded work boundaries inspect authenticated Codex usage via get_usage_limits; check all applicable windows and stop new implementation/assignments when any remaining percentage is <=10. Ask running agents to checkpoint, preserve exact completed/pending/test/Git evidence here and in the ledger, commit/push safely, and record a UTC deadline330minutes after the checkpoint. Never extend an active deadline on repeated checks or consume reset credits automatically. Resume only after deadline and recovered usage; a low weekly window can keep work stopped longer.

Native Codex heartbeat `continue-hms-after-usage-cooldown` is active; it is not an unattended cloud worker. The Windows PC, Codex app and repository access must remain available; exact-time wake is best effort. [Usage checkpoint](docs/operations/USAGE-CHECKPOINT.md) is the continuation record. [usage_guard.py](scripts/usage_guard.py) evaluates tool-supplied JSON without credential scraping; [Check-Usage.ps1](scripts/Check-Usage.ps1) is its Windows wrapper. Exit0 permits work,75 means checkpoint/wait,76 means unavailable/untrusted usage. Ignore `.local/` snapshots; do not store full account data in Git.

Required sequence for each feature/change:

1. Update/complete plan: pages, fields, actions, permissions, states, interfaces, data, migration, security threats, failure cases and tests.
2. Multiple pre-code checks: requirement/permission review, scenario walkthrough, threat/abuse review, test-case/fixture design; then write tests and confirm expected failure where executable. Runtime tests cannot pass before implementation exists.
3. Implement the smallest coherent change; use Superpowers TDD/debugging/planning/review skills as applicable.
4. Run relevant unit, API, integration, UI, security/access/concurrency checks; fix failures; record actual evidence. Expand performance/recovery checks at their planned milestones.
5. Update HMS.md and plan.md in the same change, including status, exact files/contracts, decisions and test results.
6. Review the staged diff and check for secrets, patient data, unrelated files and unsafe generated artifacts.
7. Commit and push the completed change set to the configured GitHub repository; verify remote commit SHA. Never force-push or erase remote work to satisfy this rule.

'Every change' means each completed, coherent, verified change set, not every keystroke or broken intermediate edit. If push fails, preserve the local commit, report the exact failure and retry safely after inspecting state; do not claim upload succeeded.

Use required skills at these sources: [Superpowers](https://github.com/obra/superpowers), [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill). These skills are installed in the current Codex environment; other developers must install/use them in their own environment. Repository rules and user instructions remain authoritative.

## 15. Repository, cloud and release policy

The specified GitHub repo was verified empty and public at initial preparation; connected account has push permission. Public source control must never contain patient/lead data, production dumps/backups, call recordings, credentials, connection strings or private environment files. Synthetic data only.

Cloud production is separate from GitHub publication. No cloud provider, domain, paid resource or production deployment is created by these documents. Plan separate development, staging and production identities/storage; production data must not enter ordinary preview/test environments. Releases require gated deployment, migrations, health checks, rollback and monitoring. Record actual environments and URLs here when they exist.

## 16. Implementation inventory and current verification

| Item | State |
|---|---|
| Requirements/research | Original baseline plus consolidated research and addenda exist |
| HMS.md / plan.md | Initial documents reviewed and published; owner/design readiness gate still required before product implementation |
| Agent workflow | AGENTS.md and safe ignore rules prepared |
| Product pages/APIs/models/MCP | Phase A backend/frontend/security under active implementation; no runtime completion claimed in this checkpoint |
| Unit/integration/UI/security/load/restore tests | Usage guard8/8 passed RED->GREEN; product agents report their own results before integration; load/restore/production tests remain pending |
| Documentation checks | Local links, C-01–C-20/O-01–O-11 coverage, 92 unique page IDs, secret-pattern scan and baseline-copy hash passed. New files pass staged whitespace checks; five intentional original Markdown hard breaks preserved |
| GitHub sync | Initial commit `17df5ef52750cfb55ad9d146dbeba1d9d4820699` verified against remote main; follow-up publication evidence tracked in Git history/handoff |
| Cloud/production | Not deployed |

Current detailed business parameters (rent cycles, package/refund rules, payer tariffs, clinical forms) are configuration/spec decisions, not reasons to investigate rented premises. Future call-center product questions stay deferred. Detailed uncertainties, design gates and page catalogue live in plan.md.

## 17. Change record format

For every change add: ID/date; request and reason; changed behaviour/files/pages/contracts/data/permissions; migrations/recovery impact; tests actually executed and results; outstanding risks/decisions; remote publication reference or verifiable commit subject. Do not put a commit's own SHA into itself; Git history/handoff supplies the final SHA.

### CHG-0001 — 23 October 2026 — Initial project reference and implementation planning

- Request: create HMS.md and plan.md; enforce planning/testing/coding, security, MCP, cloud, IP policy, backups/import/export, master admin and continuous GitHub documentation.
- Files: HMS.md, plan.md, AGENTS.md, .gitignore, existing docs/research/*.md.
- Behaviour: documentation only; no runtime feature or migration. Captures original C-01–C-20 and latest O-01–O-11.
- Design decisions: Django/DRF, React/TypeScript/Vite and PostgreSQL planning direction; bounded MCP; shared-data-aware backups; trusted-proxy-aware IP enforcement.
- Verification: initial local-link/owner-coverage/page-ID/secret-pattern checks passed; original baseline copy matches. Independent read-only review found one Important payer-summary traceability gap and two Minor references; all fixed and reviewer verified no remaining Important/Critical documentation findings. Staged diff and remote SHA verified in publication handoff. No product tests executed.
- Operational impact: no deployed service or patient-data change. Product implementation awaits the planning gate in plan.md.

### CHG-0002 — 23 October 2026 — Record reviewed publication and verification evidence

- Request/reason: keep the living documents accurate after the initial GitHub publication.
- Files: HMS.md and plan.md; status/evidence updates only, no application behaviour, API, schema, permission or migration change.
- Evidence: initial local/remote main SHA both `17df5ef52750cfb55ad9d146dbeba1d9d4820699`; clean working tree observed after that push. Seven Markdown files checked, no broken local links, all 20 baseline and 11 current owner IDs mapped, 92 unique page IDs, no targeted secret-pattern matches. Original downloaded baseline and local copy SHA-256 match. Five original Markdown hard breaks deliberately retained; other staged whitespace checks pass.
- Review: one independent read-only reviewer; identified C-20 payer-strip coverage and reference corrections were fixed and verified. This evidence is documentation verification, not runtime security/capacity certification.
- Publication: commit subject `docs: record verified initial publication and review evidence`; verify resulting remote SHA in handoff. Implementation/design gate remains open, no product tests/build/deployment performed.

### CHG-0003 — 23 October 2026 — Make simple professional UX and API-first architecture mandatory

- Owner request: prevent end-user confusion and make the entire application API-based as a top priority.
- Files: HMS.md, plan.md and AGENTS.md. Added O-12/O-13, API-contract-first/OpenAPI and adapter parity rules, plain-language role-focused UX and staff-usability acceptance checks.
- Scope: every portal, master-admin, security/IP, dataops, reporting and compatible MCP adapter; no hidden UI-only workflows or frontend-authoritative business rules. Internal service reuse is permitted without redundant HTTP calls.
- Tests/impact: documentation coverage/link/diff checks at commit; new API-contract/parity and staff-task acceptance tests are planned, not executed. No runtime, schema, permission configuration, migration or deployment changed.
- Publication: commit subject `docs: require simple professional UX and API-first architecture`; remote SHA verified at handoff. Product development remains behind the existing planning gate.

### CHG-0004 — 23 October 2026 — Start authorised team and usage-aware execution

- Owner authorised implementation using five specialist agents and a stop-at10%-remaining / resume-after330minutes rule. First runtime slice is frozen in docs/implementation/phase-a-contract.md; actual call-center integration remains deferred.
- Files: usage guard/Windows wrapper/tests, .gitignore scratch exclusions, AGENTS.md, HMS.md, plan.md, implementation ledger/contract and usage checkpoint. No unrelated in-progress backend/frontend files included in this change set.
- Verification: eight usage-guard behaviour tests initially failed because implementation was absent, then all eight passed; includes exact threshold, weekly limit, missing/nonfinite data, preserved cooldown and recovered restart. No app-security/load/capacity claim.
- Scheduling: native heartbeat created successfully, id continue-hms-after-usage-cooldown. Initial snapshot66%primary/65%weekly remaining; latest boundary52%primary/63%weekly remaining, so no cooldown started. No reset credit used.
- Publication: commit subject `build: start team execution with tested usage checkpoint guard`; current branch feat/hms-foundation. Subsequent agent work is uncommitted until integrated/tested/documented.

## 18. Technical references

- [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html), [row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), [recovery](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [MCP authorisation](https://modelcontextprotocol.io/specification/latest/basic/authorization), [MCP security](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices)
- [OWASP authorisation guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

References guide implementation; they do not prove this unimplemented application meets any standard.
