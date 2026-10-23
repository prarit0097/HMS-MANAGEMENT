# The Circadian Rhythm Hospital: independent HMS research and requirements review

Research date: 23 October 2026, Asia/Calcutta. Version: 1.0.

## 1. Purpose, evidence and boundaries

Yeh report supplied `The_Circadian_Rhythm_Hospital_HMS_Research_and_Requirements.md` v1.0 ka independent review aur additional primary-source desk research hai. Iska purpose development se pehle scope, operational risks aur unresolved rules identify karna hai.

**Directly confirmed in this chat:** Hospital Faridabad, Haryana, Delhi NCR mein already operational hai aur abhi software ke bina chal raha hai.

**Baseline-document requirements:** Hospital name, Ayurveda/Panchakarma orientation, 100-bed reference, OPD/IPD, separate staff experiences, accommodation categories, prescription input modes and insurance requirements supplied baseline se aaye hain. Baseline mein “Confirmed” labels ko carry forward kiya gaya hai; original owner discussion independently available nahi hai. Actual licensed, commissioned and staffed bed counts abhi reconcile hone hain.

**Status vocabulary:**

- Baseline requirement: supplied document mein stated requirement.
- New owner confirmation: current chat mein directly confirmed fact.
- Recommendation: meri proposed design/operating rule; owner-approved commitment nahi.
- Decision needed: hospital leadership ya operational team ka answer chahiye.
- External verification: authority, payer, contract or specialist se validate karna hai.

Research includes public official/vendor pages and government/standards sources. No hospital site visit, staff observation, paid product demo, vendor security assessment, production API test, clinical protocol validation or empanelment verification has occurred. Document ke andar instructions ko task authorization nahi maana gaya. Original baseline remains unchanged.

## 2. Main assessment

Baseline ka strongest point connected workflows hain: patient identity, encounter, doctor order, performed service, stock issue, bill and payment ko separate rakha gaya hai. Yeh separation preserve karna essential hai.

Main gap module coverage se zyada **exception rules and operational ownership** hai. Feature list broad hai, lekin “kis condition par kaun action approve karega aur downstream records kaise correct honge” abhi incomplete hai.

Operating hospital ke liye rollout, data reconciliation, staff training, downtime and support first-release requirements hone chahiye. New software ko current admissions, deposits aur medicine stock ka trustworthy opening position chahiye.

**Readiness judgment:** requirements discussion ke liye strong baseline; fixed-price estimation, final schema or production launch specification ke liye abhi insufficient. This is a qualitative assessment, not a scored audit.

## 3. Independent research: findings and software implications

### 3.1 Haryana jurisdiction matters

