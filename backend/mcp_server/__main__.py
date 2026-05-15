"""Entry point: python -m backend.mcp_server

Supports two transport modes:
  - stdio (default): for local use with Claude Desktop / Cursor / Claude Code.
  - sse: for remote use behind Docker / a reverse proxy.

Usage:
  python -m backend.mcp_server              # stdio
  python -m backend.mcp_server --sse        # SSE on 0.0.0.0:8002
  python -m backend.mcp_server --sse --port 9000

Port 8002 is deliberate — it must not collide with FinanceData2's MCP
server on 8001.
"""

import argparse
import logging
import uuid

from backend.mcp_server.server import create_server

logger = logging.getLogger("acttrace-mcp")


def _run_sse_with_auth(server, host: str, port: int) -> None:
    """Run SSE transport with X-API-Key authentication.

    Every SSE request must present a valid, active ActTrace API key via the
    ``X-API-Key`` header (or an ``?api_key=`` query param). On success the
    raw key is propagated to the tools through the request-scoped context;
    on failure a JSON 401/403 is returned without reaching any tool.
    """
    import anyio
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    from backend.dependencies import get_api_key_repository
    from backend.mcp_server.context import set_owner_key_prefix

    repo = get_api_key_repository()
    logger.info("ActTrace MCP auth enabled — validating X-API-Key")

    class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
        """Reject SSE requests lacking a valid, active ActTrace API key."""

        async def dispatch(self, request: Request, call_next):
            api_key = request.headers.get("x-api-key") or request.query_params.get(
                "api_key"
            )

            if not api_key:
                return JSONResponse(
                    {
                        "code": "missing_api_key",
                        "message": "Missing API key. Provide an X-API-Key "
                        "header or ?api_key= query param.",
                        "detail": None,
                    },
                    status_code=401,
                )

            try:
                key_record = repo.get_by_key(api_key)
            except Exception:  # noqa: BLE001 — never leak internals to caller
                logger.warning("API key lookup failed", exc_info=True)
                return JSONResponse(
                    {
                        "code": "auth_unavailable",
                        "message": "Unable to validate API key.",
                        "detail": None,
                    },
                    status_code=401,
                )

            if not key_record:
                return JSONResponse(
                    {
                        "code": "invalid_api_key",
                        "message": "Invalid API key.",
                        "detail": None,
                    },
                    status_code=401,
                )

            if not key_record.get("is_active"):
                return JSONResponse(
                    {
                        "code": "key_deactivated",
                        "message": "API key is deactivated.",
                        "detail": None,
                    },
                    status_code=403,
                )

            # Propagate the caller to tools via the request-scoped ContextVar.
            set_owner_key_prefix(api_key)

            request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

    starlette_app = server.sse_app()
    starlette_app.add_middleware(ApiKeyAuthMiddleware)

    async def _serve() -> None:
        config = uvicorn.Config(
            starlette_app,
            host=host,
            port=port,
            log_level="info",
        )
        uvi_server = uvicorn.Server(config)
        await uvi_server.serve()

    anyio.run(_serve)


def main() -> None:
    parser = argparse.ArgumentParser(description="ActTrace MCP Server")
    parser.add_argument(
        "--sse",
        action="store_true",
        help="Run with SSE transport (for Docker/remote).",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="SSE bind host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8002, help="SSE bind port (default: 8002)"
    )
    args = parser.parse_args()

    server = create_server(host=args.host, port=args.port)

    if args.sse:
        _run_sse_with_auth(server, host=args.host, port=args.port)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
