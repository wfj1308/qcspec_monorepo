"""Reporting flow helpers used by routers and domain services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from supabase import Client

from services.api.domain.reporting.flows import (
    export_report_by_proof_id_flow,
    export_report_flow,
    generate_report_flow,
    get_report_flow,
    list_reports_flow,
)

_DEFAULT_REPORT_TYPE = "inspection"
_DEFAULT_EXPORT_FORMAT = "docx"
_ALLOWED_EXPORT_FORMATS = {"docx", "pdf"}


@dataclass(slots=True)
class _ReportExportPayload:
    project_id: str
    enterprise_id: str
    type: str
    format: str
    location: str | None
    date_from: str | None
    date_to: str | None


@dataclass(slots=True)
class _ReportGeneratePayload:
    project_id: str
    enterprise_id: str
    location: str | None
    date_from: str | None
    date_to: str | None


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _to_optional_text(value: Any) -> str | None:
    text = _to_text(value)
    return text or None


def _read_attr(body: Any, name: str, default: Any = None) -> Any:
    if body is None:
        return default
    return getattr(body, name, default)


def _require_attr_text(body: Any, name: str) -> str:
    value = _to_text(_read_attr(body, name))
    if not value:
        raise HTTPException(400, f"{name} is required")
    return value


def _normalize_export_format(value: Any) -> str:
    fmt = _to_text(value, _DEFAULT_EXPORT_FORMAT).lower() or _DEFAULT_EXPORT_FORMAT
    if fmt not in _ALLOWED_EXPORT_FORMATS:
        raise HTTPException(400, "format must be docx or pdf")
    return fmt


async def export_report(*, body: Any, sb: Client) -> dict[str, Any]:
    payload = _ReportExportPayload(
        project_id=_require_attr_text(body, "project_id"),
        enterprise_id=_require_attr_text(body, "enterprise_id"),
        type=_to_text(_read_attr(body, "type"), _DEFAULT_REPORT_TYPE) or _DEFAULT_REPORT_TYPE,
        format=_normalize_export_format(_read_attr(body, "format", _DEFAULT_EXPORT_FORMAT)),
        location=_to_optional_text(_read_attr(body, "location")),
        date_from=_to_optional_text(_read_attr(body, "date_from")),
        date_to=_to_optional_text(_read_attr(body, "date_to")),
    )
    return await export_report_flow(body=payload, sb=sb)


async def export_report_by_proof_id(
    *,
    proof_id: str,
    format: str,
    report_type: str,
    sb: Client,
) -> Any:
    normalized_proof_id = _to_text(proof_id)
    if not normalized_proof_id:
        raise HTTPException(400, "proof_id is required")
    return await export_report_by_proof_id_flow(
        proof_id=normalized_proof_id,
        format=_normalize_export_format(format),
        report_type=_to_text(report_type, _DEFAULT_REPORT_TYPE) or _DEFAULT_REPORT_TYPE,
        sb=sb,
    )


async def generate_report(*, body: Any, background_tasks: Any, sb: Client) -> dict[str, Any]:
    payload = _ReportGeneratePayload(
        project_id=_require_attr_text(body, "project_id"),
        enterprise_id=_require_attr_text(body, "enterprise_id"),
        location=_to_optional_text(_read_attr(body, "location")),
        date_from=_to_optional_text(_read_attr(body, "date_from")),
        date_to=_to_optional_text(_read_attr(body, "date_to")),
    )
    return await generate_report_flow(body=payload, background_tasks=background_tasks, sb=sb)


def list_reports(*, project_id: str, sb: Client) -> dict[str, Any]:
    normalized_project_id = _to_text(project_id)
    if not normalized_project_id:
        raise HTTPException(400, "project_id is required")
    return list_reports_flow(project_id=normalized_project_id, sb=sb)


def get_report(*, report_id: str, sb: Client) -> dict[str, Any]:
    normalized_report_id = _to_text(report_id)
    if not normalized_report_id:
        raise HTTPException(400, "report_id is required")
    return get_report_flow(report_id=normalized_report_id, sb=sb)
