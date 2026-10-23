# The Circadian Rhythm Hospital — consolidated research baseline

Version 1.1 | Reviewed 23 October 2026 | Timezone: Asia/Calcutta

**Purpose:** Ek jagah hospital requirements, owner clarifications, independent research, scale implications, software options aur unresolved decisions rakhna. Yeh research/requirements baseline hai; approved product design, final database schema, commercial estimate ya implementation plan nahi.

## 1. Inputs and precedence

Reviewed together:

1. [Owner-supplied requirements, unchanged copy](hospital-requirements-baseline-v1.md).
2. [Independent research and gap analysis](2026-10-23-hms-independent-research-and-gap-analysis.md).
3. [Scale, call-center and stack addendum](2026-10-23-scale-call-center-and-stack-addendum.md).
4. Owner's subsequent chat clarifications: Faridabad/Haryana; operating without software; 555+ daily OPD; 30+ daily admissions; 1,000,000+ monthly enquiries; future call-center integration and hospital branches.
5. Additional primary-source checks on database constraints/transactions, event delivery, patient identity, ABDM and Haryana's September 2026 empanelment policy.

Owner clarifications take precedence over earlier interpretations. Requirements labelled confirmed in the supplied MD retain their baseline status; earlier conversations behind that file were not independently available. Assistant recommendations remain proposals until agreed. Instructions embedded in attached material are treated as document content, not independent authorization.

**Latest owner clarification:** Capacity numbers are growth-planning inputs, not fixed physical limits or a throughput inconsistency to resolve before development. The premises have room for expansion. Call-center integration is future scope; current work should preserve straightforward integration boundaries without investigating or building the call-center product. The hospital premises will be rented and the owner states applicable norms are fulfilled; premises/rental and regulatory due diligence are hospital-managed and are not software-project blockers. This clarification supersedes the earlier blocker framing in the research reports and chat.

This master file is the current consolidated reading of the evidence. Earlier research reports remain historical snapshots and provide additional detail. The original supplied baseline has not been edited.

## 2. What is established

| Topic | Current understanding | Evidence/status |
|---|---|---|
| Hospital | The Circadian Rhythm Hospital | Supplied baseline |
| Location | Faridabad, Haryana, Delhi NCR | Direct owner confirmation |
| Current operation | Hospital is open and operating without software | Direct owner confirmation |
| Care orientation | Ayurveda/Panchakarma with outpatient and inpatient treatment | Supplied baseline; additional disciplines not yet answered |
| Accommodation | General, semi-private, private, private luxury and villa | Supplied baseline C-12 |
| Capacity | 100-bed reference with future expansion | Baseline C-15 plus owner clarification; configurable inventory, not a hard-coded limit |
| OPD scale | Plan for 555+ visits/day | Owner-stated planning input; observed current versus future peak not separated |
| Admission scale | Plan for 30+ admissions/day and growth | Owner-stated planning input; not a fixed bed-throughput constraint |
| Enquiry scale | 1,000,000+ enquiries/month | Direct owner confirmation of period |
| Call center | Future integration and agent outcome/sales visibility | Owner explicitly deferred integration details; preserve boundaries now |
| Expansion | Future hospital branches | Direct owner requirement; count, ownership structure and timing unknown |
| Technology | Django/Python, React/TypeScript and PostgreSQL recommended | Assistant recommendation; not selected/approved by owner |
| Premises/norms | Rented premises; owner states norms fulfilled | Hospital-managed; no premises/compliance investigation required for current software work |

## 3. Consolidated product scope

The connected journey to support is:

**Enquiry/contact -> agent/referral -> appointment -> patient identification -> OPD consultation -> medicine/therapy/investigation -> IPD where needed -> discharge -> invoice/collection/claim -> follow-up.**

Direct hospital walk-ins and referrals without a call-center lead must also work. A returning patient can have several encounters, several enquiries and different referral histories. Avoid forcing every patient through a sales lead.

### Baseline requirement coverage

