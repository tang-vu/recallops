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
