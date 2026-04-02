"""
Enterprise settings routes for QCSpec.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Form

from services.api.dependencies import get_settings_service
from services.api.domain import SettingsService
from services.api.settings_schemas import (
    ErpNextTestRequest,
    GitPegRegistrarTestRequest,
    SettingsUpdate,
)

router = APIRouter()


@router.get("/")
async def get_settings(enterprise_id: str, settings_service: SettingsService = Depends(get_settings_service)):
    return await settings_service.get_settings(enterprise_id=enterprise_id)


@router.post("/template/upload")
async def upload_template(
    enterprise_id: str = Form(...),
    file: UploadFile = File(...),
    settings_service: SettingsService = Depends(get_settings_service),
):
    return await settings_service.upload_template(enterprise_id=enterprise_id, file=file)


@router.post("/erpnext/test")
async def test_erpnext_connection(
    body: ErpNextTestRequest,
    settings_service: SettingsService = Depends(get_settings_service),
):
    return await settings_service.test_erpnext_connection(body=body)


@router.post("/gitpeg/test")
async def test_gitpeg_registrar_connection(
    body: GitPegRegistrarTestRequest,
    settings_service: SettingsService = Depends(get_settings_service),
):
    return await settings_service.test_gitpeg_registrar_connection(body=body)


@router.patch("/")
async def update_settings(
    enterprise_id: str,
    body: SettingsUpdate,
    settings_service: SettingsService = Depends(get_settings_service),
):
    return await settings_service.update_settings(enterprise_id=enterprise_id, body=body)
