# The Circadian Rhythm Hospital
## HMS + Ayurveda/Panchakarma + IPD + Insurance + CRM

**Document:** Consolidated research and functional requirements  
**Version:** 1.0 — discussion baseline  
**Prepared:** 23 October 2026, India time  
**Language:** Hinglish with development-friendly English terminology  
**Hospital capacity reference:** 100 beds, as specified by the hospital owner  
**Status:** Requirements consolidation; software implementation, commercial estimates and vendor selection are not completed.

---

## 1. Purpose and requirement status

Is document mein ab tak ki discussion, official-source product research, confirmed hospital requirements aur recommended additions consolidate ki gayi hain. Yeh next discussion, screen planning, database design aur development scope ka working reference hai.

### Status labels

- **Confirmed:** User ne directly specify kiya hai.
- **Recommended:** Discussion mein proposed feature; implementation detail hospital team se finalise karna hai.
- **Pending decision:** Business/clinical/financial rule abhi decide hona hai.
- **External verification:** Insurer, scheme, vendor, applicable rules ya agreement se confirm karna hai.

Previous assistant suggestions ko automatically owner-approved requirement nahi maana gaya hai. Research product websites ke public descriptions par based hai; hands-on demos, contracts, security audits aur production integrations verify nahi kiye gaye.

## 2. Product vision

**Confirmed:** The Circadian Rhythm Hospital ke liye connected hospital management system banana hai, jisme reception, doctors, pharmacy, accounts aur central admin ke role-specific panels hon. Hospital Ayurveda-oriented hoga aur patients admit bhi honge.

System ki foundation:

1. Ek patient ka permanent hospital record.
2. Har OPD visit aur IPD admission ki separate identity.
3. Doctor-approved orders se departmental worklists.
4. Room aur bed allocation ka live record.
5. Prescribed, scheduled, performed, dispensed, billed aur paid events ki separate tracking.
6. Insurance/scheme information ka relevant departments mein continuous visibility.
7. Patient inquiry aur follow-up ke liye connected CRM.

**Important distinction:** Staff portals separate experiences honge, lekin patient data ek connected system mein rahega. Har role ko poora confidential record dena zaroori nahi hai.

## 3. Confirmed requirements register

| ID | Confirmed requirement |
|---|---|
| C-01 | Hospital name: The Circadian Rhythm Hospital |
| C-02 | Reception patient details, history aur doctor selection record karegi |
| C-03 | Reception ka separate portal hoga |
| C-04 | Doctor consultation aur prescription record karega |
| C-05 | Doctor prescription type, upload aur voice se draft kar sakega |
| C-06 | Treatment medicine-only, therapy-only ya dono ho sakta hai |
| C-07 | Reception therapy coordination/scheduling karegi |
| C-08 | Pharmacist actual supplied medicines update karega |
| C-09 | Accounts ka separate billing/payment portal hoga |
| C-10 | Central admin staff IDs, rules aur rates manage karega |
| C-11 | IPD admissions first operational scope mein honge |
| C-12 | General, semi-private, private, private luxury aur villa accommodation categories honge |
| C-13 | Room types, room numbers aur rates configurable honge |
| C-14 | Unique bed numbers aur room-to-bed mapping hogi |
| C-15 | Hospital ke 100 beds ka total, filled, empty aur room-wise distribution dikhega |
| C-16 | Booked/occupied indicator green aur unbooked/available indicator red hoga; text labels bhi honge |
| C-17 | Reception private insurance aur government/employer card details poochegi |
| C-18 | Insurer/card name, coverage limit aur AYUSH coverage capture hogi |
| C-19 | Cashless aur reimbursement workflows honge |
| C-20 | Coverage summary reception, doctor, pharmacy, accounts aur relevant portals mein dikhegi |

## 4. Indian HMS research and design benchmarks

Kisi verified market-share ranking ke bina in platforms ko numerical “India ke top” order mein rank nahi kiya gaya. Yeh hospital ke use case ke relevant reference products hain.

| Reference | Officially described capabilities | Design lesson | Source |
|---|---|---|---|
| MocDoc | OPD registration, queues, clinical notes, prescriptions, pharmacy, batches, stock and billing | Reception-to-pharmacy continuity aur departmental worklists | S1 |
| Medinous | EMR, doctor workbench, OPD/IPD, nursing, pharmacy, dietary management, billing and insurance modules | Full hospital departmental architecture | S2 |
| Bahmni | Open-source patient registration, clinical services, prescriptions/orders, inpatient beds, stock and accounting | Existing foundation customise karne ka option | S3, S4 |
| Eka Care / DocAssist | Digital prescription, practice management, follow-up and voice-based structured documentation | Doctor entry effort kam karna | S5, S6 |
| AyuPlus | Ayurveda OPD/IPD, Prakruti assessment, Panchakarma records and billing | Procedure-specific Ayurveda documentation | S7, S8 |
| Vaidya Manager / Ayush Manager | Therapy scheduling, prescriptions, multilingual entry, diet, reports and follow-up | Therapy plus dietary/lifestyle workflow | S9 |
| Ministry of Ayush A-HMIS | Integrated patient-care and administrative platform for Ayush facilities | Ayush system-specific government reference | S10, S11 |

