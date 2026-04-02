"""
Shared Supabase client provider for API routers.
"""

from __future__ import annotations

from functools import lru_cache
import os
from typing import Iterable

from fastapi import HTTPException
from supabase import Client, create_client


@lru_cache(maxsize=32)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def _first_non_empty_env(names: Iterable[str]) -> str:
    for name in names:
        value = str(os.getenv(str(name)) or "").strip()
        if value:
            return value
    return ""


def get_supabase_client(
    *,
    url_envs: Iterable[str] = ("SUPABASE_URL",),
    key_envs: Iterable[str] = ("SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY"),
    error_detail: str = "Supabase not configured",
) -> Client:
    url = _first_non_empty_env(url_envs)
    key = _first_non_empty_env(key_envs)
    if not url or not key:
        raise HTTPException(500, error_detail)
    return _supabase_client_cached(url, key)
