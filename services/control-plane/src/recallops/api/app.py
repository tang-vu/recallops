"""FastAPI application for the memory-gated RecallOps control plane."""

from __future__ import annotations

import hmac
import json
import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse

from recallops import __version__
from recallops.api.logging import log_event
from recallops.api.schemas import (
    ApprovalWriteRequest,
    BenchmarkUnavailable,
    BudgetWriteRequest,
    DemoProcessResponse,
    EvaluationResponse,
    ExceptionWriteRequest,
    ExecutionAuthorizationResponse,
    ExecutionRequest,
    JobCallbackRequest,
    JobResponse,
    JobVerificationRequest,
    JobWriteRequest,
    MemoryWriteResponse,
    PermissionWriteRequest,
    PolicyWriteRequest,
    SystemStatusResponse,
)
from recallops.memory.port import MemorySubsystemError
from recallops.memory.sibyl_store import SibylMemoryStore
from recallops.models import (
    Decision,
    FailureFingerprint,
    IdempotencyRecord,
    JobStatus,
    ProposedAction,
    VerificationOutcome,
)
from recallops.orchestration.execution import (
    ExecutionDeniedError,
    ExecutionGate,
    ReceiptExpiredError,
    ReceiptNotFoundError,
    ReplayConflictError,
    request_digest,
    sha256_text,
)
from recallops.orchestration.guard import CommerceGuard
from recallops.orchestration.jobs import JobStateMachine, JobTransitionError
from recallops.policy.engine import PolicyEngine

LOGGER = logging.getLogger("recallops.api")