### Research limitations

- Vendor claims are not independent proof of operational quality, adoption, compliance or integration success.
- Current prices, SLA, customisation cost, data export quality and implementation effort have not been validated.
- No paid subscription or vendor demo has been purchased or conducted.
- A-HMIS direct page fetch failed during one research attempt; government portal and Ministry publication supplied supporting description.
- Our proposed features below are recommendations, not claims that every benchmark product offers all of them.

### Build versus customise

**Recommended:** Fresh development aur Bahmni jaise existing foundation ki customisation ka bounded technical evaluation karein. Open-source licensing ka matlab implementation/hosting/support free hona nahi hota. Final choice Ayurveda forms, usability, insurance tariff complexity, maintainability aur team capability par depend karegi.

## 5. Identifiers and shared patient record

| Entity | Purpose |
|---|---|
| UHID | Permanent patient identity across all visits/admissions |
| OPD visit ID | Specific outpatient consultation |
| IPD admission ID | Specific inpatient stay |
| Order ID | Medicine, therapy, investigation or other authorised service |
| Session ID | Individual therapy appointment/performance |
| Room ID / bed ID | Accommodation resource |
| Invoice / receipt ID | Financial documents |
| Coverage record / claim ID | Policy/scheme details and admission-specific claim |

**Recommended rules:** Mobile number ko unique patient key na banayein; ek family same mobile share kar sakti hai. Duplicate suggestions show karein, but record merge authorised review se ho. Historical records ko silently overwrite na karein.

Patient-level insurance record renew/update ho sakta hai. Har admission/claim par us waqt ki verified coverage aur tariff ka snapshot preserve rahe.

## 6. End-to-end workflow

### 6.1 OPD

1. Reception existing patient search kare ya quick registration kare.
2. Demographics, visit reason, documents aur insurance/card declaration capture ho.
3. Doctor assignment, token aur check-in ho.
4. Vitals/initial history authorised staff enter kare.
5. Doctor history verify kare, consultation aur treatment plan record kare.
6. Approved prescription se medicine/therapy/test worklists create hon.
7. Medicine ho to pharmacy actual dispensing record kare.
8. Therapy ho to reception coordinator resources/time book kare aur therapist session record kare.
9. Accounts applicable charges, deposits aur payments handle kare.
10. Approved documents aur follow-up plan patient ko diya jaye.

Payment services se pehle ya baad mein hospital policy ke according configure hoga; clinical/service order aur collection separate events hain.

### 6.2 IPD

1. Doctor admission advise kare; authorised direct admission route bhi configurable ho.
2. UHID select/create karke separate IPD number generate ho.
3. Treating doctor, diagnosis/reason, attendant, consent aur payer details capture hon.
4. Eligible room category aur available bed choose ho.
5. Estimate, package, deposit aur coverage verification/pre-auth workflow start ho.
6. Admission confirm hone par selected bed occupied ho aur ward worklists update hon.
7. Nursing, rounds, therapy, pharmacy aur investigations connected record mein chalein.
8. Services/usage se charges rules ke according running bill mein aayein.
9. Zaroorat par room transfer, approval enhancement aur revised orders record hon.
10. Doctor discharge plan approve kare; summary and take-home prescription prepare ho.
11. Pharmacy returns, services reconciliation aur financial clearance process ho.
12. Patient ke physically exit karne par bed cleaning pending ho.
13. Housekeeping confirmation ke baad bed available ho.
14. Insurance/scheme receivable settlement discharge ke baad bhi tracked rahe.

### 6.3 Medicine and therapy routing

Doctor ki approved prescription se departmental orders automatically populate karna recommended hai. Reception doctor ki therapy choice dobara type na kare; reception schedule/resources manage kare. Paper uploads se extracted orders clinical approval ke bina release na hon.

## 7. Roles and portals

