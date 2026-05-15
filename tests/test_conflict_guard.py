"""Tests for the financial-services conflict guard (Step 1 of precedence).

Covers BLUEPRINT acceptance fixtures 5 and 6, the financial_override bypass,
and individual financial keywords each triggering out-of-scope.
"""
import pytest

from backend.services.acttrace_classification_service import classify


# --- Fixture 5: portfolio recommender --------------------------------------
def test_fixture_5_portfolio_recommender_out_of_scope():
    facts = {
        "feature_name": "portfolio recommender",
        "description": "Provides investment advice on a client portfolio.",
    }
    result = classify(facts)
    assert result["risk_category"] == "out_of_scope_financial_services"
    assert result["confidence"] == "high"
    assert result["triggering_facts"]


# --- Fixture 6: credit scoring assistant -----------------------------------
def test_fixture_6_credit_scoring_out_of_scope():
    facts = {
        "feature_name": "credit scoring assistant",
        "description": "Assesses the creditworthiness of loan applicants.",
    }
    result = classify(facts)
    assert result["risk_category"] == "out_of_scope_financial_services"
    assert result["confidence"] == "high"
    assert result["triggering_facts"]


# --- financial_override bypasses the conflict guard ------------------------
def test_financial_override_bypasses_conflict_guard():
    """A financial-keyword input with financial_override=True should NOT be
    classified out-of-scope; it falls through to the other precedence rules."""
    facts = {
        "feature_name": "internal banking dashboard summarizer",
        "description": "Summarizes internal reports for staff only.",
        "internal_only": True,
        "user_facing": False,
        "automated_decision": False,
        "financial_override": True,
    }
    result = classify(facts)
    assert result["risk_category"] != "out_of_scope_financial_services"
    # 'banking' present but overridden -> minimal_risk via Step 6.
    assert result["risk_category"] == "minimal_risk"


def test_financial_override_allows_high_risk_classification():
    """Override lets a financial-keyword input still hit a later rule."""
    facts = {
        "feature_name": "bank HR CV screener",
        "description": "Screens candidates during hiring at a bank.",
        "financial_override": True,
    }
    result = classify(facts)
    assert result["risk_category"] == "possible_high_risk"


# --- Individual financial keywords each trigger out-of-scope ---------------
@pytest.mark.parametrize(
    "keyword",
    [
        "bank",
        "trading",
        "hedge fund",
        "mifid",
        "asset management",
        "credit scoring",
    ],
)
def test_individual_financial_keyword_triggers_out_of_scope(keyword):
    facts = {
        "feature_name": "some feature",
        "description": f"This feature involves {keyword} operations.",
    }
    result = classify(facts)
    assert result["risk_category"] == "out_of_scope_financial_services"
    assert result["confidence"] == "high"
    assert keyword in result["triggering_facts"]


def test_conflict_guard_takes_precedence_over_high_risk():
    """Conflict guard (Step 1) wins even when high-risk keywords also match."""
    facts = {
        "feature_name": "bank hiring tool",
        "description": "Recruitment screening for a private bank.",
    }
    result = classify(facts)
    assert result["risk_category"] == "out_of_scope_financial_services"
