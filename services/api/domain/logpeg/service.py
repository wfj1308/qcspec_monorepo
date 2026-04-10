"""LogPeg domain facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.logpeg.helpers import (
    logpeg_daily_service_flow,
    logpeg_export_service_flow,
    logpeg_monthly_service_flow,
    logpeg_sign_service_flow,
    logpeg_weekly_service_flow,
)


class LogPegService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def daily(
        self,
        *,
        project_id: str,
        date: str,
        weather: str = "",
        temperature_range: str = "",
        wind_level: str = "",
        language: str = "zh",
    ) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "logpeg_daily",
            logpeg_daily_service_flow,
            sb=supabase,
            project_id=project_id,
            date=date,
            weather=weather,
            temperature_range=temperature_range,
            wind_level=wind_level,
            language=language,
        )

    async def weekly(self, *, project_id: str, week_start: str, language: str = "zh") -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "logpeg_weekly",
            logpeg_weekly_service_flow,
            sb=supabase,
            project_id=project_id,
            week_start=week_start,
            language=language,
        )

    async def monthly(self, *, project_id: str, month: str, language: str = "zh") -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "logpeg_monthly",
            logpeg_monthly_service_flow,
            sb=supabase,
            project_id=project_id,
            month=month,
            language=language,
        )

    async def sign(self, *, project_id: str, body: Any) -> Any:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "logpeg_sign",
            logpeg_sign_service_flow,
            sb=supabase,
            project_id=project_id,
            body=body,
        )

    async def export(self, *, project_id: str, date: str, format: str = "pdf", language: str = "zh") -> tuple[bytes, str, str]:
        supabase = self.require_supabase()
        return await self.run_guarded(
            "logpeg_export",
            logpeg_export_service_flow,
            sb=supabase,
            project_id=project_id,
            date=date,
            format=format,
            language=language,
        )
