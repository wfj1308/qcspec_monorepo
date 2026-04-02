"""GitPeg autoreg domain facade."""

from __future__ import annotations

from typing import Any

from services.api.core.base import BaseService
from services.api.domain.autoreg.flows import AutoRegisterProjectRequest
from services.api.domain.autoreg.helpers import autoreg_project, autoreg_projects


class AutoregService(BaseService):
    async def autoreg_project(self, *, req: AutoRegisterProjectRequest) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("autoreg_project", autoreg_project, req=req, sb=supabase)

    async def autoreg_projects(self, *, limit: int) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("autoreg_projects", autoreg_projects, limit=limit, sb=supabase)
