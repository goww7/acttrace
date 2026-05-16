"""Orchestrator-owned constants — the regulatory jig for ActTrace.

Build agents import from here. Do not redefine these values elsewhere.
"""
from __future__ import annotations

RULE_VERSION = "acttrace-rules-1.0.0"
PROMPT_VERSION = "deterministic-no-llm"

DISCLAIMER = (
    "ActTrace provides operational compliance workflow support, documentation "
    "drafts, and evidence management. It does not provide legal advice, does "
    "not certify compliance, and does not replace review by qualified counsel. "
    "AI Act obligations may vary by product, use case, jurisdiction, and "
    "future regulatory guidance."
)

ESCALATION_WARNING = (
    "This use case may require specialized legal review and may fall outside "
    "the self-serve scope of ActTrace. Do not rely on this output as a final "
    "classification."
)

FINANCIAL_SCOPE_NOTICE = (
    "ActTrace is currently scoped for non-financial SaaS and technology "
    "companies. Financial-services AI governance is outside supported scope."
)

SOURCE_REFS = [
    {
        "title": "European Commission — Regulatory framework for AI",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/"
               "regulatory-framework-ai",
    },
    {
        "title": "EU AI Act — implementation timeline",
        "url": "https://artificialintelligenceact.eu/implementation-timeline/",
    },
]

# --- Risk categories -------------------------------------------------------
CATEGORY_PROHIBITED = "prohibited"
CATEGORY_POSSIBLE_HIGH_RISK = "possible_high_risk"
CATEGORY_LIMITED_RISK = "limited_risk_transparency"
CATEGORY_MINIMAL_RISK = "minimal_risk"
CATEGORY_UNKNOWN = "unknown"
CATEGORY_NEEDS_LEGAL_REVIEW = "needs_legal_review"
CATEGORY_OUT_OF_SCOPE_FS = "out_of_scope_financial_services"

# Categories that must surface ESCALATION_WARNING in API output / packets.
ESCALATION_CATEGORIES = {
    CATEGORY_PROHIBITED,
    CATEGORY_POSSIBLE_HIGH_RISK,
    CATEGORY_NEEDS_LEGAL_REVIEW,
    CATEGORY_OUT_OF_SCOPE_FS,
}

# --- Keyword lists (lowercase; substring match on a normalized haystack) ---
CONFLICT_GUARD_KEYWORDS = [
    "private bank", "investment bank", "bank", "banking", "neobank",
    "wealth management", "asset management", "portfolio", "investment advice",
    "investment research", "investment adviser", "investment advisor",
    "trading", "brokerage", "broker", "hedge fund", "family office",
    "robo-advisor", "robo advisor", "roboadvisor", "liquidity", "market abuse",
    "anti-money", "money laundering", " aml ", " kyc ", "credit scoring",
    "credit score", "creditworthiness", "credit risk", "underwriting",
    "securities", "dora", "mifid", "ucits", "aifmd", "finma", "esma",
]

PROHIBITED_KEYWORDS = [
    "social scoring", "social credit", "subliminal", "predictive policing",
    "manipulative technique", "untargeted scraping of facial",
    "emotion recognition in the workplace",
]

HIGH_RISK_KEYWORDS = [
    "hiring", "recruitment", "recruiting", "cv screening", "resume screening",
    "candidate screening", "candidate ranking", "applicant ranking",
    "promotion decision", "employee evaluation", "worker monitoring",
    "education admission", "student assessment", "exam scoring", "exam grading",
    "essential services", "healthcare triage", "medical diagnosis",
    "biometric identification", "biometric categorization",
    "emotion recognition", "law enforcement", "migration", "asylum",
    "border control", "critical infrastructure",
]

TRANSPARENCY_KEYWORDS = [
    "chatbot", "conversational assistant", "conversational ai",
    "conversational", "support assistant", "support assist", "support_assist",
    "virtual assistant", "ai-generated content", "ai generated content",
    "generated content", "synthetic content", "synthetic media", "deepfake",
    "summarization", "summary", "recommendation", "automated reply",
    "reply drafting", "reply assistant", "ai agent",
]

# --- Obligations per category ---------------------------------------------
OBLIGATIONS = {
    CATEGORY_PROHIBITED: [
        "This practice may be prohibited under Article 5 of the EU AI Act.",
        "Do not deploy this use case pending qualified legal review.",
    ],
    CATEGORY_POSSIBLE_HIGH_RISK: [
        "Conduct a full Annex III high-risk assessment.",
        "Establish a risk management system (Art. 9).",
        "Apply data and data-governance controls (Art. 10).",
        "Maintain technical documentation (Art. 11).",
        "Implement human oversight measures (Art. 14).",
        "Obtain qualified legal review before deployment.",
    ],
    CATEGORY_NEEDS_LEGAL_REVIEW: [
        "Facts are insufficient or borderline — obtain qualified legal review.",
    ],
    CATEGORY_LIMITED_RISK: [
        "Article 50: inform natural persons they are interacting with an AI "
        "system.",
        "Label or disclose AI-generated or AI-assisted content where "
        "applicable.",
        "Provide clear, accessible disclosure at the point of interaction.",
    ],
    CATEGORY_MINIMAL_RISK: [
        "No mandatory AI Act obligations identified for this use case.",
        "Voluntary codes of conduct are encouraged (Art. 95).",
    ],
    CATEGORY_UNKNOWN: [
        "Provide the missing information to obtain a documented "
        "classification.",
    ],
    CATEGORY_OUT_OF_SCOPE_FS: [
        "Financial-services AI governance is outside ActTrace supported scope.",
    ],
}
