"""LogPeg flow entrypoints."""

from __future__ import annotations

from typing import Any

from services.api.domain.logpeg.models import LogPegSignRequest
from services.api.domain.logpeg.runtime import LogPegEngine


def _project_uri_from_id(sb: Any, project_id: str) -> str:
    rows = sb.table("projects").select("id,v_uri").eq("id", str(project_id or "").strip()).limit(1).execute().data or []
    if not rows:
        return ""
    row = rows[0] if isinstance(rows[0], dict) else {}
    return str(row.get("v_uri") or "").strip().rstrip("/")


async def daily_log_flow(
    *,
    sb: Any,
    project_id: str,
    date: str,
    weather: str = "",
    temperature_range: str = "",
    wind_level: str = "",
    language: str = "zh",
) -> dict[str, Any]:
    project_uri = _project_uri_from_id(sb, project_id)
    engine = LogPegEngine(sb=sb)
    out = await engine.generate_daily_log(
        project_uri=project_uri,
        log_date=date,
        weather=weather,
        temperature_range=temperature_range,
        wind_level=wind_level,
        language=language,
    )
    return {"ok": True, "log": out.model_dump(mode="json")}


async def weekly_log_flow(*, sb: Any, project_id: str, week_start: str, language: str = "zh") -> dict[str, Any]:
    project_uri = _project_uri_from_id(sb, project_id)
    engine = LogPegEngine(sb=sb)
    out = await engine.generate_weekly_log(project_uri=project_uri, week_start=week_start, language=language)
    return {"ok": True, **out.model_dump(mode="json")}


async def monthly_log_flow(*, sb: Any, project_id: str, month: str, language: str = "zh") -> dict[str, Any]:
    project_uri = _project_uri_from_id(sb, project_id)
    engine = LogPegEngine(sb=sb)
    out = await engine.generate_monthly_log(project_uri=project_uri, year_month=month, language=language)
    return {"ok": True, **out.model_dump(mode="json")}


async def sign_daily_log_flow(*, sb: Any, project_id: str, body: LogPegSignRequest) -> dict[str, Any]:
    project_uri = _project_uri_from_id(sb, project_id)
    engine = LogPegEngine(sb=sb)
    out = await engine.sign_daily_log(
        project_uri=project_uri,
        log_date=body.date,
        executor_uri=body.executor_uri,
        signed_by=body.signed_by,
        weather=body.weather,
        temperature_range=body.temperature_range,
        wind_level=body.wind_level,
        language=body.language,
    )
    return {
        "ok": True,
        "v_uri": out.v_uri,
        "data_hash": out.data_hash,
        "sign_proof": out.sign_proof,
        "log": out.model_dump(mode="json"),
    }


async def export_daily_flow(*, sb: Any, project_id: str, date: str, format: str = "pdf", language: str = "zh") -> tuple[bytes, str, str]:
    project_uri = _project_uri_from_id(sb, project_id)
    engine = LogPegEngine(sb=sb)
    return await engine.export_daily_log(project_uri=project_uri, log_date=date, format=format, language=language)