| Portal / role | Main responsibilities | Status |
|---|---|---|
| Admin | Configuration, accounts, permissions, masters, rates and oversight | Confirmed |
| Reception / admission | Registration, queues, bookings, admissions and bed allocation | Confirmed |
| Doctor | Clinical notes, diagnosis, orders, prescription, rounds, discharge | Confirmed |
| Pharmacy | Stock, actual issue, partial dispensing and returns | Confirmed |
| Accounts | Estimates, bills, deposits, collections and refunds | Confirmed |
| Therapist / Panchakarma | Assigned therapy, performance and observations | Recommended |
| Nursing / ward | Vitals, medicine administration, monitoring and handover | Recommended; necessary IPD workflow |
| Insurance / TPA desk | Eligibility, approvals, queries, claims and settlement | Recommended |
| Housekeeping | Cleaning assignments and bed readiness | Recommended |
| Maintenance | Room/bed/equipment blocking and repair status | Recommended |
| Diet / kitchen | Doctor-approved meal instructions and service list | Recommended |
| Patient portal | Approved reports, bills, bookings and schedule | Later phase |

Small team mein ek person ko multiple approved roles mil sakte hain. Shared staff logins avoid karein; action actual staff identity se record ho.

## 8. Central admin panel

### 8.1 User administration

- Staff create, invite/activate, disable and role assign.
- Department, branch if later required, ward and reporting assignment.
- Granular view/create/edit/approve/cancel/refund/export permissions.
- Discount limits, refund approval aur exceptional override permissions.
- Login/session management and sensitive access audit.
- Staff deactivation se historical actions delete na hon.

### 8.2 Masters

- Departments, doctors, clinic timings and appointment slots.
- Medicine names, formulations, units, pack conversions, rates and applicable tax setup.
- Therapies, duration, resources, consumables, forms and charges.
- Buildings, floors, room categories, rooms/villas, beds, amenities and capacity.
- Consultation, rounds, nursing, tests, meals and additional service charges.
- Packages, inclusions, exclusions and extra-use rules.
- Insurers, TPAs, schemes, corporate payers and agreements.
- Document templates, numbering formats, consent forms and notification templates.

### 8.3 Tariff rules

Rates effective-date ke saath versioned hon. Medicine batch/MRP and selling-price constraints, where applicable, accountant/pharmacy team define kare. Self-pay, insurer aur scheme tariff books separate ho sakti hain.

**Business invariants:** Finalised old bills automatically reprice na hon. Running admissions ko new rate par shift karne ka rule explicit ho. Financial adjustment/refund original transaction ko erase karke na ho; traceable correction document ho.

## 9. Reception and intake

### Quick registration

Name, age/DOB, contact, gender as clinically/administratively required, address, visit reason, selected doctor and patient category.

### Detailed intake

- Complaints and patient-reported history.
- Ongoing medicines, allergies, previous treatment and relevant conditions.
- Uploaded lab reports, prescriptions and referral documents.
- Emergency contact/attendant and relationship.
- Insurance/card declaration, document capture and verification task.
- Communication and relevant consent records.

Reception history ko patient-reported mark karein. Doctor verification aur clinical assessment separate hon. Long form ke karan quick check-in unnecessarily block na ho; mandatory fields hospital policy se decide hon.

Reception views: doctor queues, waiting patients, therapy-to-schedule list, follow-up appointments, admission requests and room/bed board.

## 10. Doctor portal and prescription

### Clinical workspace

Patient history, allergies, previous notes, uploaded reports, current vitals, previous prescriptions, active admission, relevant payer status and today’s worklist ek coherent screen mein available ho.

### Input modes

| Mode | Behaviour |
|---|---|
| Typed | Structured clinical fields, medicine/therapy search and saved templates |
| Uploaded | Original image/PDF preserved; optional extraction produces reviewable draft |
| Voice | Hindi/English dictation produces editable clinical/prescription draft |

Voice/OCR se medicine name, dose, unit, frequency aur duration incorrectly capture ho sakte hain. Doctor approval ke baad hi actionable orders release hon. Original upload aur approved structured version dono preserve hon. Audio recording retention/consent policy pending decision hai.

### Medicine prescription fields

Medicine/formulation, strength, dose, unit, route, frequency, duration, quantity, before/after-food instruction, applicable Anupana and additional guidance.

### Therapy order fields

Procedure, course/session count, duration, body area, applicable material/oil/medicine, preparation instructions, precautions, monitoring and review requirements.

### Clinical lifecycle

Draft → Approved → Amended/Superseded, with original versions retained. Reception/pharmacy clinical orders independently change na karein. Template reuse current patient ke liye review ke baad ho.

IPD doctor features: daily rounds, progress notes, revised orders, investigations, discharge advice and discharge summary approval.

## 11. Ayurveda and Panchakarma

**Recommended optional templates:** Prakriti/Vikriti, Dosha assessment, Agni, Koshtha, relevant Ashtavidha/Dashavidha examination, Pathya–Apathya, dietary/lifestyle instructions and procedure-specific records. Clinical leadership templates and mandatory fields finalise kare.

