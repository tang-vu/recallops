.PHONY: help install check api demo-session-1 demo-session-2 demo-reset benchmark

UV ?= uv
DEMO_DB ?= $(CURDIR)/.data/demo/recallops-demo.db

help:
	@echo "RecallOps targets"
	@echo "  check           Run all implemented local quality gates"
	@echo "  api             Start the versioned FastAPI control plane"
	@echo "  demo-session-1  Persist a deterministic failed outcome"
	@echo "  demo-session-2  Recall it from a fresh process"
	@echo "  demo-reset      Reset only the validated demo database with confirmation"
	@echo "  benchmark       Compare Sibyl memory with the explicit stateless baseline"

install:
	$(UV) sync --all-packages --all-extras --python 3.12

check:
	$(UV) run --project services/control-plane ruff format --check --config services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane ruff check --config services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane mypy --config-file services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane pytest -c services/control-plane/pyproject.toml services/control-plane/tests --cov=recallops --cov-report=term-missing

api:
	$(UV) run --project services/control-plane uvicorn recallops.api.app:app --host 127.0.0.1 --port 8000

demo-session-1:
	$(UV) run --project services/control-plane python -m recallops.demo.session1 --db "$(DEMO_DB)"

demo-session-2:
	$(UV) run --project services/control-plane python -m recallops.demo.session2 --db "$(DEMO_DB)"

demo-reset:
	$(UV) run --project services/control-plane python -m recallops.demo.reset --db "$(DEMO_DB)" --confirm RESET_RECALLOPS_DEMO

benchmark:
	@echo "Available after the benchmark milestone."
