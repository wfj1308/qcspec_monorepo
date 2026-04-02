"""Team management flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.team.flows import (
    create_member_flow,
    list_members_flow,
    remove_member_flow,
    update_member_flow,
)


def list_members(*, enterprise_id: str, include_inactive: bool, sb: Client) -> dict[str, Any]:
    return list_members_flow(
        enterprise_id=enterprise_id,
        include_inactive=include_inactive,
        sb=sb,
    )


def create_member(*, body: Any, sb: Client) -> dict[str, Any]:
    return create_member_flow(body=body, sb=sb)


def update_member(*, user_id: str, body: Any, sb: Client) -> dict[str, Any]:
    return update_member_flow(user_id=user_id, body=body, sb=sb)


def remove_member(*, user_id: str, sb: Client) -> dict[str, Any]:
    return remove_member_flow(user_id=user_id, sb=sb)
