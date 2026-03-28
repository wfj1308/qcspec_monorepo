"""
Shared FastAPI dependencies.
"""

from __future__ import annotations

from supabase import Client

from services.api.auth_service import ensure_no_proxy_for_supabase
from services.api.supabase_provider import get_supabase_client


def get_supabase() -> Client:
    return get_supabase_client()


def get_supabase_for_auth() -> Client:
    ensure_no_proxy_for_supabase()
    return get_supabase_client()
