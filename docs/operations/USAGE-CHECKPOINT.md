# Usage-aware HMS continuation

Owner instruction: when any applicable Codex usage window has 10% or less remaining, checkpoint HMS.md and stop new work; resume no earlier than 5 hours30minutes later and only with recovered usage.

State: ACTIVE_OWNER_RESUMED
checkpoint_at_utc: null
resume_not_before_utc: null
owner_resume_at_utc: 2026-10-23T13:36:49Z

Latest owner message: Continue limit aa gyi hai puri. Coordinator treats this direct instruction to resume now as an explicit waiver of the prior15:19:16UTC deadline. Authenticated at13:36:49UTC: primary100%remaining, weekly40%remaining (not all windows fully reset). Guard then evaluated current minimum39%remaining/continue at13:40. Historical09:49:16stop/15:19:16deadline preserved in ledger and ignored guard history. No reset credit consumed, no automatic waiver from recovery alone. New future<=10reading still creates fresh330minute cooldown. Same native heartbeat updated in place; no duplicate team/schedule.

automation_id: continue-hms-after-usage-cooldown
automation_interval_minutes: 330

Historical stop:6%remaining at05:02:15Z; checkpoint safely pushed. Owner first waived cooldown only for Hostinger deployment, then explicitly resumed general development with this later instruction. Deployed restricted synthetic preview remains as documented in HOSTINGER-PREVIEW.md.

Completed source: reception reliability and resource configuration, published2ca8239 with actual GitHubCI39935239961success166backend/25subtests,30frontend/build,19rootchecks. Existing live preview remains47b3618. Do not repeat these completed slices. Staff source contract staff-access-contract.md is now verified:4staff APIs/core0004/branch permissions, actualPG213tests/25subtests,49frontend/build; review races reproduced and fixed. Publication tracked in ledger/Git handoff. Next incomplete slice is MFA/security contract and RED-first implementation; do not repeat staff work. MFA remains unimplemented. Full remaining clinical/finance/MCP/dataops/release gates remain.

Before substantive work and bounded task boundaries, coordinator calls get_usage_limits and prefers rateLimitsByLimitId. remaining=100-usedPercent. Check primary and secondary applicable windows. A low weekly window may require longer than330minutes; never resume below threshold or consume reset credits automatically. Unknown usage means do not start a new large work unit until visibility returns.

At threshold: notify agents to checkpoint, stop assignments, preserve their changes/evidence, update HMS.md/plan.md/ledger, run safe bounded checks, commit/push if possible and record actual failures rather than claiming success. Record UTC checkpoint and earliest resume. Preserve an unelapsed deadline on repeated low readings. Update the same native heartbeat rather than create duplicates. No Windows scheduled credential-scraping script is used; native scheduling has authenticated usage access. Scheduler requires local PC/Codex/repo availability and cannot guarantee an exact wall-clock wake.

On wake: read this state, Git status/log and implementation ledger; do not duplicate a still-running team; enforce deadline and usage first. Continue from the first incomplete reviewed task. Stay quiet during unchanged cooldown checks. Disable automation only on actual completion or owner cancellation.
