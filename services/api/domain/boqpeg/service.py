"""BOQPeg application service facade."""

from __future__ import annotations

from typing import Any

from fastapi.concurrency import run_in_threadpool
from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.boqpeg.helpers import (
    boqpeg_bidirectional_closure_flow,
    boqpeg_bind_bridge_items_flow,
    boqpeg_bridge_piles_flow,
    boqpeg_create_bridge_entity_flow,
    boqpeg_create_pile_entity_flow,
    boqpeg_create_bridge_schedule_flow,
    boqpeg_create_process_chain_flow,
    boqpeg_engine_parse_flow,
    boqpeg_phase1_bridge_report_flow,
    boqpeg_product_manifest_flow,
    boqpeg_full_line_piles_flow,
    boqpeg_get_pile_entity_flow,
    boqpeg_full_line_schedule_flow,
    boqpeg_forward_bom_flow,
    boqpeg_get_bridge_schedule_flow,
    boqpeg_get_process_chain_flow,
    boqpeg_import_active_job_flow,
    boqpeg_import_async_flow,
    boqpeg_import_flow,
    boqpeg_import_job_flow,
    boqpeg_match_design_boq_flow,
    boqpeg_normref_logic_scaffold_flow,
    boqpeg_parse_design_manifest_flow,
    boqpeg_progress_payment_flow,
    boqpeg_preview_flow,
    boqpeg_reverse_conservation_flow,
    boqpeg_tab_to_peg_flow,
    boqpeg_sync_bridge_schedule_flow,
    boqpeg_submit_process_table_flow,
    boqpeg_update_pile_state_flow,
    boqpeg_unified_alignment_flow,
)


class BOQPegService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def import_upload(self, **kwargs: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("boqpeg_import_upload", run_in_threadpool, boqpeg_import_flow, sb=supabase, **kwargs)

    async def preview_upload(self, **kwargs: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("boqpeg_preview_upload", run_in_threadpool, boqpeg_preview_flow, sb=supabase, **kwargs)

    async def import_upload_async(self, **kwargs: Any) -> Any:
        return await self.run_guarded("boqpeg_import_upload_async", run_in_threadpool, boqpeg_import_async_flow, **kwargs)

    async def get_import_job(self, *, job_id: str) -> Any:
        return await self.run_guarded("boqpeg_import_job", boqpeg_import_job_flow, job_id=job_id)

    async def get_active_import_job(self, *, project_uri: str) -> Any:
        return await self.run_guarded("boqpeg_import_active_job", boqpeg_import_active_job_flow, project_uri=project_uri)

    async def engine_parse(self, **kwargs: Any) -> Any:
        return await self.run_guarded("boqpeg_engine_parse", run_in_threadpool, boqpeg_engine_parse_flow, **kwargs)

    async def forward_bom(self, *, body: dict[str, Any]) -> Any:
        return await self.run_guarded("boqpeg_forward_bom", boqpeg_forward_bom_flow, body=body)

    async def reverse_conservation(self, *, body: dict[str, Any]) -> Any:
        return await self.run_guarded("boqpeg_reverse_conservation", boqpeg_reverse_conservation_flow, body=body)

    async def progress_payment(self, *, body: dict[str, Any]) -> Any:
        return await self.run_guarded("boqpeg_progress_payment", boqpeg_progress_payment_flow, body=body)

    async def unified_alignment(self, *, body: dict[str, Any]) -> Any:
        return await self.run_guarded("boqpeg_unified_alignment", boqpeg_unified_alignment_flow, body=body)

    async def parse_design_manifest(self, **kwargs: Any) -> Any:
        return await self.run_guarded("boqpeg_parse_design_manifest", run_in_threadpool, boqpeg_parse_design_manifest_flow, **kwargs)

    async def match_design_boq(self, **kwargs: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_match_design_boq",
            run_in_threadpool,
            boqpeg_match_design_boq_flow,
            sb=supabase,
            **kwargs,
        )

    async def bidirectional_closure(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_bidirectional_closure",
            boqpeg_bidirectional_closure_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def create_bridge_entity(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_create_bridge_entity",
            boqpeg_create_bridge_entity_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def bind_bridge_items(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_bind_bridge_items",
            boqpeg_bind_bridge_items_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def full_line_piles(self, *, project_uri: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_full_line_piles",
            boqpeg_full_line_piles_flow,
            sb=supabase,
            project_uri=project_uri,
        )

    async def create_pile_entity(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_create_pile_entity",
            boqpeg_create_pile_entity_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def update_pile_state(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_update_pile_state",
            boqpeg_update_pile_state_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def get_pile_entity(self, *, project_uri: str, bridge_name: str, pile_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_get_pile_entity",
            boqpeg_get_pile_entity_flow,
            sb=supabase,
            project_uri=project_uri,
            bridge_name=bridge_name,
            pile_id=pile_id,
        )

    async def bridge_piles(self, *, project_uri: str, bridge_name: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_bridge_piles",
            boqpeg_bridge_piles_flow,
            sb=supabase,
            project_uri=project_uri,
            bridge_name=bridge_name,
        )

    async def create_bridge_schedule(
        self,
        *,
        project_uri: str,
        bridge_name: str,
        body: dict[str, Any],
        commit: bool = False,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_create_bridge_schedule",
            boqpeg_create_bridge_schedule_flow,
            sb=supabase,
            project_uri=project_uri,
            bridge_name=bridge_name,
            body=body,
            commit=bool(commit),
        )

    async def get_bridge_schedule(self, *, project_uri: str, bridge_name: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_get_bridge_schedule",
            boqpeg_get_bridge_schedule_flow,
            sb=supabase,
            project_uri=project_uri,
            bridge_name=bridge_name,
        )

    async def sync_bridge_schedule(
        self,
        *,
        project_uri: str,
        bridge_name: str,
        body: dict[str, Any],
        commit: bool = False,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_sync_bridge_schedule",
            boqpeg_sync_bridge_schedule_flow,
            sb=supabase,
            project_uri=project_uri,
            bridge_name=bridge_name,
            body=body,
            commit=bool(commit),
        )

    async def full_line_schedule(self, *, project_uri: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_full_line_schedule",
            boqpeg_full_line_schedule_flow,
            sb=supabase,
            project_uri=project_uri,
        )

    async def create_process_chain(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_create_process_chain",
            boqpeg_create_process_chain_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def get_process_chain(self, *, project_uri: str, component_uri: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_get_process_chain",
            boqpeg_get_process_chain_flow,
            sb=supabase,
            project_uri=project_uri,
            component_uri=component_uri,
        )

    async def submit_process_table(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_submit_process_table",
            boqpeg_submit_process_table_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def product_manifest(self) -> Any:
        return await self.run_guarded(
            "boqpeg_product_manifest",
            boqpeg_product_manifest_flow,
        )

    async def phase1_bridge_report(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_phase1_bridge_report",
            boqpeg_phase1_bridge_report_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def normref_logic_scaffold(self, *, body: dict[str, Any], commit: bool = False) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "boqpeg_normref_logic_scaffold",
            boqpeg_normref_logic_scaffold_flow,
            sb=supabase,
            body=body,
            commit=bool(commit),
        )

    async def tab_to_peg(self, **kwargs: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("boqpeg_tab_to_peg", run_in_threadpool, boqpeg_tab_to_peg_flow, sb=supabase, **kwargs)
