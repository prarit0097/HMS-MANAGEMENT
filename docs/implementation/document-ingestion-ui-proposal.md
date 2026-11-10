# Registration image UI proposal

**DRAFT — 8 November 2026.** Coordinator proposal for reconciliation, not a frozen API, implementation or verified browser result. Read with [ingestion design](document-ingestion-design.md), [metadata contract](patient-document-metadata-contract.md) and [6 November checkpoint](../operations/document-ingestion-planning-checkpoint-2026-11-06.json). Existing 50 HTTP operations include four deployed but disabled metadata operations; none supplies bytes, scanning or download. R04 stays hidden until useful ingestion passes end-to-end acceptance and reviewed activation.

## Existing workspace and smallest extension

`frontend/src/pages.tsx` opens Patient details inside `Modal`; `App.tsx` remounts operational pages on branch/navigation changes and supplies branch-scoped permissions. Preserve that dialog, patient search/page position, visual classes and demographic correction. Add an inline **Documents** subview with **Back to patient details**, not another dialog/global navigation destination. A routed workspace adds navigation work without helping this bounded task; nested dialogs complicate focus. No new style, token framework or dependency is proposed.

Keep patient full name, UHID and actual named branch above every document action. Use existing patient data and `user.branches`; missing/mismatched patient branch or missing named branch blocks entry without a document request. Never display a UUID as a branch name or invent clinical details. Registration JPEG/PNG only: no PDF, clinical category, OCR, thumbnail, creator-name lookup or new patient API.

## Entry and API consumer requirements

**Proposed additive discovery**, requiring independent API review: authenticated CurrentUser gains optional `document_ingestion_by_branch`, mapping currently authorised branch UUIDs to `{available:boolean,categories:["registration"]}`. Availability means reviewed deployment enablement of a usable ingestion journey; it is no patient/object existence probe and exposes no provider/scanner diagnostics. Omitted map/key, malformed data, false availability or an empty category list means hidden. CurrentUser must derive this from trusted readiness/configuration; client build flags and permission strings cannot substitute. Transient dependency failure after entry returns an honest unavailable result.

Before rendering entry, require explicit `branch_permissions[patient.branch]` containing `documents.registration.read`, exact selected-branch equality and available registration ingestion. Never use App's legacy global-union fallback when the branch map is absent. Adding requires the same branch's write permission plus current returned action capability; read-only users can view/download only when authorised. Master status grants nothing here. Refresh CurrentUser after session/branch authority changes; absence or failure clears document state. Each server operation independently reauthorises patient/category/branch/network/session.

Additional API contracts needed before code (names/paths remain coordinator decisions):

| Consumer need | Required input/output |
|---|---|
| Discovery | CurrentUser addition above; default-deny compatibility and freshness rules. |
| Unified ingestion list/detail | Patient scope, bounded keyset cursor; opaque intent/content identities, declared filename/size, server time, separate intent and ingestion status, allowed next actions, reconciliation guidance. `results/has_more/next_cursor`, no count; no creator name, digest or storage locator. |
| Receive bytes | Existing metadata create supplies declaration/intent; new raw-byte command binds that intent and immutable received generation, exact size/digest/type and operation-specific retry identity. Return authoritative receipt/status, never infer acceptance from transport success. |
| Reconcile | Same keyed metadata replay plus a precisely contracted receive replay/status action resolving unknown acknowledgement without creating another intent/generation. Bound same-key/payload/conflict behavior. |
| Download | Current accepted-content identity and fresh capability; private same-origin attachment response with bounded bytes, safe filename/media headers and audited authorisation. No public/bearer URL. |
| Withdraw | Existing creator/version intent withdrawal remains unchanged. Separate accepted-content withdrawal contract/capability is required; its lifetime cannot inherit the intent's 30-minute deadline. Return authoritative outcome/version and retry semantics. |

Preserve the four closed metadata payloads. A separate unified ingestion projection must distinguish an expired declaration from a still-accepted file; never map accepted content back into `pending/expired/withdrawn`. Exact status enums, receipt generations, retry headers, errors and withdrawal reason rules await backend reconciliation. No frontend production work until OpenAPI/page actions freeze these interfaces.

## Subviews, states and actions

List rows show filename, size, requested time, plain ingestion status and permitted actions. Refresh resets cursor history to the first page; **Next documents** uses the opaque cursor and **Previous documents** uses memory-only cursor history. No total or invented page number.

