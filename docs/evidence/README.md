# Evidence Index

This directory indexes reproducible, non-sensitive evidence. It must never contain wallet secrets, access tokens, raw private memories, email contents, payment card data, private build links, or fabricated partner artifacts.

## Evidence status

| Integration | Evidence | Status |
| --- | --- | --- |
| Sibyl Memory | Local 0.8.0 four-tier smoke test | Obtained |
| Sibyl Memory | Separate-process Session 1 write and Session 2 recall | Obtained locally and covered by an automated integration test |
| Virtuals ACP | Real job ID and verifiable link | Not obtained; fixture work will be labeled |
| Base Sepolia | Contract address and transaction hash | Not obtained |

Only real public identifiers will be added. Fixture output will be stored separately and labeled `FIXTURE MODE`.
