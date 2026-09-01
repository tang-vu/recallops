# Demo Script

Target length: 3 minutes 30 seconds. Record the fresh-process sequence as one continuous, unedited segment. Do not display private credentials, wallet dialogs, email, or unpublished links.

## Preflight

- Use the exact commit shown in the interface and terminal.
- Run `make check`, `make benchmark`, and `make deletion-test` before recording.
- Reset only the validated demo database with `make demo-reset`.
- Keep `FIXTURE MODE` visible unless a real Virtuals job has been independently verified.
- Keep Base labeled `NOT CONFIGURED` or `LOCAL ANVIL` unless a public Base Sepolia transaction exists.
- Never claim either partner multiplier from fixture or Anvil evidence.

## 0:00 to 0:25 - The problem

Narration:

> Autonomous agents can hold wallets and hire services, but their sessions are disposable while economic consequences are not. A new process can forget that a provider failed, a permission was revoked, or a cumulative budget was already spent. RecallOps prevents that forgotten state from becoming another harmful transaction.

Visual: open the Overview. Show the protected agent, healthy Sibyl status, integration labels, and zero invented metrics.

## 0:25 to 0:55 - The control plane

Narration:

> RecallOps puts Sibyl Memory on the critical path before every commerce action. It recalls policy and outcomes, applies deterministic rules, and returns exactly APPROVE, DENY, or ESCALATE with the memories that changed the result. An LLM may propose work, but it cannot authorize money.

Visual: move through the action form and receipt evidence structure. Briefly point to the three-stage sequence: recall, decide, authorize.

## 0:55 to 1:35 - Session 1

Command: `make demo-session-1`

Narration:

> This is Session 1. The output shows its operating-system process ID, session UUID, UTC time, and Git commit. Agent A is the cheaper provider, but its deterministic deliverable fails verification because required vulnerability evidence is missing. RecallOps writes the policy, budget, permission, failure fingerprint, task-scoped counterparty probation, and chronological events through Sibyl.

Visual: keep the PID and session UUID visible. Highlight the WARM failure record and COLD verification event. Then let the command exit completely.

## 1:35 to 2:25 - Fresh Session 2

Command: `make demo-session-2`

Narration:

> Session 1 is gone. This is a genuinely new process with a different PID and session UUID, using only the same durable Sibyl database. The new request again prefers Agent A because it costs less. RecallOps retrieves the previous failure from Session 1. That memory changes the economic decision to DENY with REPEATED_FAILURE_FINGERPRINT. Agent B remains eligible and receives APPROVE.

Visual: show both process identities, the retrieved source session, Agent A's red decision receipt, and Agent B's approval. Keep the fixture label visible if the ACP job is local.

## 2:25 to 3:05 - Guarded execution and audit proof

Narration for the currently verified local build:

> Approval is still not execution. RecallOps binds the receipt to one action, rechecks the current offering, creates at most one explicitly labeled fixture job, and requires verification before payment or receipt anchoring. The Base registry has passed local Anvil deployment, fuzzing, transaction verification, and exact replay tests. There is no public Base or Virtuals claim yet.

If real partner evidence is obtained later, replace only the last two sentences with:

> Agent B opens this live Virtuals ACP job after policy approval. After verification passes, RecallOps anchors only the receipt digest on Base Sepolia and writes the confirmed transaction back to Sibyl. These are the public ACP and explorer links.

Do not use the live narration unless both links are real and independently verified.

## 3:05 to 3:30 - Benchmark and deletion proof

Narration:

> Across twelve deterministic scenarios, Sibyl Memory produced zero unsafe repeats, zero budget violations, one hundred percent decision accuracy, and complete evidence. The explicit stateless comparator approved every unsafe repeat and violated the cumulative budget. When Sibyl is deleted from the production path, RecallOps fails closed and stops commerce. If we instead choose the benchmark-only stateless behavior, the harmful rehire repeats. Memory is not decoration here. It is the safety boundary.

Visual: show run ID `1627c118-32a7-5bc2-8c14-fdfe62db1849`, seed `20260901`, both benchmark columns, and the passing deletion-test JSON.
