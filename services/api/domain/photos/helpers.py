"""Photo/media flow helpers used by routers and domain services."""

from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from supabase import Client

from services.api.domain.photos.flows import delete_photo_flow, list_photos_flow, upload_photo_flow


async def upload_photo(
    *,
    file: UploadFile,
    project_id: str,
    enterprise_id: str,
    location: str | None,
    inspection_id: str | None,
    gps_lat: float | None,
    gps_lng: float | None,
    sb: Client,
) -> dict[str, Any]:
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


def list_photos(*, project_id: str, inspection_id: str | None, limit: int, sb: Client) -> dict[str, Any]:
    return list_photos_flow(project_id=project_id, inspection_id=inspection_id, limit=limit, sb=sb)


def delete_photo(*, photo_id: str, sb: Client) -> dict[str, Any]:
    return delete_photo_flow(photo_id=photo_id, sb=sb)
