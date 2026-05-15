"""MCP request-scoped context: carries the authenticated API key owner prefix.

Mirrors FinanceData2's ``backend/mcp_server/context.py``. The SSE auth
middleware validates the presented ``X-API-Key`` and calls
``set_owner_key_prefix``; any MCP tool then reads ``get_owner_key_prefix`` to
scope its work to the caller. A ``contextvars.ContextVar`` keeps this safe
across concurrent SSE requests.
"""

from __future__ import annotations

import contextvars

_owner_key_prefix: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mcp_owner_key_prefix", default=""
)


def set_owner_key_prefix(api_key: str) -> None:
    """Called from the MCP auth middleware after the X-API-Key is validated."""
    _owner_key_prefix.set(api_key[:10] if api_key else "")


def get_owner_key_prefix() -> str:
    """Called from any MCP tool to scope work / audit events to the caller."""
    return _owner_key_prefix.get()
