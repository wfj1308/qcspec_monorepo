"""Photo/media domain facade."""

from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.photos.helpers import delete_photo, list_photos, upload_photo


class PhotosService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def upload_photo(
        self,
        *,
        file: UploadFile,
        project_id: str,
        enterprise_id: str,
        location: str | None,
        inspection_id: str | None,
        gps_lat: float | None,
        gps_lng: float | None,
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "upload_photo",
            upload_photo,
            file=file,
            project_id=project_id,
            enterprise_id=enterprise_id,
            location=location,
            inspection_id=inspection_id,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            sb=supabase,
        )

    async def list_photos(self, *, project_id: str, inspection_id: str | None, limit: int) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "list_photos",
            list_photos,
            project_id=project_id,
            inspection_id=inspection_id,
            limit=limit,
            sb=supabase,
        )

    async def delete_photo(self, *, photo_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("delete_photo", delete_photo, photo_id=photo_id, sb=supabase)
