# Memory Implementation

RecallOps uses `sibyl-memory-client==0.8.0` as its only production persistence implementation. The browser does not touch the database, and the control plane has no production database fallback.

## Critical path

The economic guard in [`orchestration/guard.py`](../services/control-plane/src/recallops/orchestration/guard.py) performs this sequence:

1. Call `MemoryPort.load_evaluation_context` before evaluating the action.
2. Retrieve mandatory owner policy, cumulative budget, and a task-scoped matching failure from Sibyl.
3. Pass the recalled records to the pure deterministic policy engine.
4. Persist the exact proposed action through `MemoryPort.write_proposed_action`.
5. Persist the action-bound decision receipt through `MemoryPort.write_decision`.
6. Return `ESCALATE` if a mandatory read or write fails.

The execution gate reloads the durable proposed action and receipt before any adapter call. It writes an action-bound authorization, validates current offering price against the approved ceiling, then permits one idempotent Virtuals dispatch. The resulting job and its receipt link are written back through Sibyl.

## Exact Sibyl calls

All calls live in [`memory/sibyl_store.py`](../services/control-plane/src/recallops/memory/sibyl_store.py).

| Tier | RecallOps record | Sibyl 0.8.0 call | Used for evaluation |
| --- | --- | --- | --- |
| HOT | Active process/session and demo stage | `set_state("recallops:active-session", body)` | Operational proof, not final policy authority |
| WARM | Owner policy | `set_entity("owner_policy", ...)` / `get_entity(...)` | Per-action limit, cumulative limit, chain, currency, verifier rule |
| WARM | Budget account | `set_entity("budget_account", ...)` / `get_entity(...)` | Durable cumulative spend and active window |
| WARM | Failure fingerprint | `set_entity("failure_fingerprint", ...)` / `get_entity(...)` | Denies the same provider, category, and task fingerprint |
| WARM | Counterparty profile | `set_entity("counterparty_profile", ...)` | Task-specific probation consequence |
| WARM | Permission grant or revocation | `set_entity("permission_grant", ...)` / `get_entity(...)` | Agent, provider, category, and validity scope |
| WARM | Human exception and approval | `set_entity("human_exception", ...)` / `set_entity("human_approval", ...)` | Scoped override evidence; never a broad policy bypass |
| WARM | Decision receipt | `set_entity("decision_receipt", ...)` | Cross-session audit and future replay protection |
| WARM | Proposed action | `set_entity("proposed_action", ...)` / `get_entity(...)` | Binds provider, offering, amount, and task to later execution |
| WARM | Idempotency and execution authorization | `set_entity(...)` / `get_entity(...)` | Exactly-once request binding before adapter dispatch |
| WARM | Commerce job | `set_entity("commerce_job", ...)` | Callback deduplication, verification, and payment state |
| COLD | Policy, action, decision, authorization, ACP, and verification events | `write_event(...)` | Chronological audit timeline and approval-before-dispatch trace |
| REFERENCE | Versioned policy schema metadata | `set_reference(...)` | Names the decision set and decimal encoding |
| ARCHIVE | Superseded records | Not called in Milestone 1 | `archive_entity(...)` will be wrapped when policy lifecycle APIs arrive in Milestone 2 |

The 0.8.0 client returns a `NotFoundError` for missing entities. The adapter translates a missing expected record to `None`, which produces `ESCALATE` for mandatory policy or budget state. Other SDK exceptions become `MemorySubsystemError` and fail closed.

## Deterministic names and tenant isolation

Every tenant receives a separate Sibyl tenant namespace. Stable entity names use SHA-256 over unambiguous, ordered identity fields:

- Owner policy: owner ID
- Budget account: owner ID plus currency
- Counterparty profile: provider ID plus task category
- Failure fingerprint: provider ID plus task category plus task fingerprint

The original values remain in the entity body for inspectable evidence. Hashing the key avoids delimiter ambiguity and unbounded user-controlled entity names; it is not presented as encryption.

## Fresh-process proof

[`test_fresh_process.py`](../services/control-plane/tests/test_fresh_process.py) launches Session 1 and Session 2 through two independent `subprocess.run` calls using the same absolute database path.

Session 1 persists:

- Owner policy and policy schema reference
- Zero-spend cumulative budget account
- Agent A failure fingerprint
- Agent A task-scoped counterparty profile on probation
- Chronological policy, budget, and failed-verification events

It closes `MemoryClient.storage` and exits. Session 2 creates a new `MemoryClient`, PID, and session UUID. The matching Agent A failure is recalled and included verbatim in `memory_evidence`, producing `DENY` with `REPEATED_FAILURE_FINGERPRINT`. Agent B has no matching failure and receives `APPROVE` under the same recalled policy and budget. The demo then exercises the approved adapter path in `FIXTURE MODE`, writes an unmistakable `fixture:` job, and links it to the receipt. A live ACP job remains a separately gated mode.

The test fails if the WARM Sibyl writes or reads are removed because Session 2 then lacks mandatory policy state or cannot recall the Agent A failure.

## Money and evidence integrity

Pydantic validates money as `Decimal` with six fractional places and serializes it as a decimal string. Every evidence item includes its Sibyl tier, record identity, write and recall timestamps, source session, active status, exact non-secret body, explanation, and SHA-256 content digest. The receipt includes a digest over the ordered evidence snapshot.

These hashes make changes detectable within RecallOps artifacts. They do not become onchain proof until the separate Base receipt registry is implemented and exercised.
