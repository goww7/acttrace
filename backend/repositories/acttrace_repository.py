"""SQLite repository for ActTrace domain tables.

Convention copied from FinanceData2: no base class, per-call connections via
closing(), WAL mode, inline CREATE TABLE migrations in __init__, a threading
Lock around writes.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


class ActTraceRepository:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._lock = Lock()
        self._ensure_schema()

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
                CREATE TABLE IF NOT EXISTS acttrace_ai_systems (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    name TEXT NOT NULL,
                    feature_name TEXT,
                    description TEXT,
                    attributes_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'active',
                    last_classified_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS acttrace_risk_assessments (
                    id TEXT PRIMARY KEY,
                    ai_system_id TEXT NOT NULL,
                    risk_category TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    summary TEXT,
                    rationale TEXT,
                    triggering_facts_json TEXT NOT NULL DEFAULT '[]',
                    missing_information_json TEXT NOT NULL DEFAULT '[]',
                    obligations_json TEXT NOT NULL DEFAULT '[]',
                    source_refs_json TEXT NOT NULL DEFAULT '[]',
                    rule_version TEXT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS acttrace_transparency_notices (
                    id TEXT PRIMARY KEY,
                    ai_system_id TEXT,
                    notice_type TEXT NOT NULL,
                    tone TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    body TEXT NOT NULL,
                    suggested_placement TEXT,
                    caveats_json TEXT NOT NULL DEFAULT '[]',
                    human_review_recommended INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS acttrace_audit_events (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    actor TEXT,
                    actor_type TEXT,
                    action TEXT NOT NULL,
                    object_type TEXT,
                    object_id TEXT,
                    request_id TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )

    # --- AI systems --------------------------------------------------------
    def create_ai_system(
        self,
        *,
        name: str,
        feature_name: Optional[str] = None,
        description: Optional[str] = None,
        attributes: Optional[dict] = None,
        organization_id: Optional[str] = None,
    ) -> dict:
        row_id = _new_id("ais")
        now = _now()
        with self._lock, closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO acttrace_ai_systems "
                "(id, organization_id, name, feature_name, description, "
                "attributes_json, status, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (row_id, organization_id, name, feature_name, description,
                 json.dumps(attributes or {}), "active", now, now),
            )
        return self.get_ai_system(row_id)  # type: ignore[return-value]

    def get_ai_system(self, ai_system_id: str) -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM acttrace_ai_systems WHERE id=?", (ai_system_id,)
            ).fetchone()
        return self._ai_system_to_dict(row) if row else None

    def mark_classified(self, ai_system_id: str) -> None:
        now = _now()
        with self._lock, closing(self._connect()) as conn:
            conn.execute(
                "UPDATE acttrace_ai_systems SET last_classified_at=?, "
                "updated_at=? WHERE id=?",
                (now, now, ai_system_id),
            )

    # --- Risk assessments --------------------------------------------------
    def create_risk_assessment(self, *, ai_system_id: str, result: dict) -> dict:
        row_id = _new_id("rsk")
        now = _now()
        with self._lock, closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO acttrace_risk_assessments "
                "(id, ai_system_id, risk_category, confidence, summary, "
                "rationale, triggering_facts_json, missing_information_json, "
                "obligations_json, source_refs_json, rule_version, status, "
                "created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (row_id, ai_system_id, result["risk_category"],
                 result["confidence"], result.get("summary", ""),
                 result.get("rationale", ""),
                 json.dumps(result.get("triggering_facts", [])),
                 json.dumps(result.get("missing_information", [])),
                 json.dumps(result.get("obligations", [])),
                 json.dumps(result.get("source_refs", [])),
                 result.get("rule_version", ""), "draft", now),
            )
        return self.get_risk_assessment(row_id)  # type: ignore[return-value]

    def get_risk_assessment(self, assessment_id: str) -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM acttrace_risk_assessments WHERE id=?",
                (assessment_id,),
            ).fetchone()
        return self._assessment_to_dict(row) if row else None

    def get_latest_assessment(self, ai_system_id: str) -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM acttrace_risk_assessments WHERE ai_system_id=? "
                "ORDER BY created_at DESC LIMIT 1",
                (ai_system_id,),
            ).fetchone()
        return self._assessment_to_dict(row) if row else None

    # --- Notices -----------------------------------------------------------
    def create_notice(self, *, ai_system_id: Optional[str], notice: dict) -> dict:
        row_id = _new_id("not")
        now = _now()
        with self._lock, closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO acttrace_transparency_notices "
                "(id, ai_system_id, notice_type, tone, language, body, "
                "suggested_placement, caveats_json, human_review_recommended, "
                "version, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (row_id, ai_system_id, notice["notice_type"], notice["tone"],
                 notice.get("language", "en"), notice["body"],
                 notice.get("suggested_placement", ""),
                 json.dumps(notice.get("caveats", [])),
                 1 if notice.get("human_review_recommended") else 0,
                 int(notice.get("version", 1)), "draft", now),
            )
        return self.get_notice(row_id)  # type: ignore[return-value]

    def get_notice(self, notice_id: str) -> Optional[dict]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM acttrace_transparency_notices WHERE id=?",
                (notice_id,),
            ).fetchone()
        return self._notice_to_dict(row) if row else None

    # --- Audit events ------------------------------------------------------
    def create_audit_event(
        self,
        *,
        action: str,
        actor: Optional[str] = None,
        actor_type: str = "api",
        object_type: Optional[str] = None,
        object_id: Optional[str] = None,
        request_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        row_id = _new_id("aud")
        with self._lock, closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO acttrace_audit_events "
                "(id, organization_id, actor, actor_type, action, object_type, "
                "object_id, request_id, metadata_json, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (row_id, organization_id, actor, actor_type, action,
                 object_type, object_id, request_id,
                 json.dumps(metadata or {}), _now()),
            )
        return row_id

    def list_audit_events(
        self, *, organization_id: Optional[str] = None, limit: int = 100
    ) -> list[dict]:
        query = "SELECT * FROM acttrace_audit_events"
        params: list[Any] = []
        if organization_id:
            query += " WHERE organization_id=?"
            params.append(organization_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with closing(self._connect()) as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # --- Row mappers -------------------------------------------------------
    @staticmethod
    def _ai_system_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["attributes"] = json.loads(d.pop("attributes_json") or "{}")
        return d

    @staticmethod
    def _assessment_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["triggering_facts"] = json.loads(d.pop("triggering_facts_json") or "[]")
        d["missing_information"] = json.loads(
            d.pop("missing_information_json") or "[]")
        d["obligations"] = json.loads(d.pop("obligations_json") or "[]")
        d["source_refs"] = json.loads(d.pop("source_refs_json") or "[]")
        return d

    @staticmethod
    def _notice_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["caveats"] = json.loads(d.pop("caveats_json") or "[]")
        d["human_review_recommended"] = bool(d["human_review_recommended"])
        return d
