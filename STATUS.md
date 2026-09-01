# RecallOps Status

Last updated: 2026-09-01 UTC

## Current milestone

Milestone 4 complete: Guarded Virtuals integration

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
- Expanded policy rules for revocation, permission expiry and scope, prohibited providers, human exceptions, probation, evidence confidence, and policy conflicts.
- Added a versioned FastAPI/OpenAPI service with correlation IDs, redacted structured logs, strict request limits, and an admin mutation boundary.
- Added durable evaluation idempotency, action-bound execution authorization, receipt expiry, and human approval checks.
- Added commerce job state transitions, duplicate callback suppression, verifier outcome persistence, and payment gating.
- Added a production Dockerfile and Compose service with a named Sibyl volume and loopback-only port binding.
- Added a responsive Next.js control-plane console with overview, request, decision receipt, memory timeline, counterparties, benchmark, integration proof, and demo views.
- Connected the browser to FastAPI through a server-side allowlisted proxy; Sibyl and the admin token remain server-side.
- Derived every displayed metric from durable receipts and explicitly labeled unavailable benchmark and partner evidence.
- Added strict TypeScript, ESLint, Vitest, and Playwright coverage for the critical denial presentation on desktop and mobile.
- Added a narrow `VirtualsPort` with explicit fixture and maintained ACP CLI live adapters.
- Restricted live ACP calls to Base Sepolia, machine-readable JSON, bounded output, a minimal child-process environment, and sanitized error handling.
- Added durable proposed actions, approval-before-dispatch events, ACP job records, receipt-to-job links, offering price checks, and dispatch replay protection.
- Kept live dispatch disabled behind `RECALLOPS_ENABLE_LIVE_VIRTUALS=true` and documented the smallest human-controlled setup sequence.

## Tests and checks actually run

- Sibyl 0.8.0 HOT state write/read smoke test
- Sibyl 0.8.0 WARM entity write/read smoke test
- Sibyl 0.8.0 COLD event write smoke test
- Sibyl 0.8.0 REFERENCE write/read smoke test
- GitHub CLI authentication and repository visibility checks
- Ruff format check: passed on 17 Python source and test files
- Ruff lint: passed
- mypy strict mode: passed on 17 source and test files
- pytest: 31 passed with 84% statement coverage
- `pip-audit --strict`: no known vulnerabilities found
- Uvicorn loopback smoke test: health and versioned OpenAPI passed
- Docker image build: passed with frozen production dependencies
- Docker Compose smoke test: container reached `healthy`, Sibyl schema version 4, 22 OpenAPI paths, then stopped cleanly
- Real Sibyl adapter round trip on temporary SQLite: passed
- Sibyl tenant isolation: passed
- Fresh-process integration test with two subprocesses: passed
- Manual Session 1 run: PID 36244, session `3c81d887-e833-4bc6-a5a1-ae3116128550`, 9 successful Sibyl writes across HOT, WARM, COLD, and REFERENCE
- Manual Session 2 run: PID 12816, session `103b442a-a359-43fe-b311-5d54f1e40227`, recalled Session 1 failure and denied Agent A
- TypeScript strict check: passed
- ESLint with zero warnings: passed
- Vitest: 3 tests in 2 files passed
- Next.js production build: passed
- Playwright: 2 browser projects passed (Chromium desktop and Pixel 7 mobile emulation)
- Real Web -> FastAPI -> Sibyl proxy smoke test: Sibyl schema 4 was healthy; Agent A returned `DENY` with `REPEATED_FAILURE_FINGERPRINT` and `COUNTERPARTY_ON_PROBATION`, backed by four recalled WARM entities
- Manual Milestone 3 Session 1: PID 58968, session `8ad5461b-aef0-4243-9a8e-dfdfc382ecec`, 11 successful Sibyl writes
- pytest after Virtuals integration: 39 passed with 84% statement coverage
- Ruff format and lint after Virtuals integration: passed
- mypy strict after Virtuals integration: passed on 32 source and test files
- Virtuals fixture dispatch: created only `fixture:` job IDs after durable authorization, persisted the job and receipt link, and returned the same job on replay
- ACP CLI isolated dependency audit: 27 findings, including 9 high; available audit fix did not clear them
- Real Web -> FastAPI -> fixture ACP -> Sibyl smoke test: `APPROVE`, `FIXTURE_JOB_CREATED`, durable `SUCCEEDED` authorization, one `fixture:` job, receipt link matched, and zero fake links
- Updated Docker image build: passed; Compose reached healthy with real Sibyl schema 4 and `FIXTURE MODE`, then stopped cleanly
- Fresh Milestone 4 process proof after validated demo reset: Session 1 PID 61028, UUID `f54b2112-f705-4e03-8365-8fc3c29ea7e0`; Session 2 PID 3316, UUID `82f3c912-d6de-4892-af55-6559db0c6b47`; Session 2 recalled Session 1, denied Agent A, approved Agent B, and persisted `fixture:31c50808-45de-4b41-b63d-57d959d945e9`

## Known failures

- Foundry and Anvil are not installed yet.
- A first smoke-test harness exposed that `MemoryClient.storage.close()` must be called explicitly on Windows before deleting a temporary SQLite database. The production adapter will own this lifecycle.
- GNU Make is not installed in the inspected Windows environment. The Makefile is available for judge and CI environments; equivalent uv commands were executed directly.
- Live Virtuals dispatch is intentionally disabled; live mode reports `NOT_DISPATCHED` until the explicit enable flag is set.
- ACP CLI 1.0.34 has unresolved upstream audit findings and a deprecated legacy v1 transitive dependency, so it is not vendored in the default runtime.
- Rate limiting is not implemented in-process; current deployment binds to loopback and expects an edge control for public hosting.

## Live evidence obtained

- Real local Sibyl Memory 0.8.0 reads and writes: obtained in smoke tests, automated integration tests, and the manual two-process demo.
- Base Sepolia deployment and transaction: not yet obtained; no multiplier claim.
- Virtuals ACP job: not yet obtained; no multiplier claim.

## Human actions needed

None for fixture-complete Milestones 0 through 4. A real Virtuals job requires review of the upstream CLI audit, browser authentication, an identified Base Sepolia wallet, signer policy, testnet funding, and explicit approval of the exact maximum testnet amount.

## Next tasks

- Implement and fuzz-test the receipt registry contract locally.
- Prepare Base Sepolia deployment without deploying or signing until explicit wallet approval.
