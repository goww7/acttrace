"""Example: embed the ActTrace classification engine in your own FastAPI service.

The ActTrace classification engine is pure Python — no separate server, no DB,
no LLM. This example shows how to import it directly, expose your own
/api/compliance/classify endpoint, and validate your AI feature inventory at
startup.

Run (from the acttrace repo root):
    pip install -e .
    pip install fastapi uvicorn
    uvicorn examples.fastapi_app:app --reload

Try it:
    curl http://localhost:8000/health
    curl -s -X POST http://localhost:8000/api/compliance/classify \\
      -H 'content-type: application/json' \\
      -d '{
        "feature_name": "Support chatbot",
        "description": "Answers customer support questions using an LLM.",
        "user_facing": true,
        "model_provider": "OpenAI"
      }'
"""
from __future__ import annotations

import warnings
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from acttrace.services.acttrace_classification_service import classify

_BLOCK_CATEGORIES = {"prohibited", "possible_high_risk"}

# AI features this service ships — validated at startup before accepting traffic.
_OWN_FEATURES = [
    {
        "name": "support-chatbot",
        "feature_name": "Customer support chatbot",
        "description": "Answers customer support questions using an LLM.",
        "user_facing": True,
        "model_provider": "OpenAI",
        "use_case": "chatbot",
    },
    {
        "name": "article-summarizer",
        "feature_name": "Article summarizer",
        "description": "Summarises long articles for internal editorial staff.",
        "user_facing": False,
        "internal_only": True,
        "model_provider": "Anthropic",
        "use_case": "summarization",
    },
]


def _validate_ai_inventory() -> None:
    """Classify every feature in _OWN_FEATURES; warn on any that need review."""
    flagged = []
    for feature in _OWN_FEATURES:
        result = classify(feature)
        if result["risk_category"] in _BLOCK_CATEGORIES:
            flagged.append(f"{feature['name']}: {result['risk_category']}")
    if flagged:
        warnings.warn(
            "ActTrace: AI features that need review before deployment: "
            + ", ".join(flagged)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    _validate_ai_inventory()
    yield


app = FastAPI(title="My SaaS — compliance-aware API", lifespan=lifespan)


class ClassifyRequest(BaseModel):
    feature_name: Optional[str] = None
    description: Optional[str] = None
    user_facing: Optional[bool] = None
    internal_only: Optional[bool] = None
    model_provider: Optional[str] = None
    industry: Optional[str] = None
    use_case: Optional[str] = None
    high_risk_domain: Optional[bool] = None
    automated_decision: Optional[bool] = None
    sensitive_data: Optional[bool] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/compliance/classify")
def classify_endpoint(body: ClassifyRequest) -> dict:
    """EU AI Act risk classification — no auth or token cost required."""
    facts = {k: v for k, v in body.model_dump().items() if v is not None}
    result = classify(facts)
    return {
        "risk_category": result["risk_category"],
        "confidence": result["confidence"],
        "summary": result["summary"],
        "obligations": result["obligations"],
        "rule_version": result["rule_version"],
        "disclaimer": (
            "ActTrace provides operational compliance workflow support. "
            "Not legal advice."
        ),
    }
