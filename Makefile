.PHONY: help check demo-session-1 demo-session-2 demo-reset benchmark

help:
	@echo "RecallOps targets"
	@echo "  check           Run all implemented local quality gates"
	@echo "  demo-session-1  Persist a deterministic failed outcome"
	@echo "  demo-session-2  Recall it from a fresh process"
	@echo "  demo-reset      Reset only the validated demo database with confirmation"
	@echo "  benchmark       Compare Sibyl memory with the explicit stateless baseline"

check:
	@echo "Quality gates are added with each workspace milestone."

demo-session-1:
	@echo "Available after the Milestone 1 vertical slice."

demo-session-2:
	@echo "Available after the Milestone 1 vertical slice."

demo-reset:
	@echo "Available after the Milestone 1 vertical slice."

benchmark:
	@echo "Available after the benchmark milestone."
