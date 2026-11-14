# Ingestion supervisor and scanner identity mapping

**DRAFT — 15 November 2026, Asia/Calcutta.** Bounded candidate for review, not a frozen schema, implementation plan, migration, executable acceptance or activation. Read with [launch proof](document-ingestion-launch-proof-draft.md), [guard authority](document-ingestion-guard-authority-contract.md), [runtime](document-ingestion-runtime-contract.md) and [persistence](document-ingestion-persistence-contract.md). No source, API, setting, dependency, OS or live change is supplied. Existing S0/S1/B3 delivery remains complete.

## Minimal identity set

Use **one `supervisor_launch_instance` UUID** for the exact root-authorised supervisor process lifetime, with the launch draft's immutable boot/PID/start/unit/manifest tuple. Do not also add `supervisor_launch_generation`: it has no independent transition or consumer beyond the instance and would create another equality field without another security property. UUID equality fences identity; it never authenticates process provenance.

Use **one `scanner_generation` UUID** for one daemon start plus its immutable engine/config/validator/signature snapshot. The existing DRAFT name `supervisor_generation` means this scanner lifecycle and is replaced by `scanner_generation` at every proposed consumer below. It must not represent the supervisor launch instance. Never infer either identity from the other, content generation, restore epoch, policy hash or readiness token.

Each new scanner start creates a new scanner UUID even with identical snapshot hashes. A signature/config/validator change requires the runtime's stop/snapshot/start sequence and a new UUID, not in-place mutation. Supervisor replacement requires old owned processes to cease; the replacement starts its own daemon and therefore also obtains a new scanner UUID. The identities stay distinct because a scanner can restart while its supervisor stays unchanged.

## Exact candidate field mapping

| Proposed location | Candidate amendment / invariant |
|---|---|
| Control namespace | `installation_id` and `restore_epoch` remain separate external-guard identities; neither is a process or scanner generation. |
| Control expected launch | Name the launch UUID `expected_supervisor_launch_instance`; keep expected boot/PID/start/unit/manifest fields from the launch draft. These six nullable fields are all absent or all present. No additional launch-generation column. Only the reviewed root launch transition may replace them; unknown commit requires reread of the same intended tuple before publication. |
| Control current scanner | Rename proposed `supervisor_generation` to nullable `scanner_generation`; null means no currently authorised scanner generation. It is fixed for one daemon lifecycle. Setting/replacing it requires the current trusted launch and the separately constrained transition; it cannot replace the expected launch or open any gate. Exact publisher database privilege enforcement remains a blocking gate. |
| Control readiness | Add nullable `readiness_supervisor_launch_instance`; readiness true requires equality to the complete expected launch, nonnull `scanner_generation`, existing readiness token/policy/signature/time evidence and all parent readiness checks. On readiness invalidation clear the readiness linkage/token/evidence tuple. Scanner generation may remain recorded only while that daemon lifecycle is still authorised; fence/termination clears it. Historical attempts retain their original scanner identity. |
| DocumentScanWork issued claim | Rename proposed `supervisor_generation` to `scanner_generation`; add `supervisor_launch_instance`. Together with existing `readiness_token`, all three are present for an issued claim and absent before first claim. Clear/replace an old claim tuple only through the existing cessation-confirmed retry/reconciliation transition; never rewrite it merely because Control changed. Existing cycle/ordinal/lease/worker/epoch/deadline fences remain independent. |
| DocumentScanAttempt immutable evidence | Rename proposed `supervisor_generation` to `scanner_generation`; add required `supervisor_launch_instance` for every issued attempt, including unavailable/abandoned evidence. Copy the original claim identities, not current Control at completion. A failed claim that never committed creates no issued attempt authority. Existing immutable policies/digest/size/cycle/ordinal evidence remains. |
| Scan IPC / internal service contracts | The issued-claim and result vocabularies carry both named identities, readiness token and existing claim fences. Reply equality requires the issued tuple; final locked authority selection additionally requires its launch/scanner/readiness tuple still equals current Control. Untrusted payload values cannot create trusted launch proof. No raw service-command, caller PID or operator override is added. |
| Content / receipt / ingestion event | Content's accepted-attempt link supplies historical scan identities; do not add duplicated current scanner/launch pointers to content or receive receipts. `scan_result` audit links the exact immutable attempt. A later unrelated launch/scanner change does not rewrite accepted evidence or revoke existing-file access by itself. |

