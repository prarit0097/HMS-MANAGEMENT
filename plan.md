# Circadian HMS implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers `executing-plans` or, when selected, `subagent-driven-development` task-by-task. Use `writing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion` and review skills as applicable. Apply UI/UX Pro Max to UI planning, implementation and review. Checklist status must reflect evidence, not intent.

**Goal:** Build a secure cloud HMS for the operating hospital, with connected Ayurveda/OPD/IPD/finance workflows, expandable branches/capacity, a master-admin control plane, controlled MCP and future call-center integration boundaries.

**Architecture:** API-first modular Django/DRF core with PostgreSQL, simple professional React/TypeScript staff frontend, protected files and bounded background workers. Every application capability has a versioned documented API; all clients/adapters share its authorised capability contracts and business services. Independent workload limits protect hospital operations from imports, reporting and integrations.

**Tech stack:** Python/Django/DRF; React/TypeScript/Vite; PostgreSQL; proposed Celery/RabbitMQ and Redis; private object storage. Supported compatible versions pinned before scaffolding. Hostinger existing VPS selected for restricted preview; identity/OAuth products not yet selected.

**Spec:** [HMS.md](HMS.md), [consolidated research](docs/research/HMS_CONSOLIDATED_RESEARCH_BASELINE.md), latest owner instructions.

**Status:** Version1.7.2,23October2026: USAGE STOP primary9%/weekly25%; checkpoint14:38:35.257381UTC, earliest20:08:35.257381UTC (24October1:38:35AM IST) plus allwindows>10. Staff69f4fda verified/CIgreen. Identity9newops36total source WIP236PG/25subtests/64frontend-agent pass, known proof-age-after-lock and security coverage/review unfinished. Preview47b3618unchanged; no implementation during cooldown.

## 1. Global constraints and owner requirement mapping

| ID | Owner instruction | Planning coverage |
|---|---|---|
| O-01 | HMS.md explains product and tracks every change | HMS.md sections 1–18, AGENTS.md, Task 00 and every task closeout |
| O-02 | plan.md covers every page, feature and function before development | Page catalogue, contracts, tasks and planning gate |
| O-03 | Planning -> multiple testing -> coding | Section 2 and per-task red/green/review workflow |
| O-04 | Push every completed change to specified GitHub repo | Section 17 and AGENTS.md; remote SHA verification |
| O-05 | Security is main focus | Threat/control/test catalogue, Tasks 01–05, release gates |
| O-06 | MCP connectivity for compatible AI clients | MCP contract, pages M17/M18, Task 15 |
| O-07 | Cloud-hosted authorised remote access | Cloud/deployment and Task 17 |
| O-08 | Configurable whitelist/blacklist and whitelist-only access | Pages M06/M07, IP contract, Task 03 |
| O-09 | Full/portal backups and imports/exports | Pages M09–M13, recovery/data-movement contracts, Tasks 13–14 |
| O-10 | Master admin above all portals | Master-admin catalogue and permission ceiling |
| O-11 | Superpowers and UI/UX Pro Max | Skill workflow, design checks, per-task closeout |
| O-12 | End-user frontend must be simple, professional and minimise confusion | Common UI contract, role-task walkthroughs and Task 17 usability acceptance |
| O-13 | Entire application API-based; top architectural priority | API-contract-first gate, OpenAPI, all-capability coverage and independent API/parity tests |
| O-14 | Five-agent team; stop at10%usage remaining; resume after5h30 | Team/ledger contract, tested usage guard, native continuation heartbeat and durable checkpoint |

Carry forward C-01–C-20 from the original baseline, explicitly mapped below. No 100-bed hard limit. Call-center product investigation/implementation deferred; IDs/events/permissions prepared now. Premises rent/norms owner-managed. Preserve green booked/occupied and red available beds with accessible labels. UI/API/MCP/file paths enforce the same security ceiling. No live patient data in Git or ordinary test environments.

### Original confirmed-requirement traceability

| ID | Pages / owning tasks | Required acceptance |
|---|---|---|
| C-01 | M02 / 01–02 | Hospital identity configured and consistently displayed/printed |
| C-02 | R02–R06 / 04 | Intake/history provenance and doctor assignment preserved |
| C-03 | R01–R12 / 02/04/07 | Reception portal/action scope enforced |
| C-04 | D01–D07 / 05/08 | Consultation and approved prescription version retained |
| C-05 | D03/D08 / 05 | Typed/upload/voice draft reviewed before release; voice timing agreed |
| C-06 | D03/P01/R07 / 05/06/10 | Medicine-only, therapy-only and combined routes produce correct independent worklists |
| C-07 | R07/T02 / 06 | Reception schedules approved therapy without editing clinical order |
| C-08 | P01/P02/P06 / 10 | Actual partial supply/remaining/return quantity traceable |
| C-09 | A01–A10 / 11 | Accounts portal and controlled payment/adjustment workflows |
| C-10 | M02–M05/M14/A08 / 02/09/11 | Staff/rules/rates configurable with audit/versioning |
| C-11 | R08–R11/N01–N05/D04/D06 / 07/08/12 | Connected first-release IPD journey supported |
| C-12 | R09/M14 / 07 | All five accommodation categories including exclusive villa |
| C-13 | M14/R09/A08 / 07/11 | Room identifiers/categories/effective rates configurable |
| C-14 | R09 / 07 | Unique bed identity and valid room mapping enforced |
| C-15 | R09/G01 / 07/16 | Current capacity reconciles; expansion beyond 100 supported |
| C-16 | R09 / 07 | Green booked/occupied, red available and distinct accessible labels |
| C-17 | R04/I02 / 04/12 | Insurance/government/employer declaration and evidence capture |
| C-18 | I02 / 04/12 | Payer, reported/verified limit and AYUSH status; unknown not zero |
| C-19 | I01–I06/A03 / 12 | Cashless/reimbursement status and claim/settlement kept separate |
| C-20 | R04/D02/P01/P02/N02/T04/A03/I02 / 04/05/10/12 | Shared permitted payer strip follows encounter across portals; forbidden fields/docs withheld |

Every implementation task includes its mapped C/O acceptance cases in addition to named regression tests. A desired capability whose release is undecided remains visibly undecided, never silently removed.

## 2. Workflow and the planning gate

### Project planning gate — required before product scaffolding/code

- [x] Owner reviewed the direction and explicitly requested team implementation; current active slice frozen separately, later release details remain reviewable.
- [ ] For each active-release page/action below, field rules, permissions, state transitions, data ownership and failures are reviewed. A future-only page is explicitly deferred, not silently missing.
- [ ] Security/access/IP/MCP/backup design receives an independent review and findings are resolved.
- [ ] Role/branch/data-category matrix, financial/stock invariants and API contracts are frozen for the first vertical slice.
- [ ] Each active capability/page action is mapped to a versioned OpenAPI operation with request/response/errors/permission rules; no hidden UI-only feature or frontend-authoritative business rule.
- [ ] Representative role-task walkthroughs validate plain labels, clear next action and understandable errors; identified confusion is addressed before release.
- [ ] Business parameters for that release are supplied or a configurable safe behaviour is explicitly agreed; no hidden clinical/accounting guesses.
- [ ] Multiple pre-code scenario/threat/test-design reviews are recorded, including negative cases and fixtures.
- [ ] Supported dependency versions, initial cloud strategy, local/staging isolation and tooling are documented before related implementation.
- [ ] Remaining pages have explicit deferred release status or complete detail; no unplanned page/feature is coded.

This document is allowed to be drafted now. Unreviewed proposed defaults do not become owner approvals. Do not use questions about deferred call-center details or premises compliance to hold this gate open. Rented premises do not determine patient room tariffs.

### Per-task execution sequence

1. Complete/update the task's exact design and interfaces in plan.md and HMS.md.
2. Check requirements/permissions; check threats/failure paths; design fixtures/assertions; write failing executable tests and verify the intended failure when the runtime exists.
3. Code the smallest implementation that fulfils those tests and contracts.
4. Run relevant unit/integration/UI/security tests, review, repair, and rerun affected checks.
5. Update actual evidence and status in both documents; review diff/secrets; commit/push and verify remote SHA.

Multiple testing before coding includes specification/scenario/threat/test-design validation and the red-test stage. It does not imply runtime tests can pass before the feature exists. Documentation-only work gets coverage/link/review checks, not invented application test results.

## 3. Review focus: cross-cutting failure classes

| Failure class | Required behaviour | Owning task/test |
|---|---|---|
| Spoofed IP/proxy chain or direct-origin access | Deny network-policy bypass across HTTP, MCP, assets and reconnects | Task 03 / `test_forwarded_header_does_not_bypass_policy` |
| Shared identity crossing branch/agent boundaries | Authorise both matching and disclosed fields; no guessed-ID leak | Tasks 02/04/16 / `test_branch_and_agent_projection_isolation` |
| Duplicate/out-of-order delivery and concurrent writes | One valid outcome; no double bed/stock/receipt; reject stale writes | Tasks 05/07/10/11 / concurrency/idempotency suites |
| Module restore missing shared dependencies or credentials | Reject unsafe snapshot; never blind-overwrite live data | Task 13 / `test_module_restore_rejects_missing_dependencies` |
| AI/client/attachment asking to expand privilege | Treat content as data; server permissions/confirmation remain authoritative | Task 15 / `test_tool_content_cannot_grant_authority` |

## 4. Planned repository map

All paths are proposed until implemented. Keep feature logic together; no dependency installation or source scaffolding occurs in the documentation task.

