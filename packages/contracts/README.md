# RecallOps Contracts

`RecallOpsReceiptRegistry` anchors non-sensitive decision digests after the memory gate. It does not store policy text, memories, prompts, deliverables, personal data, or funds.

## Local checks

```bash
forge fmt --check --root packages/contracts
forge test --root packages/contracts -vvv
forge snapshot --root packages/contracts --check
npm ci --prefix packages/contracts
npm --prefix packages/contracts run check
```

The contract accepts deployments only on local Anvil chain ID `31337` or Base Sepolia chain ID `84532`. Calls recheck the runtime chain, accept only the immutable authorized submitter, and treat an exact repeated receipt as an idempotent no-op. A conflicting reuse of the same receipt digest reverts.

The typed viem client in `client/` verifies chain ID, deployed contract configuration, submitter authorization, simulation, transaction success, emitted state, and exact idempotent replay. It receives requests over standard input and never accepts a private key. A local Anvil node may expose an unlocked development account; Base Sepolia requires a separately approved wallet-enabled RPC signer plus two explicit live gates.

## Deployment

`script/DeployLocal.s.sol` is limited to Anvil. `script/DeployBaseSepolia.s.sol` is limited to Base Sepolia and requires `RECALLOPS_RECEIPT_SUBMITTER`.

No Base Sepolia deployment has been made. See `docs/base-deployment.md` for the approval boundary and evidence checklist.
