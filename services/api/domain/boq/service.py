"""BOQ, evidence center, readiness, and merkle facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.boq_audit_engine_service import get_item_sovereign_history, run_boq_audit_engine
from services.api.evidence_center_service import get_all_evidence_for_item
from services.api.domain.boq.helpers import (
    download_evidence_center_zip,
    get_evidence_center_evidence,
    project_readiness_check,
)
from services.api.triprole_engine import get_boq_realtime_status
from services.api.unit_merkle_service import build_unit_merkle_snapshot


class BOQService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def item_sovereign_history(self, *, project_uri: str, subitem_code: str, max_rows: int) -> Any:
        return await self.run_guarded(
            "boq_item_sovereign_history",
            get_item_sovereign_history,
            project_uri=project_uri,
            subitem_code=subitem_code,
            max_rows=max_rows,
            sb=self.require_supabase(),
        )

    async def download_evidence_center(
        self,
        *,
        project_uri: str,
        subitem_code: str,
        proof_id: str | None,
        verify_base_url: str,
    ) -> Any:
        return await self.run_guarded(
            "download_evidence_center",
            download_evidence_center_zip,
            project_uri=project_uri,
            subitem_code=subitem_code,
            proof_id=proof_id,
            verify_base_url=verify_base_url,
            sb=self.require_supabase(),
        )

    async def evidence_center_evidence(
        self,
        *,
        project_uri: str | None,
        subitem_code: str | None,
        boq_item_uri: str | None,
        smu_id: str | None,
    ) -> Any:
        return await self.run_guarded(
            "evidence_center_evidence",
            self._evidence_center_evidence,
            project_uri=project_uri,
            subitem_code=subitem_code,
            boq_item_uri=boq_item_uri,
            smu_id=smu_id,
        )

    async def reconciliation(
        self,
        *,
        project_uri: str,
        subitem_code: str,
        max_rows: int,
        limit_items: int,
    ) -> Any:
        return await self.run_guarded(
            "boq_reconciliation",
            run_boq_audit_engine,
            project_uri=project_uri,
            subitem_code=subitem_code,
            max_rows=max_rows,
            limit_items=limit_items,
            sb=self.require_supabase(),
        )

    async def realtime_status(self, *, project_uri: str) -> Any:
        return await self.run_guarded(
            "boq_realtime_status",
            get_boq_realtime_status,
            project_uri=project_uri,
            sb=self.require_supabase(),
        )

    async def readiness_check(self, *, project_uri: str) -> Any:
        return await self.run_guarded(
            "project_readiness_check",
            project_readiness_check,
            project_uri=project_uri,
            sb=self.require_supabase(),
        )

    async def unit_merkle_root(
        self,
        *,
        project_uri: str,
        unit_code: str,
        proof_id: str,
        max_rows: int,
    ) -> Any:
        return await self.run_guarded(
            "unit_merkle_root",
            build_unit_merkle_snapshot,
            project_uri=project_uri,
            unit_code=unit_code,
            proof_id=proof_id,
            max_rows=max_rows,
            sb=self.require_supabase(),
        )

    def _evidence_center_evidence(
        self,
        *,
        project_uri: str | None,
        subitem_code: str | None,
        boq_item_uri: str | None,
        smu_id: str | None,
    ) -> dict[str, Any]:
        if boq_item_uri and not subitem_code and not smu_id:
            return get_all_evidence_for_item(sb=self.require_supabase(), boq_item_uri=boq_item_uri)
        return get_evidence_center_evidence(
            project_uri=project_uri,
            subitem_code=subitem_code,
            boq_item_uri=boq_item_uri,
            smu_id=smu_id,
            sb=self.require_supabase(),
        )
