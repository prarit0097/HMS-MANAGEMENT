# Profile contract-data and structural schema plan

> Scope selected by coordinator17November2026 under owner-authorised planning/testing workflow. This permits only documentation data artifacts, not production parser/OS/SQL/ingestion implementation or activation.

Goal: make the reviewed root-profile, AVCTL-only projection and14-key launch data shapes executable as structural contracts, with explicit tests demonstrating where schema acceptance is insufficient. JSON artifacts live under docs/implementation, are not imported by the app and do not change the50HTTP operations. Other-role projections/child launch remain deferred.

Affected artifacts: document-ingestion-profile-data-contract.md (normative proposed data/semantic boundaries); schemas/ingestion-profile-data-v1.schema.json (Draft2020-12 local-only$defs rootProfile,avctlProjection,launchRecord); fixtures/ingestion-profile-data-v1.json (synthetic bases and mutation/wire cases); measured evidence JSON; HMS.md/plan.md/ledger/USAGE. No app source/dependency/CI/service/key/role/profile is added. Documentation-only publication does not restart unchanged preview.

## Pre-artifact checks and execution

- [x] Independent scenario/threat review reconciled exact closed fields, sevenUID/twelveGID distinctness, strict supplementary/peer mapping and deterministic ProjectAvctl(P,B) byte equality. AVCTLprojection only; no invented7daemon lifecycle.
- [x] Independent test design separates structural rejection from canonical/semantic/OS limits, including integralfloat, aliasing and wrongpeer/hash acceptance. No productionauth claim.
- [x] Synthetic fixture catalogue written before schema:71prepared cases plus5raw-wire limit examples, no real IDs/namespace values or allocation instructions.
- [x] Literal RED on17November: ignored local runner loaded jsonschema4.26.0, parsed/applied all71fixtures, then failed only missing schema artifact; application tests0. This is one missing-artifact failure, not71executed security test failures.
- [x] Write exact reviewed structural schema, no remote$refs/customruntime functions.
- [x] Run metaschema and all fixtures; classify structural positives/negatives separately from schema-valid limitation examples. Do not mislabel shape validation as wire/OS verification.
- [x] Independent schema/fixture/source review, reconcile findings and rerun affected checks.
- [ ] Full documentation/API/whitespace/stagedcredential validation, living docs in same commit, push and exactremoteSHA verification. Record CItruthfully; no WIP/runtime deployment.

Execution command in existing ignored checks environment: `.local/checks-venv/Scripts/python.exe .local/check_profile_contract_20261117.py`. The ignored runner is one-shot documentation tooling, not a shipped parser/helper; it applies public fixture set/remove mutations and uses Draft202012Validator on local$defs, then parses rawwire limit examples with ordinary json.loads to demonstrate information loss. Validators must never fetch remote resources or inspect VPS/settings/credentials. Existing package environment observedPython3.13.5/jsonschema4.26.0; no install/pin change made. Public fixtures plus schema are inspectable source of each expected structural result.

Reference: [JSON Schema2020-12 validation](https://json-schema.org/draft/2020-12/json-schema-validation). Mathematical integer permits zero fractional parts; schema cannot prove canonical integer spelling, duplicate-key absence, raw byte bounds, cross-document mappings or OS provenance. Root/profile/projection canonical wire and semantic/authority gates remain mandatory and unimplemented. No new unused facts helper is authorised.

## Measured result

[Evidence](../operations/document-profile-shape-evidence-2026-11-17.json): RED missing schema with71preparedcases, then GREEN71cases(55expectedrejections/9limitpositives) plus5rawwirelimitexamples0.0999s,0applicationtests. Final independent artifact review found no Important defect. Allrefs local; lexical/crossfield/OS limits remain intentionally outside structural validation. Publication gate below is recorded separately from these local results. No production leaf or ingestion capability is frozen.
