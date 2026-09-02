# Virtuals ACP Live Setup

Status: adapter complete, fixture verified, live execution disabled, no multiplier claim.

## Runtime choice

RecallOps targets the maintained `@virtuals-protocol/acp-cli` 1.0.34 interface. The live adapter invokes only v2-oriented commands with argument arrays, never a shell:

- `acp browse <query> --chain-ids 84532 --top-k <n> --json`
- `acp client create-job --provider <wallet> --offering-name <name> --requirements <json> --chain-id 84532 --json`
- `acp job history --job-id <id> --chain-id 84532 --json`

Every call forces `IS_TESTNET=true`, restricts chain ID to Base Sepolia `84532`, caps output at 1 MiB, caps requirements at 64 KiB, forwards only an environment allowlist, and sanitizes CLI output before an error can reach logs or an API response.

Fixture mode does not invoke ACP. Its IDs always start with `fixture:` and it emits no explorer or job links.

## Upstream dependency audit

An isolated install of ACP CLI 1.0.34 on 2026-09-01 resolved 400 packages, including maintained `@virtuals-protocol/acp-node-v2` 0.1.12. It also transitively included deprecated `@virtuals-protocol/acp-node` 0.3.0 beta for legacy commands. `npm audit --audit-level=high` reported 27 total findings, including 9 high-severity findings; the available audit fix did not clear them.

The installed CLI and v2 source were re-inspected on 2026-09-02. The current browse JSON uses a top-level `data` list, chain objects with `chainId`, and offerings with `priceValue` denominated in USDC. Job history returns `entries`; RecallOps derives deliverables, budget and funding metadata, and completed or rejected verification outcomes from those entries. Adapter fixtures mirror these observed shapes.

RecallOps does not call the legacy CLI paths and does not vendor this dependency into its default runtime. A live run requires an isolated, operator-reviewed CLI installation. This is an explicit known limitation, not a suppressed quality gate.

## Human-controlled bootstrap

These steps must be performed only after reviewing the upstream audit and approving the exact wallet and testnet action:

```bash
npm view @virtuals-protocol/acp-cli@1.0.34 version dependencies engines
mkdir recallops-acp-review
cd recallops-acp-review
npm init --yes
npm install --save-exact @virtuals-protocol/acp-cli@1.0.34
npm audit --audit-level=high
npx acp skill print
npx acp configure start --json
```

The last command returns a browser authentication URL and request ID. Do not place either in repository files or shared logs. After the owner completes the browser step:

```bash
npx acp configure complete --request-id <request-id> --json
npx acp agent whoami --json
```

Agent creation, signer registration, wallet funding, and any USDC approval are human-controlled actions. They are not automated by RecallOps setup.

## Safe read-only verification

With testnet mode enabled, provider discovery is read-only:

```bash
IS_TESTNET=true acp browse "dependency security audit" --chain-ids 84532 --top-k 5 --json
```

In PowerShell, set `$env:IS_TESTNET = "true"` for that terminal before invoking the same `acp browse` command.

Record the selected provider wallet, exact offering name, requirement schema, price, and currency. The live execution endpoint re-reads offering metadata and refuses a price or currency that exceeds the amount already approved by RecallOps.

RecallOps also exposes a combined, read-only readiness command:

```bash
RECALLOPS_ACP_EXECUTABLE=/absolute/path/to/acp make partner-preflight
```

The 2026-09-02 run reached Base Sepolia chain ID 84532 and observed the current public block and gas price. ACP returned `NO_ACTIVE_AGENT`, so no provider discovery, job, payment, or signer action occurred. This is expected until the human-controlled bootstrap above is completed.

## Enabling dispatch

Live mode needs all of the following server-only configuration:

```text
RECALLOPS_VIRTUALS_MODE=LIVE VIRTUALS
RECALLOPS_ACP_EXECUTABLE=/absolute/path/to/acp
RECALLOPS_ENABLE_LIVE_VIRTUALS=true
```

Do not set the final flag until the wallet owner has approved the specific Base Sepolia wallet, maximum testnet amount, signer policy, and reversibility. With live mode configured but the final flag absent, RecallOps persists the execution authorization but returns `NOT_DISPATCHED` without invoking ACP.

The dispatch trace is persisted in this order:

1. Sibyl action and `APPROVE` receipt already exist.
2. Sibyl execution authorization is written.
3. Current offering price and currency are checked against the approved ceiling.
4. Sibyl records `VIRTUALS_DISPATCH_STARTED`.
5. The ACP CLI creates the job.
6. Sibyl stores the job, links it to the decision receipt, and records `VIRTUALS_JOB_CREATED`.

If the CLI fails or times out after dispatch starts, the authorization is marked `FAILED` and cannot be automatically retried. A fresh decision is required because the external result may be uncertain.
