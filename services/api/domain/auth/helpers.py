"""Auth flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.auth.flows import (
    get_enterprise_flow,
    get_me_flow,
    login_flow,
    logout_flow,
    register_enterprise_flow,
    require_auth_user,
)


def require_auth_identity(*, token: str, sb: Client) -> dict[str, Any]:
    return require_auth_user(token=token, sb=sb)


def register_enterprise(*, body: Any, sb: Client) -> dict[str, Any]:
    return register_enterprise_flow(body=body, sb=sb)


def login(*, body: Any, sb: Client) -> dict[str, Any]:
    return login_flow(body=body, sb=sb)


def get_me(*, token: str, sb: Client) -> dict[str, Any]:
    return get_me_flow(token=token, sb=sb)


def logout(*, token: str, sb: Client) -> dict[str, Any]:
    return logout_flow(token=token, sb=sb)


def get_enterprise(*, enterprise_id: str, sb: Client) -> dict[str, Any]:
    return get_enterprise_flow(enterprise_id=enterprise_id, sb=sb)