| State/subview | Staff text/action and required behavior |
|---|---|
| List loading/empty/error | Loading status; **No registration documents**; or plain unavailable message with **Refresh documents**. Do not reuse stale rows as current permission evidence. |
| Add/select | Native labelled **Choose image**; help: **JPEG or PNG, up to 10 MiB**. One file; no camera requirement. Browser checks nonempty size, supported declaration and filename rules before hashing; server validates bytes independently. |
| Preparing | **Preparing image…** while SHA-256 is calculated locally. Disable Send until resolved. No editable digest/type/size declaration form. Failure offers **Choose another image** without a request. |
| Confirm | Show patient/UHID/branch, filename and size; **Confirm this is the correct patient**, then **Send image**. Selection/hashing alone sends no metadata or bytes. Changing patient/file clears confirmation. |
| Sending | **Sending image…**; one active logical submission, no fabricated percentage. Create declaration only after confirmation, then receive bytes. Disable duplicate Send; distinguish receipt from accepted file. |
| Processing | **Image received. Checks are in progress.** Only when server confirms receipt. **Refresh status**; no automatic polling/replay or premature Download. |
| Accepted | **Available to download** only from authoritative accepted status/capability. **Download image** performs a fresh authorised request. Announce **Download started**, never claim the file was saved to disk. |
| Failed/unavailable | **Image could not be accepted** or **Document service unavailable** from contracted safe codes. No scanner internals. Show only server-permitted retry/withdraw/refresh actions. |
| Unknown acknowledgement | **We could not confirm the result. Check status before sending again.** Explicit **Check result** uses the retained logical identity; no new-key retry, success or rollback assertion. |
| Withdraw | Inline confirmation within the same dialog, with reason only as required by the chosen contract. Label **Withdraw request** versus **Withdraw document** precisely. Refresh authoritative state on conflict; no silent deletion or optimistic success. |

## Memory, navigation and failure policy

Coordinator UX proposals, **not measured/frozen limits**: one selected file and one active send per dialog; 10 MiB is the existing declaration ceiling (10,485,760 bytes); zero automatic mutations/polls. Do not invent request timeouts, scan promises or retry intervals.

Keep file, digest, keys, payload fingerprints, cursor history and pending results only in memory. Clear them on dialog close, patient/branch/session change, logout, revocation and after settled completion when no reconciliation needs them. Clear hashing buffers promptly; release file input and blob URLs. No filename/key/PHI in URLs, storage, logs or analytics.

Back from selection discards the draft. During sending/unknown outcome, Back/Close/Escape uses an inline **Leave documents?** choice: **Keep checking** or **Leave**; explain that leaving does not cancel server work. No nested modal. Forced navigation invalidates the generation immediately. Bind every digest/read/send/download/error/finally settlement to session+branch+patient+selection generation and request sequence; aborted fetches do not establish rollback.

Offline blocks reads/writes/download and marks cached status stale. Reconnection requires explicit successful **Refresh documents** before actions resume; no automatic replay. Reload/close loses keys: refresh the authorised list and inspect server state; never identify a prior submission solely by filename/digest or blindly create a replacement. If identity cannot be recovered, show **Result cannot be confirmed here. Contact the hospital administrator before sending again.** No operational bypass is implied.

## Minimal proposed file map and acceptance

Later implementation: `pages.tsx` passes patient/branch/user context into new `PatientDocuments.tsx`; `types.ts` adds reviewed closed projections; `api.ts` gets explicit bounded raw-byte/attachment helpers (current helper forces JSON); `ui.tsx` only changes if its existing focus loop cannot support inline subview transitions. Reuse existing styles. Keep tests alongside the feature; no component framework expansion.

Browser/staff acceptance remains OPEN: ordinary reception chooses correct patient and sends JPEG/PNG; read-only/mixed-branch/master/missing-map users never fetch forbidden documents; 0/10MiB/10MiB+1/type/name/hash failure is clear; accepted file remains distinguishable after intent expiry; explicit refresh, cursor navigation, safe download and both withdrawal kinds work. Cover lost create/receive/withdraw acknowledgements, duplicate clicks, conflict, offline/reconnect, reload/key loss, close during send, late digest/POST/GET/download after context change and revocation. Verify no persistent sensitive state or eager download.

At 375/768/1024/1440px and 200% zoom, identity, labels and actions remain readable. Keyboard completes chooser/confirm/send/refresh/download/withdraw/leave; focus moves to subview heading/error summary, returns to opener, remains trapped in the one dialog and is visible. Text statuses use contextual polite announcements without focus theft; errors associate with fields and do not rely on colour. Representative reception staff must complete the journey and explain received versus accepted versus unknown result using synthetic records.

UI/UX Pro Max was read; verified prior query evidence in the 6 November checkpoint returned Submit Feedback, Contextual Live Badge Updates and Inline Validation. Applied only to feedback, contextual announcements and field errors. No new search, implementation, browser exercise, staff acceptance or test was run for this proposal.