```text
HMS.md                         living product/architecture/change reference
plan.md                        reviewed catalogue, contracts, tasks and evidence
AGENTS.md                      enforceable developer/agent workflow
docs/research/                 preserved research provenance
docs/decisions/                dated decisions referenced from HMS.md
backend/pyproject.toml         pinned Python dependencies/tooling
backend/config/                environment config, root URLs, jobs, ASGI
backend/apps/platform/         organisations, branches, staff, access context
backend/apps/security/         IP policies, MFA/session orchestration, auditing
backend/apps/patients/         identity, contacts, duplicate review, documents
backend/apps/reception/        appointments, check-in, queues
backend/apps/clinical/         notes, orders, prescription versions, rounds
backend/apps/admissions/       beds, reservations, allocations, transfers, exit
backend/apps/therapy/          courses, resource bookings, performance
backend/apps/nursing/          care tasks, administrations, handover
backend/apps/inventory/        products, batches, locations, movements, returns
backend/apps/finance/          tariffs, packages, charges, invoices, money ledger
backend/apps/coverage/         payer verification, pre-auth, claims, settlements
backend/apps/operations/       cleaning, maintenance, diet instructions
backend/apps/dataops/          backup manifests, restore staging, import/export
backend/apps/integrations/     outbox, external IDs, delivery/reconciliation
backend/apps/mcp/              MCP transport, scoped tools, confirmations
backend/apps/reporting/        bounded reporting/projections and definitions
backend/tests/                 cross-module access/concurrency/recovery tests
frontend/package.json          pinned frontend dependencies and commands
frontend/src/app/              route tree, authenticated shell, providers
frontend/src/features/         one folder per portal/domain, API and components
frontend/src/shared/           UI primitives, forms, state/error handling
frontend/tests/                component/accessibility/contract tests
docs/api/                     versioned OpenAPI contracts and compatibility policy
e2e/                          connected patient and platform journeys
infra/                        reviewed cloud/network/IaC/deployment config
scripts/                      safe validation/operations tooling
.github/workflows/            checks, documentation gate, controlled delivery
```

Each backend app owns `models.py`, `services.py`, `selectors.py`, `api.py`, `tests/` or an equivalent focused split. API handlers validate/authorise and call services; database mutation is not duplicated in MCP tools/import jobs.

## 5. Common UI contract for every page

- Non-negotiable owner requirement: simple, professional and role-focused. Familiar hospital vocabulary, consistent navigation/actions, restrained visuals, readable spacing and one clear primary next step per task.
- Show essential fields first, optional details on demand; explain results/corrections/next steps in plain language. Never hide patient identity, safety alerts, financial consequences or required confirmations to make a page look simpler. Keep implementation jargon out of end-user flows.
- Authenticated shell: explicit organisation/branch, staff identity, role, navigation, task notifications and session status; master-admin cross-branch context is conspicuous.
- Patient pages: UHID and two appropriate identifying details visible before care/financial actions; identifiers never imply authority to view.
- Relevant patient/encounter views share a permission-filtered payer strip: payer label, payment mode, verification/AYUSH/pre-auth status and checked-at time. Doctor sees relevant coverage/document tasks; pharmacy sees authorised item-billing restrictions. Policy numbers, claim amounts and attachments require separate grants. Unknown/absent coverage is explicit; financial denial cannot change a clinical order.
- Tables: server-side filters, sort allowlist, pagination, bounded result counts, saved view only within the user's scope, column visibility without privilege escalation.
- Forms: labelled fields, required/optional rules, unit/date/currency cues, validation summary plus field errors, draft/unsaved-change handling and explicit success/conflict outcomes.
- Every page plans loading, empty, denied, validation, server failure, stale/conflict, expired-session and offline states. Do not show private record existence in unauthorised errors.
- Keyboard navigation and visible focus; normal text contrast at least 4.5:1; no colour-only state; reduced motion; usable 375/768/1024/1440 widths where the workflow is offered.
- Desktop-first dense clinical workspaces with responsive task views; mobile does not expose unsafe truncated actions. Accessible alternative to drag/drop and calendar interaction.
- Printing has approved content, version/author identity, page breaks and controlled access. Production self-hosted/approved fonts/assets; no unnecessary third-party requests from clinical screens.
- Preview/confirm for high-impact operations; server rechecks authorisation, version and confirmation. Disabled buttons alone are not enforcement.

UI/UX Pro Max research: healthcare query's marketing/neumorphic output rejected; narrower enterprise minimal/high-contrast style considered suitable as a direction. Specific branding/palette remains a review decision. Use outcome-focused validation guidance from its UX search; do not copy landing-page layouts into staff portals.

## 6. Page catalogue — master admin and shared access

Legend: `MA` master admin; `SEC` delegated security operator; `DATA` delegated backup/import/export operator; `CLIN` clinician; `REC` reception; `ACC` accounts; other abbreviations match portal names. Permission is always action + branch + data category, not the abbreviation alone. UI tests use page ID; control suites are in section 11.

| ID / route | Fields and information | Actions/functions | Access and acceptance emphasis |
|---|---|---|---|
| S01 `/login` | Identifier, password, generic errors, challenge status | Authenticate, MFA transition, throttled retry | No user enumeration; network policy applies before private content |
| S02 `/auth/mfa` | Challenge, recovery option | Verify, enrol when required, controlled recovery | Replay/expiry/rate limits; never bypass MFA with a recovery link |
| S03 `/auth/recover` | Account request, verified recovery step | Request/reset through selected identity flow | Generic response, expiring one-use tokens, revoke affected sessions |
| S04 `/me` | Profile, assigned roles/branches, preferences | Edit permitted profile/preferences | Cannot self-grant roles or change verified identity unchecked |
| S05 `/me/security` | MFA, session/device list, last activity | Revoke session, rotate credentials, MFA management | Step-up, protect current admin recovery, audit |
| S06 `/work` | Scoped due work, alerts and handoffs | Filter, acknowledge, open task | No cross-portal/branch disclosure; retries do not double-acknowledge |
| S07 `/notifications` | Scoped notifications and timestamps | Read/acknowledge, retry failed delivery if delegated | No patient data in unauthenticated notification links |
| S08 `/access-denied` | Generic policy outcome and support reference | Return, sign out | No whitelist contents, patient existence or infrastructure leak |
| M01 `/admin` | Branch/portal health, work queues, security/job summaries | Drill into permitted pages | MA aggregate permission; no full clinical chart by default |
| M02 `/admin/organisation` | Display/legal-document identity config, timezone, numbering | Edit/version approved settings | Step-up for critical numbering; no historical bill rewrite |
| M03 `/admin/branches` | Branch code/name/contact/status, scope | Create/edit/activate/archive, assign access | New branches need no code/database fork; protect referenced history |
| M04 `/admin/staff` | Staff identity, department, employment status, branch grants | Invite, activate/deactivate, session revocation | Individual identity; cannot disable last recovery-capable MA blindly |
| M05 `/admin/permissions` | Role/action/data/branch matrix, grant history | Preview/grant/revoke, simulate access | Least privilege, delegated ceilings, no self-escalation |
| M06 `/admin/security/ip-rules` | Mode, IP/CIDR, scope, purpose, expiry, denies | Validate/add/edit/disable, allow verified current IP | Trusted client address, deny precedence, IPv4/IPv6, audit |
| M07 `/admin/security/policy-preview` | Effective policies, current-path impact, rollback deadline | Test selected identity/path; confirm timed change | Step-up; lost access triggers rollback; no unauthenticated bypass |
| M08 `/admin/security/events` | Login/access/grant/IP events, redacted metadata | Filter, investigate, revoke session | SEC scoped access; bounded export requires own grant |
| M09 `/admin/backups` | Full/module jobs, scope, encryption/checksum/version metadata | Request, monitor, cancel pending jobs, authorised download | DATA privilege, step-up, private archives; no secrets in downloads |
| M10 `/admin/backups/:id` | Manifest, dependency counts, protected file inventory | Inspect/verify, initiate restore preview | Same access ceiling as backup contents; manifest tamper detection |
| M11 `/admin/restores` | Staged archive, compatibility, conflicts, impact and approval | Validate/preview/approve isolated restore/cutover | No direct live overwrite; pre-restore recovery point; failed checks block |
| M12 `/admin/imports` | Dataset/template/schema version, scope, rows/errors/mapping | Upload scan, dry-run, deduplicate, approve/resume | No direct signed-order/final-invoice override; transactional/chunked policy |
| M13 `/admin/exports` | Dataset/columns/scope/purpose, status/expiry | Preview/request/download/revoke | Row/field restrictions, formula-injection protection, no blanket MA data grant |
| M14 `/admin/masters` | Departments, doctors, products, therapy/resources, service masters | Scoped editors, effective-dated activation/versioning | Referenced records archive; record field/unit constraints per master |
| M15 `/admin/templates` | Prescription/consent/discharge/billing templates, version and language | Draft/preview/publish/retire | Clinical templates published only with clinical authority; safe rendering |
| M16 `/admin/integrations` | Connector status, scopes, delivery failures, external ID namespace | Register/disable, rotate references, replay permitted events | Secrets stored securely, not displayed; call-center connector deferred |
| M17 `/admin/mcp/clients` | Client identity, grant/scopes, allowed tools, network context | Authorise/revoke/disable, view compatibility results | OAuth/user delegation and organisation ceiling; no shared MA token |
| M18 `/admin/mcp/activity` | Redacted tool calls, actor, branch, confirmation/result | Filter, investigate, revoke client/tool | No raw clinical prompt logging by default; no SQL/shell tool |
| M19 `/admin/jobs` | Import/report/backup/event jobs, progress and failure reason | Cancel/retry authorised job | Idempotent retry; no arbitrary job payload editing/execution |
| M20 `/admin/audit` | Sensitive access and immutable change references | Filter/drill/restricted export | Audit reader cannot amend history or access all referenced charts |
| M21 `/admin/platform` | Settings versions, service/queue/backup health, runbooks | View/check, reviewed maintenance actions | No public environment dump, credentials or command console |
| M22 `/admin/retention` | Dataset policy, archive/legal-hold flags where supplied, expiry jobs | Preview/approve policy and pending actions | No blind automatic clinical deletion; DATA/SEC separation and audit |

Permission/masters/template editors are named subviews of the listed pages; adding a new editor requires its own field/action/test details before coding. No hidden unplanned settings page is exempt.

## 7. Page catalogue — hospital portals

