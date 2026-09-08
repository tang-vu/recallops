// Records one continuous browser video. Captions are drawn during capture;
// there are no cuts, replaced network responses, or fabricated process results.
import { chromium } from "../apps/web/node_modules/playwright/index.mjs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const credentialFile = process.argv[process.argv.indexOf("--credentials") + 1];
if (!process.argv.includes("--credentials") || !credentialFile) {
  throw new Error("Usage: node scripts/record-demo.mjs --credentials <private workspace key JSON>");
}
const keys = JSON.parse(await readFile(resolve(credentialFile), "utf8"));
if (!keys.owner_key) throw new Error("An existing demo workspace owner key is required.");
const origin = process.env.RECALLOPS_DEMO_ORIGIN ?? "https://recallops.tangvu.dev";
const output = resolve(".data/demo-recordings", new Date().toISOString().replaceAll(/[:.]/g, "-"));
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1600, height: 900 },
  recordVideo: { dir: output, size: { width: 1600, height: 900 } },
});
let page;
const chapters = [];
const responses = {};
const started = Date.now();
async function caption(text, seconds) {
  chapters.push({ seconds: (Date.now() - started) / 1000, text });
  console.log(text);
  await page.evaluate((text) => {
    let box = document.getElementById("recording-caption");
    if (!box) {
      box = document.createElement("div");
      box.id = "recording-caption";
      box.style.cssText = "position:fixed;bottom:0;left:0;right:0;z-index:2147483647;background:#102923;color:#fff;padding:20px 48px;font:22px/1.45 Arial,sans-serif;pointer-events:none;border-top:3px solid #44cca4;";
      document.body.append(box);
      const clock = document.createElement("div");
      clock.style.cssText = "position:fixed;right:16px;top:8px;z-index:2147483647;background:#102923;color:#fff;padding:7px 12px;font:12px monospace;pointer-events:none;";
      document.body.append(clock);
      const tick = () => { clock.textContent = `CONTINUOUS BROWSER CAPTURE | ${new Date().toISOString()}`; };
      tick();
      setInterval(tick, 1000);
      document.body.style.paddingBottom = "160px";
    }
    box.textContent = text;
  }, text);
  await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
}

