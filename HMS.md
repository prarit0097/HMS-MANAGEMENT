# The Circadian Rhythm Hospital — HMS living project reference

Document version: 1.13.2 | Updated: 24 October 2026, Asia/Calcutta
Repository: https://github.com/prarit0097/HMS-MANAGEMENT
Current state: **ACTIVE — scheduled resume after elapsed cooldown.** Scheduled resume2026-10-24T11:07:26UTC after saved11:06:20UTC deadline elapsed. Authenticated primary100%/weekly55%remaining at entry; subsequent guardcontinue minimum54%. No owner waiver or reset credit needed. Historical05:36stop preserved; no active cooldown. Exactd33937f CI40067046203success decoded520PG/168subtests34.29s,115frontend/typecheck/build,19root/schema/docs; source7252345CI40066986031cancelled by laterpush, never claimedpassed. Resume exactGETtime boundary, independentUIreview and edgeisolation/cache design; no repeateddeployment.

Root final frontend115/8files58.52s, typecheck/build24modules190ms passed. Root actualPG520/168subtests41.80s/check0/nodrift; testDBabsent0/appCREATEDB=f/previewactive independently confirmed. Root19projecttests10.171s, schema/map/link checks passed. Seven network operations have source implementations, explicit pending acceptance; no deployment. First resume task is exact GET server-time/snapshot deadline regression, remaining concurrency/fresh review, frontend independent review/browser and edge isolated-PG/no304 design amendment. All source stays recoverable on feat/hms-foundation; fresh CI and remote SHA recorded at publication.

## Current network source checkpoint — acceptance pending

Network B2/C source exists, acceptance incomplete: environment ceiling AND durable overlay, explicit owner/master/OS operator/fresh MFA, six strict management APIs and session-free private probe, fixed preview/rollback transactions and typed OS operations are implemented. Current-user capability and effective deployment summary are wired. OpenAPI/page actions now distinguish46 source-implemented operations from release acceptance; the seven network operations carry explicit pending-security-ui-edge-acceptance. No live operator/owner/policy/schema or runtime deployment changed.

Root actual PostgreSQL frozen run:520 passed/168subtests41.80s, including12 new concurrency cases; Django check0/no migration drift. First run516passed/1failed39.23s: test reused existing trusted-proxy setting so no actual drift; corrected to assert a genuinely different fingerprint, without weakening production enforcement. Local backend492passed/28explicitPG-indexskips/168subtests43.37s. Reviewer69focused passes fixed mixed-owner GET, summary state short-circuit and unsupportedOPTIONS; independent overflow probe led2RED->503/no-write2GREEN. Final fixes lack complete fresh source re-review. Known read response timing concern: server_time selected after coherent snapshot may cross rollback; add exact RED then coherent projection fix before acceptance. Broader staff-service/operator/owner-transfer/activation-event race cases remain.

Frontend source implements memory drafts, preview/apply/keep/restore, permission navigation, deadline/conflict/unknown-write gates and pinned history. Valid-JSON malformed envelopes reproduced17RED plus enum-array regression; local guards prevent crashes/false success. Specialist full115 tests (72 existing+43 network), typecheck/build pass; root rerun recorded separately. Independent frontend review and actual synthetic browser/staff walkthrough are pending.

Edge source/harness is WIP NOT DEPLOYABLE. Seven source/safety tests pass; actual run failed at private PostgreSQL HBA rejection before Nginx/Gunicorn/HTTP launch. No shared HBA change made. Exact disposable DB/private config removed after zero-connection check;18185/18186 listeners absent and old preview active. Candidate-only Gunicorn26.2.0 installed in validation venv, not live venv. Independent Nginx1.24 source inspection confirms If-None-Match:* can still produce304 despite etag off; strict no304 acceptance is retained. Future explicit isolated-PG and conditional-cache design amendment needed before actual edge matrix. No runtime edge claim.

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

### External HMS reference reviewed —24October2026

[ICTHospital source comparison](docs/research/2026-10-24-icthospital-comparison.md) pins commit e506dfb553f7d146a6d0cddc136ffd5b6c9bdb09 and maps useful workflows to this project. Keep Django/DRF, React/TypeScript and PostgreSQL; most registration/appointment/admission/prescription/dispensing/part-payment concepts already exist in our design. No foreign code/assets/dependencies/schema were adopted. Root GPLv3 versus Composer MIT metadata remains unresolved for any future material copying.

A dedicated laboratory lifecycle is an explicitly deferred, unapproved extension candidate: current test alerts do not implement ordering/specimens/verified partial results. Reporting design will independently define source-linked compatible-unit supply, invoice-wise receivable ageing and census/bed-time occupancy with historical capacity. Preserve historical catalogue labels/prices alongside stable identities and immutable signed/final versions. Outbound reminders remain unconfigured pending consent, provider/cost, disclosure and delivery contracts; actual call-center integration stays deferred. These are planning refinements, no new page ID/API/permission/migration or delivered feature.

Evidence: two source specialists plus fresh independent documentation review; three Minor citation/length-of-stay clarifications corrected. Actual upstream CI39252436524 has160tests/474assertions passing in SQLite but dependency audit failing3advisories/2packages; no local upstream execution or production readiness claim. Our own doc-only8b70d6eCI40031346794 observed successful; application-source301/72/19 evidence remains historical and livepreview separate.

## 5. Technical direction and actual implementation

| Layer | Planned choice | Actual state |
|---|---|---|
| Backend language/framework | Python + Django5.2.18 | Phase A implemented under backend/hms and backend/apps/core; deployed only as restricted preview, not ready for real hospital data |
| HTTP API | Django REST Framework3.16.1; versioned `/api/v1/` | Session/CSRF/scoped operational+master+staff APIs and9self-security operations implemented (39total source operations including3read-only history operations); bounded verification, deployment separate |
| Frontend | React19.3.1 + TypeScript7.0.2 + Vite8.3.5 | API-backed workspace, reception reliability, branch/bed/staff configuration, Account security/login MFA and lazy administration/self-security history; selected-branch controls remain scoped |
| Database | PostgreSQL for production; SQLite for local synthetic development | Local SQLite synthetic development; isolated TLS PostgreSQL17.11 deployed and48tests/25subtests passed |
| Background work | Celery; durable broker, proposed RabbitMQ | Not configured |
| Disposable cache/rate limit | Redis where justified | Not configured |
| IP policy primitives | Framework-independent trusted-proxy resolver and allow/deny evaluator | Resolver/evaluator and request middleware implemented; trusted loopback proxy configured; admin policy UI/recovery still planned |
| Files | Private cloud object storage, encrypted and access-controlled | Not provisioned |
| Runtime | Containerised services; production Linux; local Windows development supported | Hostinger preview runs dedicated Gunicorn/systemd/static Nginx and private containerised PostgreSQL; development Compose remains separate |
| Remote MCP | Authenticated HTTP endpoint with supported MCP transport/version | Not implemented |
| Cloud provider | Hostinger existing VPS selected for this authenticated preview; private database, future file storage unprovisioned | Dedicated /opt/hms preview resources created on owner existing VPS |
| CI/testing | pytest, Vitest/component tests and contract/docs checks; remaining e2e/security/load gates | Current audit source actual PostgreSQL301passed/25subtests/0skips16.14s, frontend72passed/typecheck/build; system/migration checks clean and bounded source review approved. Audit16b6ca3actualGitHubCI40002404443success301backend/25subtests15.69s,72frontend/typecheck/build,19root/OpenAPI/Compose/docs decoded and verified; deployedpreview separate. Preview deployment remains separate |

The language direction is the current planning baseline from previous recommendations, not proof of delivered capacity. Supported mutually compatible versions will be pinned and recorded before scaffolding. Docker Compose is a proposed local integration tool, not an automatic production deployment architecture.

Why this direction: Django/DRF suit connected records, permissions and APIs; React/TypeScript suit interactive staff workflows; PostgreSQL supports relational integrity and transactions. Higher traffic requires measurements, correct indexes, bounded queries, connection budgets and worker isolation, not an automatic change of language.

## 6. Planned system structure

Start with a modular transactional core. Separate clinical, admission, therapy, stock, finance, coverage, identity, audit and platform responsibilities. Background ingestion/reporting must not consume all capacity needed for care. External systems use APIs/events, not direct writes into clinical tables.

**API-first is mandatory across the whole product.** Define and version OpenAPI contracts before implementing endpoints/pages: request/response schemas, authentication, permissions, errors, filtering/pagination, concurrency/idempotency and asynchronous job/download flows. Every user-visible capability, including master-admin, security, IP policies, backups, imports/exports and reporting, must be operable through its authorised API rather than depend on a hidden UI-only backend path. The browser is an API client; it never accesses the database or decides authoritative billing/clinical permissions. Important calculations and state transitions live in backend services.

MCP is a protocol adapter to those same capability contracts, permissions and services. It may reuse services in-process; API-first does not require wasteful internal HTTP loopbacks. Background jobs reuse those services under explicit service identities. No adapter, Django admin page or import may introduce an alternative privileged mutation path. Maintain API compatibility/versioning and test each released capability through its API independently of the frontend.

Browser / compatible MCP client -> cloud edge -> trusted proxy -> authenticated application -> authorised business services -> PostgreSQL/private files. Background jobs consume durable work with retries, deduplication and reconciliation. Private database/cache/broker endpoints are never generally internet-accessible.

Master admin is a permissioned application role, not a PostgreSQL superuser account exposed through a webpage. Clinical signing still requires an authorised clinician. Infrastructure administration and patient-chart access are separate privileges.

