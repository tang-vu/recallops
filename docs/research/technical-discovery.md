# Technical Discovery

Initial access date: 2026-09-01 UTC. Package source and public network checks refreshed 2026-09-02 UTC.

This note records concise implementation findings from current primary sources. It intentionally does not reproduce large documentation excerpts.

## Build and submission rules

- [Hackathon rules](https://hack.sibyllabs.org/rules): the build window is September 1 through September 10, 2026 UTC. Sibyl Memory must be load-bearing, the demo must show cold-start recall in an unedited segment, the README must expose critical-path calls, and a deletion test is required. Partner multipliers require visible, exercised product work.
- [Submission instructions](https://hack.sibyllabs.org/submissions): the submission requires a public repository, a 2 to 5 minute demo, team and partner stack details, and a memory implementation note. Submission is performed from the private build page and is not authorized for automation in this project.

## Sibyl Memory

Sources:

- [Documentation overview](https://docs.sibyllabs.org/)
- [Memory overview](https://docs.sibyllabs.org/memory/)
- [Five-tier concepts](https://docs.sibyllabs.org/memory/concepts)
- [Integrations](https://docs.sibyllabs.org/memory/integrations)
- [Source repository](https://github.com/Sibyl-Labs/Sibyl-Memory), HEAD observed as `7499554adf7f8794c17473b85a087b85742dc05c`
- [PyPI package](https://pypi.org/project/sibyl-memory-client/)

Choice: pin `sibyl-memory-client==0.8.0`, released August 31, 2026, with Python 3.12 for the control plane.

Hackathon account tooling was rechecked on 2026-09-02. The official setup page currently recommends `sibyl-memory-cli[mcp]`; PyPI reported `sibyl-memory-cli==0.4.0` as the newest release. It was installed in an isolated Python 3.12 `uv tool` environment and resolved `sibyl-memory-client==0.8.0`, `sibyl-memory-hermes==0.4.0`, and `sibyl-memory-mcp==0.2.0`. This account-level CLI is separate from the project's frozen production environment. On Windows CP1252 terminals, the CLI's setup report currently raises `UnicodeEncodeError` while printing an arrow character; setting `PYTHONUTF8=1` avoids the display bug. The isolated extra also did not expose its nested MCP executable on `PATH`, so `sibyl-memory-mcp==0.2.0` was installed as a second isolated tool. After a dry run and configuration backup, `sibyl setup codex` added the `mcp_servers.sibyl_memory` entry and verified that the server starts cleanly.

Verified API surface from the installed 0.8.0 wheel:

- `MemoryClient.local(path, tenant_id=...)`
- HOT: `set_state(key, body)` and `get_state(key)`
- WARM: `set_entity(category, name, body, status=...)` and `get_entity(category, name)`
- COLD: `write_event(...)` and `read_events(...)`
- REFERENCE: `set_reference(key, body, metadata=...)` and `get_reference(key)`
- ARCHIVE: `archive_entity(category, name, reason=...)`
- FTS5: `search_entities(query, category=...)`

Smoke-test result: real SQLite-backed writes and reads passed for HOT, WARM, COLD, and REFERENCE tiers. The wheel supports Python 3.10 or newer. On Windows the client owns open SQLite connections through `MemoryClient.storage`; `MemoryClient.storage.close()` is required before a temporary database can be removed. RecallOps will wrap that lifecycle explicitly.

The production control plane will use Sibyl's local SQLite substrate directly through the SDK. A test-only stateless baseline will never be selected as a runtime fallback.

## Virtuals ACP

Sources:

- [Base Virtuals integration page](https://docs.base.org/agents/plugins/native/virtuals)
- [`acp-node-v2` source](https://github.com/Virtual-Protocol/acp-node-v2)
- [`acp-cli` source](https://github.com/Virtual-Protocol/acp-cli)

Observed package versions on 2026-09-01:

- `@virtuals-protocol/acp-cli==1.0.34`, Node.js 20.19 or newer
- `@virtuals-protocol/acp-node-v2==0.1.12`

Choice: use the maintained ACP CLI as the first live adapter because every command supports `--json`, event streams are NDJSON, `IS_TESTNET=true` separates testnet state, and its P256 private signer stays in the OS keychain after browser approval. Use `acp configure start --json` followed by `acp configure complete` for non-blocking authentication. Live job operations still require agent registration, signer approval, and funding, so fixture tests will be completed before requesting the smallest human action.

Security follow-up: an isolated install of CLI 1.0.34 on the access date still pulled deprecated `@virtuals-protocol/acp-node` 0.3.0 beta for legacy paths and produced 9 high-severity npm audit findings. `npm audit fix` did not clear them. RecallOps invokes only the maintained CLI's v2 default job paths but does not vendor the CLI into its default runtime. Live use is an operator-reviewed prerequisite documented in `docs/virtuals-live-setup.md`.

The installed 1.0.34 CLI source was re-inspected on 2026-09-02 rather than relying on older examples. Browse results use `data`, `chains[].chainId`, and USDC `priceValue`; `job history --json` returns chronological `entries` containing `budget.set`, `job.funded`, `job.submitted`, `job.completed`, and `job.rejected` events. RecallOps parses those exact current shapes. A real isolated CLI invocation reached the authentication boundary and returned `NO_ACTIVE_AGENT`; no live job or partner evidence was created.

The v2 SDK remains a supported alternative if embedding provides a material lifecycle advantage. It currently requires wallet and signer configuration and uses `createJobByOfferingName` for buyer work. Deprecated v1 and archived OpenClaw packages are excluded.

## Base

Sources:

- [Base x402 payment guide](https://docs.base.org/agents/guides/x402-payments)
- [Base Virtuals plugin guide](https://docs.base.org/agents/plugins/native/virtuals)
- [Base network connection reference](https://docs.base.org/base-chain/quickstart/connecting-to-base)
- [Base Sepolia funding guide](https://docs.base.org/get-started/get-funds)
- [Foundry v1.8.1 release](https://github.com/foundry-rs/foundry/releases/tag/v1.8.1)
- [Solidity 0.8.36 release](https://www.soliditylang.org/blog/2026/07/09/solidity-0.8.36-release-announcement/)

Choice: use Foundry 1.8.1, Solidity 0.8.36, and viem 2.56.1. The compiler release includes two security fixes, so the contract pins the current stable compiler rather than an older example version. The Base reference confirms Sepolia chain ID `84532` and the official `https://sepolia-explorer.base.org` explorer. The registry anchors only digests after approval and verification; Foundry tests and local Anvil deployment precede any testnet action.

The official Windows Foundry 1.8.1 archive was checksum-verified before installation. Its observed SHA-256 was `02d98fc2c573793960ee06b7f642487d483fe30572f7e248804c207334a418d8`. Local contract tests, fuzzing, lint, gas snapshot, deployment, and a viem transaction all passed. Base Sepolia remains unconfigured and unclaimed.

On 2026-09-02 the official public Base Sepolia RPC returned chain ID 84532, block 46,276,519, and gas price 6,000,000 wei during the read-only preflight. A separate Foundry deployment simulation with a dummy submitter estimated 555,569 gas and 0.000006111259 testnet ETH at its observed maximum fee. Neither check requested a signature or broadcast a transaction.

x402 is a stretch integration, not the critical path. The current Base MCP flow supports Base and Base Sepolia but requires a separate approval link and wallet signature for a payment. No paid or signed call will be attempted without explicit approval.

## Toolchain

- Python 3.12 managed by uv 0.11.8
- Node.js 24.14.1 and npm 11.11.0, compatible with current ACP CLI requirements
- FastAPI and Pydantic v2 for the versioned control-plane API
- Next.js and strict TypeScript for the operations console
- Foundry 1.8.1 and viem 2.56.1 for contracts and typed application interaction

Versions beyond the packages above will be locked when their workspace is introduced and smoke-tested.

Milestone 2 control-plane lock after smoke and test execution:

- FastAPI 0.141.1
- Pydantic 2.13.5
- Uvicorn 0.52.4
- `httpx2` 2.12.0 for Starlette's current TestClient transport
- mypy 1.20.2, pytest 8.4.2, pytest-cov 6.3.0, Ruff 0.16.5

The use of `httpx2` is intentional: current Starlette 1.6 emits a deprecation warning when its compatibility fallback imports `httpx`. The current transport was installed and the warning disappeared.

Milestone 3 web lock after local build and browser verification:

- Next.js 16.3.4 and React 19.2.8
- Tailwind CSS 4.3.3
- TanStack Query 5.102.8
- TypeScript 6.0.3 in strict mode
- Vitest 4.1.11 and Playwright 1.62.1
- ESLint 9.39.5 with `eslint-config-next` 16.3.4
- jsdom 29.0.1

npm is the web workspace package manager and `apps/web/package-lock.json` is the reproducible lock. ESLint 10 and the TypeScript 7 prerelease were not selected because the current Next.js lint plugins do not yet declare compatible peer ranges. jsdom 30 was not selected because its current Node engine starts at 24.15 while the inspected environment is Node 24.14.1.
