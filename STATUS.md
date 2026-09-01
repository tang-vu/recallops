# RecallOps Status

Last updated: 2026-09-01 UTC

## Current milestone

Milestone 1 complete: Load-bearing memory vertical slice

## Completed work

- Verified the build began after September 1, 2026 at 00:00 UTC.
- Inspected the existing public repository and preserved its initial history.
- Read all mandatory live sources and recorded package choices.
- Smoke-tested `sibyl-memory-client==0.8.0` against a real temporary SQLite database.
- Established the monorepo skeleton, license, security boundary, and initial documentation.
- Implemented `SibylMemoryStore` as the only production `MemoryPort` implementation.
- Added explicit HOT, WARM, COLD, and REFERENCE writes with tenant isolation and deterministic entity names.
- Implemented a deterministic decimal-safe policy engine and mandatory commerce guard.
- Implemented Session 1 verifier failure persistence and separate-process Session 2 recall.
- Proved the recalled Agent A failure changes the economic decision to `DENY` while Agent B receives `APPROVE`.
- Added safe reset validation restricted to `.data/demo/recallops-demo.db`.

## Tests and checks actually run

- Sibyl 0.8.0 HOT state write/read smoke test
- Sibyl 0.8.0 WARM entity write/read smoke test
- Sibyl 0.8.0 COLD event write smoke test
- Sibyl 0.8.0 REFERENCE write/read smoke test
- GitHub CLI authentication and repository visibility checks
- Ruff format check: passed on 17 Python source and test files
- Ruff lint: passed
- mypy strict mode: passed on 17 source and test files
- pytest: 15 passed with 88% statement coverage
- `pip-audit --strict`: no known vulnerabilities found
- Real Sibyl adapter round trip on temporary SQLite: passed
- Sibyl tenant isolation: passed
- Fresh-process integration test with two subprocesses: passed
- Manual Session 1 run: PID 36244, session `3c81d887-e833-4bc6-a5a1-ae3116128550`, 9 successful Sibyl writes across HOT, WARM, COLD, and REFERENCE
- Manual Session 2 run: PID 12816, session `103b442a-a359-43fe-b311-5d54f1e40227`, recalled Session 1 failure and denied Agent A

## Known failures

- Foundry and Anvil are not installed yet.
- A first smoke-test harness exposed that `MemoryClient.storage.close()` must be called explicitly on Windows before deleting a temporary SQLite database. The production adapter will own this lifecycle.
- GNU Make is not installed in the inspected Windows environment. The Makefile is available for judge and CI environments; equivalent uv commands were executed directly.
- The policy engine currently implements the Milestone 1 rules. Permission, exception, revocation, replay, and execution state transitions remain Milestone 2 work.

## Live evidence obtained

- Real local Sibyl Memory 0.8.0 reads and writes: obtained in smoke tests, automated integration tests, and the manual two-process demo.
- Base Sepolia deployment and transaction: not yet obtained; no multiplier claim.
- Virtuals ACP job: not yet obtained; no multiplier claim.

## Human actions needed

None for completed Milestones 0 and 1.

## Next tasks

- Implement the complete policy schemas and versioned FastAPI API.
- Enforce permissions, revocations, exceptions, replay resistance, expiry, idempotency, and execution state transitions.
- Add structured correlation IDs and secret-redacting JSON logs.
- Begin the judge-facing Next.js control-plane interface only after Milestone 2 gates pass.
