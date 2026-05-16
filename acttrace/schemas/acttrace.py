"""Pydantic v2 schemas + enums for the ActTrace API."""
from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# --- Enums -----------------------------------------------------------------
class ActTraceRiskCategory(str, Enum):
    prohibited = "prohibited"
    possible_high_risk = "possible_high_risk"
    limited_risk_transparency = "limited_risk_transparency"
    minimal_risk = "minimal_risk"
    unknown = "unknown"
    needs_legal_review = "needs_legal_review"
    out_of_scope_financial_services = "out_of_scope_financial_services"


class ActTraceConfidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ActTraceHumanReviewLevel(str, Enum):
    none = "none"
    optional = "optional"
    required_before_action = "required_before_action"
    required_after_action = "required_after_action"


class ActTraceNoticeType(str, Enum):
    chatbot = "chatbot"
    ai_generated_content = "ai_generated_content"
    support_assist = "support_assist"
    summarization = "summarization"
    synthetic_media = "synthetic_media"
    internal_ai = "internal_ai"
    other = "other"


class ActTraceNoticeTone(str, Enum):
    plain = "plain"
    formal = "formal"
    developer_docs = "developer_docs"
    policy = "policy"
    ui_microcopy = "ui_microcopy"


class ActTraceActorType(str, Enum):
    user = "user"
    api = "api"
    mcp = "mcp"
    system = "system"


# --- Free diagnostic (unauthenticated) ------------------------------------
class ActTraceDiagnosticRequest(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    feature_name: Optional[str] = None
    description: Optional[str] = None
    user_facing: Optional[bool] = None
    eu_available: Optional[bool] = None
    model_provider: Optional[str] = None
    use_case: Optional[str] = None
    human_review_level: Optional[ActTraceHumanReviewLevel] = None


class ActTraceDiagnosticResponse(BaseModel):
    risk_category: ActTraceRiskCategory
    confidence: ActTraceConfidence
    summary: str
    recommended_next_steps: List[str]
    upgrade_required_for: List[str]
    disclaimer: str


# --- Classification (authenticated) ---------------------------------------
class ActTraceClassifyRequest(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    feature_name: Optional[str] = None
    description: Optional[str] = None
    use_case: Optional[str] = None
    user_facing: Optional[bool] = None
    eu_available: Optional[bool] = None
    internal_only: Optional[bool] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    human_review_level: Optional[ActTraceHumanReviewLevel] = None
    automated_decision: Optional[bool] = None
    high_risk_domain: Optional[bool] = None
    sensitive_data: Optional[bool] = None
    output_categories: List[str] = Field(default_factory=list)
    financial_override: bool = False


class ActTraceRiskAssessmentRead(BaseModel):
    id: str
    ai_system_id: str
    risk_category: ActTraceRiskCategory
    confidence: ActTraceConfidence
    summary: str
    rationale: str
    triggering_facts: List[str]
    missing_information: List[str]
    obligations: List[str]
    source_refs: List[dict]
    rule_version: str
    status: str
    request_id: Optional[str] = None
    escalation_warning: Optional[str] = None
    disclaimer: str
    created_at: str


# --- Transparency notices --------------------------------------------------
class ActTraceNoticeGenerateRequest(BaseModel):
    ai_system_id: Optional[str] = None
    ai_system_name: str
    feature_name: Optional[str] = None
    notice_type: ActTraceNoticeType
    tone: ActTraceNoticeTone = ActTraceNoticeTone.plain
    language: str = "en"
    output_categories: List[str] = Field(default_factory=list)
    human_review_level: Optional[ActTraceHumanReviewLevel] = None
    risk_category: Optional[ActTraceRiskCategory] = None


class ActTraceNoticeRead(BaseModel):
    id: str
    ai_system_id: Optional[str] = None
    notice_type: ActTraceNoticeType
    tone: ActTraceNoticeTone
    language: str
    body: str
    suggested_placement: str
    caveats: List[str]
    human_review_recommended: bool
    version: int
    status: str
    request_id: Optional[str] = None
    disclaimer: str
    created_at: str


class ActTraceError(BaseModel):
    code: str
    message: str
    detail: Optional[Any] = None
