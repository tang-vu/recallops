"use client";

import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import type { DecisionReceipt } from "@/lib/types";
import {
  ReviewQueue,
  type AuthorizationCheck,
  type OwnerReview,
} from "@/components/review-queue";

type Policy = {
  per_action_limit: string;
  cumulative_budget: string;
  recorded_spend: string;
  currency: string;
  chain: string;
  permission: string;
  task_categories: string[];
  prohibited_providers: string[];
  require_verifier: boolean;
  high_risk_requires_human: boolean;
  agent_enabled: boolean;
  window_ends_at: string;
};
type Workspace = {
  id: string;
  name: string;
  agent_id: string;
  policy: Policy;
  memory_healthy: boolean;
};
type Action = {
  provider_id: string;
  offering: string;
  task_category: string;
  task_fingerprint: string;
  requested_amount: string;
  currency: string;
  chain: string;
  permission: string;
  required_verifier: string | null;
  risk_class: string;
};
type History = {
  receipt: DecisionReceipt;
  action: Action | null;
  review?: OwnerReview | null;
};
class WorkspaceError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function api<T>(
  path = "",
  method = "GET",
  body?: unknown,
  idempotencyKey?: string,
): Promise<T> {
  const response = await fetch(`/api/workspace${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((item: { msg: string }) => item.msg).join(" ")
          : "Request failed. Please retry.";
    throw new WorkspaceError(detail, response.status);
  }
  return data as T;
}

export function WorkspaceConsole() {
  const queryClient = useQueryClient();
  const workspace = useQuery({
    queryKey: ["workspace"],
    queryFn: () => api<Workspace>(),
    retry: false,
  });
  const [keys, setKeys] = useState<{
    owner_key?: string;
    agent_key: string;
  } | null>(null);
  async function entered(newKeys?: { owner_key?: string; agent_key: string }) {
    setKeys(newKeys ?? null);
    queryClient.removeQueries({ queryKey: ["workspace-history"] });
    await queryClient.invalidateQueries({ queryKey: ["workspace"] });
  }
  return (
    <main id="main-content" className="product-shell workspace-shell">
      <header className="product-nav">
        <Link className="product-brand" href="/">
          RecallOps<span>MEMORY AUTHORITY</span>
        </Link>
        <nav>
          <Link href="/docs">API guide</Link>
          <Link href="/demo">Sample demo</Link>
        </nav>
      </header>
      {workspace.isPending ? (
        <div className="workspace-empty" role="status">
          Opening your workspace…
        </div>
      ) : workspace.error ? (
        workspace.error instanceof WorkspaceError &&
        workspace.error.status === 401 ? (
          <WorkspaceEntry onEntered={entered} />
        ) : (
          <div className="workspace-empty">
            <p role="alert">{workspace.error.message}</p>
            <button
              className="secondary-button"
              onClick={() => void workspace.refetch()}
            >
              Retry connection
            </button>
          </div>
        )
      ) : workspace.data ? (
        <WorkspaceBody
          key={workspace.data.id}
          workspace={workspace.data}
          keys={keys}
          setKeys={setKeys}
          onChanged={() =>
            queryClient.invalidateQueries({ queryKey: ["workspace"] })
          }
          onLogout={async () => {
            await api("/session", "DELETE");
            setKeys(null);
            queryClient.removeQueries({ queryKey: ["workspace-history"] });
            await workspace.refetch();
          }}
        />
      ) : null}
    </main>
  );
}

function WorkspaceEntry({
  onEntered,
}: {
  onEntered: (keys?: {
    owner_key?: string;
    agent_key: string;
  }) => Promise<void>;
}) {
  const [login, setLogin] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      if (login) {
        await api("/session", "POST", { owner_key: form.get("owner_key") });
        await onEntered();
      } else {
        const result = await api<{ owner_key: string; agent_key: string }>(
          "",
          "POST",
          { name: form.get("name"), agent_id: form.get("agent_id") },
        );
        await onEntered(result);
      }
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="workspace-entry">
      <div>
        <p className="eyebrow">YOUR AGENT’S CHECKPOINT</p>
        <h1>
          Start with a boundary.
          <br />
          <em>Build a memory.</em>
        </h1>
        <p>
          Create a private workspace, set your policy, and connect an agent with
          its own API key.
        </p>
        <ol>
          <li>Set limits and allowed task categories.</li>
          <li>Evaluate a real request before executing it.</li>
          <li>Record failures so later attempts remember.</li>
        </ol>
        <p className="data-note">
          Developer preview: access uses a generated owner key. Save it when
          shown; email recovery is not available.
        </p>
      </div>
      <form className="workspace-card" onSubmit={submit}>
        <h2>{login ? "Open your workspace" : "Create a workspace"}</h2>
        {login ? (
          <label>
            Owner recovery key
            <input
              name="owner_key"
              type="password"
              autoComplete="off"
              required
              placeholder="ro_owner_…"
            />
          </label>
        ) : (
          <>
            <label>
              Workspace name
              <input
                name="name"
                required
                maxLength={80}
                placeholder="Acme agent operations"
              />
            </label>
            <label>
              Agent identifier
              <input
                name="agent_id"
                required
                defaultValue="my-agent"
                pattern="[a-zA-Z0-9_-]{1,64}"
                maxLength={64}
              />
              <small>Letters, numbers, hyphens, or underscores.</small>
            </label>
          </>
        )}
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        <button className="primary-button" disabled={busy}>
          {busy ? "Opening…" : login ? "Open workspace" : "Create workspace →"}
        </button>
        <button
          className="quiet-button"
          type="button"
          disabled={busy}
          onClick={() => {
            setLogin(!login);
            setError("");
          }}
        >
          {login ? "Create a new workspace" : "Already have an owner key?"}
        </button>
      </form>
    </section>
  );
}

function WorkspaceBody({
  workspace,
  keys,
  setKeys,
  onChanged,
  onLogout,
}: {
  workspace: Workspace;
  keys: { owner_key?: string; agent_key: string } | null;
  setKeys: (keys: { owner_key?: string; agent_key: string } | null) => void;
  onChanged: () => Promise<unknown>;
  onLogout: () => Promise<void>;
}) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("overview");
  const [busy, setBusy] = useState(false);
  const history = useQuery({
    queryKey: ["workspace-history", workspace.id],
    queryFn: () => api<History[]>("/decisions"),
    retry: false,
    refetchInterval: tab === "reviews" && !busy ? 10_000 : false,
  });
  const [checks, setChecks] = useState<Record<string, AuthorizationCheck>>({});
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<DecisionReceipt | null>(null);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [pendingEvaluation, setPendingEvaluation] = useState<{
    body: string;
    key: string;
  } | null>(null);
  async function perform(operation: () => Promise<void>, success = "") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await operation();
      setNotice(success);
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function refreshHistory() {
    await queryClient.invalidateQueries({
      queryKey: ["workspace-history", workspace.id],
    });
  }
  const decisions = history.data ?? [];
  const policy = workspace.policy;
  function actionFrom(form: FormData): Action {
    return {
      provider_id: String(form.get("provider_id")),
      offering: String(form.get("offering")),
      task_category: String(form.get("task_category")),
      task_fingerprint: String(form.get("task_fingerprint")),
      requested_amount: String(form.get("requested_amount")),
      currency: policy.currency,
      chain: policy.chain,
      permission: policy.permission,
      required_verifier: String(form.get("required_verifier")) || null,
      risk_class: String(form.get("risk_class")),
    };
  }
  return (
    <>
      <section className="workspace-heading">
        <div>
          <p className="eyebrow">PRIVATE WORKSPACE / {workspace.agent_id}</p>
          <h1>{workspace.name}</h1>
          <code>{workspace.id}</code>
        </div>
        <div className="button-row">
          <span
            className={`status-pill ${workspace.memory_healthy ? "green" : "red"}`}
          >
            {workspace.memory_healthy
              ? "Memory connected"
              : "Memory unavailable"}
          </span>
          <button
            className="quiet-button"
            disabled={busy}
            onClick={() => void perform(onLogout)}
          >
            Sign out
          </button>
        </div>
      </section>
      {keys && (
        <section
          className="workspace-key-card"
          aria-label="Workspace credentials"
        >
          <h2>Save your keys now.</h2>
          <p>
            Keys are shown only here. Keep the owner key for access to this
            workspace; give only the agent key to your application.
          </p>
          {keys.owner_key && (
            <label>
              Owner recovery key<code>{keys.owner_key}</code>
            </label>
          )}
          <label>
            Agent API key<code>{keys.agent_key}</code>
          </label>
          <button className="secondary-button" onClick={() => setKeys(null)}>
            I’ve saved my keys
          </button>
        </section>
      )}
      <nav className="workspace-tabs" aria-label="Workspace sections">
        {[
          ["overview", "Overview"],
          ["policy", "Policy & access"],
          ["evaluate", "Request playground"],
          ["history", "Decision history"],
          ["reviews", "Review queue"],
          ["failures", "Record a failure"],
          ["connect", "Connect agent"],
        ].map(([id, label]) => (
          <button
            key={id}
            aria-current={tab === id ? "page" : undefined}
            disabled={busy}
            onClick={() => {
              setTab(id);
              setResult(null);
              setError("");
              setNotice("");
            }}
          >
            {label}
          </button>
        ))}
      </nav>
      {error && (
        <p className="alert danger" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="inline-note" role="status">
          {notice}
        </p>
      )}
      {tab === "overview" && (
        <>
          <div className="workspace-stats">
            {[
              ["Evaluated", decisions.length],
              [
                "Approved",
                decisions.filter(
                  ({ receipt }) => receipt.decision === "APPROVE",
                ).length,
              ],
              [
                "Denied",
                decisions.filter(({ receipt }) => receipt.decision === "DENY")
                  .length,
              ],
              [
                "Needs review",
                decisions.filter(
                  ({ receipt }) => receipt.decision === "ESCALATE",
                ).length,
              ],
            ].map(([label, value]) => (
              <article key={label}>
                <span>{label}</span>
                <strong>
                  {history.isPending ? "…" : history.isError ? "—" : value}
                </strong>
                <small>Latest 100 decisions</small>
              </article>
            ))}
          </div>
          {history.isError && (
            <p role="alert">
              History unavailable.{" "}
              <button onClick={() => void history.refetch()}>Retry</button>
            </p>
          )}
          <div className="workspace-columns">
            <section className="workspace-card">
              <p className="eyebrow">ACTIVE BOUNDARIES</p>
              <h2>
                {policy.agent_enabled
                  ? "Agent access enabled"
                  : "Agent access paused"}
              </h2>
              <dl className="workspace-facts">
                <div>
                  <dt>Per-action limit</dt>
                  <dd>
                    {policy.per_action_limit} {policy.currency}
                  </dd>
                </div>
                <div>
                  <dt>Recorded spend / budget</dt>
                  <dd>
                    {policy.recorded_spend} / {policy.cumulative_budget}{" "}
                    {policy.currency}
                  </dd>
                </div>
                <div>
                  <dt>Allowed tasks</dt>
                  <dd>
                    {policy.task_categories.join(", ") || "All categories"}
                  </dd>
                </div>
                <div>
                  <dt>Window ends</dt>
                  <dd>
                    {new Date(policy.window_ends_at).toLocaleDateString()}
                  </dd>
                </div>
              </dl>
              <button
                className="secondary-button"
                onClick={() => setTab("policy")}
              >
                Edit policy →
              </button>
            </section>
            <section className="workspace-card">
              <p className="eyebrow">NEXT STEP</p>
              <h2>
                {decisions.length
                  ? "Turn outcomes into memory."
                  : "Make your first decision."}
              </h2>
              <p>
                {decisions.length
                  ? "Record a verified provider failure, then evaluate the same task again to see the recalled evidence."
                  : "Your workspace starts empty. Use the playground to evaluate your own provider, task, and amount."}
              </p>
              <button
                className="primary-button"
                onClick={() =>
                  setTab(decisions.length ? "failures" : "evaluate")
                }
              >
                {decisions.length ? "Record a failure" : "Open playground"} →
              </button>
              <p className="data-note">
                This gateway evaluates requests. Your application must enforce
                the verdict before execution. Spend is owner-reported; approvals
                do not reserve funds.
              </p>
            </section>
          </div>
        </>
      )}
      {tab === "reviews" &&
        (history.isPending ? (
          <p role="status">Loading review queue…</p>
        ) : history.isError ? (
          <div className="alert danger" role="alert">
            {history.error.message}
            <button
              className="secondary-button"
              onClick={() => void history.refetch()}
            >
              Retry
            </button>
          </div>
        ) : (
          <ReviewQueue
            items={decisions}
            busy={busy}
            checks={checks}
            onReview={(id, decision, reason) =>
              void perform(async () => {
                await queryClient.cancelQueries({
                  queryKey: ["workspace-history", workspace.id],
                });
                const saved = await api<{ review: OwnerReview }>(
                  `/decisions/${id}/review`,
                  "POST",
                  {
                    decision,
                    reason,
                  },
                );
                queryClient.setQueryData<History[]>(
                  ["workspace-history", workspace.id],
                  (previous) =>
                    previous?.map((item) =>
                      item.receipt.receipt_id === id
                        ? { ...item, review: saved.review }
                        : item,
                    ),
                );
              }, "Owner review saved. The agent must check current authorization before execution.")
            }
            onCheck={(id) =>
              void perform(async () => {
                const check = await api<AuthorizationCheck>(
                  `/decisions/${id}/authorization`,
                );
                setChecks((previous) => ({ ...previous, [id]: check }));
              })
            }
          />
        ))}
      {tab === "policy" && (
        <form
          className="workspace-card"
          key={JSON.stringify(policy)}
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void perform(async () => {
              const updated = {
                ...policy,
                per_action_limit: form.get("per_action_limit"),
                cumulative_budget: form.get("cumulative_budget"),
                recorded_spend: form.get("recorded_spend"),
                currency: form.get("currency"),
                chain: form.get("chain"),
                window_ends_at: new Date(
                  `${String(form.get("window_ends_at"))}Z`,
                ).toISOString(),
                task_categories: String(form.get("task_categories"))
                  .split(",")
                  .map((v) => v.trim())
                  .filter(Boolean),
                prohibited_providers: String(form.get("prohibited_providers"))
                  .split(",")
                  .map((v) => v.trim())
                  .filter(Boolean),
                require_verifier: form.has("require_verifier"),
                high_risk_requires_human: form.has("high_risk_requires_human"),
                agent_enabled: form.has("agent_enabled"),
              };
              await api("/policy", "PUT", updated);
              await onChanged();
            }, "Policy saved to durable memory.");
          }}
        >
          <h2>Policy & agent access</h2>
          <p>
            Changes apply to new evaluations. A saved decision is a historical
            record, not a permanent execution permit.
          </p>
          <div className="workspace-form-grid">
            <label>
              Per-action limit
              <input
                name="per_action_limit"
                type="number"
                min="0"
                step="0.000001"
                defaultValue={policy.per_action_limit}
                required
              />
            </label>
            <label>
              Cumulative budget
              <input
                name="cumulative_budget"
                type="number"
                min="0"
                step="0.000001"
                defaultValue={policy.cumulative_budget}
                required
              />
            </label>
            <label>
              Recorded spend
              <input
                name="recorded_spend"
                type="number"
                min="0"
                step="0.000001"
                defaultValue={policy.recorded_spend}
                required
              />
            </label>
            <label>
              Currency
              <input
                name="currency"
                pattern="[A-Z0-9]{2,12}"
                defaultValue={policy.currency}
                required
              />
            </label>
            <label>
              Chain
              <input
                name="chain"
                defaultValue={policy.chain}
                maxLength={64}
                required
              />
            </label>
            <label>
              Window ends (UTC)
              <input
                type="datetime-local"
                name="window_ends_at"
                defaultValue={policy.window_ends_at.slice(0, 16)}
                required
              />
            </label>
            <label>
              Allowed task categories
              <input
                name="task_categories"
                defaultValue={policy.task_categories.join(", ")}
              />
              <small>Comma-separated. Empty allows all categories.</small>
            </label>
            <label>
              Blocked provider IDs
              <input
                name="prohibited_providers"
                defaultValue={policy.prohibited_providers.join(", ")}
              />
              <small>Comma-separated, exact provider IDs.</small>
            </label>
          </div>
          <div className="workspace-checks">
            <label>
              <input
                type="checkbox"
                name="agent_enabled"
                defaultChecked={policy.agent_enabled}
              />{" "}
              Allow {workspace.agent_id} to request {policy.permission}
            </label>
            <label>
              <input
                type="checkbox"
                name="require_verifier"
                defaultChecked={policy.require_verifier}
              />{" "}
              Require a verifier on each action
            </label>
            <label>
              <input
                type="checkbox"
                name="high_risk_requires_human"
                defaultChecked={policy.high_risk_requires_human}
              />{" "}
              Escalate high-risk actions for human review
            </label>
          </div>
          <p className="data-note">
            Recorded spend is maintained by the owner. This preview does not
            reserve budgets or reconcile payments. Update spend from your ledger
            before evaluating new spending.
          </p>
          <button className="primary-button" disabled={busy}>
            {busy ? "Saving…" : "Save policy"}
          </button>
        </form>
      )}
      {tab === "evaluate" && (
        <div className="workspace-columns">
          <form
            className="workspace-card"
            onChange={() => setResult(null)}
            onSubmit={(event) => {
              event.preventDefault();
              const payload = actionFrom(new FormData(event.currentTarget));
              const body = JSON.stringify(payload);
              const key =
                pendingEvaluation?.body === body
                  ? pendingEvaluation.key
                  : crypto.randomUUID();
              setPendingEvaluation({ body, key });
              void perform(async () => {
                setResult(null);
                const response = await api<{ receipt: DecisionReceipt }>(
                  "/evaluate",
                  "POST",
                  payload,
                  key,
                );
                setResult(response.receipt);
                setPendingEvaluation(null);
                await refreshHistory();
              });
            }}
          >
            <h2>Request playground</h2>
            <p>
              Evaluate against your saved policy and memory. No job or payment
              is executed.
            </p>
            <fieldset disabled={busy} className="workspace-fields">
              <ActionFields policy={policy} />
            </fieldset>
            <button
              className="primary-button"
              disabled={busy || !workspace.memory_healthy}
            >
              {busy ? "Recalling memory…" : "Evaluate request →"}
            </button>
          </form>
          <section className="workspace-card" aria-live="polite">
            {result ? (
              <Verdict receipt={result} />
            ) : (
              <div className="workspace-empty">
                <p className="eyebrow">AWAITING REQUEST</p>
                <h2>The reason matters.</h2>
                <p>
                  Your decision, reason codes, and recalled memory will appear
                  here.
                </p>
              </div>
            )}
          </section>
        </div>
      )}
      {tab === "history" && (
        <section className="workspace-card">
          <div className="workspace-section-head">
            <div>
              <h2>Decision history</h2>
              <p>
                Latest 100 durable receipts. Expand a decision to inspect its
                evidence.
              </p>
            </div>
            <button
              className="secondary-button"
              disabled={history.isFetching}
              onClick={() => void history.refetch()}
            >
              Refresh
            </button>
          </div>
          <div className="workspace-form-grid">
            <label>
              Search provider or task
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Provider, fingerprint, reason…"
              />
            </label>
            <label>
              Decision
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                {["ALL", "APPROVE", "DENY", "ESCALATE"].map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
          </div>
          {history.isPending ? (
            <p role="status">Loading history…</p>
          ) : history.isError ? (
            <p role="alert">{history.error.message}</p>
          ) : (
            <>
              <div className="workspace-history">
                {decisions
                  .filter(
                    (item) =>
                      (filter === "ALL" || item.receipt.decision === filter) &&
                      JSON.stringify(item)
                        .toLowerCase()
                        .includes(search.toLowerCase()),
                  )
                  .map((item) => (
                    <details key={item.receipt.receipt_id}>
                      <summary>
                        <span
                          className={`workspace-verdict ${item.receipt.decision.toLowerCase()}`}
                        >
                          {item.receipt.decision}
                        </span>
                        <strong>
                          {item.action?.provider_id ?? "Unknown provider"}
                        </strong>
                        <span>{item.action?.task_category}</span>
                        <time>
                          {new Date(item.receipt.created_at).toLocaleString()}
                        </time>
                      </summary>
                      <p>
                        {item.action?.offering} ·{" "}
                        {item.action?.requested_amount} {item.action?.currency}
                      </p>
                      <code>{item.action?.task_fingerprint}</code>
                      <Verdict receipt={item.receipt} />
                      <button
                        className="quiet-button"
                        onClick={() => {
                          const url = URL.createObjectURL(
                            new Blob([JSON.stringify(item, null, 2)], {
                              type: "application/json",
                            }),
                          );
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = `recallops-${item.receipt.receipt_id}.json`;
                          a.click();
                          URL.revokeObjectURL(url);
                        }}
                      >
                        Download receipt JSON
                      </button>
                    </details>
                  ))}
              </div>
              {!decisions.some(
                (item) =>
                  (filter === "ALL" || item.receipt.decision === filter) &&
                  JSON.stringify(item)
                    .toLowerCase()
                    .includes(search.toLowerCase()),
              ) && (
                <div className="workspace-empty">
                  {decisions.length
                    ? "No decisions match your filters."
                    : "No decisions yet. Evaluate your first request in the playground."}
                </div>
              )}
            </>
          )}
        </section>
      )}
      {tab === "failures" && (
        <form
          className="workspace-card"
          onSubmit={(event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const fields = new FormData(form);
            void perform(async () => {
              await api("/failures", "POST", Object.fromEntries(fields));
              form.reset();
            }, "Failure saved. Future matching requests will recall this evidence.");
          }}
        >
          <h2>Record a verified failure</h2>
          <p>
            Use an actual outcome from your verifier or review process. A
            matching provider, task category, and fingerprint will be remembered
            on future evaluations.
          </p>
          <div className="workspace-form-grid">
            <label>
              Provider ID
              <input
                name="provider_id"
                required
                maxLength={128}
                placeholder="audit-provider"
              />
            </label>
            <label>
              Task category
              <input
                name="task_category"
                required
                maxLength={128}
                defaultValue={policy.task_categories[0] ?? ""}
              />
            </label>
            <label>
              Task fingerprint
              <input
                name="task_fingerprint"
                required
                maxLength={256}
                placeholder="dependency-audit:v1"
              />
            </label>
            <label>
              Verifier ID
              <input
                name="verifier_id"
                required
                maxLength={128}
                placeholder="schema-verifier-v1"
              />
            </label>
          </div>
          <label>
            What failed?
            <textarea
              name="verification_reason"
              required
              maxLength={512}
              rows={4}
              placeholder="Required evidence was missing from the deliverable."
            />
          </label>
          <p className="data-note">
            Failure evidence persists across sessions. This preview retains
            recorded failures; review the details before saving.
          </p>
          <button className="primary-button" disabled={busy}>
            {busy ? "Saving…" : "Save failure to memory"}
          </button>
        </form>
      )}
      {tab === "connect" && (
        <section className="workspace-card">
          <p className="eyebrow">ONE REQUEST BEFORE EVERY ACTION</p>
          <h2>Connect {workspace.agent_id}</h2>
          <p>
            Use the agent key in the Authorization header. It can evaluate
            requests and check current authorization; it cannot change policy,
            read history, or write failure
            evidence.
          </p>
          <pre className="workspace-code">{`const response = await fetch("${typeof window === "undefined" ? "" : window.location.origin}/api/workspace/evaluate", {
  method: "POST",
  headers: {
    "Authorization": "Bearer " + process.env.RECALLOPS_AGENT_KEY,
    "Content-Type": "application/json",
    "Idempotency-Key": actionId // stable for retries of this request
  },
  body: JSON.stringify(${JSON.stringify({ provider_id: "audit-provider", offering: "Dependency audit", task_category: policy.task_categories[0] ?? "security-review", task_fingerprint: "dependency-audit:v1", requested_amount: "1.00", currency: policy.currency, chain: policy.chain, permission: policy.permission, required_verifier: "schema-verifier-v1", risk_class: "LOW" }, null, 2)})
});
if (!response.ok) throw new Error("Stop: decision unavailable");
const { receipt } = await response.json();
// For ESCALATE, pause and ask the owner to review in the console.
// After review, use this same check; never treat ESCALATE as approval.
const authorization = await fetch(
  "${typeof window === "undefined" ? "" : window.location.origin}/api/workspace/decisions/" + receipt.receipt_id + "/authorization",
  { headers: { "Authorization": "Bearer " + process.env.RECALLOPS_AGENT_KEY } }
);
if (!authorization.ok) throw new Error("Stop: authorization unavailable");
const permit = await authorization.json();
if (!permit.allowed_now) throw new Error(permit.reason_code);
if (Date.parse(permit.expires_at) <= Date.now()) throw new Error("Decision expired");
// Execute this exact action through your own application.
// A decision does not reserve funds or execute a payment.`}</pre>
          <div className="workspace-section-head">
            <div>
              <h3>Replace the agent key</h3>
              <p>
                Rotating immediately revokes the previous agent key. Update your
                application with the replacement.
              </p>
            </div>
            <button
              className="secondary-button"
              disabled={busy}
              onClick={() =>
                void perform(async () => {
                  const replacement = await api<{ agent_key: string }>(
                    "/keys/rotate",
                    "POST",
                    {},
                  );
                  setKeys(keys ? { ...keys, ...replacement } : replacement);
                })
              }
            >
              Rotate agent key
            </button>
          </div>
          <Link href="/docs">Read the API contract and operating limits →</Link>
        </section>
      )}
      <footer className="product-footer">
        <span>Private workspace / Sibyl-backed decisions</span>
        <Link href="/docs">API & operating limits</Link>
      </footer>
    </>
  );
}

