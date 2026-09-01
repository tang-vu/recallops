# Virtuals Runtime Boundary

RecallOps integrates with the maintained `@virtuals-protocol/acp-cli` through the Python adapter in `services/control-plane/src/recallops/integrations/virtuals.py`. The CLI is an operator-supplied, opt-in live prerequisite and is not part of the default control-plane or web dependency graph.

On 2026-09-01, an isolated install of ACP CLI 1.0.34 showed that the official package still transitively includes deprecated `@virtuals-protocol/acp-node` for legacy commands and reported unresolved high-severity npm audit findings. RecallOps never invokes legacy commands, but does not vendor that dependency while those findings remain. The exact audit result and live setup decision are recorded in `docs/virtuals-live-setup.md`.

Fixture mode and all automated tests require no ACP package, credentials, wallet, or network access. Live mode requires a separately reviewed CLI installation and remains dispatch-disabled until `RECALLOPS_ENABLE_LIVE_VIRTUALS=true` is explicitly configured.
