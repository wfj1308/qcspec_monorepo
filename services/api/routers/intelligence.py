"""Spatial, finance, OM, and analytics routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from services.api.dependencies import get_intelligence_service
from services.api.domain import IntelligenceService
from services.api.domain.proof.schemas import (
    FinanceProofExportBody,
    NormEvolutionBody,
    OMBundleExportBody,
    OMEventBody,
    PredictiveQualityBody,
    RwaConvertBody,
    SpatialBindBody,
    SpecDictEvolutionBody,
    SpecDictExportBody,
)

router = APIRouter()


@router.post("/spatial/bind")
async def bind_utxo_to_spatial(
    body: SpatialBindBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.bind_utxo_to_spatial(body=body)


@router.get("/spatial/dashboard")
async def get_spatial_dashboard(
    project_uri: str,
    limit: int = 5000,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.get_spatial_dashboard(project_uri=project_uri, limit=limit)


@router.post("/ai/predictive-quality")
async def run_predictive_quality_analysis(
    body: PredictiveQualityBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.predictive_quality_analysis(body=body)


@router.post("/finance/proof/export")
async def export_finance_proof(
    body: FinanceProofExportBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.export_finance_proof(body=body)


@router.post("/rwa/convert")
async def convert_rwa_asset(
    body: RwaConvertBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.convert_to_finance_asset(body=body)


@router.post("/om/handover/export")
async def export_om_handover_bundle(
    body: OMBundleExportBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.export_om_bundle(body=body)


@router.post("/om/event/register")
async def register_om_event(
    body: OMEventBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.register_om_event(body=body)


@router.post("/norm/evolution/report")
async def generate_norm_evolution_report(
    body: NormEvolutionBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.generate_norm_evolution_report(body=body)


@router.post("/specdict/evolve")
async def evolve_specdict(
    body: SpecDictEvolutionBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.evolve_specdict(body=body)


@router.post("/specdict/export")
async def export_specdict_bundle(
    body: SpecDictExportBody,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.export_specdict_bundle(body=body)


@router.get("/ar/overlay")
async def get_ar_overlay(
    project_uri: str,
    lat: float,
    lng: float,
    radius_m: float = 80.0,
    limit: int = 50,
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
):
    return await intelligence_service.get_ar_overlay(
        project_uri=project_uri,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        limit=limit,
    )
