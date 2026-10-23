# Phase A API contract

[openapi-v1.yaml](openapi-v1.yaml) is OpenAPI 3.0.3 expressed using the JSON subset of YAML 1.2. This keeps the local page-action checker dependency-free; standard OpenAPI tooling can read the file. [page-actions-v1.json](page-actions-v1.json) maps each of the 18 bounded operations to the relevant [plan page](../../plan.md). SYSTEM denotes the health probe rather than a staff page. API contract existence does not establish implementation, test coverage or deployment; those are recorded in [HMS.md](../../HMS.md) and the [ledger](../implementation/ledger.md).

The frontend currently combines page subsets into Overview, Patients, Appointments, Bed board and Master administration tabs. A mapped API action is not automatically a claim that its UI control exists. Future catalogue fields such as patient clinical history, payer summaries, reservations and discharge are outside Phase A.

## Authentication, permissions and network policy

The browser first calls `GET /api/v1/auth/csrf/`, then sends the `csrftoken` cookie value in `X-CSRFToken` on login and every mutation. Login rotates the CSRF token; clients read the updated cookie for later writes. Django uses an HttpOnly session cookie, with no JWT or password stored in localStorage. Anonymous/private access may return 401 or 403 depending on the session-authentication failure. IP policy applies to auth/CSRF paths too; only the minimal health probe is exempt. The health response is process health, not database readiness.

Organisation/branch context derives from authenticated assignments. Query/body branch IDs never grant access. Phase A reception can read and write patients/appointments/admissions; doctors and nurses have scoped read access. Master admin has nonclinical platform inventory only unless separately assigned an operational role. Pharmacist/accounts/therapist capabilities remain unavailable. A user may have multiple assignments with different branches; the backend evaluates permission at the requested branch even when the UI shows a role union.

Errors use `{code,message,field_errors?,request_id?}`. A missing or out-of-scope patient/appointment/object returns a concealed 404 where applicable; an explicitly unauthorised selected branch returns 403. Field errors must not disclose foreign records. Limits are default25/max100, nonnegative offset, and search is bounded to200characters. Current local requests are same-origin through Vite; no wildcard CORS, automatic visitor whitelisting or trusted forwarded-header shortcut is configured.

## State and retry boundaries

Appointment PATCH requires `expected_version`. Supported transitions are scheduled→scheduled/checked_in/cancelled/no_show, checked_in→checked_in/completed/cancelled, no_show→no_show/scheduled, and terminal completed→completed or cancelled→cancelled. Completed/cancelled records cannot be rescheduled or otherwise edited. A successful PATCH increments version; stale retries return409. Check-in creates at most one encounter, even when repeated with the current version. This provides no clinical approval.

Admission allocation requires an available bed and patient at the same permitted branch. Transactions and unique active-allocation constraints are the intended integrity boundary; a conflicting retry returns409. PostgreSQL race-test execution is required before claiming locking correctness. Demographic PATCH has no optimistic version yet and uses last authorised write. Generic creation idempotency keys are not implemented: patient/appointment registration retries may create duplicates. Shared phone numbers are deliberately allowed.

Bed availability is read-only except initial admission allocation. Exclusive-room/villa reservations, transfers, discharge and cleaning actions remain deferred. Therapy counts return `null`, never fabricated zero. No patient-record DELETE operation exists. Clinical signing/final bills and corrections belong to later reviewed contracts.

## Validation and compatibility

From the repository root, after installing [check dependencies](../../infra/requirements-checks.txt):

```powershell
python -m openapi_spec_validator docs/api/openapi-v1.yaml
python scripts/check_project_docs.py --links-only --api-contract
python -m unittest discover -s scripts/tests -v
```

The validator checks OpenAPI schema validity; the documentation checker checks operation IDs, full mapping and permission agreement. Neither alone proves runtime parity. Backend API/security tests and frontend client tests remain separate CI gates. Breaking request/response/permission changes require review, synchronized client/type changes, updated page-action mapping and an explicit compatibility/migration decision before release. Add a new API version when an existing released client cannot remain compatible; do not silently redefine a released operation.

## Future MCP and data operations boundary

There is no remote MCP listener, OAuth client registration, AI tool transport, backup/restore/import/export endpoint or privileged data job enabled by this package. A future adapter may call the same authorised business services in-process, under the user's scope and permitted network path. It must not invent an SQL/shell/URL tool or acquire greater permissions than the API. OAuth audience validation, revocation, high-impact confirmation, dependency manifests, encrypted backup storage and isolated restore drills require later designs and verification. Container volumes are local development persistence, not a backup system.
