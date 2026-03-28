"""
QCSpec media evidence routes.
services/api/routers/photos.py
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from supabase import Client

from services.api.dependencies import get_supabase
from services.api.photos_flow_service import delete_photo_flow, list_photos_flow, upload_photo_flow

router = APIRouter()


@router.post("/upload", status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    enterprise_id: str = Form(...),
    location: Optional[str] = Form(None),
    inspection_id: Optional[str] = Form(None),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
    sb: Client = Depends(get_supabase),
):
    return await upload_photo_flow(
        file=file,
        project_id=project_id,
        enterprise_id=enterprise_id,
        location=location,
        inspection_id=inspection_id,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        sb=sb,
    )


@router.get("/")
async def list_photos(
    project_id: str,
    inspection_id: Optional[str] = None,
    limit: int = 50,
    sb: Client = Depends(get_supabase),
):
    return list_photos_flow(
        project_id=project_id,
        inspection_id=inspection_id,
        limit=limit,
        sb=sb,
    )


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str, sb: Client = Depends(get_supabase)):
    return delete_photo_flow(photo_id=photo_id, sb=sb)
