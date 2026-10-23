# Network B2a — coherent read-only policy snapshot

Status: frozen bounded internal service after coordinator and independent pre-code security review; no implementation yet. Consumes the [frozen network contract](network-access-contract.md) and [implemented B1 schema](network-foundation-schema.md). This is the first internal B2 unit; it adds no HTTP endpoint, capability advertisement, operator command, middleware wiring or portal protection. Existing39implemented/sevenplanned operations remain unchanged.

## Intent and files

Create `backend/apps/core/network_snapshot.py` and `backend/tests/test_network_snapshot.py` only. Goal: obtain one coherent stored-policy graph and select candidate/fallback without writes or permissive repair. This service will later support independently authorised API/edge adapters. The frontend never calls it directly.

Exact public interfaces:

- `NetworkStateUnavailable(Exception)`: generic unavailable/corrupt-state message; no raw DB exception/policy/header disclosure. Future adapters map this to503; this unit does not emit HTTP responses.
- Frozen dataclass `NetworkSnapshot`: `revision:int`, `bound_owner_id:UUID|None`, `confirmed_policy:dict`, `effective_policy:dict`, `pending_change_id:UUID|None`, `pending_status:str|None`, `candidate_policy:dict|None`, `activated_at:datetime|None`, `rollback_at:datetime|None`, `activation_revision:int|None`. Policy dictionaries are independent detached canonical copies, including from one another. Pending status is exactly `pending`, `expired_unreconciled` or null.
- `load_network_snapshot(now: datetime) -> NetworkSnapshot`: require an aware datetime (invalid caller value raises ValueError), query singleton1 with pending change and its preview joined in exactly one SELECT/consistent statement snapshot for baseline and pending graphs. No transactions requiring row locks, caches, settings/environment lookup, authentication lookup, extra relationship queries or state mutation. Missing state, unavailable DB, invalid saved data or broken links raise NetworkStateUnavailable. Capture DB errors at the service boundary; never return an unrestricted fallback.

## Required validation before selection

1. State ID1 and strict safe revision1..9007199254740991; validate confirmed policy and digest with B1 `validate_saved_policy`. No owner configuration is read: stored policy remains enforced even when management owner configuration is absent/malformed/mismatched. Null stored owner is permitted for a baseline without pending change.
2. If no pending pointer, return confirmed as effective; every pending field is null. Terminal history not referenced by the singleton has no effect.
3. If pending exists, validate *both* candidate and fallback, even after deadline; fallback canonical data/digest must equal confirmed. Pending owner must equal nonnull state.bound_owner_id; base_revision+1=activation_revision=state.revision. Status must be pending; finished_at/terminal_revision/confirm_expected_revision/revert_expected_revision must all be null. Broken pointers or a terminal/foreign change are unavailable, not a guessed rollback.
4. `activated_at`/`rollback_at` are aware and exactly300seconds apart. A clock before saved activation returns unavailable (fail closed under backwards clock movement); clock synchronisation is an operational prerequisite. At now<rollback_at select candidate/statuspending. At equality/after select fallback/status expired_unreconciled without modifying stored revision, pointer, status or events.
5. Every effective pending change originates from its saved preview. Null preview is allowed for terminal OOB history only, not a currently referenced pending candidate. Validate change.preview_id and preview.result_change_id reciprocal pointers, preview.owner/actor/base_revision/policy against change, and matching session_digest/epoch/operator_version/verified_ip/environment_digest. Bindings are storage consistency checks, not a check that the initiating actor is still active; revocation must not silently change a candidate before its fixed deadline.
6. SHA bindings are64lowercasehex; epochs0..safeMax, operator versions1..safeMax; stored IP is canonical resolver identity. Preview expires_at=created_at+300seconds, and created_at<=activated_at<expires_at. Preview candidate/digest matches the change. Do not extend either deadline. Normalisation display/reason/history projection and current authority/fingerprint checks belong to later B2 mutation/API services.

All policy validation precedes choosing an allowed path. This service makes no environment-AND-network decision yet; current resolver/environment middleware remains unchanged until full integration. An OS/DB operator can recompute hashes; no tamper-proof archive claim follows. Returned rules are internal sensitive data and require the future network-operator ceiling before HTTP projection.

## Pre-code scenarios, threats and tests

Scenario review: initial unbound singleton yields the confirmed overlay; valid owner-bound pending graph yields candidate, exact deadline yields fallback, all reads leave DB untouched. Management configuration changes/revocation do not erase stored restrictions. An unreferenced terminal history row does not block the confirmed baseline.

Threat review: fail closed on missing/corrupt policy, altered digest, foreign owner, terminal pointer, missing or swapped preview, reciprocal link mismatch, swapped bindings, malformed dates or revision chain. Validate a corrupt candidate even when it has logically expired. Read graph once to avoid mixing old state with newly changed pending records. No private event/session/IP binding is returned to an ordinary user by this internal unit.

RED-first test names/assertions, before implementation:

- `test_initial_snapshot_is_one_query_and_write_free`: explicit fixture singleton, one SELECT; policy dictionaries are detached; no create/update/event/profile change.
- `test_missing_or_unavailable_state_does_not_create_or_allow`: missing singleton and simulated DatabaseError raise NetworkStateUnavailable; no GET repair.
- `test_pending_boundary_selects_fallback_without_worker_or_write`: before/equality/after fixed rollback; unchanged state/change/events/revision; canonical saved candidate/fallback validated.
- `test_corrupt_saved_policy_and_pending_links_fail_closed`: parametrise all scalar/digest/owner/status/link/binding/time cases above, using actual persisted rows/updates where constraints permit, and isolated saved-row probes for DB-impossible scalar shapes. Do not weaken DB constraints to manufacture corruption.
- `test_expired_corrupt_candidate_still_fails_closed`: no silent fallback over damaged graph.
- `test_owner_environment_does_not_disable_stored_restrictions`: absent/invalid owner settings leave valid stored selection unchanged; no authority inferred.
- `test_naive_clock_is_rejected_and_backwards_clock_is_unavailable`: distinguish invalid caller input from corrupt/unreliable decision context.
- `test_unreferenced_history_is_not_an_effective_policy`: no unnecessary terminal-history query or failure.

Run targeted tests RED, implement minimum service, targeted GREEN, fresh independent source/probe review, then coordinator actual PostgreSQL/full-backend/migration checks. A one-query assertion is not a load benchmark; no request enforcement or race-safe mutation claim until B2 integration. Root alone updates living docs, commits/pushes and verifies remote SHA. No live DB schema/policy/operator/edge changes.
