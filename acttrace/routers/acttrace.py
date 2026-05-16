"""ActTrace HTTP router — /api/acttrace/*.

Auth is enforced by ApiKeyAuthMiddleware (not decorators). The free diagnostic
path is on the middleware exemption list.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request

from acttrace.dependencies import get_acttrace_service
from acttrace.schemas.acttrace import (
    ActTraceClassifyRequest,
    ActTraceDiagnosticRequest,
    ActTraceDiagnosticResponse,
    ActTraceNoticeGenerateRequest,
    ActTraceNoticeRead,
    ActTraceRiskAssessmentRead,
)
from acttrace.services.acttrace_service import ActTraceService

router = APIRouter(prefix="/api/acttrace", tags=["acttrace"])


def _owner(request: Request) -> Optional[str]:
    key = getattr(request.state, "api_key", None)
    if isinstance(key, dict):
        return key.get("key_prefix") or key.get("id")
    return key


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


@router.post(
    "/diagnostics/free",
    response_model=ActTraceDiagnosticResponse,
    summary="Free EU AI Act risk diagnostic (no auth, 0 tokens)",
    responses={422: {"description": "Invalid request body"}},
)
async def free_diagnostic(
    body: ActTraceDiagnosticRequest,
    service: ActTraceService = Depends(get_acttrace_service),
) -> ActTraceDiagnosticResponse:
    return service.free_diagnostic(body.model_dump(mode="json"))


@router.post(
    "/classify",
    response_model=ActTraceRiskAssessmentRead,
    summary="Classify an AI system under the EU AI Act",
    responses={
        401: {"description": "API key required or invalid"},
        429: {"description": "Token quota exceeded"},
    },
)
async def classify(
    body: ActTraceClassifyRequest,
    request: Request,
    service: ActTraceService = Depends(get_acttrace_service),
) -> ActTraceRiskAssessmentRead:
    return service.classify_ai_system(
        body.model_dump(mode="json"),
        owner=_owner(request),
        actor_type="api",
        request_id=_request_id(request),
    )


@router.post(
    "/notices",
    response_model=ActTraceNoticeRead,
    summary="Generate an Article 50 transparency notice",
    responses={
        401: {"description": "API key required or invalid"},
        429: {"description": "Token quota exceeded"},
    },
)
async def generate_notice(
    body: ActTraceNoticeGenerateRequest,
    request: Request,
    service: ActTraceService = Depends(get_acttrace_service),
) -> ActTraceNoticeRead:
    return service.generate_notice(
        body.model_dump(mode="json"),
        owner=_owner(request),
        actor_type="api",
        request_id=_request_id(request),
    )
