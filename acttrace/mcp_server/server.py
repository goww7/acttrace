"""Core ActTrace MCP server — registers the ActTrace tools.

Mirrors FinanceData2's ``backend/mcp_server/server.py`` pattern: a
``create_server`` factory builds a :class:`FastMCP` instance, sets the
server-level instructions, and delegates tool registration to per-module
``register`` functions.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from acttrace.mcp_server.tools import acttrace


def create_server(host: str = "0.0.0.0", port: int = 8002) -> FastMCP:
    """Build and return the ActTrace FastMCP server."""
    mcp = FastMCP(
        "acttrace",
        host=host,
        port=port,
        instructions=(
            "ActTrace MCP server — a developer-facing EU AI Act compliance "
            "assistant for non-financial SaaS and technology products. It "
            "exposes two tools: 'acttrace_classify' runs a deterministic EU "
            "AI Act risk classification of an AI feature (prohibited, "
            "possible high-risk, limited-risk/transparency, minimal-risk, or "
            "unknown), and 'acttrace_generate_transparency_notice' generates "
            "an Article 50 transparency notice that discloses AI use to end "
            "users. Use acttrace_classify when asked whether an AI feature is "
            "EU AI Act compliant or what risk tier it falls into; use "
            "acttrace_generate_transparency_notice when asked for AI "
            "disclosure copy or an Article 50 notice. ActTrace targets "
            "non-financial use cases; financial-services features are "
            "reported as out of scope. All output is informational and is "
            "NOT legal advice or certified compliance."
        ),
    )

    acttrace.register(mcp)

    return mcp
