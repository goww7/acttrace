"""Shared pytest fixtures for the ActTrace test suite.

The HTTP integration tests run against an isolated temp SQLite file so they
never touch a developer's working `acttrace.sqlite3`. The env var is set
before the app is imported so the dependency singletons resolve to it.
"""
from __future__ import annotations

import os
import tempfile

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="acttrace_test_")
os.environ["ACTTRACE_DB_PATH"] = os.path.join(_TMP_DIR, "acttrace.sqlite3")
os.environ.setdefault("ACTTRACE_API_KEY_AUTH", "1")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from acttrace.app import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def api_key(client) -> str:
    """A valid free-plan key, minted through the real issuance endpoint."""
    resp = client.post("/api/keys/generate")
    assert resp.status_code == 200, resp.text
    return resp.json()["api_key"]