| ID / route | Fields and information | Actions/functions | Access and acceptance emphasis |
|---|---|---|---|
| R01 `/reception` | Today queue/appointments, unscheduled therapy, admission requests | Open task, doctor/date filter | Branch scope; clear stale/live status |
| R02 `/patients` | Name/contact/legacy/UHID search, matching suggestions | Bounded search, create patient | Shared phone allowed; authorised matching, no automatic merge |
| R03 `/patients/new` | Name; DOB or approximate age if known; contact/address and optional context | Quick register, duplicate review | No fake DOB for unknown age; mandatory clinical fields reviewed |
| R04 `/patients/:id` | Permitted demographics, visits, allergies/alerts by grant, documents and payer summary | Edit demographics, open encounter, upload permitted document | Reception history labelled patient-reported; sensitive tabs separately granted |
| R05 `/appointments` | Branch/doctor/date/time/type/status, referral ID | Book/reschedule/cancel/check-in | Slot policy, duplicate/retry protection, no forced CRM lead |
| R06 `/queue` | Token/check-in/doctor/wait/state | Assign/reassign/call/mark no-show | Encounter separate from appointment; audit reassignment |
| R07 `/reception/therapy` | Approved sessions awaiting schedule, count/resources | Book/reschedule, contact task | Cannot change clinical procedure/dose |
| R08 `/admissions/new` | Patient, treating doctor/reason, attendant, payer, estimate/deposit references | Create/confirm admission | Exact authority configurable; bed allocation atomic |
| R09 `/beds` | Room/category/floor, beds, current/future reservations, restrictions | Filter/reserve/allocate/open transfer | Green booked/occupied, red available plus labels; exclusive capacity correct |
| R10 `/reservations` | Resource/date interval/expiry, patient/reference, status | Create/expire/convert/cancel | Future reservations do not replace present occupancy |
| R11 `/admissions/:id` | Stay, bed history, approved care, running financial/coverage summaries | Handover/transfer/coordinate discharge | Permissions per action; no early bed availability |
| R12 `/follow-ups` | Due appointment/therapy callback, assigned staff/outcome | Assign/complete/rebook | Basic operational follow-up only; no call-center build implied |
| D01 `/doctor` | Assigned OPD/IPD and pending review work | Open consultation/rounds | Care-context and branch restrictions |
| D02 `/doctor/encounters/:id` | Reviewed history, vitals, allergies, diagnosis, notes, previous orders and permitted payer/verification strip | Draft/save/review/sign/amend consultation; open permitted evidence tasks | Signed versions immutable; no auto-sign; financial status does not alter clinical authority |
| D03 `/doctor/encounters/:id/prescription` | Medicine strength/dose/unit/route/frequency/duration/quantity; Anupana/instructions; therapy course | Draft typed/upload/voice, validate/approve/amend orders | Extraction remains draft; independent medicine/therapy routes |
| D04 `/doctor/admissions/:id/rounds` | Daily notes, vitals, current instructions and pending care | Add/sign rounds, revise/stop future orders | Preserve already delivered/dispensed/administered records |
| D05 `/doctor/reviews` | Nursing/therapy/test alerts and documents needing acknowledgement | Review/acknowledge/request action | Ownership and urgent escalation policy configurable |
| D06 `/doctor/admissions/:id/discharge` | Course, diagnosis, follow-up, take-home orders and summary | Draft/review/sign/amend summary | Clinical sign-off does not clear finance or free bed |
| D07 `/doctor/templates` | Permitted clinical templates and optional Ayurveda assessments | Save personal draft/use approved template | Review per patient; no uncontrolled mandatory-field expansion |
| D08 `/doctor/drafts` | Upload/voice drafts, source, extraction status/errors | Compare/edit/approve/discard, retry allowed job | No external processor disclosure without approved configuration |
| T01 `/therapy` | Assigned sessions, readiness and escalation | Open/start eligible session | Assignment/context permissions |
| T02 `/therapy/calendar` | Staff/room/equipment/time, buffers and leave | Schedule/move/cancel resources | All required resources reserved atomically; keyboard alternative |
| T03 `/therapy/courses/:id` | Ordered/scheduled/completed/missed counts and order version | Review schedule, follow-up task | Counts distinct; future stop does not erase completion |
| T04 `/therapy/sessions/:id` | Readiness, actual start/end, actual procedure/material quantity, observations | Start/complete/stop/escalate/correct | Clinical protocol supplied by leadership; correction attributable |
| T05 `/therapy/materials` | Session materials by batch/location and wastage | Record use/return/request stock | Unit conversion and stock/finance policies respected |
| N01 `/nursing` | Ward census, shift tasks, pending admissions/discharges | Accept handover/open care | Branch/ward/context grants |
| N02 `/nursing/admissions/:id` | Vitals/charts, orders, precautions, care plan | Record observations/care, escalate | Actual time separate from entry time; versioned correction |
| N03 `/nursing/medications` | Due/given/held/refused/missed/PRN dose, reason, authorised order | Record administration or reason | Supply is not administration; duplicate prevention and changed-order handling |
| N04 `/nursing/handovers` | Shift, patient problems/tasks, handover acknowledgements | Prepare/acknowledge/escalate | Retain historical sign-off and actual identity |
| N05 `/nursing/discharges` | Preparation, take-home instruction acknowledgement and tasks | Complete checklist, flag pending care | Does not substitute doctor approval/financial clearance |
| P01 `/pharmacy` | Approved pending issues, shortages, alerts and permitted payer status per encounter | Open prescription/issue | No independent clinical change; claim attachments hidden without grant |
| P02 `/pharmacy/issues/:id` | Order, pending quantity, product/batch/location/expiry, actual supply, payer strip and authorised item billing restrictions | Partial/full dispense, request substitution | No oversupply/expired batch; atomic stock/charge handoff; no automatic order change on rejection |
| P03 `/pharmacy/stock` | Product, units, batch, expiry, usable/quarantined/location quantity | Filter/count/transfer | FEFO preference; no negative stock via race |
| P04 `/pharmacy/products` | Formulation, strength, units/conversions, price/tax references | Create/version/retire | Clinical/product master edit authority separate |
| P05 `/pharmacy/purchases` | Supplier, received items/batch/expiry/quantity/cost, discrepancies | Draft/approve receipt, supplier return | Receive once; preserve movements; stock opening separately identified |
| P06 `/pharmacy/returns` | Original issue, quantity/reason, inspection status | Accept/quarantine/restock/credit request | Financial credit independent from usable restock |
| P07 `/pharmacy/movements` | Purchase/issue/ward transfer/use/return/write-off ledger | Trace/reconcile/authorised adjustment | No ledger deletion; reasons and permissions |
| P08 `/pharmacy/alerts` | Expiry, low stock, recall/block status | Acknowledge/block/reorder task | Blocked batch cannot issue through API/import |
| A01 `/accounts` | Charges, collection, advances, dues, refunds and closing | Drill into separate metrics | No misleading combined revenue/collections figure |
| A02 `/accounts/estimates` | Patient/encounter, tariff, services/packages, validity | Draft/version/issue estimate | Estimate not invoice; no automatic payment obligation |
| A03 `/accounts/admissions/:id` | Running charges, deposits, allocations, payer split | Review/reconcile/request charge adjustment | Source links, no duplicate package charge |
| A04 `/accounts/invoices` | Draft/final/credited invoices, series, scope | Draft/review/finalise/issue adjustment | Final versions preserved; decimal rounding and branch series |
| A05 `/accounts/payments` | Method, reference, amount, allocation and state | Receive/allocate/reconcile | Idempotent callback/manual entry; advance distinct |
| A06 `/accounts/refunds` | Original transaction, amount/reason, approver/beneficiary | Request/approve/execute/reconcile | Authority limits, step-up, no self-approval if policy requires separation |
| A07 `/accounts/packages` | Versioned inclusions/exclusions/nights/sessions/extras | Configure/assign/consume/review unused entitlement | Agreed cancellation/upgrade rules before execution |
| A08 `/accounts/tariffs` | Self-pay/payer rates, effective periods and rules | Draft/approve/version | No retrospective rewrite of final bills |
| A09 `/accounts/closing` | Shift opening, method totals, expected/actual variance | Close/reconcile/approve variance | Receipts retained; controlled reopening |
| A10 `/accounts/discharge-clearance` | Pending issues/returns/charges/deposits/payer decisions | Reconcile/record clearance or authorised exception | Not physical exit or payer settlement |
| I01 `/insurance` | Verification/pre-auth/query/claim follow-ups | Assign/open cases | Claims desk grant only; scoped clinical evidence |
| I02 `/insurance/coverage/:id` | Policy/member/relation/validity, limits, AYUSH, entitlement, evidence/verifier | Record/verify/version snapshot | Unknown is not zero; patient-reported versus verified |
| I03 `/insurance/authorisations/:id` | Estimate, submitted documents/ref, query, approved amount/expiry | Submit manually/record query/respond/enhance | No implied live payer API or guarantee of payment |
| I04 `/insurance/claims/:id` | Submitted lines, evidence, status/query, deductions | Assemble/submit/reconcile/appeal | Patient liability reviewed, no automatic rejection-to-patient assignment |
| I05 `/insurance/settlements` | Claim, remittance, allocation/deduction/outstanding | Record/allocate/reconcile/close | Approval distinct from received amount; survives discharge |
| I06 `/insurance/payers` | Payer/TPA/scheme, agreement validity/service scope/tariff refs | Configure/version supplied agreement | No independent premises/empanelment investigation |
| H01 `/operations/cleaning` | Bed/room, departed patient reference restricted, staff/times | Assign/start/complete/confirm ready | Physical exit first; avoid clinical info on housekeeping screen |
| H02 `/operations/maintenance` | Resource restriction, reason, start/expected end/status | Block/request repair/reopen | Occupancy and restriction can coexist; audited override policy |
| H03 `/operations/diet` | Doctor-approved meal instructions and restrictions | Acknowledge service/instruction | Minimum scope only; detailed kitchen stock deferred |
| G01 `/management` | Defined OPD/IPD/therapy/stock/finance/claims metrics | Scoped filter/drill/report request | Census denominator and time filters explicit |
| G02 `/reports` | Allowed report catalogue, parameters, queued jobs | Preview/generate/download | Bounds, permissions, fresh/stale label; background isolation |

### Future-only call-center/patient pages — planned boundaries, not current implementation

| ID / conceptual route | Intended future capability | Current work |
|---|---|---|
| F01 `/crm/agent` | Assigned referrals and patient journey outcomes | Define permitted projection and event contracts only |
| F02 `/crm/referrals/:id` | Origin/current agent, campaign, appointment/visit outcome and authorised financial summary | Stable IDs and immutable attribution history; connector deferred |
| F03 `/patient` | Approved patient documents/appointments/receipts | No patient portal build in the initial slice; separate auth/privacy review |

