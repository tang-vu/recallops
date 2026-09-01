import { expect, test } from "@playwright/test";

const status = {
  service: "recallops-control-plane",
  version: "0.1.0",
  memory_configured: true,
  memory_healthy: true,
  memory_path_hint: ".../e2e.db",
  virtuals_mode: "FIXTURE MODE",
  base_mode: "LOCAL ONLY",
  base_chain_id: 84532,
  fixture_data: true,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/control-plane/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("v1/system/status")) return route.fulfill({ json: status });
    if (path.includes("v1/decisions")) return route.fulfill({ json: [] });
    if (path.includes("v1/memory/evidence")) return route.fulfill({ json: [] });
    if (path.includes("v1/counterparties")) return route.fulfill({ json: [] });
    if (path.endsWith("v1/jobs")) return route.fulfill({ json: [] });
    if (path.includes("v1/benchmark/latest")) return route.fulfill({ json: { available: false, reason: "No benchmark run has been persisted yet." } });
    if (path.endsWith("v1/actions/evaluate")) {
      const request = route.request().postDataJSON() as { action_id: string; session_id: string };
      return route.fulfill({
        json: {
          receipt: {
            receipt_id: "7dfe3fe6-9d08-4aa3-9aa5-56815686f816",
            decision: "DENY",
            action_id: request.action_id,
            tenant_id: "recallops-demo",
            session_id: request.session_id,
            policy_version: "demo-policy-v1",
            reason_codes: ["REPEATED_FAILURE_FINGERPRINT", "COUNTERPARTY_ON_PROBATION"],
            human_summary: "This provider previously failed verification for the same task fingerprint.",
            memory_evidence: [
              {
                tier: "WARM",
                record_type: "failure_fingerprint",
                record_name: "failure:test",
                source_session_id: "e53f9d7d-8890-4bfd-9fe2-3aa4f9b474d7",
                written_at: "2026-09-01T06:00:00Z",
                recalled_at: "2026-09-01T06:05:00Z",
                why_it_mattered: "Matched the same provider, task category, and failure fingerprint.",
                status: "active",
                content: { provider_id: "agent-a", task_fingerprint: "sha256:dependency-audit-v1" },
                content_digest: "a".repeat(64),
              },
            ],
            budget_before: "0.00",
            budget_after_if_approved: "1.00",
            counterparty_risk: { level: "HIGH" },
            memory_snapshot_digest: "b".repeat(64),
            created_at: "2026-09-01T06:05:00Z",
            expires_at: "2026-09-01T06:10:00Z",
            virtuals_job_id: null,
            base_transaction_hash: null,
          },
          writes: [],
          idempotent_replay: false,
        },
      });
    }
    return route.fulfill({ status: 404, json: { detail: "Not mocked" } });
  });
});

test("shows a recalled failure changing the action decision", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("SIBYL HEALTHY")).toBeVisible();
  await expect(page.getByText("No metrics are invented.")).toBeVisible();

  await page.getByRole("button", { name: "Evaluate action" }).click();

  await expect(page.getByText("DENY", { exact: true })).toBeVisible();
  await expect(page.getByText("REPEATED_FAILURE_FINGERPRINT", { exact: true })).toBeVisible();
  await expect(page.getByText("Matched the same provider, task category, and failure fingerprint.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Authorize execution" })).toBeDisabled();
});
