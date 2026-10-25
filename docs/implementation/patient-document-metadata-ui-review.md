# Patient document metadata — UI and readiness review

25 October 2026. **DESIGN REVIEW ONLY; coordinator reconciliation/freeze required.** This review owns no application code, role grant, runtime setting, deployment or acceptance result. It narrows the UI/readiness recommendation in [metadata draft](patient-document-metadata-contract.md), read with [foundation](patient-document-foundation-contract.md), [full UI proposal](patient-documents-ui-plan.md), [HMS](../../HMS.md), [plan](../../plan.md) and [ledger](ledger.md). Other transaction, limiter, quota and security freeze gates remain coordinator responsibilities.

## Decision and staff value

Recommend the next bounded source slice remain **API-only with no Documents entry, count, placeholder, SHA256 form or document request in the staff frontend**. R04 remains incomplete. This is an engineering sequencing decision within the authorised scope; it needs no new owner policy decision.

The useful reception task is: find the right patient, confirm identity, attach a registration file, and understand whether it has been received and is available. The dormant foundation and four proposed metadata operations cannot complete that task. They record declarations only; pending requests expire after 30 minutes and have no byte-admission path. Inspecting or withdrawing synthetic declarations has test value, but no demonstrated routine staff benefit. A metadata-only screen would add another patient subview and imply an attachment workflow that cannot finish. Do not create production records merely to populate a demonstration screen.

Alternatives considered: (1) expose a declaration form, which adds a technical SHA256 task and false attachment expectations; (2) expose read/withdraw only, which offers little value before any working source of received files; (3) independently test metadata APIs while deferring the entire staff-facing entry. Choose (3). Cost: no visible R04 document progress in this slice, followed by a separate ingestion/UI contract and verification slice. API availability and visible staff features need not advance together.

## Actual source observations

- `frontend/src/App.tsx` uses workspace hashes, a current branch selector and a branch-keyed operational page remount. Navigation uses the global permission union; operational children normally receive `branch_permissions[branch]`. There is also a legacy fallback to the global union when `branch_permissions` is absent. That fallback must **never** authorise future document controls: missing exact-branch grants means no document entry/actions.
- `frontend/src/pages.tsx` Patients is a paged search table; View opens one Patient details `Modal`, and demographic correction replaces its body. PatientDetail currently receives only id/editable/onSaved. It has no document client, feature-discovery input or branch label. Reusing this body later requires explicitly threading the authorised named branch and exact scope, not inventing them from a patient UUID.
- `frontend/src/types.ts` User has optional branch permission mapping; Patient contains branch UUID, name/UHID/DOB/age/phone. No document type or capability is implemented. `backend/apps/core/authorization.py` CurrentUser returns active membership branch arrays and their global union. Reception has patient read/write; doctor/nurse patient read; master administration has platform grants. No current document grants exist.
- The broad UI proposal includes PDF, clinical-reference categories, doctor downloads and byte PUT; none belongs to this registration JPEG/PNG metadata slice. Its original offset/count pagination is also superseded here by the metadata draft's keyset cursor. Treat those examples as future proposals, never current acceptance requirements or available categories.

## Readiness, activation and discovery contract

Use the draft's deployment-owned strict boolean `HMS_DOCUMENT_METADATA_ENABLED`, default false, solely for the **four metadata routes/services**. Invalid or missing dependency configuration must fail closed. Environment activation is an operator configuration decision under a reviewed rollout; there is no staff toggle, visitor flag, bootstrap auto-enable, additional discovery endpoint or CurrentUser shape expansion in this slice.

| Condition | Exact effect to freeze |
|---|---|
| Action/session authority absent | Existing normal denial before patient/document disclosure; activation must not grant access |
| Action/session authority valid, metadata disabled | Generic503 `document_metadata_unavailable` before patient/document lookup, capability projection or writes; no filename/count/cursor |
| Metadata enabled in reviewed synthetic acceptance runtime | Four operations may accept declarations without storage/scanner. They still accept no bytes and expose no content route |
| Metadata DB/audit/authority/network dependency unavailable | Fail503 without metadata or success capability disclosure; never permissive fallback |
| CurrentUser contains proposed document grants | Describes authority ceiling only. Does not mean metadata runtime enabled, upload possible, file received or a UI entry available |
| Successful metadata list/detail/command | Existing response is sufficient discovery for an explicit authorised API client: current metadata capabilities plus `can_upload=false`, `can_download=false`, `upload_categories=[]` |
| Staff frontend in this source slice | No document fetch on bootstrap, patient list, Patient details, branch changes or hidden components; no document entry even if grants appear |

`can_create_intent` means declaration authority under the current enabled metadata policy, not an upload affordance. `allowed_media_types` and size limits describe accepted declarations; do not use them to display a file chooser or accepted-upload formats. Do not add speculative clinical categories, PDF, worker/readiness states or content URLs to ease future UI implementation.

The draft's proposed subsequent metadata UI says entry requires enabled discovery through a successful list while also forbidding eager metadata fetch. This is circular: the user needs an entry before the first list. Remove that subsequent metadata-only UI from the next frozen delivery scope. For this API-only slice no UI discovery problem remains. A future ingestion/UI freeze must choose a truthful entry policy and readiness contract together; do not add a fifth endpoint now to solve a deferred screen.

