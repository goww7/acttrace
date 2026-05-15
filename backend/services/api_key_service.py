"""Business logic for ActTrace API keys: token costing + quota enforcement.

Adapted from FinanceData2's ``ApiKeyService`` and trimmed for the MVP — no
billing periods, no email side effects, no Stripe. Token costs are matched
against the request path by longest-prefix wins.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from backend.repositories.api_key_repository import ApiKeyRepository

logger = logging.getLogger("acttrace")


class ApiKeyService:
    """Validates keys, prices requests in tokens, and enforces quotas."""

    # (path_prefix, token_cost). Matched longest-prefix-wins; the default for
    # an unmatched /api/* path is 1 token.
    TOKEN_COSTS: List[Tuple[str, int]] = [
        ("/api/acttrace/diagnostics/free", 0),
        ("/api/acttrace/classify", 15),
        ("/api/acttrace/notices", 10),
        ("/api/keys", 0),
        ("/api/health", 0),
    ]

    DEFAULT_TOKEN_COST: int = 1

    def __init__(self, repo: ApiKeyRepository):
        self._repo = repo

    # ------------------------------------------------------------------
    # Costing
    # ------------------------------------------------------------------
    def get_token_cost(self, endpoint: str, method: str = "POST") -> int:
        """Return the token cost for ``endpoint`` via longest-prefix match.

        ``method`` is accepted for interface symmetry with the route table
        but the ActTrace MVP prices purely on path.
        """
        path = endpoint or ""
        best_cost = self.DEFAULT_TOKEN_COST
        best_len = -1
        for prefix, cost in self.TOKEN_COSTS:
            if path.startswith(prefix) and len(prefix) > best_len:
                best_cost = cost
                best_len = len(prefix)
        return best_cost

    # ------------------------------------------------------------------
    # Quota enforcement
    # ------------------------------------------------------------------
    def check_and_increment(
        self, api_key: str, endpoint: str = "", method: str = "POST"
    ) -> Dict[str, Any]:
        """Validate the key, price the request, enforce quota, charge tokens.

        Raises ``ValueError`` with a machine code on failure:
          - ``INVALID_API_KEY``    — key not found
          - ``API_KEY_DEACTIVATED`` — key found but inactive
          - ``QUOTA_EXCEEDED``     — free plan would exceed its hard cap

        Paid plans (starter/pro/enterprise) are allowed to run into overage.
        On success returns a usage summary dict.
        """
        key_info = self._repo.get_by_key(api_key)
        if not key_info:
            raise ValueError("INVALID_API_KEY")
        if not key_info.get("is_active"):
            raise ValueError("API_KEY_DEACTIVATED")

        plan = key_info.get("plan", "free")
        tokens_used = int(key_info.get("tokens_used", 0))
        tokens_limit = int(key_info.get("tokens_limit", 0))
        cost = self.get_token_cost(endpoint, method) if endpoint else 0

        projected = tokens_used + cost
        is_overage = False
        if projected > tokens_limit:
            if plan == "free":
                # Free tier is a hard wall.
                raise ValueError("QUOTA_EXCEEDED")
            # Paid plans keep working past the limit.
            is_overage = True

        if cost > 0:
            self._repo.increment_token_usage(api_key, cost)

        new_used = tokens_used + cost
        return {
            "plan": plan,
            "tokens_charged": cost,
            "tokens_used": new_used,
            "tokens_remaining": max(0, tokens_limit - new_used),
            "tokens_limit": tokens_limit,
            "is_overage": is_overage,
        }

    # ------------------------------------------------------------------
    # Usage logging
    # ------------------------------------------------------------------
    def log_request(self, **kw: Any) -> None:
        """Delegate a usage-log write to the repository (best-effort)."""
        try:
            self._repo.log_usage(**kw)
        except Exception:
            logger.warning("acttrace_usage_log_failed", exc_info=True)
