# Submission Draft

Prepared only. Do not publish or submit without explicit approval from Vu Tang.

## Demo title

RecallOps: The Memory Gate That Stops Agents Repeating Expensive Mistakes

## Short description

RecallOps gives agent developers a private workspace for durable policy and failure memory. Before a proposed action, it recalls Sibyl state and returns an inspectable `APPROVE`, `DENY`, or `ESCALATE` receipt. Owners can review high-risk requests and revoke individual receipts; agents recheck current authorization before execution.

## Submission description

Agent processes are disposable, but budgets, revocations, and failed counterparties are not. RecallOps puts Sibyl Memory on the execution critical path so a fresh session cannot repeat an economically harmful action simply because its in-process context disappeared.

In the deterministic two-process proof, Session 1 records Agent A's failed verification through Sibyl and terminates. Session 2 starts with a different PID and UUID, prefers Agent A because it is cheaper, recalls the earlier task-scoped failure, and denies the rehire. Agent B remains eligible. Every result contains reason codes, budget math, memory evidence, and a snapshot digest.

The developer product provides isolated Sibyl workspaces, separate owner and agent keys, editable policy, failure capture, decision history, and durable owner reviews. A review stays bound to its original action and expiry. Owners can revoke a single receipt with a reason saved in Sibyl, preserving the original decision and other receipts. Current authorization re-reads memory, so revocation, a new failure, changed policy, or paused agent can block a previously approved request. Revocation cannot undo completed execution or block a separately evaluated new request. Spending checks use owner-reported spend; the integrating application retains responsibility for execution and atomic budget enforcement.

The FastAPI control plane also implements permissions, revocations, exceptions, probation, verification, action binding, expiry, and idempotency. The Next.js console displays both fresh processes and their matching source-session evidence. A 12-scenario benchmark compares the production Sibyl path with an explicit stateless baseline, while the repository's deletion test proves that disabling required Sibyl reads stops production commerce.

The repository also includes a guarded Virtuals ACP boundary and a digest-only Base receipt registry. Partner multipliers are claimed only if real public evidence is obtained before submission. Fixture ACP jobs and local Anvil transactions remain clearly labeled and are not presented as partner proof.

## Video description

This continuous 2-minute-56-second recording shows the developer workspace, owner review, and current authorization flow, followed by two real operating-system processes using one durable Sibyl database. Session 1 records a provider failure and exits. Session 2 recalls that exact source session, denies Agent A, and approves Agent B. PID, UUID, UTC timestamp, and commit are visible. The recording closes with the deterministic benchmark and API guide. On-screen English captions explain the flow; there is no audio track. Deliverables and ACP dispatch are fixtures, with no live payment or partner transaction claimed.

Repository: https://github.com/tang-vu/recallops

## Build-log post

Built RecallOps for the Sibyl Labs Hackathon 2026: a deterministic safety control plane for agent-to-agent commerce. The core proof is deliberately simple and load-bearing. One process records an economically relevant verification failure through Sibyl Memory. A fresh process retrieves it and changes the next hiring decision. Removing memory either stops commerce or, in the explicit stateless benchmark, repeats the unsafe action.

The shipped build includes a FastAPI policy engine, Next.js evidence console, guarded Virtuals ACP adapter, Base receipt registry, 12-scenario benchmark, cross-process tests, deletion proof, and security gates. No users, PMF, live partner jobs, or public testnet transactions are claimed without evidence.

## First X post

267 characters. Published through the browser-backed Build in Public MCP on 2026-09-04.

```text
Autonomous agents should not forget expensive mistakes.

I built RecallOps for the @sibyl_labs_ Hackathon: durable policy memory that gates hiring, spending, permissions, and retries with APPROVE, DENY, or ESCALATE.

Live: https://recallops.tangvu.dev

#BuildInPublic
```

Published URL: `https://x.com/tangvu_dev/status/2095872903506215334`

The attached launch visual is stored at `docs/evidence/social/recallops-launch-light.png`. Its PNG contains only image header, image data, and end chunks; generated metadata and ancillary profiles were stripped.

## Demo launch post

RecallOps gives autonomous agent commerce a durable safety memory. It remembers budgets, revocations, permissions, verifier failures, and task-scoped counterparty outcomes across fresh processes, then returns an inspectable `APPROVE`, `DENY`, or `ESCALATE` before money can move.

Built for the Sibyl Labs Hackathon 2026. Demo and repository links to be added only after approval.

## Suggested tags

`Sibyl Memory`, `agentic commerce`, `AI agents`, `policy engine`, `Base`, `Base Sepolia`, `Virtuals ACP`, `agent safety`, `auditability`, `hackathon`

Remove `Base`, `Base Sepolia`, or `Virtuals ACP` from partner-claim fields if real evidence has not been obtained. Technology references in the architecture remain accurate, but multiplier claims require exercised public proof.