function ActionFields({ policy }: { policy: Policy }) {
  return (
    <div className="workspace-form-grid">
      <label>
        Provider ID
        <input
          name="provider_id"
          required
          maxLength={128}
          placeholder="audit-provider"
        />
      </label>
      <label>
        Task category
        <input
          name="task_category"
          required
          maxLength={128}
          defaultValue={policy.task_categories[0] ?? "security-review"}
        />
      </label>
      <label>
        Offering
        <input
          name="offering"
          required
          maxLength={256}
          placeholder="Dependency audit"
        />
      </label>
      <label>
        Task fingerprint
        <input
          name="task_fingerprint"
          required
          maxLength={256}
          placeholder="dependency-audit:v1"
        />
      </label>
      <label>
        Amount ({policy.currency})
        <input
          name="requested_amount"
          type="number"
          min="0"
          step="0.000001"
          defaultValue="1.00"
          required
        />
      </label>
      <label>
        Risk
        <select name="risk_class">
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((risk) => (
            <option key={risk}>{risk}</option>
          ))}
        </select>
      </label>
      <label>
        Verifier ID
        <input
          name="required_verifier"
          maxLength={128}
          placeholder="schema-verifier-v1"
        />
      </label>
      <p className="data-note">
        Permission: {policy.permission}
        <br />
        Chain: {policy.chain}
      </p>
    </div>
  );
}

