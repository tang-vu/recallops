import { defineConfig, devices } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const testData = mkdtempSync(join(tmpdir(), "recallops-browser-"));

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  workers: 2,
  expect: { timeout: 15_000 },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:41789",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command:
        "uv run --project ../../services/control-plane uvicorn recallops.api.app:app --host 127.0.0.1 --port 41790",
      url: "http://127.0.0.1:41790/health",
      env: {
        RECALLOPS_MEMORY_DB: join(testData, "demo.db"),
        RECALLOPS_WORKSPACE_DIR: join(testData, "workspaces"),
        RECALLOPS_VIRTUALS_MODE: "FIXTURE MODE",
        RECALLOPS_BASE_MODE: "NOT CONFIGURED",
      },
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 41789",
      url: "http://127.0.0.1:41789",
      reuseExistingServer: false,
      timeout: 120_000,
      env: { RECALLOPS_API_URL: "http://127.0.0.1:41790" },
    },
  ],
});