Before activating any future page, add complete fields/actions/states/tests and review it through the same gate. No call-center product/API question is required for current hospital design.

## 8. Proposed service/API contracts

These are design contracts to review/freeze before implementation. Function bodies are intentionally not written in a planning task. Exact endpoint naming belongs to the owning task and must be recorded before coding; no generic catch-all mutation endpoint.

**API-first for every feature, not only external integrations.** Before each task, add/update `docs/api/openapi-v1.yaml` with operation IDs, paths, schemas, permission rules, error cases, pagination/filter limits, idempotency/version handling and job/file lifecycle. Map each page action to an operation ID. UI components consume typed API clients; no direct database access or authoritative clinical/financial state mutation in frontend code. Asynchronous work has authenticated job-status/cancel/result contracts as appropriate; private files use authorised upload/download flows.

MCP maps its bounded tools to the same capability contracts and services. In-process adapters/jobs may call services without HTTP loopbacks, but cannot bypass authentication context, IP/branch/data permissions, validation or audit. The capability's API must still exist and be tested independently of the UI. Internal infrastructure-only code is not exposed as an unnecessary public operation.

Version OpenAPI and generated client types together; gate contract-breaking changes and require an explicit version/migration plan. APIs are authenticated/authorised by default; 'API-based' never means anonymous public data access. Django admin is not an alternative unplanned product workflow.

### Shared types and response rules

`UUID`, timezone-aware `datetime`, decimal quantity/money, `CurrencyCode`, enumerated status and explicit version integer. Proposed immutable request/result dataclasses below are owned by `backend/apps/platform/contracts.py` or the owning domain's `contracts.py`.

- `AccessContext(actor_id, organisation_id, branch_ids, permissions, auth_strength, client_id?, verified_client_ip, request_id)` is server-derived, never trusted from request JSON.
- `PageRequest(cursor?, limit, filters, sort)` -> `PageResult(items, next_cursor, freshness_at)`; default 25, maximum 100 as an initial engineering choice, subject to review.
- `MutationResult(entity_id, version, audit_event_id)`; stale `expected_version` returns conflict without partial writes.
- `ConfirmationIntent(id, actor_id, action, payload_hash, expected_version, expires_at, consumed_at?)` is server-stored and one-use.
- API errors use stable `code`, safe `message`, optional authorised field errors and `request_id`; deny responses do not disclose private record existence. Financial webhooks use their own signed/idempotent contracts.
- All lists/objects require object and field authorisation, not only a global 'logged in' check. Browser transport uses secure session/CSRF flow; remote MCP uses reviewed OAuth.

| Owning path | Function signature / result | Invariants |
|---|---|---|
| `security/ip_policy.py` | `evaluate_ip(ctx: NetworkContext, policy: EffectiveIPPolicy) -> IPDecision` | Normalise addresses; deny overrides; trusted proxies only; no per-visitor auto-allow |
| `security/policy_changes.py` | `preview_policy_change(ctx: AccessContext, command: PolicyChange) -> PolicyPreview`; `confirm_policy_change(ctx, preview_id: UUID, confirmation_id: UUID) -> MutationResult` | Step-up, current-path test, rollback deadline, audit |
| `platform/authorization.py` | `authorize(ctx: AccessContext, action: str, resource: ResourceRef) -> None` | Reject unauthorised branch/data/action; no user-supplied context escalation |
| `patients/services.py` | `register_patient(ctx, command: RegisterPatient, idempotency_key: str) -> PatientResult`; `search_patients(ctx, query: PatientQuery, page: PageRequest) -> PageResult` | Shared phones; safe matching; stable IDs; field masks |
| `reception/services.py` | `book_appointment(ctx, command: BookAppointment, idempotency_key: str) -> AppointmentResult`; `check_in(ctx, appointment_id: UUID, expected_version: int) -> EncounterResult` | No duplicate visit on retry; walk-in supported |
| `clinical/services.py` | `save_draft(ctx, command: NoteDraft, expected_version: int) -> NoteResult`; `approve_orders(ctx, draft_id: UUID, expected_version: int, idempotency_key: str) -> ApprovedOrderSet` | Clinical signer, immutable approved version, atomic departmental event handoff |
| `admissions/services.py` | `allocate_bed(ctx, command: AllocateBed, idempotency_key: str) -> AllocationResult`; `transfer_bed(ctx, command: TransferBed, expected_version: int) -> AllocationResult` | Conflicts/exclusivity rejected; historical intervals preserved |
| `therapy/services.py` | `schedule_session(ctx, command: ScheduleSession, idempotency_key: str) -> SessionResult`; `record_performance(ctx, command: SessionPerformance, expected_version: int) -> SessionResult` | Resource conflict protection; ordered/actual separate |
| `nursing/services.py` | `record_administration(ctx, command: Administration, idempotency_key: str) -> AdministrationResult` | Authorised order/dose, held/refused reason, no duplicate administration |
| `inventory/services.py` | `dispense(ctx, command: Dispense, idempotency_key: str) -> DispenseResult`; `inspect_return(ctx, command: InspectReturn, expected_version: int) -> ReturnResult` | Lock usable batch stock; partial supply; no automatic unsafe restock |
| `finance/services.py` | `post_charge(ctx, command: Charge, source_event_id: UUID) -> ChargeResult`; `record_receipt(ctx, command: Receipt, idempotency_key: str) -> ReceiptResult` | Decimal amounts; one source charge; explicit funding/allocation; immutable corrections |
| `coverage/services.py` | `record_authorisation(ctx, command: AuthorisationUpdate, expected_version: int) -> AuthorisationResult`; `allocate_settlement(ctx, command: Settlement, idempotency_key: str) -> SettlementResult` | Verified evidence and state tracks; approval != receipt |
| `coverage/selectors.py` | `get_coverage_summary(ctx: AccessContext, encounter_id: UUID) -> CoverageSummary` | Server grants choose returned fields; includes explicit unknown/pending state, payer/mode/status/check time and permitted item restrictions; no clinical mutation |
| `operations/services.py` | `record_exit(ctx, admission_id: UUID, expected_version: int) -> ExitResult`; `confirm_ready(ctx, cleaning_task_id: UUID, expected_version: int) -> ResourceResult` | Exit/cleaning/readiness sequence, authorised exceptions audited |
| `dataops/backups.py` | `request_backup(ctx, command: BackupRequest) -> JobRef`; `validate_archive(ctx, archive_id: UUID) -> ArchiveValidation` | Scope/dependency manifest/checksums; no key exposure |
| `dataops/restores.py` | `preview_restore(ctx, command: RestoreRequest) -> RestorePreview`; `execute_restore(ctx, preview_id: UUID, confirmation_id: UUID) -> JobRef` | Isolated validation, approved cutover, conflicts not silently overwritten |
| `dataops/transfers.py` | `dry_run_import(ctx, command: ImportRequest) -> ImportPreview`; `commit_import(ctx, preview_id: UUID, confirmation_id: UUID) -> JobRef`; `request_export(ctx, command: ExportRequest) -> JobRef` | Row/field scope; preview hash; bounds; no final-record bypass |
| `integrations/outbox.py` | `append_event(transaction, event: DomainEvent) -> UUID`; `deliver_event(event_id: UUID) -> DeliveryResult` | Durable handoff, retry/dedup, ordering/version checks |
| `mcp/services.py` | `invoke_tool(ctx, tool_name: str, arguments: dict, idempotency_key: str | None) -> ToolResult` | Typed validated catalogue, same authorisation/services, never arbitrary execution |

### State lifecycle planning

- Clinical draft -> approved -> amended/superseded; new version rather than overwrite.
- Session ordered -> scheduled -> arrived -> started -> completed/stopped; missed/postponed/cancelled with reasons; no false completion count.
- Admission pending -> active -> discharge-in-progress -> physically exited; clinical/financial/claims subtracks independent.
- Resource physical occupancy, reservation and restriction stored separately; derive a mutually exclusive current display bucket including exclusive-blocked capacity where needed.
- Dispense pending -> partially supplied -> supplied; return is a linked movement/inspection flow.
- Invoice draft -> final -> linked credit/adjustment; receipt initiated -> confirmed/failed/reversed, with separate refund flow.
- Backup queued -> running -> verifying -> complete/failed/cancelled; restore cannot begin from unverified archive.
- Import uploaded -> scanning -> preview -> approved -> applying -> completed/failed/reconciled; partial commit policy must be explicit per dataset.

## 9. IP/network and cloud design

Production proposal: private data plane; HTTPS edge with WAF/rate limits; trusted proxy overwrites forwarded headers; origin reachable only from approved edge/service paths. Browser/MCP paths require authenticated identity and effective network permission. Cloud access is remote access through these controls, not public anonymous access.

`allow_authenticated` still enforces identity/permissions and blocklist. `allowlist_only` adds address/CIDR membership. Deny takes precedence; inherited policies intersect. Initial production bootstrap requires explicitly supplied approved admin network and recovery process before enforcement; never auto-open the system if no list is configured.

Provide 'allow my verified current public IP', address validation, scope/expiry/purpose, effective-policy preview and timed rollback. The phrase 'app IP' is not implemented as trusting the server's IP or automatically allowing all incoming users. Confirm meaning only when configuring a real rule.

Test IPv4, IPv6, mapped-address normalisation, CIDR boundaries, disabled/expired rules, simultaneous updates, spoofed headers, changing user IP, direct origin, nested policy restrictions, long-lived streams, file downloads, MFA/bootstrap and lockout recovery.

MCP clients may use different egress than browser users. Require an approved gateway/network path or narrow explicitly approved integration setting that respects organisation policy. If unavailable, connection is denied; no wildcard rule to make ChatGPT/Claude work.

Cloud provider selection must document network topology, regional storage, key/secrets services, availability/recovery targets, logging, costs and operations owner. No paid resources/deployment occurs in this documentation phase. Protect CI identities; isolate environments; no real production records in previews.

## 10. MCP tool plan

Remote HTTP MCP must implement the supported protocol's authorisation/discovery/audience/resource requirements; pin SDK/protocol and validate selected clients. Reference: [MCP authorisation](https://modelcontextprotocol.io/specification/latest/basic/authorization) and [security guidance](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices). No promise of compatibility with every client/version.

