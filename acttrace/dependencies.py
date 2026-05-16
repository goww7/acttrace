"""Lightweight singleton dependency container for the ActTrace API.

Mirrors FinanceData2's container idea without the full AppContainer machinery —
the MVP only needs four lazily-built singletons.
"""
from __future__ import annotations

from functools import lru_cache

from acttrace.config import get_settings
from acttrace.repositories.acttrace_repository import ActTraceRepository
from acttrace.repositories.api_key_repository import ApiKeyRepository
from acttrace.services.acttrace_service import ActTraceService
from acttrace.services.api_key_service import ApiKeyService


@lru_cache(maxsize=1)
def get_acttrace_repository() -> ActTraceRepository:
    return ActTraceRepository(get_settings().acttrace_db_path)


@lru_cache(maxsize=1)
def get_api_key_repository() -> ApiKeyRepository:
    return ApiKeyRepository(get_settings().acttrace_db_path)


@lru_cache(maxsize=1)
def get_api_key_service() -> ApiKeyService:
    return ApiKeyService(get_api_key_repository())


@lru_cache(maxsize=1)
def get_acttrace_service() -> ActTraceService:
    return ActTraceService(get_acttrace_repository())
