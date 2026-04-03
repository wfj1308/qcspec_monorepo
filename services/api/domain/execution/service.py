"""Execution domain facade for TripRole, remediation, and lab workflows."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.execution.helpers import (
    aggregate_provenance_chain_flow,
    apply_variation_flow,
    calc_inspection_frequency_flow,
    close_remediation_trip_flow,
    did_reputation_flow,
    execute_triprole_action_flow,
    get_frequency_dashboard_flow,
    get_full_lineage_flow,
    ingest_sensor_data_flow,
    open_remediation_trip_flow,
    record_lab_test_flow,
    replay_offline_packets_flow,
    remediation_reinspect_flow,
    scan_confirm_signature_flow,
    trace_asset_origin_flow,
    transfer_asset_flow,
    verify_component_utxo_flow,
)


class ExecutionService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def execute_triprole(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("execute_triprole", execute_triprole_action_flow, body=body, sb=supabase)

    async def ingest_sensor_data(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("ingest_sensor_data", ingest_sensor_data_flow, body=body, sb=supabase)

    async def record_lab_test(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("record_lab_test", record_lab_test_flow, body=body, sb=supabase)

    async def calc_frequency(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("calc_frequency", calc_inspection_frequency_flow, body=body, sb=supabase)

    async def get_frequency_dashboard(self, *, project_uri: str, limit_items: int) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "get_frequency_dashboard",
            get_frequency_dashboard_flow,
            project_uri=project_uri,
            limit_items=limit_items,
            sb=supabase,
        )

    async def get_provenance(self, *, utxo_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_provenance", aggregate_provenance_chain_flow, utxo_id=utxo_id, sb=supabase)

    async def get_full_lineage(self, *, utxo_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_full_lineage", get_full_lineage_flow, utxo_id=utxo_id, sb=supabase)

    async def trace_asset_origin(self, *, utxo_id: str = "", boq_item_uri: str = "", project_uri: str = "") -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "trace_asset_origin",
            trace_asset_origin_flow,
            utxo_id=utxo_id,
            boq_item_uri=boq_item_uri,
            project_uri=project_uri,
            sb=supabase,
        )

    async def did_reputation(self, *, project_uri: str, participant_did: str, window_days: int) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "did_reputation",
            did_reputation_flow,
            project_uri=project_uri,
            participant_did=participant_did,
            window_days=window_days,
            sb=supabase,
        )

    async def transfer_asset(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("transfer_asset", transfer_asset_flow, body=body, sb=supabase)

    async def verify_component_utxo(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "verify_component_utxo",
            verify_component_utxo_flow,
            body=body,
            sb=supabase,
        )

    async def apply_variation(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("apply_variation", apply_variation_flow, body=body, sb=supabase)

    async def replay_offline_packets(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("replay_offline_packets", replay_offline_packets_flow, body=body, sb=supabase)

    async def scan_confirm_signature(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("scan_confirm_signature", scan_confirm_signature_flow, body=body, sb=supabase)

    async def open_remediation(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("open_remediation", open_remediation_trip_flow, body=body, sb=supabase)

    async def remediation_reinspect(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("remediation_reinspect", remediation_reinspect_flow, body=body, sb=supabase)

    async def close_remediation(self, *, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("close_remediation", close_remediation_trip_flow, body=body, sb=supabase)
