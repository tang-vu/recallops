"use client";

import { useEffect, useState } from "react";
import type { DecisionReceipt } from "@/lib/types";
import type { ReceiptRevocation } from "@/components/receipt-controls";

export type OwnerReview = {
  review_id: string;
  decision: "APPROVE" | "REJECT";
  reason: string;
  reviewed_by: string;
  created_at: string;
  expires_at: string;
};
export type AuthorizationCheck = {
  allowed_now: boolean;
  reason_code: string;
  checked_at: string;
  expires_at: string;
};
type ReviewItem = {
  receipt: DecisionReceipt;
  review?: OwnerReview | null;
  revocation?: ReceiptRevocation | null;
  action: {
    provider_id: string;
    offering: string;
    task_category: string;
    task_fingerprint: string;
    requested_amount: string;
    currency: string;
    risk_class: string;
  } | null;
};

export function ReviewQueue({
  items,
  busy,
  onReview,
  onCheck,
  checks,
}: {
  items: ReviewItem[];
  busy: boolean;
  onReview: (
    id: string,
    decision: "APPROVE" | "REJECT",
    reason: string,
  ) => void;
  onCheck: (id: string) => void;
  checks: Record<string, AuthorizationCheck>;
}) {
  const [now, setNow] = useState(() => Date.now());
  const [filter, setFilter] = useState("Pending");
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);
  const escalated = items.filter(
    (item) => item.receipt.decision === "ESCALATE",
  );
  const visible = escalated.filter((item) => {
    if (filter === "All") return true;
    if (filter === "Reviewed") return Boolean(item.review);
    if (filter === "Revoked") return Boolean(item.revocation);
    if (filter === "Expired")
      return !item.review && Date.parse(item.receipt.expires_at) <= now;
    return (
      !item.review &&
      !item.revocation &&
      Date.parse(item.receipt.expires_at) > now
    );
  });
  return (
    <section className="workspace-card">
      <div className="workspace-section-head">
        <div>
          <p className="eyebrow">OWNER DECISION DESK</p>
          <h2>Review queue</h2>
          <p>
            Review high-risk actions within the receipt’s five-minute window.
            Each review stays attached to its original request.
          </p>
        </div>
        <label>
          Show reviews
          <select
            aria-label="Review filter"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
          >
            {["Pending", "Reviewed", "Revoked", "Expired", "All"].map(
              (value) => (
                <option key={value}>{value}</option>
              ),
            )}
          </select>
        </label>
      </div>
      <p className="data-note">
        Only HUMAN_APPROVAL_REQUIRED can be approved here. Missing evidence and
        other policy conditions must be fixed before a fresh evaluation. Latest
        100 decisions.
      </p>
      {!visible.length && (
        <div className="workspace-empty">
          {filter === "Pending"
            ? "No pending reviews. High-risk requests appear here when evaluated."
            : "No reviews in this view."}
        </div>
      )}
      {visible.map(({ receipt, action, review, revocation }) => {
        const expired = Date.parse(receipt.expires_at) <= now;
        const reviewable =
          receipt.reason_codes.length === 1 &&
          receipt.reason_codes[0] === "HUMAN_APPROVAL_REQUIRED";
        const check = checks[receipt.receipt_id];
        return (
          <article className="review-item" key={receipt.receipt_id}>
            <div className="workspace-section-head">
              <div>
                <span
                  className={`workspace-verdict ${revocation || review?.decision === "REJECT" ? "deny" : "escalate"}`}
                >
                  {revocation
                    ? "REVOKED"
                    : review
                      ? review.decision === "APPROVE"
                        ? "OWNER APPROVED"
                        : "OWNER REJECTED"
                      : expired
                        ? "EXPIRED"
                        : "NEEDS REVIEW"}
                </span>
                <h3>
                  {action?.provider_id ?? "Unknown provider"} ·{" "}
                  {action?.offering}
                </h3>
              </div>
              <strong>
                {action?.requested_amount} {action?.currency}
              </strong>
            </div>
            <p>{receipt.human_summary}</p>
            <code>{action?.task_fingerprint}</code>
            <dl className="workspace-facts">
              <div>
                <dt>Risk / task</dt>
                <dd>
                  {action?.risk_class} / {action?.task_category}
                </dd>
              </div>
              <div>
                <dt>Expires</dt>
                <dd>
                  <time dateTime={receipt.expires_at}>
                    {new Date(receipt.expires_at).toLocaleTimeString()}
                  </time>
                  {!expired &&
                    ` · ${Math.ceil((Date.parse(receipt.expires_at) - now) / 1000)}s left`}
                </dd>
              </div>
            </dl>
            <details>
              <summary>Inspect recalled evidence</summary>
              <div className="reason-row">
                {receipt.reason_codes.map((code) => (
                  <code key={code}>{code}</code>
                ))}
              </div>
              {receipt.memory_evidence.map((evidence, i) => (
                <div key={i}>
                  <h4>{evidence.record_type.replaceAll("_", " ")}</h4>
                  <p>{evidence.why_it_mattered}</p>
                  <pre className="workspace-code">
                    {JSON.stringify(evidence.content, null, 2)}
                  </pre>
                </div>
              ))}
            </details>
            {revocation ? (
              <div className="revocation-record">
                <strong>Receipt revoked</strong>
                <p>{revocation.reason}</p>
                <small>
                  The owner stopped this receipt. Its original decision and
                  review remain in decision history.
                </small>
              </div>
            ) : review ? (
              <div className="review-outcome">
                <p>
                  <strong>Owner’s reason:</strong> {review.reason}
                </p>
                <small>
                  Recorded {new Date(review.created_at).toLocaleString()}. The
                  original receipt remains ESCALATE.
                </small>
                <button
                  className="secondary-button"
                  disabled={busy}
                  onClick={() => onCheck(receipt.receipt_id)}
                >
                  Check current authorization
                </button>
                {check && (
                  <p role="status">
                    <strong>
                      {check.allowed_now
                        ? "Allowed at last check"
                        : "Blocked at last check"}
                    </strong>{" "}
                    · {check.reason_code}
                    <br />
                    <small>
                      Checked {new Date(check.checked_at).toLocaleTimeString()}.
                      Recheck immediately before execution.
                    </small>
                  </p>
                )}
              </div>
            ) : expired ? (
              <p className="data-note">
                This request expired. The agent must submit a new evaluation
                before review.
              </p>
            ) : (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  const form = new FormData(event.currentTarget);
                  const button = (event.nativeEvent as SubmitEvent)
                    .submitter as HTMLButtonElement;
                  if (!button || !["APPROVE", "REJECT"].includes(button.value))
                    return;
                  onReview(
                    receipt.receipt_id,
                    button.value as "APPROVE" | "REJECT",
                    String(form.get("reason")),
                  );
                }}
              >
                <label>
                  Review reason
                  <textarea
                    name="reason"
                    required
                    maxLength={512}
                    rows={2}
                    placeholder="Explain your decision for the audit trail."
                  />
                </label>
                <div className="button-row">
                  <button
                    className="primary-button"
                    value="APPROVE"
                    disabled={busy || !reviewable}
                  >
                    Approve this request
                  </button>
                  <button
                    className="secondary-button"
                    value="REJECT"
                    disabled={busy}
                  >
                    Reject request
                  </button>
                </div>
                {!reviewable && (
                  <p className="data-note">
                    Approval is unavailable for this reason. Fix the underlying
                    condition and evaluate again.
                  </p>
                )}
              </form>
            )}
          </article>
        );
      })}
    </section>
  );
}
