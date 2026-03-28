"""
Enterprise settings routes for QCSpec.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Form
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.settings_schemas import (
    ErpNextTestRequest,
    GitPegRegistrarTestRequest,
    SettingsUpdate,
)
from services.api.settings_service import (
    get_settings_flow,
    test_erpnext_connection_flow,
    test_gitpeg_registrar_connection_flow,
    update_settings_flow,
    upload_template_flow,
)

router = APIRouter()


@router.get("/")
async def get_settings(enterprise_id: str, sb: Client = Depends(get_supabase)):
    return await get_settings_flow(enterprise_id=enterprise_id, sb=sb)


@router.post("/template/upload")
async def upload_template(
    enterprise_id: str = Form(...),
    file: UploadFile = File(...),
    sb: Client = Depends(get_supabase),
):
    return await upload_template_flow(enterprise_id=enterprise_id, file=file, sb=sb)


@router.post("/erpnext/test")
async def test_erpnext_connection(body: ErpNextTestRequest):
    return await test_erpnext_connection_flow(body=body)


@router.post("/gitpeg/test")
async def test_gitpeg_registrar_connection(body: GitPegRegistrarTestRequest):
    return await test_gitpeg_registrar_connection_flow(body=body)


@router.patch("/")
async def update_settings(
    enterprise_id: str,
    body: SettingsUpdate,
    sb: Client = Depends(get_supabase),
):
    return await update_settings_flow(enterprise_id=enterprise_id, body=body, sb=sb)
