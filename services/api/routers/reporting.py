"""
QCSpec report routes
services/api/routers/reporting.py
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel

from services.api.dependencies import get_reporting_service
from services.api.domain import ReportingService

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
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    return await reporting_service.export(body=body)


@router.get("/export")
async def export_report_by_proof_id(
    proof_id: str = Query(..., description="Proof UTXO ID, e.g. GP-PROOF-XXXX"),
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    report_type: str = Query("inspection"),
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    return await reporting_service.export_by_proof_id(
        proof_id=proof_id,
        format=format,
        report_type=report_type,
    )


@router.post("/generate", status_code=202)
async def generate_report(
    body: ReportRequest,
    background_tasks: BackgroundTasks,
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    return await reporting_service.generate(
        body=body,
        background_tasks=background_tasks,
    )


@router.get("/")
async def list_reports(
    project_id: str,
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    return await reporting_service.list(project_id=project_id)


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    reporting_service: ReportingService = Depends(get_reporting_service),
):
    return await reporting_service.get(report_id=report_id)
