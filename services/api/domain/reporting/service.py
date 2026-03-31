"""Reporting domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.reports_flow_service import export_report_flow, generate_report_flow, list_reports_flow


class ReportingService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def generate(self, *, body: Any) -> Any:
        return await self.run_guarded("generate_report", generate_report_flow, body=body, sb=self.require_supabase())

    async def export(self, *, body: Any) -> Any:
        return await self.run_guarded("export_report", export_report_flow, body=body, sb=self.require_supabase())

    async def list(self, *, project_id: str) -> Any:
        return await self.run_guarded("list_reports", list_reports_flow, project_id=project_id, sb=self.require_supabase())
