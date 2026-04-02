"""Reporting domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.reporting.helpers import (
    export_report,
    export_report_by_proof_id,
    generate_report,
    get_report,
    list_reports,
)


class ReportingService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def export(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("export_report", export_report, body=body, sb=supabase)

    async def export_by_proof_id(self, *, proof_id: str, format: str, report_type: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "export_report_by_proof_id",
            export_report_by_proof_id,
            proof_id=proof_id,
            format=format,
            report_type=report_type,
            sb=supabase,
        )

    async def generate(self, *, body: Any, background_tasks: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "generate_report",
            generate_report,
            body=body,
            background_tasks=background_tasks,
            sb=supabase,
        )

    async def list(self, *, project_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("list_reports", list_reports, project_id=project_id, sb=supabase)

    async def get(self, *, report_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_report", get_report, report_id=report_id, sb=supabase)
