"""Tests for the deterministic classification engine.

Covers BLUEPRINT acceptance fixtures 1, 2, 3, 4 and 7, plus confidence-value
checks and structural assertions on the classified result.
"""
from backend.services.acttrace_classification_service import classify
from backend.services.acttrace_constants import RULE_VERSION, SOURCE_REFS


# --- Fixture 1: limited_risk_transparency ----------------------------------
def test_fixture_1_limited_risk_transparency():
    facts = {
        "feature_name": "customer support assistant",
        "use_case": "support_assist",
        "user_facing": True,
        "model_provider": "OpenAI",
        "description": "An AI assistant that helps support agents draft "
        "replies to customer tickets.",
        "human_review_level": "required_before_action",
    }
    result = classify(facts)
    assert result["risk_category"] == "limited_risk_transparency"
    assert result["confidence"] == "medium"
    assert result["triggering_facts"]


# --- Fixture 2: minimal_risk -----------------------------------------------
def test_fixture_2_minimal_risk():
    facts = {
        "feature_name": "internal document summarizer",
        "internal_only": True,
        "user_facing": False,
        "automated_decision": False,
        "description": "Summarizes internal engineering documents for staff.",
    }
    result = classify(facts)
    assert result["risk_category"] == "minimal_risk"
    assert result["confidence"] == "medium"


# --- Fixture 3: possible_high_risk (HR CV screener) ------------------------
def test_fixture_3_possible_high_risk_hiring():
    facts = {
        "feature_name": "HR CV screener",
        "description": "Ranks job applicants during hiring and recruitment.",
    }
    result = classify(facts)
    assert result["risk_category"] == "possible_high_risk"
    assert result["confidence"] == "medium"


# --- Fixture 4: possible_high_risk (exam scorer) ---------------------------
def test_fixture_4_possible_high_risk_exam():
    facts = {
        "feature_name": "exam scorer",
        "description": "Performs automated student assessment of exams.",
    }
    result = classify(facts)
    assert result["risk_category"] == "possible_high_risk"
    assert result["confidence"] == "medium"


# --- Fixture 7: unknown (missing model_provider) ---------------------------
def test_fixture_7_unknown_missing_model_provider():
    facts = {
        "feature_name": "chatbot",
        "user_facing": True,
        "description": "A general-purpose user-facing chatbot.",
    }
    result = classify(facts)
    assert result["risk_category"] == "unknown"
    assert result["confidence"] == "low"


def test_fixture_7_populates_missing_information():
    facts = {
        "feature_name": "chatbot",
        "user_facing": True,
        "description": "A general-purpose user-facing chatbot.",
    }
    result = classify(facts)
    assert result["missing_information"]
    assert "model_provider" in result["missing_information"]


def test_missing_description_populates_missing_information():
    facts = {"feature_name": "some tool"}
    result = classify(facts)
    assert result["risk_category"] == "unknown"
    assert result["confidence"] == "low"
    assert "description" in result["missing_information"]


# --- Confidence values per precedence rule ---------------------------------
def test_confidence_high_for_prohibited():
    facts = {
        "feature_name": "scoring engine",
        "description": "Builds a social scoring system for citizens.",
    }
    result = classify(facts)
    assert result["risk_category"] == "prohibited"
    assert result["confidence"] == "high"


def test_confidence_medium_for_high_risk_domain_flag():
    facts = {
        "feature_name": "generic tool",
        "description": "A tool with no risk keywords.",
        "high_risk_domain": True,
    }
    result = classify(facts)
    assert result["risk_category"] == "possible_high_risk"
    assert result["confidence"] == "medium"
    assert "high_risk_domain" in result["triggering_facts"]


def test_confidence_low_for_unknown_fallback():
    facts = {
        "feature_name": "mystery feature",
        "description": "A feature that matches no rule and is not internal.",
    }
    result = classify(facts)
    assert result["risk_category"] == "unknown"
    assert result["confidence"] == "low"


# --- Structural assertions on a classified result --------------------------
def test_classified_result_has_non_empty_metadata():
    facts = {
        "feature_name": "HR CV screener",
        "description": "Ranks job applicants during hiring.",
    }
    result = classify(facts)
    assert result["source_refs"]
    assert result["source_refs"] == SOURCE_REFS
    assert result["obligations"]
    assert result["rule_version"]
    assert result["rule_version"] == RULE_VERSION


def test_result_has_all_contract_keys():
    result = classify({"feature_name": "exam scorer",
                        "description": "automated student assessment"})
    for key in (
        "risk_category", "confidence", "summary", "rationale",
        "triggering_facts", "missing_information", "obligations",
        "source_refs", "rule_version",
    ):
        assert key in result
    assert isinstance(result["summary"], str) and result["summary"]
    assert isinstance(result["rationale"], str) and result["rationale"]
