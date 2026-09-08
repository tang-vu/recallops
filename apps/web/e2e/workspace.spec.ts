import { expect, test } from "@playwright/test";

test("private workspace uses real policy and remembers a failure", async ({ page }, testInfo) => {
  test.setTimeout(90_000);
  await page.goto("/");
  await page.screenshot({ path: testInfo.outputPath("product-home.png"), fullPage: true });
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
  await page.getByRole("combobox", { name: "Decision", exact: true }).selectOption("DENY");
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
  await page.screenshot({ path: testInfo.outputPath("workspace-policy.png"), fullPage: true });
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
