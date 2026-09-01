# Judging Map

This map distinguishes implemented evidence from planned demo scenes. Partner claims remain unverified until public proof exists.

| Criterion | Product behavior | Source | Test | Demo scene | Evidence |
| --- | --- | --- | --- | --- | --- |
| Load-bearing critical path | Mandatory Sibyl read precedes deterministic evaluation; mandatory receipt write precedes execution authorization | `memory/sibyl_store.py`, `orchestration/guard.py` | `test_fresh_process_recall_changes_economic_decision`, `test_memory_read_failure_escalates_and_stops_commerce` | 0:55 to 2:25 | Session JSON with PID, UUID, commit, writes, recall |
| Fresh-process recall | Process B retrieves Process A's task-scoped Agent A failure | `demo/session1.py`, `demo/session2.py` | `test_fresh_process_recall_changes_economic_decision` | 1:35 to 2:25 | Local run recorded in `STATUS.md`; video pending |
| Multiple memory tiers | HOT session, WARM policy/outcomes, COLD events, REFERENCE schema | `memory/sibyl_store.py` | `test_real_sibyl_round_trip_and_explicit_close` | 0:55 to 1:35 | Structured list of successful Sibyl writes |
| Economic consequence | Matching verified failure changes Agent A to `DENY`; Agent B remains eligible | `policy/engine.py` | `test_matching_failure_changes_decision_to_deny` | 1:55 to 2:35 | Receipt reason codes and exact evidence body |
| Dynamic policy | Revocation, exception, probation, verifier failure, and budgets alter later decisions | `policy/engine.py`, `orchestration/jobs.py` | `test_revoked_permission_is_a_hard_deny`, `test_valid_human_exception_can_cover_matching_failure`, `test_failed_verification_blocks_payment_and_updates_future_policy` | Planned policy evidence panel | Test report; UI pending |
| Deletion test | Removing mandatory memory must stop commerce or expose unsafe stateless repeats | Benchmark work pending | Test pending Milestone 6 | 3:05 to 3:30 | JSON/CSV/Markdown pending |
| Deterministic authority | No LLM decides money or permissions | `policy/engine.py` | Policy unit suite | 0:25 to 0:55 | Source and OpenAPI receipt schema |
| State safety | Idempotency, expiry, action binding, human approval, verifier-before-payment | `orchestration/execution.py`, `orchestration/jobs.py` | `test_evaluation_and_execution_are_durably_idempotent`, `test_failed_job_cannot_be_paid` | Planned receipt execution panel | HTTP integration tests |
| Tenant isolation | Same entity name cannot cross tenant boundary | `memory/sibyl_store.py` | `test_tenant_isolation_uses_sibyl_schema` | Optional evidence detail | Test report |
| Security | Redaction, strict inputs, admin gate, safe reset, fail closed | `api/logging.py`, `api/app.py`, `demo/reset.py` | `test_secret_redaction_is_recursive`, `test_reset_rejects_paths_outside_exact_target`, API tests | Optional architecture cutaway | `docs/security-model.md` |
| Originality | Economic consequences, task-scoped trust, evidence receipts | `README.md`, `docs/architecture.md` | Demonstrated across suite | First 25 seconds and close | Product narrative |
| Virtuals multiplier | Real ACP-native job after approval | Adapter pending Milestone 4 | Fixture tests pending | 2:25 to 3:05 | No evidence and no claim yet |
| Base multiplier | Real Sepolia contract interaction after approval | Contract pending Milestone 5 | Foundry tests pending | 2:50 to 3:05 | No evidence and no claim yet |
| Pitch | 2 to 5 minute fresh-session story | Demo script pending final edit | Presentation path pending Playwright | Full 3:30 target | Video pending human approval |
