# RecallOps Control Plane

This workspace owns policy evaluation, Sibyl Memory access, decision receipts, and guarded execution.

## Install

From the repository root:

```bash
uv sync --all-packages --all-extras --python 3.12
```

## Load-bearing proof

```bash
make demo-reset
make demo-session-1
make demo-session-2
```

Session 1 writes a task-scoped Agent A failure through the real Sibyl 0.8.0 SDK. Session 2 is a new operating-system process and recalls that record before evaluation. The exact match changes Agent A to `DENY`; Agent B receives `APPROVE` under the same budget and policy.

The database defaults to `.data/demo/recallops-demo.db`. Override `DEMO_DB` only for Session 1 and Session 2. Reset remains restricted to the exact project-owned default demo path.

## API

Set `RECALLOPS_MEMORY_DB` and generate a high-entropy `RECALLOPS_ADMIN_TOKEN`, then run:

```bash
make api
```

OpenAPI is served from `http://127.0.0.1:8000/v1/openapi.json`; interactive docs are at `/docs`. Administrative policy, budget, permission, exception, approval, and demo mutations require `X-RecallOps-Admin-Token`. Action evaluation and execution authorization require an `Idempotency-Key` of at least eight characters.

The Milestone 2 execute endpoint persists an action-bound authorization but reports `NOT_DISPATCHED` until a Virtuals adapter is configured. It never fabricates a job ID.
