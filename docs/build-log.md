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

Commit: `9c4f101` (`feat(web): build decision evidence dashboard`)

### 07:55 - Guarded Virtuals ACP boundary

- Added explicit `VirtualsPort`, fixture, and maintained ACP CLI live adapters.
- Enforced Base Sepolia, JSON-only subprocess arguments, output limits, environment allowlisting, credential redaction, current offering price checks, and idempotent dispatch.
- Persisted proposed actions, ACP jobs, receipt-to-job links, and pre/post-dispatch events through Sibyl.
- Kept live dispatch behind a second explicit configuration flag and added the exact human-controlled setup guide.
- Found 9 unresolved high-severity npm audit findings in the official CLI's isolated dependency tree, including a deprecated legacy v1 transitive package. The CLI is therefore not vendored into the default runtime.
- Ran 39 backend tests plus Ruff and mypy; exercised fixture dispatch without wallet or network activity.

Commit: `429539b` (`feat(virtuals): execute guarded ACP jobs`)

### 08:34 - Verified local Base receipt anchoring

- Installed the checksum-verified official Foundry 1.8.1 toolchain and pinned Solidity 0.8.36.
- Implemented a digest-only registry with chain validation, immutable submitter authorization, exact idempotence, and conflicting replay rejection.
- Added local and Base Sepolia deployment scripts without embedding a key or signing a public transaction.
- Added a typed viem 2.56.1 bridge that validates the registry, simulates the call, confirms the receipt, verifies persisted state, and recovers the original transaction on replay.
- Added a control-plane boundary that permits anchoring only after `APPROVE`, successful ACP dispatch, and passed verification, then persists the confirmed anchor back to Sibyl.
- Deployed locally on Anvil and executed a real local transaction. Repeating the same request returned `created=false` and the original hash.
- Ran 13 Foundry tests, 1,024 total fuzz cases, high-severity lint, gas snapshot checks, 3 viem tests, and the Base API integration tests.

Commit: `5aab07a` (`feat(base): anchor verified decision receipts`)

### 09:04 - Benchmark, deletion proof, and judging package

- Added twelve deterministic scenarios covering budgets, repeated failures, task scope, revocation, expiry, prompt injection, verification, replay, exceptions, probation, and missing memory.
- Ran every scenario through the production `SibylMemoryStore` and an isolated stateless comparator with seed 20260901.
- Measured 0% unsafe repeats, 0% budget violations, 100% decision accuracy, and 100% evidence completeness on the Sibyl path.
- Demonstrated that disabling Sibyl stops production commerce with `ESCALATE`, while the comparator repeats the unsafe approval.
- Exported JSON, CSV, and Markdown artifacts and connected the verified artifact to the API and dashboard.
- Drafted the 3:30 demo, problem-validation disclosure, submission checklist, and unpublished submission materials.

Commit: `e403931` (`test: add cross-session deletion benchmark`)

All Python, web, browser, Solidity, viem, and dependency gates then passed in [GitHub Actions run 33492189813](https://github.com/tang-vu/recallops/actions/runs/33492189813).

### 09:37 - Completed the five-tier memory lifecycle

- Wrapped Sibyl 0.8.0 `archive_entity(...)` in the production adapter.
- Archived changed policies, permissions, exceptions, and counterparty lifecycle states before replacement.
- Added admin-gated lifecycle operations for expired or revoked permission and exception records, plus explicit counterparty retirement.
- Verified that retirement removes the active profile while retaining the failure fingerprint that still protects future decisions.

Commit: recorded in Git history as `feat(memory): archive superseded lifecycle records`.

## 2026-09-02

### 03:55 - Partner integration preflight

- Re-inspected the installed ACP CLI 1.0.34 and maintained v2 source to verify current browse, offering, and history JSON shapes.
- Updated the live adapter to parse chain objects, USDC pricing, deliverables, funding metadata, and verifier outcomes from current v2 history entries.
- Exercised the real isolated CLI through the adapter. It reached the expected `NO_ACTIVE_AGENT` boundary and emitted no job, payment, or partner evidence.
- Added a read-only machine-readable preflight. It observed Base Sepolia chain ID 84532, block 46,276,519, and gas price 6,000,000 wei while asserting zero writes and zero signature requests.
- Simulated the Base Sepolia deployment with a dummy submitter and no broadcast. Foundry estimated 555,569 gas and 0.000006111259 testnet ETH at the observed maximum fee.

## 2026-09-04

### 04:50 - Persistent public preview

- Created a dedicated Cloudflare Tunnel for `recallops.tangvu.dev` without changing the routes used by other projects on the host.
- Ran Next.js, loopback-only FastAPI, and the tunnel connector under PM2 with automatic resurrection.
- Moved the deployed Sibyl database and logs to a persistent machine-local application directory outside Git.
- Exercised the hosted Session 1 and Session 2 controls. Two separate process IDs proved that the second process recalled the first process's failure and denied Agent A.
- Verified the public UI and proxied health endpoint over HTTPS, then recorded non-sensitive deployment evidence.

Commit: `e2ded02` (`chore(deploy): publish Cloudflare-hosted preview`)

### 06:02 - Signature memory authority interface

- Reworked the visual system from a conventional technical dashboard into a purpose-built memory authority console.
- Added a large operational thesis, a four-stage commerce route, an instrument-style decision gate, a mandatory-read contract, an oversized verdict, and a visual memory bridge between source and recall sessions.
- Preserved strict evidence truthfulness: all telemetry remains derived from API records, fixture and live states remain unmistakable, and no decorative metric was introduced.
- Inspected full-page desktop and Pixel 7 renders from the public deployment.
- Passed strict TypeScript, zero-warning ESLint, 3 Vitest tests, a production build, and the critical Playwright denial flow on desktop and mobile.
- Re-ran the actual public browser path through Next.js, FastAPI, and Sibyl and observed `DENY` with `REPEATED_FAILURE_FINGERPRINT`.

### 08:11 - Light institutional visual system

- Replaced the dark palette with a warm paper and graphite interface so RecallOps does not resemble the default dark aesthetic used by many AI products.
- Retained the product-specific control language: signal green for memory authority, decision red for denials, the instrument gate, the cross-session bridge, and the evidence-first layout.
- Removed decorative glow from the core surfaces and used restrained technical grids, borders, typography, and whitespace to carry hierarchy.
- Rebuilt and restarted the public Next.js process, inspected delayed full-page desktop and Pixel 7 captures with live data, and retained the existing loopback API and Cloudflare boundary.
- Passed strict TypeScript, zero-warning ESLint, 3 Vitest tests, the production build, and Playwright denial flows on desktop and mobile.

### 12:42 - First social asset prepared

- Generated a 1672 by 941 launch visual matching the light RecallOps interface and the two-session memory story.
- Re-encoded the PNG with metadata stripping and verified directly that its only remaining chunks are `IHDR`, `IDAT`, and `IEND`.
- Updated the first X post to tag the official Sibyl Labs account, link the live product, and stay within 267 characters without unsupported partner claims.
- Confirmed that the installed and latest Build in Public MCP release is 0.5.0. Its tweet tool accepts text only and cannot start OAuth until an X developer app key and secret are configured locally, so no post was claimed or fabricated.
