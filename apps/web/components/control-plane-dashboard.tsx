"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import { summarizeDecisions } from "@/lib/metrics";
import type {
  BaseAnchorRecord,
  BenchmarkMetrics,
  BenchmarkReport,
  CounterpartyEntity,
  Decision,
  DecisionReceipt,
  EvaluationResponse,
  ExecutionResponse,
  JobRecord,
  JournalEvent,
  SystemStatus,
} from "@/lib/types";

const TENANT_ID = "recallops-demo";
const NAV_ITEMS = [
  ["overview", "Overview"],
  ["action", "Action request"],
  ["receipt", "Decision receipt"],
  ["memory", "Memory evidence"],
  ["counterparties", "Counterparties"],
  ["benchmark", "Benchmark"],
  ["integrations", "Integration proof"],
  ["demo", "Demo mode"],
] as const;

function statusClass(decision: Decision): string {
  return `decision-${decision.toLowerCase()}`;
}

function short(value: string | null | undefined, length = 12): string {
  if (!value) return "Not available";
  return value.length > length * 2 ? `${value.slice(0, length)}...${value.slice(-8)}` : value;
}

function displayError(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : "Unexpected error";
}

export function ControlPlaneDashboard() {
  const queryClient = useQueryClient();
  const [provider, setProvider] = useState("agent-a");
  const [amount, setAmount] = useState("1.00");
  const [risk, setRisk] = useState("MEDIUM");
  const [receipt, setReceipt] = useState<DecisionReceipt | null>(null);
  const [executionNote, setExecutionNote] = useState<string | null>(null);
  const [demoResult, setDemoResult] = useState<Record<string, unknown> | null>(null);

  const statusQuery = useQuery({
    queryKey: ["system-status"],
    queryFn: () => apiRequest<SystemStatus>("v1/system/status"),
  });
  const decisionsQuery = useQuery({
    queryKey: ["decisions", TENANT_ID],
    queryFn: () => apiRequest<DecisionReceipt[]>(`v1/decisions?tenant_id=${TENANT_ID}&limit=100`),
  });
  const evidenceQuery = useQuery({
    queryKey: ["evidence", TENANT_ID],
    queryFn: () => apiRequest<JournalEvent[]>(`v1/memory/evidence?tenant_id=${TENANT_ID}&limit=100`),
  });
  const counterpartiesQuery = useQuery({
    queryKey: ["counterparties", TENANT_ID],
    queryFn: () => apiRequest<CounterpartyEntity[]>(`v1/counterparties?tenant_id=${TENANT_ID}&limit=100`),
  });
  const benchmarkQuery = useQuery({
    queryKey: ["benchmark"],
    queryFn: () => apiRequest<BenchmarkReport>("v1/benchmark/latest"),
  });
  const jobsQuery = useQuery({
    queryKey: ["jobs", TENANT_ID],
    queryFn: () => apiRequest<JobRecord[]>(`v1/jobs?tenant_id=${TENANT_ID}&limit=20`),
  });

  const metrics = useMemo(() => summarizeDecisions(decisionsQuery.data ?? []), [decisionsQuery.data]);
  const latestReceipt = receipt ?? decisionsQuery.data?.[0] ?? null;
  const anchorQuery = useQuery({
    queryKey: ["base-anchor", latestReceipt?.receipt_id],
    queryFn: () => apiRequest<BaseAnchorRecord>(`v1/decisions/${latestReceipt?.receipt_id}/anchor?tenant_id=${TENANT_ID}`),
    enabled: Boolean(latestReceipt?.base_transaction_hash),
  });

  const evaluateMutation = useMutation({
    mutationFn: async () => {
      const actionId = crypto.randomUUID();
      const sessionId = crypto.randomUUID();
      const proposed = {
        action_id: actionId,
        tenant_id: TENANT_ID,
        owner_id: "vu-tang",
        requesting_agent_id: "procurement-agent",
        provider_id: provider,
        offering: "Deterministic dependency audit",
        task_category: "security-review",
        task_fingerprint: "sha256:dependency-audit-v1",
        requested_amount: amount,
        currency: "USDC",
        chain: "base-sepolia",
        session_id: sessionId,
        required_verifier: "deterministic-schema-verifier-v1",
        risk_class: risk,
        permission: "hire-agent",
        proposed_at: new Date().toISOString(),
        rationale: provider === "agent-a" ? "Prefer Agent A because it is cheaper." : "Use the selected provider.",
        evidence_confidence: "1.0",
      };
      return apiRequest<EvaluationResponse>("v1/actions/evaluate", {
        method: "POST",
        headers: { "Idempotency-Key": `web-evaluate-${crypto.randomUUID()}` },
        body: JSON.stringify(proposed),
      });
    },
    onSuccess: async (result) => {
      setReceipt(result.receipt);
      setExecutionNote(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["decisions", TENANT_ID] }),
        queryClient.invalidateQueries({ queryKey: ["evidence", TENANT_ID] }),
      ]);
      document.querySelector("#receipt")?.scrollIntoView({ behavior: "smooth" });
    },
  });

  const executeMutation = useMutation({
    mutationFn: async () => {
      if (!receipt) throw new Error("Evaluate an action first.");
      return apiRequest<ExecutionResponse>(
        `v1/actions/${receipt.action_id}/execute?tenant_id=${encodeURIComponent(receipt.tenant_id)}`,
        {
          method: "POST",
          headers: { "Idempotency-Key": `web-execute-${receipt.receipt_id}` },
          body: JSON.stringify({
            receipt_id: receipt.receipt_id,
            adapter_payload: { outputFormat: "JSON evidence report" },
          }),
        },
      );
    },
    onSuccess: async (result) => {
      const jobReference = result.job ? ` Job ${result.job.job_id}.` : "";
      setExecutionNote(`${result.executor_status}: ${result.note}${jobReference}`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["decisions", TENANT_ID] }),
        queryClient.invalidateQueries({ queryKey: ["evidence", TENANT_ID] }),
        queryClient.invalidateQueries({ queryKey: ["jobs", TENANT_ID] }),
      ]);
    },
  });

  const demoMutation = useMutation({
    mutationFn: (session: 1 | 2) =>
      apiRequest<{ result: Record<string, unknown> }>(`v1/demo/session-${session}`, { method: "POST", body: "{}" }),
    onSuccess: async ({ result }) => {
      setDemoResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["decisions", TENANT_ID] }),
        queryClient.invalidateQueries({ queryKey: ["evidence", TENANT_ID] }),
        queryClient.invalidateQueries({ queryKey: ["counterparties", TENANT_ID] }),
      ]);
    },
  });

  function submitAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    evaluateMutation.mutate();
  }

  const status = statusQuery.data;
  const connected = Boolean(status?.memory_healthy);
  const latestJob = jobsQuery.data?.[0] ?? null;

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="RecallOps navigation">
        <a className="brand" href="#overview" aria-label="RecallOps overview">
          <span className="brand-mark">R</span>
          <span>
            <strong>RecallOps</strong>
            <small>CONTROL PLANE</small>
          </span>
        </a>
        <nav>
          {NAV_ITEMS.map(([href, label], index) => (
            <a href={`#${href}`} key={href} className={index === 0 ? "active" : undefined}>
              <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
              {label}
            </a>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className={`health-dot ${connected ? "healthy" : "offline"}`} aria-hidden="true" />
          <span>
            <strong>{connected ? "Sibyl connected" : "Commerce stopped"}</strong>
            <small>{status?.memory_path_hint ?? "Memory unavailable"}</small>
          </span>
        </div>
      </aside>

      <main id="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">PROTECTED AGENT</p>
            <h1>Procurement Agent <span>/ vu-tang</span></h1>
          </div>
          <div className="mode-row" aria-label="Integration modes">
            <span className={`mode-badge ${connected ? "live" : "danger"}`}>SIBYL {connected ? "HEALTHY" : "UNAVAILABLE"}</span>
            <span className="mode-badge fixture">{status?.virtuals_mode ?? "FIXTURE MODE"}</span>
            <span className="mode-badge local">BASE {status?.base_mode ?? "NOT CONFIGURED"}</span>
          </div>
        </header>

        <div className="content">
          <section id="overview" className="section-block" aria-labelledby="overview-title">
            <div className="section-heading">
              <div><p className="eyebrow">SYSTEM OVERVIEW</p><h2 id="overview-title">Economic memory at a glance</h2></div>
              <button className="quiet-button" onClick={() => void statusQuery.refetch()}>Refresh state</button>
            </div>
            <div className="metric-grid">
              <Metric label="Memory health" value={connected ? "Healthy" : "Unavailable"} tone={connected ? "green" : "red"} note={connected ? `Schema ready · ${status?.memory_path_hint}` : "Fail-closed ESCALATE"} />
              <Metric label="Actions evaluated" value={decisionsQuery.isLoading ? "..." : String(metrics.evaluated)} note="Durable receipts in current tenant" />
              <Metric label="Unsafe repeats prevented" value={decisionsQuery.isLoading ? "..." : String(metrics.unsafeRepeatsPrevented)} tone="red" note="Matching failure fingerprints" />
              <Metric label="Approved actions" value={decisionsQuery.isLoading ? "..." : String(metrics.approvals)} tone="green" note="Approval is not execution" />
            </div>
            {!connected && <div className="alert danger"><strong>Commerce is stopped.</strong> Mandatory Sibyl Memory is not healthy; RecallOps will not default to approval.</div>}
          </section>

          <section id="action" className="section-block" aria-labelledby="action-title">
            <div className="section-heading"><div><p className="eyebrow">PRE-EXECUTION GATE</p><h2 id="action-title">Evaluate an action request</h2></div><span className="sequence">01 RECALL · 02 DECIDE · 03 AUTHORIZE</span></div>
            <form className="action-card" onSubmit={submitAction}>
              <div className="form-grid">
                <label>Task<input value="Dependency security audit" readOnly /></label>
                <label>Provider<select value={provider} onChange={(event) => { const selected = event.target.value; setProvider(selected); if (selected === "agent-a") setAmount("1.00"); if (selected === "agent-b") setAmount("1.50"); }}><option value="agent-a">Agent A · 1.00 USDC</option><option value="agent-b">Agent B · 1.50 USDC</option><option value="agent-c">Agent C · untested</option></select></label>
                <label>Offering<input value="Deterministic dependency audit" readOnly /></label>
                <label>Requested amount<div className="input-suffix"><input inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} aria-label="Requested amount in USDC" /><span>USDC</span></div></label>
                <label>Risk class<select value={risk} onChange={(event) => setRisk(event.target.value)}><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label>
                <label>Permission<input value="hire-agent" readOnly /></label>
              </div>
              <div className="form-footer">
                <p><span className="health-dot healthy" /> Evaluation reads policy, budget, permission, and outcome memory before returning a decision.</p>
                <div className="button-row">
                  <button type="submit" className="primary-button" disabled={evaluateMutation.isPending || !connected}>{evaluateMutation.isPending ? "Evaluating..." : "Evaluate action"}</button>
                  <button type="button" className="execute-button" disabled={!receipt || receipt.decision !== "APPROVE" || executeMutation.isPending} onClick={() => executeMutation.mutate()}>{executeMutation.isPending ? "Authorizing..." : "Authorize execution"}</button>
                </div>
              </div>
              {evaluateMutation.isError && <p className="inline-error" role="alert">{displayError(evaluateMutation.error)}</p>}
              {executeMutation.isError && <p className="inline-error" role="alert">{displayError(executeMutation.error)}</p>}
              {executionNote && <p className="inline-note" role="status">{executionNote}</p>}
            </form>
          </section>

          <section id="receipt" className="section-block" aria-labelledby="receipt-title">
            <div className="section-heading"><div><p className="eyebrow">INSPECTABLE OUTPUT</p><h2 id="receipt-title">Decision receipt</h2></div>{latestReceipt && <code>{short(latestReceipt.receipt_id, 8)}</code>}</div>
            {latestReceipt ? <Receipt receipt={latestReceipt} /> : <EmptyState title="No receipt yet" body="Evaluate an action to see the durable decision, exact reason codes, budget computation, and recalled evidence." />}
          </section>

          <section id="memory" className="section-block" aria-labelledby="memory-title">
            <div className="section-heading"><div><p className="eyebrow">CROSS-SESSION TIMELINE</p><h2 id="memory-title">Memory evidence</h2></div><span>{evidenceQuery.data?.length ?? 0} journal events</span></div>
            <div className="timeline">
              {(evidenceQuery.data ?? []).slice(0, 12).map((event) => <TimelineEvent event={event} key={event.id} />)}
              {!evidenceQuery.isLoading && !evidenceQuery.data?.length && <EmptyState title="No memory events" body="Run Session 1 to write policy and a verification failure through Sibyl." />}
              {evidenceQuery.isError && <InlineUnavailable error={evidenceQuery.error} />}
            </div>
          </section>

          <section id="counterparties" className="section-block" aria-labelledby="counterparties-title">
            <div className="section-heading"><div><p className="eyebrow">TASK-SCOPED TRUST</p><h2 id="counterparties-title">Counterparties</h2></div><span>No global reputation shortcuts</span></div>
            <div className="table-wrap"><table><thead><tr><th>Provider</th><th>Task category</th><th>Success</th><th>Failed</th><th>Fingerprint</th><th>Status</th></tr></thead><tbody>
              {(counterpartiesQuery.data ?? []).map((entity) => <tr key={entity.id}><td><strong>{entity.body.provider_id ?? "Unknown"}</strong></td><td>{entity.body.task_category ?? "Unknown"}</td><td>{entity.body.successful_jobs ?? 0}</td><td>{entity.body.failed_jobs ?? 0}</td><td><code>{short(entity.body.last_failure_fingerprint, 10)}</code></td><td><span className={`status-pill ${entity.status === "probation" ? "amber" : "green"}`}>{entity.status ?? "active"}</span></td></tr>)}
              {!counterpartiesQuery.data?.length && <tr><td colSpan={6}>No counterparty outcomes have been recorded.</td></tr>}
            </tbody></table></div>
          </section>

          <section id="benchmark" className="section-block" aria-labelledby="benchmark-title">
            <div className="section-heading"><div><p className="eyebrow">DELETION TEST</p><h2 id="benchmark-title">With memory vs. stateless baseline</h2></div><span className={`status-pill ${benchmarkQuery.data?.available ? "green" : "amber"}`}>{benchmarkQuery.data?.available ? "12 SCENARIOS" : "NOT RUN"}</span></div>
            <div className="benchmark-grid"><BenchmarkColumn title="Sibyl Memory" tone="green" metrics={benchmarkQuery.data?.summary?.sibyl_memory} /><BenchmarkColumn title="Stateless comparison" tone="red" metrics={benchmarkQuery.data?.summary?.stateless_baseline} /></div>
            <p className="data-note">{benchmarkQuery.data?.available ? `Reproducible run ${benchmarkQuery.data.run_id} · seed ${benchmarkQuery.data.seed}. The stateless baseline is benchmark-only and never selectable in production.` : `${benchmarkQuery.data?.reason ?? "No benchmark artifact has been persisted."} No metrics are invented.`}</p>
          </section>

          <section id="integrations" className="section-block" aria-labelledby="integrations-title">
            <div className="section-heading"><div><p className="eyebrow">VERIFIABLE, NOT DECORATIVE</p><h2 id="integrations-title">Integration proof</h2></div></div>
            <div className="integration-grid">
              <IntegrationCard name="Sibyl Memory" status={connected ? "VERIFIED LOCAL" : "UNAVAILABLE"} tone={connected ? "green" : "red"} rows={[["Database", status?.memory_path_hint ?? "Redacted"], ["Runtime", "sibyl-memory-client 0.8.0"], ["Evidence", "Reads and writes on critical path"]]} />
              <IntegrationCard name="Virtuals ACP" status={status?.virtuals_mode ?? "FIXTURE MODE"} tone={latestJob?.integration_mode === "LIVE VIRTUALS" ? "green" : "amber"} rows={[["ACP job", latestJob?.job_id ?? "No job recorded"], ["Adapter", "ACP CLI boundary ready"], ["Claim", latestJob?.integration_mode === "LIVE VIRTUALS" ? "Live evidence recorded" : "Not claimed"]]} />
              <IntegrationCard name="Base" status={status?.base_mode ?? "NOT CONFIGURED"} tone={status?.base_mode === "BASE SEPOLIA" && latestReceipt?.base_transaction_hash ? "green" : "amber"} rows={[["Network", `${status?.base_mode ?? "Not configured"} · ${status?.base_chain_id ?? 84532}`], ["Transaction", latestReceipt?.base_transaction_hash ?? "No transaction recorded"], ["Claim", status?.base_mode === "BASE SEPOLIA" && latestReceipt?.base_transaction_hash ? "Live evidence recorded" : "Not claimed"]]} explorerUrl={anchorQuery.data?.explorer_url} />
            </div>
          </section>

          <section id="demo" className="section-block" aria-labelledby="demo-title">
            <div className="section-heading"><div><p className="eyebrow">PRESENTER CONTROLS</p><h2 id="demo-title">Fresh-process demo</h2></div><span className="mode-badge fixture">FIXTURE MODE · REAL SIBYL</span></div>
            <div className="demo-card"><div><h3>One durable database, two operating-system processes</h3><p>Session 1 writes Agent A&apos;s failed verification and exits. Session 2 starts with a new PID and UUID, recalls that failure, denies Agent A, and selects Agent B.</p></div><div className="button-row"><button className="secondary-button" disabled={demoMutation.isPending} onClick={() => demoMutation.mutate(1)}>Run Session 1</button><button className="primary-button" disabled={demoMutation.isPending} onClick={() => demoMutation.mutate(2)}>Run Session 2</button></div></div>
            {demoMutation.isError && <InlineUnavailable error={demoMutation.error} />}
            {demoResult && <pre className="demo-output" aria-label="Latest demo process output">{JSON.stringify(demoResult, null, 2)}</pre>}
          </section>
        </div>
      </main>
    </div>
  );
}

