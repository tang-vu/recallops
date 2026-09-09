"use client";

import { useEffect, useState } from "react";
import type { AuthorizationCheck } from "@/components/review-queue";

export type ReceiptRevocation = {
  revocation_id: string;
  reason: string;
  revoked_by: "owner";
  created_at: string;
};

export function ReceiptControls({
  expiresAt,
  revocation,
  busy,
  check,
  onCheck,
  onRevoke,
}: {
  expiresAt: string;
  revocation?: ReceiptRevocation | null;
  busy: boolean;
  check?: AuthorizationCheck;
  onCheck: () => void;
  onRevoke: (reason: string) => void;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const expired = Date.parse(expiresAt) <= now;
  return (
    <section
      className="receipt-controls"
      aria-label="Receipt authorization controls"
    >
      <h3>Current authorization</h3>
      <p>
        The original receipt is historical evidence. Check current permission
        immediately before execution.
      </p>
      <button className="secondary-button" disabled={busy} onClick={onCheck}>
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
          <small>Checked {new Date(check.checked_at).toLocaleString()}</small>
        </p>
      )}
      {revocation ? (
        <div className="revocation-record">
          <strong>Receipt revoked</strong>
          <p>{revocation.reason}</p>
          <small>
            Recorded {new Date(revocation.created_at).toLocaleString()}. This
            receipt cannot be reinstated.
          </small>
        </div>
      ) : expired ? (
        <p>This receipt expired. A new request needs a fresh evaluation.</p>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onRevoke(String(new FormData(event.currentTarget).get("reason")));
          }}
        >
          <label>
            Revocation reason
            <textarea
              name="reason"
              required
              maxLength={512}
              rows={2}
              placeholder="Why should this request stop?"
            />
          </label>
          <button className="secondary-button" disabled={busy}>
            Revoke this receipt
          </button>
          <p className="data-note">
            Stops this receipt at its next authorization check. Other requests
            remain eligible. It cannot undo work already executed or prevent a
            separately evaluated request.
          </p>
        </form>
      )}
    </section>
  );
}
