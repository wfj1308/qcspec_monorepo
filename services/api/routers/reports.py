"""
QCSpec report routes
services/api/routers/reports.py
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.reports_flow_service import (
    export_report_by_proof_id_flow,
    export_report_flow,
    generate_report_flow,
    get_report_flow,
    list_reports_flow,
)

router = APIRouter()


class ReportRequest(BaseModel):
    project_id: str
    enterprise_id: str
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ReportExportRequest(BaseModel):
    project_id: str
    enterprise_id: str
    type: str = "inspection"
    format: str = "docx"
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@router.post("/export")
async def export_report(
    body: ReportExportRequest,
    sb: Client = Depends(get_supabase),
):
    return await export_report_flow(body=body, sb=sb)


@router.get("/export")
async def export_report_by_proof_id(
    proof_id: str = Query(..., description="Proof UTXO ID, e.g. GP-PROOF-XXXX"),
    format: str = Query("docx", regex="^(docx|pdf)$"),
    report_type: str = Query("inspection"),
    sb: Client = Depends(get_supabase),
):
    return await export_report_by_proof_id_flow(
        proof_id=proof_id,
        format=format,
        report_type=report_type,
        sb=sb,
    )


@router.post("/generate", status_code=202)
async def generate_report(
    body: ReportRequest,
    background_tasks: BackgroundTasks,
    sb: Client = Depends(get_supabase),
):
    return await generate_report_flow(
        body=body,
        background_tasks=background_tasks,
        sb=sb,
    )


@router.get("/")
async def list_reports(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    return list_reports_flow(project_id=project_id, sb=sb)


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    sb: Client = Depends(get_supabase),
):
    return get_report_flow(report_id=report_id, sb=sb)
