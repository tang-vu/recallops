# Deployment Operations

The public RecallOps preview is available at <https://recallops.tangvu.dev>.

## Runtime topology

```text
Internet
   |
   v
Cloudflare Tunnel: recallops.tangvu.dev
   |
   v
Next.js: 127.0.0.1:3220
   |
   | allowlisted same-origin proxy
   v
FastAPI: 127.0.0.1:8820
   |
   v
Sibyl SQLite: %LOCALAPPDATA%/RecallOps/data/recallops.db
```

Only the Next.js service is routed through the tunnel. FastAPI and Sibyl remain reachable only from the host. The browser never receives the Sibyl path or administrative token.

## Process supervision

The checked-in [`ecosystem.config.cjs`](../ecosystem.config.cjs) defines three PM2 processes:

- `recallops-web`: production Next.js server
- `recallops-api`: Uvicorn and the FastAPI control plane
- `recallops-tunnel`: the dedicated Cloudflare Tunnel connector

The ecosystem file generates one high-entropy administrative token in memory and passes it to both server processes. It never prints or commits that value. PM2 persists the expanded process environment in its machine-local resurrection snapshot.

Build and start from PowerShell:

```powershell
npm run build --prefix apps/web
pm2 start ecosystem.config.cjs
pm2 save
```

Inspect or restart only RecallOps:

```powershell
pm2 list
pm2 logs recallops-api --lines 100 --nostream
pm2 logs recallops-web --lines 100 --nostream
pm2 logs recallops-tunnel --lines 100 --nostream
pm2 restart recallops-api recallops-web recallops-tunnel
pm2 save
```

Local and public health checks:

```powershell
Invoke-WebRequest http://127.0.0.1:8820/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:3220/api/control-plane/health -UseBasicParsing
Invoke-WebRequest https://recallops.tangvu.dev/api/control-plane/health -UseBasicParsing
```

## Durable state and secrets

Runtime data is intentionally outside the repository:

- Database: `%LOCALAPPDATA%/RecallOps/data/recallops.db`
- Logs: `%LOCALAPPDATA%/RecallOps/logs/`
- Tunnel config: `%LOCALAPPDATA%/RecallOps/cloudflared/config.yml`
- Tunnel credential: the host's protected Cloudflare credential directory

Do not copy the database into Git. Do not place the Cloudflare credential or PM2 dump in the repository. Normal demo history is retained; the deployment does not call the destructive demo reset command.

## Evidence labels

The hosted preview intentionally starts with:

- Sibyl: real durable local runtime
- Virtuals: `FIXTURE MODE`
- Base: `NOT CONFIGURED`

The tunnel does not change partner evidence. No Virtuals or Base multiplier may be claimed until a real ACP job and a real Base Sepolia transaction are separately recorded.
