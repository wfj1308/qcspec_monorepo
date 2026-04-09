"""LogPeg service helper wrappers."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.logpeg.flows import (
    daily_log_flow,
    export_daily_flow,
    monthly_log_flow,
    sign_daily_log_flow,
    weekly_log_flow,
)


async def logpeg_daily_service_flow(
    *,
    sb: Client,
    project_id: str,
    date: str,
    weather: str = "",
    temperature_range: str = "",
    wind_level: str = "",
    language: str = "zh",
) -> dict[str, Any]:
    return await daily_log_flow(
        sb=sb,
        project_id=project_id,
        date=date,
        weather=weather,
        temperature_range=temperature_range,
        wind_level=wind_level,
        language=language,
    )


async def logpeg_weekly_service_flow(*, sb: Client, project_id: str, week_start: str, language: str = "zh") -> dict[str, Any]:
    return await weekly_log_flow(sb=sb, project_id=project_id, week_start=week_start, language=language)


async def logpeg_monthly_service_flow(*, sb: Client, project_id: str, month: str, language: str = "zh") -> dict[str, Any]:
    return await monthly_log_flow(sb=sb, project_id=project_id, month=month, language=language)


async def logpeg_sign_service_flow(*, sb: Client, project_id: str, body: Any) -> dict[str, Any]:
    return await sign_daily_log_flow(sb=sb, project_id=project_id, body=body)


async def logpeg_export_service_flow(*, sb: Client, project_id: str, date: str, format: str = "pdf", language: str = "zh") -> tuple[bytes, str, str]:
    return await export_daily_flow(sb=sb, project_id=project_id, date=date, format=format, language=language)
