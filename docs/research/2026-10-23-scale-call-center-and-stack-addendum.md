# HMS scale, call-center integration and stack recommendation addendum

Date: 23 October 2026, Asia/Calcutta. Status: research recommendation, not an approved implementation design.

## New owner inputs

- Plan for 555+ OPD visits per day and 30+ inpatient admissions per day.
- Plan for 1,000,000+ enquiries **per month**, clarified directly by the owner.
- Future call-center management integration: agents should see outcomes of patients they refer, including relevant sales information, to support follow-up.
- Future hospital branches.

These are planning inputs; actual observed traffic, agent count, peak concurrency, branch schedule and retention remain unknown. Enquiry currently means an incoming business enquiry; whether repeat calls/messages are included has not been defined. Clinical scope question from the previous research discussion also remains open.

## Capacity interpretation

At a 30-day reference month, 1,000,000 enquiries is approximately 33,333/day and 12 million/year at the stated floor. Spread evenly across 24 hours it is about 0.39 new enquiries/second; concentrated into ten working hours it is about 0.93/second. Neither calculation represents peak requests, concurrent agents, integration retries, activity updates, historical searches or reporting load.

555 daily OPD encounters would be about 202,575/year if that minimum were sustained every day. Encounters are not unique patients. Thirty daily admissions would be 10,950/year on the same simplifying assumption. These figures are arithmetic illustrations, not forecasts.

Enquiry records can each generate many calls, messages, tasks, assignments and audit events. Capacity tests must model those activities and simultaneous staff usage, rather than benchmark empty tables or one insert per enquiry.

### Bed-capacity implication

For a stable single facility with 100 usable beds and 30 inpatient admissions/day, the census relation occupied beds approximately equals admissions/day multiplied by average length of stay implies about 3.33 days at 100% occupancy, or 2.83 days at 85% occupancy. These are capacity illustrations, not clinical targets. Longer Ayurveda stays, blocked beds, exclusive villas or higher admission volume reduce feasibility at the stated capacity. Confirm whether admissions refer to overnight inpatient stays, day care, or future network-wide volume, and measure actual length of stay.

## Stack recommendation

**Retain Python + Django + Django REST Framework for the core, React + TypeScript + Vite for staff interfaces, and PostgreSQL for authoritative transactional records.** The increased volumes alone do not establish a need to change backend language. Suitability must be validated through a realistic prototype/load test and maintenance-team capability.

Django exposes transaction management needed to compose critical updates; constraints, concurrency policy, access controls and retries still require deliberate application design. [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)

Supporting candidates: Celery workers for background processing, a durable broker selected during design, Redis for disposable caching/rate limits where justified, and private object storage for attachments or permitted recordings. Celery supports Django integration. [Celery documentation](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)

NestJS + TypeScript remains a valid alternative if the long-term maintenance team is substantially stronger in TypeScript or an existing call-center platform can reuse its framework. Integration can use HTTP APIs and events across different languages, so matching the call-center language is not mandatory. No evidence currently requires Java/Go services or a full microservice architecture.

## Architecture direction under consideration

1. A core HMS with explicit module boundaries for patient identity, encounters, clinical care, accommodation, therapy, pharmacy, finance and payer workflows.
2. A bounded CRM/integration component with its own worker capacity and database connection budget. It can start as a logical module and become independently deployable if measured workload or the existing CRM justifies it.
3. An authoritative source for each entity and a documented API/event contract; external CRM must not directly write clinical or financial tables.
4. Durable event handoff using an outbox or equivalent: business change and event entry commit together, then workers deliver with retries and deduplication. Delivery is not assumed exactly once.
5. Separate reporting paths when needed, so agent dashboards and bulk campaign exports do not exhaust bedside transaction capacity.

Do not deploy one microservice per department by default. Equally, avoid placing unrestricted lead imports and heavy call-center reporting in the same request/worker pool as clinical care.

## Call-center-to-hospital journey

Enquiry -> identified person/contact -> assigned agent -> appointment/referral -> arrival/check-in -> consultation -> therapy/admission -> invoicing -> collection/refund -> follow-up.

