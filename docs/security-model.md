# Security Model

RecallOps assumes proposed tasks, provider metadata, callbacks, and paid endpoint responses are untrusted. Owner policy and human approvals are privileged control-plane records.

## Protected assets

- Owner policy and permission integrity
- Cumulative budget accuracy across sessions
- Counterparty outcome history
- Decision and execution authorization binding
- Wallet and partner credentials outside the repository
- Private memories, deliverables, prompts, and personal data

## Trust boundaries

| Boundary | Trust level | Control |
| --- | --- | --- |
| Browser or agent to FastAPI | Untrusted | Strict Pydantic schemas, 1 MiB request cap, no unknown fields |
| Administrative mutation | Privileged | Constant-time comparison of `X-RecallOps-Admin-Token`; disabled when unconfigured |
| Control plane to Sibyl | Mandatory local dependency | Tenant-specific client, explicit lifecycle, fail-closed errors |
| Control plane to Virtuals | External and economic | Dispatch requires durable action-bound authorization; secrets stay in OS keychain |
| Control plane to Base | Public and irreversible | Sepolia allowlist, digest-only payload, approval-before-anchor ordering |

## Threats and implemented controls

### Memory unavailable or corrupt

Missing policy, missing budget, invalid memory payloads, SDK errors, and missing idempotency results return `ESCALATE` or stop the request. RecallOps never substitutes another production store and never defaults to `APPROVE`.

### Tenant data leakage

Every store is opened with the action's tenant identifier. Deterministic entity names do not replace Sibyl tenant isolation. Integration tests write the same owner name under two tenants and prove the second cannot retrieve the first tenant's policy.

### Permission and approval replay

Permissions carry owner, agent, provider, task category, validity window, and revocation state. Execution receipts bind action ID, tenant, expiry, and evidence digest. Human approvals bind the exact receipt and action. A different idempotency payload produces HTTP 409.

### Duplicate callbacks and double payment

Job callback IDs are durably retained in the job entity. A duplicate callback returns the current record with no additional writes. Payment authorization is reachable only from `VERIFIED_PASSED`; a failed verification is terminal for payment.

### Prompt injection and malicious metadata

Natural-language rationale is inert data and never interpreted as policy. The deterministic engine ignores instructions asking it to override memory. Unknown action fields and oversized rationale are rejected. External deliverables and paid API responses will remain untrusted verifier inputs.

### Secret disclosure

Request logs contain method, path, status, and correlation ID, not bodies or headers. The recursive redactor covers tokens, authorization fields, seed phrases, private keys, OTPs, cards, CVVs, and email content. `.env`, database files, keys, wallet material, and private evidence are ignored by Git.

### Unsafe deletion

The reset command resolves its target and accepts only the exact project-owned `.data/demo/recallops-demo.db` file. It requires the literal confirmation `RESET_RECALLOPS_DEMO`. Normal Sibyl databases are never reset by that command.

## Onchain privacy

The planned Base registry receives only non-sensitive digests and enum metadata. Raw policy, memory bodies, prompts, deliverables, emails, and personal data stay offchain. A digest proves content consistency only when the verifier has the original content; it does not make private data recoverable.

## Current limitations

- The local admin token is a coarse-grained control, not a multi-user identity system.
- The Sibyl SQLite file relies on operating-system and volume permissions; application-level encryption at rest is not added.
- Rate limiting is expected at the deployment edge and is not implemented in-process yet.
- Virtuals and Base live adapters are not configured, so no partner credential path has been exercised.
- Dependency audit covers known published advisories, not undisclosed vulnerabilities.