Planned repository ownership and function interfaces are in plan.md. Any changed implementation path/interface must be reflected there and here in the same change.

Phase A implementation-path ruling: this bounded slice uses `backend/hms/` for configuration and `backend/apps/core/` for initial relational models, serializers, scoped services and API handlers. Security primitives are in `backend/apps/security/`. This differs from the future per-domain package map in plan.md; future clinical/finance/dataops modules must be split deliberately with migrations/contracts, not duplicated or assumed already present. Patient identity currently has a home-branch scope; full cross-branch chart/identity sharing is not implemented.

Verified bounded source [identity-security contract](docs/implementation/identity-security-contract.md) defines9self-security operations (36source operations now implemented and bounded-source verified), enrolled-login202 challenge and anonymous CSRF logout, encrypted TOTP/recovery codes/epoch revocation and production privileged-write MFA. PyOTP2.10.0/cryptography50.0.2 selected from official package documentation; dependencies installed only local/candidate runtimes. Exact schema/error/state/lock/key/UI acceptance preceded code; current bounded source is verified; full release gates remain; human recovery/WebAuthn/read audit remain release work.

Current source API contract is [OpenAPI v1](docs/api/openapi-v1.yaml), with [page-action map](docs/api/page-actions-v1.json) and [compatibility/security notes](docs/api/README.md). Contract validation is separate from runtime parity. Current deployed47b3618 has no generic create-request idempotency keys; patient/appointment creation retries can duplicate records. Verified source now implements optional per-user/operation UUID Idempotency-Key on three creates, atomic result references with current permission rechecks, and browser stable logical-form keys. Current deployed preview lacks it until updated; legacy calls without optional header retain duplicate risk. Source also implements global bed status filtering, demographic correction UI, versioned appointment rescheduling and paged patient selection. core0002 migration adds a fingerprint/result-only retry ledger; no PII payload copy or automatic expiry.

### Verified scoped staff source

Four organisation-scoped staff APIs and StaffAdministration UI implement create/search/page, branch-role replacement and suspend/restore. platform.staff.manage belongs to active master_admin only; no operational/clinical grant follows. core0004 adds Membership.is_active and unique organisation/user StaffAccessRevision. Existing grants default active; legacy response version0 does not write on GET, new staff version1. CurrentUser adds branch_permissions; operational controls follow selected branch, navigation/admin retain union compatibility. Backend remains authoritative.

Create-only passwords are validated12..128characters and hashed, never returned/audited/stored in browser storage. Initial password distribution and human recovery remain separate gates; bounded MFA is verified below. Self-access edits are denied. Suspension affects only current organisation grants and immediately removes their effective API ceiling; global account_active is readonly and other organisations remain intact. Desired assignments are retained for restore; removed grants are traceably replaced, with no signed-record deletion. Versioned PATCH409 protects against stale edits. Create has no generic replay guarantee; refresh/search after ambiguous save. Assignment request batches1..100 are not database capacity limits; response arrays remain uncapped by that batch bound.

Configuration joins organisation locking and reauthorises after waits, operational row-locked writes and keyed replays refresh scope, and staff snapshots retry version-before/after reads to prevent old roles/new versions. Seven consistency regressions were observed RED then GREEN; mixed-branch API/UI regressions were separately RED then GREEN. Staff-slice PostgreSQL213tests/25subtests passed with temporary database cleanup/CREATEDB revocation, system checks and migration drift clean. Candidate validation did not migrate/redeploy the live preview. Fresh independent review found two Important consistency issues and one Minor response-cap mismatch, all resolved with covering tests/schema correction. Bounded MFA verification follows below; full identity recovery/read audit, live browser/staff acceptance and hospital release remain incomplete.


### Historical identity-security WIP checkpoint — resolved by the verification record below

Backend adds core0005IdentitySecurity/IdentityEnrollment/IdentityChallenge/IdentityBackupCode/IdentityNetworkBudget, identity_security.py services and API adapters, active epoch middleware, stableUser NO KEY UPDATE locks ahead of privileged organisation locks, dedicated PyOTP2.10.0/cryptography50.0.2, shared trusted-IP/account/challenge budgets, purpose/user/device-bound Fernet and hash-only single-use recovery codes. Login202 remains unauthenticated until bound proof; logout explicitly CSRF-protects anonymous/stale cancellation. Source defaults privileged MFA enforcement outside development. No private key provisioned and no live account enrolled/migrated.

Frontend implements second-factor login/cancel, Account security for all full-session users, nine self API flows, local manual enrollment secret, one-time recovery-code acknowledgement, masked passwords, error-secret cleanup and actionable MFA policy guidance without automatic write replay. Existing branch permissions remain. Component tests do not replace authenticated browser/staff acceptance.

Observed RED before code: initial backend9failures; statusPOST405, session rotation, password-login lock race/bounds regressions; frontend initial3failures, recovery ack and confirmation-secret cleanup regressions. First actualPG candidate4failed/230passed/25subtests exposed session rotation and3FK-lock deadlocks. After existing agent fixes NO KEY UPDATE/session rotation, root final frozen candidate236passed/25subtests/0skips17.68s, check0issues/no migration drift; testDB cleaned/CREATEDB revoked. Separate /opt/hms/validation/identity-20261023/venv only, deployed runtime/schema untouched. Frontend64tests/typecheck/build passed. These are bounded source checks, not full identity approval.

Unfinished security gate: privileged services must reevaluate15minute proof age AFTER waiting for organisation locks (identity locks already serialize epoch changes); reproduce RED then fix after cooldown. Fresh independent read-only source pass established no additional Important/Critical defect but was stopped at threshold and gave no full approval. Missing executable coverage: ciphertext swapping, expired/cross-session/consumed enrollment, anonymous verify CSRF, fixed-window/challenge lifetime edges, latest-challenge/profile creation races and full revoke-versus-platform-write PostgreSQL ordering. Current helper factor races alone do not prove full API ordering. Do not deploy/publish as hospital-ready. First resume starts these exact gaps rather than duplicate completed staff/deployment.

### Current bounded identity-security verification

The earlier WIP findings above are historical. Authenticator/recovery/session source now passes actual PostgreSQL259tests/25subtests, coordinator frontend64tests/typecheck/build and bounded independent security review. Existing Account security nine self APIs retain exact OpenAPI0.4 contracts; no new API/schema in this repair. core0005 contains IdentitySecurity, IdentityEnrollment, IdentityChallenge, IdentityBackupCode and IdentityNetworkBudget; dedicated encrypted secrets, full-code salted hashes, trusted-IP/account/challenge counters, single-use factor consumption and session epochs are implemented. Production privileged writes require enrolled/recent MFA as well as normal current grants; ordinary in-flight requests may finish, no universal instantaneous cancellation claim.

Freshness is rechecked after organisation/branch/bed/staff revision lock waits and at transactional audit boundaries so rejected writes roll back. Five tracked expiry regressions were observed RED then GREEN; fresh independent bed-wait probe independently GREEN. Added negative coverage proves ciphertext user/device/purpose binding, expired/cross-session/consumed enrollment, anonymous verify CSRF, fixed five-minute account failure windows, independent five-attempt challenge ceilings and missing-key failure without factor/account-attempt penalties. Eight actual PostgreSQL request races exercise revoke/platform both winners, confirmation versus revoke/disable both winners, and concurrent profile/latest challenge creation. Existing two factor helper races remain covered; all15PG-only cases ran in the259suite. Clock freshness is evaluated at authorisation/transaction boundaries, not guaranteed at post-commit wall-clock time.

Repeated bed-edit test failure was diagnosed as whole-page accessibility lookup across sequential summary/branch/bed loading on Windows. Test now waits Bed inventory and scopes the same button/assertions; no timeout, payload, production behaviour or expected409 retention changed. Root64tests/typecheck/build passed after repair. Local isolated synthetic browser sign-in and Account security page visually verified; no real staff acceptance, credential-change browser flow or live-VPS-browser claim. Preview47b3618/source remain separate; private test keys/SQLite/credentials/screenshot ignored.

Key provisioning/rotation/off-host restoration, human recovery, immutable/read audit and remaining clinical/financial/MCP/dataops product are open release work. No full hospital security certification or breach-proof promise. Operations guide records these distinctions.

### Verified bounded administration history and own security activity

[Audit-history contract](docs/implementation/audit-history-contract.md), OpenAPI0.5 and page map cover3newGEToperations/39implemented source operations. GET platform/organisations/{org}/audit-events/ and /{event}/ require active same-org platform.audit.read (master only) plus current MFA policy; GET auth/security/activity/ returns only the caller's branchless security activity, including when organisation grants are suspended but identity remains active. Master history allows5nonclinical configuration/staff actions only; self8security actions only. Clinical, foreign organisation, null-branch admin and colleague/global events are excluded.

API projections never return raw stored JSON. Typed/action-specific fields, scalar maxima, positive64bit IDs/nonnegative versions (bool rejected), valid UUID/reference handling, same-org branch/target labels and1000assignment-per-snapshot crop with explicit flag protect output. Lists strictly reject unknown/duplicate parameters, use bounded25/default100max pages/offset<=10000 and aware RFC3339 calendar after-inclusive/before-exclusive windows <=90days/default30; future before clipsnow. Returned window is pinned by UI across pages; refresh/filter changes reset it. core0006adds audit_branch_time_id/audit_actor_time_id indexes. GETs create no profile/audit rows; events are not automatically deleted.