All patients par all fields compulsory nahi honge. Procedure content doctor-approved clinical protocols se aayega; this document is software design, not treatment guidance.

### Scheduling

- Doctor-approved order reception/therapy coordinator ki list mein aaye.
- Date, time, therapist, room/bed and equipment allocate hon.
- Therapist availability, leave, preparation and cleaning gaps consider hon.
- Same therapist/resource ki overlapping appointment block ho.
- Session status: ordered, scheduled, arrived, started, completed, missed, postponed, stopped or cancelled.
- Prescribed count, scheduled count and completed count separate ho.

### Therapist recording

Instructions, actual start/end, performed treatment, actual material usage, observations and escalation to doctor. Unexpected observation par doctor review task ban sake. Completed session edit authorised correction ke saath ho.

## 12. Rooms, wards, villas and 100-bed management

### Resource hierarchy

**Hospital → Building/block → Floor → Ward/room/villa → Bed.**

| Category | Allocation model |
|---|---|
| General ward | Every bed individually identified and assigned |
| Semi-private | Beds separately tracked; partial room occupancy visible |
| Private | Exclusive room booking linked to physical bed(s) |
| Private luxury | Exclusive room with category tariff/amenities |
| Villa | Whole-unit booking with physical beds and permitted occupancy configured |

**Prevent duplicate capacity:** Room aur uske beds ko separate inventory capacity ki tarah double-count na karein. Companion/attendant sleeping facilities ko clinical beds mein tabhi count karein jab hospital explicitly aisa classify kare. Villa-exclusive booking underlying beds ko conflicting allocations se protect kare.

### Resource fields

Room/ward number, category, floor, bed number, clinical capacity, exclusive/shared allocation rule, applicable tariff, amenities, active/inactive status and maintenance flag.

### User-required colours and labels

| State | Indicator | Meaning |
|---|---|---|
| Occupied | Green + OCCUPIED | Patient currently admitted on bed |
| Booked/reserved | Green booked marker + RESERVED text | Reservation, admission pending |
| Available/unbooked | Red + AVAILABLE | Empty and ready for allocation |
| Cleaning pending | Yellow + CLEANING | Not ready for next patient |
| Maintenance/blocked | Grey + BLOCKED | Temporarily unavailable |

Booked and occupied both use the requested green family, but distinct text/icon/border keeps them distinguishable. Status text is mandatory for accessibility and clarity. Future dated booking current occupancy ko replace na kare.

### Dashboard example — illustrative numbers only

| Capacity state | Example count |
|---|---:|
| Total active clinical beds | 100 |
| Occupied | 65 |
| Reserved for current allocation window | 5 |
| Available | 25 |
| Cleaning pending | 3 |
| Maintenance/blocked | 2 |
| Reconciled total | 100 |

Actual counts live allocations se calculate honge. Future reservations separate calendar/list mein dikhengi; aaj occupied bed ki kal ki reservation aaj ke status total mein dobara count nahi hogi. Operational occupancy percentage ka denominator explicitly define karein, particularly blocked beds ke treatment ke liye.

### Room-wise display

Example: Semi-private SP-01 → 2 beds → 1 occupied / 1 available. Room card par capacity and availability, bed tiles par individual status. Patient name/IPD/doctor details only authorised views mein; public/shared display anonymised ho.

### Transfers and discharge

Transfer source/target bed, time, reason and staff identity save kare. Old/new billing periods overlap na karein. Doctor discharge approval se bed immediately available na ho: physical checkout → cleaning → ready confirmation follow ho.

Room rent cycle pending: calendar day, rolling 24 hours or fixed checkout; grace period, late charge and transfer prorating explicitly decide hon.

## 13. Nursing and inpatient care

- Ward-wise census and admission handover.
- Vitals and nursing notes.
- Authorised medicine administration record: due/given/held/refused/missed and reason.
- Doctor instructions and pending tasks.
- Monitoring charts such as intake/output when ordered.
- Therapy preparation and transport/readiness coordination.
- Shift handover and escalation.
- Discharge checklist and take-home instruction acknowledgement.

**Key distinction:** Prescribed medicine ≠ pharmacy-issued medicine ≠ nurse-administered medicine. Each event has time, quantity where relevant, and staff identity.

## 14. Pharmacy and inventory

- Approved prescriptions automatically in pharmacist worklist.
- Actual dispensing including partial supply; remaining quantity pending.
- Batch, expiry, supplier, purchases, stock movement and sale price.
- Usable first-expiry-first-out batch preference and expired stock restriction.
- Low-stock/near-expiry alerts.
- Pack-to-unit conversions: strip/tablet, bottle/ml, pack/gram as configured.
- OPD sale, IPD issue, ward transfer, patient return, supplier return, damage and write-off.
- Controlled substitution requiring authorised clinical approval where appropriate.
- Therapy oils/consumables separately trackable by store/location/session.

