"""Team management domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.team.helpers import (
    create_member,
    list_members,
    remove_member,
    update_member,
)


class TeamService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def list_members(self, *, enterprise_id: str, include_inactive: bool) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "list_members",
            list_members,
            enterprise_id=enterprise_id,
            include_inactive=include_inactive,
            sb=supabase,
        )

    async def create_member(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("create_member", create_member, body=body, sb=supabase)

    async def update_member(self, *, user_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "update_member",
            update_member,
            user_id=user_id,
            body=body,
            sb=supabase,
        )

    async def remove_member(self, *, user_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("remove_member", remove_member, user_id=user_id, sb=supabase)