AuditHistory.tsx lazily opens named administration history/details and personal security activity. It uses plain labels, branch/action/date filters, India dates, safe Before/After fields, truncation/empty/error/retry states and Account security guidance. No resource/staff lookup scope is silently added. Initial backend18RED, hostile enums2RED, invalid-offset2RED and RFC3339-shape3RED led to fixes; source targeted41passed/1PGskip. Fresh independent reviewer confirmed offset fixes/strictparser and bounded privacy approval. Root actual PostgreSQL301passed/25subtests16.14s/check0/no drift, including real index/EXPLAIN test; testDB removed/CREATEDB revoked, candidate-only schema.

Frontend8new tests pass. An existing staff test timed out once at5000ms under overlapping suites; isolated18passed and root serial72passed26.75s/typecheck/build without timeout/assertion changes. Spacing-only detail-body class then rebuilt/visually checked. Root local synthetic browser verified stale-session logout, password-to-MFA challenge, one-use recovery login, personal activity and scoped history/details; synthetic fixture was pre-enrolled by setup code, so browser enrollment/password-change flow is not claimed. Private fixture/screenshot stay ignored. No full real-staff/live-VPS acceptance, immutable/read-event audit, export, raw IP, retention, human recovery or hospital release claim.

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

The [network-access design proposal](docs/implementation/network-access-design.md) is superseded for execution by the [frozen Task03 contract](docs/implementation/network-access-contract.md). OpenAPI0.6.0/page map catalogues46operations:39existing source operations and7planned network operations (read/preview/activate/confirm/revert/history/private edge probe). Six management APIs require current owner Master AND separately OS-provisioned operator AND unconditional enrolled/recent MFA, including development. Existing getCurrentUser will advertise only derived installation authority; getPlatformSummary effective-mode metadata changes are planned, not yet implemented. No ordinary Master grant acquires operator rights.

Frozen grammar bounds raw ASCII rules1..64characters/100per list, strict booleans, canonical mapped IPv4/IPv6, deny precedence and environment AND durable-overlay enforcement. State/snapshot/pending crosslinks failclosed; five-minute bound preview and fixed rollback need no worker for effective expiry; post-wait current path/epoch/MFA/authority checks, private network events and audited OOB commands are explicit. Missing/malformed owner config disables management while consistent saved enforcement remains. Full HTML/assets/SPA/API Nginx guard requires isolated actual edge/HTTPS/failure tests before any portal-wide claim. Current resolver/environment middleware remains the only implemented network enforcement.

StageB1 is independently tested pure canonical policy/digest validation and durable models/migration only, without new endpoint, permission advertisement or middleware integration. StageB2 adds complete transactions/APIs/OOB, StageC UI, StageD actual isolated edge evidence; live rollout is separate StageE. No operator, policy, edge configuration, migration or key was provisioned by this freeze. Rule enable/expiry and scoped lower-level overlays remain explicitly deferred. This is a bounded reviewed design, not a security certification.


Cloud hosting and IP restriction are compatible: users can connect remotely only when the effective network and identity policy allows it.

Planned modes: `allow_authenticated` (all network locations still require auth; blocklist applies) and `allowlist_only` (exact/CIDR match also required). Blocklist takes precedence over allowlist. Organisation policy is the ceiling; branch/portal/user policies can narrow it, never widen it. Effective access is the intersection of applicable allow rules minus applicable denies.

Support IPv4/IPv6 canonicalisation, exact addresses, CIDR, enabled flag, purpose, owner, expiry and change history. Resolve client IP only through an explicitly trusted proxy chain, overwrite untrusted forwarded headers and prevent direct-origin bypass. Re-evaluate on requests including long-lived session reconnects; downloaded private assets and API routes must not escape policy enforcement.

**Interpretation of the owner's 'app IP' request:** provide 'allow my verified current IP' for a master admin to add their current observed public address, and allow explicitly configured office/VPN egress addresses. Do not automatically whitelist every visitor. If the owner meant the cloud server's IP, distinguish it from the client's public egress address before applying a rule; it normally cannot identify a remote staff member.

Policy changes need preview, current-session validation, step-up MFA, audit and timed rollback/confirmation. A tested out-of-band recovery process uses cloud/VPN/identity controls; it is not a hidden unauthenticated URL. Never bypass a deny rule by silently adding a recovery exception.

Remote ChatGPT/Claude client egress may differ from the user's browser IP. Configure an explicit approved private gateway or narrow integration policy under the organisation's network ceiling. If a compatible network path cannot be established, MCP remains blocked; never silently disable whitelist-only mode to make a connector work.

### Network StageB1 source foundation — verified, no runtime activation

`apps/security/network_policy.py` independently implements canonical_policy, policy_digest and validate_saved_policy: strict three-field JSON, real booleans, raw ASCII rule length1..64,100rules/list before dedup, decimal CIDR prefixes1..3digits, mapped-IP equivalence, deterministic ordering and detached snapshots. Stored rules must already be canonical and SHA256-matched; invalid data raises ValueError rather than repairing it. SHA256 detects inconsistencies and is not protection against a database operator recomputing hashes.

`core/network_models.py`/model discovery and migration0007 add NetworkPolicyState, NetworkOperator, NetworkPolicyPreview, NetworkPolicyChange and private NetworkPolicyEvent; exact fields in [foundation schema](docs/implementation/network-foundation-schema.md). Database constraints bound singleton/revisions, unique operator/key/activation/result links, exact300s timestamps, terminal scalar consistency and event enums. Migration inserts only an unbound unrestricted overlay with digest; no environment read, user/operator grant or policy activation. Reversal refuses nonpristine state/history, including corrupt JSON integer0 substituted for booleanfalse. Cross-row graph/authority checks, immutable service writes and request enforcement remain StageB2; no DB-superuser immutability claim.

TDD evidence: parser final17RED then39targeted passes/168subtests; model discoveryRED then targeted33SQLitepasses. Fresh independent review reproduced one Important reverse bool/int equality defect; actual MigrationExecutor regression RED then strict historical JSON comparison GREEN. Reviewer final33passes and658additional parser probes, no unresolved Critical/Important/Minor in boundedB1. Root final isolated actual PostgreSQL **351passed/168subtests19.98s**, systemcheck0/no drift; temporary testDB absent and CREATEDB revoked, original preview service active. Earlier346PG21.20s and local330/16skips precede final5reverse cases/fix and are historical. Default-Python full parser-agent attempt lacked pyotp; corrected candidate runtime supplied actual full evidence.

OpenAPI remains0.6.0/46catalogued39implemented: all7network APIs still planned. No current-user advertisement, summary behaviour, middleware, API, UI, OS command, operator, owner binding or Nginx/runtime policy was enabled. Migration0007 ran only in disposable validation DB; initial47b3618preview/live schema preserved. Frontend unchanged; historical72tests/build are not a newly rerun UI result. Next: [frozen B2a snapshot selector](docs/implementation/network-snapshot-contract.md), then full StageB2 services/APIs/OOB, UI and edge gates. Frozen B2a contract network-snapshot-contract.md defines exact NetworkSnapshot/NetworkStateUnavailable/load_network_snapshot internal interfaces, one joined read, strict candidate/fallback/reciprocal preview/bindings/revision/time validation, pending finish metadata null and fixed deadline fallback with independent policy dictionaries. No auth/environment lookup, API, mutation or middleware activation in this unit. Independent pre-code review found no Important blocker; three precisions incorporated before code. Pending preview is required; null preview belongs to terminal OOB history only. Backwards clock fails closed. B1ca8dd41actualCI40039667570all3jobs success verified. A trailing blank at parsertest EOF was flagged by prior whitespace check but the PowerShell batch continued to commit; removed now without behaviour/assertion changes. Future commits follow separately inspected checks. No new app tests claimed for this design/formatting change.

### Remaining network B2 integration — frozen plan, implementation in progress

[Isolated edge validation plan](docs/implementation/network-edge-validation-plan.md) is frozen before templates/harness implementation. Actual source and HTTP acceptance remain pending; no live Nginx installation or preview change is authorised by validation.

[Integration execution plan](docs/implementation/network-integration-plan.md) completes the exact environment/authority/access/history/API/OOB modules and existing middleware/settings/URLs/current-user/effective-summary wiring against OpenAPI0.6.0. Pre-code security review resolved expiry savepoint/outcome accounting, owner-descriptor fingerprint, session-free probe middleware order, post-event/FK-wait proof/deadline/path rechecks and immutable historical OS recovery with one revision increment. No remaining Important/Critical design blocker was found; this is not source or runtime approval. Environment6missing-service and HTTP14missing-route/probe RED cases were observed before production code. Current-owner history remains scoped; no new clinical/ordinary-master grant follows.

Backend and frontend have exclusive source ownership. StageC notes/tests cover the frozen API-only Network access UI; source work in progress is not delivered. Actual PostgreSQL event-driven race matrix, strict API parity, fresh source review, frontend verification and real isolated edge tests remain before completion. Read-only host preflight found Nginx1.24.0 with auth_request compiled and free loopback18185/18186; candidate Gunicorn absent. This is readiness evidence, not a running edge guard or deployment; other VPS applications/live47b3618remain unchanged.

### Network B2a source — verified internal read, not request enforcement

[Snapshot contract](docs/implementation/network-snapshot-contract.md) implemented in core/network_snapshot.py with81tests in test_network_snapshot.py. load_network_snapshot returns a frozen NetworkSnapshot from one joined SELECT over singleton/pending/preview. It validates all saved canonical policies/digests, owner/revision/reciprocalpreview/bindings/300sdates and nullpendingfinishmetadata before selection, including corrupt candidates after expiry. Missing/DB/corruptstate yields generic NetworkStateUnavailable; no repair/cache/auth/environment lookup/write. Beforedeadline candidate is selected; at/afterdeadline fallback and expired_unreconciled are returned without changing revision/history. Independent dictionaries prevent returned-policy aliasing. No broader network decision or user authority is inferred from this internal result.

