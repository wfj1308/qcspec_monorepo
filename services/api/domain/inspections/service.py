"""Inspection domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.inspections.helpers import (
    create_inspection,
    delete_inspection,
    list_inspections,
    project_stats,
)


class InspectionsService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def list_inspections(
        self,
        *,
        project_id: str,
        result: str | None,
        kind: str | None,
        limit: int,
        offset: int,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "list_inspections",
            list_inspections,
            project_id=project_id,
            result=result,
            kind=kind,
            limit=limit,
            offset=offset,
            sb=supabase,
        )

    async def create_inspection(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("create_inspection", create_inspection, body=body, sb=supabase)

    async def project_stats(self, *, project_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("project_stats", project_stats, project_id=project_id, sb=supabase)

    async def delete_inspection(self, *, inspection_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("delete_inspection", delete_inspection, inspection_id=inspection_id, sb=supabase)
