import type { DecisionReceipt } from "./types";

export function summarizeDecisions(decisions: DecisionReceipt[]) {
  return {
    evaluated: decisions.length,
    unsafeRepeatsPrevented: decisions.filter((item) => item.reason_codes.includes("REPEATED_FAILURE_FINGERPRINT"))
      .length,
    approvals: decisions.filter((item) => item.decision === "APPROVE").length,
  };
}