Precode contract/security review preceded81missingfeatureREDs; targeted81GREEN3.98s. Final localfullbackend416passed/16PG-onlyskips/168subtests101.17s. Freshindependent review81passed4.56s plus11 pointer/overflow/expiry/copy/error-disclosure probes, no Critical/Important/Minor findings in B2a. RootfinalactualisolatedPG432passed/168subtests20.22s, check0/nodrift; testDBabsent/CREATEDBrevoked/oldpreviewserviceactive verified. This is source/test verification, not deployed protection, mutation race safety or fullhospital approval.

Next after cooldown: read latestledger/CI and parentnetworkcontract, then complete B2 environment fingerprint/AND decision, unconditional network authority/current-user/effective-summary, transactionalpreview/apply/confirm/revert/history/OOB and API/middleware integration. All7network operations remain planned;39existing APIs implemented/46catalogued. No staff controls, IP policy activation or portalassets/Nginx change delivered by B2a. Existing frontend remains unchanged; exactB1ca8dd41CI40039667570decoded351PG/168subtests25.81s,72frontend/typecheck/build and19root/OpenAPI/Compose/docs green. NewB2a CI is separate/pending until checked.

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

Cloud deployment is separate from GitHub publication. Owner subsequently authorised a dedicated Hostinger preview at hms.praritsidana.com; see the deployment runbook for actual resources and limits. No hospital production cutover or new paid subscription was performed. Plan separate development, staging and production identities/storage; production data must not enter ordinary preview/test environments. Releases require gated deployment, migrations, health checks, rollback and monitoring. Record actual environments and URLs here when they exist.

## 16. Implementation inventory and current verification

| Item | State |
|---|---|
| Requirements/research | Original baseline plus consolidated research and addenda exist |
| HMS.md / plan.md | Living implementation/verification/deployment inventory maintained; future slices retain design gates |
| Agent workflow | AGENTS.md and safe ignore rules prepared |
| Product pages/APIs/models/MCP | Operational preview/reception reliability/branch-bed-staff configuration and bounded MFA/session/recovery-code source implemented; full recovery/read audit/MCP/clinical/finance/therapy/nursing/dataops remain planned |
| Unit/integration/UI/security/load/restore tests | VPS actual PostgreSQL48passed/25subtests, frontend11tests/typecheck/build passed; HTTPS/session/CSRF/throttle/isolation and database backup/restore smoke passed. No capacity or full security certification |
| Documentation checks | Local links, C-01–C-20/O-01–O-11 coverage, 92 unique page IDs, secret-pattern scan and baseline-copy hash passed. New files pass staged whitespace checks; five intentional original Markdown hard breaks preserved |
| GitHub sync | Initial commit `17df5ef52750cfb55ad9d146dbeba1d9d4820699` verified against remote main; follow-up publication evidence tracked in Git history/handoff |
| Cloud/production | Authenticated preview deployed on Hostinger under /opt/hms; no real-data/hospital production release |

Local verification observed: synthetic development account login succeeded through the frontend and authorised dashboard displayed3 synthetic patients,3 appointments,0 active admissions and12 available beds. No real hospital data used. Development account password exists only in ignored local database/environment, never source or documentation. [Local setup](docs/operations/LOCAL-DEVELOPMENT.md) explains creating a private synthetic account.

Previously open first100-bed admission-selector finding is fixed: paginated25-bed choices, selection cleared on page change, retry on errors and regression selecting bed101+. Frontend11tests and build passed on VPS. Independent whole-product review and live staff/browser acceptance remain incomplete. Appointment input explicitly uses device-local timezone while schedule displays IST; align/validate the intended staff workflow before hospital rollout.

Remaining security/operational gates: complete MFA, distributed application login abuse controls (shared Nginx edge limit verified for preview), comprehensive sensitive-read/immutable audits, full cross-branch identity/access, exclusive room/villa rules, production OAuth/MCP, full/module backup/restore/import/export, and GitHubCI execution. Actual PostgreSQL same-bed race and isolated database restore smoke passed; full recovery/capacity remain unverified.

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

### CHG-0005 — 23 October 2026 — Verified IP policy primitives

- Security agent delivered backend/apps/security/ip_policy.py, package exports and pure tests. Trusted proxies resolved right-to-left; untrusted forwarded headers ignored; IPv4/mapped-IPv6 canonicalised; CIDR/blocklist precedence and malformed/oversized-chain fail-closed behaviour covered.
- Evidence: agent reported RED assertions against an interface skeleton, then GREEN. Coordinator reran `python -m pytest backend/apps/security/tests/test_ip_policy.py -q`:22 passed,25 subtests passed. A simultaneous broad scripts test discovery also saw8 expected RED tests from the platform agent's not-yet-implemented documentation checker; those uncommitted tests are not included in this change. Usage guard8 still pass.
- Scope/limits: pure IP evaluator only; this commit does not prove deployed edge firewall, middleware, admin lockout recovery, MFA or production security. Backend integration is under implementation.
- Publication: `feat: add tested trusted-proxy and IP policy primitives`; no migrations, real records or deployment.

### CHG-0006 — 23 October 2026 — Preserve first runnable development slice at usage cooldown

- Files: remaining backend foundation/migrations/tests/instructions; frontend source/package lock/component/API tests; OpenAPI/page map; development Compose/Dockerfiles/.dockerignore; CI workflow; tested documentation checker; README/local setup; updated HMS.md/plan.md/ledger/usage checkpoint. No dependencies, database, credential files or runtime snapshots committed.
- Delivered: authenticated session/CSRF API, organisation/branch/role checks, patient search/registration/detail, appointments/check-in, bed listing/initial admission, dashboard and nonclinical master inventory; simple API-driven UI with clear unavailable future modules.
- Evidence: backend agent47passed/1PGskip/25subtests; frontend agent8passed/typecheck/build; coordinator root scripts16passed and pureIP22passed/25subtests, plus successful synthetic browser sign-in/dashboard. Final checkpoint rerun details in ledger. API/map/local-link checker passed; remote CI and Compose startup unverified.
- Review: five specialists used in batches; independent fifth reviewer identified first100-bed admission-selector limitation. No new fixes after <=10% stop; issue retained as first resume task. Review incomplete, no production approval.
- Usage: threshold observed6%remaining at05:02:15Z; earliest resume10:32:15Z (4:02PM IST). At manual Continue08:34Z, usage recovered55% but deadline remained active. Native same-chat heartbeat updated; no reset credit consumed and no new implementation during cooldown.
- Publication: `wip: checkpoint runnable HMS foundation and pending review`; feature branch only, not merged/deployed. Resume ledger preserves exact pending work.
- Final coordinator checkpoint reruns: backend47passed/1PostgreSQL-only skipped/25subtests in56.72seconds; frontend typecheck passed,8tests passed,build passed. API/map/local-link checker passed and targeted credential-pattern scan across60source/docs files found no matches. These preservation checks do not waive the known review finding or production gates.

### CHG-0007 — 23 October2026 — Owner-authorised isolated Hostinger preview

- Owner authorised immediate deployment of current work to hms.praritsidana.com with separate folder and preservation of other VPS apps; explicitly waived active cooldown for this deployment only. No reset credit used; general usage/deadline rules remain.
- Plan: docs/implementation/hostinger-preview-plan.md; operations/evidence: docs/operations/HOSTINGER-PREVIEW.md. Added dedicated infra/hostinger service, private PostgreSQL/TLS/hba/Compose, Gunicorn26.2.0 dependency, static Nginx/Basic gate/CSRF/forwarded-header/login-rate controls, bootstrap and verification/backup/renewal templates. No secret or live database in source.
- UI: first100-bed admission selector fixed with paged API choices and >100 regression; initial-preview/synthetic-only labels. No schema or API capability changes; existing initial migration applied to new isolated preview database.
- Access/data: generated owner login stored only private server/ignored local access files; explicit master_admin+reception memberships, no clinical signing.120synthetic beds, initially zero patients. App DB role non-superuser/no CREATEDB after checks. Secrets0600, database/backend loopback only, TLS required. Preview IP mode initially authenticated access; full IP/MFA/backup portal product remains planned.
- Evidence: actual PostgreSQL48passed/25subtests with clean final teardown; frontend11passed/typecheck/build; deployment smoke seven assertion groups passed; external origin port checks blocked; DB dump checksum/restore120beds/zero patients passed; existing Nginx configuration checksums unchanged, five other domain checks200/307. Automated live browser could not pass Basic authentication prompt, so authenticated live browser acceptance remains unverified.
- Operational impact: dedicated /opt/hms and hms-preview units/project/vhost, HTTPS certificate and renewal hook, daily database backup timer. Other app stacks not restarted; only graceful shared Nginx reload after syntax check. Full recovery/off-host encryption/load/security/staff acceptance still open. This is restricted preview, never real-patient readiness.
- Publication: feat: deploy isolated authenticated HMS preview on Hostinger; final verified SHA in handoff. Full remaining HMS development returns to normal usage guard.
- Final additional evidence:19root documentation/usage tests passed; actual app PostgreSQL connectionTLS/non-superuser/NOCREATEDB verified and explicit nonTLS connection rejected. Source/API mapping/local-link checks passed.

### CHG-0008 — 23October2026 — Owner resumes development; freeze reception reliability contract

