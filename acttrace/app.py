"""FastAPI application factory for the ActTrace API.

ActTrace is a developer-facing EU AI Act compliance API: deterministic risk
classification + Article 50 transparency-notice generation. It is fully
isolated from FinanceData2 — its own SQLite file, its own config.

``create_app()`` wires the auth middleware and routers; a module-level
``app`` is exposed so ``uvicorn acttrace.app:app`` works directly.
"""

from __future__ import annotations

from fastapi import FastAPI

from acttrace.config import get_settings
from acttrace.dependencies import get_api_key_service
from acttrace.middleware.api_key_auth import ApiKeyAuthMiddleware
from acttrace.routers import acttrace as acttrace_router
from acttrace.routers import keys as keys_router

API_DESCRIPTION = """\
**ActTrace** is a developer-facing EU AI Act compliance API for non-financial
SaaS and technology companies. It provides:

* **Risk classification** — deterministic, rule-based assessment of an AI
  system's risk category under the EU AI Act.
* **Article 50 transparency notices** — ready-to-use disclosure copy for
  user-facing AI features.

**Not legal advice.** ActTrace does not provide legal advice and does not
certify compliance. Every response carries a disclaimer; treat its output as
engineering guidance to be reviewed with qualified counsel.

## Authentication

Every `/api/*` request (except the free diagnostic, key generation, and
health) must include your key in the `X-API-Key` header. Generate a free key
with `POST /api/keys/generate`.
"""


def create_app() -> FastAPI:
    """Build and configure the ActTrace FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ActTrace API",
        description=API_DESCRIPTION,
        version="0.1.0",
    )

    # API key authentication + token-quota enforcement.
    app.add_middleware(
        ApiKeyAuthMiddleware,
        api_key_service=get_api_key_service(),
        enabled=settings.api_key_auth_enabled,
    )

    # Routers — the acttrace router carries its own /api/acttrace prefix;
    # the keys router declares fully-qualified paths.
    app.include_router(acttrace_router.router)
    app.include_router(keys_router.router)

    return app


app = create_app()
