"""SQLite-backed API key storage with token-usage tracking.

ActTrace stores everything in one SQLite file (``acttrace.sqlite3``). This
repository owns the ``acttrace_api_keys`` and ``acttrace_api_usage_log``
tables; the classification/notice repository owns its own tables in the same
file. Pattern adapted from FinanceData2's ``SQLiteApiKeyRepository`` but
trimmed for the MVP: no Stripe, no billing periods, no marketing — and a
single ``acttrace_`` table prefix.

Keys are hashed with bcrypt at rest. A clear ``key_prefix`` (first ~10 chars
of the raw key) is stored alongside so a presented key can be located without
scanning every hash.
"""

from __future__ import annotations

import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional


class ApiKeyRepository:
    """CRUD repository for ActTrace API keys and per-request usage logs."""

    # Token allowance per plan. Free is a hard cap; paid plans permit overage
    # (the service layer enforces that distinction).
    TOKEN_LIMITS: Dict[str, int] = {
        "free": 200,
        "starter": 2_500,
        "pro": 15_000,
        "enterprise": 1_000_000,
    }

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._lock = Lock()
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Connection / schema
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS acttrace_api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key TEXT NOT NULL UNIQUE,
                    key_prefix TEXT NOT NULL,
                    plan TEXT NOT NULL DEFAULT 'free',
                    tokens_used INTEGER NOT NULL DEFAULT 0,
                    tokens_limit INTEGER NOT NULL DEFAULT 200,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_acttrace_api_keys_prefix "
                "ON acttrace_api_keys(key_prefix)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS acttrace_api_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key_id INTEGER,
                    key_prefix TEXT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER,
                    tokens_charged INTEGER NOT NULL DEFAULT 0,
                    is_overage INTEGER NOT NULL DEFAULT 0,
                    request_id TEXT,
                    latency_ms INTEGER,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_acttrace_usage_key "
                "ON acttrace_api_usage_log(api_key_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_acttrace_usage_ts "
                "ON acttrace_api_usage_log(timestamp DESC)"
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_key() -> str:
        """Return a fresh raw key shaped ``act_<32 hex chars>``."""
        return f"act_{secrets.token_hex(16)}"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "key_prefix": row["key_prefix"],
            "plan": row["plan"],
            "is_active": bool(row["is_active"]),
            "tokens_used": int(row["tokens_used"]),
            "tokens_limit": int(row["tokens_limit"]),
        }

    def _resolve_row(
        self, conn: sqlite3.Connection, raw_key: str
    ) -> Optional[sqlite3.Row]:
        """Find a key row by prefix lookup + bcrypt verify.

        Imported lazily so the module loads even when bcrypt is absent at
        import time (e.g. during ``py_compile``); a missing dependency only
        surfaces when a key is actually resolved.
        """
        import bcrypt

        if not raw_key:
            return None
        prefix = raw_key[:10]
        rows = conn.execute(
            "SELECT * FROM acttrace_api_keys WHERE key_prefix = ?",
            (prefix,),
        ).fetchall()
        for row in rows:
            try:
                if bcrypt.checkpw(raw_key.encode(), row["api_key"].encode()):
                    return row
            except ValueError:
                # Stored value is not a valid bcrypt hash — skip it.
                continue
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_key(self, plan: str = "free") -> Dict[str, Any]:
        """Mint a new key. Returns the plaintext key — shown only once."""
        import bcrypt

        raw_key = self._generate_key()
        key_prefix = raw_key[:10]
        api_key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
        token_limit = self.TOKEN_LIMITS.get(plan, self.TOKEN_LIMITS["free"])
        now = self._now()

        with self._lock:
            with closing(self._connect()) as conn:
                cur = conn.execute(
                    """INSERT INTO acttrace_api_keys
                       (api_key, key_prefix, plan, tokens_used, tokens_limit,
                        is_active, created_at, updated_at)
                       VALUES (?, ?, ?, 0, ?, 1, ?, ?)""",
                    (api_key_hash, key_prefix, plan, token_limit, now, now),
                )
                new_id = cur.lastrowid

        return {
            "api_key": raw_key,
            "key_prefix": key_prefix,
            "plan": plan,
            "id": new_id,
        }

    def get_by_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Resolve a presented raw key to its record, or ``None``."""
        with self._lock:
            with closing(self._connect()) as conn:
                row = self._resolve_row(conn, api_key)
                return self._row_to_dict(row) if row else None

    def increment_token_usage(self, api_key: str, tokens: int) -> int:
        """Add ``tokens`` to the key's usage counter. Returns the new total."""
        now = self._now()
        with self._lock:
            with closing(self._connect()) as conn:
                row = self._resolve_row(conn, api_key)
                if not row:
                    return 0
                key_id = row["id"]
                conn.execute(
                    """UPDATE acttrace_api_keys
                       SET tokens_used = tokens_used + ?, updated_at = ?
                       WHERE id = ?""",
                    (int(tokens), now, key_id),
                )
                updated = conn.execute(
                    "SELECT tokens_used FROM acttrace_api_keys WHERE id = ?",
                    (key_id,),
                ).fetchone()
                return int(updated["tokens_used"]) if updated else 0

    def log_usage(self, **kw: Any) -> None:
        """Best-effort insert into ``acttrace_api_usage_log``.

        Accepted keyword args: ``api_key_id``, ``key_prefix``, ``endpoint``,
        ``method``, ``status_code``, ``tokens_charged``, ``is_overage``,
        ``request_id``, ``latency_ms``. Any failure is swallowed — usage
        logging must never break a request.
        """
        try:
            now = self._now()
            with self._lock:
                with closing(self._connect()) as conn:
                    conn.execute(
                        """INSERT INTO acttrace_api_usage_log
                           (api_key_id, key_prefix, endpoint, method,
                            status_code, tokens_charged, is_overage,
                            request_id, latency_ms, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            kw.get("api_key_id"),
                            kw.get("key_prefix"),
                            kw.get("endpoint", ""),
                            kw.get("method", ""),
                            kw.get("status_code"),
                            int(kw.get("tokens_charged", 0) or 0),
                            1 if kw.get("is_overage") else 0,
                            kw.get("request_id"),
                            kw.get("latency_ms"),
                            now,
                        ),
                    )
        except Exception:
            # Usage logging is fire-and-forget — never propagate.
            pass