| Planned tool | Scope / arguments | Output / mutation limit |
|---|---|---|
| `patients.search` | `patients:read`; bounded query, cursor, permitted branch | Masked allowed identities; no bulk clinical chart |
| `patients.summary` | `patients:summary`; patient ID and context | Only approved permitted summary fields |
| `appointments.list` | `appointments:read`; branch/date/patient filters | Bounded appointments |
| `appointments.create` | `appointments:write`; reviewed slot/patient/type, idempotency key | Booking through shared service; explicit user-authorised action |
| `appointments.reschedule` | `appointments:write`; ID/version/new slot/key | Conflict checked, audited history |
| `beds.availability` | `beds:read`; branch/category/date interval | Availability, no unrestricted named census |
| `finance.summary` | `finance:summary`; permitted patient/encounter | Defined billed/collected/advance/outstanding fields |
| `tasks.create_followup` | `tasks:write`; permitted subject/assignee/due/reason/key | Operational task only, no care order |
| `clinical.create_draft` | `clinical:draft`; authorised encounter, draft content/key | Unsigned draft, never approval/prescription release |
| `jobs.status` | `jobs:read`; caller-owned/permitted job | Safe status, no credentials/unrestricted download URL |

Clinical signing, refund execution, restores, broad exports and access/IP changes are initially UI-only controlled operations, not autonomous MCP tools. Additions require dedicated design, scopes, server-enforced approval and tests. Server-stored confirmation binds actor/action/payload hash/state version/expiry and is single-use; clients cannot grant themselves authority with a flag. Tool descriptions and data never override policy.

## 11. Security/test catalogue

