"""
Public verify routes (no auth).
services/api/routers/verify.py
"""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status

from services.api.dependencies import get_public_verify_service
from services.api.domain import PublicVerifyService

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
    verify_service: PublicVerifyService = Depends(get_public_verify_service),
):
    return await verify_service.resolve_spec_rule_public(
        spec_uri=spec_uri,
        metric=metric,
        component_type=component_type,
    )


@public_router.get("/spec/threshold")
async def resolve_normpeg_threshold_public(
    spec_uri: str,
    context: str = "",
    value: float | None = None,
    design: float | None = None,
    verify_service: PublicVerifyService = Depends(get_public_verify_service),
):
    return await verify_service.resolve_normpeg_threshold_public(
        spec_uri=spec_uri,
        context=context,
        value=value,
        design=design,
    )


@router.post("/anchor/mock-run")
async def run_mock_anchor_once(
    x_internal_key: str | None = Header(default=None, alias="X-QCSPEC-Internal-Key"),
    verify_service: PublicVerifyService = Depends(get_public_verify_service),
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

    return await verify_service.run_mock_anchor_once()


@public_router.get("/{proof_id}")
async def get_public_verify_detail(
    proof_id: str,
    lineage_depth: str = "item",
    verify_service: PublicVerifyService = Depends(get_public_verify_service),
):
    return await verify_service.get_public_verify_detail(
        proof_id=proof_id,
        lineage_depth=lineage_depth,
        verify_base_url=_verify_base_url(),
    )


@public_router.get("/{proof_id}/dsp")
async def download_dsp_package(
    proof_id: str,
    verify_service: PublicVerifyService = Depends(get_public_verify_service),
):
    return await verify_service.download_dsp_package(
        proof_id=proof_id,
        verify_base_url=_verify_base_url(),
    )
