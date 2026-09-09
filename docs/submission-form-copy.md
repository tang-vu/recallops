# Sibyl Submission Form Copy

Prepared on 2026-09-02 UTC. Copy review only. Do not save the private form, publish posts, upload a video, or mark the build ready without Vu Tang's explicit approval.

Update / September 9: the repo, published video, post pair, and prepared memory
fields were saved to the private build page as part of the user's authorized
submission preparation. An independent reload verified the values and checked
primitives. Ready remains unmarked for the planned September 10 submission;
see [saved-page evidence](evidence/build-page-preparation-2026-09-09.md).

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

New product build-log published on 2026-09-08 with both `@sibylcap` and
`@sibyl_labs_` tags:

```text
https://x.com/tangvu_dev/status/2097309402600759522
```

Demo-video post published on 2026-09-09, with the continuous 176.12-second
recording and both tags:

```text
https://x.com/tangvu_dev/status/2097381347782525063
```

Use the September 8 build-log and September 9 demo-video post as the submission
pair. The September 9 post is also the public demo-video URL.

Additional product update, published and verified after receipt revocation shipped:

```text
https://x.com/tangvu_dev/status/2097713301811839264
```

This optional extra post is recorded here for the builder's final review; it
has not been appended to the private build page.

## Fields that must remain empty for now

- Ready for judging: must remain unmarked until the final human truth review and explicit approval.

## Evidence behind the copy

- Production memory adapter: `services/control-plane/src/recallops/memory/sibyl_store.py`
- Mandatory read gate: `services/control-plane/src/recallops/orchestration/guard.py`
- Deterministic decision engine: `services/control-plane/src/recallops/policy/engine.py`
- Fresh-process test: `services/control-plane/tests/test_fresh_process.py`
- Deletion proof: `services/control-plane/src/recallops/benchmark/deletion.py`
- Benchmark report: `benchmark/results/latest.md`
