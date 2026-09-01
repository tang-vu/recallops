# Technical Discovery

Access date: 2026-09-01 UTC

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

The v2 SDK remains a supported alternative if embedding provides a material lifecycle advantage. It currently requires wallet and signer configuration and uses `createJobByOfferingName` for buyer work. Deprecated v1 and archived OpenClaw packages are excluded.

## Base

Sources:

- [Base x402 payment guide](https://docs.base.org/agents/guides/x402-payments)
- [Base Virtuals plugin guide](https://docs.base.org/agents/plugins/native/virtuals)

Choice: prioritize a minimal Solidity receipt registry on Base Sepolia. It will anchor only decision digests after policy approval. Foundry tests and local Anvil deployment precede any testnet action.

x402 is a stretch integration, not the critical path. The current Base MCP flow supports Base and Base Sepolia but requires a separate approval link and wallet signature for a payment. No paid or signed call will be attempted without explicit approval.

## Toolchain

- Python 3.12 managed by uv 0.11.8
- Node.js 24.14.1 and npm 11.11.0, compatible with current ACP CLI requirements
- FastAPI and Pydantic v2 for the versioned control-plane API
- Next.js and strict TypeScript for the operations console
- Foundry and viem for contracts and application interaction; Foundry is not installed in the inspected environment yet

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
