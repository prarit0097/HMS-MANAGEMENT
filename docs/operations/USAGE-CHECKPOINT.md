# Usage-aware HMS continuation

Owner instruction: when any applicable Codex usage window has 10% or less remaining, checkpoint HMS.md and stop new work; resume no earlier than 5 hours30minutes later and only with recovered usage.

State: ACTIVE_OWNER_RESUMED
checkpoint_at_utc: null
resume_not_before_utc: null
owner_resume_at_utc: 2026-10-23T09:12:37Z

Owner explicitly requested further development now and cooldown adjustment based on recovered usage. This supersedes the old active deadline (historical checkpoint05:02:15Z, historical earliest10:32:15Z). Coordinator verified primary76%remaining, weekly51%remaining; the smaller51% governs continuation. No reset credit used. The prior local guard state is preserved in ignored history and current guard returns continue. Future fresh <=10% reading still triggers a new330minute minimum cooldown; mere recovery never automatically waives a future deadline. The same heartbeat was updated, not duplicated.

automation_id: continue-hms-after-usage-cooldown
automation_interval_minutes: 330

Historical stop:6%remaining at05:02:15Z; checkpoint safely pushed. Owner first waived cooldown only for Hostinger deployment, then explicitly resumed general development with this later instruction. Deployed restricted synthetic preview remains as documented in HOSTINGER-PREVIEW.md.

Current active slice: reception-reliability-contract.md. Bed101selector is already fixed/deployed; do not repeat it. Continue scoped retry safety, demographic/reschedule UI, global bed filter/patient selection and actual CI verification. Remaining clinical/finance/MCP/backups/security gates stay planned.

Before substantive work and bounded task boundaries, coordinator calls get_usage_limits and prefers rateLimitsByLimitId. remaining=100-usedPercent. Check primary and secondary applicable windows. A low weekly window may require longer than330minutes; never resume below threshold or consume reset credits automatically. Unknown usage means do not start a new large work unit until visibility returns.

At threshold: notify agents to checkpoint, stop assignments, preserve their changes/evidence, update HMS.md/plan.md/ledger, run safe bounded checks, commit/push if possible and record actual failures rather than claiming success. Record UTC checkpoint and earliest resume. Preserve an unelapsed deadline on repeated low readings. Update the same native heartbeat rather than create duplicates. No Windows scheduled credential-scraping script is used; native scheduling has authenticated usage access. Scheduler requires local PC/Codex/repo availability and cannot guarantee an exact wall-clock wake.

On wake: read this state, Git status/log and implementation ledger; do not duplicate a still-running team; enforce deadline and usage first. Continue from the first incomplete reviewed task. Stay quiet during unchanged cooldown checks. Disable automation only on actual completion or owner cancellation.