- Latest owner instruction explicitly resumes further work and adjusts cooldown; authenticated check primary76%remaining/weekly51%remaining allows work. Previous deadline waived by owner only, not automatic recovery. Same native heartbeat updated, local previous state archived, current guard returns continue. No reset credit consumed; future <=10% thresholds still create fresh330minute deadlines.
- Files: usage checkpoint/ledger/AGENTS clarification, active reception-reliability contract, OpenAPI optional Idempotency-Key UUID header on existing patients/appointments/admissions creates and status query enum on existing bedsGET. Existing operation IDs/permissions/response schemas preserved. New behaviours planned, not yet implemented by this contract commit.
- Source UI scope: patient demographic editing, scheduled-appointment rescheduling with expected_version, pageable patient choice and database-filtered bed status; key-per-form retry safety. No clinical signing/finance/call-center expansion. Backend/frontend implementation delegated with exclusive paths and mandatory RED tests; platform verifies actual GitHubCI.
- Ruling: optional key preserves API compatibility; browser must adopt stable keys, legacy clients remain duplication risk. Idempotency ledger stores fingerprint/result UUID, never raw request/response PII; replay reauthorises current user/branch/action. Existing demographic PATCH lacks optimistic version and is explicitly not signed-record concurrency protection.
- Verification: usage guard evaluated authenticated snapshot with minimum51% and continue; contract/page-action validation run at publication. Application tests belong to implementation change, not this contract. Existing Hostinger preview remains prior47b3618 until separately verified update.

### CHG-0009 —23October2026 — Repair living-document encoding/line endings

- Coordinator corrected a Windows text-write encoding/newline mistake in the preceding documentation commit. Normalised HMS.md/plan.md/usage checkpoint to UTF-8/LF without changing approved product scope or deployment. No runtime code or patient data affected.
- Re-run whitespace, links/API-map and commit-synchronisation checks at publication. Actual GitHubCI for47b3618 independently verified successful: backend48passed/25subtests, frontend11passed/build, root19tests/OpenAPI/Compose/docs gate. A separately discovered Error field_errors scalar-vs-array parity bug is assigned to active backend slice with RED tests, not yet fixed by this documentation change.

### CHG-0010 —23October2026 — Verified reception reliability and malformed-input safety

- Backend: optional Idempotency-Key UUID on patient/appointment/admission creates; canonical fingerprint/result-only ledger core0002 with unique actor/operation/key, atomic domain+audit write, scoped current projection replay. Same key/body201same entity, changed body409, malformed key400, failed validation/domain claim rolled back. Legacy no-header clients retain duplicate risk; no expiry yet. Permission/branch/read-only fields rechecked on every replay.
- Frontend: demographic correction through existing PATCH, scheduled rescheduling with expected_version and stale409 recovery, patient selector pagination, server-filtered bed status/counts, stable per-form UUID across failed saves and clear key-conflict recovery; names max160matches backend. No UI-authoritative writes/hidden endpoints/localStorage payloads. Demographic edits remain last-authorised-write, not signed-record concurrency guarantees.
- API: optional header/status contract extensions frozen first, response operations/permissions preserved; error arrays normalised. Login/strict serializers reject nonobject bodies400; keyed multipart unsupported field validates before fingerprint, preventing500. No upload feature added.
- Evidence: frontend5principal RED tests then20passed/typecheck/build; backend reliability RED24failed/9passed plus array/nested RED then37GREEN; independent fresh reviewer26isolated probes found2Important500cases and1Minorlength mismatch. Root reproduced37case safety suite RED27failed/10passed, fixed, targeted74passed, final actual PostgreSQL123passed/25subtests/no skips/warnings in8.60s; migration drift clean. Tests use isolated DB, app CREATEDB revoked afterward. OpenAPI validator/map/link/whitespace checks passed.
- Actual initial47b3618GitHub push workflow39929354427 verified all3jobs success:48backend/25subtests,11frontend,19root checks. New source commit CI result is not assumed. No deferred bounded review finding; full hospital/security/staff/live-browser gates remain.
- Deployment distinction: existing Hostinger authenticated synthetic preview stays47b3618; new migration/source is verified but not deployed in this change. No real hospital data or other VPS app changes. Publication subject feat: make reception retries and patient workflows reliable; final remoteSHA supplied in handoff.

### CHG-0011 —23October2026 — Freeze bounded branch/bed master configuration

- Current reception source03c5634 actual GitHubCI run39932864508 independently verified success:123backend/25subtests,20frontend/build,19root/OpenAPI/Compose/docs checks. Push/remote SHA verified, deployment remains47b3618.
- Design: resource-administration-contract.md freezes page/action/data/permission/failure/tests before code. OpenAPI0.2.0/page map add5operations (23total): scoped organisation branch GET/POST, bed GET/POST and versioned unoccupied-bed PATCH. Only new platform.configure master role grant; never operational/clinical rights.
- Planned data: Bed.version and AuditEvent.details migration, atomic allocation increments, allowlisted nonclinical config before/after snapshots; not yet claimed implemented by this contract. Occupied/reserved/active-admission edits409; no deletion/manual admission override. No100bed cap or first100branch-choice cap.
- Source UI plan: simple branch/bed configuration within current summary organisation, paged lists/branch selection, retained errors and conflict reload. Staff/MFA/multi-org switching/clinical products remain separate. Case-insensitive code/bed collision protected under service locks; config creates may409 on retry, not generic idempotency guarantee.
- Preflight reviewer found no design blocker; backend/frontend RED-first assignments isolated. Ruling: current summary organisation bounds UI, explicit org-scoped APIs can serve other assigned org; wrong assumption costs later selector work, not wider data access. OpenAPI validator/map/local-link checks passed before code; full implementation tests/review pending.

### CHG-0012 —23October2026 — Verified master resources and fresh usage checkpoint

- Source:5new org-scoped platform.configure operations, core/resource_admin.py services/serializers/API, route/grant additions,0003Bed.version/AuditEvent.details, allocation version increments and allowlisted configuration before/after audits. Branch/bed creates under locked case-insensitive collision checks; no100bed cap, occupied/reserved/active-admission edits denied, stale versions409, wrongorg/branch concealed, master config never clinical/operational access.
- UI: extracted ResourceAdministration, branch/bed create/list/edit panels, named branch filter/paging beyond100, readonly/occupied controls, retained validation/conflict feedback, explicit staff-access assignment requirement on new branches. Current summary organisation UI only; full staff/MFA/tariffs/multi-org selector remain planned. Configuration creates may409 on retry rather than generic key replay.
- Pre-code evidence: contract/OpenAPI/page-action extensions frozen and preflight reviewed; backend initial25failed/1passed RED, frontend6failed/1passed RED plus branch-filter RED. Final source local backend162passed/4PGskips, frontend30passed/build. Required-category schema parity RED fixed.
- Review/fix: independent security bounded80backendSQLite/10frontend tests plus source review no extra Important/Critical. Coordinator discovered FK-lock cycle; deterministic actualPGRED1deadlock failure, no_key branch locking fixGREEN1passed, full actualPG166passed/25subtests/0skips/0warnings9.67seconds, system/drift clean. Final coordinator frontend30passed/typecheck/build. No independent full hospital approval claimed.
- Data/operations: migrations verified only in isolated test database, app CREATEDB revoked afterwards. Existing47b3618Hostingerpreview unchanged; no realdata/otherapp/deployment changes. NewsourceCI pending until observed. Source OpenAPI/map/links/whitespace/credential checks at publication; finalSHA in handoff.
- Usage: new9%primary/40%weekly remaining observed09:49:16UTC. Stop assignments (agents already completed), fresh guard checkpoint and same heartbeat330minute update; earliest15:19:16UTC/8:49:16PM IST. No reset credit or deadline extension. Earlier owner general resume does not waive this new checkpoint. Next resume verifies latest CI then plans staff identity/MFA before further clinical scope; full product remains incomplete.

### CHG-0013 —23October2026 — Owner-resume override and scoped staff-access contract

- Latest direct owner instruction Continue limit aa gyi hai puri at13:36:49UTC explicitly resumes now, superseding prior15:19:16cooldown. Authenticated primary100%/weekly40%remaining; local guard continue atminimum39%; preserve historical checkpoint state. Same heartbeat updated in place, no reset credits, no duplicate running team. Future<=10stops still330minute minimum.
- Actual latest resource2ca8239pushCI39935239961success verified from all job logs:166backend/25subtests11.20seconds/check/drift,30frontend/typecheck/build,19root/OpenAPI/Compose/docs. No CI mutation required; Node action deprecation warning remains nonblocking.
- New frozen staff-access-contract.md and OpenAPI0.3.0/page map4operations (27total) before production code: org-scoped staff GET/POST/PATCH and staff-specific paged branch-option GET under platform.staff.manage. Permission scope/password/state/error/race/UI/test design documented and independently preflight reviewed. Models/grants/UI are planned, not delivered by this contract.
- Planned data: Membership.is_active authoritative scope and StaffAccessRevision lazy legacy0/new1; role replacement/suspension audited with allowlisted IDs/roles, no passwords/name/body copies. Org lock plus post-lock actor grant recheck protects mutual-admin suspension. Global account_active stays readonly; suspension revokes hospital permissions without globally disabling other organisations. Staff branch lookup avoids widening configuration rights.
- Rulings: owner direct resume waives only old deadline; source staff suspends organisation grants, not global account/session identity.1..100assignment request boundary is not hospital record capacity. Legacy0avoids hidden GET writes. Costs if scope insufficient are explicit future identity/UI migration; no broader authority granted.
- MFA researched separately with official sources before choosing secret/challenge/recovery/session architecture. No MFA/password reset/deployment completion claim. Backend/frontend RED-first exclusive assignments and security preflight underway; coordinator owns docs/Git.

