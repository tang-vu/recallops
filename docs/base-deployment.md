# Base Receipt Registry Deployment

RecallOps has a complete local receipt-registry path. This guide prepares Base Sepolia without claiming that a public deployment exists.

## What is already verified

- `RecallOpsReceiptRegistry.sol` compiles with Solidity 0.8.36.
- Foundry 1.8.1 format, high-severity lint, 13 unit/fuzz tests, and the gas snapshot pass.
- Anvil deployment is restricted to chain ID 31337.
- Base Sepolia deployment is restricted to chain ID 84532.
- The viem client verifies RPC chain ID, registry chain ID, authorized submitter, simulation, receipt success, persisted record hash, and idempotent replay.
- The control plane refuses to anchor before an approved ACP job passes verification.
- Only digests and decision metadata go onchain.

## Local reproduction

Run Anvil in one terminal:

```bash
anvil --host 127.0.0.1 --port 8545 --chain-id 31337
```

Use one of Anvil's public development addresses as the submitter. Do not copy its development private key into the repository.

```bash
export RECALLOPS_RECEIPT_SUBMITTER=0xYourAnvilAddress
forge script packages/contracts/script/DeployLocal.s.sol:DeployLocal \
  --root packages/contracts \
  --rpc-url http://127.0.0.1:8545 \
  --broadcast --unlocked --sender "$RECALLOPS_RECEIPT_SUBMITTER"
```

Build the viem bridge and configure the control plane with the local address:

```bash
npm ci --prefix packages/contracts
npm --prefix packages/contracts run build
export RECALLOPS_BASE_MODE="LOCAL ANVIL"
export RECALLOPS_BASE_RPC_URL=http://127.0.0.1:8545
export RECALLOPS_BASE_CONTRACT_ADDRESS=0xYourLocalRegistry
export RECALLOPS_BASE_SUBMITTER=0xYourAnvilAddress
```

The API route is `POST /v1/decisions/{receipt_id}/anchor`. It requires the admin token, an idempotency key, tenant ID, action ID, successful execution, an ACP job, and passed verification.

## Base Sepolia approval boundary

No Base Sepolia command should be run until the operator supplies explicit approval for all of these facts:

- Exact action: deploy one registry and anchor one approved, verified RecallOps receipt.
- Network: Base Sepolia, chain ID 84532.
- Wallet: a specific public wallet address controlled by the builder.
- Maximum cost: an explicit cap in testnet ETH; no purchased funds and no mainnet asset.
- Reversibility: deployment and anchor transactions are irreversible, although they carry only digests.
- Necessity: obtain explorer-verifiable Base partner evidence for the hackathon.

After approval, an operator-controlled wallet-enabled RPC signer must be configured outside the repository. RecallOps does not accept or manage a raw private key. Live anchoring additionally requires:

```bash
export RECALLOPS_BASE_MODE="BASE SEPOLIA"
export RECALLOPS_BASE_RPC_URL=https://your-approved-wallet-rpc.example
export RECALLOPS_BASE_CONTRACT_ADDRESS=0xYourPublicRegistry
export RECALLOPS_BASE_SUBMITTER=0xYourApprovedWallet
export RECALLOPS_BASE_DEPLOYMENT_BLOCK=123456
export RECALLOPS_ENABLE_BASE_SEPOLIA=true
export RECALLOPS_BASE_APPROVAL_ID=human-approval-reference
```

The official rate-limited public Base RPC is suitable for reads but does not sign transactions. The deployment and first anchor must be separately signed by the approved wallet. Record the contract address, deployment transaction, anchor transaction, block numbers, chain ID, exact Git commit, and explorer links in `docs/evidence/` only after independently verifying them.

## Claim policy

The Base multiplier remains unclaimed until both a real Base Sepolia deployment and a real product-triggered anchor transaction are visible on the official explorer. Local Anvil hashes are never presented as public evidence.
