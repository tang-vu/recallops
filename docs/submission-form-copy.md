# Sibyl Submission Form Copy

Prepared on 2026-09-02 UTC. Copy review only. Do not save the private form, publish posts, upload a video, or mark the build ready without Vu Tang's explicit approval.

## Public repository URL

```text
https://github.com/tang-vu/recallops
```

## What breaks when memory is deleted?

```text
Without Sibyl Memory, RecallOps cannot recover mandatory policy and outcome history across fresh processes. Production fails closed with ESCALATE and stops agent commerce; the explicit stateless benchmark instead rehires a known-failing provider and violates cumulative budgets.
```

## Memory walkthrough

```text
Persist: Owner policies, cumulative budgets, permissions, task-scoped provider failures, verification outcomes, decisions, and execution references through Sibyl state, entities, journal events, references, and archives.
Recall (fresh session): A separate Session 2 operating-system process opens the same durable Sibyl database and retrieves Agent A's Session 1 failure fingerprint and mandatory policy state without a shared process cache.
Changes the agent's decision by: Denying the cheaper Agent A rehire with REPEATED_FAILURE_FINGERPRINT, allowing Agent B only after every deterministic policy check passes, and failing closed if mandatory memory cannot be retrieved.
```

## Memory primitives to select

Select only primitives exercised by the submitted runtime and recorded demo.

- `recall`
- `entities`

Do not select `semantic search`, `temporal / time-travel`, `summarization`, `reflection`, or `consolidation` unless the implementation, automated test, and demo visibly exercise that primitive before submission. RecallOps uses FTS5-capable Sibyl APIs internally, but the current critical decision path performs deterministic named retrieval and does not depend on semantic search.

## Post URLs

```text
https://x.com/tangvu_dev/status/2095872903506215334
```

One of the two required build-in-public posts is now published. Add a second real URL only after that post exists.

## Fields that must remain empty for now

- Demo video URL: no approved public upload exists.
- Ready for judging: must remain unmarked until the final human truth review and explicit approval.

## Evidence behind the copy

- Production memory adapter: `services/control-plane/src/recallops/memory/sibyl_store.py`
- Mandatory read gate: `services/control-plane/src/recallops/orchestration/guard.py`
- Deterministic decision engine: `services/control-plane/src/recallops/policy/engine.py`
- Fresh-process test: `services/control-plane/tests/test_fresh_process.py`
- Deletion proof: `scripts/deletion_test.py`
- Benchmark report: `benchmark/results/latest.md`
