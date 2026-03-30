"""
Public verify routes (no auth).
services/api/routers/verify.py
"""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.verify_public_flow_service import (
    download_dsp_package_flow,
    get_public_verify_detail_flow,
    resolve_normpeg_threshold_public_flow,
    resolve_spec_rule_public_flow,
    run_mock_anchor_once_flow,
)

router = APIRouter()
public_router = APIRouter()


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _mock_anchor_enabled() -> bool:
    return _is_truthy(
        str(
            os.getenv("VERIFY_ENABLE_MOCK_ANCHOR")
            or os.getenv("QCSPEC_VERIFY_ENABLE_MOCK_ANCHOR")
            or ""
        )
    )


def _mock_anchor_internal_key() -> str:
    return str(
        os.getenv("VERIFY_MOCK_ANCHOR_INTERNAL_KEY")
        or os.getenv("QCSPEC_VERIFY_MOCK_ANCHOR_INTERNAL_KEY")
        or ""
    ).strip()


def _verify_base_url() -> str:
    base = str(os.getenv("QCSPEC_VERIFY_BASE_URL") or "https://verify.qcspec.com").strip()
    return base.rstrip("/")


@public_router.get("/spec/resolve")
async def resolve_spec_rule_public(
    spec_uri: str,
    metric: str = "",
    component_type: str = "",
    sb: Client = Depends(get_supabase),
):
    return await resolve_spec_rule_public_flow(
        spec_uri=spec_uri,
        metric=metric,
        component_type=component_type,
        sb=sb,
    )


@public_router.get("/spec/threshold")
async def resolve_normpeg_threshold_public(
    spec_uri: str,
    context: str = "",
    value: float | None = None,
    design: float | None = None,
    sb: Client = Depends(get_supabase),
):
    return await resolve_normpeg_threshold_public_flow(
        spec_uri=spec_uri,
        context=context,
        value=value,
        design=design,
        sb=sb,
    )


@router.post("/anchor/mock-run")
async def run_mock_anchor_once(
    x_internal_key: str | None = Header(default=None, alias="X-QCSPEC-Internal-Key"),
):
    if not _mock_anchor_enabled():
        # Default-off in all environments unless explicitly enabled.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    expected_key = _mock_anchor_internal_key()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="mock anchor internal key not configured",
        )
    if not hmac.compare_digest(str(x_internal_key or ""), expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    return await run_mock_anchor_once_flow()


@public_router.get("/{proof_id}")
async def get_public_verify_detail(
    proof_id: str,
    lineage_depth: str = "item",
    sb: Client = Depends(get_supabase),
):
    return await get_public_verify_detail_flow(
        proof_id=proof_id,
        lineage_depth=lineage_depth,
        sb=sb,
        verify_base_url=_verify_base_url(),
    )


@public_router.get("/{proof_id}/dsp")
async def download_dsp_package(
    proof_id: str,
    sb: Client = Depends(get_supabase),
):
    return await download_dsp_package_flow(
        proof_id=proof_id,
        sb=sb,
        verify_base_url=_verify_base_url(),
    )
