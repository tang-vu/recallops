.PHONY: help install check check-e2e api web demo-session-1 demo-session-2 demo-reset benchmark

UV ?= uv
DEMO_DB ?= $(CURDIR)/.data/demo/recallops-demo.db

help:
	@echo "RecallOps targets"
	@echo "  check           Run all implemented local quality gates"
	@echo "  check-e2e       Run the Playwright presentation path"
	@echo "  api             Start the versioned FastAPI control plane"
	@echo "  web             Start the judge-facing operations console"
	@echo "  demo-session-1  Persist a deterministic failed outcome"
	@echo "  demo-session-2  Recall it from a fresh process"
	@echo "  demo-reset      Reset only the validated demo database with confirmation"
	@echo "  benchmark       Compare Sibyl memory with the explicit stateless baseline"

install:
	$(UV) sync --all-packages --all-extras --python 3.12
	npm ci --prefix apps/web

check:
	$(UV) run --project services/control-plane ruff format --check --config services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane ruff check --config services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane mypy --config-file services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane pytest -c services/control-plane/pyproject.toml services/control-plane/tests --cov=recallops --cov-report=term-missing
	npm --prefix apps/web run typecheck
	npm --prefix apps/web run lint
	npm --prefix apps/web run test
	npm --prefix apps/web run build
	npm --prefix apps/web run test:e2e

check-e2e:
	npm --prefix apps/web run test:e2e

api:
	$(UV) run --project services/control-plane uvicorn recallops.api.app:app --host 127.0.0.1 --port 8000

web:
	npm --prefix apps/web run dev

demo-session-1:
	$(UV) run --project services/control-plane python -m recallops.demo.session1 --db "$(DEMO_DB)"

demo-session-2:
	$(UV) run --project services/control-plane python -m recallops.demo.session2 --db "$(DEMO_DB)"

demo-reset:
	$(UV) run --project services/control-plane python -m recallops.demo.reset --db "$(DEMO_DB)" --confirm RESET_RECALLOPS_DEMO

benchmark:
	@echo "Available after the benchmark milestone."
