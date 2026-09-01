# RecallOps Web

This Next.js application is the judge-facing operations console for RecallOps. It talks only to the FastAPI control plane through a same-origin, server-side route handler. The browser never receives a Sibyl database path or admin credential and never accesses Sibyl directly.

## Local setup

Install locked dependencies from the repository root:

```bash
npm ci --prefix apps/web
```

Start the control plane on `127.0.0.1:8000`, then start the web application:

```bash
npm --prefix apps/web run dev
```

The console is available at `http://127.0.0.1:3000`. Configure the server-only proxy with:

```text
RECALLOPS_API_URL=http://127.0.0.1:8000
RECALLOPS_ADMIN_TOKEN=<same value configured on the control plane>
```

`RECALLOPS_ADMIN_TOKEN` is needed only for the presenter Session 1 and Session 2 controls. It is never prefixed with `NEXT_PUBLIC_` and is not bundled into browser JavaScript.

## Quality gates

```bash
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run build
npm --prefix apps/web run test:e2e
```

Playwright starts an isolated Next.js server on port 41789 and uses test-only network fixtures. The separate manual smoke test documented in `STATUS.md` exercises the real Next.js proxy, FastAPI API, and Sibyl database together.
