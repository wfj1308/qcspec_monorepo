"""BOQ, evidence center, readiness, and merkle routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from services.api.dependencies import get_boq_service
from services.api.domain import BOQService

router = APIRouter()


@router.get("/boq/item-sovereign-history")
async def get_boq_item_sovereign_history(
    project_uri: str,
    subitem_code: str,
    max_rows: int = 50000,
    boq_service: BOQService = Depends(get_boq_service),
):
    return await boq_service.item_sovereign_history(
        project_uri=project_uri,
        subitem_code=subitem_code,
        max_rows=max_rows,
    )


@router.get("/boq/evidence-center/download")
async def download_boq_evidence_center(
    project_uri: str,
    subitem_code: str,
    proof_id: Optional[str] = None,
    verify_base_url: Optional[str] = None,
    boq_service: BOQService = Depends(get_boq_service),
):
    return await boq_service.download_evidence_center(
        project_uri=project_uri,
        subitem_code=subitem_code,
        proof_id=proof_id,
        verify_base_url=verify_base_url or "https://verify.qcspec.com",
    )


@router.get("/boq/evidence-center/evidence")
async def get_boq_evidence_center_evidence(
    project_uri: Optional[str] = None,
    subitem_code: Optional[str] = None,
    boq_item_uri: Optional[str] = None,
    smu_id: Optional[str] = None,
    boq_service: BOQService = Depends(get_boq_service),
):
    return await boq_service.evidence_center_evidence(
        project_uri=project_uri,
        subitem_code=subitem_code,
        boq_item_uri=boq_item_uri,
        smu_id=smu_id,
    )


@router.get("/boq/reconciliation")
async def get_boq_reconciliation(
    project_uri: str,
    subitem_code: str = "",
    max_rows: int = 50000,
    limit_items: int = 2000,
    boq_service: BOQService = Depends(get_boq_service),
):
    return await boq_service.reconciliation(
        project_uri=project_uri,
        subitem_code=subitem_code,
        max_rows=max_rows,
        limit_items=limit_items,
    )


@router.get("/boq/realtime-status")
async def get_boq_realtime_status(
    project_uri: str,
    boq_service: BOQService = Depends(get_boq_service),
):
    return await boq_service.realtime_status(project_uri=project_uri)


@router.get("/project-readiness-check")
async def get_project_readiness_check(
    project_uri: str,
    boq_service: BOQService = Depends(get_boq_service),
):
    return await boq_service.readiness_check(project_uri=project_uri)


@router.get("/unit/merkle-root")
async def get_unit_merkle_root(
    project_uri: str,
    unit_code: str = "",
    proof_id: str = "",
    max_rows: int = 20000,
    boq_service: BOQService = Depends(get_boq_service),
):
    return await boq_service.unit_merkle_root(
        project_uri=project_uri,
        unit_code=unit_code,
        proof_id=proof_id,
        max_rows=max_rows,
    )
