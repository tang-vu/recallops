# Architecture

RecallOps is a control plane, not an execution wallet and not a chatbot. It owns the policy decision that must occur before any downstream economic adapter can act.

## Runtime boundaries

```text
Operations console (untrusted browser input)
                    |
                    | HTTPS / versioned OpenAPI
                    v
FastAPI control plane
  |-- input validation, admin boundary, correlation ID, redacted logs
  |-- CommerceGuard
  |     |-- mandatory Sibyl reads
  |     |-- deterministic PolicyEngine
  |     `-- mandatory Sibyl decision write
  |-- ExecutionGate
  |     |-- action and receipt binding
  |     |-- expiry and human approval checks
  |     `-- durable idempotent authorization
  |-- JobStateMachine
  |     |-- duplicate callback suppression
  |     |-- verifier result persistence
  |     `-- payment only after verification passes
  |
  |-- SibylMemoryStore (only production MemoryPort)
  |     `-- local SQLite + FTS5, tenant isolated
  |
  |-- VirtualsPort
  |     |-- VirtualsFixtureAdapter [explicit fixture IDs]
  |     `-- VirtualsLiveAdapter [ACP CLI JSON, Base Sepolia only]
  `-- Base receipt anchoring [Milestone 5]
```

The web application will call only the FastAPI boundary. It will never import the Sibyl SDK or access the SQLite file.

## Decision pipeline

```text
Proposed action
    |
    v
Validate strict schema and decimal money
    |
    v
Recall owner policy + budget + permission + counterparty outcomes + exception
    | memory failure
    +-------------------------> ESCALATE and stop
    |
    v
Evaluate deterministic hard rules
    |
    +--> DENY: revoked, prohibited, invalid permission, hard limit, matching failure
    +--> ESCALATE: missing/conflicting memory, low confidence, probation, human review
    `--> APPROVE: all required checks pass
    |
    v
Persist action-bound, expiring receipt and idempotency record
    |
    v
Authorize adapter dispatch exactly once
    |
    v
Verify job before payment, persist outcome, update future policy context
```

An LLM can propose an action or summarize evidence later, but it cannot choose or override the final enum.

## Durable data ownership

Sibyl Memory owns every production fact that can change an economic decision:

| Tier | RecallOps ownership |
| --- | --- |
| HOT | Current session, PID, commit, pending demo stage |
| WARM | Policies, budgets, permissions, exceptions, failure fingerprints, counterparty profiles, decisions, idempotency records, execution authorizations, jobs |
| COLD | Chronological policy, verification, decision, authorization, and job transition events |
| REFERENCE | Versioned policy schema and risk definition metadata |
| ARCHIVE | Superseded permissions, expired exceptions, and retired counterparties as lifecycle APIs are completed |

No PostgreSQL, Redis, browser storage, or shadow SQLite schema reproduces this function in production.

## State transitions

The execution gate and job state machine enforce these invariants:

- A receipt is bound to one tenant and action.
- An expired receipt cannot authorize execution.
- `DENY` never authorizes execution.
- `ESCALATE` requires an active human approval bound to the same receipt and action.
- Reusing the same idempotency key and payload returns the original result.
- Reusing a key or receipt with a different payload produces a conflict.
- Current Virtuals offering price and currency cannot exceed the approved action ceiling.
- A live ACP call is disabled by default even when live mode is selected.
- An uncertain ACP failure cannot be automatically retried from the same authorization.
- Duplicate provider callbacks return the existing job without another Sibyl write.
- Only `SUBMITTED` can become verified.
- Only `VERIFIED_PASSED` can become `PAYMENT_AUTHORIZED`.
- `VERIFIED_FAILED` creates a durable failure fingerprint and cannot be paid.

## Deployment shape

The root Compose service runs the control plane on loopback and persists the Sibyl file in a named Docker volume. Administrative mutations remain disabled unless `RECALLOPS_ADMIN_TOKEN` is explicitly set. The default integration labels are `FIXTURE MODE` and `LOCAL ONLY`.

The Next.js application reaches only the API through an allowlisted same-origin proxy. The Virtuals adapter runs inside the control plane only after the durable execution gate. Base anchoring remains a separate post-approval boundary.
