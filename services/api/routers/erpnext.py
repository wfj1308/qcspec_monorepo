"""
ERPNext integration routes and helpers for QCSpec.
services/api/routers/erpnext.py
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.api.dependencies import get_erpnext_integration_service
from services.api.domain import ERPNextIntegrationService

router = APIRouter()


class ERPNextNotifyRequest(BaseModel):
    enterprise_id: str
    project_id: Optional[str] = None
    stake: str
    subitem: Optional[str] = None
    result: str
    amount: Optional[float] = None
    reason: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


@router.get("/gate-check")
async def check_metering_gate(
    enterprise_id: str,
    stake: str,
    subitem: str,
    result: str = "pass",
    project_id: Optional[str] = None,
    project_code: Optional[str] = None,
    erpnext_service: ERPNextIntegrationService = Depends(get_erpnext_integration_service),
):
    return await erpnext_service.check_metering_gate(
        enterprise_id=enterprise_id,
        stake=stake,
        subitem=subitem,
        result=result,
        project_id=project_id,
        project_code=project_code,
    )


@router.get("/project-basics")
async def get_project_basics(
    enterprise_id: str,
    project_code: Optional[str] = None,
    project_name: Optional[str] = None,
    erpnext_service: ERPNextIntegrationService = Depends(get_erpnext_integration_service),
):
    return await erpnext_service.get_project_basics(
        enterprise_id=enterprise_id,
        project_code=project_code,
        project_name=project_name,
    )


@router.get("/metering-requests")
async def get_metering_requests(
    enterprise_id: str,
    project_code: Optional[str] = None,
    stake: Optional[str] = None,
    subitem: Optional[str] = None,
    status: Optional[str] = None,
    erpnext_service: ERPNextIntegrationService = Depends(get_erpnext_integration_service),
):
    return await erpnext_service.get_metering_requests(
        enterprise_id=enterprise_id,
        project_code=project_code,
        stake=stake,
        subitem=subitem,
        status=status,
    )


@router.post("/notify")
async def notify_erpnext(
    body: ERPNextNotifyRequest,
    erpnext_service: ERPNextIntegrationService = Depends(get_erpnext_integration_service),
):
    return await erpnext_service.notify_erpnext(body=body)


@router.get("/probe")
async def probe_erpnext(
    enterprise_id: str,
    sample_project_name: str = "QCSpec sample project",
    sample_stake: str = "K22+500",
    sample_subitem: str = "compaction",
    erpnext_service: ERPNextIntegrationService = Depends(get_erpnext_integration_service),
):
    return await erpnext_service.probe_erpnext(
        enterprise_id=enterprise_id,
        sample_project_name=sample_project_name,
        sample_stake=sample_stake,
        sample_subitem=sample_subitem,
    )
