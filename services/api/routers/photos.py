"""
QCSpec media evidence routes.
services/api/routers/photos.py
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from services.api.dependencies import get_photos_service
from services.api.domain import PhotosService

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
    photos_service: PhotosService = Depends(get_photos_service),
):
    return await photos_service.upload_photo(
        file=file,
        project_id=project_id,
        enterprise_id=enterprise_id,
        location=location,
        inspection_id=inspection_id,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
    )


@router.get("/")
async def list_photos(
    project_id: str,
    inspection_id: Optional[str] = None,
    limit: int = 50,
    photos_service: PhotosService = Depends(get_photos_service),
):
    return await photos_service.list_photos(
        project_id=project_id,
        inspection_id=inspection_id,
        limit=limit,
    )


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str, photos_service: PhotosService = Depends(get_photos_service)):
    return await photos_service.delete_photo(photo_id=photo_id)
