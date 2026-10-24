# Protected patient documents — UI proposal

24 October 2026. **Design only; not frozen, implemented, tested with staff or deployed.** Task04 / R04. Coordinator must reconcile this proposal with `patient-documents-design.md`, the security proposal, versioned OpenAPI and page-action map before code. Schema-dependent proposals below do not grant authority. No frontend, runtime, storage or deployment change is made by this document.

## Basis and present behaviour

Read AGENTS.md, HMS.md, plan.md planning gate/Task04/R04/cross-cutting UX requirements, implementation ledger and Phase A/reception contracts, consolidated research identity/disclosure guidance and ICTHospital comparison. Shared identity does not grant shared clinical access; the external attachment reference proves no protected-file implementation.

Actual frontend inspected: `frontend/src/pages.tsx` Patients/PatientDetail, `App.tsx`, `ui.tsx`, `types.ts`, `api.ts`, styles and package manifest. React19/TypeScript uses hash-level workspace navigation; Patients is a paged search table, View opens Patient details in `Modal`, and corrections replace its body. App remounts operational pages on branch change and passes branch-specific permissions. Patient has name/UHID/branch/DOB/age/phone; no document type/API exists. `api.ts` assumes JSON request/response and cannot carry raw bytes/downloads unchanged. Existing Modal has focus return, Escape and a focus loop, but those mechanisms require new-view/browser verification; do not claim accessibility from reuse alone.

Actual backend `authorization.py`: reception has patient read/write; doctor/nurse patient read; master_admin has platform permissions and no automatic patient or clinical rights. No document grants currently exist. PatientDetail GET filters permitted registration branches; do not assume a future document on another branch is authorised because its patient UUID is known.

## Approach and scope

1. **Proposed choice: extend existing single patient dialog.** Add a Documents section below demographics, replacing its body with Documents, Upload document or Document details when requested. Keep the identity block in every subview; Back to patient details / Back to documents makes the return explicit. No nested dialogs. Smallest change compatible with the existing correction pattern.
2. Tabs within the dialog would make sense once several real patient workspaces exist, but introducing a tab keyboard model for one new section adds little value now.
3. A routed patient page is a reasonable future R04 home for visits and clinical work. Current App only resolves workspace hashes; introducing that route now expands scope and back/deep-link requirements. Do not advertise `/patients/:id` as an implemented route.

The coordinator selects/freezes the pattern; this is a specialist recommendation, not an assertion of owner approval. No redesign of reception, encounters, navigation, branding or other modules. No preview, OCR, extraction, signing, clinical acknowledgement, editing/reclassification of accepted files, email/share link, bulk export, patient portal or upload-from-URL action.

## Entry, identity and disclosure

Patients > search > **View [patient name]** > Patient details > **View documents**. Show that section/action only when the current branch capability allows at least one category; do not fetch documents on opening demographics. No document count, hidden-category placeholder or “clinical files restricted” hint to users without that category. A concealed resource response must not reveal whether a file exists.

Every document list/detail/upload heading is preceded by patient full name, UHID, and two appropriate identifying details from authorised patient data: known DOB/age and phone where present. Show `Not recorded` rather than fabricated identity; retain name/UHID and ask staff to confirm identity when both secondary details are absent. Never require invented DOB/phone to upload. Display named **Branch: [name] ([code])** and the authorised organisation label only if supplied by an existing/new contracted API; do not infer organisation from a UUID or reuse an unrelated summary. No redundant full address or identity-document number in the banner.

Opening documents re-fetches current authorised patient identity and document scope; never silently retarget an open upload when branch/patient/session changes. Branch change, logout, permission loss or modal close clears in-memory file references, document responses and pending UI state; late promises cannot restore them. No PHI/file names/content in browser storage, URL/query/hash, analytics, console or error telemetry. Preserve the list search/page behind the dialog when returning within the same branch.

## Category and API authority proposal

Architect proposal received before writing: `registration` and `clinical_reference`; category-specific `documents.registration.read/write` and `documents.clinical_reference.read/write`. Reception registration, doctor clinical reference, others including master none by default. **Pending coordinator freeze**: exact grants, any read prerequisite for uploads, own-withdraw rules, role mapping and response shape. UI checks advertised branch capabilities, never hard-coded role names. Registration files can themselves be sensitive; their metadata also requires category access. No insurance attachments or expanded clinical-chart grant is implied.

