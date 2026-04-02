"""Projects router flow helpers used by domain services."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.domain.projects.router_flows import (
    complete_project_gitpeg_registration_flow,
    create_project_router_domain_flow,
    delete_project_router_flow,
    export_projects_csv_router_flow,
    get_project_router_flow,
    gitpeg_registrar_webhook_flow,
    list_activity_router_flow,
    list_projects_router_flow,
    sync_project_autoreg_router_flow,
    update_project_router_flow,
)

_ACTIVITY_LIMIT_MIN = 1
_ACTIVITY_LIMIT_MAX = 200


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


def _require_text(value: Any, *, field: str) -> str:
    text = _to_text(value)
    if not text:
        raise HTTPException(400, f"{field} is required")
    return text


def _clamp_activity_limit(value: int) -> int:
    try:
        iv = int(value)
    except Exception:
        iv = 20
    if iv < _ACTIVITY_LIMIT_MIN:
        return _ACTIVITY_LIMIT_MIN
    if iv > _ACTIVITY_LIMIT_MAX:
        return _ACTIVITY_LIMIT_MAX
    return iv


def list_projects(*, enterprise_id: str, status: str | None, project_type: str | None, sb: Client) -> dict[str, Any]:
    return list_projects_router_flow(
        enterprise_id=_require_text(enterprise_id, field="enterprise_id"),
        status=_to_optional_text(status),
        project_type=_to_optional_text(project_type),
        sb=sb,
    )


def list_activity(*, enterprise_id: str, limit: int, sb: Client) -> dict[str, Any]:
    return list_activity_router_flow(
        enterprise_id=_require_text(enterprise_id, field="enterprise_id"),
        limit=_clamp_activity_limit(limit),
        sb=sb,
    )


def export_projects_csv(
    *,
    enterprise_id: str,
    status: str | None,
    project_type: str | None,
    sb: Client,
) -> StreamingResponse:
    return export_projects_csv_router_flow(
        enterprise_id=_require_text(enterprise_id, field="enterprise_id"),
        status=_to_optional_text(status),
        project_type=_to_optional_text(project_type),
        sb=sb,
    )


async def create_project(*, body: Any, sb: Client) -> dict[str, Any]:
    if body is None:
        raise HTTPException(400, "body is required")
    _require_text(_read_attr(body, "enterprise_id"), field="enterprise_id")
    _require_text(_read_attr(body, "name"), field="name")
    _require_text(_read_attr(body, "type"), field="type")
    return await create_project_router_domain_flow(body=body, sb=sb)


async def sync_project_autoreg(*, project_id: str, body: Any, sb: Client) -> dict[str, Any]:
    return await sync_project_autoreg_router_flow(
        project_id=_require_text(project_id, field="project_id"),
        body=body,
        sb=sb,
    )


async def complete_project_gitpeg_registration(*, project_id: str, body: Any, sb: Client) -> dict[str, Any]:
    if body is None:
        raise HTTPException(400, "body is required")
    _require_text(_read_attr(body, "code"), field="code")
    return await complete_project_gitpeg_registration_flow(
        project_id=_require_text(project_id, field="project_id"),
        body=body,
        sb=sb,
    )


async def gitpeg_registrar_webhook(*, request: Request, sb: Client) -> dict[str, Any]:
    return await gitpeg_registrar_webhook_flow(request=request, sb=sb)


def get_project(*, project_id: str, sb: Client) -> dict[str, Any]:
    return get_project_router_flow(project_id=_require_text(project_id, field="project_id"), sb=sb)


def update_project(*, project_id: str, updates: dict[str, Any], sb: Client) -> dict[str, Any]:
    patch = updates if isinstance(updates, dict) else {}
    if not patch:
        raise HTTPException(400, "updates is required")
    return update_project_router_flow(
        project_id=_require_text(project_id, field="project_id"),
        updates=patch,
        sb=sb,
    )


def delete_project(*, project_id: str, enterprise_id: str | None, sb: Client) -> dict[str, Any]:
    return delete_project_router_flow(
        project_id=_require_text(project_id, field="project_id"),
        enterprise_id=_to_optional_text(enterprise_id),
        sb=sb,
    )
