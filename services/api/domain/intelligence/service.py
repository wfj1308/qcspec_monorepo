"""Intelligence domain facade for spatial, finance, OM, and analytics flows."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.proof_flow_service import (
    ar_anchor_overlay_flow,
    bind_utxo_to_spatial_flow,
    convert_to_finance_asset_flow,
    export_finance_proof_flow,
    export_sovereign_om_bundle_flow,
    generate_norm_evolution_report_flow,
    get_spatial_dashboard_flow,
    register_om_event_flow,
    predictive_quality_analysis_flow,
    specdict_evolution_flow,
    specdict_export_bundle_flow,
)


class IntelligenceService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def bind_utxo_to_spatial(self, *, body: Any) -> Any:
        return await self.run_guarded("bind_utxo_to_spatial", bind_utxo_to_spatial_flow, body=body, sb=self.require_supabase())

    async def get_spatial_dashboard(self, *, project_uri: str, limit: int) -> Any:
        return await self.run_guarded(
            "get_spatial_dashboard",
            get_spatial_dashboard_flow,
            project_uri=project_uri,
            limit=limit,
            sb=self.require_supabase(),
        )

    async def predictive_quality_analysis(self, *, body: Any) -> Any:
        return await self.run_guarded("predictive_quality_analysis", predictive_quality_analysis_flow, body=body, sb=self.require_supabase())

    async def export_finance_proof(self, *, body: Any) -> Any:
        return await self.run_guarded("export_finance_proof", export_finance_proof_flow, body=body, sb=self.require_supabase())

    async def convert_to_finance_asset(self, *, body: Any) -> Any:
        return await self.run_guarded("convert_to_finance_asset", convert_to_finance_asset_flow, body=body, sb=self.require_supabase())

    async def export_om_bundle(self, *, body: Any) -> Any:
        return await self.run_guarded("export_om_bundle", export_sovereign_om_bundle_flow, body=body, sb=self.require_supabase())

    async def register_om_event(self, *, body: Any) -> Any:
        return await self.run_guarded("register_om_event", register_om_event_flow, body=body, sb=self.require_supabase())

    async def generate_norm_evolution_report(self, *, body: Any) -> Any:
        return await self.run_guarded("generate_norm_evolution_report", generate_norm_evolution_report_flow, body=body, sb=self.require_supabase())

    async def evolve_specdict(self, *, body: Any) -> Any:
        return await self.run_guarded("evolve_specdict", specdict_evolution_flow, body=body, sb=self.require_supabase())

    async def export_specdict_bundle(self, *, body: Any) -> Any:
        return await self.run_guarded("export_specdict_bundle", specdict_export_bundle_flow, body=body, sb=self.require_supabase())

    async def get_ar_overlay(self, *, project_uri: str, lat: float, lng: float, radius_m: float, limit: int) -> Any:
        return await self.run_guarded(
            "get_ar_overlay",
            ar_anchor_overlay_flow,
            project_uri=project_uri,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            limit=limit,
            sb=self.require_supabase(),
        )
