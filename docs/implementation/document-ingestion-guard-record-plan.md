# S1 guard-record facts decoder implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers `executing-plans` or `subagent-driven-development` task-by-task after freeze. Coordinator alone commits/pushes/deploys.

**Status:** FROZEN leaf-only, 13 November2026 after independent scenario/threat/test-design approval, parent timestamp/restore alignment and coordinator scope review. Parent ingestion remains UNFROZEN; no implementation/test/activation claim.

**Goal:** Decode bounded guard JSON into immutable facts for a future trusted OS reader, without establishing authority.

**Architecture:** One unused pure function and one frozen facts dataclass. Prefer stdlib JSON with duplicate detection and explicit field validation; a general schema dependency adds unnecessary machinery, while an OS reader would entangle a separately reviewable trust boundary.

**Tech stack:** Python stdlib `json`, `uuid`, `datetime`, `dataclasses`, `re`; tests use `unittest`.

**Parents:** [Retention version1 grammar](document-ingestion-retention-contract.md), [guard authority](document-ingestion-guard-authority-contract.md). The exact six-fractional-digit UTC spelling below is a proposed narrowing of their finite-UTC rule: coordinator must align those parent paragraphs before leaf freeze. No broader parent freeze follows.

## Scope and interfaces

Future files: `backend/apps/core/document_guard_record.py` and `backend/tests/test_document_guard_record.py`. Coordinator updates HMS.md, plan.md and ledger.md with actual evidence. No pages/actions/API/permissions/schema/settings/dependencies/callers change; existing S0/B3 and 50 HTTP operations remain closed and unchanged. No filesystem, OS, network, DB, authentication, context, clock sampling, guard creation, flags or user capability.

```python
@dataclass(frozen=True)
class GuardRecordFacts:
    version: int
    installation_id: UUID
    epoch: UUID
    mode: str
    reason: str
    recorded_at: datetime
    manifest_sha256: str | None

def parse_guard_record(raw: bytes) -> GuardRecordFacts: ...
```

This is the sole public parsing function. The dataclass has no custom methods, factory, `allowed` property or authorisation operation. Constructing facts directly proves nothing. It is **not** `GuardObservation`: no trusted provenance, invocation identity or monotonic boundaries are manufactured here.

Require `type(raw) is bytes` and `1 <= len(raw) <= 4096` before decoding. Reject mutable buffers, views, subclasses and coerced input. Decode strict UTF-8, reject BOM, then parse one JSON object with no trailing non-whitespace. Standard JSON whitespace, member order and escapes are allowed; canonical requirements apply to decoded strings, not raw JSON spelling. Reject duplicate keys at every object level (including escaped-equivalent keys), nonfinite constants, extra/missing members and non-object roots. No defaulting or coercion.

Exactly seven members:

| Member | Exact decoded acceptance |
|---|---|
| `version` | `type(value) is int`, equal to1; bool/float excluded |
| `installation_id`, `epoch` | Exact str; `str(UUID(value)) == value`, lowercase hyphenated36-character form; no UUID-version/ordering restriction |
| `mode` | Exact str, `active` or `closed` |
| `reason` | Exact str, `fresh`, `maintenance` or `restore` |
| `recorded_at` | Exact str matching ASCII `YYYY-MM-DDTHH:mm:ss.ffffffZ`; valid Gregorian date/time, years0001–9999, seconds00–59; return aware `datetime` with `timezone.utc` |
| `manifest_sha256` | None or exact str of64 lowercase ASCII hex characters |

Return UUID objects, aware datetime, unchanged strings and version. No age, current-time comparison, hash verification or cross-field authority inference. All six mode/reason combinations and either manifest shape decode, including **active+restore**: these are syntax-valid facts only. Future authority MUST separately reject `reason=restore`, require active mode, trusted fresh OS provenance and matching locked Control/current permissions; this helper cannot reopen restore state or grant access. Parent authority wording must preserve that explicit rejection at alignment.

Every invalid input raises exactly `ValueError("Invalid guard record.")`, suppressing exception chaining and supplied values. Normalize only expected validation/JSON/Unicode/UUID/date failures and bounded-input `RecursionError`; do not catch `Exception`, memory exhaustion or process-control failures. Private helpers only; no logging or input echo.

## Scenario, threat and test matrix

| Risk/scenario | Executable assertions required |
|---|---|
| Valid independent fixtures | Literal synthetic UUID/timestamp/hash JSON; null/hash; all six state pairs; reordered/escaped keys; UTC microseconds and frozen-field assignment failure |
| Size/mutability abuse | Empty,4096 valid bytes padded with whitespace,4097 bytes, multibyte byte-count boundary; wrong exact types/subclasses |
| Parser ambiguity | Invalid UTF-8/BOM, malformed/truncated JSON, trailing object/garbage, duplicate/escaped duplicate, every missing/extra key, scalar/list/null roots, nested structures, bounded recursion |
| Type/coercion confusion | Each field: bool/int/float/null/list/object substitutions; version0/2/1.0/true; NaN/Infinity/-Infinity and overflow-number values rejected |
| Canonical facts | Uppercase/compact/braced/URN/invalid UUIDs; wrong enums/case; invalid dates/leap days/leap seconds, offsets/lowercasez/missing or wrong fraction; uppercase/short/long/nonhex hashes |
| Authority confusion/leaks | Active+restore returns facts only; no observation/authority API, caller or IO imports; every rejection exact error with no chained input diagnostic; directly constructed facts have no authority semantics |

## Execution gates

- [x] Align parent timestamp/restore wording; independent scenario/permission and threat/test reviews, then coordinator leaf-only freeze before code.
- [x] Write synthetic unittest matrix importing the absent module. From `backend`, record interpreter and run `python -m unittest discover -s tests -p test_document_guard_record.py -v`; retain literal missing-module RED before production.
- [x] Implement only this contract; run identical portable command GREEN. Fresh independent source/test review verifies independent fixtures, expected exception boundaries and no callers/side effects.
- [ ] Coordinator runs source-compatible pinned Django5.2.18 full actual isolated PostgreSQL regression/check/no-migration-drift and required schema/repository checks; record commands/results and isolation. No environment repair or live fallback; portable GREEN alone is insufficient.
- [ ] Coordinator commits/pushes, verifies remote SHA and exact-SHA CI, then reviewed source-only HMS preview rehearsal/backup/rollback/live preservation/postrestore and same-change MD evidence. No guard provisioning, migration, ingestion invocation or flag activation. Docs-only publication does not restart unchanged runtime.

Self-review: exact interfaces/types/errors and bounded parsing are specified; parent alignment and independent reviews remain open. No code or executable test was written/run for this draft. Shared rolling300minute reserve applies; stop new work at<=10%, preserve checkpoint/history, no resets/account/model bypass.

Coordinator ruling: exact facts-only decoding is independently testable and needed by the planned trusted reader; no provenance or permission inference belongs here. Strict timestamps narrow the parent grammar consistently. Active+restore must parse as facts and never grant authority. Independent reviewer found no leaf blocker; root completed both conditional parent alignments before freeze. Initial RED and all implementation/delivery gates remain open.

## WIP checkpoint —13 November2026

RootmissingmoduleRED beforecode; actual18portablegroups0.380s andindependentreview18groups0.322s/no findings. Sourceimplemented andportableverified ONLY, full actualPG/check/drift/requiredchecks/exactCI/reviewedpreview/live/postrestore remainunchecked; not complete/deployed. See [checkpoint](../operations/document-guard-record-checkpoint-2026-11-13.json). No parentfreeze/capability or OSguardreading claim.
