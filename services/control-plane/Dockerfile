FROM ghcr.io/astral-sh/uv:0.11.8 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY services/control-plane/pyproject.toml services/control-plane/README.md ./services/control-plane/
COPY services/control-plane/src ./services/control-plane/src

RUN uv sync --frozen --no-dev --package recallops-control-plane

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RECALLOPS_MEMORY_DB=/data/recallops.db

EXPOSE 8000

CMD ["uvicorn", "recallops.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
