"""ActTrace MCP tools — EU AI Act risk classification + transparency notices.

Two tools, both thin wrappers over :class:`ActTraceService`:

  - ``acttrace_classify`` — deterministic EU AI Act risk classification of an
    AI feature.
  - ``acttrace_generate_transparency_notice`` — generates an Article 50
    transparency notice.

The service runs synchronous SQLite work, so calls are pushed onto a worker
thread via ``asyncio.to_thread``. The service already persists results and
writes audit events — the tools must not duplicate that.

Output is **not legal advice**; the service attaches a ``disclaimer`` field to
every result.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from acttrace.dependencies import get_acttrace_service
from acttrace.mcp_server.context import get_owner_key_prefix


def _ok(tool: str, data: Any) -> str:
    """Canonical success envelope, serialized as a JSON string."""
    return json.dumps({"ok": True, "tool": tool, "data": data}, default=str)


def _err(exc: Exception) -> str:
    """Canonical error envelope for a failed tool call."""
    return json.dumps(
        {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, default=str
    )


def register(mcp: FastMCP) -> None:
    """Register the ActTrace tools onto the given FastMCP instance."""

    @mcp.tool()
    async def acttrace_classify(
        feature_name: str,
        description: Optional[str] = None,
        use_case: Optional[str] = None,
        user_facing: Optional[bool] = None,
        eu_available: Optional[bool] = None,
        internal_only: Optional[bool] = None,
        model_provider: Optional[str] = None,
        human_review_level: Optional[str] = None,
        automated_decision: Optional[bool] = None,
        high_risk_domain: Optional[bool] = None,
        sensitive_data: Optional[bool] = None,
        financial_override: bool = False,
    ) -> str:
        """Classify an AI feature's EU AI Act risk category.

        Runs ActTrace's deterministic classification engine and returns a
        risk category (``prohibited``, ``possible_high_risk``,
        ``limited_risk_transparency``, ``minimal_risk``, ``unknown``, or
        ``out_of_scope_financial_services``) with confidence, rationale,
        triggering facts, missing information, obligations, and source
        references.

        Use this when asked "Is this AI feature EU AI Act compliant?", "What
        risk tier does my AI feature fall into?", or for a general AI Act
        risk classification.

        ActTrace is for non-financial SaaS / technology products. Financial
        use cases are reported as ``out_of_scope_financial_services`` unless
        ``financial_override`` is set. The result is informational and is
        NOT legal advice.

        Args:
            feature_name: Short name of the AI feature (e.g. "support chatbot").
            description: What the feature does. Strongly recommended — an
                empty description yields an ``unknown`` verdict.
            use_case: Short use-case label (e.g. "support_assist").
            user_facing: True if end users interact with the feature.
            eu_available: True if the feature is available to EU users.
            internal_only: True if the feature is for internal staff only.
            model_provider: Underlying model provider (e.g. "OpenAI"). Required
                for a confident verdict when the feature is user-facing.
            human_review_level: One of "none", "optional",
                "required_before_action", "required_after_action".
            automated_decision: True if the feature makes automated decisions.
            high_risk_domain: True if the feature operates in a high-risk
                domain (hiring, education, biometrics, etc.).
            sensitive_data: True if the feature processes sensitive data.
            financial_override: Set True to bypass the financial-services
                out-of-scope guard for a borderline non-financial feature.
        """
        try:
            service = get_acttrace_service()
            payload = {
                "feature_name": feature_name,
                "description": description,
                "use_case": use_case,
                "user_facing": user_facing,
                "eu_available": eu_available,
                "internal_only": internal_only,
                "model_provider": model_provider,
                "human_review_level": human_review_level,
                "automated_decision": automated_decision,
                "high_risk_domain": high_risk_domain,
                "sensitive_data": sensitive_data,
                "financial_override": financial_override,
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            result = await asyncio.to_thread(
                service.classify_ai_system,
                payload,
                owner=get_owner_key_prefix() or None,
                actor_type="mcp",
            )
            return _ok("acttrace_classify", result)
        except Exception as exc:  # noqa: BLE001 — surface as error envelope
            return _err(exc)

    @mcp.tool()
    async def acttrace_generate_transparency_notice(
        ai_system_name: str,
        notice_type: str,
        feature_name: Optional[str] = None,
        tone: str = "plain",
        language: str = "en",
        human_review_level: Optional[str] = None,
        risk_category: Optional[str] = None,
    ) -> str:
        """Generate an EU AI Act Article 50 transparency notice.

        Produces user-facing copy that discloses AI use, plus a suggested
        placement, caveats, and a human-review recommendation.

        Use this when asked for an "AI transparency notice", "Article 50
        notice", "AI disclosure copy", or "chatbot AI disclaimer".

        ActTrace is for non-financial SaaS / technology products. The
        generated notice is a starting draft and is NOT legal advice.

        Args:
            ai_system_name: Name of the AI system / product the notice is for.
            notice_type: One of "chatbot", "ai_generated_content",
                "support_assist", "summarization", "synthetic_media",
                "internal_ai", "other".
            feature_name: Optional short name of the specific feature.
            tone: One of "plain", "formal", "developer_docs", "policy",
                "ui_microcopy". Defaults to "plain".
            language: Notice language. English ("en") only for the MVP.
            human_review_level: One of "none", "optional",
                "required_before_action", "required_after_action". When set to
                "required_before_action" the notice will not recommend extra
                human review.
            risk_category: Optional risk category from a prior classification
                to tailor the notice.
        """
        try:
            service = get_acttrace_service()
            payload = {
                "ai_system_name": ai_system_name,
                "feature_name": feature_name,
                "notice_type": notice_type,
                "tone": tone,
                "language": language,
                "human_review_level": human_review_level,
                "risk_category": risk_category,
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            result = await asyncio.to_thread(
                service.generate_notice,
                payload,
                owner=get_owner_key_prefix() or None,
                actor_type="mcp",
            )
            return _ok("acttrace_generate_transparency_notice", result)
        except Exception as exc:  # noqa: BLE001 — surface as error envelope
            return _err(exc)
