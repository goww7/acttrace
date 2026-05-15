"""Deterministic EU AI Act risk-classification engine for ActTrace.

Pure Python. No FastAPI, no DB, no network, no LLM. Implements the 7-step
decision precedence from BLUEPRINT.md ("Classification engine contract").
All keyword lists, obligations, source refs and string constants are imported
from ``acttrace_constants`` — none are redefined here.
"""
from __future__ import annotations

from backend.services.acttrace_constants import (
    CATEGORY_LIMITED_RISK,
    CATEGORY_MINIMAL_RISK,
    CATEGORY_OUT_OF_SCOPE_FS,
    CATEGORY_POSSIBLE_HIGH_RISK,
    CATEGORY_PROHIBITED,
    CATEGORY_UNKNOWN,
    CONFLICT_GUARD_KEYWORDS,
    HIGH_RISK_KEYWORDS,
    OBLIGATIONS,
    PROHIBITED_KEYWORDS,
    RULE_VERSION,
    SOURCE_REFS,
    TRANSPARENCY_KEYWORDS,
)

# Fields concatenated (lowercased) to form the keyword-match haystack.
_HAYSTACK_FIELDS = (
    "industry",
    "feature_name",
    "name",
    "description",
    "use_case",
    "company_name",
)


def _build_haystack(facts: dict) -> str:
    """Lowercase concatenation of the haystack fields, space-separated."""
    parts = []
    for field in _HAYSTACK_FIELDS:
        value = facts.get(field)
        if value:
            parts.append(str(value))
    return " ".join(parts).lower()


def _matched_keywords(haystack: str, keywords) -> list[str]:
    """All keywords whose (substring) form appears in the haystack."""
    return [kw for kw in keywords if kw in haystack]


def _result(
    risk_category: str,
    confidence: str,
    summary: str,
    rationale: str,
    triggering_facts: list[str],
    missing_information: list[str],
) -> dict:
    """Assemble the contract return dict for a verdict."""
    return {
        "risk_category": risk_category,
        "confidence": confidence,
        "summary": summary,
        "rationale": rationale,
        "triggering_facts": triggering_facts,
        "missing_information": missing_information,
        "obligations": OBLIGATIONS[risk_category],
        "source_refs": SOURCE_REFS,
        "rule_version": RULE_VERSION,
    }


def classify(facts: dict) -> dict:
    """Classify an AI use case under the EU AI Act.

    Applies the 7-step decision precedence (first match wins). ``facts`` keys
    are all optional; see BLUEPRINT.md for the full schema.
    """
    facts = facts or {}
    haystack = _build_haystack(facts)

    # --- Step 1: Conflict guard (financial services out of scope) ----------
    if facts.get("financial_override") is not True:
        fs_hits = _matched_keywords(haystack, CONFLICT_GUARD_KEYWORDS)
        if fs_hits:
            return _result(
                CATEGORY_OUT_OF_SCOPE_FS,
                "high",
                "This appears to be a financial-services use case, which is "
                "outside ActTrace's supported scope.",
                "Conflict guard fired: financial-services keyword(s) "
                f"{fs_hits} were detected in the use-case description. "
                "ActTrace is scoped for non-financial SaaS and technology "
                "companies, so this use case is classified as out of scope.",
                fs_hits,
                [],
            )

    # --- Step 2: Prohibited (Article 5) ------------------------------------
    prohibited_hits = _matched_keywords(haystack, PROHIBITED_KEYWORDS)
    if prohibited_hits:
        return _result(
            CATEGORY_PROHIBITED,
            "high",
            "This use case matches an AI practice that may be prohibited "
            "under Article 5 of the EU AI Act.",
            "Prohibited-practice rule fired: keyword(s) "
            f"{prohibited_hits} were detected in the use-case description, "
            "which corresponds to a practice that may be banned under "
            "Article 5. Do not deploy pending qualified legal review.",
            prohibited_hits,
            [],
        )

    # --- Step 3: High-risk (Annex III) -------------------------------------
    high_risk_hits = _matched_keywords(haystack, HIGH_RISK_KEYWORDS)
    high_risk_domain = facts.get("high_risk_domain") is True
    if high_risk_hits or high_risk_domain:
        triggers = list(high_risk_hits)
        if high_risk_domain:
            triggers.append("high_risk_domain")
        return _result(
            CATEGORY_POSSIBLE_HIGH_RISK,
            "medium",
            "This use case may fall into a high-risk category under Annex III "
            "of the EU AI Act and requires a full high-risk assessment.",
            "High-risk rule fired: "
            + (
                f"keyword(s) {high_risk_hits} were detected in the use-case "
                "description"
                if high_risk_hits
                else ""
            )
            + (" and " if high_risk_hits and high_risk_domain else "")
            + (
                "the high_risk_domain flag was set to True"
                if high_risk_domain
                else ""
            )
            + ". This corresponds to an Annex III high-risk area, so a full "
            "high-risk assessment and qualified legal review are required.",
            triggers,
            [],
        )

    # --- Step 4: Missing info ----------------------------------------------
    missing_information: list[str] = []
    if not (facts.get("description") or "").strip():
        missing_information.append("description")
    if facts.get("user_facing") is True and not (
        facts.get("model_provider") or ""
    ).strip():
        missing_information.append("model_provider")
    if missing_information:
        return _result(
            CATEGORY_UNKNOWN,
            "low",
            "Not enough information was provided to classify this AI system.",
            "Missing-information rule fired: required fact(s) "
            f"{missing_information} were not supplied. A documented "
            "classification cannot be produced until they are provided.",
            [],
            missing_information,
        )

    # --- Step 5: Transparency (Article 50) ---------------------------------
    if facts.get("user_facing") is True:
        transparency_hits = _matched_keywords(haystack, TRANSPARENCY_KEYWORDS)
        if transparency_hits:
            return _result(
                CATEGORY_LIMITED_RISK,
                "medium",
                "This user-facing AI feature carries limited-risk "
                "transparency obligations under Article 50 of the EU AI Act.",
                "Transparency rule fired: the feature is user-facing and "
                f"keyword(s) {transparency_hits} were detected in the "
                "use-case description. Article 50 requires informing natural "
                "persons that they are interacting with an AI system.",
                transparency_hits,
                [],
            )

    # --- Step 6: Minimal risk ----------------------------------------------
    if (
        facts.get("internal_only") is True
        and facts.get("user_facing") is not True
        and facts.get("automated_decision") is not True
        and facts.get("high_risk_domain") is not True
        and facts.get("sensitive_data") is not True
    ):
        return _result(
            CATEGORY_MINIMAL_RISK,
            "medium",
            "This use case appears to be minimal risk with no mandatory EU "
            "AI Act obligations identified.",
            "Minimal-risk rule fired: the system is internal-only, not "
            "user-facing, makes no automated decisions, is not in a "
            "high-risk domain, and does not process sensitive data. No "
            "mandatory AI Act obligations were identified.",
            ["internal_only"],
            [],
        )

    # --- Step 7: Fallback --------------------------------------------------
    return _result(
        CATEGORY_UNKNOWN,
        "low",
        "This use case could not be matched to a specific EU AI Act risk "
        "category from the facts provided.",
        "No classification rule matched: the use case did not trigger the "
        "conflict guard, prohibited, high-risk, transparency, or minimal-risk "
        "rules, and no required facts were missing. Additional detail is "
        "needed to produce a documented classification.",
        [],
        [],
    )