## Permission ceiling and API/page-action parity

Static proposed additions may give only active reception membership `documents.registration.read/write`; they must not alter other role grants or add custom grant administration. Every decision is evaluated in the addressed patient's exact current branch. Global union or membership in another branch is insufficient. Master plus doctor without reception is still denied document access; reception-B plus doctor-A cannot access registration documents-A. Master plus reception-A may qualify through reception-A, without clinical signing rights.

| Operation | Required exact-branch conjunction | R04 mapping at this slice |
|---|---|---|
| `listPatientDocumentIntents` | `patients.read` and `documents.registration.read` | Planned later entry/refresh; independently API-tested now, no frontend caller |
| `getPatientDocumentIntent` | Same read conjunction | Planned later details/status refresh; independently API-tested now |
| `createPatientDocumentIntent` | Read conjunction plus `patients.write` and `documents.registration.write` | Planned internal first step of later working file selection/upload; no staff declaration form |
| `withdrawPatientDocumentIntent` | Write conjunction; first transition additionally creator, pending, matching version and before expiry | Planned later withdraw confirmation; independently API-tested now |

No upload/download/page capability exists merely because these four operations are catalogued. Register exactly their draft paths under `/api/v1/patients/{patient_id}/documents/`; no frontend-only mutation, new readiness route, metadata audit browser or content endpoint. Record the page-action map as deferred R04 consumers, not four implemented UI actions. Replays reauthorise current branch/session/network scope; a previously known UUID or stored command key is not authority.

Metadata includes sensitive filenames even without bytes. Preserve concealed404 for missing/foreign/mismatched patient/document, safe error messages, committed disclosure accounting, no-store and no conditional304. No hidden category counts, generic admin-history document union, creator identity, reason, digest or patient demographics are added to projections. Retain separately authorised patient identity in a future UI rather than copying it into document API responses.

## Later R04 gate, not this slice's completion criterion

Before introducing a staff entry, freeze the complete useful registration-file journey including byte admission, private storage/encryption, structural validation, scanner/key/worker failure, exact accepted/available state semantics, expiry and retention, current authorisation and explicit delivery. No upload/storage/scanner/ready/download capability is claimed by this review. Metadata controls cannot substitute for these contracts or actual evidence.

Keep the existing single Patient details dialog pattern unless a later R04 route is independently designed. Retain name/UHID, available DOB-or-age/phone and named branch throughout; absent identifiers say Not recorded. A later document feature must fail closed when branch mapping is missing and reject scope mismatch before rendering. Avoid nested dialogs. Present only actual allowed categories. Status text must distinguish a declaration, receipt of bytes, safety processing and authorised availability.

Freeze future page/action API parity, exact discovery/entry behavior and unknown-command reconciliation before UI code. Bind every result and mutation settlement to patient/branch/session generation; clear sensitive state on context change/close/logout/permission loss. Do not automatically replay writes on reconnect. A detail GET alone cannot attribute which command committed after an ambiguous POST. Preserve exact payload/key for explicit same-key recovery only while the authorised context remains valid; no browser storage, URLs, logs or analytics for filenames/reasons/keys.

Later browser acceptance must cover keyboard entry/back/close/focus return, inline errors with linked focusable summary, safe unavailable/empty states, visible status announcements and readable identity/actions at375/768/1024/1440px. Synthetic staff walkthrough must actually attach a supported registration image and explain the observed received/checking/available state. PDF/clinical/doctor walkthroughs await their separate scope; no claim of real-staff acceptance from synthetic execution.

## Executable test design and evidence limits

These are proposed tests; **none was run and no RED/GREEN result is claimed**:

1. API-only regression: staff pages/bootstrap/Patient details produce zero metadata calls and no Documents/Upload/Download/SHA256 controls even when synthetic CurrentUser includes document grants. No production frontend change is needed to manufacture this pass.
2. Activation: normal-authority denial remains before disclosure; authorised disabled request503 before object queries/writes; enabled synthetic metadata works with absent storage/scanner while all upload/download fields stay false and category list empty; missing metadata dependency503. No setting or client flag enables content.
3. Exact-branch matrix for all four operations and replay: reception-A allowed; doctor/nurse/master-only denied; reception-B+doctor-A deniedA; inactive assignment, stale session and revoked grant deny. CurrentUser adds only static reception document grants to the corresponding branch arrays/global union and no future categories.
4. API schema/parity: four documented operations only, no implicit content route or UI-only writes; projections contain no digest/reason/creator label/PHI beyond the frozen declaration fields; closed capabilities, safe errors/no-store/never304, audit failure prevents disclosure. Independently verify actual API responses, not frontend mocks.
5. Later UI gate: missing branch map never falls back to global union; no eager fetching; scope change/close cannot settle late data or ambiguous writes into another patient; same-key recovery and offline explicit refresh; declared versus received versus available wording; no real upload claim before byte acknowledgement or download before current ready authority.

Actual review evidence: source/document inspection only. UI/UX Pro Max search executed `status empty unavailable feedback --domain ux` returned Empty States and Submit Feedback, which support useful empty-state guidance and explicit outcome feedback. Mobile Haptic Feedback was also returned and is inapplicable to this desktop browser review; no recommendation to add it. This is a targeted existing-flow review, not a new visual-system design. No product tests, browser task, deployment, dependency install or application mutation was performed.
