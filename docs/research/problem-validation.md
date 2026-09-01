# Problem Validation

Access date: 2026-09-01 UTC

This is secondary desk research, not primary market validation. RecallOps has no claimed users, interviews, pilots, design partners, waitlist, revenue, or product-market-fit evidence. The PMF bonus should be treated as zero unless genuine public evidence is added later.

## What public evidence supports

Agent-led commerce creates an authorization and accountability gap. Google's [Agent Payments Protocol announcement](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol) says autonomous payment breaks the historical assumption that a person is directly clicking buy, and frames authorization, authenticity, and accountability as core questions. AP2 addresses transaction-specific mandates. RecallOps explores the adjacent control-plane problem: whether prior permissions, cumulative spend, and verified counterparty outcomes should permit the agent to initiate that transaction at all.

Agents with tools can cause real damage when permissions or autonomy exceed what a task requires. OWASP's [Excessive Agency guidance](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) identifies excessive functionality, permissions, and autonomy as root causes, including failures triggered by prompt injection or a compromised peer agent. RecallOps responds with a deterministic authority boundary where natural-language instructions cannot override policy.

Persistent memory is itself security-sensitive. OWASP's [Agentic AI threat material](https://genai.owasp.org/download/50592/?tmstv=1754459367) includes memory poisoning as a threat to long-term agent context. RecallOps therefore does not equate recall with trust: evidence is typed, tenant-scoped, digestible, and interpreted by deterministic rules. Missing or corrupt mandatory memory stops commerce.

NIST's [AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) calls for documented risk tolerances, human oversight processes, evaluation evidence, monitoring, and internal controls for third-party AI components. RecallOps turns those broad controls into inspectable runtime receipts for agent-to-agent commerce.

## Product hypothesis

The evidence supports a credible technical hypothesis, not demonstrated demand:

1. Autonomous agents will increasingly receive authority to hire services and initiate payments.
2. Transaction protocols can prove a specific authorization, but an agent also needs durable context about budgets, revocations, counterparties, and prior outcomes.
3. Session-local reasoning is insufficient for cumulative economic policy.
4. A deterministic memory gate can prevent unsafe repeats while preserving inspectable human control.

## What remains unvalidated

- Which buyer segment has the strongest need: agent platforms, wallet providers, marketplaces, or enterprise automation teams.
- Whether teams prefer a standalone control plane, an embedded SDK, or a hosted policy service.
- Acceptable latency and operational burden for durable memory on every action.
- Which policy templates and verifier standards generalize across marketplaces.
- Willingness to pay and procurement constraints.

These questions require real interviews and usage after the hackathon. They must not be inferred from repository stars, benchmark results, or partner integrations.