The server returns only allowed rows/categories and separately authorises every list/detail/upload/content/withdraw request using current organisation, branch, patient and category scope. `patients.read/write`, platform privileges and role labels cannot substitute for document grants. Client disabling is convenience only. Do not load a forbidden category then hide it in CSS. No clinical signing right follows from uploading a clinical reference.

Before code, OpenAPI and the page-action contract must freeze exact paths/operationIds, request/response schemas, media/size bounds, error codes, retry semantics and permission rules for every action below. The current architect direction is two-step metadata POST then raw PUT `application/octet-stream`, not multipart, followed by authorised GET content. Route spellings and envelope fields remain pending; all operations remain under `/api/v1/`.

| R04 page action | Required versioned API behaviour | Client contract |
|---|---|---|
| Enter/reload Documents | GET patient document list, explicit branch, strict category filter, default25/max100/offset<=10000 proposal | Lazy load; only permitted category choices; never local filtering of unauthorised rows |
| Open file metadata | GET document detail in same scope | Show allowlisted metadata and authoritative `can_download` / `can_withdraw` proposal |
| Start upload | POST metadata/category/idempotency key | Returns stable document ID/state and exact byte-upload contract; no “uploaded” success yet |
| Send selected bytes | PUT fixed document byte endpoint, bounded raw body with CSRF/session | Never arbitrary destination/URL; no JSON helper reuse; transport status does not imply clean |
| Refresh check/result | GET detail/list | Status originates on server; explicit Refresh status, no mutation/scan promotion in browser |
| Download | GET fixed content endpoint, fresh ACL/network/session/category/ready recheck | Explicit attachment only; no prefetch/inline iframe/public or reusable signed URL |
| Withdraw own eligible file, if frozen | POST document withdrawal with exact version/reason rules | Separate confirmation subview; result traceable; no delete, restore or unwithdraw feature inferred |

Capability discovery must also be contractual: allowed categories, read/upload actions and bounds must be advertised through a frozen extension to current-user capabilities or another versioned operation. Do not introduce an uncontracted metadata endpoint. If limits are shared constants they must match schema/server policy exactly and fail closed when absent/inconsistent. List/detail content must not contain storage paths, bucket keys, malware-engine output or unrelated patient fields.

## List, metadata and upload

Documents subview: identity banner; **Documents** heading; **Upload document** if permitted; small category selector only when two authorised categories exist; **Refresh documents**; server-paged list. Suggested columns: Document name, Category, Added (IST/date), Status, **Details**. Show size in detail rather than forcing more columns on narrow displays. Each action accessible name includes document name. Initial empty text: `No documents to display.` Add `Use Upload document to add a permitted file.` only for an upload-capable user. Count describes only returned authorised rows. New upload resets list to first page and refreshes from API; never append an invented ready row.

Metadata subview: safe display name, category label, byte size, detected type, added time and uploader label only if contract supplies it, status and a plain next step. Long names wrap; hostile text renders as text. Show **Download** only with current response authority and ready status; detail alone never downloads. No raw JSON or scan reason text. `Checked for file safety. This does not approve its clinical contents.` accompanies Available clinical references without treating the scan as diagnostic validation.

Upload subview uses visible labels and essential fields only: **Category** (only allowed options; explicit selection if multiple), **Choose file**, and **Document name** if the frozen metadata requires a separate name. Prefill safe display name from the file but allow correction before submission. No arbitrary description/diagnosis, encounter selector, identity number, tags or date field added speculatively. Proposed bounds from architecture: one PDF/JPEG/PNG, maximum10MiB, filename120 characters; freeze exact byte interpretation, safe name policy and MIME/signature behaviour before coding. Display allowed formats/size before chooser. Native file input is fully usable without drag/drop; omit drag/drop initially.

