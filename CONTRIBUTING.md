# Contributing

RecallOps is a solo hackathon project, but focused issues and pull requests are welcome.

## Development rules

1. Keep Sibyl Memory on the production execution critical path.
2. Never add a silent production memory fallback.
3. Use decimal-safe currency types and deterministic policy rules.
4. Label all fixture data and keep it separate from live evidence.
5. Do not commit secrets, wallet material, local databases, or fabricated evidence.
6. Add tests for policy and state-transition changes.

Use conventional commits and run the relevant checks before opening a pull request. The root `make check` target will become the complete local quality gate as each workspace is added.
