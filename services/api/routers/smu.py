"""SMU routes.

Genesis import endpoints are legacy compatibility aliases and are forwarded to
BOQPeg service handlers so old clients and new clients share one import chain.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from services.api.dependencies import get_boqpeg_service, get_smu_service
from services.api.domain import BOQPegService, SMUService
from services.api.domain.proof.schemas import SMUExecuteBody, SMUFreezeBody, SMUSignBody, SMUValidateBody

router = APIRouter()
public_router = APIRouter()


def _to_text(value: object) -> str:
    return str(value or "").strip()


def _parse_json_object(raw: str, *, field_name: str) -> dict[str, object]:
    text = _to_text(raw)
    if not text:
        return {}
    try:
        decoded = json.loads(text)
    except Exception as exc:
        raise HTTPException(400, f"invalid {field_name}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise HTTPException(400, f"{field_name} must decode to object")
    return decoded


@router.post("/smu/genesis/import")
async def import_smu_genesis(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    bridge_mappings_json: str = Form(""),
    commit: bool = Form(True),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    bridge_mappings = _parse_json_object(bridge_mappings_json, field_name="bridge_mappings_json")
    return await boqpeg_service.import_upload(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
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
    bridge_mappings_json: str = Form(""),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    bridge_mappings = _parse_json_object(bridge_mappings_json, field_name="bridge_mappings_json")
    return await boqpeg_service.preview_upload(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
    )


@router.post("/smu/genesis/import-async")
async def import_smu_genesis_async(
    file: UploadFile = File(...),
    project_uri: str = Form(...),
    project_id: str = Form(""),
    boq_root_uri: str = Form(""),
    norm_context_root_uri: str = Form(""),
    owner_uri: str = Form(""),
    bridge_mappings_json: str = Form(""),
    commit: bool = Form(True),
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    bridge_mappings = _parse_json_object(bridge_mappings_json, field_name="bridge_mappings_json")
    return await boqpeg_service.import_upload_async(
        file=file,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        commit=commit,
    )


@router.get("/smu/genesis/import-job/{job_id}")
async def get_smu_genesis_import_job(job_id: str, boqpeg_service: BOQPegService = Depends(get_boqpeg_service)):
    return await boqpeg_service.get_import_job(job_id=job_id)


@public_router.get("/smu/genesis/import-job-public/{job_id}")
async def get_smu_genesis_import_job_public(
    job_id: str,
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.get_import_job(job_id=job_id)


@router.get("/smu/genesis/import-job-active")
async def get_smu_genesis_import_job_active(
    project_uri: str,
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.get_active_import_job(project_uri=project_uri)


@public_router.get("/smu/genesis/import-job-active-public")
async def get_smu_genesis_import_job_active_public(
    project_uri: str,
    boqpeg_service: BOQPegService = Depends(get_boqpeg_service),
):
    return await boqpeg_service.get_active_import_job(project_uri=project_uri)


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