**Example:** 30 tablets prescribed, 20 supplied, 10 pending. Actual dispensing and charges should match hospital’s approved issue/billing model. Return should reverse the relevant financial and stock movements with traceability.

Bahmni describes drug-order-generated draft billing and first-to-expire batch selection [S4]; this is a design benchmark, not a deployment commitment.

## 15. Accounts, billing and packages

### Charges

Consultations, room/bed/villa stay, rounds, nursing, therapy, medicines, consumables, investigations, meals, attendant services and authorised extras.

### Financial workflow

Estimate → deposit/advance → running charges → reviewed invoice → receipt/adjustment/refund → reconciliation. Cash, UPI, card, bank transfer and split payments recommended. Payer receivable and patient outstanding separately maintained.

### Packages

Configure nights, room category, therapies/sessions, doctor visits, medicines, meals, exclusions, extra stay, upgrades and cancellation/unused-service rules. Included service should not be charged again unless applicable approved conditions require it.

Purchased sessions ≠ scheduled sessions ≠ completed sessions. Billing recognition and cancellation policy finalise with accounts team.

### Controls

- Approved discounts and refunds with reason and role limits.
- No silent deletion of final invoices/payments.
- Cashier shift closing and payment reconciliation.
- Duplicate charge prevention and service-to-charge linking.
- Hospital/pharmacy billing entities, tax treatment and invoice formats configured with accountant review.
- Consolidated patient statement can coexist with legally/accounting-required separate invoices.

## 16. Insurance, government schemes and TPA

### 16.1 Core principle

**Confirmed:** Card/company, limit and AYUSH coverage capture karna hai, cashless/reimbursement support chahiye aur information last tak portals mein dikhni chahiye.

**External verification:** Card hona automatic free-treatment approval nahi hai. Coverage hospital empanelment/network eligibility, applicable policy/scheme, treatment eligibility, limits, referral and approvals par depend kar sakti hai. Official sources link cashless/AYUSH services to applicable terms and authorisation [S12–S16].

### 16.2 Payer categories

Self-pay; private health insurance; government health scheme; employer/corporate benefit; mixed funding where permitted and verified.

User examples: HDFC ERGO, Niva Bupa, SBI Life, CGHS, CAPF, CBSE and RGHS.

- HDFC ERGO/Niva Bupa: record exact health policy and TPA if applicable; no blanket coverage promise.
- SBI Life: exact product/card verify karein; name alone se hospital indemnity cover assume na karein. SBI General has health-insurance products [S17].
- CGHS/RGHS/Ayushman CAPF: scheme-specific beneficiary, entitlement and hospital eligibility rules configure hon.
- CBSE: exact card/employer benefit reference pending. Is name ko verified standalone health scheme label na dein.
- Additional payer names admin verified master se add kare.

### 16.3 Reception capture fields

| Group | Required capability |
|---|---|
| Identity | Insurer/scheme, policy/member/card ID, policyholder, beneficiary and relation |
| Validity | Policy period, applicable card validity and document date |
| Coverage | Total sum insured/entitlement, verified available balance if obtainable |
| AYUSH | Covered/not covered/pending, applicable limit, exclusions and supporting evidence |
| Entitlement | Room category/rent cap and relevant procedure/package conditions |
| Patient contribution | Applicable co-pay, deductible and non-covered items |
| Documents | Card front/back, policy schedule, referral, authorisation and other evidence |
| Verification | Patient-reported versus verified values, source, checked by, time and comments |

Unknown limit must stay unknown, not zero. Total policy cover, remaining benefit, AYUSH allowance, pre-auth amount and final approved claim are separate fields.

### 16.4 Payment modes

| Mode | Workflow |
|---|---|
| Cashless requested | Eligibility → estimate → pre-auth → query/approval → treatment → final claim → settlement |
| Reimbursement | Patient pays hospital → itemised claim documents supplied → patient claims from payer |
| Self-pay | Direct payment, with authorised future reclassification/adjustment if required |

Mode belongs to visit/admission/claim, not a permanent patient attribute. Multiple available policies/schemes can be recorded; actual funding coordination must be verified and double recovery prevented.

### 16.5 Insurance desk

Eligibility and empanelment review; pre-auth reference and submitted documents; payer queries and responses; revised estimates; enhancement requests for longer stay/treatment; discharge/final approval documents; submission tracking; deductions, rejection, resubmission and received payments.

**Separate status tracks:**

- Verification: not checked / pending / verified eligible / ineligible / needs clarification.
- Pre-authorisation: draft / submitted / query / approved / partially approved / rejected / expired or cancelled when applicable.
- Claim: draft / submitted / query / under review / partially settled / settled / rejected / closed.

