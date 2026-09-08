import type { DecisionReceipt, MemoryEvidence } from "@/lib/types";

export type DemoResult = {
  demo_stage: "SESSION_1" | "SESSION_2";
  process: {
    process_id: number;
    session_id: string;
    utc_timestamp: string;
    git_commit: string;
  };
  process_terminated_after_output: boolean;
  verification?: { outcome: string; reason: string };
  successful_sibyl_writes?: unknown[];
  retrieved_memory_record?: MemoryEvidence[];
  agent_a_decision?: DecisionReceipt;
  agent_b_decision?: DecisionReceipt;
};

export function DemoProof({
  first,
  second,
}: {
  first?: DemoResult;
  second?: DemoResult;
}) {
  const source = second?.retrieved_memory_record?.find(
    (item) =>
      item.record_type === "failure_fingerprint" &&
      item.source_session_id === first?.process.session_id,
  );
  const verified = Boolean(
    first &&
      second &&
      source &&
      first.process.process_id !== second.process.process_id &&
      first.process.session_id !== second.process.session_id &&
      first.process_terminated_after_output &&
      second.process_terminated_after_output &&
      Date.parse(first.process.utc_timestamp) <
        Date.parse(second.process.utc_timestamp) &&
      second.agent_a_decision?.session_id === second.process.session_id &&
      second.agent_a_decision.decision === "DENY" &&
      second.agent_a_decision.reason_codes.includes(
        "REPEATED_FAILURE_FINGERPRINT",
      ),
  );
  return (
    <div className="demo-proof" aria-label="Fresh process evidence">
      <div className="demo-proof-status" role="status">
        <strong>
          {verified
            ? "Fresh-process recall verified"
            : "Waiting for a matching session pair"}
        </strong>
        <p>
          {verified
            ? "A new process recalled this Session 1 failure and denied the repeated request."
            : "Run Session 1, let it exit, then run Session 2. Both results stay visible here."}
        </p>
      </div>
      <div className="demo-proof-grid">
        {[first, second].map((result, index) => (
          <article key={index}>
            <p className="eyebrow">
              SESSION {index + 1} /{" "}
              {index === 0 ? "WRITE AND EXIT" : "START FRESH AND RECALL"}
            </p>
            <h3>
              {result
                ? index === 0
                  ? "Verification failed. Memory saved."
                  : `Agent A: ${result.agent_a_decision?.decision ?? "No decision"}`
                : "Not run in this view"}
            </h3>
            {result && (
              <>
                <dl>
                  <dt>Operating-system PID</dt>
                  <dd data-testid={`session-${index + 1}-pid`}>
                    {result.process.process_id}
                  </dd>
                  <dt>Session UUID</dt>
                  <dd>
                    <code>{result.process.session_id}</code>
                  </dd>
                  <dt>Started at (UTC)</dt>
                  <dd>
                    <time dateTime={result.process.utc_timestamp}>
                      {result.process.utc_timestamp}
                    </time>
                  </dd>
                  <dt>Git commit</dt>
                  <dd>
                    <code>{result.process.git_commit}</code>
                  </dd>
                  <dt>Process</dt>
                  <dd>
                    {result.process_terminated_after_output
                      ? "Exited after returning output"
                      : "Exit not confirmed"}
                  </dd>
                </dl>
                <p>
                  {index === 0
                    ? result.verification?.reason
                    : result.agent_a_decision?.human_summary}
                </p>
                {index === 0 && (
                  <p>
                    {result.successful_sibyl_writes?.length ?? 0} successful
                    Sibyl writes
                  </p>
                )}
                {index === 1 && (
                  <>
                    <p className="demo-proof-reason">
                      {result.agent_a_decision?.reason_codes.join(", ")}
                    </p>
                    <p>
                      Agent B:{" "}
                      <strong>
                        {result.agent_b_decision?.decision ?? "No decision"}
                      </strong>
                    </p>
                  </>
                )}
                <details>
                  <summary>Inspect full process output</summary>
                  <pre className="demo-output">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </details>
              </>
            )}
          </article>
        ))}
      </div>
      {source && (
        <p className="demo-proof-source">
          Recalled failure source: <code>{source.source_session_id}</code>
          <br />
          {source.why_it_mattered}
        </p>
      )}
      <p className="data-note">
        Real local Sibyl persistence. Provider deliverables and ACP execution
        use labeled fixtures. No live payment or Base transaction is claimed.
      </p>
    </div>
  );
}
