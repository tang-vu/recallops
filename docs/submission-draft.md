# Submission Draft

Prepared only. Do not publish or submit without explicit approval from Vu Tang.

## Demo title

RecallOps: The Memory Gate That Stops Agents Repeating Expensive Mistakes

## Short description

RecallOps is a memory-gated control plane for autonomous agent commerce. Before an agent hires a provider, spends budget, reuses a permission, or authorizes payment, RecallOps retrieves durable policy and outcome history from Sibyl Memory and returns an inspectable `APPROVE`, `DENY`, or `ESCALATE` receipt.

## Submission description

Agent processes are disposable, but budgets, revocations, and failed counterparties are not. RecallOps puts Sibyl Memory on the execution critical path so a fresh session cannot repeat an economically harmful action simply because its in-process context disappeared.

In the deterministic two-process proof, Session 1 records Agent A's failed verification through Sibyl and terminates. Session 2 starts with a different PID and UUID, prefers Agent A because it is cheaper, recalls the earlier task-scoped failure, and denies the rehire. Agent B remains eligible. Every result contains reason codes, budget math, memory evidence, and a snapshot digest.

The FastAPI control plane enforces decimal-safe limits, cumulative budgets, permissions, revocations, exceptions, probation, verification, action binding, expiry, and idempotency. The Next.js operations console makes the fresh-session consequence and exact evidence visible. A 12-scenario benchmark compares the production Sibyl path with an explicit stateless baseline, while the deletion test proves that disabling Sibyl stops production commerce.

The repository also includes a guarded Virtuals ACP boundary and a digest-only Base receipt registry. Partner multipliers are claimed only if real public evidence is obtained before submission. Fixture ACP jobs and local Anvil transactions remain clearly labeled and are not presented as partner proof.

## Video description

One durable Sibyl database. Two separate operating-system processes. Session 1 records a provider failure and exits. Session 2 recalls that outcome, blocks the cheaper unsafe repeat, and selects an allowed alternative. The demo then shows deterministic evidence receipts, execution gates, the 12-scenario benchmark, and the Sibyl deletion test.

Repository: https://github.com/tang-vu/recallops

## Build-log post

Built RecallOps for the Sibyl Labs Hackathon 2026: a deterministic safety control plane for agent-to-agent commerce. The core proof is deliberately simple and load-bearing. One process records an economically relevant verification failure through Sibyl Memory. A fresh process retrieves it and changes the next hiring decision. Removing memory either stops commerce or, in the explicit stateless benchmark, repeats the unsafe action.

The shipped build includes a FastAPI policy engine, Next.js evidence console, guarded Virtuals ACP adapter, Base receipt registry, 12-scenario benchmark, cross-process tests, deletion proof, and security gates. No users, PMF, live partner jobs, or public testnet transactions are claimed without evidence.

## First X post

268 characters. Prepared for the Build in Public MCP `tweet` tool.

```text
Building RecallOps for the @sibylcap Hackathon.

A fresh agent can forget a failed provider, revoked permission, or spent budget. RecallOps puts Sibyl Memory before every economic action: APPROVE, DENY, or ESCALATE.

https://github.com/tang-vu/recallops #buildinpublic
```

The selected MCP tool supports text-only posts, so this first post does not use generated media. No image or AI metadata is involved.

## Demo launch post

RecallOps gives autonomous agent commerce a durable safety memory. It remembers budgets, revocations, permissions, verifier failures, and task-scoped counterparty outcomes across fresh processes, then returns an inspectable `APPROVE`, `DENY`, or `ESCALATE` before money can move.

Built for the Sibyl Labs Hackathon 2026. Demo and repository links to be added only after approval.

## Suggested tags

`Sibyl Memory`, `agentic commerce`, `AI agents`, `policy engine`, `Base`, `Base Sepolia`, `Virtuals ACP`, `agent safety`, `auditability`, `hackathon`

Remove `Base`, `Base Sepolia`, or `Virtuals ACP` from partner-claim fields if real evidence has not been obtained. Technology references in the architecture remain accurate, but multiplier claims require exercised public proof.
