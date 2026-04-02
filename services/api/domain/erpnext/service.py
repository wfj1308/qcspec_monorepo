"""ERPNext integration domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.erpnext.helpers import (
    check_metering_gate,
    get_metering_requests,
    get_project_basics,
    notify_erpnext,
    probe_erpnext,
)


class ERPNextIntegrationService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def check_metering_gate(
        self,
        *,
        enterprise_id: str,
        stake: str,
        subitem: str,
        result: str,
        project_id: str | None,
        project_code: str | None,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "check_metering_gate",
            check_metering_gate,
            enterprise_id=enterprise_id,
            stake=stake,
            subitem=subitem,
            result=result,
            project_id=project_id,
            project_code=project_code,
            sb=supabase,
        )

    async def get_project_basics(
        self,
        *,
        enterprise_id: str,
        project_code: str | None,
        project_name: str | None,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "get_project_basics",
            get_project_basics,
            enterprise_id=enterprise_id,
            project_code=project_code,
            project_name=project_name,
            sb=supabase,
        )

    async def get_metering_requests(
        self,
        *,
        enterprise_id: str,
        project_code: str | None,
        stake: str | None,
        subitem: str | None,
        status: str | None,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "get_metering_requests",
            get_metering_requests,
            enterprise_id=enterprise_id,
            project_code=project_code,
            stake=stake,
            subitem=subitem,
            status=status,
            sb=supabase,
        )

    async def notify_erpnext(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("notify_erpnext", notify_erpnext, body=body, sb=supabase)

    async def probe_erpnext(
        self,
        *,
        enterprise_id: str,
        sample_project_name: str,
        sample_stake: str,
        sample_subitem: str,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "probe_erpnext",
            probe_erpnext,
            enterprise_id=enterprise_id,
            sample_project_name=sample_project_name,
            sample_stake=sample_stake,
            sample_subitem=sample_subitem,
            sb=supabase,
        )