Suggested domain records: enquiry, contact/person, lead, campaign/source, assignment history, referral/attribution, appointment, patient linkage, branch, encounter and permitted outcome/sales projection. Preserve raw enquiry activity separately from the deduplicated lead/person.

### Identity and attribution

- A lead is not automatically a patient; create/link hospital identity at an appropriate verified stage.
- A phone number is searchable but not a unique person key; families may share phones.
- Use organisation-wide patient identity with branch-local encounter/registration identifiers where needed. Shared identity does not imply unrestricted cross-branch clinical access.
- Store origin agent, current responsible agent, campaign, referring branch and attribution rule separately.
- Assignment changes must not rewrite historical attribution. Define reactivation, multiple agents, repeat visits, cross-branch visits and attribution windows.
- Agent performance or commission rules are not yet confirmed; preserve enough event history to support later approved rules.

### What an agent should see

Recommended default: assigned leads, appointments, arrival/visit outcome, follow-up due, relevant service category, and specifically authorised billing/collection summaries. Decide whether refund, payer settlement and branch data affect the agent's view.

Detailed diagnoses, prescriptions, sensitive notes, attachments and complete insurance documents require independent permission decisions. The owner's request for records/sales visibility does not define unrestricted access. Financial analytics should distinguish invoiced amount, collected amount, refunds and payer outstanding.

### Integration reliability

- Stable internal and external IDs, source event ID, version and timestamps.
- Authenticated webhook/API requests and narrowly scoped integration credentials.
- Idempotent ingestion; a repeated delivery must not duplicate a lead or appointment.
- Ordering/version checks so an older callback cannot overwrite a newer status.
- Retry limits, failed-event review, replay and scheduled reconciliation.
- Explicit freshness timestamp on agent projections; transient sync failure must not block hospital care.
- Migration/export compatibility with the actual call-center product. Its name, stack and API capabilities remain unknown.

## PostgreSQL design and operations

- Use organisation and branch scope consistently across operational records and permissions. Globally shared masters and patient identities need explicit ownership rules.
- Branch-aware foreign keys/constraints prevent cross-branch resource references. Apply least-privilege access and consider row-level security as defence in depth; table owners and privileged roles can bypass it unless appropriately constrained. [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- Index real query patterns: assigned agent/status/follow-up time, branch/encounter date, external event IDs and normalised contact search. Avoid returning or loading millions of records into a screen.
- Use transactions, constraints and row/resource locking for beds, stock, package consumption and receipt allocation. UI checks alone cannot enforce correctness.
- Maintain connection pooling/limits and reserved resource capacity for critical care operations.
- Consider time partitions for very large append-heavy activity/audit tables after query and retention analysis. Partitioning has trade-offs and is not automatically necessary for every table. [PostgreSQL partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- Consider a read replica or separate reporting store for eligible reporting workloads. Replication lag means critical current bed/stock/payment decisions should read authoritative state. [PostgreSQL availability and replication](https://www.postgresql.org/docs/current/high-availability.html)
- Plan high availability to the agreed outage target and backups with point-in-time recovery. Replication is not a substitute for backup, and private files also need recovery. [PostgreSQL PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- Add a dedicated search system only if indexed database search fails measured requirements. Avoid premature sharding.

Clinical records, financial records, lead activity and call recordings need separately reviewed retention/access policies. Cache is not the source of truth. Store attachment/recording bytes in private storage rather than defaulting to database blobs; retain protected references and metadata.

## Validation required before sizing or commitments

Record concurrent agents and clinical staff, operating hours, campaign bursts/import sizes, enquiries versus repeat interactions, calls/tasks per lead, branch count/timeline, document/audio sizes, retention, report types and response-time requirements.

Run tests for concurrent bed allocation, stock issue and payment retries while enquiry ingestion, follow-up searches and reporting run concurrently. Test real table cardinality and realistic skew, integration outage/replay, branch access isolation, backup restore and failover. Measure latency distributions, throughput, errors, queue lag and connection saturation.

No server size, cost, capacity guarantee, retention duration, branch count or final infrastructure topology is approved by this addendum. Language recommendation remains Django/Python, with resource isolation and integration reliability becoming explicit architectural requirements.
