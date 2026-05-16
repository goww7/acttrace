"""API key authentication middleware for the ActTrace API.

Adapted from FinanceData2's ``ApiKeyAuthMiddleware``, simplified for the MVP:
one SQLite file, no billing-period headers, no geo/IP enrichment.

Responsibilities, every request:
  * stamp ``request.state.request_id`` and the ``X-Request-ID`` response header
  * skip auth for exempt paths and non-``/api/*`` paths
  * for protected ``/api/*`` paths: validate ``X-API-Key``, charge tokens,
    attach the key dict to ``request.state.api_key``, and emit rate-limit
    headers on the response

When ``enabled`` is False the middleware still sets the request id but does
no authentication at all.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from acttrace.services.api_key_service import ApiKeyService

logger = logging.getLogger("acttrace")

# Paths that never require an API key. The free diagnostic is the public
# funnel entry point; key issuance and health must be reachable unauthenticated.
EXEMPT_PATHS = (
    "/api/acttrace/diagnostics/free",
    "/api/health",
    "/api/keys",
    "/api/keys/generate",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/",
)


def _is_exempt(path: str) -> bool:
    """True when ``path`` should bypass authentication."""
    if path == "/":
        return True
    for exempt in EXEMPT_PATHS:
        if exempt == "/":
            continue
        if path == exempt or path.startswith(exempt + "/") or path.startswith(exempt):
            return True
    return False


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Validates ``X-API-Key`` and enforces token-based quotas."""

    def __init__(self, app, api_key_service: ApiKeyService, enabled: bool = True):
        super().__init__(app)
        self._service = api_key_service
        self._enabled = enabled

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Stable per-request id, shared with downstream handlers + logs.
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()

        # Auth disabled → pass straight through, but still surface the id.
        if not self._enabled:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # CORS preflight carries no API key; let it through untouched.
        if method == "OPTIONS":
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Non-API paths and exempt paths skip auth entirely.
        if not path.startswith("/api/") or _is_exempt(path):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # ── Protected /api/* path ───────────────────────────────────────
        api_key = (request.headers.get("x-api-key") or "").strip()
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "code": "API_KEY_REQUIRED",
                    "message": (
                        "An API key is required. Include it via the "
                        "X-API-Key header. Generate a free key at "
                        "POST /api/keys/generate."
                    ),
                    "detail": None,
                },
                headers={"X-Request-ID": request_id},
            )

        try:
            usage = self._service.check_and_increment(
                api_key, endpoint=path, method=method
            )
        except ValueError as exc:
            code = str(exc)
            if code == "API_KEY_DEACTIVATED":
                status, message = 403, "This API key has been deactivated."
            elif code == "QUOTA_EXCEEDED":
                status, message = (
                    429,
                    "Token quota exceeded. Upgrade your plan to continue.",
                )
            else:
                code = "INVALID_API_KEY"
                status, message = 401, "The provided API key is not valid."
            return JSONResponse(
                status_code=status,
                content={"code": code, "message": message, "detail": None},
                headers={"X-Request-ID": request_id},
            )

        # Attach the full key dict for downstream handlers (router reads
        # request.state.api_key.key_prefix as the owner identifier).
        request.state.api_key = self._service._repo.get_by_key(api_key)

        response = await call_next(request)

        # Quota / rate-limit headers. Token unit is used with the
        # spec-standard X-RateLimit-* names so off-the-shelf SDKs react to 429s.
        tokens_charged = usage.get("tokens_charged", 0)
        tokens_remaining = usage.get("tokens_remaining", 0)
        tokens_limit = usage.get("tokens_limit", 0)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Plan"] = str(usage.get("plan", "free"))
        response.headers["X-Tokens-Charged"] = str(tokens_charged)
        response.headers["X-Tokens-Remaining"] = str(tokens_remaining)
        response.headers["X-RateLimit-Limit"] = str(tokens_limit)
        response.headers["X-RateLimit-Remaining"] = str(tokens_remaining)

        # Fire-and-forget usage log.
        try:
            key_info = getattr(request.state, "api_key", None) or {}
            self._service.log_request(
                api_key_id=key_info.get("id") if isinstance(key_info, dict) else None,
                key_prefix=(
                    key_info.get("key_prefix") if isinstance(key_info, dict) else None
                ),
                endpoint=path,
                method=method,
                status_code=response.status_code,
                tokens_charged=tokens_charged,
                is_overage=bool(usage.get("is_overage")),
                request_id=request_id,
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        except Exception:
            logger.warning("acttrace_usage_log_failed", exc_info=True)

        return response
