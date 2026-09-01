# Local Base Registry Evidence

Status: local development evidence only. This is not Base Sepolia evidence and does not support a partner multiplier claim.

Executed on 2026-09-01 UTC with Foundry 1.8.1, Solidity 0.8.36, viem 2.56.1, and Anvil chain ID 31337.

## Automated checks

- 13 Foundry tests passed with no failures.
- Two fuzz tests ran 512 cases each for receipt uniqueness and submitter authorization.
- `forge fmt --check` passed.
- `forge lint --severity high` passed.
- Gas snapshot generation and comparison passed.
- Three viem unit tests passed, followed by strict TypeScript compilation.
- Python API integration proved that pre-verification anchoring is blocked and post-verification replay is idempotent.

## Local transaction

- Registry: `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`
- Authorized Anvil development submitter: `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`
- Viem transaction: `0x5be41edc311b7ba79091bb0843d7544c2f348a1f5ba02b8c1206ec213ca0b751`
- Receipt digest: `0x900f746ddc0ca4293a966e13c9690654cb423728fd812774352b106325823014`
- Persisted record hash: `0xace2a160d21f4d28e35044edfff2cdb16ebcc5afe35e0fece03445267afea0b6`

The receipt returned success, the registry reported the digest as anchored, and `anchorCount` reflected one new record. Repeating the same viem request returned the original transaction hash with `created=false`; no second event was created.

Anvil state is ephemeral and has no public explorer link. These identifiers are included only to make the local verification trace inspectable.