| Baseline IDs | Requirement carried forward | Important implementation boundary |
|---|---|---|
| C-01 | Hospital identity/name | Legal entity, brand and branch may differ; model explicitly |
| C-02, C-03 | Reception intake/history, doctor selection and reception portal | Patient-reported history separate from doctor-reviewed assessment |
| C-04, C-05 | Doctor consultation, prescription; typed/upload/voice entry | Extraction/dictation produces a draft; approved orders require clinical review; voice timing undecided |
| C-06 | Medicine-only, therapy-only or combined treatment | Independent worklists and no forced medicine sale |
| C-07 | Reception coordinates therapy | Clinical order belongs to doctor; scheduling ownership is operational |
| C-08 | Pharmacist records actual supply | Partial issue, outstanding quantity, batch and traceable returns |
| C-09 | Accounts portal | Charges, invoices, receipts, advances, patient dues and payer receivables separate |
| C-10 | Central administration | Staff identity, roles, masters, rates and approval rules |
| C-11 | IPD in first operational scope | Include minimum nursing, therapy and bed-readiness responsibilities |
| C-12, C-13, C-14 | Accommodation categories, configurable rooms/rates and unique mapped beds | Distinguish physical capacity, occupancy and exclusive allocation |
| C-15 | 100-bed total/filled/empty/room-wise view | Counts reconcile to actual inventory; future reservations do not inflate current occupancy |
| C-16 | Green booked/occupied and red available | Preserve requested colours; add mandatory labels and distinguish reserved/occupied |
| C-17, C-18 | Insurance/government/employer details, limits and AYUSH coverage | Unknown versus verified values, evidence and snapshot history |
| C-19, C-20 | Cashless/reimbursement and coverage visibility across relevant portals | Approval is not settlement; permissions control the level of detail |

### New owner requirements

- N-01: Operate for an existing hospital in Faridabad with paper-to-digital transition.
- N-02: Plan and validate the stated OPD, admission and monthly enquiry scale.
- N-03: Support future call-center connection with linked patient outcomes and authorised sales visibility for agents.
- N-04: Support future branches through explicit branch identity, permissions and data ownership.

The exact breadth of CRM, telephony, agent commissions, marketing automation and a patient app has not been confirmed. Future integration support is distinct from building a new call-center product now.

## 4. Recommended operational modules

| Module | Responsibilities |
|---|---|
| Organisation/admin | Facilities, branches, staff, roles, approvals, versioned masters |
| Patient identity | Search, UHID, contacts, relationships, duplicate review, legacy IDs |
| Reception/OPD | Appointments, walk-ins, queues, check-in, doctor allocation |
| Clinical | Reviewed history, observations, notes, diagnoses, prescription/order versions, rounds |
| Therapy | Courses, sessions, resources, readiness, actual performance and materials |
| Admission/accommodation | Admission, allocation, reservations, transfer, exit and bed readiness |
| Nursing | Due care/medication tasks, administration, observation, escalation and handover |
| Pharmacy/inventory | Procurement/receipt, batches, locations, issue, consumption, returns and adjustments |
| Finance | Estimates, packages, charges, deposits, invoices, collections, refunds and reconciliation |
| Insurance desk | Verification, pre-authorisation, enhancement, queries, claims and settlements |
| Housekeeping/maintenance | Cleaning, operational restrictions and authorised readiness |
| CRM integration | External IDs, referrals, agent attribution, permitted patient-outcome views and follow-ups |
| Reporting/audit | Operational drill-down, financial definitions, access/change history and export control |

Kitchen/dietetics, advanced circadian diaries, investigations, emergency/OT and patient access need scope confirmation. If a test is outsourced, minimum order/result/acknowledgement workflow may still be needed.

Each employee may hold several authorised roles, but action attribution stays with an individual login. A role-specific portal need not mean a separately deployed app or database.

## 5. Scale research and capacity implications

At the stated floor, a 30-day month gives approximately 33,333 enquiries/day. One million/month becomes 12 million/year if maintained. These counts do not tell us peak request rate or simultaneous agents.

