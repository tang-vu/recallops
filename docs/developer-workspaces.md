# Developer workspaces

The developer preview adds a self-service decision gateway to the existing
commerce demo. `/` is the product entry, `/workspace` is the private console,
`/docs` is the integration guide, and `/demo` preserves the sample scenario.

## Run locally

Install the frozen Python dependencies with `uv sync --project services/control-plane --all-extras --frozen`
and the web dependencies with `npm ci --prefix apps/web`. Configure
`RECALLOPS_MEMORY_DB` to an absolute path on persistent local disk, start FastAPI
on loopback, and point the web server's `RECALLOPS_API_URL` at it.

Workspace files default to a `workspaces` sibling directory next to the demo
database. `RECALLOPS_WORKSPACE_DIR` overrides that directory. Keep it outside Git
on persistent storage. The public web server must use HTTPS in production;
owner session cookies are Secure, HttpOnly, SameSite=Strict, and expire after
seven days. Never expose the legacy FastAPI service directly to the Internet.

## User flow

1. Create a workspace with a name and one agent identifier.
2. Save the owner recovery key and agent key. The server persists only SHA-256
   hashes of 256-bit random keys; the UI shows plaintext keys only at issuance.
3. Save policy, task scope, budget window, and recorded spend. Policy changes
   use real Sibyl writes and retain superseded policy memory.
4. Evaluate requests in the playground or call `POST /api/workspace/evaluate`
   with a bearer key and an 8–128-character `Idempotency-Key`.
5. Record a verified failure as owner. A later matching provider/category/task
   fingerprint recalls the failure and changes the decision.
6. Inspect/filter the latest 100 receipts and export individual JSON records.
7. Pause access or rotate the agent key from the console.
8. Review escalated high-risk actions in Review queue. An owner reason is required;
   reviews persist in Sibyl and expire with the original five-minute receipt.
9. Immediately before execution, the agent calls
   `GET /api/workspace/decisions/{receipt_id}/authorization`. It must stop on a
   non-2xx response, `allowed_now=false`, or expiry.

## Owner review contract

`POST /api/workspace/decisions/{receipt_id}/review` accepts an owner-authenticated
JSON body with `decision` (`APPROVE` or `REJECT`) and `reason` (1–512 characters).
Only an unexpired `ESCALATE` receipt can be reviewed. Approval requires exactly
`HUMAN_APPROVAL_REQUIRED` in both the original receipt and a fresh memory check,
with the same policy version. An existing review is final: identical retries
return it; a changed verdict/reason receives 409. Reviews and their audit events
use Sibyl; the original policy receipt is not changed.

The authorization endpoint is available to agent and owner keys within the
workspace. It re-reads current policy, permission, budget, failure, and review
memory. Paused access, incomplete policy updates, changed policy versions,
expired receipts, owner rejection, or new failing checks stop authorization.
Both ordinary APPROVE receipts and owner-reviewed escalations need this check.
`allowed_now` describes the check instant; it is not an execution token or a
funds reservation. Clients must execute only the exact bound action and provide
their own atomic spending enforcement.

## Boundaries

- Every workspace has its own UUID-named Sibyl database. The registry holds
  identity, credential hashes, rate counters, and an editable configuration
  snapshot. It is never a substitute for Sibyl at the decision boundary.
- Owner identity, tenant, requesting agent, action ID, and action timestamp are
  assigned by the server. Agent keys can evaluate and check current authorization;
  owner keys control
  policy, failure reports, history, and key rotation.
- A registry write transaction serializes evaluations and key/config changes
  across worker processes. Identical concurrent evaluation retries return the
  same durable receipt; a different body under the same key receives 409.
- Policy updates touch several Sibyl records. Before an update, a stop marker
  is committed to the registry. If the process stops or a write fails, evaluation
  remains unavailable until the owner successfully saves the policy again.
- Browser writes require a matching Origin/Host or an explicit bearer key.
  The public gateway streams request bodies with a 16 KiB cap and does not
  forward user-selected upstream paths or tenant IDs.
- The initial service cap is 10 workspace creations per UTC hour per instance
  and 120 successful authenticated requests per UTC minute per workspace.
- Back up the whole workspace directory consistently while the API is stopped,
  including the identity registry and every Sibyl database. Losing the registry
  loses key associations. Losing Sibyl removes required decision evidence.

## Revoking a single receipt

An owner can open a request in Decision history and choose **Revoke this
receipt**, with a required reason. The API is
`POST /api/workspace/decisions/:receipt_id/revoke` with a JSON `reason`.
Agent keys cannot call it. The original policy receipt and any owner review
remain unchanged; a separate Sibyl entity retains the revocation, owner role,
action/receipt binding, reason, and timestamp.

Once successfully saved, the revocation cannot be removed. An identical retry
returns the same record; a different reason returns 409 rather than rewriting
history. Current authorization returns `allowed_now: false` with
`RECEIPT_REVOKED` for an unexpired revoked receipt, including after a policy
update or agent pause/resume. Replaying the original evaluation still returns
its historical receipt; it does not restore authorization.

Other receipts remain independently eligible. This stops one receipt at the
next authorization check, not an already running job or a different fresh
request. Broader stops belong in policy restrictions or the agent pause control.
If the revoke request fails, do not assume it saved: verify authorization or
pause access. Revocations are included in history JSON exports. Missing or
unreadable revocation state fails closed at the authorization boundary.

## Preview limits

The product gateway evaluates requests; it does not dispatch jobs, reserve
budgets, sign transactions, or reconcile payments. Spending checks compare the
request to owner-reported spend. An application that needs a hard concurrent
spending cap must enforce it in its own executor/ledger. This differs from the
separately gated fixture/partner execution path retained in the demo.

Clients must halt on non-2xx responses, network failures, DENY, and expired
receipts. ESCALATE pauses execution until a scoped owner review and a successful
current authorization check. An APPROVE receipt applies only to its exact proposed action.
A replay is historical evidence, not a new check against a changed policy. Use
a new action/key for a new intended attempt.

This preview supports one owner credential and one agent per workspace. It does
not include team accounts, email recovery, billing,
failure deletion, or high-availability storage. No automatic live deployment
is performed by building these routes.

## Validation

`test_workspaces.py` exercises real Sibyl isolation and persistence, role
boundaries, verified failure recall, policy/budget checks, key rotation, replay
conflicts and concurrency, durable owner reviews, authorization invalidation,
injected memory failures, interrupted policy recovery,
and durable creation limits. Playwright starts an isolated FastAPI instance with
temporary workspace storage and exercises the real browser-to-Sibyl flow on
desktop and mobile; the older demo scenario retains its network fixtures.