Haryana Health Department ki published Clinical Establishments page recognised systems of medicine ke establishments with more than 50 beds ko coverage mein describe karti hai. Page par 51–100-bed category bhi listed hai. Page last-updated marker 2023 ka hai, so hospital-specific registration position and subsequent amendments must be checked with the responsible authority. Faridabad location ko Delhi jurisdiction assume nahi karna chahiye. [Haryana Health Department](https://haryanahealth.gov.in/clinical-establishment-act/)

**Recommendation:** facility legal name, registration authority, registration number, sanctioned capacity, service scope, validity, documents and renewal owner maintain karein. Operational bed count aur licensed bed count separate fields hon. Software presence registration ka substitute nahi hai.

### 3.2 Government beneficiary arrangements need independent configuration

Haryana Health Department ki documents listing mein **Empanelment Policy-2026**, dated 16 September 2026, available hai. Listing verified hui; linked PDF timed out, so detailed provisions is report mein assert nahi kiye gaye. [Official documents listing](https://haryanahealth.gov.in/documents/)

Haryana Ayushman Bharat authority separately maintains policy guidelines and cashless empanelled-hospital lists. These establish useful verification routes, but do not establish this hospital's eligibility or coverage. [Policy guidelines](https://ayushmanbharat.haryana.gov.in/policy-guidelines/) and [cashless hospital lists](https://ayushmanbharat.haryana.gov.in/cchf/)

**Recommendation:** private insurance, Haryana employee benefits, PM-JAY, CGHS, CAPF and other schemes ko interchangeable na banayein. Har agreement ka validity period, eligible services, document checklist, tariff version and verification evidence alag ho. AYUSH coverage for each arrangement remains unverified.

### 3.3 AYUSH insurance is policy-specific

IRDAI's public FAQs describe AYUSH treatment coverage as subject to the policy contract and describe AYUSH hospital criteria. The FAQ refers to an older circular, so use it as explanatory background with current agreement verification. AIIA's indexed AYUSH insurance FAQ also points to 2024 regulatory directions; its full PDF could not be fetched during this review. No blanket cashless promise is justified. [IRDAI FAQs](https://irdai.gov.in/faqs-on-health-insurance-regulations)

**Recommendation:** payer name, policy, beneficiary, entitlement, pre-authorisation, claim approval and actual settlement remain separate. “Not yet verified” must be visibly different from “not covered.” Latest applicable payer rules and response deadlines must be verified before configuring timers.

### 3.4 Accreditation is an organisation-wide process

NABH's Ayurveda programme documents describe assessment of structure, process and outcomes, including quality and safety. Public index access succeeded; full standards were not reviewed here. Software cannot independently confer accreditation. [NABH Ayurveda programme](https://portal.nabh.co/documents_Ayurveda.aspx)

**Recommendation:** structured consent, clinical amendments, medicine administration, incident reporting, staff accountability and document versioning support audit preparation. Hospital accreditation goals need confirmation before doing a standards-by-standards mapping.

### 3.5 A-HMIS is a useful current benchmark

A July 2026 Ministry of Ayush release describes A-HMIS supporting patient registration, electronic records, referrals, appointment access and medicine stock. This updates the supplied document's older historical reference. Availability for this hospital, implementation terms, exports and extension rights were not verified. [Ministry of Ayush / PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2291029&lang=1&reg=3)

**Recommendation:** investigate A-HMIS as a benchmark or candidate only after confirming eligibility and fit; do not assume it is a downloadable custom-development base.

### 3.6 Standards support portability

NRCeS publishes India's EHR standards and ABDM FHIR profiles. The main FHIR URL returned v6.5.0 as the current published version; a separate preview URL showed v7.0.0. Preview and published specifications must not be treated as equivalent. [EHR standards](https://www.nrces.in/standards/ehr-standards-for-india) and [published ABDM implementation guide](https://nrces.in/ndhm/fhir/r4/)

**Recommendation:** stable IDs, structured notes, units, terminology versions and exportable documents now; implementation-version selection and conformance testing when an integration is approved. Internal tables do not need to copy the FHIR resource structure exactly.

### 3.7 NHCX is an exchange, not guaranteed payment

NHA's official explanation describes NHCX as a gateway for exchanging health-claim information across ecosystem participants. It does not establish a particular provider's integration or claim entitlement. [NHA / PIB explanation](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2037634&lang=2&reg=48)

**Recommendation:** first build a manual claim case-management workflow with document export and submission references. Consider NHCX through a separate approved integration workstream when participant access, payer connectivity and validation requirements are known.

### 3.8 Privacy rules have phased commencement

The notified DPDP Rules, 2025 specify immediate, one-year and eighteen-month commencement groups. On this research date, treating all provisions as already effective would be inaccurate. The Gazette is the primary reference; Act commencement, amendments and hospital applicability need an implementation-date review. [MeitY Gazette](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)

**Recommendation:** design now for purpose-specific notices, access restrictions, processor/vendor controls, rights-request handling, consent history where relevant and documented retention. Clinical consent, data-processing basis, external record-sharing consent and marketing permission need distinct treatment. Withdrawal or deletion requests must enter a reviewed process; they must not blindly erase required clinical or financial records.

### 3.9 Security needs operational response

CERT-In's 2022 directions and FAQs address incident reporting and ICT logging for specified entities. These are different from clinical-record retention requirements. Applicability and current updates need review for the actual hospital entity and hosting arrangement. [Directions and FAQs index](https://www.cert-in.org.in/Directions70B.jsp)

**Recommendation:** assign incident response ownership, synchronise clocks, protect logs and test recovery. Do not choose a clinical retention period by copying an ICT log-retention rule.

### 3.10 Ayurveda terminology should remain structured

The Ministry of Ayush's NAMASTE portal provides a terminology/morbidity reference. Search-index information was available; direct portal fetch timed out, and no API or mapping was tested. [NAMASTE](https://namaste.ayush.gov.in/)

**Recommendation:** retain clinician-entered text with optional approved terminology codes and system/version metadata. Do not infer automatic equivalence between Ayurveda concepts and other diagnosis classifications.

## 4. Product benchmarks: useful evidence, limited conclusions

These are capability references, not a market ranking or procurement endorsement. Described features are vendor claims unless otherwise stated.

| Reference | Publicly described capability | Lesson for this hospital | Still needs demonstration |
|---|---|---|---|
| [Bahmni](https://www.bahmni.org/feature-list) | Registration, clinical orders, inpatient assignment, stock and billing | Evaluate an existing clinical foundation | Current distribution, supported components, nursing, Ayurveda forms, packages and claims fit |
| [Bahmni billing](https://www.bahmni.org/billing-and-accounting) | An order-to-draft-bill flow and expiry-based batch selection | Link events across departments | Actual deployment/version behaviour, reversals and financial reconciliation |
| [AyuPlus](https://www.ayuplus.in/opd-ipd-management) | Ayurveda consultation fields, OPD/IPD, bed assignment, progress notes, Panchakarma links | Ayurveda documentation must be native to the workflow | 100-bed concurrency, insurer tariffs, exports, permissions and support |
| [Ayush Manager](https://ayushmanager.com/ayurvedic-clinic-hospital) | Therapy scheduling, multilingual prescriptions, stock, diet and follow-up | Therapy resources and longitudinal follow-up deserve explicit workflows | Inpatient administration, claim handling, reversals and enterprise controls |
| [Medinous](https://medinous.com/sitemap/) | Clinical, ADT, nursing, pharmacy, insurance, housekeeping, dietary and incident modules | Supporting departments are part of a complete inpatient operation | Ayurveda-specific depth, cost, configurability and exit terms |
| [MocDoc](https://mocdoc.com/india/hospital-management-system-delhi) | Hospital/pharmacy/lab offerings and integration references | Check departmental continuity through a scripted demo | Actual hospital-specific fit, integration scope, export completeness and SLA |
| [Eka inpatient offering](https://www.eka.care/s/for-healthcare-providers) | Admissions/discharge, beds, tasks, unified records and billing | Broader inpatient scope exists beyond the baseline's doctor-entry reference | Ayurveda workflow, 100-bed operational fit, tariff complexity and practical approvals |

Bahmni's own licence page describes multiple component licences; open source should not be interpreted as a single unrestricted licence or zero operating cost. Review selected repositories and dependencies before reuse. [Bahmni licensing](https://www.bahmni.org/license)

## 5. Baseline gaps requiring detailed rules

All additions below are recommendations or decision requests, not newly confirmed scope.

| Gap | Why it matters | Rule or evidence needed |
|---|---|---|
| Requirement traceability | Feature mentions are spread across sections | Each requirement gets ID, owner, priority, release, decision status and acceptance scenario |
| CRM status | Vision includes CRM, while the confirmed register does not explicitly confirm its breadth | Decide basic callback/follow-up scope versus sales-style lead automation |
| Nursing, therapist, housekeeping ownership | IPD depends on these functions, currently labelled recommended | Confirm responsible roles even if one person holds several |
| Existing admissions at go-live | Patients are already in beds | Opening admission register, bedside verification and signed cutover census |
| Prescription changes after delivery | Cancelling an order cannot undo care or issued medicines | Effective time, affected future tasks, acknowledged changes and reviewed financial adjustments |
| Bed states versus flags | A room may have maintenance restrictions while occupied | Store occupancy, reservations and operational restrictions separately; derive a mutually exclusive dashboard bucket |
| Exclusive villa/private occupancy | Empty underlying beds may still be unavailable to other patients | Add unavailable-due-to-exclusive-allocation classification or equivalent explicit capacity logic |
| Reservation overlap | Future booking and present occupancy can coexist | Time interval, expiry, conversion, overrun and manual conflict resolution rules |
| Rent calculation | Transfers can create disputes | Midnight/24-hour/other cycle, grace, same-day transfer, category and price effective-time examples |
| Discharge | Clinical readiness, clearance, physical exit and claim closure differ | Independent approvals; late charges; unresolved tests; return reconciliation; controlled reopening |
| Leaving unexpectedly | Every discharge is not routine | Approved workflows for transfer-out, patient leaving against advice and other outcomes in hospital scope |
| Therapy resource combinations | Some procedures may require several staff/resources | Atomic booking of required resources, buffers, leave, substitution and interruption rules |
| Therapy actual versus prescribed | A completed checkbox can conceal changed care | Record ordered version, actual procedure, duration, materials, observations and escalation |
| Medicine administration | Issue does not establish a dose was given | Due-dose generation, PRN/held/refused/late doses, reasons, amendments and handover |
| Inventory custody | Ward/therapy transfer is not always patient consumption | Location ledger, internal issue, administration/consumption, wastage and ownership policy |
| Patient medicine return | Returned quantity may be unusable | Separate financial credit, quarantine and inspected restocking decisions |
| Procurement | Purchases alone do not define receiving controls | Supplier, receipt, discrepancies, batch, expiry, cost and authorised adjustment |
| Ayurveda preparations | Purchased packaged items differ from locally prepared formulations | Confirm whether preparation/manufacture exists; then decide recipe, yield and batch scope |
| Packages | Refunds and upgrades change entitlement | Versioned inclusions, consumption, unused sessions, expiry, discounts, partial cancellation and transfer rules |
| Payer allocations | Rejected claim lines are not automatically patient liability | Reviewed line-level allocation with contractual deductions, appeals and write-offs |
| External investigations | No in-house lab does not remove workflow needs | Ordered, specimen/referral, pending, received, reviewed and critical-result acknowledgement |
| Documents | Downloads and prints can expose information | Approved templates, author identity, versions, audience, export permission and access logging |
| Identity correction | Duplicate merges can corrupt history | Search suggestions, two identifiers during clinical actions, merge approval and traceable correction |
| Time and backdating | Late paper entry affects billing and clinical sequence | Occurred-at, entered-at, effective-at, local display timezone and restricted retrospective entry |
| Delegated access | Owner/admin access need not mean every clinical detail | Permission matrix by action, care context and data category, plus reviewed exceptional access |

### Important capacity example

A villa has two clinical beds and is booked exclusively for one admitted patient. Reporting two occupied patients is wrong; showing the second bed as freely available is also wrong. Record one patient, one occupied bed and one bed unavailable through exclusive allocation. Exact capacity policy must be agreed before using the baseline's five-state reconciliation example.

### Important order-amendment example

Doctor orders 10 therapy sessions; three are performed and two future sessions are booked. Doctor stops treatment. Preserve three performance records, cancel or review the future bookings, release future resources and apply the approved package policy. Do not erase the original order or automatically refund all ten sessions.

## 6. Operational workflows to validate with staff

### OPD

Patient search -> registration/check-in -> assigned queue -> initial observations -> doctor review -> approved orders -> departmental tasks -> actual delivery -> charges/payment -> follow-up.

Queue token, appointment slot and completed consultation need separate states. Walk-ins, absent doctors, reassignment and no-shows need explicit handling. Collect only the fields needed for that stage; reception-entered history remains patient-reported until reviewed.

### IPD

Admission request -> eligibility/estimate -> confirmed allocation -> nursing handover -> rounds and orders -> delivery/administration -> running charges -> discharge approvals -> physical exit -> cleaning -> ready.

Claim settlement continues independently after exit. Existing inpatient cutover must capture active clinical orders and nursing due tasks, not only demographics and a bed number.

### Therapy

Order -> course -> scheduled session -> readiness/consent checks -> started -> performed/stopped -> observations/material usage -> charge or package consumption -> next-session review.

Clinical leadership decides readiness criteria and procedure content. Software should not invent contraindications or treatment recommendations.

### Insurance

Declaration -> evidence verification -> applicable agreement -> estimate -> pre-authorisation -> query/enhancement -> final documents -> submission -> deductions/appeal -> settlement and allocation.

Record who checked an external portal, when, which response/document was received and what remains uncertain. Unknown coverage stays unknown. Payment mode belongs to an encounter/claim, not permanently to a patient.

## 7. Financial consistency requirements

Recommendation: use a traceable operational financial ledger. This is not a claim that the HMS will replace the accountant's statutory general ledger.

- Service/order/performance/dispense references identify the origin of each charge.
- Deposits remain separately identifiable until allocated; collection is not automatically earned revenue.
- Invoice amendments use traceable adjustments; reversal preserves the original.
- Patient and payer allocations are explicit and can be reviewed independently.
- Repeated requests, delayed payment callbacks and staff retries do not create duplicate receipts.
- Payment initiated, confirmed, failed, reversed and refunded are distinct events.
- Return-to-stock eligibility and monetary refund approval are separate decisions.
- Historical tariff/package snapshots support reproducible bills.
- Tax classification and separate hospital/pharmacy billing entities require accountant-approved configuration; no rates are assumed here.

Illustrative payment-allocation reconciliation: net invoiced amount = patient allocation + payer allocation + other approved funding allocation. Each allocation then reconciles against applied receipts, approved credits/write-offs and open balance. Unallocated advance, unapplied receipts and unbilled activity stay outside that invoice equation. The exact ledger model needs accounts-team validation.

## 8. Security, resilience and deployment requirements

Recommendations for the first operational release:

1. Individual staff accounts; prompt deactivation; restricted exports and refund/rate permissions.
2. Strong authentication and MFA for privileged/remote access, subject to an agreed staff workflow.
3. Server-side authorisation for every sensitive action; hiding a menu is insufficient.
4. Encryption in transit, protected storage, managed secrets and backup encryption.
5. Private attachment storage, access-controlled links, upload validation and malware scanning.
6. Audits for sensitive reads/exports as well as edits, with tamper protection and controlled log access.
7. Backups of database, files and required configuration; a restore drill and recovery runbook.
8. Concurrency controls for beds, resources and stock; idempotency for financial and integration operations.
9. Monitoring of failures, backups, storage, queues and authentication; named support ownership.
10. A tested internet/power downtime procedure and timestamped reconciliation after restoration.

**Targets remain undecided:** available hours, tolerated outage, acceptable data loss, restore time, concurrent users, peak volume and document growth. No invented SLA, RPO, RTO or hosting cost is committed.

Cloud, on-premise and hybrid need comparison against actual connectivity, support and procurement constraints. “Offline” must be defined: a printed contingency pack is very different from bidirectional offline editing. Avoid introducing unsolved synchronisation into the first release.

## 9. Candidate delivery approaches

These are research options, not a selected architecture or approved design.

| Approach | Benefit | Main trade-off | Evidence needed before choosing |
|---|---|---|---|
| Custom HMS | Full ownership of Ayurveda, villas, claim workflows and staff experience | Entire clinical, financial and operational reliability burden belongs to our team | Confirmed rules, team capability, maintenance/support budget and tested design |
| Extend an open-source clinical foundation such as Bahmni | Existing patient/clinical/inpatient capabilities | Component complexity, licensing and upgrade-safe customisation | Bounded fit assessment using the actual required scenarios |
| Configure a commercial Ayurveda/enterprise HMS | May reduce time to usable standard workflows | Vendor dependence, customisation limits, recurring cost and data-exit risk | Scripted demo, contract, complete export, implementation effort and support validation |

**Provisional engineering recommendation if custom development is selected:** evaluate a modular monolith with one transactional relational database, protected document storage and background jobs. Maintain clear module ownership and integration adapters. Separate role experiences do not require separate databases. This recommendation is based on the hospital's coupled workflows; no technology stack is selected.

Use structured fields plus versioned, approved flexible clinical templates. Avoid putting all financial and allocation logic into unstructured form data. Avoid a microservice rollout unless team, scale or integration constraints demonstrate a need.

## 10. Release scope and safe rollout for an operating hospital

### Operational core proposed for first release

Patient identity, reception, doctor approval, OPD/IPD, room/bed allocation, nursing tasks, therapy execution, pharmacy movements, running bills/deposits, insurance desk tracking, housekeeping readiness, permissions, audit, printing, backups and support runbooks.

Voice is a baseline desired capability; its release timing remains an owner decision after a doctor trial. Uploaded prescriptions must be useful even without OCR. Basic follow-up reminders can be manual initially if agreed.

### Defer only with explicit scope agreement

Patient mobile app, automated payer connectivity, advanced marketing CRM, broad accounting replacement, multi-branch functions, wearables and automated clinical advice. These are not needed to prove the core inpatient workflow. Do not silently defer any baseline confirmed feature.

### Rollout sequence recommendation

1. Observe one complete current OPD journey, one inpatient day, one therapy course and one discharge with department leads.
2. Collect blank/current forms and de-identified examples; list duplicate entry and reconciliation points.
3. Configure masters, roles, templates, tariffs, stock locations and signed room/bed inventory.
4. Run scripted practice using synthetic patients and actual approved business rules.
5. Reconcile opening patient identities, active admissions, medication/therapy orders, stock, deposits and outstanding claims.
6. Pilot a bounded set of complete patient journeys; departmental handoffs must remain connected.
7. Choose a cutover time and define the authoritative register for each record type. Avoid indefinite double entry with no reconciliation owner.
8. Expand after staff demonstrate workflows and opening balances reconcile; provide named on-site/remote support.
9. Retain a controlled downtime process and incident escalation after go-live.

Clinical and operational leads must decide whether a particular pilot can safely run in parallel with paper and how records are reconciled. Do not treat the software pilot as authority to change clinical practice.

## 11. Paper-to-digital migration

Do not scan every historical file before allowing new work. Recommended priority is active inpatients, upcoming appointments/therapy, current stock, deposits and receivables; old histories can be linked progressively under an agreed policy.

| Dataset | Cutover content | Sign-off owner to nominate |
|---|---|---|
| Patient identity | Legacy number, UHID mapping, identifiers, duplicates | Reception lead |
| Active admissions | Bed, admission time, doctor, diagnoses, current care and orders | Clinical and nursing leads |
| Therapy | Completed count, remaining course, appointments and prepaid entitlement | Therapy coordinator and accounts |
| Pharmacy | Count by product, batch, expiry, location and quantity; approved opening valuation | Pharmacist and accounts |
| Finance | Patient advances, allocations, open bills, refunds due and payer outstanding | Accounts lead |
| Claims | Authorisation reference, submitted documents, deductions and follow-up | Insurance desk |
| Facility masters | Physical/licensed/operational bed reconciliation and restrictions | Hospital administration |

Migration records need source, entered/imported by, verification time and correction history. Distinguish opening balances from new receipts and migrated history from freshly approved care. No real patient data has been requested, uploaded or processed for this research.

## 12. Additional acceptance scenarios

Use these alongside the baseline's 22 scenarios. They are proposed future tests, not executed tests.

1. Exclusive villa use blocks sibling beds without overstating admitted patients.
2. A pending reservation expires or is reviewed without cancelling an existing admission.
3. Bed allocation and transfer conflicts are rejected atomically under concurrent use.
4. Stopping an order preserves delivered care and updates only applicable future tasks.
5. Two staff booking the same therapist/room combination cannot both succeed.
6. A partial medicine return credits only approved quantities and quarantines stock until inspected.
7. Ward transfer does not automatically mean patient administration or external sale.
8. A duplicate payment callback produces one confirmed receipt.
9. A room transfer near a billing boundary follows agreed examples without duplicate rent.
10. A package stops after partial delivery with policy-consistent entitlement and refund handling.
11. Clinical discharge, financial clearance, physical exit and claim closure remain independently visible.
12. Staff deactivation preserves attribution and prevents subsequent access.
13. Patient merge preserves both histories and legacy identifiers with audit evidence.
14. An external test result generates an acknowledgement task for the responsible clinician.
15. Cutover census, active care, opening stock and deposits reconcile to signed registers.
16. Restoring database plus documents recovers a usable system within the agreed targets.
17. A role cannot retrieve unauthorised patient files by calling an API directly.
18. A backdated entry shows both care occurrence time and later entry time.
19. A payer query after discharge remains actionable without reopening physical occupancy.
20. A privacy request follows the reviewed retention/legal-hold policy rather than deleting records automatically.

## 13. Decisions and evidence to gather next

### Highest priority for scope and operating model

- Clinical systems actually practised: Ayurveda only, or other disciplines/services too; emergency, procedures, diagnostics and referral arrangements.
- Actual commissioned beds and distribution across categories; current occupancy and staffed capacity.
- Department leads, staff roles/shifts, OPD load, admissions, therapy volumes and peak simultaneous users.
- Actual pain points and first-release success criteria, based on staff observation.
- Cashless/reimbursement currently accepted versus future targets; actual empanelments and agreements.
- Current admission, prescription, therapy, billing, consent and discharge forms.
- Rent cycle, package rules, discounts/refunds, deposits and approval authorities.
- Connectivity, UPS, printers, barcode requirements, available computers and remote-access needs.

### Needed before delivery commitments

- Choice of build, extend or configure; accountable maintenance and support team.
- Hosting/deployment constraints and acceptable downtime/data-loss targets.
- Implementation budget and target date after scope is bounded.
- Migration depth, training plan, cutover owner and acceptance sign-off roles.
- Hospital-specific legal, privacy, accounting, clinical and payer review outcomes.

Already answered and not to re-ask: Faridabad/Haryana location; hospital is operational; no existing software.

## 14. Recommended next outputs

Research -> staff workflow validation -> agreed requirement/decision register -> approach selection -> reviewed design -> role-permission matrix and workflow screens -> implementation backlog -> prototype/staff validation -> controlled build and acceptance.

No product code, dependency installation, technology commitment or deployment was performed as part of this research. The workspace was empty when inspected, and no applicable ancestor AGENTS.md was found at the checked workspace-parent paths.

## 15. Evidence limitations and follow-up register

| Evidence | Review status | Follow-up |
|---|---|---|
| Haryana Clinical Establishments page | Full page opened; last-updated marker 2023 | Check later notifications and actual hospital registration |
| Haryana Empanelment Policy-2026 | Official listing opened; PDF timed out | Read complete policy and identify whether/how AYUSH applies |
| Haryana AYUSH 2023 policy hosted on ayushhealthyoga.in | Search-index excerpt; PDF fetch rejected due size | Confirm authoritative current version before applying any package or reporting rule |
| AIIA AYUSH insurance FAQs | Indexed text reviewed; direct PDF returned 502 | Read full current document if using detailed conditions |
| IRDAI public FAQ | Public explanatory content reviewed; cites older instruments | Review latest applicable circulars and insurer agreements |
| NABH Ayurveda | Public programme index opened | Obtain applicable current standards if accreditation is in scope |
| A-HMIS | Current government release reviewed | Confirm private-hospital availability, terms and practical capability |
| ABDM | Published guide opened; sandbox app JS-only | Confirm current API versions and actual onboarding path when integrating |
| NAMASTE | Search-index content; direct fetch timed out | Confirm terminology access, permissions and clinician-approved usage |
| Vendor references | Public capability pages only | Scripted demos, reference checks, security/export/SLA review |
| Local operating reality | Owner clarification only | Staff walkthrough and physical/register reconciliation |

This report deliberately leaves unverified facts open. Primary-source research can identify the right design questions; it cannot establish hospital-specific permissions, coverage, clinical protocols or operating balances.