For illustration, evenly distributed enquiry creation is about 0.39/second over 24 hours or 0.93/second over ten hours. Each enquiry may generate many calls, notes, callbacks, imports, webhook retries and audit events. Use actual activity patterns for sizing; these averages are not capacity guarantees.

OPD encounters are not unique patients. Enquiries are not automatically unique people, and the same patient can create several enquiries. Whether the owner's number counts unique leads, inbound calls, messages or all enquiries is unresolved.

### Capacity can expand

The owner clarified that the site has space to expand and provided 100 beds / 30+ daily admissions to communicate growth requirements. Do not treat these as a fixed census equation or a prerequisite to development. Add rooms, wards, beds and branches through configuration; preserve historical allocations and rates as capacity changes. No hard-coded 100-bed ceiling. Current inventory is configuration needed for operation, not a limit on the data model.

### Measurements needed before hosting estimates

Concurrent agents and hospital users; working hours; peak campaign/import bursts; activity events per enquiry; read/write mix; search/report patterns; retention; attachment/recording sizes; current and planned branches; availability/data-loss targets. Realistic load tests must combine clinical writes and call-center traffic.

## 6. Stack conclusion after reviewing all inputs

**Current recommendation remains Python + Django + Django REST Framework, React + TypeScript + Vite, and PostgreSQL.** This is an engineering judgment based on coupled records/workflows and maintainability, not a benchmark result or an owner-approved decision.

