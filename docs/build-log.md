# Build Log

All times are UTC. This log records work supported by repository history and executed checks; it does not claim users, partner verification, or live transactions.

## 2026-09-01

### 06:10 - Build start and discovery

- Verified the build began inside the official window.
- Inspected the pre-existing repository: one GitHub-generated initial commit and `.gitattributes` only.
- Read the required current Sibyl, Base, and Virtuals primary sources.
- Smoke-tested `sibyl-memory-client==0.8.0` on Python 3.12.
- Found and documented the SDK's explicit `storage.close()` requirement for temporary SQLite cleanup on Windows.

Commit: `a32a7eb` (`chore: bootstrap RecallOps monorepo`)

### 06:16 - Load-bearing memory vertical slice

- Implemented the only production memory adapter with explicit HOT, WARM, COLD, and REFERENCE calls.
- Added deterministic decimal-safe policy evaluation and fail-closed guard behavior.
- Implemented two independent demo processes sharing only the durable Sibyl database.
- Session 1 wrote Agent A's failed verification. Session 2 recalled it, denied Agent A, and approved Agent B.
- Ran Ruff, mypy strict, 15 tests, package build, and dependency audit before push.

Commit: `7b28628` (`feat(memory): prove fresh-process Sibyl recall`)

### 06:29 - Policy API and economic state safety

- Expanded policy context with permissions, revocations, human exceptions, evidence confidence, and probation.
- Added versioned FastAPI/OpenAPI endpoints with correlation IDs, conservative logs, admin mutation boundary, and input caps.
- Persisted idempotency records and action-bound execution authorizations in Sibyl.
- Added job verification and payment state transitions. Duplicate callbacks are side-effect free; failed jobs cannot be paid and affect future decisions.
- Replaced deprecated Starlette test transport fallback with current `httpx2`.
- Ran 31 tests with 84% coverage, Ruff, mypy strict, Uvicorn HTTP smoke checks, Docker Compose health checks, and `pip-audit --strict`.

Commit: `a2e6306` (`feat(policy): enforce memory-gated commerce actions`)

### 07:35 - Judge-facing control-plane console

- Built the responsive Next.js operations interface around the policy gate rather than a chat layout.
- Added exact decision evidence, durable receipt metrics, task-scoped counterparty state, integration proof, and fresh-process presenter controls.
- Kept the Sibyl path and admin token behind a server-side, route-allowlisted control-plane proxy.
- Ran strict type checking, ESLint, Vitest, a Next.js production build, and Playwright on desktop and mobile.
- Exercised the real Web -> FastAPI -> Sibyl route: the recalled Session 1 failure denied Agent A with exact evidence.

Commit: pending at the time of this entry.
