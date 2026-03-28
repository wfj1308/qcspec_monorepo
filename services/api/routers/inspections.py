"""
QCSpec inspection routes
services/api/routers/inspections.py
"""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.inspections_service import (
    create_inspection_flow,
    delete_inspection_flow,
    list_inspections_flow,
    project_stats_flow,
)

router = APIRouter()


class InspectionCreate(BaseModel):
    project_id: str
    location: str
    type: str
    type_name: str
    value: Optional[float] = None
    standard: Optional[float] = None
    unit: str = ""
    result: str  # pass / warn / fail
    person: Optional[str] = None
    remark: Optional[str] = None
    inspected_at: Optional[str] = None
    photo_ids: Optional[List[str]] = []
    # Live rebar fields (Proof UTXO compatible state_data payload).
    design: Optional[float] = None
    limit: Optional[str] = None
    values: Optional[List[float]] = None
    # SpecIR optional inputs.
    spec_uri: Optional[str] = None
    norm_uri: Optional[str] = None
    component_type: Optional[str] = None
    structure_type: Optional[str] = None


class InspectionFilter(BaseModel):
    result: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@router.get("/")
async def list_inspections(
    project_id: str,
    result: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    sb: Client = Depends(get_supabase),
):
    """List inspections by project."""
    return await list_inspections_flow(
        project_id=project_id,
        result=result,
        kind=type,
        limit=limit,
        offset=offset,
        sb=sb,
    )


@router.post("/", status_code=201)
async def create_inspection(
    body: InspectionCreate,
    sb: Client = Depends(get_supabase),
):
    """Create an inspection and append proof-chain record."""
    return await create_inspection_flow(body=body, sb=sb)


@router.get("/stats/{project_id}")
async def project_stats(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    """Inspection stats for a project."""
    return await project_stats_flow(project_id=project_id, sb=sb)


@router.delete("/{inspection_id}")
async def delete_inspection(
    inspection_id: str,
    sb: Client = Depends(get_supabase),
):
    """Delete inspection."""
    return await delete_inspection_flow(inspection_id=inspection_id, sb=sb)
