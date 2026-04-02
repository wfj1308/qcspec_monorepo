"""
QCSpec inspection routes
services/api/routers/inspections.py
"""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from services.api.dependencies import get_inspections_service
from services.api.domain import InspectionsService

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
    photo_ids: Optional[List[str]] = Field(default_factory=list)
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
    inspections_service: InspectionsService = Depends(get_inspections_service),
):
    """List inspections by project."""
    return await inspections_service.list_inspections(
        project_id=project_id,
        result=result,
        kind=type,
        limit=limit,
        offset=offset,
    )


@router.post("/", status_code=201)
async def create_inspection(
    body: InspectionCreate,
    inspections_service: InspectionsService = Depends(get_inspections_service),
):
    """Create an inspection and append proof-chain record."""
    return await inspections_service.create_inspection(body=body)


@router.get("/stats/{project_id}")
async def project_stats(
    project_id: str,
    inspections_service: InspectionsService = Depends(get_inspections_service),
):
    """Inspection stats for a project."""
    return await inspections_service.project_stats(project_id=project_id)


@router.delete("/{inspection_id}")
async def delete_inspection(
    inspection_id: str,
    inspections_service: InspectionsService = Depends(get_inspections_service),
):
    """Delete inspection."""
    return await inspections_service.delete_inspection(inspection_id=inspection_id)