- Django provides a useful application foundation; DRF provides API tooling. Patient-level permissions, clinical amendments, financial controls and audit must be built explicitly. [Django overview](https://www.djangoproject.com/start/overview/), [DRF](https://www.django-rest-framework.org/)
- React/TypeScript is suitable for interactive staff panels. Vite can produce the frontend build; Next.js remains an option if server-rendered/public experiences become a concrete requirement. [Vite](https://vite.dev/guide/), [Next.js](https://nextjs.org/docs/app)
- PostgreSQL provides relational integrity and concurrency primitives. Correct constraints, indexes and transactions matter more than labelling the database enterprise-ready. [Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- Celery and a durable broker are candidates for background work. Redis can support disposable cache/rate limits; authoritative clinical/financial state remains durable. [Celery/Django](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- Attachments and permitted recordings belong in access-controlled object storage with metadata and recovery coverage.

### Approaches still to choose between

| Approach | Why consider it | Main trade-off |
|---|---|---|
| Custom Django-based HMS | Own Ayurveda, accommodation, finance and integration workflows | Our team owns reliability, security, testing, operations and long-term support |
| Extend a clinical foundation such as Bahmni | Reuse existing clinical/inpatient capabilities | Component expertise, licences, upgrade-safe extensions and integration effort |
| Configure commercial HMS | Potentially faster fit for standard operating workflows | Vendor limits, recurring costs, extension rights, export and support quality |

NestJS/TypeScript remains an alternative custom backend if the actual maintenance team is much stronger in it. FastAPI can be appropriate for focused APIs/services. No supplied volume establishes a need to abandon Python or introduce multiple backend languages.

Do not pin framework/database versions from a generic 'latest' page. At implementation time choose supported, mutually compatible stable releases and record the upgrade/support policy.

## 7. Architecture principles proposed for the design stage

1. Explicit boundaries for clinical, accommodation, inventory, finance, coverage and CRM integration.
2. A core transactional application can start as a modular monolith; separate staff experiences share authorised records.
3. Call-center imports, retries and heavy reporting receive independently limited worker/connection capacity. More physical separation is chosen from measurements and the actual CRM contract.
4. One authoritative owner for each entity. Do not let external software edit hospital clinical/financial tables directly.
5. Critical business changes and outgoing integration events use a durable handoff with retries, deduplication and reconciliation.
6. Failure of CRM, reminders, voice extraction or reporting does not prevent essential hospital recording.
7. Reporting replicas/projections can be stale; current bed/stock/payment decisions use authoritative state.
8. Deployment boundaries can evolve as measured load, team capacity and uptime requirements change.

Django transactions support grouping changes atomically, but broad long-lived transactions have costs. Database constraints and appropriate locking must complement them. [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)

An outbox avoids the gap between a committed business change and a failed notification. Duplicate delivery still requires idempotent consumers, and event order/version handling remains necessary. This pattern does not require selecting AWS. [Transactional outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 8. Identity and branches

Recommended organisation hierarchy: organisation/legal entity as appropriate -> branch/facility -> department/resource locations. Determine whether future branches share a legal entity before selecting invoice numbering and payer-contract ownership.

Recommended identity distinctions:

- Enquiry: incoming activity, potentially repeated or unqualified.
- Lead/contact: deduplicated operational identity where appropriate; not automatically a patient.
- Patient/UHID: hospital identity linked through reviewed matching.
- Encounter/admission: a particular visit or stay at a branch.
- Referral/attribution: a historical link to source, campaign and agent.

Retain legacy and external identifiers with issuer/source; do not use phone alone as a unique patient identifier. Review uncertain matches and merges, preserve history and protect against accidental cross-person disclosure.

Organisation-wide identity can coexist with branch-local registration IDs. Shared identity does not grant shared clinical access automatically. HL7's Patient resource separates patient identity/demographic information from referenced clinical information; use standards-aware mappings rather than assuming an internal table is already an integration. [FHIR R4 Patient](https://www.hl7.org/fhir/R4/patient.html)

Admission transfers between branches require an agreed clinical/financial process, not just changing `branch_id`. Local stock, tariffs, bed numbers, invoice series, cashier shifts and payer agreements must have appropriate scope.

## 9. Agent visibility and sales attribution

The owner's intent is continuity: an agent can tell whether a referred patient came, consulted, received therapy or was admitted, and see permitted sales outcomes for relevant follow-up.

Recommended initial agent projection: assigned person/lead, referral, appointment, arrival/visit outcome, permitted treatment/service milestone, follow-up task and authorised financial summary. Detailed diagnosis, prescription, clinical notes and insurance attachments need independent permissions.

Preserve original referring agent, current assignee, reassignment history, campaign, attribution window and branch. Define credit for repeat visits, several agents, reactivated leads and cross-branch visits. Commission/incentive rules are not confirmed.

Do not label invoice total, cash collected and revenue as one 'sales' figure. Define at least net invoiced amount, applied collections, refunds, advances and payer outstanding. Agent performance needs the same signed definitions as accounts.

API/webhook contracts need external IDs, authentication, event ID/version, occurrence time, delivery state, duplicate handling, ordering checks, retry/replay and reconciliation. Agent views should show update freshness. Telephony recording, dialler integration and messaging automation remain separate scope decisions.

## 10. Data integrity rules to carry into design

| Domain | Required invariant or proposed rule |
|---|---|
| Clinical | Original approved notes/orders remain attributable; amendments retain versions and effective time |
| Orders | Cancelling future care does not erase completed sessions, dispensed medicines or administered doses |
| Medication | Prescribed, issued, transferred to ward and administered are separate records |
| Bed | No overlapping conflicting allocations; private/villa exclusivity also protects underlying beds |
| Capacity | Empty-but-unavailable sibling beds do not become available or falsely count as occupied patients |
| Therapy | Required staff/room/equipment booked without resource conflicts; preparations/cleaning considered |
| Stock | Quantities reconcile by product/unit/batch/location; returns require separate usability decision |
| Finance | Charges reference source events; repeated processing cannot duplicate receipts/charges |
| Tariffs | Effective-dated history; finalised old invoices do not silently reprice |
| Coverage | Unknown, reported and verified values differ; cover, pre-auth, claim approval and settlement remain separate |
| Discharge | Clinical readiness, financial clearance, physical exit, cleaning and claim closure are distinct |
| Access | Branch/resource/data-category restrictions enforced server-side and audited |
| Time | Occurred-at and entered-at are preserved; backdating follows controlled rules |
| Integration | Stale or repeated events cannot overwrite newer state or duplicate business actions |

Package inclusion, unused-session credit, medicine substitution and financial liability rules need hospital approval; software must not invent them. These are software business rules, distinct from premises rent or regulatory due diligence, which the owner has excluded from the current work.

## 11. Database strength means operations as well as schema

Recommendations:

- Referential/unique/check constraints; branch-aware resource relationships; transactions for critical multi-record updates.
- Query-driven composite indexes, filtered/paginated worklists and bounded exports.
- Measured connection pooling/limits, worker isolation and slow-query monitoring.
- Consider row-level security as additional protection with safe database-role design; privileged roles/owners may bypass policies. [Row-level security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- Partition large activity/audit tables only when query, retention and constraint implications justify it. Avoid automatic partitioning of every table. [Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- Introduce reporting replicas/search infrastructure when workload justifies them; manage freshness explicitly.
- Agree availability and recovery targets, implement appropriate redundancy and protected backups with tested point-in-time recovery. Replication alone does not protect against mistaken deletion. [PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- Protect and recover private documents/configuration alongside the database.

Performance acceptance must cover realistic cardinality, simultaneous admission/dispense/payment actions, lead ingestion bursts, agent searches and reports. No hardware cost or throughput guarantee is established by this research.

## 12. Regulatory, insurance and interoperability research

**Scope clarification:** The sources below are retained as research background. Premises, building rental and fulfilment of applicable norms are hospital-managed according to the owner, and are not prerequisites for continuing software design. Do not request another registration/accreditation/premises review. Software access controls, record integrity and configurable insurance workflows remain part of the product requirements.

### Haryana establishment context

The Haryana Health Department's published guidance covers recognised medicine systems with more than 50 beds and lists a 51–100-bed category. Its older update marker means later notifications and this hospital's actual registration must still be checked. Faridabad is treated as Haryana, not Delhi. [Official guidance](https://haryanahealth.gov.in/clinical-establishment-act/)

### Update: September 2026 policy successfully accessed

The seven-page Health Department letter dated 16 September 2026, previously inaccessible, was retrieved on this review. It concerns empanelment of private hospitals/medical colleges for state employees, pensioners and dependants and links scope/validity to accreditation. It is not evidence of this hospital's empanelment or of AYUSH applicability. No automatic replacement of a separate AYUSH arrangement is inferred. [Official policy PDF](https://cdnbbsr.s3waas.gov.in/s31177967c7957072da3dc1db4ceb30e7a/uploads/2026/09/20260916589809650.pdf)

**Software implication:** keep facility registration, accreditation, payer empanelment, service scope and tariff contracts as separately versioned evidence. Current AYUSH-specific arrangements and the hospital's actual agreements remain externally unverified.

### Insurance and government beneficiaries

IRDAI public FAQs explain policy-dependent AYUSH coverage. Current contract/circular review is still needed. Private insurers, CGHS, CAPF, Haryana benefits, RGHS and PM-JAY must not share assumed entitlements. SBI Life and CBSE examples in the supplied document remain unresolved exact products/benefits. [IRDAI FAQs](https://irdai.gov.in/faqs-on-health-insurance-regulations)

### Accreditation and A-HMIS

NABH Ayurveda programme information is a quality/process reference, not certification of software. Current full standards mapping is outstanding if accreditation is a project goal. A 2026 Ministry release confirms A-HMIS as a useful contemporary benchmark; private-hospital availability and reuse terms are unverified. [NABH](https://portal.nabh.co/documents_Ayurveda.aspx), [Ministry of Ayush update](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2291029&lang=1&reg=3)

### ABDM, terminology and claims

The main NRCeS published guide returned v6.5.0 based on FHIR R4. A preview or a generic newer FHIR release must not be adopted as the integration contract automatically. Actual onboarding, profile version and conformance validation are separate work. NHCX is a claim-information exchange, not a promise of claim approval. [NRCeS](https://nrces.in/ndhm/fhir/r4/), [NHCX official explanation](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2037634&lang=2&reg=48)

NAMASTE is a relevant Ayurveda terminology reference. Direct access/API/licensing/mapping was not validated; terminology selection needs clinical review. [NAMASTE](https://namaste.ayush.gov.in/)

### Privacy and security

The notified DPDP Rules have phased commencement; implementation-date applicability and the Act's commencement instruments need review. Design purpose-specific access, processing notices/bases, consent where appropriate, vendor controls, request handling and reviewed retention. Withdrawal must not blindly delete required clinical/financial records. [MeitY Gazette](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)

CERT-In ICT security directions are a separate incident/logging consideration; do not confuse log retention with clinical-record retention. [CERT-In directions](https://www.cert-in.org.in/Directions70B.jsp)

## 13. Market benchmarks: what they establish

| Reference | Public capability signal | Remaining fit question |
|---|---|---|
| [Bahmni](https://www.bahmni.org/feature-list) | Clinical/registration/inpatient/stock/billing foundation | Current components, Ayurveda extension, insurance and maintenance fit |
| [AyuPlus](https://www.ayuplus.in/opd-ipd-management) | Ayurveda OPD/IPD and linked therapy records | Complex tariffs, scale, API/export and operational controls |
| [Ayush Manager](https://ayushmanager.com/ayurvedic-clinic-hospital) | Therapy, multilingual entry, diet and follow-up | Full inpatient/claims/financial controls |
| [Medinous](https://medinous.com/sitemap/) | Broad clinical and supporting departments | Ayurveda depth, cost, integrations and contractual fit |
| [MocDoc](https://mocdoc.com/india/hospital-management-system-delhi) | Departmental HMS offerings | Scripted end-to-end fit, exports, API rights and support |
| [Eka](https://www.eka.care/s/for-healthcare-providers) | Broader inpatient/bed/task capabilities | Required Ayurveda, tariff and call-center integration details |

Vendor pages are claims, not independent capacity/security/compliance proof. No paid demo, procurement ranking or vendor selection was performed. Bahmni combines components with different licences; inspect selected components before reuse. [Licensing](https://www.bahmni.org/license)

## 14. First operational release versus future scope

**Baseline business scope to preserve:** OPD + IPD, reception, doctors, admin, pharmacy, accounts, room/bed board, insurance capture and cashless/reimbursement tracking; typed/upload prescriptions. Voice remains desired with launch timing undecided.

**Recommended supporting minimum:** nursing/therapy/housekeeping responsibilities; approved structured orders; partial dispensing; versioned tariffs/packages as agreed; deposits/running bills; manual insurance desk; access/audit; recovery; migration; staff training and support.

**Foundation now for future requirements:** stable patient/branch IDs, permissions, source attribution, external-ID mappings and durable integration boundaries. Whether operational CRM or an integration adapter is built in release one depends on the existing call-center software and scope decision.

**Later candidates, subject to agreement:** advanced automation, patient app, deep accounting replacement, verified payer/ABDM integrations, advanced circadian diary, expanded dietetics and branch rollouts. Do not silently defer confirmed requirements.

## 15. Rollout in an operating hospital

1. Validate current OPD, inpatient-day, pharmacy, therapy, cashier and discharge workflows with named department leads.
2. Obtain approved blank forms and de-identified worked examples; catalogue masters and exception rules.
3. Reconcile physical/licensed/operational beds, active admissions, active orders, opening batch/location stock, deposits, dues and claims.
4. Train staff using synthetic journeys, including partial issue, amended order, transfer, package cancellation and failed payment.
5. Pilot complete connected journeys with explicit source-of-truth and paper reconciliation ownership.
6. Cut over at an agreed time with signed balances/census, support coverage and a tested downtime process.
7. Expand after acceptance evidence; monitor failures, workload and financial/stock reconciliation.

Historical scanning can proceed under policy without delaying safe capture of new work. Imported history and opening balances need source and verifier metadata. Restore tests must recover both records and files.

## 16. Acceptance coverage to preserve and extend

Retain all 22 baseline acceptance scenarios; the previous independent report adds 20 and the scale addendum adds concurrent-load/integration/isolation checks. These remain proposed future tests, not executed software tests.

Priority journeys for eventual validation:

- Existing patient -> new encounter -> medicine-only/therapy-only/combined worklists.
- Approved draft -> amended order after partial delivery -> correct remaining tasks and charges.
- Simultaneous allocation -> room transfer -> exclusive villa -> correct capacity and rent.
- Partial dispense -> nurse administration -> return quarantine -> approved financial adjustment.
- Package consumption -> unused session -> agreed cancellation/refund without duplicate charge.
- Pre-auth/query/enhancement -> discharge -> claim deduction/settlement -> correct outstanding.
- Enquiry/referral -> patient linkage -> cross-branch appointment -> authorised agent outcome.
- Repeated/out-of-order webhook -> one business action and correct latest status.
- Call-center burst/reporting -> acceptable clinical latency and preserved correctness.
- Staff deactivation, direct API/file access, exports and cross-branch access restrictions.
- Signed paper-to-digital cutover and tested backup restoration/failure recovery.

For every signed requirement, attach owner, priority, release, rule, permission and acceptance evidence. No blanket claim of compliance or capacity should precede this validation.

## 17. Decision register

| ID | Open decision | Why it matters | Needed for |
|---|---|---|---|
| D-01 | Ayurveda only or other clinical disciplines; diagnostics/emergency/procedures | Changes clinical screens, staffing and operational scope | Scope/design |
| D-02 | Detailed peak workload when sizing/testing infrastructure | Refines growth testing; fixed bed/admission reconciliation is not required | Later sizing/test plan |
| D-03 | Existing call-center product, APIs and supported events | Explicitly deferred by owner; do not investigate/build now | Future integration phase only |
| D-04 | Agent count, concurrent users, peak traffic, enquiry definition and retention | Determines realistic load and hosting needs | Sizing/test plan |
| D-05 | Bed distribution, exclusivity and rent cycle/grace/transfer examples | Prevents allocation and billing disputes | Accommodation design |
| D-06 | Package, discount, refund, stock-return and substitution authority | Defines controlled exceptions | Financial/clinical design |
| D-07 | Hospital-supplied payer names, tariff rules and verification fields | Configures insurance software; no independent empanelment investigation required now | Insurance setup |
| D-08 | Branch access boundaries and configurable invoice numbering | Supports future branches; premises/legal due diligence outside current work | Branch model |
| D-09 | Approved clinical forms/consents and voice priority | Defines usable doctor/therapy workflow | Clinical design |
| D-10 | Hosting, connectivity, devices, recovery targets and support team | Establishes operational feasibility | Deployment plan |
| D-11 | Build versus extend/configure; team's skills, budget and target date | Chooses implementation approach | Plan/estimates |
| D-12 | Migration depth, cutover owners and sign-off roles | Protects an operating hospital during transition | Go-live plan |

Already answered: location, operational status, absence of software, monthly enquiry period, growth-oriented capacity, space for expansion, future-only call-center integration, intended agent linkage, future branches, rented premises and owner-managed norms. Do not repeatedly ask these or make deferred/excluded topics development blockers.

## 18. Research limits and change log

Completed: consolidated document review, primary-source desk research and technical/operational gap assessment. Not completed: staff workflow sign-off, vendor demos, prototype/load test or production integrations. Premises/rental and regulatory verification are outside the current requested software scope; future call-center implementation is deferred.

Known evidence update: the 2026 Haryana policy PDF is now accessible and its scope was checked. Earlier reports' timeout notes are historical. AYUSH applicability and this hospital's agreements remain unverified. AIIA FAQ full fetch and NAMASTE direct portal access were previously unsuccessful; no unsupported detailed conclusions are added from them.

No source code, dependency installation, approved design or deployment has been created. Research is ready to support approach selection and workflow/design discussion; unresolved hospital-specific decisions are explicit rather than silently assumed.

Change log v1.0: consolidated original C-01–C-20, current owner clarifications, scale/call-center/branches, architecture recommendation, source updates, rollout and decision register.

Change log v1.1: owner clarified expandable capacity, future-only call-center integration, rented premises and fulfilled norms; removed these topics as current development blockers and retained scalable configuration/integration boundaries.
