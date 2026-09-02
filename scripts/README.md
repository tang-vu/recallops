# RecallOps Scripts

Scripts in this directory must be deterministic, redact secrets, validate destructive targets, and require explicit confirmation before resetting demo state.

Partner preflight is implemented as the installed Python command `recallops-partner-preflight` and exposed through `make partner-preflight`. It performs public network reads and ACP discovery only. It never creates a job, signs a transaction, or writes external state.
