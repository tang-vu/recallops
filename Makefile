.PHONY: help install check check-contracts check-e2e api web demo-session-1 demo-session-2 demo-reset benchmark deletion-test

UV ?= uv
FORGE ?= forge
DEMO_DB ?= $(CURDIR)/.data/demo/recallops-demo.db

help:
	@echo "RecallOps targets"
	@echo "  check           Run all implemented local quality gates"
	@echo "  check-e2e       Run the Playwright presentation path"
	@echo "  check-contracts Run Foundry and viem receipt registry gates"
	@echo "  api             Start the versioned FastAPI control plane"
	@echo "  web             Start the judge-facing operations console"
	@echo "  demo-session-1  Persist a deterministic failed outcome"
	@echo "  demo-session-2  Recall it from a fresh process"
	@echo "  demo-reset      Reset only the validated demo database with confirmation"
	@echo "  benchmark       Compare Sibyl memory with the explicit stateless baseline"
	@echo "  deletion-test   Prove disabled Sibyl stops production commerce"

install:
	$(UV) sync --all-packages --all-extras --python 3.12
	npm ci --prefix apps/web
	npm ci --prefix packages/contracts

check:
	$(UV) run --project services/control-plane ruff format --check --config services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane ruff check --config services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane mypy --config-file services/control-plane/pyproject.toml services/control-plane/src services/control-plane/tests
	$(UV) run --project services/control-plane pytest -c services/control-plane/pyproject.toml services/control-plane/tests --cov=recallops --cov-report=term-missing
	mkdir -p .data
	$(UV) export --project services/control-plane --format requirements-txt --no-emit-project --no-dev --no-hashes --output-file .data/audit-requirements.txt
	$(UV) tool run pip-audit --strict --requirement .data/audit-requirements.txt
	npm --prefix apps/web run typecheck
	npm --prefix apps/web run lint
	npm --prefix apps/web run test
	npm --prefix apps/web run build
	npm --prefix apps/web run test:e2e
	npm audit --prefix apps/web --audit-level=high
	$(MAKE) check-contracts

check-contracts:
	$(FORGE) fmt --check --root packages/contracts
	$(FORGE) lint --root packages/contracts --severity high
	$(FORGE) test --root packages/contracts -vvv
	$(FORGE) snapshot --root packages/contracts --check packages/contracts/.gas-snapshot
	npm --prefix packages/contracts run check
	npm audit --prefix packages/contracts --audit-level=high

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
	$(UV) run --project services/control-plane python -m recallops.benchmark.runner --db "$(CURDIR)/.data/benchmark/recallops-benchmark.db" --output-dir "$(CURDIR)/benchmark/results" --seed 20260901 --replace

deletion-test:
	$(UV) run --project services/control-plane python -m recallops.benchmark.deletion --output "$(CURDIR)/benchmark/results/deletion-test.json"
