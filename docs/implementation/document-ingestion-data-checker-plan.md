# Repository ingestion-document checker: implementation and scoped delivery

> Use Superpowers TDD/review/verification. Scope selected17November2026 for developer tooling only; no runtime/OS/SQL ingestion authority. Exact pre-code scenario/threat/test review below must finish before implementation.

Purpose: turn published profile-contract examples into an enforced repository/CI gate, rather than add an unused runtime facts helper. No hospital page/action/permission, API/MCP/job or app module changes. Every example remains synthetic. Structural schemas remain the existing local-only Draft2020-12 artifacts.

Files: new scripts/check_ingestion_profile_data.py; scripts/tests/test_ingestion_profile_data.py; fixture catalogue semantic_valid expectations; checks workflow explicit CLI step; infra/requirements-checks.txt explicit existing jsonschema4.26.0 pin; living docs/evidence. No changes to backend/frontend/hostinger/edge runtime files.

## Frozen tooling interface after review

`validate_bundle(profile_raw:bytes, projection_raw:bytes, launch_raw:bytes, schema:dict) -> None`: fixed generic ValueError subclass on any invalid documentation bundle; no returned authority object. Parse exact canonical ASCII compact sorted JSON objects with duplicate-key, float/exponent/nonfinite, lexicalnegativezero, BOM, whitespace/newline/escape and rawbyte limit rejection (P8192/Q2048/L2048). Never reflect values or low-level exception text. Bounded input and recursion errors fail closed.

Validate local schema shapes with jsonschema, reject nonlocal$refs before any resolution, no network/repository imports of runtime settings. P requires seven distinct UIDs/twelve distinct GIDs, primary map equality and exact sorted role supplementary sets. Q must equal exact deterministic ProjectAvctl(P,originalPbytes), including sourcehash/peer identities/copies. L must match P/Q installation,boot,uid,gid,suppgroups,unit,cgroup,host user/pid/cgroup namespaces; mnt remains dynamic positive inode only, PID/start/restoreepoch/manifest cannot be authenticated from examples. Data consistency never proves OS or current Control authority.

`check_catalogue(root:Path)->dict` reads ONLY fixed docs schema/fixture paths below trusted developer-selected repo root, bounded schema64KiB/catalogue256KiB. Validate representative71structural cases and5raw-wire examples with their expected structural/semantic booleans; add semantic_valid metadata rather than reclassify structural limitations. Cases with coherent forged livefacts remain semantically valid and never authority. CLI optional--root, returns0 on exact expectations/1 otherwise; fixed generic diagnostics no supplied values/paths or exception dumps. No writes, shell/SQL/URLs or real profiles/credentials.

## Tests and safety before code

- [x] Independent scenario/permission, threat/abuse and test review accepts narrow tooling boundaries.
- [x] Tests first: canonical edge cases, projection/hash/identity/group errors, data versus OS authority, nonlocalref denial, fixedpaths/readbounds, privacy and real catalogue+CLI. Record literal missing-module RED after dependency/fixtures prerequisites pass.
- [x] Minimal implementation+CI consumer, then focused GREEN/full root checks+schema/docs and fresh independent review. Do not rerun backend/frontend without runtime change/new concern; pushCI independently runs its configured jobs.
- [x] Every completed code change updates HMS/plan/ledger, verified push/exactCI, scoped HMS-only tool deployment and actual validation, then final docs. No WIP deployment.

## Scoped VPS tooling deployment (review before execution)

This is a developer-tool release, not an application runtime release. After source review/tests/exactGitpushCI, prove runtime diff against e7ab28f empty for backend/frontend and deployed hostinger/edge paths. Deploy only committed checker/schema/synthetic fixtures to a NEW root-private literal /opt/hms/validation/profile-data-check-20261117-<shortSHA> directory, never overwrite current app release. Preflight checks resolved directory under HMS validation, absent target, preview symlink/service and suitable existing Python/jsonschema. Prefer existing compatible validation environment. If absent, separately review isolated tool-only dependency environment; no live/global package change or install merely to suppress a validation failure.

