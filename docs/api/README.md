# HMS API and bounded master configuration

[openapi-v1.yaml](openapi-v1.yaml) is OpenAPI 3.0.3 expressed using the JSON subset of YAML 1.2. This keeps the local page-action checker dependency-free; standard OpenAPI tooling can read the file. [page-actions-v1.json](page-actions-v1.json) maps each of the36bounded operations(27verified staff/foundation plus9checkpointed identity-security WIP operations) to the relevant [plan page](../../plan.md). SYSTEM denotes the health probe rather than a staff page. API contract existence does not establish implementation, test coverage or deployment; those are recorded in [HMS.md](../../HMS.md) and the [ledger](../implementation/ledger.md).

The frontend currently combines page subsets into Overview, Patients, Appointments, Bed board and Master administration tabs. A mapped API action is not automatically a claim that its UI control exists. Future catalogue fields such as patient clinical history, payer summaries, reservations and discharge are outside Phase A.

## Authentication, permissions and network policy

The browser first calls `GET /api/v1/auth/csrf/`, then sends the `csrftoken` cookie value in `X-CSRFToken` on login and every mutation. Login rotates the CSRF token; clients read the updated cookie for later writes. Django uses an HttpOnly session cookie, with no JWT or password stored in localStorage. Anonymous/private access may return 401 or 403 depending on the session-authentication failure. IP policy applies to auth/CSRF paths too; only the minimal health probe is exempt. The health response is process health, not database readiness.

Organisation/branch context derives from authenticated assignments. Query/body branch IDs never grant access. Phase A reception can read and write patients/appointments/admissions; doctors and nurses have scoped read access. Master admin has nonclinical inventory/resource configuration, with the new staff-management source contract below; operational/clinical roles remain explicit. Pharmacist/accounts/therapist capabilities remain unavailable. A user may have multiple assignments with different branches; the backend evaluates permission at the requested branch even when the UI shows a role union.

## Staff access extension — verified source, deployment separate

Four operations list/create staff, version-edit organisation assignments/suspension and page staff branch options. Separate platform.staff.manage is checked against current active master grants in the explicit organisation; staff-only client scopes do not gain resource writes. Password is create-only/write-only/validated, never returned/audited. Membership.is_active governs every operational scope/replay; global account_active remains readonly and independent. Suspending hospital access does not globally disable another organisation's identity. Legacy revision0projects without GET mutation; new staff revision1. Self edits denied, stale409 and malformed400. Org lock plus post-lock permission recheck prevents mutually suspended administrators from using stale grants. See [staff design/test contract](../implementation/staff-access-contract.md); MFA/deployment remain separate. CurrentUser includes additive branch_permissions derived from active branch roles; operational UI uses selected-branch grants, legacy responses fall back to union. Staff snapshots use a bounded revision consistency retry; resource writes and locked operational/replay paths recheck current scope after waits. Actual source213PostgreSQL tests/25subtests and49frontend tests passed; see ledger for review/evidence.

Errors use `{code,message,field_errors?,request_id?}`. A missing or out-of-scope patient/appointment/object returns a concealed 404 where applicable; an explicitly unauthorised selected branch returns 403. Field errors must not disclose foreign records. Limits are default25/max100, nonnegative offset, and search is bounded to200characters. Current local requests are same-origin through Vite; no wildcard CORS, automatic visitor whitelisting or trusted forwarded-header shortcut is configured.

## State and retry boundaries

Appointment PATCH requires `expected_version`. Supported transitions are scheduled→scheduled/checked_in/cancelled/no_show, checked_in→checked_in/completed/cancelled, no_show→no_show/scheduled, and terminal completed→completed or cancelled→cancelled. Completed/cancelled records cannot be rescheduled or otherwise edited. A successful PATCH increments version; stale retries return409. Check-in creates at most one encounter, even when repeated with the current version. This provides no clinical approval.

