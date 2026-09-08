import { expect, test } from "@playwright/test";

test("private workspace uses real policy and remembers a failure", async ({
  page,
}, testInfo) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await page.screenshot({
    path: testInfo.outputPath("product-home.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Create your workspace" }).click();
  await page.getByLabel("Workspace name").fill("Browser workspace");
  const created = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/workspace") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Create workspace" }).click();
  const credentials = await (await created).json();
  await expect(
    page.getByRole("heading", { name: "Browser workspace", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "I’ve saved my keys" }).click();
  await page
    .getByRole("button", { name: "Request playground", exact: true })
    .click();
  await page.getByLabel("Provider ID", { exact: true }).fill("test-provider");
  await page.getByLabel("Offering", { exact: true }).fill("Audit dependencies");
  await page
    .getByLabel("Task fingerprint", { exact: true })
    .fill("audit:browser:v1");
  await page.getByLabel("Verifier ID", { exact: true }).fill("schema-check-v1");
  await page.getByRole("button", { name: "Evaluate request" }).click();
  await expect(page.getByText("APPROVE", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Record a failure", exact: true })
    .click();
  await page.getByLabel("Provider ID", { exact: true }).fill("test-provider");
  await page
    .getByLabel("Task fingerprint", { exact: true })
    .fill("audit:browser:v1");
  await page.getByLabel("Verifier ID", { exact: true }).fill("schema-check-v1");
  await page
    .getByLabel("What failed?")
    .fill("Dependency evidence was missing.");
  await page.getByRole("button", { name: "Save failure to memory" }).click();
  await expect(page.getByRole("status")).toContainText("Failure saved");
  await page
    .getByRole("button", { name: "Request playground", exact: true })
    .click();
  await page.getByLabel("Provider ID", { exact: true }).fill("test-provider");
  await page.getByLabel("Offering", { exact: true }).fill("Audit dependencies");
  await page
    .getByLabel("Task fingerprint", { exact: true })
    .fill("audit:browser:v1");
  await page.getByLabel("Verifier ID", { exact: true }).fill("schema-check-v1");
  await page.getByRole("button", { name: "Evaluate request" }).click();
  await expect(page.getByText("DENY", { exact: true })).toBeVisible();
  await expect(
    page.getByText("REPEATED_FAILURE_FINGERPRINT", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Decision history", exact: true })
    .click();
  await expect(page.locator(".workspace-history > details")).toHaveCount(2);
  await page
    .getByRole("combobox", { name: "Decision", exact: true })
    .selectOption("DENY");
  await expect(page.locator(".workspace-history > details")).toHaveCount(1);
  await page.getByRole("button", { name: "Policy & access" }).click();
  await page.getByLabel("Per-action limit", { exact: true }).fill("0.50");
  await page.getByRole("button", { name: "Save policy", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Policy saved");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Browser workspace", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page
    .getByRole("button", { name: "Already have an owner key?" })
    .click();
  await page.getByLabel("Owner recovery key").fill(credentials.owner_key);
  await page
    .getByRole("button", { name: "Open workspace", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Browser workspace", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Policy & access" }).click();
  await expect(
    page.getByLabel("Per-action limit", { exact: true }),
  ).toHaveValue("0.50");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("workspace-policy.png"),
    fullPage: true,
  });
});

test("public gateway blocks cross-origin session writes and oversized requests", async ({
  request,
}) => {
  expect((await request.get("/api/workspace/toString")).status()).toBe(404);
  const csrf = await request.post("/api/workspace/session", {
    headers: { Origin: "https://unrelated.example" },
    data: { owner_key: "invalid" },
  });
  expect(csrf.status()).toBe(403);
  const oversized = await request.post("/api/workspace/evaluate", {
    headers: { Authorization: "Bearer test-only" },
    data: { offering: "x".repeat(17_000) },
  });
  expect(oversized.status()).toBe(413);
});

test("owner reviews a real escalation and new failure blocks its authorization", async ({
  page,
}, testInfo) => {
  test.setTimeout(90_000);
  await page.goto("/workspace");
  await page.getByLabel("Workspace name").fill("Review desk check");
  await page.getByRole("button", { name: "Create workspace" }).click();
  await page.getByRole("button", { name: /saved my keys/ }).click();
  await page
    .getByRole("button", { name: "Request playground", exact: true })
    .click();
  await page.getByLabel("Provider ID", { exact: true }).fill("review-provider");
  await page
    .getByLabel("Offering", { exact: true })
    .fill("Sensitive dependency audit");
  await page
    .getByLabel("Task fingerprint", { exact: true })
    .fill("review:audit:v1");
  await page.getByLabel("Verifier ID", { exact: true }).fill("review-verifier");
  await page
    .getByRole("combobox", { name: "Risk", exact: true })
    .selectOption("HIGH");
  await page.getByRole("button", { name: "Evaluate request" }).click();
  await expect(page.getByText("ESCALATE", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Review queue", exact: true }).click();
  await page
    .getByLabel("Review reason")
    .fill("I reviewed the scope and accepted this request.");
  await page.getByRole("button", { name: "Approve this request" }).click();
  await expect(
    page.getByText("Owner review saved.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Review filter" })
    .selectOption("Reviewed");
  await expect(page.getByText("OWNER APPROVED", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Check current authorization" })
    .click();
  await expect(
    page.getByText("Allowed at last check", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("owner-review.png"),
    fullPage: true,
  });
  const failure = await page.request.post("/api/workspace/failures", {
    headers: { Origin: new URL(page.url()).origin },
    data: {
      provider_id: "review-provider",
      task_category: "security-review",
      task_fingerprint: "review:audit:v1",
      verifier_id: "review-verifier",
      verification_reason: "New evidence shows required data is missing.",
    },
  });
  expect(failure.status()).toBe(201);
  await page
    .getByRole("button", { name: "Check current authorization" })
    .click();
  await expect(
    page.getByText("Blocked at last check", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("REPEATED_FAILURE_FINGERPRINT", { exact: false }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Review queue", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Review filter" })
    .selectOption("Reviewed");
  await expect(page.getByText("OWNER APPROVED", { exact: true })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