Identity/category/name review and **Upload document** submit follow the chooser. Local validation gives early feedback; backend validates original bytes/type/signature/size independently. After metadata allocation but before byte acknowledgement say **Uploading…**; do not show fabricated percentage. Busy submit guard blocks double activation. On accepted byte PUT show `Upload received. The file is being checked and cannot be downloaded yet.` only when its actual API state confirms this. Replace the form with metadata/status and clear selected File references. Cancelling/closing before commit clears memory; closing during transfer may leave an allocated/uploaded document, so reopen/reconcile rather than silently claim cancellation. Exact pending-transfer navigation behaviour is a freeze item.

## Server states and plain language

Map only frozen enums. The architect currently proposes these; do not add a fictitious `scanning` enum to the frontend. If backend has only `quarantined`, use generic checking text; explicit queued/scanning labels require real server substates.

| Contract state proposal | Visible label and next step | Download |
|---|---|---|
| `awaiting_upload` | Waiting for upload — file has not been received; reconcile/resume only under frozen retry contract | Unavailable |
| `quarantined` | Being checked — `The file is not available until checks finish. Refresh status later.` Queued/scanning only when server distinguishes them | Unavailable |
| `ready` | Available — checked file, clinical contents still require normal clinical review | Explicit authorised Download |
| `rejected` | Blocked — `This file could not pass the hospital’s file checks. Choose a different file or contact support.` No raw detection text | Unavailable |
| `scan_failed` | Check unavailable — `File checks could not finish. The file remains unavailable. Contact support if this continues.` | Unavailable |
| `withdrawn` | Withdrawn — safe approved reason/time if frozen; record remains traceable | Unavailable |
| Content/storage unavailable or unknown enum | File unavailable — `Refresh status or contact support.` Unknown shapes fail closed and do not render a ready action | Unavailable |

No mark-safe, skip check, release, force retry scan or administrator download override. Scanner retry is operational work unless a reviewed versioned capability explicitly adds it. Future scan state transitions arrive through GET, never browser timers that mark completion. Avoid continual screen-reader announcements: announce a status change once in a polite region, never every refresh tick. Explicit refresh is the minimum slice; automatic bounded polling needs a frozen cadence/backoff/stop policy first.

## Failure, retry and recovery design

| Failure | Required response |
|---|---|
| List/detail loading | Neutral loading text/status; no stale patient content from prior scope |
| Validation/oversize/type/name | Focusable summary with links to fields, linked inline errors; retain permitted metadata and chosen file only within same live dialog; server raw payload never echoed |
| Permission/session/network denial | Concealed plain error, clear file/detail data and disable file actions; reauthenticate through existing shell flow; no file-existence hint |
| Offline | `You are offline. Reconnect, then refresh documents before continuing.` Disable starts/downloads/withdraw; reconnect never sends writes or resumes bytes automatically |
| Unknown POST/PUT outcome, timeout,5xx, unreadable success | `We could not confirm the upload. Refresh its status before trying again.` Block new logical upload; reconcile same stable operation/document under frozen API idempotency contract; no automatic new key/file duplication |
| Conflict/stale withdrawal | Retain safe draft reason, require fresh detail/status before new confirmation; no optimistic removal |
| Scanner/storage unavailable503 | Explain file unavailable and provide Refresh status/contact support; never promote quarantine or synthesize clean state |
| Content becomes unavailable between detail and Download | Fresh GET is denied safely; clear busy, refresh detail; no fallback URL or cached blob |
| Download request error/binary malformed | No saved error HTML as file; distinguish JSON errors from approved binary headers, fail closed; say `Download could not start. Refresh status and try again.` |
| Download received | Say `Download started.` only after authorised successful binary response; browser cannot prove the OS saved it |

Metadata POST unknown before stable ID requires exact same-key replay/lookup in the API contract before UI implementation; searching by filename is not reconciliation. Raw-byte PUT retries require defined replay/resume guarantees; do not infer resumable offsets. A new replacement upload is a deliberate new action after prior status is resolved. Memory-only Blob URL, if required for same-origin attachment delivery, is revoked promptly on completion/scope change; no blob prefetch, persistent cache or temporary public link. Browser download remains an explicit user disclosure; no copying file contents to clipboard.

## Accessibility and representative acceptance

