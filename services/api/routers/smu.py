"""SMU and genesis routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from services.api.dependencies import get_smu_service
from services.api.domain import SMUService
from services.api.domain.proof.schemas import SMUExecuteBody, SMUFreezeBody, SMUSignBody, SMUValidateBody

router = APIRouter()
public_router = APIRouter()


@router.post("/smu/genesis/import")
async def import_smu_genesis(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    commit: bool = Form(True),
    smu_service: SMUService = Depends(get_smu_service),
):
    return await smu_service.import_genesis(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        commit=commit,
    )


@router.post("/smu/genesis/preview")
async def preview_smu_genesis(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    smu_service: SMUService = Depends(get_smu_service),
):
    return await smu_service.preview_genesis(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
    )


@router.post("/smu/genesis/import-async")
async def import_smu_genesis_async(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    commit: bool = Form(True),
    smu_service: SMUService = Depends(get_smu_service),
):
    return await smu_service.import_genesis_async(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        commit=commit,
    )


@router.get("/smu/genesis/import-job/{job_id}")
async def get_smu_genesis_import_job(job_id: str, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.get_import_job(job_id=job_id)


@public_router.get("/smu/genesis/import-job-public/{job_id}")
async def get_smu_genesis_import_job_public(job_id: str, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.get_import_job(job_id=job_id)


@router.get("/smu/genesis/import-job-active")
async def get_smu_genesis_import_job_active(project_uri: str, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.get_active_import_job(project_uri=project_uri)


@public_router.get("/smu/genesis/import-job-active-public")
async def get_smu_genesis_import_job_active_public(project_uri: str, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.get_active_import_job(project_uri=project_uri)


@router.get("/smu/spu/library")
async def get_smu_spu_library(smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.get_spu_library()


@router.get("/smu/node/context")
async def get_smu_node_context(
    project_uri: str,
    boq_item_uri: str,
    component_type: str = "generic",
    measured_value: Optional[float] = None,
    smu_service: SMUService = Depends(get_smu_service),
):
    return await smu_service.get_node_context(
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
        component_type=component_type,
        measured_value=measured_value,
    )


@router.post("/smu/execute")
async def execute_smu_trip(body: SMUExecuteBody, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.execute_trip(body=body)


@router.post("/smu/sign")
async def sign_smu_trip(body: SMUSignBody, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.sign_trip(body=body)


@router.post("/smu/validate-logic")
async def validate_smu_logic(body: SMUValidateBody, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.validate_logic(body=body)


@router.post("/smu/freeze")
async def freeze_smu_asset(body: SMUFreezeBody, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.freeze_asset(body=body)


@router.post("/smu/erpnext/retry")
async def retry_erpnext_push(limit: int = 20, smu_service: SMUService = Depends(get_smu_service)):
    return await smu_service.retry_erpnext_push(limit=limit)
