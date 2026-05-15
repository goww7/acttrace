"""Runtime configuration for the ActTrace API.

Isolated from FinanceData2 — its own env vars, its own SQLite file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


@dataclass(frozen=True)
class Settings:
    acttrace_db_path: Path
    api_key_auth_enabled: bool


def get_settings() -> Settings:
    db_path = os.environ.get(
        "ACTTRACE_DB_PATH", str(PROJECT_ROOT / "acttrace.sqlite3")
    )
    return Settings(
        acttrace_db_path=Path(db_path),
        api_key_auth_enabled=_flag("ACTTRACE_API_KEY_AUTH", True),
    )