Approval ≠ settlement. Approval remaining can be an estimate and should not be portrayed as guaranteed final reimbursement.

### 16.6 Visibility across portals

Common strip example: **Payer: Niva Bupa | Cashless requested | AYUSH verification pending | Pre-auth submitted**.

| Portal | Relevant visibility |
|---|---|
| Reception | Card, verification, missing documents, payment category and eligibility alerts |
| Doctor | Coverage summary, clinical evidence/document requests and approval status |
| Nursing/therapy | Authorised services/session limits and documentation tasks |
| Pharmacy | Relevant coverage restrictions and item billing classification |
| Accounts | Approved, submitted, deductions, patient share and received/outstanding amounts |
| Insurance desk | Full claim documents and workflow within permissions |
| Admin | Masters, agreements, empanelment validity and reports |

Clinical order and coverage decision remain separate; insurance rejection should not silently alter a doctor order. Urgent care/escalation policies must not be replaced by financial UI locks.

### 16.7 Rooms and tariffs

- Chosen room category compare with entitlement.
- Upgrade shows potential additional liability and records acceptance/approval.
- Scheme/package codes and negotiated tariffs effective-date ke saath save hon.
- Transfer/extra stay can generate insurance review or enhancement task.
- Total bill, claim submitted, approved amount, patient payable, payer received and outstanding separately visible.
- Unapproved amount automatically patient payable na ho; applicable agreement and review ke baad allocate karein.

### 16.8 Manual-first operation and integrations

MVP document upload, portal submission reference aur manual verified status tracking se operate kar sake. Live eligibility, balance checks, automatic pre-auth/claim submission sirf actually available and authorised payer integrations ke through enable hon. Software mein insurer name add karna integration ya hospital empanelment establish nahi karta.

## 17. Housekeeping, maintenance and dietary operations

**Recommended:** Cleaning queue, assigned staff, started/completed timestamps and supervisor-ready confirmation. Maintenance block with reason, expected resolution and authorised reopening. Bed/room cleaning state real operational granularity par record ho.

Diet/kitchen portal admitted patients ke doctor-approved meal instructions aur relevant restrictions display kare. Detailed dietetics, meal inventory and billing scope pending decision.

## 18. CRM, reminders and circadian-specific additions

### CRM

Inquiry → contacted → appointment → visited → follow-up stages; registered patient records se linked but distinct. Assigned callbacks, due follow-ups, missed therapy outreach, complaints and feedback. Marketing communication consent clinical-care records se separate manage karein.

### Hospital-specific optional module

Sleep/wake time, meals timing, shift-work history, sleep diary and doctor-approved daily routine plans. These support longitudinal clinical review; automatic diagnosis/treatment recommendations are not part of the defined scope.

### Patient access — later phase

Approved prescriptions, reports, receipts, upcoming appointments, therapy schedule and discharge instructions. Draft/internal records by default visible na hon.

## 19. Management dashboard

| Area | Recommended views |
|---|---|
| OPD | Registrations, consultations, queue and waiting time |
| IPD | Total/occupied/available beds, floor/category view, expected admission/discharge |
| Room operations | Cleaning, blocked resources, transfers and reservations |
| Therapy | Ordered/booked/completed/missed sessions and resource utilisation |
| Pharmacy | Pending issue, low stock, expiry and returns |
| Accounts | Billed, collected, advances, dues, refunds and cashier closing |
| Insurance | Pending verification/pre-auth, queries, submitted claims, deductions and receivable ageing |
| CRM | Due callbacks, follow-ups and complaints |

Revenue, collections, advance and receivables should not be presented as the same metric. Every dashboard count should have defined date/status filters and drill-down records.

## 20. Security, audit and reliability

**Recommended foundational requirements:**

- Individual logins and role-based access; sensitive permissions separately controlled.
- Encryption in transit, protected file storage and controlled exports/downloads.
- Audit for clinical approvals/amendments, patient merge, rate changes, admission/transfers, dispensing, financial adjustments and claim updates.
- Versioned signed/approved documents; staff identity and timestamps.
- Backups with actual restore testing and agreed recovery targets.
- Prevent concurrent double bed allocation or stock over-issue.
- Reliable retry/idempotency for payment, charge and notification processing.
- Graceful handling of internet/power interruptions; downtime/recovery procedure agreed.
- Data migration, retention, consent, hosting, access and deletion rules reviewed against applicable requirements before production.

ABHA/ABDM is a potential future integration. ABHA participation is voluntary according to the official reference [S19]; ABDM health data exchange requires consent and integration validation/security requirements [S18]. ABHA input field alone does not mean ABDM integration is complete.

