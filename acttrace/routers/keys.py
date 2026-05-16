"""Key issuance + health router for the ActTrace API — /api/keys, /api/health.

Both routes here are on the auth middleware's exemption list: a caller must
be able to mint a first key and probe liveness without already holding one.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from acttrace.dependencies import get_api_key_repository
from acttrace.repositories.api_key_repository import ApiKeyRepository

router = APIRouter(tags=["keys"])


@router.post(
    "/api/keys/generate",
    summary="Generate a free ActTrace API key (no auth)",
)
async def generate_key(
    repo: ApiKeyRepository = Depends(get_api_key_repository),
) -> dict:
    """Issue a fresh free-plan key.

    The plaintext key is returned exactly once — it is bcrypt-hashed at rest
    and cannot be recovered later. Callers must store it now.
    """
    created = repo.create_key(plan="free")
    return {
        "api_key": created["api_key"],
        "key_prefix": created["key_prefix"],
        "plan": created["plan"],
        "note": (
            "Store this API key now — it is shown only once and cannot be "
            "retrieved later. Send it on every request via the X-API-Key header."
        ),
    }


@router.get(
    "/api/health",
    summary="Liveness probe (no auth)",
)
async def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok", "service": "acttrace"}