Schema CHECK spelling, nullable issued-claim terminal states, immutable evidence construction, FK ordering and SQL privilege boundaries must be frozen together in the schema/service leaf. These candidate field names supersede neither existing draft text nor source until coordinator reconciliation. No ingestion model with these generation fields is implemented in `backend/apps` at this review.

## Selection and transition matrix

| Trigger | Expected launch | Scanner / readiness | Required result |
|---|---|---|---|
| Scanner restart or signature replacement under same supervisor | Unchanged instance and OS tuple | Readiness invalidated before stop; new daemon has new scanner UUID and fresh readiness token/evidence | Old issued attempts cannot promote using old scanner/readiness identities. Do not reopen intake merely by receiving a new token. |
| Supervisor replacement, even with identical engine/signatures | Root installs fresh instance/OS tuple only after old owned cessation | Old readiness/scanner fenced; replacement daemon gets fresh scanner UUID | Paused old supervisor cannot adopt new UUIDs by rereading Control. Identical hashes never imply same process. |
| Readiness renewal, same processes and snapshot | Unchanged | Same scanner UUID; fresh token/evidence under parent freshness policy | Claims bound to an older token follow the parent exact-token rule; renewal must not silently make old claims current. Exact renewal-versus-inflight policy requires concurrency acceptance before freeze. |
| Known claim commit; result delayed across scanner/launch change | Current tuple differs from original claim | Original evidence identities remain immutable | Final selection denies promotion; record only authorised unavailable/stale outcome under the frozen result/audit contract. Never retag result as current. |
| Claim/install/readiness ACK unknown | No speculative replacement or adoption | Reconcile original identities/token; no reminting deadline or claimed rollback | Do no scan work until original claim is known committed; no fresh readiness advertisement until installation/publication outcome is reconciled. |
| API close or external guard/epoch mismatch | Tuple possession conveys no authority | Publication/promotion independently checks current gates/guard | No authority despite matching UUIDs. Postcommit observation failure leaves publisher locally unready; no instantaneous OS/DB atomicity claim. |
| Restore or copied enabled Control | External target epoch and maintenance remain decisive | Copied process/readiness/scanner facts are not current evidence | First-slice restore reopening remains unavailable; this document supplies no recovery principal or reopen procedure. |

## Client, API and acceptance effects

No changes to the current 50 implemented HTTP operations, S1 facts grammar, B3 receipts or existing CurrentUser shape. The five ingestion APIs remain proposed. Launch/scanner UUIDs, OS tuple and engine evidence are internal, excluded from staff JSON, error strings, MCP and ordinary logs. Optional future availability uses the parent boolean capability projection; it does not expose or accept these identity fields. Frontend does not choose generations, retry scan claims or manufacture readiness. No user-facing field/page/action is added by this mapping.

Required executable cases after leaf freeze: same supervisor with scanner replacement; supervisor replacement with identical snapshot; old publisher paused before Control lock; wrong-instance same-UID/fork/reexec subject to the launch threat model; unknown ACK at installation/renewal/claim/result; readiness renewal while a claim waits; stale result cannot be relabelled; copied restored Control cannot reopen; immutable accepted history survives routine update. Prove OS evidence is collected outside business locks and final generation comparisons occur after lock waits. These are a test design, **not tests run or passing evidence**.

## Blocking exit gates

- [ ] Reconcile exact field names and nullability across Control, work, attempt, IPC, guard and runtime drafts, including renewal versus active-claim semantics.
- [ ] Freeze trusted launch descriptor/provenance/OS lifetime mechanism and SQL privilege ceiling; UUID possession and Python types do not enforce either.
- [ ] Independently review scenarios/threats and freeze the smallest schema/service leaf before literal RED, actual PostgreSQL races and Linux ownership/cessation tests.
- [ ] Keep native validation/scanning/resource/public-ingress/retention/recovery and staff/browser acceptance separate from this mapping and from production release.