def _configured_path(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit.expanduser().resolve()
    raw = os.getenv("RECALLOPS_MEMORY_DB")
    return Path(raw).expanduser().resolve() if raw else None


def _path_hint(path: Path | None) -> str | None:
    return f".../{path.name}" if path is not None else None


def create_app(*, memory_db: Path | None = None, admin_token: str | None = None) -> FastAPI:
    configured_db = _configured_path(memory_db)
    configured_admin_token = admin_token or os.getenv("RECALLOPS_ADMIN_TOKEN") or None
    application = FastAPI(
        title="RecallOps Control Plane",
        version=__version__,
        description="Memory-gated policy decisions for autonomous agent commerce.",
        openapi_url="/v1/openapi.json",
    )

    @contextmanager
    def store(tenant_id: str) -> Iterator[SibylMemoryStore]:
        if configured_db is None:
            raise MemorySubsystemError("RECALLOPS_MEMORY_DB is not configured")
        with SibylMemoryStore(configured_db, tenant_id) as opened:
            yield opened

    def require_admin(
        supplied: Annotated[str | None, Header(alias="X-RecallOps-Admin-Token")] = None,
    ) -> None:
        if configured_admin_token is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Administrative mutations are disabled until RECALLOPS_ADMIN_TOKEN is set.",
            )
        if supplied is None or not hmac.compare_digest(supplied, configured_admin_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @application.middleware("http")
    async def correlation_middleware(request: Request, call_next: Any) -> Response:
        supplied = request.headers.get("x-correlation-id", "")
        try:
            correlation_id = str(UUID(supplied))
        except ValueError:
            correlation_id = str(uuid4())
        request.state.correlation_id = correlation_id
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > 1_048_576:
                    error_response = JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={"detail": "Request body exceeds the 1 MiB limit."},
                    )
                    error_response.headers["X-Correlation-ID"] = correlation_id
                    return error_response
            except ValueError:
                error_response = JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length header."},
                )
                error_response.headers["X-Correlation-ID"] = correlation_id
                return error_response
        try:
            response = cast(Response, await call_next(request))
        except Exception:
            log_event(
                LOGGER,
                "request.failed",
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
            )
            raise
        response.headers["X-Correlation-ID"] = correlation_id
        log_event(
            LOGGER,
            "request.completed",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response

    @application.get("/health")
    def health() -> JSONResponse:
        if configured_db is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "degraded", "memory": "not_configured"},
            )
        try:
            with store("recallops-health") as memory:
                result = memory.health()
        except MemorySubsystemError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "degraded", "memory": "unavailable"},
            )
        return JSONResponse(content={"status": "ok", "memory": result})

    @application.get("/v1/system/status", response_model=SystemStatusResponse)
    def system_status() -> SystemStatusResponse:
        healthy = False
        if configured_db is not None:
            try:
                with store("recallops-health") as memory:
                    healthy = bool(memory.health()["healthy"])
            except MemorySubsystemError:
                healthy = False
        return SystemStatusResponse(
            version=__version__,
            memory_configured=configured_db is not None,
            memory_healthy=healthy,
            memory_path_hint=_path_hint(configured_db),
            virtuals_mode=os.getenv("RECALLOPS_VIRTUALS_MODE", "FIXTURE MODE"),
            base_mode=os.getenv("RECALLOPS_BASE_MODE", "LOCAL ONLY"),
            base_chain_id=int(os.getenv("RECALLOPS_BASE_CHAIN_ID", "84532")),
            fixture_data=True,
        )

    @application.post(
        "/v1/policies", response_model=MemoryWriteResponse, dependencies=[Depends(require_admin)]
    )
    def write_policy(payload: PolicyWriteRequest) -> MemoryWriteResponse:
        with store(payload.policy.tenant_id) as memory:
            writes = memory.write_policy(payload.policy, str(payload.source_session_id))
        return MemoryWriteResponse(writes=tuple(writes))

    @application.get("/v1/policies/current")
    def current_policy(tenant_id: str, owner_id: str) -> Any:
        with store(tenant_id) as memory:
            result = memory.get_current_policy(owner_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        return result

    @application.post(
        "/v1/budgets", response_model=MemoryWriteResponse, dependencies=[Depends(require_admin)]
    )
    def write_budget(payload: BudgetWriteRequest) -> MemoryWriteResponse:
        with store(payload.budget.tenant_id) as memory:
            writes = memory.write_budget(payload.budget)
        return MemoryWriteResponse(writes=tuple(writes))

    @application.post(
        "/v1/permissions",
        response_model=MemoryWriteResponse,
        dependencies=[Depends(require_admin)],
    )
    def write_permission(payload: PermissionWriteRequest) -> MemoryWriteResponse:
        with store(payload.permission.tenant_id) as memory:
            writes = memory.write_permission(payload.permission)
        return MemoryWriteResponse(writes=tuple(writes))

    @application.post(
        "/v1/exceptions",
        response_model=MemoryWriteResponse,
        dependencies=[Depends(require_admin)],
    )
    def write_exception(payload: ExceptionWriteRequest) -> MemoryWriteResponse:
        with store(payload.exception.tenant_id) as memory:
            writes = memory.write_exception(payload.exception)
        return MemoryWriteResponse(writes=tuple(writes))

    @application.post(
        "/v1/approvals",
        response_model=MemoryWriteResponse,
        dependencies=[Depends(require_admin)],
    )
    def write_approval(payload: ApprovalWriteRequest) -> MemoryWriteResponse:
        with store(payload.approval.tenant_id) as memory:
            receipt = memory.get_decision(str(payload.approval.receipt_id))
            if (
                receipt is None
                or receipt.decision is not Decision.ESCALATE
                or receipt.action_id != payload.approval.action_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Approval must reference the same action on an ESCALATE receipt.",
                )
            writes = memory.write_human_approval(payload.approval)
        return MemoryWriteResponse(writes=tuple(writes))

    @application.post("/v1/actions/evaluate", response_model=EvaluationResponse)
    def evaluate_action(
        action: ProposedAction,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8)],
    ) -> EvaluationResponse:
        body_digest = request_digest(action.model_dump(mode="json"))
        key_digest = sha256_text(idempotency_key)
        operation = "evaluate-action"
        try:
            with store(action.tenant_id) as memory:
                existing = memory.get_idempotency_record(operation, key_digest)
                if existing is not None:
                    if not hmac.compare_digest(existing.request_digest, body_digest):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Idempotency key was already used for a different request.",
                        )
                    receipt = memory.get_decision(existing.result_reference)
                    if receipt is None:
                        raise MemorySubsystemError("Idempotency result receipt is missing")
                    return EvaluationResponse(receipt=receipt, writes=(), idempotent_replay=True)
                receipt, writes = CommerceGuard(memory).evaluate(action)
                if writes:
                    writes.extend(
                        memory.write_idempotency_record(
                            IdempotencyRecord(
                                tenant_id=action.tenant_id,
                                operation=operation,
                                key_digest=key_digest,
                                request_digest=body_digest,
                                result_reference=str(receipt.receipt_id),
                            )
                        )
                    )
                return EvaluationResponse(receipt=receipt, writes=tuple(writes))
        except MemorySubsystemError:
            receipt = PolicyEngine().fail_closed(
                action,
                "MEMORY_READ_FAILED",
                "Mandatory Sibyl Memory is unavailable; commerce is stopped.",
            )
            return EvaluationResponse(receipt=receipt, writes=())

    @application.post(
        "/v1/actions/{action_id}/execute", response_model=ExecutionAuthorizationResponse
    )
    def authorize_execution(
        action_id: UUID,
        payload: ExecutionRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8)],
        tenant_id: Annotated[str, Query(min_length=1, max_length=128)],
    ) -> ExecutionAuthorizationResponse:
        digest = request_digest({"action_id": str(action_id), **payload.model_dump(mode="json")})
        try:
            with store(tenant_id) as memory:
                authorization, replay, writes = ExecutionGate(memory).authorize(
                    receipt_id=payload.receipt_id,
                    action_id=action_id,
                    idempotency_key=idempotency_key,
                    request_body_digest=digest,
                )
        except ReceiptNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ReceiptExpiredError as exc:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
        except (ExecutionDeniedError, ReplayConflictError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return ExecutionAuthorizationResponse(
            authorization=authorization,
            writes=tuple(writes),
            idempotent_replay=replay,
        )

    @application.get("/v1/decisions/{receipt_id}")
    def get_decision(receipt_id: UUID, tenant_id: str) -> Any:
        with store(tenant_id) as memory:
            receipt = memory.get_decision(str(receipt_id))
        if receipt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
        return receipt

    @application.get("/v1/decisions")
    def list_decisions(tenant_id: str, limit: Annotated[int, Query(ge=1, le=500)] = 100) -> Any:
        with store(tenant_id) as memory:
            return memory.list_decisions(limit)

    @application.get("/v1/memory/evidence")
    def memory_evidence(tenant_id: str, limit: Annotated[int, Query(ge=1, le=500)] = 100) -> Any:
        with store(tenant_id) as memory:
            return memory.list_journal(limit)

    @application.get("/v1/counterparties")
    def counterparties(tenant_id: str, limit: Annotated[int, Query(ge=1, le=500)] = 100) -> Any:
        with store(tenant_id) as memory:
            return memory.list_counterparties(limit)

    @application.post(
        "/v1/jobs",
        response_model=JobResponse,
        dependencies=[Depends(require_admin)],
    )
    def create_job(payload: JobWriteRequest) -> JobResponse:
        if payload.job.integration_mode == "LIVE VIRTUALS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Live jobs can only be created by the configured Virtuals adapter.",
            )
        with store(payload.job.tenant_id) as memory:
            authorization = memory.get_execution_authorization(str(payload.job.receipt_id))
            if (
                authorization is None
                or authorization.action_id != payload.job.action_id
                or payload.job.status is not JobStatus.CREATED
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A job requires a matching durable execution authorization.",
                )
            if memory.get_job(payload.job.job_id) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Job already exists"
                )
            writes = memory.write_job(payload.job, "JOB_CREATED")
        return JobResponse(job=payload.job, writes=tuple(writes))

    @application.post(
        "/v1/jobs/{job_id}/submitted",
        response_model=JobResponse,
        dependencies=[Depends(require_admin)],
    )
    def submit_job(job_id: str, payload: JobCallbackRequest) -> JobResponse:
        with store(payload.tenant_id) as memory:
            job = memory.get_job(job_id)
            if job is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            try:
                updated, duplicate = JobStateMachine().mark_submitted(job, payload.callback_id)
            except JobTransitionError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            writes = [] if duplicate else memory.write_job(updated, "JOB_SUBMITTED")
        return JobResponse(job=updated, writes=tuple(writes), duplicate_callback=duplicate)

    @application.post(
        "/v1/jobs/{job_id}/verify",
        response_model=JobResponse,
        dependencies=[Depends(require_admin)],
    )
    def verify_job(job_id: str, payload: JobVerificationRequest) -> JobResponse:
        with store(payload.tenant_id) as memory:
            job = memory.get_job(job_id)
            if job is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            outcome = VerificationOutcome(payload.outcome)
            try:
                updated, duplicate = JobStateMachine().verify(
                    job,
                    callback_id=payload.callback_id,
                    outcome=outcome,
                    verifier_id=payload.verifier_id,
                    reason=payload.reason,
                )
            except JobTransitionError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            writes: list[dict[str, str]] = []
            if not duplicate:
                writes.extend(memory.write_job(updated, f"VERIFICATION_{outcome.value}"))
                if outcome is VerificationOutcome.FAILED:
                    writes.extend(
                        memory.write_failure(
                            FailureFingerprint(
                                tenant_id=job.tenant_id,
                                provider_id=job.provider_id,
                                task_category=job.task_category,
                                task_fingerprint=job.task_fingerprint,
                                verifier_id=payload.verifier_id,
                                verification_reason=payload.reason,
                                source_session_id=payload.source_session_id,
                                job_reference=job.job_id,
                            )
                        )
                    )
        return JobResponse(job=updated, writes=tuple(writes), duplicate_callback=duplicate)

    @application.post(
        "/v1/jobs/{job_id}/authorize-payment",
        response_model=JobResponse,
        dependencies=[Depends(require_admin)],
    )
    def authorize_job_payment(job_id: str, payload: JobCallbackRequest) -> JobResponse:
        with store(payload.tenant_id) as memory:
            job = memory.get_job(job_id)
            if job is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            try:
                updated, duplicate = JobStateMachine().authorize_payment(job, payload.callback_id)
            except JobTransitionError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            writes = [] if duplicate else memory.write_job(updated, "PAYMENT_AUTHORIZED")
        return JobResponse(job=updated, writes=tuple(writes), duplicate_callback=duplicate)

    @application.get("/v1/jobs/{job_id}")
    def get_job(job_id: str, tenant_id: str) -> Any:
        with store(tenant_id) as memory:
            job = memory.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job

    def run_demo_process(module: str) -> DemoProcessResponse:
        if configured_db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RECALLOPS_MEMORY_DB is not configured",
            )
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-m", module, "--db", str(configured_db)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Demo child process failed; inspect redacted server logs.",
            )
        return DemoProcessResponse(result=json.loads(completed.stdout))

    @application.post(
        "/v1/demo/session-1",
        response_model=DemoProcessResponse,
        dependencies=[Depends(require_admin)],
    )
    def demo_session_1() -> DemoProcessResponse:
        return run_demo_process("recallops.demo.session1")

    @application.post(
        "/v1/demo/session-2",
        response_model=DemoProcessResponse,
        dependencies=[Depends(require_admin)],
    )
    def demo_session_2() -> DemoProcessResponse:
        return run_demo_process("recallops.demo.session2")

    @application.get("/v1/benchmark/latest", response_model=BenchmarkUnavailable)
    def benchmark_latest() -> BenchmarkUnavailable:
        return BenchmarkUnavailable()

    return application


app = create_app()
