# HMS developer and coding-agent instructions

Read [HMS.md](HMS.md) and [plan.md](plan.md) before work. Latest explicit user instructions take precedence. Implementation is owner-authorised; read docs/implementation/ledger.md and the active slice contract before assigning or repeating work. Coordinator alone commits/pushes shared-checkout changes.

## Mandatory workflow

1. Planning first: complete affected page/action/data/API/permission/failure/acceptance design before production code. Follow plan.md's design gate; do not treat unchecked plans as delivered features.
2. Multiple pre-code checks: scenario/permission review, threat/abuse review and test design; write/run failing executable tests where possible before implementation. Then code and run post-code verification.
3. Use installed Superpowers skills and UI/UX Pro Max when applicable. Read relevant SKILL.md; do not invent a skill result. Do not let a generated recommendation override user requirements.
4. Every completed change set must update HMS.md in the same commit: detailed affected sections, implementation status, decisions, interfaces/data/security changes, evidence and a new change record. Update plan.md task status and affected planning in the same commit. No false implementation/test claims.
5. Review and verify; commit and push every completed change set to https://github.com/prarit0097/HMS-MANAGEMENT. Verify remote SHA. No force push, unrelated files, remote overwrite, secrets or real patient/lead data. If blocked, preserve local work and report accurately.

## Security and scope

- API-first is mandatory for the entire app: define versioned OpenAPI/page-action contracts before coding, expose every user capability through an authorised API, and test it independently of the UI. Frontend is an API client, never an authoritative clinical/financial database writer. MCP/jobs reuse the same contracts/services and permission ceiling; no hidden UI-only or adapter-privileged mutation path. Internal service reuse does not require HTTP loopbacks.
- End-user UI must be simple, professional and clear: familiar hospital labels, consistent navigation, role-focused work, essential fields first, plain errors and clear next steps. Keep implementation jargon/decorative complexity out; preserve safety-critical context. Validate representative staff tasks and fix confusing steps before release.
- Security is a release gate. All UI/API/MCP/file operations enforce authenticated least-privilege organisation/branch/data access. Master admin does not automatically gain clinical-signing rights.
- Enforce effective IP policy on backend paths through explicitly trusted proxies; no direct-origin/forwarded-header bypass or automatic per-visitor whitelisting. Recovery is audited/out of band.
- MCP reuses business services; no arbitrary SQL/shell/URL tools, no unaudited high-impact writes. Compatible client connections need scoped authorisation and a permitted network path.
- No silent deletion of signed records/final bills; use traceable corrections. Transactions/constraints must protect beds, stock and money under concurrency/retries.
- Backups/imports/exports are privileged workflows. Portal backups have dependency manifests and cannot blindly restore shared data.
- Cloud production is separate from GitHub push. No production deployment or paid resource is implied by a documentation task.
- Expandable capacity; no 100-bed hard limit. Future call-center integration details/build are deferred. Rented premises/norms are owner-managed, not development blockers.

## Handoff

Owner's usage rule: coordinator checks authenticated get_usage_limits at start and bounded work boundaries. If any applicable window has <=10% remaining, stop new work/assignments, checkpoint active agents, update HMS.md/plan.md/ledger, safely commit/push, record checkpoint UTC and earliest resume+330minutes in docs/operations/USAGE-CHECKPOINT.md. Resume only after that deadline with all applicable windows >10%; do not reset an active deadline or consume reset credits. Native heartbeat id continue-hms-after-usage-cooldown handles best-effort Windows-app continuation; scripts/usage_guard.py and Check-Usage.ps1 evaluate tool-supplied snapshots without scraping credentials. Do not duplicate a still-running team.

Report what changed, tests actually run, unfinished checks and verified push SHA. Leave work recoverable. Maintain explicit planned/implemented/verified/deployed distinctions in HMS.md.

An explicit later owner instruction can waive an existing cooldown; record the instruction/time and authenticated usage in checkpoint/ledger, preserve history and update the same heartbeat. Recovery alone never waives a deadline. Latest recorded owner general-resume override:23October2026 at17:44:21Z; future <=10% stops remain mandatory.

Latest owner scheduling override:23October2026 at22:04:30Z, resume24October04:30AM IST (23October23:00Z) only if authenticated all applicable windows>10%. This replaces the former23:51:54.627991Z deadline; original stop remains historical. Future fresh<=10% stops still require330minutes. First resumed task is ICTHospital source/licence/feature comparison against plan.md.

Latest owner resume:24October2026 at05:10:42UTC, primary100%/weekly69%remaining after saved05:04:44deadline elapsed. No waiver/reset credit needed. Resume remainingnetworkB2integration; research/B1/B2a are alreadycomplete. Futurefresh<=10%stillrequires330minutes.

