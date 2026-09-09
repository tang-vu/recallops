# Per-receipt revocation release / September 9, 2026

Released commit `8469fdf581d598b3c5855325bb27487c38681ca8` to
https://recallops.tangvu.dev after backing up runtime data and restarting only
the RecallOps API and web services. Both services and the tunnel are online.

## Public deployment verification

Verified at `2026-09-09T15:44:37Z` using the dedicated deployment smoke workspace:

- Two separate LOW requests originally returned APPROVE.
- The owner revoked one receipt through the real browser UI with the reason
  "The user canceled this specific audit."
- A browser reload retained the revocation and reason.
- The agent authorization endpoint returned `allowed_now: false` and
  `RECEIPT_REVOKED` for that receipt, before its expiry.
- The other receipt returned `allowed_now: true` and
  `CURRENT_POLICY_CHECKS_PASSED` at the same verification point.
- History retained the original APPROVE as historical evidence, with the
  current revocation displayed above it.

The local evidence JSON and real browser screenshot are under the ignored
`.data/revocation-release/` directory. Screenshot SHA-256:
`166ab0c951751b9235a4a64092968c55884de5b79bce343f0d6bb2007f35a528`.

## Checks and limits

[CI run 34371444560](https://github.com/tang-vu/recallops/actions/runs/34371444560)
passed all three jobs: Python control plane, web console, and receipt registry.
Local validation passed 75 backend tests, strict mypy and Ruff, web type/lint
checks, 3 web unit tests, production build, and 11 browser cases with one
existing duplicate mobile demo writer skipped. Both revocation viewport cases
passed again after the final history layout adjustment.

Revocation takes effect when the agent checks current authorization. It cannot
undo completed execution, reserve funds, or block an independently evaluated
new request. A broad stop still requires policy restrictions or pausing access.
Memory errors fail closed; an unsuccessful revocation write is not acknowledged
as saved. No payment or live partner transaction was performed in this check.
