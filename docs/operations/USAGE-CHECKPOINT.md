# Usage-aware HMS continuation

Owner instruction: when any applicable Codex usage window has 10% or less remaining, checkpoint HMS.md and stop new work; resume no earlier than 5 hours30minutes later and only with recovered usage.

State: WAIT_COOLDOWN

Owner exception23October2026: explicitly authorised immediate existing-slice Hostinger deployment and answered yes to overriding cooldown for that deployment. Deployment completed as restricted synthetic preview; general development still respects this original deadline. Do not reset/extend it or infer cancellation of future usage stops. HOSTINGER-PREVIEW.md records deployment evidence. Resume remaining development after deadline with all applicable windows above10%; do not redeploy on every heartbeat.
checkpoint_at_utc: 2026-10-23T05:02:15.039512+00:00
resume_not_before_utc: 2026-10-23T10:32:15.039512+00:00
resume_not_before_ist: 23 October 2026, 4:02:15 PM IST
automation_id: continue-hms-after-usage-cooldown
automation_interval_minutes: 330

Threshold snapshot:6% minimum remaining. Agents were told to stop and checkpoint. At08:34Z manual Continue, minimum remaining recovered55%, but the original deadline remains active. No reset credit consumed. Native heartbeat updated in place; actual wake is best effort and may be later than earliest deadline.

Preserved work: first local API-backed login/dashboard/patient/appointment/bed/admission/master-summary slice; OpenAPI/docs/CI/local-container groundwork; exact tests and open review in HMS.md and ledger. First resume task: fix admission bed selector's first100-record limit with regression coverage, then finish independent review/CI. Full clinical/finance/MCP/backup/cloud work is not complete. No new feature fixes during cooldown.

Before substantive work and bounded task boundaries, coordinator calls get_usage_limits and prefers rateLimitsByLimitId. remaining=100-usedPercent. Check primary and secondary applicable windows. A low weekly window may require longer than330minutes; never resume below threshold or consume reset credits automatically. Unknown usage means do not start a new large work unit until visibility returns.

At threshold: notify agents to checkpoint, stop assignments, preserve their changes/evidence, update HMS.md/plan.md/ledger, run safe bounded checks, commit/push if possible and record actual failures rather than claiming success. Record UTC checkpoint and earliest resume. Preserve an unelapsed deadline on repeated low readings. Update the same native heartbeat rather than create duplicates. No Windows scheduled credential-scraping script is used; native scheduling has authenticated usage access. Scheduler requires local PC/Codex/repo availability and cannot guarantee an exact wall-clock wake.

On wake: read this state, Git status/log and implementation ledger; do not duplicate a still-running team; enforce deadline and usage first. Continue from the first incomplete reviewed task. Stay quiet during unchanged cooldown checks. Disable automation only on actual completion or owner cancellation.
