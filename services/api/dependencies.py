"""Shared FastAPI dependencies for the slim backend profile."""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from services.api.domain.auth import AuthService
from services.api.domain.auth.runtime.auth import ensure_no_proxy_for_supabase, require_auth_user
from services.api.infrastructure.database import get_supabase_client

security = HTTPBearer()


def get_supabase_for_auth() -> Client:
    ensure_no_proxy_for_supabase()
    return get_supabase_client()


def get_auth_service(sb: Client = Depends(get_supabase_for_auth)) -> AuthService:
    return AuthService(sb=sb)


def require_auth_identity(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sb: Client = Depends(get_supabase_for_auth),
) -> dict:
    return require_auth_user(token=credentials.credentials, sb=sb)

