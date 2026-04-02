"""Auth domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.auth.helpers import (
    get_enterprise,
    get_me,
    login,
    logout,
    register_enterprise,
    require_auth_identity,
)


class AuthService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def require_auth_identity(self, *, token: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("require_auth_identity", require_auth_identity, token=token, sb=supabase)

    async def register_enterprise(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("register_enterprise", register_enterprise, body=body, sb=supabase)

    async def login(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("login", login, body=body, sb=supabase)

    async def get_me(self, *, token: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_me", get_me, token=token, sb=supabase)

    async def logout(self, *, token: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("logout", logout, token=token, sb=supabase)

    async def get_enterprise(self, *, enterprise_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_enterprise", get_enterprise, enterprise_id=enterprise_id, sb=supabase)