Retain existing typography/panels/semantic buttons; visible text labels, normal-text contrast>=4.5:1, no colour-only status. At375/768/1024/1440px identity/context/actions remain readable; list becomes readable stacked rows or contained table without hiding patient context or actions. Buttons use adequate touch targets. Error summary receives focus on failed submit, links to invalid controls, retains inline `aria-describedby` errors; focus stays visible under any header/footer. File chooser, category, Upload, Refresh, Details, Download, Back and Close work by keyboard. All subview transitions move focus to a heading, restore the triggering control on return and preserve a single labelled dialog. Escape follows the same pending-upload/unsaved-change contract as Close. No nested focus traps. Announce busy and final outcome; no progress fiction. Detail-only/empty state must still have a valid focus target and close control.

Actual UI/UX Pro Max searches executed24October: `error summary validation --domain ux` returned Focusable Error Summary, Error Messages and Error Placement; these directly support summary focus/links plus inline errors. `keyboard focus modal --domain ux` returned visible Focus States and distinct Focus Not Obscured Minimum/Enhanced; this proposal requires AA minimum, does not present AAA as mandatory. `loading status screen reader --domain ux` returned semantic Screen Reader and Submit Feedback guidance. React `effect cleanup stale response --stack react` returned effect cleanup/dependency guidance; its listed applicability19.2.x is advisory against installed19.3.1, not a compatibility test or recommendation to introduce Effect Events. Existing visual direction is retained; no generated palette/marketing recommendation is applied.

Literal staff walkthroughs to perform using synthetic fixtures before acceptance:

1. Reception: “Find Synthetic Patient A by UHID, verify name and two available identifiers, add their registration PDF, and tell me when it may be downloaded.” Expect no clinical category/data, clear checking state, later fresh Download only when ready.
2. Doctor: “Open Synthetic Patient A’s clinical reference image and download it; explain whether this approves its contents.” Expect clinical grant only in assigned branch, no signing/approval claim, distinct explicit download.
3. Master only: “Open patient files using your administrator role.” Expect no patient/documents capability or document requests solely from master privileges.
4. Reception with shared-phone patients: “Attach this file to Synthetic Patient B, not A.” Verify UHID/context throughout, Back/branch switching cannot carry selected bytes into another patient.
5. Staff: “The connection dropped after Upload. Recover without adding the same file twice.” Expect unresolved outcome message and same-operation status reconciliation, no automatic write on reconnect.
6. Keyboard/screen-reader user: “Find a patient, upload an invalid file, correct the error, review status, return to the table.” Verify labels/focus/announcements and every return path. No real patient data.

Pre-code executable test design (not run; feature does not exist): category/branch capability matrix including master; forbidden categories absent from GETs/DOM/counts; correct patient/name/UHID context in every subview; blocked wrong-scope late GET/PUT/download settlements; max/exact/over byte boundaries and filename/type fields; double submit and idempotency key retention; quarantine/queued/scan_failed/rejected never downloadable; ready capability revoked before download; malformed enum/envelope/binary errors fail closed; unknown metadata POST and byte PUT reconcile without duplicate; offline/reconnect no writes; no storage/clipboard/public URL/content prefetch; one dialog/focus return/error links; paged/filter list and empty/denied/503 states; withdrawal only under frozen authority and immutable traceability. API negatives and actual backend transport tests run independently of UI mocks. Backend must prove scope/network/CSRF/size/scan gates; client tests cannot establish them.

## Freeze/verification checklist

- Coordinator freeze category/role grants, scope identity, limits and all operation schemas; add versioned OpenAPI/page actions before product code.
- Resolve two-step same-key replay/unknown outcome, byte retry, allocated-but-unuploaded expiry, cancellation and withdrawal retention/version/reason rules. Freeze exact unavailable/error semantics and whether check substates exist.
- Scenario/permission review and security threat review must resolve cross-patient/category disclosure, unsafe binary/type rendering, queued worker failure, storage exposure and audit expectations before code.
- Then write/run intended RED tests, implement API client only, and verify bounded API/component plus real browser tasks and widths. Documentation-only proposal has no application test, staff approval or runtime/deployment pass.
- Coordinator updates HMS.md, plan.md and ledger in its coherent change set and owns review/commit/push. This specialist owns only this file.
