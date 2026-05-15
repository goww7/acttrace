"""Application orchestration for the ActTrace endpoints.

Wraps the deterministic classification engine and notice generator, persists
results, and writes audit events. Endpoint handlers and MCP tools call this.
"""
from __future__ import annotations

from typing import Optional

from backend.repositories.acttrace_repository import ActTraceRepository
from backend.services import acttrace_constants as C
from backend.services.acttrace_classification_service import (
    classify as run_classification,
)
from backend.services.acttrace_notice_service import (
    generate_notice as run_notice,
)


class ActTraceService:
    def __init__(self, repo: ActTraceRepository) -> None:
        self._repo = repo

    # --- Free diagnostic (stateless, unauthenticated) ----------------------
    def free_diagnostic(self, payload: dict) -> dict:
        result = run_classification(self._facts(payload))
        return {
            "risk_category": result["risk_category"],
            "confidence": result["confidence"],
            "summary": result["summary"],
            "recommended_next_steps": self._next_steps(result["risk_category"]),
            "upgrade_required_for": [
                "evidence_vault", "packet_export", "mcp_tools",
            ],
            "disclaimer": C.DISCLAIMER,
        }

    # --- Authenticated classification --------------------------------------
    def classify_ai_system(
        self,
        payload: dict,
        *,
        owner: Optional[str] = None,
        actor_type: str = "api",
        request_id: Optional[str] = None,
    ) -> dict:
        facts = self._facts(payload)
        result = run_classification(facts)

        ai_system = self._repo.create_ai_system(
            name=(payload.get("name") or payload.get("feature_name")
                  or "Unnamed AI system"),
            feature_name=payload.get("feature_name"),
            description=payload.get("description"),
            attributes=facts,
            organization_id=owner,
        )
        assessment = self._repo.create_risk_assessment(
            ai_system_id=ai_system["id"], result=result)
        self._repo.mark_classified(ai_system["id"])
        self._repo.create_audit_event(
            action="classify_ai_system",
            actor=owner,
            actor_type=actor_type,
            object_type="risk_assessment",
            object_id=assessment["id"],
            request_id=request_id,
            organization_id=owner,
            metadata={"risk_category": result["risk_category"]},
        )

        escalation = (
            C.ESCALATION_WARNING
            if result["risk_category"] in C.ESCALATION_CATEGORIES
            else None
        )
        return {
            **assessment,
            "request_id": request_id,
            "escalation_warning": escalation,
            "disclaimer": C.DISCLAIMER,
        }

    # --- Notice generation -------------------------------------------------
    def generate_notice(
        self,
        payload: dict,
        *,
        owner: Optional[str] = None,
        actor_type: str = "api",
        request_id: Optional[str] = None,
    ) -> dict:
        notice = run_notice(payload)
        notice.setdefault("notice_type", payload.get("notice_type"))
        notice.setdefault("tone", payload.get("tone") or "plain")
        notice.setdefault("language", payload.get("language") or "en")
        notice.setdefault("version", 1)

        stored = self._repo.create_notice(
            ai_system_id=payload.get("ai_system_id"), notice=notice)
        self._repo.create_audit_event(
            action="generate_transparency_notice",
            actor=owner,
            actor_type=actor_type,
            object_type="transparency_notice",
            object_id=stored["id"],
            request_id=request_id,
            organization_id=owner,
            metadata={"notice_type": notice.get("notice_type")},
        )
        return {**stored, "request_id": request_id, "disclaimer": C.DISCLAIMER}

    # --- helpers -----------------------------------------------------------
    @staticmethod
    def _facts(payload: dict) -> dict:
        return {k: v for k, v in payload.items() if v is not None}

    @staticmethod
    def _next_steps(category: str) -> list[str]:
        if category == C.CATEGORY_OUT_OF_SCOPE_FS:
            return [C.FINANCIAL_SCOPE_NOTICE]
        if category in C.ESCALATION_CATEGORIES:
            return [
                "Create an AI system record",
                "Obtain qualified legal review",
                "Store classification evidence",
            ]
        return [
            "Create an AI system record",
            "Generate and approve a transparency notice",
            "Store model-provider and human-review evidence",
        ]
