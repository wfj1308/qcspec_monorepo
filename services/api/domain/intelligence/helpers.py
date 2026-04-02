"""Intelligence flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.core.http import binary_download_response
from services.api.domain.intelligence.flows import (
    analyze_specdict_evolution,
    bind_utxo_to_spatial,
    convert_to_finance_asset,
    export_finance_proof,
    export_sovereign_om_bundle,
    generate_norm_evolution_report,
    get_ar_anchor_overlay,
    get_spatial_dashboard,
    predictive_quality_analysis,
    register_om_event,
    export_specdict_bundle,
)


def bind_utxo_to_spatial_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return bind_utxo_to_spatial(
        sb=sb,
        utxo_id=str(body.utxo_id or ""),
        bim_id=str(body.bim_id or ""),
        coordinate=dict(body.coordinate or {}),
        project_uri=str(body.project_uri or ""),
        label=str(body.label or ""),
        metadata=dict(body.metadata or {}),
    )


def get_spatial_dashboard_flow(*, project_uri: str, limit: int, sb: Client) -> dict[str, Any]:
    return get_spatial_dashboard(
        sb=sb,
        project_uri=project_uri,
        limit=limit,
    )


def predictive_quality_analysis_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return predictive_quality_analysis(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        near_threshold_ratio=float(body.near_threshold_ratio or 0.9),
        min_samples=int(body.min_samples or 3),
        apply_dynamic_gate=bool(body.apply_dynamic_gate),
        default_critical_threshold=float(body.default_critical_threshold or 2.0),
    )


async def export_finance_proof_flow(*, body: Any, sb: Client) -> StreamingResponse:
    result = export_finance_proof(
        sb=sb,
        payment_id=str(body.payment_id or ""),
        bank_code=str(body.bank_code or ""),
        passphrase=str(body.passphrase or ""),
        run_anchor_rounds=int(body.run_anchor_rounds or 0),
    )
    return binary_download_response(
        payload=result.get("blob_bytes") or b"",
        media_type="application/octet-stream",
        filename=str(result.get("filename") or "FINANCE-PROOF.qcfp"),
        headers={
            "X-Finance-Payment-Id": str(result.get("payment_id") or ""),
            "X-Finance-Proof-Id": str(result.get("finance_proof_id") or ""),
            "X-Finance-Payload-Hash": str(result.get("payload_hash") or ""),
            "X-Finance-GitPeg-Anchor": str(result.get("finance_gitpeg_anchor") or ""),
        },
    )


async def convert_to_finance_asset_flow(*, body: Any, sb: Client) -> StreamingResponse:
    result = convert_to_finance_asset(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        boq_group_id=str(body.boq_group_id or ""),
        project_name=str(body.project_name or ""),
        bank_code=str(body.bank_code or ""),
        passphrase=str(body.passphrase or ""),
        run_anchor_rounds=int(body.run_anchor_rounds or 0),
    )
    return binary_download_response(
        payload=result.get("blob_bytes") or b"",
        media_type="application/octet-stream",
        filename=str(result.get("filename") or "RWA-ASSET.qcrwa"),
        headers={
            "X-RWA-Project-Uri": str(result.get("project_uri") or ""),
            "X-RWA-Group-Id": str(result.get("boq_group_id") or ""),
            "X-RWA-Proof-Id": str(result.get("rwa_proof_id") or ""),
            "X-RWA-Certificate-Hash": str(result.get("certificate_hash") or ""),
            "X-RWA-GitPeg-Anchor": str(result.get("rwa_gitpeg_anchor") or ""),
        },
    )


async def export_sovereign_om_bundle_flow(*, body: Any, sb: Client) -> StreamingResponse:
    result = export_sovereign_om_bundle(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        project_name=str(body.project_name or ""),
        om_owner_uri=str(body.om_owner_uri or "v://operator/om/default"),
        passphrase=str(body.passphrase or ""),
        run_anchor_rounds=int(body.run_anchor_rounds or 0),
    )
    return binary_download_response(
        payload=result.get("zip_bytes") or b"",
        media_type="application/zip",
        filename=str(result.get("filename") or "OM-HANDOVER.zip"),
        headers={
            "X-OM-Root-Uri": str(result.get("om_root_uri") or ""),
            "X-OM-Root-Proof-Id": str(result.get("om_root_proof_id") or ""),
            "X-OM-GitPeg-Anchor": str(result.get("om_gitpeg_anchor") or ""),
            "X-OM-Payload-Hash": str(result.get("payload_hash") or ""),
        },
    )


def register_om_event_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return register_om_event(
        sb=sb,
        om_root_proof_id=str(body.om_root_proof_id or ""),
        title=str(body.title or ""),
        event_type=str(body.event_type or "maintenance"),
        payload=dict(body.payload or {}),
        executor_uri=str(body.executor_uri or "v://operator/om/default"),
    )


def specdict_evolution_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return analyze_specdict_evolution(
        sb=sb,
        project_uris=list(body.project_uris or []),
        min_samples=int(body.min_samples or 5),
    )


def specdict_export_bundle_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return export_specdict_bundle(
        sb=sb,
        project_uris=list(body.project_uris or []),
        min_samples=int(body.min_samples or 5),
        namespace_uri=str(body.namespace_uri or "v://global/templates"),
        commit=bool(body.commit),
    )


def ar_anchor_overlay_flow(
    *,
    project_uri: str,
    lat: float,
    lng: float,
    radius_m: float,
    limit: int,
    sb: Client,
) -> dict[str, Any]:
    return get_ar_anchor_overlay(
        sb=sb,
        project_uri=project_uri,
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        limit=limit,
    )


def generate_norm_evolution_report_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return generate_norm_evolution_report(
        sb=sb,
        project_uris=list(body.project_uris or []),
        min_samples=int(body.min_samples or 5),
        near_threshold_ratio=float(body.near_threshold_ratio or 0.9),
        anonymize=bool(body.anonymize),
        create_proof=bool(body.create_proof),
    )
