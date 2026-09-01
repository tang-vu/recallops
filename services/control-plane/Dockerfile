FROM ghcr.io/astral-sh/uv:0.11.8 AS uv

FROM node:24.14.1-slim AS base-client
WORKDIR /build/packages/contracts
COPY packages/contracts/package.json packages/contracts/package-lock.json ./
RUN npm ci
COPY packages/contracts/client ./client
COPY packages/contracts/tsconfig.json ./
RUN npm run build && npm prune --omit=dev

FROM python:3.12-slim

COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=base-client /usr/local/bin/node /usr/local/bin/node
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY services/control-plane/pyproject.toml services/control-plane/README.md ./services/control-plane/
COPY services/control-plane/src ./services/control-plane/src
COPY --from=base-client /build/packages/contracts/dist ./packages/contracts/dist
COPY --from=base-client /build/packages/contracts/node_modules ./packages/contracts/node_modules

RUN uv sync --frozen --no-dev --package recallops-control-plane

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    RECALLOPS_MEMORY_DB=/data/recallops.db

EXPOSE 8000

CMD ["uvicorn", "recallops.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
