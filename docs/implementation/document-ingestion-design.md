# Private registration document ingestion — design reconciliation

**Status:** DRAFT, updated8 November2026 after concrete proposals and two independent pre-code reviews. Not a frozen implementation/API/UI/schema contract. No byte route, storage, scanner, worker, UI control, capability or flag activation is implemented by this proposal. Complete independent scenario/threat/test reviews and exact OpenAPI/page-action freeze before RED/code.

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

## Coordinator reconciliation —8 November2026; still not frozen

Concrete inputs: [API/persistence proposal](document-ingestion-api-proposal.md), [security/operations proposal](document-ingestion-security-proposal.md), [R04 proposal](document-ingestion-ui-proposal.md). Independent API/scenario and crypto/operations reviews found material contradictions; writing proposals did not close the design gate. The following coordinator choices supersede conflicting sentences in those DRAFT inputs, but require exact schema amendments, feasibility evidence and fresh scoped review before freeze.

| Topic | Coordinator direction and remaining obligation |
|---|---|
| Compatibility | Use linked received-content/work and a separate unified ingestion projection. Preserve all four deployed metadata contracts/models/receipts/events. Accepted-file lifetime is independent of the declaration's30minute expiry; old parent withdrawal suppresses new promotion/download. Five proposed new operations must be reconciled before adding them to OpenAPI. |
| UI/discovery | Extend the existing Patient details dialog, no new portal/nested dialog. Choose API proposal's `document_ingestion={version:1,branches:{...}}` vocabulary, with exact branch fields available/can_read/can_receive/categories to be frozen. Absent/malformed means denied; no global role-union fallback or patient existence probe. Add immutable created_at to the proposed ingestion projection if requested time is displayed. |
| Availability | Separate deployment/read/list/withdraw availability from new intake readiness/capacity. A routine scanner outage/full queue must not hide already accepted files or disable eligible withdrawal. Accepted-file download still requires current reader authority, valid accepted evidence, key/storage integrity and no withdrawal/security hold; copied ready flags alone never suffice. |
| Receive identity | Reserve from trusted declaration/header identity before body receipt; final receipt requires actual matching size/type/digest. Charge transfer capacity and a bounded attempt allowance even on same-key replay. Authorised committed replay may resolve after declaration expiry; first binding may not. Do not create another encrypted candidate/generation/scan merely to verify a committed replay: bound/read/hash its supplied bytes in memory first. |
| Crypto crash/retry | Prefer verified bounded10MiB plaintext memory before encryption. Persist generation/wrapped key/nonce/AAD version and one-use sealing state before object creation. Seal once with exclusive immutable creation; reconcile a complete existing ciphertext rather than overwrite/re-encrypt. Choose terminal failure/new declaration for an interrupted used sealing identity unless a separate fresh-attempt protocol is explicitly modelled. Exact KEK-wide wrapping-nonce uniqueness, partial-file protocol, fencing and byte accounting remain blockers; no bespoke crypto implementation is authorised yet. |
| Time | Treat60seconds as a proposed original intake-to-first-binding cutoff, not a whole HTTP/network/COMMIT response SLA. Its exact post-auth origin, monotonic/wall checks, final precommit cutoff and relationship to declaration expiry need a single coherent contract. Existing5second B3 context is never reminted/reused across slow transfer. |
| Download authority | Choose final current authorisation/audit over the exact fully verified staged generation before first byte as the minimal contract. Do not carry forward the security proposal's extra per64KiB/one-second authorisation promise without separate bounded request authority and failure design. Revocation/disconnect after selection cannot recall already authorised/transmitted bytes; no continuous-transaction or delivery guarantee. Freeze conditional/Range handling and local transfer cutoff explicitly. |
| Durable scan authority | Ordinary logout does not cancel already accepted scan work or disclose anything. Active uploader, epoch, current branch-conjoined grants and current policy for the trusted recorded origin are rechecked at claim/promotion. No replayed browser context, unrestricted worker role or public mark-clean/retry action. |
| Restore | Never reset historical attempts, receipt time or accepted verdict to rescan restored content. Ordinary ingest attempts (three/ten-minute proposal) cannot clear day-old restored files. Byte serving remains disabled after restore until a separately exact restore-epoch/evidence workflow is frozen and passes recovery acceptance; this remains an activation blocker, not a completed restore feature. |
| Numerical/isolation policy | Security's quota, timeout, pixel, memory, queue and signature-age values remain proposals. Current host has4CPU/15992MiB memory with10961MiB available at observation, but no reservation or ClamAV executable on PATH. Freeze full accounting/UID/cgroup/swap/core/temp/buffering/owned-supervisor layout and prove engine-version support before enabling bytes. Do not present proposed60uploads/org/hour as adequate for555+OPD/day or future peak load without measured workload acceptance. |

### Specific blockers remaining after these choices

1. Exact durable reservation/crypto/fence/counter/readiness schema, lock order, every-operation admission/rate/replay accounting, and resource retention while an old process may still write. Five preliminary tables do not yet supply these controls.
2. Coherent unknown-reservation/first-seal/partial-write/fsync/bind-commit/ACK recovery; explicit no-nonce-reuse and no deletion on uncertain commit. All surviving sealed objects must remain decryptable through retained keys.
3. A dedicated scanner supervisor generation, fixed command vocabulary, reload interlock, timeout fencing and confirmed owned-process termination. The general application worker does not receive arbitrary service administration.
4. Version-pinned image/scanner policy, exact trailing/container checks and original-byte preservation, real engine/limit-skip/signature/reload behavior, full process/isolation/resource envelope and realistic clinical-load coexistence. No mock clean verdict or free-memory snapshot is proof.
5. Complete restore-epoch revalidation, recovery-principal authority, old attempts/history preservation and current key/object manifest dependencies before file activation.
6. Reconciled exact five-operation/current-user/page-action/response/error/state/permission tables, scenario/threat/test matrix, then independent review and explicit freeze. No implementation, migration, new dependency, UI exposure or OpenAPI addition precedes that gate.

Local environment observation: backend `.venv` reports Django5.2.7 while source pins5.2.18; global Python reports Django6.0 and lacks psycopg, while cryptography50.0.2 matches source in both. Global Pillow13.0.0 is not a reviewed application dependency; backend Pillow is absent. Do not use either interpreter as a silently compatible Django test environment. No package was installed/updated or application test run during this planning work.
