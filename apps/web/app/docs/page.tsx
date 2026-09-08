import Link from "next/link";

export default function Docs() {
  return (
    <main id="main-content" className="product-shell">
      <header className="product-nav">
        <Link className="product-brand" href="/">
          RecallOps<span>MEMORY AUTHORITY</span>
        </Link>
        <nav>
          <Link href="/demo">Demo</Link>
          <Link className="primary-button" href="/workspace">
            Open workspace →
          </Link>
        </nav>
      </header>
      <article className="workspace-card product-docs">
        <p className="eyebrow">DEVELOPER GUIDE / PREVIEW</p>
        <h1>A checkpoint before your agent acts.</h1>
        <p>
          RecallOps evaluates proposed actions against durable owner policy,
          permission, budget, and failure memory. Your application owns
          execution and must stop on DENY, ESCALATE, an expired receipt, a
          network failure, or an unsuccessful HTTP response.
        </p>
        <h2>1. Create a private workspace</h2>
        <p>
          Open the workspace console, name your workspace, and choose an agent
          identifier. Save the owner recovery key and agent API key when shown.
          The owner key opens the console again; it is not an agent credential.
          There is no email account recovery in this preview.
        </p>
        <h2>2. Configure policy</h2>
        <p>
          Set the per-action limit, cumulative budget, recorded spend, allowed
          task categories, blocked providers, and expiry. Currency and chain
          must match each request. The initial permission is{" "}
          <code>hire-agent</code>. Pause agent access from Policy &amp; access.
        </p>
        <h2>3. Evaluate before execution</h2>
        <p>
          Send JSON to <code>POST /api/workspace/evaluate</code> with{" "}
          <code>Authorization: Bearer YOUR_AGENT_KEY</code> and an{" "}
          <code>Idempotency-Key</code> of 8–128 characters. The Connect agent
          tab generates a JavaScript example for your saved policy.
        </p>
        <pre className="workspace-code">
          {JSON.stringify(
            {
              provider_id: "audit-provider",
              offering: "Dependency audit",
              task_category: "security-review",
              task_fingerprint: "dependency-audit:v1",
              requested_amount: "1.00",
              currency: "USDC",
              chain: "base-sepolia",
              permission: "hire-agent",
              required_verifier: "schema-verifier-v1",
              risk_class: "LOW",
            },
            null,
            2,
          )}
        </pre>
        <p>
          Use decimal strings for money. Keep the same idempotency key and
          identical body when retrying a network request. Reusing a key for a
          different request returns 409. A new intended action needs a new key.
          Tenant, owner, agent identity, and timestamps are assigned by the
          server.
        </p>
        <p>
          The response contains <code>receipt</code> and{" "}
          <code>idempotent_replay</code>. Inspect <code>receipt.decision</code>,{" "}
          <code>human_summary</code>, <code>reason_codes</code>,{" "}
          <code>memory_evidence</code>, and <code>expires_at</code>. An APPROVE
          result only covers the exact proposed action. A replay returns the
          historical decision, not a fresh policy check.
        </p>
        <h2>4. Record failures</h2>
        <p>
          Use Record a failure in the console after verifying an actual failure.
          Match the provider ID, task category, and fingerprint used by future
          requests. The next matching attempt recalls that evidence. Only the
          owner key can record failures; agent keys cannot fabricate policy
          changes or alter failure history.
        </p>
        <h2>5. Review high-risk actions</h2>
        <p>
          The owner can approve or reject an escalated request in Review queue,
          with a required audit reason. Only HUMAN_APPROVAL_REQUIRED can receive
          approval; missing evidence, denied requests, and expired receipts
          cannot be overridden. A review expires with its original five-minute
          receipt and does not rewrite that receipt.
        </p>
        <p>
          Immediately before execution, call{" "}
          <code>GET /api/workspace/decisions/RECEIPT_ID/authorization</code>{" "}
          with the agent key. Proceed only when the HTTP response succeeds,{" "}
          <code>allowed_now</code> is true, and <code>expires_at</code> is still
          in the future. This rechecks current memory and access. A changed
          policy, paused agent, newly recorded failure, or rejection blocks the
          action even after owner approval. A new request needs its own review.
        </p>
        <h2>API surface</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Method</th>
                <th>Path</th>
                <th>Access</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["POST", "/api/workspace", "Create workspace"],
                ["GET", "/api/workspace", "Owner"],
                ["PUT", "/api/workspace/policy", "Owner"],
                ["GET", "/api/workspace/decisions", "Owner · latest 100"],
                ["POST", "/api/workspace/failures", "Owner"],
                [
                  "POST",
                  "/api/workspace/keys/rotate",
                  "Owner · replaces agent key",
                ],
                ["POST", "/api/workspace/evaluate", "Agent or owner"],
                [
                  "POST",
                  "/api/workspace/decisions/:id/review",
                  "Owner · decision and reason",
                ],
                [
                  "GET",
                  "/api/workspace/decisions/:id/authorization",
                  "Agent or owner · current permission",
                ],
              ].map(([method, path, access]) => (
                <tr key={method + path}>
                  <td>{method}</td>
                  <td>
                    <code>{path}</code>
                  </td>
                  <td>{access}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h2>Operating limits</h2>
        <ul>
          <li>
            This is a decision gateway. It does not execute jobs, sign
            transactions, or reserve funds. Your executor must enforce the
            verdict.
          </li>
          <li>
            Budget checks use owner-reported spend. Keep it synchronized with
            your ledger. Concurrent approvals do not provide an atomic spending
            cap.
          </li>
          <li>
            One owner key and one agent per workspace. The browser session lasts
            seven days. Rotating the agent key revokes its predecessor
            immediately.
          </li>
          <li>
            Owner reviews are action-bound and expire with their receipt. The
            authorization check does not dispatch a job or reserve funds; keep
            the check and your executor close together and enforce your own
            ledger.
          </li>
          <li>
            Failure evidence is retained. There is no failure deletion or
            account recovery workflow in this preview.
          </li>
          <li>
            The initial service cap is 10 new workspaces per hour across the
            instance and 120 successful authenticated requests per minute per
            workspace. Public requests are limited to 16 KiB.
          </li>
          <li>
            Workspace storage lives on the server’s persistent disk. Operators
            must back up both workspace metadata and Sibyl database files.
          </li>
        </ul>
      </article>
      <footer className="product-footer">
        <span>RecallOps / Developer preview</span>
        <Link href="/workspace">Build your first policy →</Link>
      </footer>
    </main>
  );
}
