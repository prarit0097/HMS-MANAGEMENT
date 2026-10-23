# Phase A: authenticated API-first hospital workspace

Owner authorised implementation with a five-agent team on 23 October 2026. This narrows the first runnable slice without discarding the remaining plan. Work on `feat/hms-foundation` in the current shared checkout; only the coordinator commits/pushes. No worktree consent is inferred; a feature branch isolates this previously documentation-only checkout.

## Team and ownership

1. Backend engineer: `backend/` except `backend/apps/security/` and `backend/tests/test_security_contract.py`; auth, scoped branches/patients/appointments/beds/admissions/dashboard, migrations, synthetic seed and backend tests.
2. Frontend engineer: `frontend/` only; simple polished API-backed login/dashboard/patients/appointments/beds/master-admin views, no hard-coded clinical records or authoritative business state.
3. Security engineer: `backend/apps/security/`, security contract tests and threat notes only; IP policy and negative access review. Coordinate integration with backend engineer.
4. Platform/dataops/MCP engineer (next batch): compose/cloud-ready local packaging, API contract validation, scoped dataops/MCP groundwork; no paid deployment or claims of completed production OAuth/backups.
5. Independent reviewer (next batch): read-only integration/spec/security review and evidence. Coordinator fixes/integrates and owns documentation, Git, usage checks and scheduling.

Five specialist assignments, maximum three child agents active concurrently. All agents read HMS.md, plan.md and AGENTS.md. No child commits/pushes or modifies shared root documentation; report exact files, red/green evidence and remaining work. At a coordinator stop request, checkpoint and stop safely.

## API contract frozen for the first slice

Base `/api/v1/`; frontend Vite proxy `/api` to `http://127.0.0.1:8000`. Django session authentication, CSRF enforced, no JWT in localStorage. Browser begins with GET `auth/csrf/`, uses CSRF cookie in `X-CSRFToken` on mutations. Error shape `{code,message,field_errors?,request_id?}`. Lists `{results: [...], count: number}` with default25/max100 and optional limit/offset. UUID IDs except Django user IDs. Dates ISO8601; money decimal strings. User-selected branch never grants access.

- `GET health/` -> `{status:'ok'}` without private details.
- `GET auth/csrf/` -> CSRF cookie + `{detail:'CSRF cookie set'}`.
- `POST auth/login/` `{username,password}` -> current-user object; invalid generic401, throttle repeated attempts.
- `GET auth/me/` -> `{id,username,name,roles:[...],branches:[{id,name,code}],permissions:[...]}`; unauthenticated401/403 safely.
- `POST auth/logout/` ->204; CSRF enforced.
- `GET branches/` -> only user's assigned branches; platform master can manage explicitly assigned organisation scope.
- `GET dashboard/?branch=<uuid>` -> `{patients_total,opd_today,active_admissions,available_beds,appointments_today,therapy_pending: number|null}`; null signals not implemented, not fabricated.
- `GET/POST patients/` with optional `q`, `branch`; body `{full_name,phone?,date_of_birth?,age?,gender?,city?,branch}`. Result `{id,uhid,full_name,phone,date_of_birth,age,gender,city,created_at,branch}`. Duplicate phones allowed. Patient identities organisation-scoped; write requires assigned branch and relevant role.
- `GET patients/<uuid>/` and PATCH permitted demographics only; cross-organisation IDs concealed. No arbitrary clinical records yet.
- `GET/POST appointments/` with branch/date/q; body `{patient,branch,doctor_name,scheduled_at,reason?}`. Result includes patient UUID + `patient_name`, doctor_name, scheduled_at, status, reason, branch and version.
- `PATCH appointments/<uuid>/` allows supported reschedule/status changes with expected_version. Allowed initial states scheduled/checked_in/completed/cancelled/no_show. Check-in creates at most one encounter; no clinical approval implied.
- `GET beds/?branch=<uuid>` -> `{id,number,room_number,category,status,patient_name|null,admission_id|null,branch}` records. Categories general/semi_private/private/private_luxury/villa. Status available/occupied/reserved/cleaning/blocked; unimplemented exclusivity must be explicitly documented and not called complete.
- `POST admissions/` `{patient,bed,treating_doctor,reason?}` -> admission; transaction prevents second active allocation, validates branch and role, initial version1.
- `GET admissions/?branch=<uuid>` -> scoped admission summary list.
- `GET platform/summary/` -> master-only nonclinical organisation/staff/configuration inventory; no blanket patient-chart disclosure.

Frontend must represent unsupported mutations as unavailable rather than fake local success. Existing backend business services own all validation. Initial roles master_admin/reception/doctor/pharmacist/accounts/nurse/therapist; explicit grants and branch assignment. No default credentials committed. `seed_demo --username ...` reads a password from environment, creates synthetic records only and is restricted to local/dev mode. Display development environment in local UI.

## Security preflight and assertions

No anonymous patient/bed/staff data; login errors generic; CSRF negative tests; branch/organisation isolation; role write restrictions; validated bounded list/search; no cross-branch patient/bed linkage; no hidden Django admin mutation path; no production debug/secret/SQLite fallbacks. SQLite permitted for local fast tests only, production PostgreSQL mandatory and concurrent correctness remains unverified until tested against PostgreSQL. Financial/clinical/MFA/OAuth/backup capabilities not built in this slice must be honestly disabled.

Security module contract: `normalise_client_ip(remote_addr: str, forwarded_for: str|None, trusted_proxies: tuple[str,...]) -> str`; only trust explicitly configured proxy networks and strip from right, reject malformed chains. `evaluate_ip(address: str, allowlist: list[str], blocklist: list[str], allowlist_only: bool) -> bool`; deny precedence; mapped IPv6 canonicalisation; empty allowlist denies in allowlist-only. Integration environment rules apply on every protected API request, no self-whitelisting endpoint yet.

Tests before code: API permission/CSRF/duplicate-phone/check-in/allocation tests; frontend API-error/keyboard/form tests; pure IPv4/IPv6/proxy-policy tests. OpenAPI source mirrors frozen operations before UI code. Unreviewed whole-app release gate stays separate from owner authorisation to implement this bounded slice.

## Preflight interface review

| Tasks/interface | Finding and ruling |
|---|---|
| 01->02->04 | Freeze session, context and list/error shapes here; avoid two incompatible auth schemes |
| 03->02/04 | Security agent owns pure resolver/evaluator; backend integrates middleware without duplicate implementation |
| 04->05/12 | Phase A has no approved clinical orders; later clinical/coverage contracts remain planned, not faked |
| 04->07 | Validate same organisation/branch and transactionally protect initial bed allocation |
| 13–15 | High-impact dataops/MCP production features require later gated slices; no unauthenticated placeholder claiming success |
| 16->future CRM | External IDs/events foundation only; actual call-center build remains deferred |
| 17 | Local running preview is not cloud production, security certification or capacity proof |

Ruling: owner request to start is implementation authorisation; existing detailed page catalogue governs future slices. No new premises/call-center questions. Work on a feature branch with safe pushes; production rollout remains separate.
