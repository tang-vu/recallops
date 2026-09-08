# Judging Map

The [published demo](https://x.com/tangvu_dev/status/2097381347782525063)
runs 2:56. The approximate scene times below refer to that recording, not the
older narration plan. [Recording evidence](evidence/demo-video-2026-09-09.md)
contains exact process identities and artifact hashes.

| Criterion | Product behavior and source | Verification | Where to inspect |
| --- | --- | --- | --- |
| Load-bearing memory | `memory/sibyl_store.py` and `orchestration/guard.py` require Sibyl policy/outcome reads before evaluation and durable receipt writes before authorization | `test_fresh_process_recall_changes_economic_decision`, `test_memory_read_failure_escalates_and_stops_commerce` | Video 1:12 to 2:26; process results in `/demo` |
| Fresh-process recall | `demo/session1.py` exits after writing; `demo/session2.py` opens the same durable database in another OS process | Backend fresh-process test and browser test `fresh process proof links two real backend processes` | Video 1:25 to 2:26 shows PIDs 61608/46704, different UUIDs, UTC timestamps, commit, and matching source |
| Economic consequence | `policy/engine.py` denies Agent A after recalling its matching failure; Agent B remains eligible | `test_matching_failure_changes_decision_to_deny` | Video 1:47 to 2:26: `REPEATED_FAILURE_FINGERPRINT`, Agent A DENY, Agent B APPROVE |
| Owner review | `api/workspaces.py` persists scoped reviews through Sibyl; current authorization re-reads memory | `test_owner_review_is_scoped_durable_and_requires_current_authorization`, `test_new_failure_invalidates_previously_approved_review` | Video 0:16 to 1:11; live `/workspace` review queue |
| Policy and spending | Deterministic limits, permissions, revocations, exceptions, probation, verifier requirements, and expiry | Policy engine tests and workspace policy/pause/expiry tests | Workspace policy and API guide. Product spend is owner-reported; the application owns execution and atomic enforcement |
| Memory tiers | HOT session, WARM policy/outcomes, COLD events, REFERENCE schema, ARCHIVE lifecycle history in `memory/sibyl_store.py` | Round-trip, permission archive, and counterparty retirement tests | Session 1 raw output lists writes. Archive lifecycle is tested in the repo and is not demonstrated in this video |
| Deletion and benchmark | `benchmark/deletion.py` fails closed when required memory is disabled; `benchmark/runner.py` compares the explicit stateless path | `test_deletion_test_stops_production_and_exposes_unsafe_baseline` and benchmark tests | Video 2:26 to 2:41 shows persisted benchmark results. The deletion command itself is not run in the video; inspect `benchmark/results/deletion-test.json` |
| Replay and execution safety | `orchestration/execution.py` and `orchestration/jobs.py` bind actions, expiry, idempotency, and verification-before-payment | Durable idempotency, denied execution, duplicate callback, and failed payment tests | Source/tests; the workspace video does not execute a payment |
| Isolation and security | Separate workspace Sibyl databases, hashed role keys, strict request models, same-origin browser writes, redacted logs | Workspace isolation/role tests, gateway browser tests, logging and reset tests | [Workspace contract](developer-workspaces.md) and [security model](security-model.md) |
| Presentation | Product home, owner review, paired process evidence, benchmark, API guide | Responsive browser tests and inspected video frames | Entire 2:56 captioned recording; no audio track |

## Partner and PMF claims

Base and Virtuals multipliers are **not claimed**. The repo retains a gated ACP
adapter and digest-only Base registry with fixture/local tests. The video labels
fixtures and does not contain a live ACP job, Base transaction, or payment.
Public RPC reads, Anvil transactions, and simulations are not multiplier proof.

No user count, interview, pilot, waitlist, revenue, or validated PMF claim is made.
The benchmark is a deterministic test comparison, not a production outcome metric.

## Submission links

- [Public repository](https://github.com/tang-vu/recallops)
- [Live product](https://recallops.tangvu.dev)
- [September 8 build-log](https://x.com/tangvu_dev/status/2097309402600759522)
- [September 9 demo video](https://x.com/tangvu_dev/status/2097381347782525063)

The private build page has not been marked ready by this documentation update.
