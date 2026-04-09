"""LogPeg routes: daily/weekly/monthly auto log generation and export."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import StreamingResponse

from services.api.dependencies import get_logpeg_service
from services.api.domain import LogPegService
from services.api.domain.logpeg.models import LogPegSignRequest

router = APIRouter()


def _sign_body_with_date(raw: dict[str, Any], date: str) -> LogPegSignRequest:
    payload = dict(raw or {})
    payload["date"] = date
    return LogPegSignRequest.model_validate(payload)


@router.get("/api/v1/logpeg/{project_id}/daily")
async def logpeg_daily_v2(
    project_id: str,
    date: str = Query(..., description="YYYY-MM-DD"),
    weather: str = "",
    temperature_range: str = "",
    wind_level: str = "",
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    return await logpeg_service.daily(
        project_id=project_id,
        date=date,
        weather=weather,
        temperature_range=temperature_range,
        wind_level=wind_level,
        language=language,
    )


@router.get("/api/v1/logpeg/{project_id}/weekly")
async def logpeg_weekly_v2(
    project_id: str,
    week_start: str = Query(..., description="YYYY-MM-DD"),
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    return await logpeg_service.weekly(project_id=project_id, week_start=week_start, language=language)


@router.get("/api/v1/logpeg/{project_id}/monthly")
async def logpeg_monthly_v2(
    project_id: str,
    month: str = Query(..., description="YYYY-MM"),
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    return await logpeg_service.monthly(project_id=project_id, month=month, language=language)


@router.post("/api/v1/logpeg/{project_id}/daily/sign")
async def logpeg_sign_v2(
    project_id: str,
    body: LogPegSignRequest = Body(...),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    return await logpeg_service.sign(project_id=project_id, body=body)


@router.get("/api/v1/logpeg/{project_id}/daily/export")
async def logpeg_export_v2(
    project_id: str,
    date: str = Query(..., description="YYYY-MM-DD"),
    format: str = Query("pdf", pattern="^(pdf|word|json)$"),
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    payload, filename, content_type = await logpeg_service.export(project_id=project_id, date=date, format=format, language=language)
    return StreamingResponse(
        iter([payload]),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# legacy compatibility routes
@router.get("/api/v1/logpeg/daily/{project_id}")
async def logpeg_daily_legacy(
    project_id: str,
    date: str = Query(...),
    weather: str = "",
    temperature: str = "",
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    return await logpeg_service.daily(project_id=project_id, date=date, weather=weather, temperature_range=temperature, language=language)


@router.get("/api/v1/logpeg/weekly/{project_id}")
async def logpeg_weekly_legacy(
    project_id: str,
    week_start: str = Query(...),
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    return await logpeg_service.weekly(project_id=project_id, week_start=week_start, language=language)


@router.get("/api/v1/logpeg/monthly/{project_id}")
async def logpeg_monthly_legacy(
    project_id: str,
    month: str = Query(...),
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    return await logpeg_service.monthly(project_id=project_id, month=month, language=language)


@router.post("/api/v1/logpeg/sign/{project_id}")
async def logpeg_sign_legacy(
    project_id: str,
    date: str = Query(...),
    body: dict[str, Any] = Body(default_factory=dict),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    sign_body = _sign_body_with_date(body, date)
    return await logpeg_service.sign(project_id=project_id, body=sign_body)


@router.get("/api/v1/logpeg/export/{project_id}")
async def logpeg_export_legacy(
    project_id: str,
    date: str = Query(...),
    format: str = Query("pdf", pattern="^(pdf|word|json)$"),
    language: str = Query("zh", pattern="^(zh|en)$"),
    logpeg_service: LogPegService = Depends(get_logpeg_service),
):
    payload, filename, content_type = await logpeg_service.export(project_id=project_id, date=date, format=format, language=language)
    return StreamingResponse(iter([payload]), media_type=content_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
