# Public Deployment Evidence

Recorded on September 4, 2026 UTC.

## Endpoint

- Public UI: <https://recallops.tangvu.dev>
- Public proxied health: <https://recallops.tangvu.dev/api/control-plane/health>
- Origin API: loopback-only and not directly exposed

The deployment runs from the public [`tang-vu/recallops`](https://github.com/tang-vu/recallops) repository. Cloudflare DNS routes the hostname to a dedicated RecallOps tunnel, and the existing machine-level PM2 resurrection task includes the three RecallOps processes in its saved snapshot.

## Checks actually executed

All of these returned HTTP 200:

- `http://127.0.0.1:8820/health`
- `http://127.0.0.1:3220/`
- `http://127.0.0.1:3220/api/control-plane/health`
- `https://recallops.tangvu.dev/`
- `https://recallops.tangvu.dev/api/control-plane/health`

The Cloudflare connector registered four healthy edge connections. A headless Chromium request loaded the public page, submitted the default Agent A action through the real Next.js proxy and FastAPI control plane, and observed:

- Decision: `DENY`
- Reason: `REPEATED_FAILURE_FINGERPRINT`
- Recalled evidence: owner policy, budget account, permission grant, and matching failure fingerprint

## Hosted fresh-process proof

The public demo controls launched two separate Python operating-system processes against the deployed Sibyl database.

Session 1:

- PID: `9072`
- Session UUID: `348cf61b-7c1d-4f38-90b1-929a59c0f25d`
- Git commit: `79617dbf2a0bfa60087ec30583b5e643fa69315c`
- Result: Agent A failed deterministic verification; HOT, WARM, COLD, and REFERENCE records were written through Sibyl

Session 2:

- PID: `41436`
- Session UUID: `18ac5c4f-4197-44a9-b9d1-b4761c921681`
- Git commit: `79617dbf2a0bfa60087ec30583b5e643fa69315c`
- Result: the new process recalled Session 1's failure, denied Agent A, approved Agent B, and created an explicitly labeled `fixture:` ACP lifecycle record

The different process IDs and session UUIDs are returned by the runtime itself. The database path is redacted in the public UI to its basename.

## Claim boundary

This evidence proves the public UI, control-plane proxy, persistent Sibyl database, and fresh-process policy recall. It is not evidence of a real Virtuals ACP job or a Base Sepolia transaction. The public interface accurately displays `FIXTURE MODE` and `BASE NOT CONFIGURED`.
