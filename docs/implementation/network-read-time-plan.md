# Network read timestamp correction and remaining race plan

Status: FROZEN by coordinator after exact contract/scenario/threat/test review and observed real-API RED; no production change or deployment. Root alone approves the code gate, maintains HMS.md/plan.md/ledger, commits, pushes and executes actual PostgreSQL/VPS checks. Existing 520 PostgreSQL tests and 12 network races are historical evidence and are not repeated merely for this proposal.

## Investigated fault and affected contract

`read_network_state` currently authorises a coherent snapshot at the authority helper's first timestamp, independently captures response `server_time`, then authorises again but discards the final snapshot. If the rollback deadline occurs between those moments, it may return the earlier candidate/status `pending` alongside a `server_time` at or after `rollback_at`. Backend enforcement independently selects fallback, so this is an incorrect management projection and countdown, not an enforcement bypass.

Preserve the frozen NetworkState schema, exact API, owner/operator/MFA ceiling, graph selector, fixed deadlines and no-GET-write requirement. Change only `backend/apps/core/network_access.py:read_network_state`; add literal regressions in `backend/tests/test_network_access_read_time.py`. No schema/migration/new permission/endpoint/UI/environment/edge changes.

## Exact service/projection timestamp contract

1. Capture an aware `started_at = timezone.now()` immediately before initial current authority and call `require_network_operator(context, now=started_at)`. Its coherent snapshot is preliminary for this read; retain the authorised owner ID.
2. Read that owner's bounded display label and the current validated environment. These operations may take time; do not reuse the preliminary snapshot as response data.
3. Capture `selected_at = timezone.now()` after those reads. If `selected_at < started_at`, fail closed with `network_policy_unavailable`503; never move a response clock backward, repair state or silently clamp time. Existing selector still rejects a clock before stored activation independently.
4. Perform fresh final `require_network_operator(context, now=selected_at)`, including current actor/session/epoch/enrollment/proof, owner/master/operator, current environment fingerprint/resolved IP and current effective path. Use the coherent NetworkSnapshot returned by THIS final authority call. Its owner must equal the initially authorised display owner; mismatch fails owner-unavailable503. Revoked authority/path continues to deny with the existing precise code, never returns policy.
5. Project `server_time = selected_at` and all revision/confirmed/effective/pending fields from the final authorised snapshot selected at exactly `selected_at`. At `selected_at < rollback_at`, candidate/pending; equality or after, fallback/expired_unreconciled. Do not load another policy snapshot after this decision, reuse preliminary policy dictionaries, rewrite revisions/pointers/events, or reconcile on GET.

`server_time` describes the explicit selection/authorisation instant; it does not promise that the clock or policy can never change after that instant while HTTP bytes are sent. This is the same bounded request semantics as the existing read-only selector. Fresh proof is checked after the potential owner-label wait. No new `require_path=False` or caller-supplied timestamp enters an HTTP body or public API.

## Pre-code scenario and threat review

Positive: synthetic entitled owner manager reads live candidate before rollback and logical fallback at/after rollback, with stored revision/pointer unchanged. Exact boundary is server-controlled, including a boundary crossed during owner-label/query work. An unrelated terminal/revision update between preliminary and final reads returns the final coherent authorised snapshot rather than old/new fields mixed together.

Negative: final owner transfer cannot pair new policy with old owner label; actor/master/operator/session/epoch/MFA/path loss at the final check denies. Backward movement during this read fails503 even if still later than activation; backward movement before activation remains503 from the selector. Corrupt/missing singleton still fails503. No cached policy, GET repair, fallback on corrupt graph, widened authority or sensitive metadata projection is introduced.

## RED-first tests and gates

Use real persisted pending graphs and real authority, API client and snapshot selector. A narrow wrapper around the service's authority call advances a controlled clock immediately after initial authorisation; it does not substitute authority results or policy. Existing enrollment marker remains the established synthetic fixture, without factor secrets.

- Parametrised literal final instants: rollback minus one microsecond, rollback equality, rollback plus one microsecond. Initial service authorisation starts two microseconds before rollback. Assert exact RFC3339 `server_time`, literal pending status and independently known candidate/fallback, stored revision2, unchanged pending pointer, change status, policies/events/security rows.
- Advance the clock after the former response-time capture and before final authority (via owner display read or the wrapper's second call); equality must still use one explicit final selection instant and its matching snapshot.
- Final clock one microsecond before `started_at` but after activation must produce503 with no policy or writes. Before-activation movement remains503. No-pending baseline still projects its current authorised policy/time unchanged.
- Preserve and rerun existing mixed-owner injected-transfer regression and six-route authority tests. Add final owner/role revocation or final snapshot revision interleaving where it catches an otherwise uncovered mix; expect denial or a fully final snapshot, never hybrid fields.

First write and run focused RED; send root actual failing assertions and this proposal. Await root code gate. Then minimal change, focused GREEN, full backend pytest, Django check and no migration drift. Root executes actual PostgreSQL on the frozen changed artifact and arranges independent source review. Record skips/failures without inferring SQLite proves concurrency.

## Bounded remaining actual PostgreSQL matrix (test design only)

After the timestamp correction gate, add remaining tests to `backend/tests/test_network_access_concurrency.py`; no new production feature is implied. Reuse synthetic owner/session helpers but do not rerun unchanged 12 cases until the changed suite/root verification warrants it. Event/barrier-controlled threads, real separate connections and real services/API; no sleep-based assertions.

1. **Staff service revocation versus network write:** two distinct owner masters; real `staff_access.change_staff` removes/suspends initiating manager's owner membership while a network request waits on the shared organisation lock. Force the staff writer to acquire the organisation first, then start the network request. Network request holds its own actor User/security and waits for Organisation; staff service does not acquire target User late. Assert staff event once, network403/no policy event, no deadlock. Reverse ordering: network event wins first, staff change follows; existing fixed deadline/graph remains intact, no subsequent HTTP adoption.
2. **OS operator revoke versus network write:** `change_operator` locks the target User/identity/org/operator before network actor acquisition. Network request reaches User lock, release revoke to commit. Assert inactive entitlement/version+1, one private revoke event, network403/no policy event. Reverse ordering serialises successfully without lost update; no deadline extension or copied authority.
3. **OS owner transfer versus network write:** real `transfer_owner` acquires sorted old/new Organisations then singleton. Existing HTTP request has old captured owner/environment context before switching configuration to target (all worker settings deliberately updated consistently for this test). Release transfer while network waits at the organisation boundary. Assert owner-transferred terminal state/event once, no copied entitlements, old request cannot mutate or obtain new-owner policy, and no reverse lock edge. Final denial may be owner-unavailable, invalidated or permission-denied according to which current-authority check observes the transfer, never success.
4. **Activation event insertion wait crossing preview deadline:** hold a colliding NetworkPolicyEvent UUID uncommitted in another transaction, inject that ID only into the real activation event INSERT, signal entry and move controlled time to the immutable preview expiry before rolling the holder back. Actual PostgreSQL unique wait must complete, final check must roll back candidate/change/pointer/event and return409 preview-expired; revision stays1 and preview remains unconsumed. Existing confirm-event rollback/MFA cases remain separate evidence.

Root reviews these test orderings before execution; if the real service locks differ from the proposed barriers, revise this plan before asserting a race has been proved. New tests are not passed evidence until actual PostgreSQL output is observed.