No claim of legal, NABH, ABDM or insurance compliance is made by this document. Actual applicable requirements and integration scope need formal verification for production.

## 21. Suggested conceptual data model

This is a development planning recommendation, not final database design.

| Domain | Main entities |
|---|---|
| Identity | Patient, contact, related person, consent, document |
| Staff | User, role, permission, department, assignment |
| Encounters | Appointment, OPD encounter, IPD admission, queue/token |
| Clinical | Note, vital, diagnosis, prescription version, order, discharge summary |
| Therapy | Procedure master, course, session, resource booking, performance record |
| Accommodation | Building, floor, room category, room, bed, reservation, allocation, transfer |
| Nursing | Care task, observation, administration event, shift handover |
| Inventory | Product, unit conversion, batch, location, purchase, movement, issue/return |
| Finance | Tariff version, package, charge, invoice, receipt, deposit, credit/refund, allocation |
| Coverage | Payer, TPA, agreement, policy/beneficiary, verification, entitlement snapshot |
| Claims | Claim, authorisation, query, attachment, submitted line, deduction, settlement |
| Operations | Cleaning task, maintenance block, meal instruction, audit event |
| CRM | Inquiry, lead stage, callback, reminder, feedback/complaint |

Clinical, inventory and financial events reference each other through IDs; do not collapse them into one editable status field.

## 22. First operational version and phased roadmap

### Phase 1 — operational MVP

**Confirmed business scope:** OPD + IPD, central admin, staff roles, reception, doctor records, pharmacy, accounts, room/bed management, 100-bed dashboard and insurance/scheme capture with cashless/reimbursement tracking.

**Recommended minimum supporting scope:** Nursing, therapist and housekeeping workflows; approved structured orders; partial dispensing; deposits/running bills; manual insurance desk; rate versioning; audit history; backups and tested restoration.

Typed and uploaded prescriptions belong in Phase 1. **Voice entry is confirmed as a desired capability, but its release timing must be agreed** after doctor trials; a reliable Hindi/English draft-and-approve workflow is the proposed implementation.

### Phase 2

Patient portal, automated consent-based reminders, advanced CRM, extended package handling, detailed dashboards, diet/kitchen depth and optional sleep/routine diary. Voice can be delivered here if deferred by agreement.

### Phase 3 — integration and expansion

Verified lab/accounting/payment interfaces, authorised insurer/scheme integrations, ABDM/ABHA, multi-branch and advanced reporting where needed. No schedule or cost commitment is established yet.

## 23. Practical acceptance scenarios

These scenarios are future implementation acceptance criteria, not tests already executed.

1. Returning patient is found without creating duplicate UHID; fresh visit gets a new encounter ID.
2. Doctor medicine-only prescription creates pharmacy worklist and no therapy booking.
3. Therapy-only prescription creates scheduling task without mandatory medicine sale.
4. Both orders route correctly and preserve the originating approved prescription.
5. Voice/upload extraction stays draft until doctor checks and approves it.
6. Two staff attempting the same bed allocation cannot create overlapping active admissions.
7. In a two-bed room, one admission leaves one available bed visible.
8. One hundred active beds reconcile across mutually exclusive current states; future bookings do not inflate the total.
9. Private/villa exclusive booking prevents conflicting underlying-bed bookings.
10. Bed transfer preserves history and avoids overlapping rent for the same billing period.
11. Discharge approval does not mark bed ready until checkout and housekeeping completion.
12. Partial dispensing of 20 out of 30 tablets leaves 10 pending and traceable stock/charges.
13. Nursing administration is not assumed from pharmacy issue.
14. Package-included therapy does not create duplicate out-of-package charge.
15. Card uploaded with unverified cover shows verification pending, never automatic free treatment.
16. Total cover, AYUSH allowance, pre-auth and final claim approval remain separate.
17. Room upgrade triggers entitlement/liability review and acceptance record.
18. Claim approved but unpaid remains outstanding after patient discharge.
19. Rate change does not retrospectively rewrite final invoices.
20. Reception cannot alter approved clinical orders; pharmacy cannot approve its own clinical substitution unless authorised.
21. Every refund/amendment is attributable and preserves original history.
22. A backup restore recovers the agreed records/documents in a controlled recovery exercise.

## 24. Pending decisions before detailed development

