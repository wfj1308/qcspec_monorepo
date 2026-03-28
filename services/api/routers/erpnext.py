"""
ERPNext integration routes and helpers for QCSpec.
services/api/routers/erpnext.py
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.erpnext_flow_service import (
    check_metering_gate_flow,
    get_metering_requests_flow,
    get_project_basics_flow,
    notify_erpnext_flow,
    probe_erpnext_flow,
)

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
    sb: Client = Depends(get_supabase),
):
    return await check_metering_gate_flow(
        enterprise_id=enterprise_id,
        stake=stake,
        subitem=subitem,
        result=result,
        project_id=project_id,
        project_code=project_code,
        sb=sb,
    )


@router.get("/project-basics")
async def get_project_basics(
    enterprise_id: str,
    project_code: Optional[str] = None,
    project_name: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    return await get_project_basics_flow(
        enterprise_id=enterprise_id,
        project_code=project_code,
        project_name=project_name,
        sb=sb,
    )


@router.get("/metering-requests")
async def get_metering_requests(
    enterprise_id: str,
    project_code: Optional[str] = None,
    stake: Optional[str] = None,
    subitem: Optional[str] = None,
    status: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    return await get_metering_requests_flow(
        enterprise_id=enterprise_id,
        project_code=project_code,
        stake=stake,
        subitem=subitem,
        status=status,
        sb=sb,
    )


@router.post("/notify")
async def notify_erpnext(
    body: ERPNextNotifyRequest,
    sb: Client = Depends(get_supabase),
):
    return await notify_erpnext_flow(body=body, sb=sb)


@router.get("/probe")
async def probe_erpnext(
    enterprise_id: str,
    sample_project_name: str = "QCSpec sample project",
    sample_stake: str = "K22+500",
    sample_subitem: str = "compaction",
    sb: Client = Depends(get_supabase),
):
    return await probe_erpnext_flow(
        enterprise_id=enterprise_id,
        sample_project_name=sample_project_name,
        sample_stake=sample_stake,
        sample_subitem=sample_subitem,
        sb=sb,
    )