Admission allocation requires an available bed and patient at the same permitted branch. Transactions and unique active-allocation constraints protect allocation; a conflicting unkeyed retry returns409. Actual PostgreSQL same-bed and same-key race tests passed for the source slice. Demographic PATCH has no optimistic version yet and uses last authorised write. Shared phone numbers are deliberately allowed.

Source reliability extension (not present in the initial47b3618deployed preview): optional UUID `Idempotency-Key` header on the three create operations. Keys are scoped to user+operation; key/fingerprint/result UUID and domain/audit write commit together. Same payload/key returns201 and the same currently authorised entity projection without another write; different payload409. Current permissions, result visibility and strict body validation apply on every replay. Validation/domain failures do not consume the key. No request/response PII is stored in the retry ledger; retention has no expiry yet. Missing header preserves legacy behaviour and duplicate risk. Browser create forms retain their logical key on a failed/ambiguous save; do not silently rotate a key to bypass conflict. Staff must search/verify a previous result before starting a fresh logical request after conflict.

`GET beds/?status=available` and the other exact documented bed statuses filter before count/pagination within permitted branches; unknown status400. Validation field errors are arrays of plain messages, including nested errors. Nonobject JSON mutation/login bodies and unsupported keyed file payloads return structured400 rather than500. No upload capability is introduced.

Operational bed availability changes through initial admission allocation. The new source configuration contract below adds only master-controlled nonoccupied readiness/configuration, not clinical/financial discharge or housekeeping task completion. Exclusive-room/villa reservations, transfers and discharge remain deferred. Therapy counts return `null`, never fabricated zero. No patient-record DELETE operation exists. Clinical signing/final bills and corrections belong to later reviewed contracts.

## Master configuration extension — verified source, deployment separate

Five additional operations under `/platform/organisations/{organisation_id}/` list/create branches and beds and version-edit bed configuration. They require separate platform.configure from a master membership in that organisation; no patient/clinical permission follows. Scope is checked before guessed org/branch/bed IDs are returned. List results remain bounded/paged; UI currently operates within the existing summary organisation.

Creates reject duplicate case-insensitive code/bed numbers with409 and do not claim generic idempotency-key semantics. Bed edits require expected_version and permit only available/cleaning/blocked states, never edits to occupied/reserved or active-admission beds. Bed.version increments on allocation/configuration; transactional allowlisted nonclinical audit snapshots protect traceability. Actual PostgreSQL166tests/25subtests passed, including a deterministic FK-deadlock regression observed RED then GREEN with branch FOR NO KEY UPDATE. Read [the configuration contract](../implementation/resource-administration-contract.md) and ledger for scope/evidence. Existing initial47b3618preview has not received this source/migration. No delete/manual occupancy/clinical-signing path is added.

## Identity security extension — checkpointed WIP, release blocked

Nine self-only security operations plus login202/anonymous CSRF logout are frozen in [identity-security contract](../implementation/identity-security-contract.md). Authenticator secrets use dedicated encrypted row-bound state, recovery codes hash-only, shared DB attempt/replay/epoch checks, stable-user locking and fresh proof for sensitive changes. Production privileged writes require enrolled/fresh MFA as well as ordinary action permissions; setup remains reachable. Source implementation is present but WIP:236actualPG/25subtests and64frontend-agent checks passed; proof-age recheck after org-lock wait, negative/race coverage and final review remain. Do not deploy as verified identity protection. TOTP is not phishing resistant; human recovery/key provisioning/read audit remain release gates. No outbound QR service or persisted browser secret.

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


Checkpoint coordinator repeat: frontend63passed/1failed (resource-administration stale-bed-edit test could not find Edit bed101 within timed wait); agent earlier64passed. Coordinator typecheck/build still passed. Affected test isolated rerun is recorded in ledger/handoff; this does not establish a repaired full suite. No source changes after stop. Investigate/repeat full suite after cooldown before marking identity delivered.
