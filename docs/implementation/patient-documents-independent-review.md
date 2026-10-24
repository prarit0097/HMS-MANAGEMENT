# Patient documents independent design review

24 October 2026; DESIGN REVIEW ONLY, not runtime acceptance. Architecture, UI and security specialists inspected actual source; a fresh fourth reviewer found the following freeze gaps. No application tests or product changes were performed by this review.

1. Metadata list/detail/replay disclose PHI. Commit bounded access accounting before response disclosure; audit failure503, no clinical events in generic administration history.
2. Exact upload replay must use an immutable receipt bound to intent/generation/original version/digest, independent of later scanner version transitions. Current authority still applies. Terminal outcomes must be explicit.
3. Freeze cross-service lock ordering against actual User/IdentitySecurity/Organisation/Membership/StaffAccessRevision ordering. Worker lease transaction ends before authority locks. Prove real revocation races in both serial orders.
4. No runtime ready/download success without concrete private encryption/storage, parser/scanner policy and resource budgets. Unavailable adapters fail closed. Synthetic test adapters cannot become runtime clean fallbacks.
5. Define fixed expiry at now>=deadline, no GET lifecycle mutation, terminal replay, and explicit HEAD/OPTIONS behavior.
6. Registration-first has no encounter link or clinical role grant. Reception needs conjunctive patient/category branch access; doctor/nurse/master get no automatic document authority.

Ruling: application-mediated private files fit current per-request network/session/branch constraints better than bearer object links. Start with pure schema foundations only while exact HTTP/storage/scanner details remain unfrozen. This does not create a capability or claim working uploads. Later metadata and byte slices each require separate exact contract/OpenAPI/page mapping, RED tests, independent review and actual PostgreSQL concurrency evidence. Cost: another source step before staff can use attachments; avoids advertising unsafe file access.

Read [architecture](patient-documents-design.md), [UI proposal](patient-documents-ui-plan.md), [security review](patient-documents-security-review.md), [plan](../../plan.md) and [ledger](ledger.md).