1. Actual 100-bed distribution across wards, rooms and villas; physical room/bed numbering list.
2. Doctors, departments, daily OPD volume, therapist/therapy-room count and staff shifts.
3. Admission, clinical approval, deposit and discharge approval authority.
4. Payment before/after service rules and emergency/exception handling.
5. Room rent cycle, grace period, transfers, exclusive occupancy and attendant charges.
6. Package definitions, unused-session treatment, refunds and upgrade rules.
7. Hospital/pharmacy entities, tax configuration and accountant-approved documents.
8. Actual insurer/scheme empanelments, tariffs, beneficiary categories and covered Ayurveda services.
9. Exact meaning/product behind SBI Life and CBSE examples.
10. Voice accuracy expectations, languages, device/microphone setup and launch priority.
11. Mandatory clinical forms, procedure records and consent wording approved by medical leadership.
12. Hosting, internet/power backup, downtime process, recovery targets and retention policy.
13. Existing patient/inventory data migration and external integration priorities.
14. Technology stack, build/customise choice, deployment model, budget and timeline.

## 25. Primary-source reference register

Research reviewed in this conversation on 23 October 2026. Product pages can change. Sources below support benchmark descriptions and coverage distinctions; they do not prove this hospital’s eligibility, empanelment or final policy coverage.

| Ref | Source and link | Used for |
|---|---|---|
| S1 | [MocDoc — HMS features](https://mocdoc.com/india/hospital-management-system-delhi) | OPD, queue, prescription, pharmacy and billing benchmark |
| S2 | [Medinous — module listing](https://medinous.com/sitemap/) | Enterprise hospital module breadth |
| S3 | [Bahmni — feature list](https://www.bahmni.org/feature-list) | Registration, clinical, IPD, stock and billing |
| S4 | [Bahmni — billing and accounting](https://www.bahmni.org/billing-and-accounting) | Order-to-draft-bill and first-expiry batch example |
| S5 | [Eka Care — doctor practice management](https://www.eka.care/s/for-doctors) | Prescriptions, queues, records and reminders |
| S6 | [Eka — DocAssist](https://product.eka.care/s/for-doctors/docassist) | Voice and structured documentation benchmark |
| S7 | [AyuPlus — Ayurveda HMS](https://www.ayuplus.in/) | Ayurveda/Panchakarma forms and clinical modules |
| S8 | [AyuPlus — OPD/IPD](https://www.ayuplus.in/opd-ipd-management) | Linked OPD/IPD records, beds and discharge benchmark |
| S9 | [Ayush Manager — Ayurveda](https://ayushmanager.com/ayurvedic-clinic-hospital) | Therapy scheduling, diet, multilingual prescriptions and follow-up |
| S10 | [National Portal — A-HMIS](https://www.india.gov.in/category/science-it-communication/subcategory/research-development/details/website-of-ayush-hospital-management-information-system) | Government description of Ayush HMIS |
| S11 | [Ministry of Ayush — Ayush in India 2021](https://ayush.gov.in/resources/pdf/ayush_india/Ayush_in_India_2021.pdf) | A-HMIS and system-specific module background; historical publication |
| S12 | [IRDAI — health insurance FAQs](https://irdai.gov.in/faqs-on-health-insurance-regulations) | Cashless/pre-authorisation and policy conditions; check current applicable rules |
| S13 | [PIB — AYUSH insurance coverage](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2292389&lang=1&reg=48) | Specific coverage subject to policies and framework |
| S14 | [HDFC ERGO — AYUSH policy](https://www.hdfcergo.com/docs/default-source/default-document-library/aayush-policy.pdf) | AYUSH network/coverage framework; actual policy still requires verification |
| S15 | [RGHS — official portal](https://rghs.rajasthan.gov.in/RGHS/home/home) | Empanelment-based services and scheme information |
| S16 | [NHA — Ayushman CAPF FAQs](https://nha.gov.in/img/resources/AB-CAPF%20FAQs_Beneficiary_CO_v11_26062024.pdf) | Beneficiary/card and empanelled-hospital context |
| S17 | [SBI General — health insurance](https://www.sbigeneral.in/health-insurance) | Health-insurance product reference; exact user card remains unverified |
| S18 | [PIB — ABDM consent/security](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2152537&lang=2&reg=48) | Consent, sandbox validation and security audits |
| S19 | [ORS — ABHA information](https://ors.gov.in/healthid) | Voluntary participation and consent-based sharing |

### Evidence boundary

Detailed scheme tariffs, government authorisation rules, tax rates, retention periods and legal compliance are intentionally not asserted here without hospital-specific verification. This document records a software requirements baseline and the research supporting it.

## 26. Next deliverables after scope discussion

Recommended sequence: confirm pending business rules → screen/workflow map → role-permission matrix → database/API design → prioritised development backlog → prototype → staff validation → implementation and acceptance testing.

This file consolidates the discussion through the insurance/government-scheme addition. Future changes should update this baseline with a version/date and an explicit change log.

---

**Change log:** v1.0 — consolidated OPD, IPD, admin, Ayurveda, room/bed capacity, pharmacy, accounts, insurance/schemes, research sources and open decisions.
