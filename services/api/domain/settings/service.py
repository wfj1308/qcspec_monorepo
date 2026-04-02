"""Enterprise settings domain facade."""

from __future__ import annotations

from typing import Any

from fastapi import UploadFile
from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.settings.connection import (
    test_erpnext_connection_flow,
    test_gitpeg_registrar_connection_flow,
)
from services.api.domain.settings.flows import (
    get_settings_flow,
    update_settings_flow,
    upload_template_flow,
)


class SettingsService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def get_settings(self, *, enterprise_id: str) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded("get_settings", get_settings_flow, enterprise_id=enterprise_id, sb=supabase)

    async def upload_template(self, *, enterprise_id: str, file: UploadFile) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "upload_template",
            upload_template_flow,
            enterprise_id=enterprise_id,
            file=file,
            sb=supabase,
        )

    async def test_erpnext_connection(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "test_erpnext_connection",
            test_erpnext_connection_flow,
            body=body,
        )

    async def test_gitpeg_registrar_connection(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "test_gitpeg_registrar_connection",
            test_gitpeg_registrar_connection_flow,
            body=body,
        )

    async def update_settings(self, *, enterprise_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "update_settings",
            update_settings_flow,
            enterprise_id=enterprise_id,
            body=body,
            sb=supabase,
        )
