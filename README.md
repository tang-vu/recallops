# RecallOps

[![Quality gates](https://github.com/tang-vu/recallops/actions/workflows/ci.yml/badge.svg)](https://github.com/tang-vu/recallops/actions/workflows/ci.yml)

**Memory-gated control plane for autonomous agent commerce**

RecallOps uses durable policy and outcome memory to decide whether an autonomous agent may hire, pay, or reuse another agent. Every proposed economic action receives exactly one inspectable decision: `APPROVE`, `DENY`, or `ESCALATE`.

Live control-plane preview: [recallops.tangvu.dev](https://recallops.tangvu.dev). The preview uses real local Sibyl persistence, visibly labeled Virtuals fixtures, and no configured Base transaction signer.

## Why it exists

Agent sessions are disposable; economic consequences are not. A fresh process must not forget that a provider failed the same task, a permission was revoked, or a cumulative budget was already consumed.

RecallOps puts Sibyl Memory on the execution critical path. If mandatory memory cannot be read, commerce fails closed. There is no production database fallback that recreates durable policy state elsewhere.

## Product walkthrough

1. An agent proposes a commerce action with a provider, task fingerprint, amount, permission, risk class, and verifier requirement.
2. The control plane retrieves owner policy, budget history, counterparty outcomes, permissions, exceptions, and prior decisions from Sibyl Memory.
3. A deterministic policy engine returns a receipt with reason codes and the exact memories that changed the result.
4. Only a current, action-bound approval may reach an execution adapter.
5. Verified outcomes are written back to Sibyl so a genuinely fresh process inherits their economic consequences.

## Load-bearing memory proof

The first vertical slice is built before the dashboard:

- Session 1 writes a rejected verification and provider failure fingerprint to Sibyl, then exits.
- Session 2 starts as a separate operating-system process against the same durable Sibyl database.
- Recall of the matching failure changes Agent A from the cheapest candidate to a denied candidate.
- Agent B is approved and the fixture path persists a clearly labeled `fixture:` job plus its receipt link; live mode remains separately gated.
- Disabling mandatory memory changes the safe result to `ESCALATE`; the explicit benchmark-only stateless baseline demonstrates the unsafe repeat separately.

Production reads and writes are easy to locate in:

- [Sibyl production adapter](services/control-plane/src/recallops/memory/sibyl_store.py): explicit HOT, WARM, COLD, REFERENCE, and ARCHIVE SDK calls
- [Deterministic policy engine](services/control-plane/src/recallops/policy/engine.py): evidence-backed decision semantics
- [Commerce guard](services/control-plane/src/recallops/orchestration/guard.py): mandatory read, evaluate, persist ordering and fail-closed behavior
- [Fresh-process integration test](services/control-plane/tests/test_fresh_process.py): Process A writes and exits; Process B recalls and changes the decision

See [the memory implementation note](docs/memory-implementation.md) for the exact call map and entity naming rules.

## Architecture

```text
Next.js operations console
          |
          v
FastAPI control plane
          |
          +--> deterministic policy engine
          |           |
          |           v
          |      Sibyl Memory (mandatory)
          |
          +--> Virtuals ACP adapter (after approval)
          |
          +--> Base receipt registry (after approval)
```

The browser never accesses the memory database directly. Partner integrations cannot execute before a valid policy receipt exists.

See [the full architecture](docs/architecture.md), [security model](docs/security-model.md), and [judging map](docs/judging-map.md).

The public preview is self-hosted behind a dedicated Cloudflare Tunnel. PM2 keeps the web console, loopback-only API, and tunnel connector alive, while the Sibyl database remains on a persistent machine-local path outside the repository. See [deployment operations](docs/deployment.md) and the [public deployment evidence](docs/evidence/public-deployment.md).

## Decision pipeline

RecallOps retrieves owner policy, cumulative budget, permission or revocation, task-scoped counterparty history, human exceptions, and verification state from Sibyl. It evaluates deterministic hard rules, persists the receipt and idempotency mapping, then authorizes at most one matching adapter dispatch. A job must pass verification before payment authorization; a failed result is written back as a future policy consequence.

Natural-language rationale is never policy authority. Requests asking the agent to ignore memory remain inert strings.

## Memory data model

- HOT: current process and demo workflow state
- WARM: policies, budgets, permissions, exceptions, counterparty profiles, failure fingerprints, decisions, jobs, and idempotency records
- COLD: chronological policy, verifier, decision, authorization, and job transition events
- REFERENCE: versioned policy schema metadata
- ARCHIVE: superseded policies and permissions, expired lifecycle records, and retired counterparty profiles through real `archive_entity(...)` calls

Entity names are deterministic and tenant isolation is enforced by Sibyl's schema. Details and exact calls are in [docs/memory-implementation.md](docs/memory-implementation.md).

## Repository layout

```text
apps/web/                    Next.js operations console
services/control-plane/      FastAPI policy and memory critical path
packages/contracts/          Base receipt registry
packages/shared/             Shared TypeScript contracts
benchmark/                   Sibyl versus stateless comparison
docs/                        Architecture, evidence, and judging material
scripts/                     Safe demo and verification commands
```

## Current status

Development began at `2026-09-01T06:10:52Z`, inside the official September 1 to September 10, 2026 UTC build window. See [STATUS.md](STATUS.md) for checks actually run, live evidence, known limitations, and human actions still required.

## Quick start

The supported toolchain is Python 3.12 with [uv](https://docs.astral.sh/uv/) and Node.js 24 with npm.

```bash
uv sync --all-packages --all-extras --python 3.12
npm ci --prefix apps/web
```

Start the API and web console in separate terminals:

```bash
make api
make web
```

The web console uses a server-side allowlisted proxy to the control plane. It provides the operations overview, action gate, exact receipt evidence, cross-session timeline, counterparties, benchmark state, integration proof, and presenter controls. See [apps/web/README.md](apps/web/README.md) for environment configuration.

Run the load-bearing proof from the repository root:

```bash
make demo-reset
make demo-session-1
make demo-session-2
```

On Windows without GNU Make, run the equivalent commands:

```powershell
$demoDb = "$PWD\.data\demo\recallops-demo.db"
uv run --project services/control-plane python -m recallops.demo.reset --db $demoDb --confirm RESET_RECALLOPS_DEMO
uv run --project services/control-plane python -m recallops.demo.session1 --db $demoDb
uv run --project services/control-plane python -m recallops.demo.session2 --db $demoDb
```

Session output is structured JSON. It displays the session UUID, operating-system PID, UTC timestamp, Git commit, exact Sibyl writes or recalled records, reason codes, decision, and integration mode. `demo-reset` refuses every path except the exact project-owned `.data/demo/recallops-demo.db` target.

## Tests

```bash
make check
```

The root quality gate runs Ruff formatting and lint, mypy strict mode, real temporary SQLite and FTS5-capable Sibyl integration tests, tenant isolation, decimal policy tests, the separate-process proof, strict TypeScript, ESLint, Vitest, a Next.js production build, and Playwright. The latest executed results are recorded in [STATUS.md](STATUS.md).

## Benchmark results

Run the fixed 12-scenario comparison with seed `20260901`:

```bash
make benchmark
```

The latest executed run is `1627c118-32a7-5bc2-8c14-fdfe62db1849`. Production `SibylMemoryStore` achieved 0% unsafe repeats, 0% budget violations, 100% expected-decision accuracy, and 100% evidence completeness. The explicit benchmark-only stateless comparator produced 100%, 50%, 41.67%, and 0% respectively. Latency is reported, not hidden: the observed median was 62.697 ms for local Sibyl versus 0.005 ms for the comparator.

See the [human-readable report](benchmark/results/latest.md), [machine-readable JSON](benchmark/results/latest.json), and [CSV](benchmark/results/latest.csv). The baseline is never selectable in production.

## Deletion test

```bash
make deletion-test
```

With Sibyl deliberately unavailable, the production guard returns `ESCALATE` with `MEMORY_READ_FAILED`, performs no writes, and stops commerce. The explicit stateless comparator approves the same harmful rehire, proving the lost capability. The result is stored in [benchmark/results/deletion-test.json](benchmark/results/deletion-test.json).

## Partner integration status

### Virtuals integration

RecallOps now ships a policy-gated `VirtualsPort`, a visibly labeled fixture adapter, and a live adapter for the maintained ACP CLI JSON interface. Execution rechecks offering price and currency against the approved action, writes `VIRTUALS_DISPATCH_STARTED`, creates at most one job, persists the job in Sibyl, and links it back to the decision receipt. Fixture IDs always start with `fixture:` and never carry fake proof links.

Live dispatch is restricted to Base Sepolia and disabled by default even when `LIVE VIRTUALS` mode is selected. The current official CLI dependency tree has unresolved audit findings, so it is an operator-reviewed external prerequisite rather than a default application dependency. See [the live setup and audit note](docs/virtuals-live-setup.md).

Run `make partner-preflight` with `RECALLOPS_ACP_EXECUTABLE` set to the reviewed CLI path to check the official Base Sepolia RPC and perform read-only ACP provider discovery. The JSON report explicitly states that it performed no writes and requested no signatures.

### Base integration

`RecallOpsReceiptRegistry.sol` is implemented and locally proven. It accepts only non-sensitive digests, permits only Anvil `31337` or Base Sepolia `84532`, validates the chain at deployment and call time, restricts writes to one immutable submitter, treats an exact retry as a no-op, and rejects conflicting receipt reuse. The FastAPI anchor endpoint requires an `APPROVE` receipt, successful action-bound execution, a durable ACP job, and `VERIFIED_PASSED` before it invokes the typed viem client. The confirmed transaction is then written back to Sibyl.

The local Anvil deployment and viem transaction are reproducible but are not partner evidence. Base Sepolia signing remains disabled behind explicit configuration and approval gates. See [the deployment and approval guide](docs/base-deployment.md) and [local evidence](docs/evidence/base-local.md).

No real Virtuals ACP job or public Base Sepolia transaction has been recorded, so neither partner multiplier is claimed. Real identifiers will appear only after verifiable actions exist.

## Security and privacy

- Money uses decimal-safe representations.
- Secrets, raw memories, prompts, deliverables, and personal data are never anchored onchain.
- Economic execution uses idempotency keys and action-bound, expiring receipts.
- Fixture integrations are visibly labeled and never produce realistic fake job IDs or explorer links.
- Base mainnet and real-asset transfers are out of scope without explicit human approval.

See [SECURITY.md](SECURITY.md) for reporting and [docs/research/technical-discovery.md](docs/research/technical-discovery.md) for version choices.

## Known limitations

- The verified Sibyl deployment is local SQLite; hosted multi-node operation is not demonstrated.
- Virtuals fixture mode is complete, but no real ACP job exists yet.
- The Base registry is proven on local Anvil, but no Base Sepolia deployment or public transaction exists yet.
- The administrative boundary is one high-entropy token, not a multi-user identity system.
- In-process rate limiting is not implemented; public deployment requires an authenticated edge.
- Secondary research supports the problem hypothesis, but there are no claimed users or PMF signals.

## Prior Work

The repository existed before the build window only as GitHub's empty initial commit containing `.gitattributes`. All RecallOps product code and documentation is being created during the September 1 through September 10, 2026 UTC build window. The concept was specified before implementation; no pre-existing RecallOps code has been reused.

RecallOps depends on open-source projects including Sibyl Memory, FastAPI, Next.js, Virtuals ACP tooling, Foundry, and viem. Their work is not claimed as original RecallOps work.

## License

[MIT](LICENSE)

## Builder

Vu Tang, solo builder for the Sibyl Labs Hackathon 2026.