Verify uploaded Git-blob hashes and exact checker output on synthetic catalogue; compare preview current symlink/service before/after, no app restart/schema/settings/key/policy/auth change or other-app mutation. No supported live document calls. Tool deployment evidence must distinguish code delivered to private validation path from unchanged e7 application source. If the environment is unavailable, preserve completed source and report pending validation honestly; do not claim production deployment from Gitpush. No paid resources or extra server.

## Pre-code review disposition17November2026

Accepted bounded tooling scope after independent scenario/threat/test review, with required fixes: reject all $dynamicRef/$recursiveRef and all nonlocal $ref before validator evaluation, reject nested $id/$schema and use fresh wrappers containing only local$defs/ref so no untrusted base scope can trigger retrieval. No arbitrary registry/URL resolution; test no network call. Reject symlink/escape/nonregular fixed inputs before read, bound descriptor reads and fail generic on races/errors; use nonblocking/nofollow flags where supported. This developer gate is not a privileged OS profile loader or proof of race-free filesystem authority. CLI output closed status/count keys only, no fixture IDs/paths/values/exception text.

Focused semantic tests must mutate P and independently rederive Q/relevantL copies, so UID/GID/membership rejection is not accidentally only stalehash rejection. Structural catalogue cases remain representative and may have multiple failure causes. Report semantic_valid expectations separately: forged but coherent OS facts stay data-consistent with authority_checks=0.

Closed report keys: status,structural_cases,structural_rejections,semantic_cases,semantic_rejections,wire_examples,wire_rejections,authority_checks. Expected current catalogue71/55/71/63/5/5/0; counts are verified results, not hardcoded permission or throughput. Failure output fixed status=failed/code=invalid_contract_data. Canonical helpers return no grant. Existing server system jsonschema4.10.3 was observed (first inline version probe had quoting failure, corrected via stdin; no change); existing private validation venv has no jsonschema. Prefer stable Draft202012 subset with static closed-reference guard and wrapper definitions so both existing server4.10.3 and local/CI4.26 can be tested, rather than installing packages. If actual compatibility fails, do not install or alter the server to force success; preserve/report pending tool validation.

## Tests-only checkpoint

17November12:55:14UTC threshold stopped implementation before it began. Saved19testmethods and71semanticmetadata(8true63false)+5wireexamples. ActualliteralRED is one loader ModuleNotFoundError for missing checker, not19executed cases. NoGREEN/CIstep/pin/module/tooldeployment. Resume only after18:25:14UTC andsafequota. Nextreview savedtests then minimal implementation; noWIPdeployment.

## Source acceptance18November

Missing-moduleRED is closed by implementedconsumedCItool. Root40scripts methods27.137s/39pass1WindowsFIFOskip plus CLI71/55structural,71/63semantic,5/5wire,authority0. Source/security/testreviews clear; LinuxFIFO/jsonschema4.10.3 and exactCI/private tool deployment remain OPEN. Backend/frontend/hostinger/edge runtime diff e7 empty, so no app release swap/restart is within this scoped delivery.

## Final source and scoped delivery acceptance18November

Exact source2cb316d CI44259948825 allthreejobsSUCCESS, decoded40root/38edge/2076PG7skips1218subtests/132frontend plus schema/docs. Actual privateVPS Python3.12.3/jsonschema4.10.3 ran21tests0skip (includingFIFO) and exact71/55/71/63/5/5/0 CLI report. FiveGitblobhashes verified at new rootprivate target; no packages installed, no app restart or release swap. e7 application PID/start/symlink unchanged. Tool source/delivery complete, no OS/runtimeauthority or ingestion capability. [Delivery evidence](../operations/document-profile-checker-delivery-evidence-2026-11-18.json).