Use OWASP authorisation guidance as a reference, not a compliance badge: [authorisation cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

| Suite | Pre-code multiple-check topics | Post-code required evidence |
|---|---|---|
| V01 identity/access | Role/data/branch matrix; grant escalation and recovery scenarios | Unit/API tests, guessed IDs, field masks, session revocation, MFA recovery |
| V02 network/IP | Proxy trust boundaries, deny precedence, lockout/recovery | Request-level spoofing/origin/download/MCP/IPv6 tests |
| V03 clinical | Draft/approval/amendment, wrong patient/version, changed future care | API/UI tests; delivered history preserved; no unreviewed extracted order |
| V04 resources | Overlapping beds/rooms/villas/therapists/equipment and time boundaries | Real PostgreSQL concurrent tests, atomic failure/no duplicate allocation |
| V05 inventory | Units/batches/expiry/returns/ward custody and retries | Real transaction/concurrent issue tests, movement reconciliation |
| V06 finance | Decimal rounding, packages, deposits, retries, discounts/refunds and payer splits | Ledger/receipt/reversal reconciliation, concurrency and duplicate-callback tests |
| V07 dataops | Archive dependencies, keys/files, restore collisions, import/export abuse | Tamper/cross-branch tests, isolated restore drill, formula-injection and signed-download authorisation |
| V08 MCP | Scope/audience/token/IP/client threats, prompts, confirmation replay | Protocol/client tests, revoked/expired/wrong-audience tokens, unauthorised tool/field denial |
| V09 UI/accessibility | All page states, patient identity, plain labels, next-action clarity, keyboard/error/print flows | Component/e2e checks, manual keyboard/contrast/print review and representative staff-task walkthroughs with confusion/wrong-turn findings resolved |
| V10 reliability/scale | Mixed clinical/CRM/import/report peaks, queue backlog, recovery targets | Realistic-cardinality latency/error/queue/connection results, worker failure/replay and restore/failover exercises |
| V11 supply chain/cloud | Secrets, dependency sources, IaC/edge/storage and CI identities | Secret/dependency/static scans, staging DAST, cloud configuration review |
| V12 documentation | Owner ID/page/task coverage, links, status and no sensitive data | Link/coverage/diff review; HMS.md updated in every change set |
| V13 API-first coverage | Every page action/capability maps to a documented operation; no adapter bypass or UI-only mutation | OpenAPI validation, typed-client/schema checks, independent API journeys, backward-compatibility checks and API/UI/MCP permission/result parity |

Release criteria: no unresolved access bypass, critical/high security defect or data-integrity defect; passing relevant checks; independent review; tested backups/recovery; scope-specific staff acceptance. A 'zero breach' promise is not a valid test result. Record residual risks and operational ownership explicitly.

## 12. Dataops and recoverability plan

Full backup covers database/files/versioned manifests and secure configuration/key recovery references. Encrypt at rest/in transit; use isolated credentials/destinations and retention with deletion/immutability policies agreed before production. Proposed manual and scheduled jobs, monitoring and failure alerting. No actual retention/RPO/RTO is invented here.

Portal snapshot scope examples: pharmacy products/batches/movements plus required identifiers; accounts charges/invoices/receipts and referenced encounters; clinical orders/notes plus necessary patient/context; master configuration excluding secret values. Each dataset has an owned schema version, shared dependency list, exportability and restore strategy. Reject 'standalone restore' when dependencies/permissions cannot be satisfied safely.

Import datasets initially proposed: patient identities, branch/resource masters, products/opening stock, active admissions/orders through verified migration paths, opening deposits/receivables and policy references. Each has its own validators; signed notes/final bills never accepted as blind editable CSV records.

Exports initially proposed: scoped patient demographics, pharmacy stock/movements, financial statements, coverage case lists and approved documents. Clinical extraction requires separate permission; portal association does not imply all columns are available.

Restore preview compares schema/app versions, checksums, organisation/branch IDs, parent references, existing final records, units and counts. Require isolated recovery, record-level conflict decisions, step-up approval and an undo/recovery plan. Full cutover uses maintenance mode and prevents concurrent writes; portal reconciliation uses controlled services/transactions. A restore must not replay historical payment/notification events as new live actions.

## 13. Implementation tasks and interfaces

Tasks are proposed delivery boundaries. Each task owns the listed files/tests and the service contracts in section 8. Feature creation waits for the project gate; future task details must be completed/reviewed before their implementation. Examples below name exact regression assertions, not fabricated test results.

### Task 00 — Documentation baseline and publication (current task)

Files: create `HMS.md`, `plan.md`, `AGENTS.md`, `.gitignore`; retain `docs/research/*.md`.
Produces: documented scope, workflow and reviewable design inventory; no product runtime.

- [x] Consolidate baseline and latest owner instructions, including O-01–O-11.
- [x] Draft living reference, page catalogue, security/IP/MCP/dataops contracts and staged tasks.
- [x] Check coverage/local links, inspect for secrets/private data and review consistency; final staged check repeated before commit.
- [x] Independent documentation/security-design review; one Important C-20 traceability gap and two Minor references fixed and corrections verified. This is not an application security audit.
- [x] Record actual verification in HMS.md; initialise/connect Git safely; commit/push and verify remote SHA. Initial local/remote main both `17df5ef52750cfb55ad9d146dbeba1d9d4820699`.

### Task 01 — Foundation, tooling and documentation gate

Files: `backend/pyproject.toml`, `backend/config/{settings,urls,asgi}.py`, `backend/apps/platform/contracts.py`, `frontend/{package.json,tsconfig.json,vite.config.ts}`, `frontend/src/app/`, `docs/api/openapi-v1.yaml`, `.github/workflows/checks.yml`, `scripts/check_project_docs.py`, `backend/tests/test_configuration.py`.
Consumes: approved stack/version/deployment choices; produces runnable synthetic-only local environment and shared types.

- [ ] Freeze versions/tool commands and environment contract; validate plan/threat/test fixtures before coding.
- [ ] Write tests `test_production_rejects_debug_or_missing_secret`, `test_docs_required_for_project_change`, `test_openapi_contract_valid`, `test_page_actions_have_api_operation_mapping`; verify expected failures.
- [ ] Implement minimal settings/schema/types/shell and CI documentation-change check; no real data.
- [ ] Run backend configuration/type/frontend build and documentation-gate tests; review generated files for secrets.
- [ ] Update HMS.md/plan.md; commit `build: establish verified HMS foundation`; push/verify.

### Task 02 — Organisation, branches, identity, permissions, MFA and audit

Partial source evidence: staff-access-contract.md delivered4APIs, core0004active memberships/revision, scoped password-safe UI and current branch controls. ActualPG213passed/25subtests and frontend49passed/build; fresh review consistency findings fixed. MFA/session/recovery/read audit and full Task02remain unchecked. Actual paths backend/apps/core/staff_access.py, authorization.py, core migration0004, frontend/src/StaffAdministration.tsx; future package split remains deliberate.

Files: `backend/apps/platform/{models,contracts,authorization,api}.py`, `backend/apps/security/{models,sessions,audit}.py`, `frontend/src/features/{auth,admin}/`, `backend/apps/platform/tests/test_access.py`, `backend/apps/security/tests/test_sessions.py`.
Consumes: AccessContext and reviewed identity provider/session strategy; produces `authorize()` and server-derived context for every later task. Pages S01–S08, M01–M05, M08/M20/M21.

- [ ] Review role/action/field/branch matrix and recovery threats; design session/grant fixtures.
- [ ] Write red tests asserting `test_branch_and_agent_projection_isolation`, `test_user_cannot_self_grant`, `test_deactivation_revokes_sessions`, `test_master_admin_cannot_sign_without_clinical_grant`.
- [ ] Implement context, secure session/MFA integration, grants and safe audit primitives.
- [ ] Verify direct API/guessed-ID/session/MFA/field tests plus UI states and audit metadata.
- [ ] Update documentation and commit/push `feat: add scoped identity and access controls`.

### Task 03 — IP policy and cloud-edge trust boundary

Partial evidence23October2026: pure resolver/evaluator complete and independently rerun22 tests/25 subtests passed. Request middleware and preview edge/network integration are verified; policy-management UI and timed rollback/recovery remain open; do not mark Task03 fully complete.

Files: `backend/apps/security/{ip_policy,policy_changes,middleware}.py`, `backend/apps/security/tests/test_ip_policy.py`, `frontend/src/features/admin/ip-policy/`, proposed `infra/edge/` config.
Consumes: Task 02; produces section 8 IP evaluation/preview functions. Pages M06/M07 and access-denied behaviour.

- [ ] Review exact/CIDR/inheritance/recovery examples, proxy trust diagram and MCP-egress conflict cases.
- [ ] Write red tests `test_forwarded_header_does_not_bypass_policy`, `test_deny_overrides_allow`, `test_ipv6_boundary`, `test_unconfirmed_policy_rolls_back`, `test_private_download_enforces_policy`.
- [ ] Implement policy, trusted-address resolver and audited timed change workflow; no automatic visitor whitelisting.
- [ ] Exercise browser/API/MCP paths, direct-origin restriction and recovery in staging topology.
- [ ] Update docs and commit/push `feat: enforce trusted network access policies`.

### Task 04 — Patients, protected files, appointments and queues

Files: `backend/apps/patients/{models,contracts,services,selectors,documents,api}.py`, `backend/apps/reception/{models,contracts,services,api}.py`, initial `backend/apps/coverage/{models,contracts,selectors}.py`, their `tests/`, `frontend/src/features/{patients,reception}/`, shared payer-strip component, `e2e/reception.spec.ts`.
Consumes: access/IP/audit; produces register/search/book/check-in and initial `get_coverage_summary()` contracts for downstream portals; Task 12 extends case management. Pages R01–R06/R12.

- [ ] Review fields/duplicates/unknown age/shared phone/document disclosure; design patient and walk-in fixtures.
- [ ] Write red tests `test_shared_phone_is_not_unique_identity`, `test_check_in_retry_creates_one_encounter`, `test_file_access_rechecks_patient_permission`, `test_upload_is_quarantined_until_validated`, `test_payer_summary_filters_ungranted_fields`.
- [ ] Implement scoped identity/search/merge-review, safe uploads, booking/check-in and queue state transitions.
- [ ] Verify record/field isolation, file limits/scan errors, invalid sort/filter, conflict/empty/offline UI and keyboard flow.
- [ ] Update docs and commit/push `feat: connect patient registration and OPD reception`.

### Task 05 — Clinical drafts, approval and reliable event handoff

Files: `backend/apps/clinical/{models,contracts,services,api}.py`, `backend/apps/integrations/{models,contracts,outbox}.py`, their `tests/`, `frontend/src/features/clinical/`, `e2e/clinical.spec.ts`.
Consumes: patients/encounters; produces approved immutable orders and durable source events. Pages D01–D03/D05/D07/D08, M15.

- [ ] Finalise clinical fields/templates and voice/upload processing policy; review signing/amendment and extraction threats.
- [ ] Write red tests `test_draft_does_not_release_order`, `test_approval_routes_medicine_and_therapy_independently`, `test_amendment_preserves_approved_version`, `test_event_retry_is_idempotent`, `test_doctor_sees_permitted_payer_summary`, `test_rejected_cover_does_not_change_order`.
- [ ] Implement typed/upload draft and approval; voice draft only after its trial/release decision, never silently drop the desired capability.
- [ ] Verify clinical signer access, concurrency/stale edits, extraction errors, outbox failure/replay and source/version traceability.
- [ ] Update docs and commit/push `feat: add approved clinical orders and durable handoff`.

### Task 06 — Therapy courses, resources and performance

Files: `backend/apps/therapy/{models,contracts,services,api}.py`, `backend/apps/therapy/tests/{test_booking,test_performance}.py`, `frontend/src/features/therapy/`, `e2e/therapy.spec.ts`.
Consumes: approved orders/resource masters; produces schedule/performance contracts and source events. Pages R07, T01–T05 and relevant M14 subviews.

- [ ] Review staff/room/equipment buffers, course counts, actual materials and interruption rules.
- [ ] Write red tests `test_required_resources_cannot_overlap`, `test_stopped_course_keeps_completed_sessions`, `test_performance_correction_is_attributable`.
- [ ] Implement atomic resource scheduling and actual session/observation recording.
- [ ] Run real database conflict tests and accessible calendar/start/stop/material flows.
- [ ] Update docs and commit/push `feat: manage therapy courses and delivered sessions`.

### Task 07 — Expandable admissions, accommodation and transfers

Files: `backend/apps/admissions/{models,contracts,services,api}.py`, `backend/apps/admissions/tests/test_allocations.py`, `frontend/src/features/admissions/`, `e2e/admission.spec.ts`.
Consumes: identity/access/resource masters; produces allocate/transfer/history contracts. Pages R08–R11/R09–R10 and admission portion of D04.

- [ ] Review configurable capacities/exclusive units, time intervals, transfer and rent-boundary examples.
- [ ] Write red tests `test_two_allocators_cannot_claim_same_bed`, `test_villa_blocks_sibling_beds_without_false_occupancy`, `test_capacity_can_exceed_100`, `test_future_reservation_keeps_current_occupancy`.
- [ ] Implement admission/reservation/allocation/transfer services with real database invariants.
- [ ] Verify concurrency, overlapping intervals, branch scope, capacity reconciliation and required colours/text.
- [ ] Update docs and commit/push `feat: support expandable inpatient accommodation`.

### Task 08 — Nursing, rounds and discharge preparation

Files: `backend/apps/nursing/{models,contracts,services,api}.py`, `backend/apps/nursing/tests/test_administration.py`, clinical rounds/discharge modules, `frontend/src/features/nursing/`, `e2e/ward.spec.ts`.
Consumes: active admission and approved orders; produces administration/care/handover records. Pages N01–N05, D04/D06.

- [ ] Review dose schedule/PRN/held/refused/late entries and changed-order responsibilities with clinical leads.
- [ ] Write red tests `test_dispense_does_not_imply_administration`, `test_dose_retry_is_not_duplicate`, `test_changed_order_updates_future_tasks_only`, `test_discharge_signing_does_not_free_bed`.
- [ ] Implement care/administration/rounds/handover and approved summary workflows.
- [ ] Verify actual/entered timestamps, correction history, shift scope and discharge handoffs.
- [ ] Update docs and commit/push `feat: record inpatient care and clinical discharge`.

### Task 09 — Stock custody and procurement

Files: `backend/apps/inventory/{models,contracts,procurement,units,movements,api}.py`, `backend/apps/inventory/tests/test_stock.py`, `frontend/src/features/pharmacy/stock/`.
Consumes: product/location masters and scoped context; produces immutable location/batch ledger and usable stock. Pages P03–P05/P07/P08.

- [ ] Review units/receipts/opening stock/transfers/expiry/quarantine; confirm preparation/manufacturing excluded unless explicitly added.
- [ ] Write red tests `test_receipt_retry_posts_once`, `test_unit_conversion_preserves_quantity`, `test_transfer_is_not_patient_consumption`, `test_expired_or_quarantined_batch_is_unusable`.
- [ ] Implement procurement/receipt, batches, location movements, block/expiry and authorised corrections.
- [ ] Verify movement reconciliation and scoped stock/expiry UI, including simultaneous transfers.
- [ ] Update docs and commit/push `feat: establish traceable pharmacy stock custody`.

### Task 10 — Actual dispensing, returns and downstream charges

Files: `backend/apps/inventory/services.py`, `backend/apps/inventory/returns.py`, `backend/apps/inventory/tests/test_dispense.py`, `frontend/src/features/pharmacy/{issues,returns}/`.
Consumes: approved orders, usable stock and outbox; produces dispense/return contracts and charge source events. Pages P01/P02/P06/T05.

- [ ] Review partial issue, substitution authority, actual material use and refund versus restock separation.
- [ ] Write red tests `test_dispense_20_of_30_leaves_10`, `test_concurrent_issue_cannot_overdraw`, `test_return_credit_does_not_auto_restock`, `test_retry_has_one_source_charge_event`, `test_pharmacy_sees_item_restrictions_without_claim_documents`.
- [ ] Implement atomic actual supply and inspection-led return flow through shared services.
- [ ] Verify real stock contention, expiry, source links and permission/UI cases.
- [ ] Update docs and commit/push `feat: link actual dispensing and inspected returns`.

### Task 11 — Tariffs, packages, bills, deposits and payments

Files: `backend/apps/finance/{models,contracts,services,tariffs,packages,ledger,api}.py`, `backend/apps/finance/tests/{test_ledger,test_packages,test_payments}.py`, `frontend/src/features/accounts/`, `e2e/billing.spec.ts`.
Consumes: source events/admissions/actual delivery; produces charge/receipt/allocation contracts. Pages A01–A10 and tariff/package M14 subviews.

- [ ] Review accountant-supplied entity/series/tax/rounding, room-cycle, inclusions, discounts/refunds and payment policies.
- [ ] Write red tests `test_source_event_creates_one_charge`, `test_package_inclusion_not_double_billed`, `test_duplicate_payment_callback_one_receipt`, `test_rate_change_keeps_final_invoice`, `test_transfer_rent_periods_do_not_overlap`.
- [ ] Implement versioned rates, explicit entitlement/ledger and approved payment/adjustment flows; no unverified external gateway enabled.
- [ ] Verify decimal totals, advances/unapplied receipts, payer splits, concurrency, refund approval and cashier reconciliation.
- [ ] Update docs and commit/push `feat: reconcile hospital billing and collections`.

### Task 12 — Insurance case management and operational discharge

Files: `backend/apps/coverage/{models,contracts,services,api}.py`, `backend/apps/operations/{models,contracts,services,api}.py`, their `tests/`, `frontend/src/features/{insurance,operations}/`, `e2e/discharge.spec.ts`.
Consumes: admissions/clinical/finance; produces separate authorisation/claim/settlement and exit/readiness contracts. Pages I01–I06/H01–H03, clearance handoffs.

- [ ] Review hospital-supplied agreements/documents and clearance/physical-exit/cleaning responsibilities; no premises due diligence.
- [ ] Write red tests `test_unknown_limit_is_not_zero`, `test_approved_unpaid_claim_remains_due`, `test_rejection_not_auto_patient_liability`, `test_exit_then_cleaning_before_ready`, `test_coverage_status_visible_only_in_authorised_portals`.
- [ ] Implement manual verification/pre-auth/query/claim/settlement and controlled exit/cleaning/restriction flows.
- [ ] Verify liability allocations, invoice links, room upgrade reviews and resource readiness under failure/retry.
- [ ] Update docs and commit/push `feat: track payer cases and safe discharge readiness`.

### Task 13 — Full/module backup and controlled restore

Files: `backend/apps/dataops/{models,contracts,backups,manifests,restores,api}.py`, `backend/apps/dataops/tests/test_recovery.py`, `frontend/src/features/admin/{backups,restores}/`, `infra/recovery/` runbooks.
Consumes: scoped shared-data ownership maps and cloud storage/key strategy; produces backup/archive validation/restore contracts. Pages M09–M11/M19/M22.

- [ ] Review dataset dependency graphs, access ceilings, keys, isolation/cutover and historic-event suppression.
- [ ] Write red tests `test_module_restore_rejects_missing_dependencies`, `test_archive_tamper_rejected`, `test_backup_does_not_include_ungranted_clinical_fields`, `test_restore_does_not_send_old_payment_events`.
- [ ] Implement encrypted jobs/manifests, isolated validation and confirmation-bound restore orchestration.
- [ ] Perform full database+files restore and at least one shared-dependency module recovery drill with recorded counts/checksums and elapsed time.
- [ ] Update docs and commit/push `feat: provide verified scoped backup and recovery`.

### Task 14 — Controlled import/export and migration

Files: `backend/apps/dataops/{transfers,templates,mapping,validators}.py`, `backend/apps/dataops/tests/test_transfers.py`, `frontend/src/features/admin/{imports,exports}/`, `docs/operations/cutover.md`.
Consumes: service contracts and permitted dataset registry; produces import preview/commit/export jobs. Pages M12/M13/M19.

- [ ] Review synthetic templates, duplicate/branch/unit mapping, chunk/rollback policy, formula injection and download expiry.
- [ ] Write red tests `test_import_dry_run_has_no_writes`, `test_preview_changed_payload_rejected`, `test_import_cannot_overwrite_final_invoice`, `test_export_masks_forbidden_columns`, `test_expired_or_revoked_download_denied`.
- [ ] Implement staged scan/dry-run/approval and bounded scoped export, using domain services for imports.
- [ ] Rehearse synthetic opening census/stock/deposit migration and reconciliation; do not publish actual hospital data.
- [ ] Update docs and commit/push `feat: control data transfer and migration workflows`.

### Task 15 — Scoped remote MCP

Files: `backend/apps/mcp/{transport,oauth,tools,services,confirmations}.py`, `backend/apps/mcp/tests/{test_authorization,test_tools}.py`, `frontend/src/features/admin/mcp/`, `docs/operations/mcp-clients.md`.
Consumes: actor/network permissions, clinical/appointment/finance services and integration framework; produces section 10 tools. Pages M17/M18 and consent/error views required by the selected OAuth integration.

- [ ] Pin protocol/SDK and review selected-client auth/discovery, disclosure, scope, network path and threat cases before code.
- [ ] Write red tests `test_wrong_audience_denied`, `test_revoked_client_denied`, `test_tool_content_cannot_grant_authority`, `test_confirmation_replay_denied`, `test_tool_respects_same_branch_and_ip_policy`.
- [ ] Implement bounded catalogue, user-delegated OAuth, field filtering, audited idempotent writes and kill switches; no SQL/shell/high-impact autonomous tools.
- [ ] Run protocol tests and selected ChatGPT/Claude client connection tests where available; document unsupported combinations accurately.
- [ ] Update docs and commit/push `feat: expose permissioned MCP workflows`.

### Task 16 — Reporting and future-integration boundaries

Files: `backend/apps/reporting/{definitions,selectors,jobs,api}.py`, `backend/apps/integrations/{external_ids,projections,reconciliation}.py`, associated `tests/`, `frontend/src/features/management/`.
Consumes: scoped domain events; produces G01/G02 and reviewed external-ID/event schema only. F01/F02 are not built.

- [ ] Review metric definitions, cache/projection freshness, source/current-agent history and bounded reporting; defer actual call-center product.
- [ ] Write red tests `test_collection_not_equal_to_invoiced_revenue`, `test_projection_respects_authorised_fields`, `test_stale_event_cannot_regress_status`, `test_report_limit_and_branch_scope`.
- [ ] Implement hospital reporting plus versioned external-ID/outbox contracts and synthetic projection fixtures.
- [ ] Verify reporting isolation/freshness and replay consistency; do not enable an unreviewed connector.
- [ ] Update docs and commit/push `feat: add bounded reporting and integration contracts`.

### Task 17 — Cloud hardening, mixed-load validation and rollout

Files: `infra/` provider-specific reviewed configuration, `.github/workflows/deploy.yml`, `backend/tests/load/`, `e2e/`, `docs/operations/{deployment,recovery,incident-response,go-live}.md`.
Consumes: chosen provider, approved recovery/availability/performance targets and all released features; produces verified staging then explicitly authorised production release.

- [ ] Complete environment/network/key/access diagrams, deployment/rollback, staff cutover and mixed-workload scenarios; set measurable acceptance targets with owner.
- [ ] Write/run negative configuration/access and load harness checks first; verify missing controls are detected.
- [ ] Implement reviewed staging infrastructure, private dependencies, CI identity controls, migrations, monitoring and recoverable deployments.
- [ ] Run V01–V13 as applicable: staging security review, independent API journeys/adapter parity, concurrent patient journeys, realistic-cardinality mixed load, queue retry, backup/restore/failover and representative staff-usability acceptance. Record actual results and fix confusing steps, not a capacity/usability guarantee.
- [ ] Update docs; commit/push; deploy only within explicit production authorisation and record release/rollback evidence.

## 14. Test commands and expected outcomes

Backend pytest and Django checks, frontend typecheck/test/build and documentation checker are implemented. Frontend lint currently aliases typecheck; e2e command is still planned. Use actual package scripts, not every proposed interface below:

```text
backend: python -m pytest
backend: python manage.py check --deploy   (review environment-specific output)
frontend: npm run typecheck
frontend: npm run lint
frontend: npm run test -- --run
frontend: npm run build
e2e: npm run test:e2e
documentation: python scripts/check_project_docs.py
```

Expected evidence is zero failed relevant tests, clean build/type checks, reviewed deployment checks, no unresolved required security findings and passing documentation gate. A missing command is a setup gap, not a test pass. Real PostgreSQL tests are required for locking/constraint claims; SQLite-only tests do not prove them. Performance/recovery thresholds are approved before measuring.

Per-task test names above define their assertions. Additional narrow tests are added for discovered behaviour; do not mirror implementation just to inflate counts.

## 15. Decisions and proposed defaults

| Topic | Proposed/required handling before related coding |
|---|---|
| Backend/frontend/database | Current Django/React/PostgreSQL direction; owner review and compatible version pinning |
| Build approach | Custom modular core proposed; record comparison with extend/configure and final choice |
| Cloud/OAuth provider | Select from security/operations/client compatibility; no paid resources assumed |
| Patient/clinical fields | Minimal registration plus configurable intake; clinician-reviewed clinical templates |
| Room billing/packages | Hospital supplies cycles/inclusions/refund policy; model configurable rules, do not invent charges |
| Payer/tax configuration | Hospital/accounts supplies terms and formats; manual verified workflow initially |
| Voice | Desired; agree launch priority and doctor trial; draft-and-approve mandatory |
| Data limits | Initial page default 25/max 100 proposed; file/import sizes and time budgets set from threat/load analysis before upload/import code |
| IP initial mode | Whitelist-only capability required; bootstrap approved admin network/recovery before enforcement |
| Backup/retention/recovery | Agree targets/dataset policies before scheduling/deployment; no clinical deletion by default |
| MCP clients | Pin protocol/OAuth strategy and test selected supported clients; no blanket compatibility claim |
| Branches | Configurable identity/access/resources now; actual branch onboarding later |
| Call center | Integration boundaries only now; do not request product/API details as current blocker |
| Premises/norms | Owner-managed; no further investigation required for this software task |

## 16. Evidence log and readiness

### Active identity security —23October2026

- [x] Exact identity-security-contract.md and OpenAPI0.4/page-map9operations frozen36total; official PyOTP/Fernet/Django/NIST/OWASP research and separate pre-code threat review. Existing-factor proof, anonymous CSRF and locked revocation design explicit.
- [ ] Backend WIP present: core0005five identity models,9self APIs/login202/logout, encrypted factors/hash recovery/DB budgets/epochs and identity locks, RED tests. Frozen candidate actualPG236passed/25subtests/check/nodrift. Complete proof-age recheck after org-lock waits and missing full API/race/negative coverage before marking delivered.
- [x] Frontend source login202/Account security/all9APIs, transient setup/recovery codes with acknowledgement/secret clearing/plain policy guidance;15new tests,64total/typecheck/build. Source-only; full security integration/browser/staff acceptance incomplete.
- [ ] Fresh source review started but stopped at usage threshold, no full approval. Root actualPG236passed/25subtests; frontend-agent64/build. Next reproduce/fix proof-age-after-lock, test ciphertextswap/enrollment expiry+crosssession+replay/anonymousverifyCSRF/accountwindow/challenge/profile/fullrevokewrite races, finishreview and actualCI. Live47b3618unchanged; no real-data release.

### Active staff access —23October2026

- [x] Owner direct-resume waiver/current usage recorded, historical checkpoint preserved, same heartbeat updated; latest2ca8239actualCI all3jobs success.
- [x] staff-access-contract.md and4OpenAPI/page-action extensions frozen; security/design preflight reviewed. Staff-only branch-option lookup avoids broad resource-write grant; total27operations.
- [x] Backend scoped create/list/grants/suspension/active-membership ceiling/version/audit with RED/current-permission/race tests; frontend password-safe/paged assignment forms and branch-specific operational controls. core0004; no global identity disable or clinical authority.
- [x] Fresh review resolved two Important races and Minor response-cap mismatch;7consistency RED->GREEN plus mixed-branch API/UI RED->GREEN. Final actual PostgreSQL213passed/25subtests/check/drift; frontend49passed/typecheck/build. API/docs/root verification and publication tracked in ledger/handoff. MFA remains separate, Task02 incomplete; preview47b3618unchanged.


### Verified master branch/bed source checkpoint —23October2026

- [x] Scoped5operation OpenAPI/page-action contract frozen before code in resource-administration-contract.md; permission/failure/audit/version/occupancy design preflight reviewed with no blocker.
- [x] Backend scoped5operations,0003version/audit migration, traceable services/concurrency; frontend named/paged branch+bed forms. Actual PostgreSQL166passed/25subtests,frontend30passed/typecheck/build.
- [x] Fresh bounded review, actual FKdeadlock RED/no_key fixGREEN/full166suite, coordinator frontend30/build, API/docs checks and same-change living docs. PublicationSHA at handoff. No complete staff/MFA/resource-rate/clinical module or live update; preview47b3618.


### Active reception reliability slice —23October2026

- [x] Owner-resume instruction recorded; authenticated primary76%/weekly51%remaining, guard continue, old cooldown waived explicitly, same heartbeat updated.
- [x] API/page/action/permission/failure/acceptance design frozen in reception-reliability-contract.md; optional UUID Idempotency-Key and beds status filter added to OpenAPI before implementation.
- [x] Backend atomic retry ledger/scoped replay/global filtering; actual final PostgreSQL123tests/25subtests, including same-key/same-bed races. Frontend corrections/reschedule/paged choices/stable-key recovery20tests/build GREEN. Initial47b3618GitHubCI actually inspected, all3jobs successful.
- [x] Fresh review and RED->GREEN fixes for2Importantmalformed-input500cases; Minorname limits aligned; integrated tests/OpenAPI/docs/whitespace passed and living docs updated. PublicationSHA at handoff. Existing deployed preview47b3618 unchanged by source delivery.


### Hostinger preview — current23October2026

- [x] Dedicated deployment plan/threat review before runtime changes; owner cooldown override explicitly limited to deployment.
- [x] First100-bed selector RED->GREEN regression;25/page choices, clear stale selection, retry; frontend11passed and build on VPS.
- [x] Isolated /opt/hms, dedicated user/service/private PostgreSQL17.11, TLS, non-superuser app role, HTTPS/static build/Gunicorn, edge Basic gate and shared login limit.
- [x] Actual PostgreSQL48tests/25subtests passed without warnings, concurrent same-bed test included. Test DB cleaned and CREATEDB revoked.
- [x] HTTPS/session/cookies/CSRF/API branch denial/edge throttle/private origin checks; backup checksum and isolated restore smoke; existing Nginx files preserved and checked domains responding.
- [ ] Authenticated live browser/staff walkthrough (browser automation cannot handle outer Basic prompt); full independent product review, MFA/read audit/off-host recovery/load and remaining clinical/finance/MCP portals.
- Deployment does not close Task17 or other full-module tasks. See operations runbook for exact limits and rollback. General development resumes under saved usage guard after this deployment exception.


### Phase A checkpoint — cooldown triggered23October2026

- Backend agent:47tests passed,1PostgreSQL concurrency test skipped onSQLite,25subtests passed; Django5.2.18/DRF3.16.1; system check/migration drift checks passed. Initial settings/services in backend/hms and apps/core rather than final per-domain package layout; refactor future domains explicitly.
- Frontend agent:typecheck,8tests and build passed; source-only production dependency audit reported0vulnerabilities. Core API-backed local screens present; full92-page catalogue is not implemented.
- Coordinator: root scripts16tests passed (usage guard8 + documentation checker8); pureIP22tests/25subtests passed. Synthetic browser login/dashboard verified; API/map/local-link checker passed. Full checkpoint reruns recorded in ledger when complete.
- Platform: OpenAPI18operations, page-action mapping, Dockerfiles/Compose and CI prepared. Docker unavailable locally; no container runtime/remoteCI pass claimed.
- Independent fifth reviewer stopped on threshold; no Critical found in bounded inspected auth/CSRF/branch/allocation paths, but review incomplete. Important open finding: admission selector hard-caps first100beds. This must be fixed/tested before any release; do not mark Tasks07/17 fully complete.
- Task01/02/03/04/07 subsets implemented, not whole-task completion. MFA, production identity/edge, all clinical/finance/dataops/MCP and remaining portals stay planned. Generic creation idempotency/cross-branch identity/exclusivity are explicit remaining work.
- Threshold6%remaining at2026-10-23T05:02:15Z; preserve earliest resume2026-10-23T10:32:15Z. Manual Continue at08:34Z found55%recovered but did not silently waive cooldown. Next: >100-bed regression/fix, complete independent review, validate remotePostgreSQLCI, then next reviewed slice.
- Coordinator checkpoint reruns confirmed backend47passed/1PGskip/25subtests and frontend typecheck/8tests/build; source/API-map/link and targeted credential-pattern checks passed. No new implementation performed during cooldown.

Active execution evidence: docs/implementation/ledger.md. Five specialist roles assigned in batches: backend, frontend, security, platform/dataops/MCP and independent review. Root coordinates shared interfaces/docs/Git. Usage guard8/8 RED->GREEN; native heartbeat active. No application capacity/production assertion follows from those developer-tool tests.

| Check | Current evidence |
|---|---|
| Owner inputs | Original baseline, research and latest O-01–O-11 incorporated |
| UI skill | Two design queries reviewed; marketing output rejected; functional enterprise direction recorded; UX validation guidance consulted |
| GitHub | Specified repo metadata checked: empty/public, connected account has push permission |
| MCP/security references | Official authorisation/security and OWASP guidance consulted |
| Documentation coverage/links | Local-link/O-ID/92 unique page-ID/secret-pattern checks passed; unchanged baseline hash verified; staged diff checked at publication |
| Independent review | Completed read-only review; Important C-20 gap and two Minor references fixed; corrections verified with no remaining Important/Critical documentation findings |
| Product tests/build/deployment | Actual VPS PostgreSQL48passed/25subtests; frontend11passed/build; authenticated preview deployed, hospital cutover not approved |
| Initial commit/push | Published to main; local/remote initial SHA both `17df5ef52750cfb55ad9d146dbeba1d9d4820699`; follow-up SHA verified at handoff |

## 17. Change control and GitHub publication

Every planned or implemented change updates HMS.md and affected plan sections. Append a change record with exact behaviour/files/contracts/security/data/test impact. Proposed, implemented, verified and deployed are distinct statuses.

Each completed coherent change set: review -> checks -> documentation -> commit -> push to https://github.com/prarit0097/HMS-MANAGEMENT -> verify local/remote SHA. Do not push real data, secrets, backups, generated dependencies or broken unreviewed work. Do not force push or overwrite unrelated remote work. If remote head changed, inspect and integrate safely. Report failed push accurately and preserve recoverable local commits.

Create feature branches/PRs when repository protection or agreed workflow requires them; publication is not production deployment. Documentation must describe the resulting state, not claim the push's own future SHA. Final handoff supplies verified commit/URL.

## 18. Changelog

- 1.0.0 — 23 October 2026: initial comprehensive planning catalogue; O-01–O-11 mapping; shared page states, service contracts, security/IP/MCP, cloud/dataops, Tasks 00–17, verification and continuous-documentation workflow. Product implementation not started.
- 1.0.1 — 23 October 2026: record completed Task 00, independent review/corrections, documentation verification and verified initial GitHub publication. No product implementation, runtime tests or deployment.
- 1.1.0 — 23 October 2026: add O-12 simple professional UX and O-13 API-first architecture; OpenAPI/page-action mapping gate, contract/parity test suite and staff-task usability checks. No application code or runtime tests added.
- 1.2.0 — 23 October2026: owner authorised team execution; freeze Phase A contract, team ownership, preflight ledger and O-14 usage pause/resume rule. Tested local usage guard and Windows wrapper, native heartbeat active. Phase A runtime work in progress.
- 1.3.0 — 23 October2026: preserve runnable first slice and five-agent evidence at usage stop; record known Important100-bed-selector defect, incomplete review, runtime limitations and exact cooldown deadline. Feature branch checkpoint, not production release.

- 1.4.0 — 23October2026: owner-authorised dedicated Hostinger authenticated preview, deployment-specific cooldown override, >100-bed selector regression/fix, actual PostgreSQL verification, HTTPS/session/security/backup/isolation evidence; full hospital release still gated.

- 1.4.1 —23October2026: owner explicitly resumes general development, prior cooldown waived with authenticated minimum51%remaining; freeze reception retry/correction/reschedule/selection contracts before implementation; same heartbeat updated.

- Documentation correction23October2026: repair coordinator Windows encoding/newline mistake; actual47b3618GitHubCI verified all3jobs successful. Error response scalar-vs-array parity finding added to active backend RED-first scope.

- 1.5.0 —23October2026: reception reliability source delivered, optional atomic scoped create keys, global bed filtering, patient corrections/versioned rescheduling/paged choices, safe object/error validation; actual PostgreSQL123passed/25subtests,frontend20passed/build. New migration/source not deployed; full-module/release gates remain open.

- 1.5.1 —23October2026: actual reception03c5634CI success recorded; freeze master branch/bed configuration23-operation catalogue before implementation.

- 1.6.0 —23October2026: master resource source complete/verified166PostgreSQL/25subtests,30frontend/build, deterministic FKdeadlock RED->GREEN; new9%usage checkpoint09:49:16UTC, earliest15:19:16UTC. No live update or realpatient cutover.

- 1.6.1 —23October2026: owner resumes13:36:49UTC waiving oldcooldown; resourceCI verified; freeze staffaccess4operations/27total and scoped suspension/version/privacy tests beforecode; MFA researched separately.

- 1.7.0 —23October2026: verified scoped staff access, active branch permissions and revocation/snapshot consistency;213PG/49frontend, MFA next, preview separate.

- 1.7.1 —23October2026: staff actualCI verified, frozen9operation identity-security contract/API before code, dedicated encryption/replay/session/counter/privileged MFA design.

- 1.7.2 —23October2026: new9%usage checkpoint/330min cooldown; identitysourceWIP236PG/64frontend-agent, knownproofage/negative-racecoverage/review pending, existingpreviewunchanged.


Checkpoint coordinator repeat: frontend63passed/1failed (resource-administration stale-bed-edit test could not find Edit bed101 within timed wait); agent earlier64passed. Coordinator typecheck/build still passed. Affected test isolated rerun is recorded in ledger/handoff; this does not establish a repaired full suite. No source changes after stop. Investigate/repeat full suite after cooldown before marking identity delivered.
