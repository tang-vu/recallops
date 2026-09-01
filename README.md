# RecallOps

**Memory-gated control plane for autonomous agent commerce**

RecallOps uses durable policy and outcome memory to decide whether an autonomous agent may hire, pay, or reuse another agent. Every proposed economic action receives exactly one inspectable decision: `APPROVE`, `DENY`, or `ESCALATE`.

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
- Disabling mandatory memory changes the safe result to `ESCALATE`; the explicit benchmark-only stateless baseline demonstrates the unsafe repeat separately.

Production reads and writes are easy to locate in:

- [Sibyl production adapter](services/control-plane/src/recallops/memory/sibyl_store.py): explicit HOT, WARM, COLD, and REFERENCE SDK calls
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

The supported control-plane toolchain is Python 3.12 with [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-packages --all-extras --python 3.12
```

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

The Milestone 1 quality gate runs Ruff formatting and lint, mypy strict mode, real temporary SQLite and FTS5-capable Sibyl integration tests, tenant isolation, decimal policy tests, and the separate-process proof. The latest executed results are recorded in [STATUS.md](STATUS.md).

## Partner integration status

Virtuals ACP and Base Sepolia are not yet claimed. Current demo execution remains `NOT_EXECUTED` after Agent B approval and clearly says why. Real partner identifiers will appear only after verifiable actions exist.

## Security and privacy

- Money uses decimal-safe representations.
- Secrets, raw memories, prompts, deliverables, and personal data are never anchored onchain.
- Economic execution uses idempotency keys and action-bound, expiring receipts.
- Fixture integrations are visibly labeled and never produce realistic fake job IDs or explorer links.
- Base mainnet and real-asset transfers are out of scope without explicit human approval.

See [SECURITY.md](SECURITY.md) for reporting and [docs/research/technical-discovery.md](docs/research/technical-discovery.md) for version choices.

## Prior Work

The repository existed before the build window only as GitHub's empty initial commit containing `.gitattributes`. All RecallOps product code and documentation is being created during the September 1 through September 10, 2026 UTC build window. The concept was specified before implementation; no pre-existing RecallOps code has been reused.

RecallOps depends on open-source projects including Sibyl Memory, FastAPI, Next.js, Virtuals ACP tooling, Foundry, and viem. Their work is not claimed as original RecallOps work.

## License

[MIT](LICENSE)

## Builder

Vu Tang, solo builder for the Sibyl Labs Hackathon 2026.