function Verdict({ receipt }: { receipt: DecisionReceipt }) {
  return (
    <div className="workspace-receipt">
      <span className={`workspace-verdict ${receipt.decision.toLowerCase()}`}>
        {receipt.decision}
      </span>
      <h3>{receipt.human_summary}</h3>
      <div className="reason-row">
        {receipt.reason_codes.map((reason) => (
          <code key={reason}>{reason}</code>
        ))}
      </div>
      <dl className="workspace-facts">
        <div>
          <dt>Budget before / after if approved</dt>
          <dd>
            {receipt.budget_before} / {receipt.budget_after_if_approved}
          </dd>
        </div>
        <div>
          <dt>Policy version</dt>
          <dd>
            <code>{receipt.policy_version}</code>
          </dd>
        </div>
      </dl>
      <h4>Recalled evidence</h4>
      {receipt.memory_evidence.length ? (
        receipt.memory_evidence.map((evidence, index) => (
          <details key={index}>
            <summary>{evidence.record_type.replaceAll("_", " ")}</summary>
            <p>{evidence.why_it_mattered}</p>
            <pre>{JSON.stringify(evidence.content, null, 2)}</pre>
          </details>
        ))
      ) : (
        <p>
          No durable evidence available. Do not proceed without a valid
          decision.
        </p>
      )}
      <small>Receipt {receipt.receipt_id}</small>
    </div>
  );
}
