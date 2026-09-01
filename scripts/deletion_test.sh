#!/usr/bin/env sh
set -eu

uv run --project services/control-plane python -m recallops.benchmark.deletion \
  --output benchmark/results/deletion-test.json
