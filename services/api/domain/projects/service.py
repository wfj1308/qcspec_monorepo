"""Projects domain facade."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.projects.helpers import (
    complete_project_gitpeg_registration,
    create_project,
    delete_project,
    export_projects_csv,
    get_project,
    gitpeg_registrar_webhook,
    list_activity,
    list_projects,
    sync_project_autoreg,
    update_project,
)


class ProjectsService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def list_projects(self, *, enterprise_id: str, status: str | None, project_type: str | None) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "list_projects",
            list_projects,
            enterprise_id=enterprise_id,
            status=status,
            project_type=project_type,
            sb=supabase,
        )

    async def list_activity(self, *, enterprise_id: str, limit: int) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("list_activity", list_activity, enterprise_id=enterprise_id, limit=limit, sb=supabase)

    async def export_projects_csv(
        self,
        *,
        enterprise_id: str,
        status: str | None,
        project_type: str | None,
    ) -> StreamingResponse:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "export_projects_csv",
            export_projects_csv,
            enterprise_id=enterprise_id,
            status=status,
            project_type=project_type,
            sb=supabase,
        )

    async def create_project(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("create_project", create_project, body=body, sb=supabase)

    async def sync_project_autoreg(self, *, project_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("sync_project_autoreg", sync_project_autoreg, project_id=project_id, body=body, sb=supabase)

    async def complete_project_gitpeg_registration(self, *, project_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "complete_project_gitpeg_registration",
            complete_project_gitpeg_registration,
            project_id=project_id,
            body=body,
            sb=supabase,
        )

    async def gitpeg_registrar_webhook(self, *, request: Request) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("gitpeg_registrar_webhook", gitpeg_registrar_webhook, request=request, sb=supabase)

    async def get_project(self, *, project_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_project", get_project, project_id=project_id, sb=supabase)

    async def update_project(self, *, project_id: str, updates: dict[str, Any]) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("update_project", update_project, project_id=project_id, updates=updates, sb=supabase)

    async def delete_project(self, *, project_id: str, enterprise_id: str | None) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "delete_project",
            delete_project,
            project_id=project_id,
            enterprise_id=enterprise_id,
            sb=supabase,
        )
