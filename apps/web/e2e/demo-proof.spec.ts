import { expect, test } from "@playwright/test";

// Both viewport projects share one demo database. Keep this proof in one
// project so another Session 1 cannot replace its source while it is running.
test("fresh process proof links two real backend processes", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "chromium",
    "One writer for the shared demo database",
  );
  test.setTimeout(90_000);
  await page.goto("/demo#demo");
  const proof = page.getByLabel("Fresh process evidence");
  await expect(proof.getByRole("status")).toContainText(
    "Waiting for a matching session pair",
  );
  await page
    .getByRole("button", { name: "Run Session 1", exact: true })
    .click();
  const first = proof.getByTestId("session-1-pid");
  await expect(first).toBeVisible();
  const firstPid = await first.textContent();
  await page.getByRole("button", { name: "Run Session 2" }).click();
  await expect(proof.getByRole("status")).toContainText(
    "Fresh-process recall verified",
  );
  expect(await proof.getByTestId("session-2-pid").textContent()).not.toBe(
    firstPid,
  );
  await expect(proof.locator(".demo-proof-reason")).toContainText("REPEATED_FAILURE_FINGERPRINT");
  await page.screenshot({
    path: testInfo.outputPath("fresh-process-proof.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 393, height: 851 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Run Session 1", exact: true })
    .click();
  await expect(proof.getByTestId("session-2-pid")).toHaveCount(0);
  await expect(proof.getByRole("status")).toContainText(
    "Waiting for a matching session pair",
  );
});