function Metric({ label, value, note, tone = "neutral" }: { label: string; value: string; note: string; tone?: string }) {
  return <article className={`metric-card ${tone}`}><p>{label}</p><strong>{value}</strong><small>{note}</small></article>;
}

function Receipt({ receipt }: { receipt: DecisionReceipt }) {
  const requested = Number(receipt.budget_after_if_approved) - Number(receipt.budget_before);
  return <article className={`receipt-card ${statusClass(receipt.decision)}`}>
    <div className="receipt-hero"><div><p>FINAL POLICY DECISION</p><strong>{receipt.decision}</strong><span>{receipt.human_summary}</span></div><div className="receipt-seal" aria-hidden="true">{receipt.decision === "APPROVE" ? "✓" : receipt.decision === "DENY" ? "×" : "!"}</div></div>
    <div className="reason-row">{receipt.reason_codes.map((code) => <code key={code}>{code}</code>)}</div>
    <div className="receipt-grid"><dl><dt>Budget before</dt><dd>{receipt.budget_before} USDC</dd><dt>Requested</dt><dd>{Number.isFinite(requested) ? requested.toFixed(2) : "Unknown"} USDC</dd><dt>After if approved</dt><dd>{receipt.budget_after_if_approved} USDC</dd></dl><dl><dt>Policy version</dt><dd>{receipt.policy_version}</dd><dt>Session</dt><dd><code>{short(receipt.session_id, 8)}</code></dd><dt>Evidence digest</dt><dd><code>{short(receipt.memory_snapshot_digest, 10)}</code></dd></dl></div>
    <div className="evidence-list"><h3>Memories that changed this decision</h3>{receipt.memory_evidence.map((item) => <details key={`${item.record_type}-${item.record_name}`}><summary><span className="tier-tag">{item.tier}</span><strong>{item.record_type.replaceAll("_", " ")}</strong><span>{item.why_it_mattered}</span></summary><pre>{JSON.stringify(item.content, null, 2)}</pre></details>)}</div>
  </article>;
}

