"""Integration tests for the ActTrace HTTP API.

Covers auth contract, structured errors, token-quota headers, the free
diagnostic, classification, and notice generation end to end.
"""
from __future__ import annotations


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "X-Request-ID" in resp.headers


def test_generate_key(client):
    resp = client.post("/api/keys/generate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api_key"].startswith("act_")
    assert body["plan"] == "free"


def test_free_diagnostic_no_auth(client):
    resp = client.post(
        "/api/acttrace/diagnostics/free",
        json={
            "company_name": "Example SaaS",
            "feature_name": "AI reply assistant",
            "description": "Drafts suggested customer support replies for agents.",
            "user_facing": True,
            "eu_available": True,
            "model_provider": "OpenAI",
            "use_case": "support_assist",
            "human_review_level": "required_before_action",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["risk_category"] == "limited_risk_transparency"
    assert body["confidence"] in ("high", "medium", "low")
    assert body["disclaimer"]
    assert body["recommended_next_steps"]
    assert "X-Request-ID" in resp.headers


def test_classify_requires_key(client):
    resp = client.post(
        "/api/acttrace/classify",
        json={"feature_name": "x", "description": "y"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "API_KEY_REQUIRED"
    assert "message" in body


def test_classify_invalid_key(client):
    resp = client.post(
        "/api/acttrace/classify",
        headers={"X-API-Key": "act_not_a_real_key"},
        json={"feature_name": "x", "description": "y"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_API_KEY"


def test_classify_ok_and_token_headers(client, api_key):
    resp = client.post(
        "/api/acttrace/classify",
        headers={"X-API-Key": api_key},
        json={
            "feature_name": "AI reply assistant",
            "description": "Drafts customer support replies shown to support agents.",
            "use_case": "support_assist",
            "user_facing": True,
            "model_provider": "OpenAI",
            "human_review_level": "required_before_action",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for field in (
        "id", "ai_system_id", "risk_category", "confidence", "summary",
        "rationale", "obligations", "source_refs", "rule_version", "disclaimer",
    ):
        assert field in body and body[field] not in (None, "", []), field
    assert body["risk_category"] == "limited_risk_transparency"
    assert body["request_id"]
    assert resp.headers.get("X-Tokens-Charged") == "15"
    assert "X-Request-ID" in resp.headers
    assert "X-Tokens-Remaining" in resp.headers


def test_classify_financial_out_of_scope(client, api_key):
    resp = client.post(
        "/api/acttrace/classify",
        headers={"X-API-Key": api_key},
        json={
            "feature_name": "portfolio recommender",
            "description": "Recommends an investment portfolio allocation to retail users.",
            "user_facing": True,
            "model_provider": "internal",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["risk_category"] == "out_of_scope_financial_services"
    assert body["escalation_warning"]


def test_classify_high_risk_escalation(client, api_key):
    resp = client.post(
        "/api/acttrace/classify",
        headers={"X-API-Key": api_key},
        json={
            "feature_name": "HR CV screener",
            "description": "Screens job applicants for hiring and recruitment decisions.",
            "user_facing": False,
            "model_provider": "internal",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["risk_category"] == "possible_high_risk"
    assert body["escalation_warning"]


def test_notice_ok(client, api_key):
    resp = client.post(
        "/api/acttrace/notices",
        headers={"X-API-Key": api_key},
        json={
            "ai_system_name": "Support Copilot",
            "feature_name": "AI reply assistant",
            "notice_type": "chatbot",
            "tone": "plain",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["body"]
    assert body["disclaimer"]
    text = body["body"].lower()
    assert "ai" in text or "artificial intelligence" in text
    assert body["caveats"]
    assert resp.headers.get("X-Tokens-Charged") == "10"


def test_notice_requires_key(client):
    resp = client.post(
        "/api/acttrace/notices",
        json={"ai_system_name": "x", "notice_type": "chatbot"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "API_KEY_REQUIRED"
