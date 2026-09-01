import { describe, expect, it } from "vitest";

import { summarizeDecisions } from "./metrics";
import type { DecisionReceipt } from "./types";

function receipt(decision: DecisionReceipt["decision"], reasonCodes: string[]): DecisionReceipt {
  return {
    receipt_id: crypto.randomUUID(),
    decision,
    action_id: crypto.randomUUID(),
    tenant_id: "tenant-a",
    session_id: crypto.randomUUID(),
    policy_version: "v1",
    reason_codes: reasonCodes,
    human_summary: "test",
    memory_evidence: [],
    budget_before: "0.00",
    budget_after_if_approved: "1.00",
    counterparty_risk: {},
    memory_snapshot_digest: "a".repeat(64),
    created_at: new Date().toISOString(),
    expires_at: new Date().toISOString(),
    virtuals_job_id: null,
    base_transaction_hash: null,
  };
}

describe("receipt metrics", () => {
  it("derives every displayed count from durable receipts", () => {
    const metrics = summarizeDecisions([
      receipt("DENY", ["REPEATED_FAILURE_FINGERPRINT"]),
      receipt("APPROVE", ["POLICY_CHECKS_PASSED"]),
      receipt("ESCALATE", ["HUMAN_APPROVAL_REQUIRED"]),
    ]);

    expect(metrics).toEqual({ evaluated: 3, unsafeRepeatsPrevented: 1, approvals: 1 });
  });
});
