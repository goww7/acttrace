"""Tests for the Article 50 transparency-notice generator.

Covers the BLUEPRINT "Notice generator contract": a notice per notice_type,
non-empty AI-disclosing body, non-empty caveats, tone variation changes the
body, and the human_review_recommended rule.
"""
from __future__ import annotations

import pytest

from acttrace.services.acttrace_notice_service import (
    NOTICE_TYPES,
    generate_notice,
)


def _base_params(**overrides) -> dict:
    params = {
        "ai_system_name": "Acme Assistant",
        "feature_name": "Helpdesk Copilot",
        "notice_type": "chatbot",
        "tone": "plain",
        "language": "en",
        "output_categories": ["chat replies"],
        "human_review_level": "recommended",
    }
    params.update(overrides)
    return params


def test_all_seven_notice_types_supported() -> None:
    """Exactly the 7 contract notice types are available."""
    assert set(NOTICE_TYPES) == {
        "chatbot",
        "ai_generated_content",
        "support_assist",
        "summarization",
        "synthetic_media",
        "internal_ai",
        "other",
    }


def _discloses_ai(body: str) -> bool:
    lowered = body.lower()
    return "ai" in lowered or "artificial intelligence" in lowered


@pytest.mark.parametrize("notice_type", NOTICE_TYPES)
def test_notice_per_type_has_disclosing_body(notice_type: str) -> None:
    """One notice per notice_type; body non-empty and discloses AI use."""
    notice = generate_notice(_base_params(notice_type=notice_type))

    assert isinstance(notice["body"], str)
    assert notice["body"].strip(), f"empty body for {notice_type}"
    assert _discloses_ai(notice["body"]), (
        f"body for {notice_type} does not disclose AI use"
    )
    assert notice["notice_type"] == notice_type


@pytest.mark.parametrize("notice_type", NOTICE_TYPES)
def test_caveats_non_empty_and_reference_disclaimer(notice_type: str) -> None:
    """Caveats are always present and flag this is not legal advice."""
    notice = generate_notice(_base_params(notice_type=notice_type))

    caveats = notice["caveats"]
    assert isinstance(caveats, list)
    assert caveats, f"empty caveats for {notice_type}"
    joined = " ".join(caveats).lower()
    assert "not legal advice" in joined
    assert "drafting support" in joined


def test_body_advises_reviewing_important_output() -> None:
    """The contract requires the body to advise human review of output."""
    for tone in ("plain", "formal", "developer_docs", "policy"):
        body = generate_notice(_base_params(tone=tone))["body"].lower()
        assert "review" in body or "verify" in body or "double-check" in body


def test_tone_variation_changes_body() -> None:
    """Two different tones for the same notice yield different body text."""
    plain = generate_notice(_base_params(tone="plain"))["body"]
    formal = generate_notice(_base_params(tone="formal"))["body"]
    policy = generate_notice(_base_params(tone="policy"))["body"]
    microcopy = generate_notice(_base_params(tone="ui_microcopy"))["body"]

    bodies = {plain, formal, policy, microcopy}
    assert len(bodies) == 4, "tones must produce distinct bodies"
    # ui_microcopy is intended to be the shortest tone.
    assert len(microcopy) < len(policy)


def test_human_review_recommended_rule() -> None:
    """False only when human_review_level == required_before_action."""
    required = generate_notice(
        _base_params(human_review_level="required_before_action")
    )
    assert required["human_review_recommended"] is False

    for level in ("recommended", "optional", "none", None):
        notice = generate_notice(_base_params(human_review_level=level))
        assert notice["human_review_recommended"] is True


def test_echoes_notice_type_tone_language() -> None:
    """The return dict echoes back the request metadata."""
    notice = generate_notice(
        _base_params(notice_type="summarization", tone="formal", language="en")
    )
    assert notice["notice_type"] == "summarization"
    assert notice["tone"] == "formal"
    assert notice["language"] == "en"
    assert isinstance(notice["suggested_placement"], str)
    assert notice["suggested_placement"].strip()


def test_chatbot_plain_matches_quality_bar() -> None:
    """The chatbot/plain reference example weaves in the feature name."""
    notice = generate_notice(
        _base_params(notice_type="chatbot", tone="plain")
    )
    body = notice["body"]
    assert "Helpdesk Copilot" in body
    assert "artificial intelligence" in body.lower()
    assert "review important information" in body.lower()


def test_unknown_type_and_tone_fall_back() -> None:
    """Unsupported notice_type / tone fall back to safe defaults."""
    notice = generate_notice(
        _base_params(notice_type="not_a_type", tone="not_a_tone")
    )
    assert notice["notice_type"] == "other"
    assert notice["tone"] == "plain"
    assert _discloses_ai(notice["body"])