Latest fresh usage stop24October2026 at05:36:20UTC primary10%/weekly55%remaining. No new implementation before11:06:20UTC (4:36:20PM IST), then only all windows>10. Prior05:10resume predates this stop. All specialists completed. Read latest checkpoint/ledger and currentGitCI; first incomplete GET timing boundary, remaining reviews/races/UIbrowser/edge blockers, no repeated initialdeployment.

Scheduled resume24October2026 at11:07:26UTC after11:06:20deadline elapsed, authenticatedprimary100%weekly55%, guardcontinue. No waiver/resetcredit;05:36stop remains historical. Futurefresh<=10stillrequires330minutes.

Latest explicit owner resume24October2026 at16:43:13UTC primary97%weekly39%remaining waives ONLY17:05:08deadline from11:35:08stop(primary9weekly41). Priorstop/history preserved; no resetcredit. Futurefresh<=10stillrequires330minutes. Firstunfinished: post-CSRF actualPG/source review, browserapply/keep/revert/history/keyboard, activeoriginprobes andfinaledgeacceptance.

Fresh authenticated stop24October2026 at17:29:37UTC primary10%weekly26%remaining. No new implementation before22:59:37UTC (25October04:29:37AM IST), then onlyallwindows>10. Prior16:43ownerresume predates this stop. Source5aee4d29939161e09f53e862f407325daad02589 pushed/remoteverified; CI40115929521 success658PG168subtests/132frontend/19root15edge/schema/docs. Dormant3model documentfoundation verified, no API/grants/storage/scanner/ready/download/live migration. All specialistscompleted; nextmetadata-contract.md is DRAFT requiring freshreview+remaininggates then OpenAPI/pageaction/servicefreeze before RED/code. Preserve originalpreview47b3618 and all otherVPSapps.

Owner resume25October2026 at06:44:43UTC primary96%weekly99%remaining after22:59:37deadline elapsed; no waiver/resetcredit. Historical17:29:37stop preserved. Resume metadata DRAFT freshreview/transaction+limiter/UIgates before contract/OpenAPI freeze andRED/code; do not repeat completedfoundation/network/reception/Encounter/deployment. Futurefresh<=10 requires330minutes.

Owner explicitly PAUSED25October2026 at07:25:27UTC to preserve remaining usage(primary19%weekly87%). No implementation/assignments/reviews or automaticresume until later explicitownerresume. AutomationPAUSED; this manualhold creates no330min deadline. Source66bfa10160eae5342b0b64a601ad05b992d40753 verifiedCI40171838097SUCCESS1276PG168subtests/132frontend/19root15edge/schema/docs. B1purehelperscomplete, B2serviceplan/review DRAFT andadmissioncontract notsaved; reconcile exactgates afterownerresume. Latestcheckpointdocs state authoritative. Preservepreview47b3618/otherVPSapps.

Owner explicitly resumed26October2026 at01:18:20IST (2026-10-25T19:48:20Z), authenticatedprimary29%weekly57%remaining. This lifts25October07:25:27manualhold; no cooldown waiver/resetcredit. Historical pause/source evidence remains. SameheartbeatACTIVE; resume B2a exactadmissioncontract/review before RED/code. Futurefresh<=10stillrequires330minutes.

Fresh authenticated stop2026-10-25T20:22:58Z primary10%weekly55%; no new work before2026-10-26T01:52:58Z (26October07:22:58AM IST), then allwindows>10. Earlier ownerresume predates stop. Owner now explicitly authorises latest implemented code deployment to existing HMS preview plus MD updates; this is FIRST pending task aftercooldown and exactCI/VPS/config/backup/rollback/security gates. No deployment occurred this turn; lastrecordedpreview47b3618/sourceb5ea87e remain distinct. Preserve otherVPSapps/keys/Basicnetworkisolation. B2a development later.

Owner26October01:56:25IST mandates every completedcodechange: verifiedGitpush, reviewed/testedHMSpreviewdeployment/liveverification, thenMDrecords. Preserve otherVPSapps/security/backup/rollback; doc-onlyupdatesdo not restartunchangedapp. Maximumavailableparallelagents(current4slotsincludingroot,3children) disjointtasks; rootaloneGit/VPS. Explicit03:30AMIST26October (25October22:00UTC) replacesONLYcurrent01:52:58UTCdeadline, original20:22:58stop retained; primary9weekly54at20:26:25UTC. No workbefore03:30 andonlyallwindows>10; futurefresh<=10requires330min. Firsttasklatestcodepreviewrollout; no resetcredits.