## 18. Technical references

- [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html), [row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), [recovery](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [MCP authorisation](https://modelcontextprotocol.io/specification/latest/basic/authorization), [MCP security](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices)
- [OWASP authorisation guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)

References guide implementation; they do not certify the incomplete application or its preview deployment.

### CHG-0014 —23October2026 — Scoped staff access and revocation consistency

- Implemented4staff APIs/27total source operations, StaffAdministration paging/search/create/role+branch edits and suspend/restore, dedicated staff branch picker beyond100, masked initial password, conflict retention and ambiguous-save guidance. Additive CurrentUser.branch_permissions keeps doctor-A/reception-B actions clear. No multi-org selector/global disable/MFA/deployment claim.
- Data/security: core0004Membership.is_active/defaultTrue and StaffAccessRevision; legacy0read-only/new1, post-org-lock reauthorisation, fresh active branch ceilings, self-edit denial, independent global account state, other-org preservation and allowlisted before/after audit without credentials. Django password validators enabled. Request assignment cap100 is not response/data capacity.
- Backend staff initial35RED, final38targeted GREEN; fresh independent review117targeted passes plus probes identified stale post-lock configuration and old-grants/new-version snapshot. Coordinator7consistency RED cases reproduced and fixed, plus branch map RED->GREEN. Configuration/appointment/admission/keyed replay permission refresh and bounded staff snapshot retry cover revocation. Minor response maxItems removed; request bound retained.
- Final coordinator actual PostgreSQL213passed/25subtests/0skips in13.46seconds; Django check0issues/no migration drift; temporary test DB cleaned/CREATEDB revoked, live database/schema untouched. Frontend49passed/typecheck/build including mixed-branch RED->GREEN. Root/API/docs validation recorded at publication; latest prior resourceCI39935239961success166backend/30frontend/19root. New source CI tracked separately after push.
- Source files backend/apps/core/{staff_access,authorization,api,models,resource_admin,services}, migration0004, settings/urls, staff/consistency/PGtests; frontend StaffAdministration/App/pages/types/styles/tests, OpenAPI and living docs. No secret/real patient data or credential/runtime artefacts published.
- Operational impact: source-only; preview remains47b3618. Full MFA/session revocation/recovery/read audit, remaining clinical/finance/MCP/dataops and actual staff acceptance remain release gates. Next bounded slice freezes identity security contract before code. Commit subject: feat: add scoped staff access and consistent revocation.

### CHG-0015 —23October2026 — Staff CI verified and identity security design frozen

- Staff commit69f4fdac65a02f50d59f633e9c0996e527c03cd3 pushSHA verified; independently inspected actual push run39968605247success at14:20:02UTC: PostgreSQL213passed/25subtests14.58s,frontend49/typecheck/build,root19/OpenAPI/Compose/docs. Source remains separate from deployed47b3618.
- Freeze identity-security-contract.md/OpenAPI0.4.0/page-action9newoperations36total before code: self authenticator enrollment/confirm, pending MFA verify, recovery rotation/disable, session revoke/stepup/password, login202 and CSRF public logout. Dedicated row-bound Fernet secrets, hash-only codes, atomic replay/counter/epoch control, existing-factor replacement proof, clear UI/transient secrets and production privileged-write policy.
- Independent pre-code specialist reviewed actual authentication/authorisation/settings and found blockers now designed explicitly: existing-factor replacement, authenticatedlogin flushing, anonymous CSRF, revocation check under stable identity lock, authoritative challenge generation and committed attempt outcomes. Ruling: in-flight ordinary requests may finish; only locked sensitive paths claim revoke ordering. Existing epoch0legacy compatibility ends at activation/epochincrement. TOTP is not phishing resistant; no full recovery/deployment/security assurance claimed.
- Files: contract/OpenAPI/map/API notes/HMS/plan/ledger/checkpoint only. OpenAPI validator/source-map/local links passed before assignment; implementation/tests remain pending. Owner authorises continuous implementation, no new hosted/paid provider or deployment. Package/research sources recorded in contract. Next RED-first backend/frontend followed by fresh review/actualPG tests.

### CHG-0016 —23October2026 — Recoverable identity WIP and new usage stop

- New threshold primary9%remaining/weekly25%, local guardcheckpoint14:38:35.257381UTC and earliest20:08:35.257381UTC/24October1:38:35AM IST. Stop messages sent to backend/frontend/reviewer; all stopped, no newimplementation/assignments after threshold. Prior13:36owner waiver does not waive this new checkpoint. Same native heartbeat updated330minutes; no reset credit or deadline extension.
- Preserved9self-security APIs/login202/CSRFpartiallogout, core0005five state models/encryption/replay/attempt/epoch services and Account security UI; source WIP, no release/deployment. Dedicated prepared operations runbook explains private keys/rotation/backup/recovery gaps, not performed provisioning. Existing47b3618preview and other VPS apps unchanged.
- Evidence: backend initialRED9; further method/session/login regressionsRED->GREEN, localfocused21passed2PGskips; earlierfull227passed7PGskips25subtests before last2login tests. ActualPGbaseline4failed230passed; finalfrozen236passed25subtests17.68s/check/nodrift/testcleanup/CREATEDBrevoked. Frontend64tests/typecheck/build after15new tests; independent read-only source review incomplete/no test execution/no fullapproval.
- Known next security work: proof-age recheck after organisation-lock wait, ciphertextswap, enrollment expiry/crosssession/replay, anonymousverifyCSRF, account/challenge/window/race coverage and actual full protected-write/revoke ordering. No unresolved claim of complete security. Root checks/stagedsecretcomparison/verifiedpush at checkpoint; Git history/handoff supplies SHA, commit subject chore: checkpoint identity security WIP at usage threshold.


Checkpoint coordinator repeat: frontend63passed/1failed (resource-administration stale-bed-edit test could not find Edit bed101 within timed wait); agent earlier64passed. Coordinator typecheck/build still passed. Affected test isolated rerun is recorded in ledger/handoff; this does not establish a repaired full suite. No source changes after stop. Investigate/repeat full suite after cooldown before marking identity delivered.

### CHG-0017 —23October2026 — Owner resumes identity completion

- Direct owner continue at17:44:21UTC, authenticated both windows100%remaining, waives old20:08:35deadline. Preserve priorcheckpoint/history; localguardcontinue and sameheartbeat updated, no reset credit consumed. Future<=10%stops mandatory.
- Active contract unchanged: identity-security-contract.md, source6660bb0WIP. Pre-code plan resumes exact reproducible bed-edit failure, proof-age-after-lock and named negative/race coverage before review/verification/publication. No new API/schema/production change in this resume record.
- HMS/plan/AGENTS/ledger/checkpoint updated coherently; doc links/API map checked at publication. No new passing application test/deployment claimed merely by resuming. Existing preview47b3618preserved.

### CHG-0018 —23October2026 — Verify identity security and repair loading regression

- Completed bounded9operation identity source without changing schema/OpenAPI count36. After frozen planning/negative/race design, backend5freshness regressions RED->GREEN; final organisation/branch/bed/staff-lock and transactional audit freshness checks protect privileged writes under waits. Added23tests15local/8PG for encryption binding, enrollment lifecycle/CSRF, attempt windows, missing-key accounting and actual API concurrency. No key provisioned/deployment performed.
- Independent fresh reviewer found Important bed-lock proof-age gap via isolated901sclock probe RED; tracked final-lock cases fixed it and independent probe plus identity suite37passed10PGskips. Bounded source approval no remaining Important/Critical established, subject to root integrated checks; no wholehospital/production approval.
- Root actual isolated PostgreSQL259passed25subtests/0skips17.20s, Django check0/no migration drift, temporary testDB removed/CREATEDB revoked. Backend agent local244passed15PGskips25subtests32.54s. Root frontend64passed18.01s/typecheck/build; original testRED reproduced then exact inventory-scoped query GREEN, no timeout/mock/production change. Private local browser sign-in/Account security page verified visually; full staff/live-browser acceptance remains open.
- Prior6660bb0pushCI39972065170success inspected; new source CI not presumed. Root OpenAPI/map/docs/19projectchecks at publication, stagedprivatecredentialcomparison and remoteSHA in handoff. Files resource_admin.py/staff_access.py/test_identity_security.py/resource-administration.test.tsx plus living/API/operations docs. No new migration in this repair; original0005still source-only.
- Owner17:44resume history preserved; no reset credit consumed. Source ready for bounded identity use in synthetic validation, not real-data hospital rollout. Remaining recovery/read audit/IP management/clinical/finance/MCP/dataops and release gates continue from plan. Commit subject: fix: verify MFA freshness across locks and identity races.

### CHG-0019 —23October2026 — Verified identity CI and freeze scoped audit history

- Independently decoded exact2c65c57pushrun39998933249success17:55:20UTC:259PG/25subtests18.68s,64frontend/typecheck/build,19root/OpenAPI/Compose/docs. RemoteSHA verified, source-only; preview47b3618unchanged.
- New audit-history-contract.md/OpenAPI0.5/page map3GEToperations39catalogued36implemented frozen before production. Five same-org nonclinical actions under new scoped auditread+recentMFA, eight own branchless security actions under fullselfsession; strict date/page/query/type/projection/label/privacy/UI/test/index design. No rawglobalbrowser/clinical/read-audit/immutable/export claim.
- Independent pre-code privacy review accepted split, required scalar maxima, bool/int rejection, extreme-date validation, stringUUIDroute400 and read-onlyrequire_platform; all incorporated before assignment. Ruling row-derived named branch filter avoids granting staff/config lookup permission; costifinsufficient later dedicatedpickerAPI, notbroaderscope.
- Files contract/OpenAPI/map/API notes/HMS/plan/ledger/checkpoint. Validator initiallycaught emptyrequiredarray in new schemas, corrected before freeze; finalOpenAPI/map/links passed. No runtime implementation/schema/test pass claimed by this design commit. Next backend/frontendRED thenfreshreview/actualPG/verifiedpush.

### CHG-0020 —23October2026 — Verified scoped administration journal and own activity

- Implemented3GETAPIs/39source operations, new active-master platform.audit.read+currentMFA, same-org five-action administration journal and eight-action authenticatedself security activity. Source paths audit_history.py/authorization/routes/models,0006indexes andtests; strict queries/typed bounded redactions/currentlabels/90daywindow/pinnedpaging. No rawclinical/globalforeignJSON/GETwrites/mutations/export/immutable/read-audit claim.
- Pre-code contract/privacyreview preceded initial18backendRED. Hostile enum2RED, offsetnormalisation2RED and calendarformat3RED fixed before source approval; RFC3339clarification/schema pattern aligned before parserimplementation. Fresh independent backend38pass1PGskip/frontend8passes and final7parserregressions independentlyGREEN, no unresolved Important/Critical established in bounded source.
- RootfinalactualPG301passed25subtests/0skips16.14s, system0/no drift and index/EXPLAIN check; temporary testDBcleaned/CREATEDBrevoked, live47b3618runtime/schema unchanged. Priorlocalfull282pass16PGskips25subtests before last3parsercases, targetedfinal41pass1PGskip. Rootfrontend72pass26.75s/typecheck/build after isolated staff18pass; earlier parallel71pass1timeout preserved as evidence, no timeout increase. Finalspacing-only followupbuild+browserchecked.
- Local browser synthetic stale-epoch re-login, MFA202challenge/recoveryverification, ownsecurityactivity and masterhistory/detail render verified. Pre-enrolled synthetic fixture (not actualbrowserenrollment), private testkeys/data/screenshots ignored. Detailpadding reusedexistingdetail-body after screenshot showed flush body. Fullstaff/livebrowser/production/immutability/read-audit remain separategates.
- NewsourceCIchecked afterpush separately; prioridentity2c65CI39998933249green. RootOpenAPI/map/docs/19checks/stagedsecrets/remoteSHA at publication. NextTask03globalIPpolicy planning: explicit operator authority, envANDDBpolicy, failclosed, timedrollback, fullportalstaticguard and auditedoutofbandrecovery; no live policy deployment by this change. Commit: feat: add scoped administration history and own security activity.

### CHG-0021 —23October2026 — Verified audit CI, network design draft and fresh usage stop

- Exact16b6ca3 remoteSHA verified; actualpushCI40002404443success18:20:48UTC, all3jobs. Rootdecoded logs: backend301passed/25subtests15.69s/check/nodrift; frontend72/typecheck/build; root19/OpenAPI/Composequiet/docs. No new test or deployment inferred from the workflow file.
- Saved network-access-design.md as planning proposal only, based independent IP/security/topology specialist. Explicit operator entitlement+owner binding, unconditional MFA, envANDDB/failclosed, durable preview/change/deadline/recovery, fullportalstatic/SPA/API Nginxguard and required tests. No new API/model/code/CLI/live provision; OpenAPI stays0.5/39implemented. Next exact contract/OpenAPI must freeze before RED implementation.
- NEW usage boundary primary10%remaining/weekly86% at18:21:54.627991UTC. All agents already completed; no new assignments/implementation after threshold. Localguardcheckpoint_and_stop, earliest23:51:54.627991UTC/24October5:21:54AM IST, allwindows>10 required. Sameheartbeat updated330minutes, no reset credit/deadline extension. Prior17:44owner resume waived only olddeadline, not this new stop.
- Completed this owner-resumed run: identity freshness/negative/concurrency review and audit-history source, final301PG/72frontend/19root, local synthetic MFArecovery/history visuals. Full recovery/read audit/clinical/finance/MCP/dataops and realstaff/security/load/restore release gates remain. Existing live47b3618and otherVPSapps preserved. Rootcheckpoint/docs checks/stagedsecretcomparison/verifiedpushSHA recorded in handoff; newdoc-onlyCI may remain unchecked until resume.

### CHG-0022 —24October2026 — Owner schedules earlier resume and repository review

- Owner scheduled resume override at 2026-10-23T22:04:30Z: resume 24 October 2026 at 04:30 AM IST (2026-10-23T23:00:00Z), replacing the former 23:51:54.627991Z deadline only. Authenticated usage at scheduling: primary2%remaining, weekly85%remaining; 100% recovery is owner expectation, not verified. No implementation before the new time; resume only all applicable windows available and>10%. Original18:21:54.627991Z stop/history preserved, no new low-reading deadline/reset credit. Same heartbeat now daily04:30 local wake; future fresh<=10% stops still require checkpoint+330minutes and updating this same heartbeat. First resume task: source/licence/security/feature comparison of ictinnovations/ICTHospital against plan.md, then pending network-access design freeze. No code copied or source implementation/deployment performed by this scheduling change. Scheduling is best effort; PC/Codex/repository/credentials must be available.
- Evidence: authenticated usage, existing heartbeat update success and saved scheduling/docs checks; no application tests rerun for this documentation-only change. Publication SHA verified separately.

### CHG-0023 —24October2026 — Resume verified and ICTHospital reference comparison

- Owner04:30scheduled resume reached; authenticated23:02:32UTC primary100%/weekly84%, later90%/83%. Local usage guard returns continue/minimum83%; previous stop and override history preserved, no reset credit. Same heartbeat maintained for this chat.
- New source-pinned research maps existing workflows, deferred laboratory gap, reporting definitions, snapshot integrity and unconfigured reminder candidates. Root licence/manifest mismatch blocks material copying; no dependencies/code/assets/runtime/API/schema/permissions/deployment changed. Simple hospital UX and API-first stack retained.
- Independent feature/security and fresh documentation reviews completed; no Important/Critical documentation blockers found, three Minor evidence refinements fixed. Local docs/links/API-map/staged-whitespace/private-credential checks recorded at publication; no application tests rerun for research. Actual upstream160test success and failed dependency audit are not our own runtime assurance. Latest own prior doc CI40031346794success verified.
- Next: freeze/review Task03 network contract and OpenAPI/page map before RED implementation; network designer/pre-code specialist working in exclusive draft/read-only roles. Full hospital release and existing47b3618preview unchanged. Commit subject: docs: compare ICTHospital workflows and resume verified development.

### CHG-0024 —24October2026 — Freeze network access contract before code

- Exact Task03 contract and OpenAPI0.6.0/page-action map define7planned/46catalogued operations, preserving39source APIs. Six fresh-MFA owner+OSoperator management capabilities, internal network-only probe, closed bounded schemas, strict retries/deadlines/error/recovery/history and fullportal edge acceptance; existing current-user/effective-summary changes explicitly planned.
- Independent security/edge reviewer identified and resolved middleware-order/probe cookies, malformed owner enforcement, pending crosslinks, post-lock effective-path, summary, environment trust and production HTTPS requirements. No remaining Important/Critical blocker found in bounded design review; not code/runtime/production approval. Coordinator raw-rule pretrim64limit and B1 individual-snapshot/B2 graph separation rulings prevent schema/implementation ambiguity; cost if insufficient is later explicit contract revision, never silent fail-open.
- StageB1 parser/schema-only tests and source are next after freeze; no runtime/API/model/permission/migration/deployment delivered in this commit. Source statuses, tests and live47b3618remain distinct. Root validator/map/link/project19checks/stagedsecretcomparison at publication; research2a77b39actualCI40038077419success verified. Commit subject: docs: freeze network access authority rollback and edge contracts.

### CHG-0025 —24October2026 — Verify network parser and durable schema foundation

- StageB1 strict purepolicy/digest helpers,5durable models/core0007 and exact fieldmap/tests implemented without exposing network APIs or changing runtime enforcement. Decimal-prefix/pretrim grammar clarified in frozen contract/OpenAPI;46catalogued39implemented unchanged.
- Tests first: parser17RED/modeldiscoveryRED. Fresh reviewer Important migration False==0 defect reproduced by actualMigrationExecutorRED, historical strictJSON comparison fixed; finalindependent33schema passes/658parserprobes and no unresolvedboundedfinding. RootfinalactualPG351passed168subtests19.98s/check0/nodrift, testDBcleaned/CREATEDBrevoked; livepreviewservice remainsactive. No full security/hospital readiness claim.
- RootOpenAPI/map/links/stagedwhitespace/privatecredentialchecks atpublication;19projectchecks23.898s previouslyrunthisunit. StageA8dbe1b0actualCI40038659241success verified; newsourceCI checkedseparately. Newsource notdeployed, no liveoperator/owner/policy/edgechange. NextStageB2 graph/transaction/API/OOB design/RED work. Commit: feat: add verified network policy parser and schema foundation.

### CHG-0026 —24October2026 — Freeze coherent network snapshot unit

- Frozen B2a contract network-snapshot-contract.md defines exact NetworkSnapshot/NetworkStateUnavailable/load_network_snapshot internal interfaces, one joined read, strict candidate/fallback/reciprocal preview/bindings/revision/time validation, pending finish metadata null and fixed deadline fallback with independent policy dictionaries. No auth/environment lookup, API, mutation or middleware activation in this unit. Independent pre-code review found no Important blocker; three precisions incorporated before code. Pending preview is required; null preview belongs to terminal OOB history only. Backwards clock fails closed. B1ca8dd41actualCI40039667570all3jobs success verified. A trailing blank at parsertest EOF was flagged by prior whitespace check but the PowerShell batch continued to commit; removed now without behaviour/assertion changes. Future commits follow separately inspected checks. No new app tests claimed for this design/formatting change.
- Root docs/OpenAPI/map/links/stagedsecret/remoteSHA at publication. Commit: docs: freeze coherent network snapshot selection unit.

### CHG-0027 —24October2026 — Verified coherent snapshot selector and fresh usage stop

- B2a read-only singlejoinedSELECT/strictgraph/fixeddeadline/corruptionfailclosed/detachedpolicy source implemented after frozenplan/review/81REDs. No HTTP/capability/auth/env/middleware/OSoperator/edge/deployment activation. RootfinalactualPG432/168subtests20.22s/check/nodrift, local416/16skips/168subtests101.17s, freshboundedreview81+11probes no unresolvedC/I/Minor. PrivatevalidationDBcleaned/CREATEDBrevoked,47b3618previewserviceactive.
- NEW primary9%/weekly70%stop23:34:44UTC, earliest05:04:44UTC/24October10:34:44AM IST. Allagentscompleted; no newwork/assignments afterboundary. Localguardcheckpoint_and_stop, sameheartbeatrescheduled330minutes; no resetcredits/deadlineextension. Priorowner04:30resume fulfilled onlyolddeadline, doesnotwaivethisfreshstop.
- Researchcomplete/no importedcode, networkA/B1/B2a source completebounded; fullB2integration/UI/edge/OOB/clinical/finance/MCP/dataops/release remain. Root finalschema/map/links/stagedsecret/whitespace/remoteSHA atpublication. ExactB1CI40039667570decoded351/72/19green; newB2aCI notpresumed. Commit subject: feat: verify coherent network snapshots and checkpoint usage.

### CHG-0028 —24October2026 — Resume remaining network integration

- Owner explicitly continued at2026-10-24T05:10:42UTC (10:40:42AM IST). Authenticated primary100%/weekly69%remaining; saved05:04:44UTC deadline already elapsed, so no cooldown waiver or reset credit was needed. Prior stop/scheduling history preserved; guardcontinue, same heartbeat updated. Exact a412637sourceCI40040673163success observed. Resume remaining networkB2 API/authority/transactions/OOB and StageC client under frozencontract; B1/B2a/ICTHospital/initialdeployment are completed and not repeated. No new runtime feature or live deployment delivered by this resume record.
- Documentation/API-map/link/stagedsecret checks at publication; no new application tests or features claimed for resume. Commit: docs: resume network integration after verified usage recovery.

### CHG-0029 —24October2026 — Freeze remaining network integration execution

- Exact module/interface/lock/outcome/test plan now frozen under parent7API contracts; API counts46catalogued39implemented until runtime verification. Independent pre-code security review no remainingImportantCriticaldesignblocker after expiry/fingerprint/probe/postinsert/OOBprecisions. Environment6RED/HTTP14RED before production implementation.
- Authority and history scope preserved, currentowner journal only, OS snapshot recovery separate and immutable historical links. No actual policy/operator/owner/edge/deployment change. StageC client inprogress under existing frozen page/action design, not delivered by planning.
- Rootdocs/OpenAPI/map/link/stagedsecret/whitespace/remoteSHA atpublication; no new application pass claimed. Earliera412637actualCI40040673163success observed. Commit: docs: freeze network API and transaction integration plan.

### CHG-0030 —24October2026 — Freeze isolated network edge validation

- Frozen [edge validation plan](docs/implementation/network-edge-validation-plan.md) covers actual Nginx/Gunicorn HTTPS acceptance, Basic AND network, denied socket identity, all portal paths, cache/security headers, fixed rollback, DB/worker faults and private probe. Exact loopback ports18185/18186 and source/runtime directories are isolated from live preview.
- Root alone provisions/removes exact disposable hms_edge_validation_20261024 and installs pinned Gunicorn only in existing candidate venv; runner receives no admin credentials and cannot create/drop databases. Owned process-group cleanup restores paused workers before termination; no global service action. Read-only preflight confirms compiled auth_request, free ports and candidate Gunicorn absent. Actual runtime evidence remains pending.
- Previous PostgreSQL RED cleanup rechecked: app role NOCREATEDB, temporary test DB absent, preview service active. Source/backend/UI work in progress is not committed as verified by this planning unit. Documentation checks at publication; no new app test pass or deployment claimed.

### CHG-0031 —24October2026 — Preserve tested network source with open acceptance gates

Network B2/C source exists, acceptance incomplete: environment ceiling AND durable overlay, explicit owner/master/OS operator/fresh MFA, six strict management APIs and session-free private probe, fixed preview/rollback transactions and typed OS operations are implemented. Current-user capability and effective deployment summary are wired. OpenAPI/page actions now distinguish46 source-implemented operations from release acceptance; the seven network operations carry explicit pending-security-ui-edge-acceptance. No live operator/owner/policy/schema or runtime deployment changed.

Root actual PostgreSQL frozen run:520 passed/168subtests41.80s, including12 new concurrency cases; Django check0/no migration drift. First run516passed/1failed39.23s: test reused existing trusted-proxy setting so no actual drift; corrected to assert a genuinely different fingerprint, without weakening production enforcement. Local backend492passed/28explicitPG-indexskips/168subtests43.37s. Reviewer69focused passes fixed mixed-owner GET, summary state short-circuit and unsupportedOPTIONS; independent overflow probe led2RED->503/no-write2GREEN. Final fixes lack complete fresh source re-review. Known read response timing concern: server_time selected after coherent snapshot may cross rollback; add exact RED then coherent projection fix before acceptance. Broader staff-service/operator/owner-transfer/activation-event race cases remain.

Frontend source implements memory drafts, preview/apply/keep/restore, permission navigation, deadline/conflict/unknown-write gates and pinned history. Valid-JSON malformed envelopes reproduced17RED plus enum-array regression; local guards prevent crashes/false success. Specialist full115 tests (72 existing+43 network), typecheck/build pass; root rerun recorded separately. Independent frontend review and actual synthetic browser/staff walkthrough are pending.

Edge source/harness is WIP NOT DEPLOYABLE. Seven source/safety tests pass; actual run failed at private PostgreSQL HBA rejection before Nginx/Gunicorn/HTTP launch. No shared HBA change made. Exact disposable DB/private config removed after zero-connection check;18185/18186 listeners absent and old preview active. Candidate-only Gunicorn26.2.0 installed in validation venv, not live venv. Independent Nginx1.24 source inspection confirms If-None-Match:* can still produce304 despite etag off; strict no304 acceptance is retained. Future explicit isolated-PG and conditional-cache design amendment needed before actual edge matrix. No runtime edge claim.

Root publication checks include19 project tests10.171s, OpenAPI/map/links/credential/whitespace; planningc9c9eec actualCI40066279371success. New source CI must be checked independently. This is recoverable feature-branch source, not release approval.

### CHG-0032 —24October2026 — Fresh usage stop and preserved integration source

NEW usage stop2026-10-24T05:36:20UTC: primary10%remaining/weekly55%. All specialists completed; no new implementation or assignments after this boundary. Earliest resume2026-10-24T11:06:20UTC (24October4:36:20PM IST), only all windows available and>10%; no reset credit. Same heartbeat330minutes; previous05:10resume does not waive this fresh stop.

Root final frontend115/8files58.52s, typecheck/build24modules190ms passed. Root actualPG520/168subtests41.80s/check0/nodrift; testDBabsent0/appCREATEDB=f/previewactive independently confirmed. Root19projecttests10.171s, schema/map/link checks passed. Seven network operations have source implementations, explicit pending acceptance; no deployment. First resume task is exact GET server-time/snapshot deadline regression, remaining concurrency/fresh review, frontend independent review/browser and edge isolated-PG/no304 design amendment. All source stays recoverable on feat/hms-foundation; fresh CI and remote SHA recorded at publication.

### CHG-0033 —24October2026 — Record verified source publication and continuation

Source checkpoint725234547a5063264be44f2e0ac58c83d00e4586 committed and pushed to feat/hms-foundation; remote SHA exactly matched, working tree clean at source publication. Actual source CI40066986031 observed in_progress, not a pass. Same native heartbeat successfully updated ACTIVE330minutes with fresh11:06:20UTC deadline and exact pending tasks; no reset credits. Root confirmed all specialists completed; no local visual servers launched. This follow-up is documentation-only publication evidence; verify its own remote SHA at handoff.

### CHG-0034 —24October2026 — Scheduled resume and verified checkpoint CI

Scheduled resume2026-10-24T11:07:26UTC after saved11:06:20UTC deadline elapsed. Authenticated primary100%/weekly55%remaining at entry; subsequent guardcontinue minimum54%. No owner waiver or reset credit needed. Historical05:36stop preserved; no active cooldown. Exactd33937f CI40067046203success decoded520PG/168subtests34.29s,115frontend/typecheck/build,19root/schema/docs; source7252345CI40066986031cancelled by laterpush, never claimedpassed. Resume exactGETtime boundary, independentUIreview and edgeisolation/cache design; no repeateddeployment.

All specialists were completed at initial inventory; backend timing/regression, fresh independent UI reviewer and edge design research run in distinct ownership batches. Root alone Git/VPS. No new feature/test pass/deployment delivered by this resume record.
