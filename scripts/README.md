# RecallOps Scripts

Scripts in this directory must be deterministic, redact secrets, validate destructive targets, and require explicit confirmation before resetting demo state.

Partner preflight is implemented as the installed Python command `recallops-partner-preflight` and exposed through `make partner-preflight`. It performs public network reads and ACP discovery only. It never creates a job, signs a transaction, or writes external state.

## Continuous demo recording

`record-demo.mjs` records the public product and real fresh-process sequence as
one uninterrupted browser video with on-screen captions. It uses an existing
demo workspace, saves one review, and runs the two labeled demo sessions. It
does not reset any database, execute a payment, publish, or submit the build.

```powershell
node scripts/record-demo.mjs --credentials "$env:LOCALAPPDATA/RecallOps/deployment-smoke-workspace.json"
```

The credential JSON must remain outside Git and contain an owner key for a
dedicated demo workspace with default policy and no pending reviews. Set
`RECALLOPS_DEMO_ORIGIN` to use another deployment. Local output goes to the
ignored `.data/demo-recordings/` directory: the original WebM and evidence JSON
with chapter timestamps, distinct PIDs/UUIDs, Git commits, and recalled source.
The captions are recorded in the browser and do not replace network responses
or modify the evidence. Inspect the recording before choosing it for submission.