try {
  // Establish the owner cookie before opening the recorded page. Keys never
  // appear in the browser UI, captions, console output, or exported evidence.
  const login = await context.request.post(`${origin}/api/workspace/session`, {
    headers: { Origin: origin }, data: { owner_key: keys.owner_key },
  });
  if (!login.ok()) throw new Error(`Workspace login failed: HTTP ${login.status()}`);
  page = await context.newPage();
  page.setDefaultTimeout(30_000);
  await page.goto(origin);
  await caption("RecallOps: durable policy memory for developers building agents that hire services or spend money. A fresh session should not forget an expensive mistake.", 15);

  await page.goto(`${origin}/workspace`);
  await page.getByRole("button", { name: "Request playground", exact: true }).click();
  const fingerprint = `demo:owner-review:${Date.now()}`;
  for (const [name, value] of [
    ["Provider ID", "demo-review-provider"], ["Offering", "Sensitive dependency audit"],
    ["Task fingerprint", fingerprint], ["Verifier ID", "deterministic-schema-verifier-v1"],
  ]) await page.getByLabel(name, { exact: true }).fill(value);
  await page.getByRole("combobox", { name: "Risk", exact: true }).selectOption("HIGH");
  await caption("Each private workspace has owner policy, an agent key, and its own Sibyl memory. This request is high risk, so the agent must pause for review.", 13);
  await page.getByRole("button", { name: "Evaluate request" }).click();
  await page.getByText("ESCALATE", { exact: true }).waitFor();
  await caption("The gateway recalls current policy and returns ESCALATE with evidence. The proposed amount is not a payment. No money moves in this demonstration.", 12);
  await page.getByRole("button", { name: "Review queue", exact: true }).click();
  const pending = page.locator(".review-item").filter({ hasText: fingerprint });
  await pending.getByLabel("Review reason").fill("Reviewed the task scope and accepted this specific request.");
  await caption("Only the owner can approve this exact request, with a reason and a five-minute expiry. Approval cannot override missing evidence or a policy denial.", 12);
  await pending.getByRole("button", { name: "Approve this request" }).click();
  await page.getByText("Owner review saved.", { exact: false }).waitFor();
  await page.getByRole("combobox", { name: "Review filter" }).selectOption("Reviewed");
  const reviewed = page.locator(".review-item").filter({ hasText: fingerprint });
  await reviewed.getByRole("button", { name: "Check current authorization" }).click();
  await reviewed.getByText("Allowed at last check", { exact: true }).waitFor();
  await reviewed.scrollIntoViewIfNeeded();
  await caption("A saved review is historical evidence. Before execution, the agent checks current authorization again. New failures, policy changes, or paused access can still block it.", 14);

  await page.goto(`${origin}/demo#demo`);
  await page.locator("#demo").scrollIntoViewIfNeeded();
  await caption("Now the memory proof. These buttons start separate Python operating-system processes against the same durable Sibyl database. Deliverables and ACP execution are labeled fixtures.", 13);
  const firstResponse = page.waitForResponse((r) => r.url().endsWith("/v1/demo/session-1") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Run Session 1", exact: true }).click();
  const first = await firstResponse;
  if (!first.ok()) throw new Error(`Session 1 failed: HTTP ${first.status()}`);
  responses.first = (await first.json()).result;
  const proof = page.getByLabel("Fresh process evidence");
  await proof.getByTestId("session-1-pid").waitFor();
  await proof.scrollIntoViewIfNeeded();
  await caption("Session 1 writes a verified failure for Agent A, then exits. Its real PID, session UUID, UTC timestamp, and Git commit are visible alongside the successful Sibyl writes.", 20);
  const secondResponse = page.waitForResponse((r) => r.url().endsWith("/v1/demo/session-2") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Run Session 2" }).click();
  const second = await secondResponse;
  if (!second.ok()) throw new Error(`Session 2 failed: HTTP ${second.status()}`);
  responses.second = (await second.json()).result;
  await proof.getByText("Fresh-process recall verified", { exact: true }).waitFor();
  await proof.scrollIntoViewIfNeeded();
  await caption("Session 2 has a different PID and UUID. It recalls the failure written by Session 1. That exact source session is linked below: memory changes Agent A to DENY.", 22);
  await caption("Agent B remains eligible and receives APPROVE. This is real Sibyl persistence across process exits. The fixture job is not evidence of a live Virtuals job or Base transaction.", 16);

  await page.locator("#benchmark").scrollIntoViewIfNeeded();
  await caption("The twelve-scenario benchmark compares durable memory with an explicit stateless baseline. These are deterministic test results, not production usage or revenue claims.", 15);
  await page.goto(`${origin}/docs`);
  await caption("Use RecallOps through the workspace API. Your application still owns execution and atomic budget enforcement. Try the product at recallops.tangvu.dev; the source and memory proof are public.", 15);
  const video = page.video();
  await context.close();
  const videoPath = await video.path();
  const firstMeta = responses.first.process;
  const secondMeta = responses.second.process;
  if (firstMeta.process_id === secondMeta.process_id || firstMeta.session_id === secondMeta.session_id) throw new Error("The recording did not capture distinct processes.");
  if (!responses.second.retrieved_memory_record.some((item) => item.source_session_id === firstMeta.session_id)) throw new Error("The second process did not recall the recorded first session.");
  await writeFile(resolve(output, "evidence.json"), JSON.stringify({
    origin, videoPath, recorded_at: new Date().toISOString(), chapters,
    first: firstMeta, second: secondMeta,
    agent_a: responses.second.agent_a_decision.decision,
    agent_b: responses.second.agent_b_decision.decision,
    source_session: firstMeta.session_id, continuous_visual_capture: true,
    narration: "On-screen captions; no synthetic execution results",
  }, null, 2));
  console.log(`Recording and evidence saved to ${output}`);
} finally {
  await browser.close();
}
