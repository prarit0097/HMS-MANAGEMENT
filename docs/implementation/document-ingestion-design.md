# Private registration document ingestion — design reconciliation

**Status:** DRAFT, 6 November2026. Not a frozen implementation/API/UI/schema contract. No byte route, storage, scanner, worker, UI control, capability or flag activation is implemented by this proposal. Complete independent scenario/threat/test reviews and exact OpenAPI/page-action freeze before RED/code.

**Baseline:** [measured B3 deployment](../operations/document-http-preview-evidence-2026-11-06.json), [current metadata contract](patient-document-metadata-contract.md), [old architecture](patient-documents-design.md), [old UI proposal](patient-documents-ui-plan.md), [plan](../../plan.md). B1/B2a/B2b/B3/budget correction are complete in restricted previewbdbe8c6/core0009/metadataFalse. Consume them; never repeat their delivery.

## Current product boundary

The next useful outcome is an authorised reception member attaching a registration image to the correct patient, seeing an honest processing result and later downloading only an accepted file through current authority. User requirements remain API-first, simple professional UI, exact organisation/branch scope, backend IP controls and traceable actions. Registration material can contain sensitive data.

Current declarations are JPEG/PNG only, at most10485760bytes and120filename characters. Existing intent states are pending/withdrawn with expired projected by the current service; no bytes/ready/scanning capability exists. Current list uses keyset pagination and returns results/has_more/next_cursor, not the old offset/count proposal. Old PDF/clinical_reference/awaiting_upload/creator-label/detected-type UI suggestions are not authority to widen the current contract. Clinical records, OCR, bulk import, URL fetches, inline preview, signing and call-center integration remain outside this slice.

## Approaches still needing a coordinator ruling

1. Application-mediated bounded raw upload and authorised attachment download, immutable private storage generations and durable scan work. This reuses the earlier recommended direction and keeps byte requests within the existing application/network boundary. It still needs explicit resource and failure controls.
2. Direct object-store upload with immutable generation/completion protocol and a separately permitted ingress path. This adds provider/IAM/bearer/replay/replacement decisions; it is not selected or provisioned.

A private local synthetic adapter can establish source behavior without selecting the production storage region/provider/encryption/DR solution. No paid resource or live service change follows from this draft. Do not silently select unencrypted storage or a scanner that always reports clean to unblock development.

## Decisions required before freeze

| Boundary | Exact contract still required |
|---|---|
| Schema/migration | Separate intent, immutable received generation, scan attempt/verdict and accepted file identities; permitted states/constraints, retained current intents/receipts/events and schema rollback compatibility. Do not add states rejected by current CHECK constraints without a reviewed migration. |
| User APIs | Exact versioned raw-byte upload/content routes, operationIds, headers/media/body bounds, permission conjunctions, request/response/error schemas, query rules and idempotency/reconciliation. Existing four metadata routes do not supply these capabilities. |
| Upload authority | Current patient/category/branch grants, creator/other-writer rules, version/expiry selection, session epoch and effective network policy around writes/waits. Do not infer permission from global role union or master status. |
| Streaming/framing | Exact accepted entity/byte-count rules, timeout/concurrency/disk budgets, before-parser/real-CSRF order, incomplete/duplicate framing, 10MiB boundary and disconnected-client effects. Metadata's4096byte reader cannot be reused for file bodies; hidden WSGI trailing-byte limits remain real. |
| Storage | Opaque server-generated identity, immutable generation, private namespaces/permissions/encryption keys, no traversal/symlinks/overwrite/public route, durable creation/delete/orphan reconciliation and unavailable/corrupt/missing-key behavior. |
| Validation/scanning | Server-observed size/digest/type, bounded image decoding/content checks, scanner transport/readiness/signature freshness, exact-generation verdict binding, quarantine, failed/stale/unknown outcomes and retry ceiling. A declaration or antivirus result alone cannot establish safe/ready state. |
| Worker authority | Constrained work identity and current-scope revocation checks, lease/claim/retry/crash recovery, scan/withdraw/upload races and same-service permission ceiling. Never reuse a five-second captured request context indefinitely or introduce a hidden unrestricted mutation tool. |
| Disclosure/download | Current authority recheck, accepted-generation integrity, committed audit before disclosure, immutable attachment response, no public/presigned bypass, conditional/range/cache behavior, and disconnect/lost-reply limits. |
| Capacity/recovery | Independent upload/scan/download budgets protecting clinical work, bounded queues/retries/disk use, expiry/withdrawal/retention and object+DB+key backup dependency manifests. Restore must re-evaluate quarantine and cannot blindly overwrite shared patient data. |
| Activation/UI | Contracted capability/availability discovery, usable end-to-end storage+scan+retrieval acceptance and reviewed rollout before exposing R04 entry. A metadata-only form is explicitly insufficient. |

