# RecallOps Web

This Next.js application includes the public product site, private developer workspace console, API guide, and the sample demo at `/demo`. Server-side route handlers connect it to the FastAPI control plane. The browser never receives a Sibyl database path or admin credential and never accesses Sibyl directly. See [developer workspaces](../../docs/developer-workspaces.md) for setup, key handling, and operating limits.

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

Playwright requires `uv` and the frozen Python dependencies. It starts isolated Next.js and FastAPI servers on ports 41789 and 41790, using temporary workspace databases. Workspace tests exercise real Sibyl; the sample demo test uses network fixtures.