function TimelineEvent({ event }: { event: JournalEvent }) {
  const kind = String(event.extra?.event_type ?? "MEMORY_EVENT");
  return <article className="timeline-event"><div className="timeline-marker" /><div><p><span className="tier-tag">COLD</span><time dateTime={event.ts}>{new Date(event.ts).toLocaleString()}</time></p><h3>{kind.replaceAll("_", " ")}</h3><p>{event.acted?.[0] ?? event.evaluated?.[0] ?? "Durable Sibyl journal event"}</p><code>{short(event.id, 8)}</code></div></article>;
}

function EmptyState({ title, body }: { title: string; body: string }) { return <div className="empty-state"><strong>{title}</strong><p>{body}</p></div>; }
function InlineUnavailable({ error }: { error: unknown }) { return <div className="alert danger" role="alert"><strong>Data unavailable.</strong> {displayError(error)}</div>; }

function BenchmarkColumn({ title, tone, metrics }: { title: string; tone: string; metrics?: BenchmarkMetrics }) {
  const rows = metrics ? [["Unsafe repeat rate", `${metrics.unsafe_repeat_rate_percent.toFixed(2)}%`], ["Budget violation rate", `${metrics.budget_violation_rate_percent.toFixed(2)}%`], ["Decision accuracy", `${metrics.decision_accuracy_percent.toFixed(2)}%`], ["Evidence completeness", `${metrics.evidence_completeness_percent.toFixed(2)}%`], ["Median / p95 latency", `${metrics.latency.median_ms.toFixed(3)} / ${metrics.latency.p95_ms.toFixed(3)} ms`]] : [["Unsafe repeat rate", "Not run"], ["Budget violation rate", "Not run"], ["Decision accuracy", "Not run"], ["Evidence completeness", "Not run"], ["Median / p95 latency", "Not run"]];
  return <article className={`benchmark-column ${tone}`}><h3>{title}</h3>{rows.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</article>;
}

function IntegrationCard({ name, status, tone, rows, explorerUrl }: { name: string; status: string; tone: string; rows: string[][]; explorerUrl?: string | null }) {
  return <article className="integration-card"><div><h3>{name}</h3><span className={`status-pill ${tone}`}>{status}</span></div><dl>{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>{explorerUrl && <a href={explorerUrl} target="_blank" rel="noreferrer">Open official explorer proof</a>}</article>;
}