## R04 staff flow to reconcile with exact APIs

Keep patient name/UHID/branch visible; do not invent DOB/phone or infer names from UUIDs. Preserve the existing detail context and list position. No new global portal or nested dialogs.

| Action/state | Intended staff behavior; final API contract is still open |
|---|---|
| Enter documents | Only after a contracted useful capability exists; fetch current permitted data lazily, no forbidden-data fetch followed by CSS hiding. |
| Select file | Show supported types/size and an explicit patient confirmation before sending bytes. Keep file/key in memory only. |
| Confirm/send | One clear action, visible bounded progress, no duplicate automatic intent on retries. Transport completion does not mean the scan passed. |
| Processing | Plain status and deliberate refresh; status announcements include context without stealing focus. Do not show Download before current accepted-file capability. |
| Failure/unknown outcome | Preserve logical request identity for explicit reconciliation; show a safe next step. No blind new-key retry or assertion that a lost response means rollback. |
| Ready/download | Explicit authorised attachment action; no inline iframe, prefetch or bearer URL. |
| Patient/branch/logout/revocation change | Clear file references/projections/pending state; generation-bound late responses cannot restore old context. |
| Keyboard/accessibility | Visible labels/errors/focus, keyboard-complete flow, meaningful async announcements and no color-only status. |

Installed UI/UX Pro Max actual query `upload status retry forms --domain ux -n3` returned Submit Feedback, Contextual Live Badge Updates and Inline Validation. Applicable guidance is loading/success/error feedback, contextual atomic announcements without focus theft and field-local validation. These suggestions do not override server authority or frozen API semantics; no new style/token system is selected.

## Scenario/threat/test gates still open

- Freeze complete page/action/API/state/payload/query/permission/error/acceptance tables; reconcile both old proposals with the current deployed schema and API before coding.
- Plan genuine session/CSRF and exact scope positives/negatives; declaration mismatch, malformed/oversize/truncated/raw framing, wrong patient/category, current grant loss, expiry, replay and ambiguous acknowledgement.
- Plan actual PostgreSQL barriers for concurrent uploads, scan/withdraw, revocation/promotion/download, lease/retry and mandatory audit failures; verify actual persisted outcomes, not SQLite substitutes.
- Require real isolated validator/scanner/storage fault tests, immutable generation replacement/corruption checks, unavailable/stale key/signature/worker cases, private-route/network probes and bounded resource exhaustion checks.
- Browser tests must cover patient-context confirmation, memory clearing, late responses, keyboard/offline/permission/status/reconciliation behavior. Staff acceptance and real-data activation remain separate release gates.

No production adapter, model, migration, dependency, provider, live configuration or OpenAPI operation is added. Further independent reviews may reject any proposal above; unfinished values remain explicit rather than guessed.

## Primary sources rechecked6November2026

[OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) supports layered checks, generated storage names, size/permission/CSRF controls and storage outside the webroot; no single check guarantees safety. This informs the draft, not an acceptance claim.

[ClamAV scanning documentation](https://docs.clamav.net/manual/Usage/Scanning.html) requires signature data and warns that clamd TCP traffic has no built-in authentication. Private transport and explicit signature/readiness requirements remain to be frozen; no scanner is installed or tested here.
