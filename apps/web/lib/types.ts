export type Decision = "APPROVE" | "DENY" | "ESCALATE";

export interface MemoryEvidence {
  tier: string;
  record_type: string;
  record_name: string;
  source_session_id: string | null;
  written_at: string;
  recalled_at: string;
  why_it_mattered: string;
  status: string;
  content: Record<string, unknown>;
  content_digest: string;
}

export interface DecisionReceipt {
  receipt_id: string;
  decision: Decision;
  action_id: string;
  tenant_id: string;
  session_id: string;
  policy_version: string;
  reason_codes: string[];
  human_summary: string;
  memory_evidence: MemoryEvidence[];
  budget_before: string;
  budget_after_if_approved: string;
  counterparty_risk: Record<string, unknown>;
  memory_snapshot_digest: string;
  created_at: string;
  expires_at: string;
  virtuals_job_id: string | null;
  base_transaction_hash: string | null;
}

export interface SystemStatus {
  service: string;
  version: string;
  memory_configured: boolean;
  memory_healthy: boolean;
  memory_path_hint: string | null;
  virtuals_mode: string;
  base_mode: string;
  base_chain_id: number;
  fixture_data: boolean;
}

export interface BaseAnchorRecord {
  receipt_id: string;
  action_id: string;
  chain_id: number;
  contract_address: string;
  transaction_hash: string;
  explorer_url: string | null;
  integration_mode: "LOCAL ANVIL" | "BASE SEPOLIA";
}

export interface BenchmarkMetrics {
  unsafe_repeat_rate_percent: number;
  budget_violation_rate_percent: number;
  decision_accuracy_percent: number;
  evidence_completeness_percent: number;
  latency: { median_ms: number; p95_ms: number };
}

export interface BenchmarkReport {
  available: boolean;
  reason?: string;
  run_id?: string;
  seed?: number;
  scenario_count?: number;
  summary?: {
    sibyl_memory: BenchmarkMetrics;
    stateless_baseline: BenchmarkMetrics;
  };
}

export interface JournalEvent {
  id: string;
  ts: string;
  evaluated: string[] | null;
  acted: string[] | null;
  extra: Record<string, unknown> | null;
}

export interface CounterpartyEntity {
  id: string;
  status: string | null;
  body: {
    provider_id?: string;
    task_category?: string;
    failed_jobs?: number;
    successful_jobs?: number;
    last_failure_fingerprint?: string;
    probation_status?: string;
  };
  updated_at: string;
}

export interface EvaluationResponse {
  receipt: DecisionReceipt;
  writes: Array<Record<string, string>>;
  idempotent_replay: boolean;
}

export interface JobRecord {
  job_id: string;
  integration_mode: "FIXTURE MODE" | "LIVE VIRTUALS";
  tenant_id: string;
  action_id: string;
  receipt_id: string;
  provider_id: string;
  task_category: string;
  task_fingerprint: string;
  chain_id: number;
  offering_name: string | null;
  status: string;
  deliverable: string | null;
  payment_metadata: Record<string, unknown>;
  verifiable_links: string[];
  adapter_response_digest: string | null;
}

export interface ExecutionResponse {
  executor_status: string;
  note: string;
  idempotent_replay: boolean;
  job: JobRecord | null;
}
