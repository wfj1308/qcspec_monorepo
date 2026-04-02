"""Canonical projects-domain router flow entry points.

This module keeps domain callers decoupled from router-layer modules and
implements stable CRUD/export flows directly. Complex GitPeg orchestration
still delegates to legacy flow composition to preserve behavior.
"""

from __future__ import annotations

from typing import Any
import re

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.domain.projects.flows import (
    AutoRegisterProjectRequest,
    complete_gitpeg_registration_flow,
    create_project_flow,
    delete_project_data,
    export_projects_csv_text,
    fetch_erpnext_project_basics,
    gitpeg_create_registration_session,
    gitpeg_exchange_token,
    gitpeg_get_registration_result,
    gitpeg_get_registration_session,
    gitpeg_registrar_config,
    gitpeg_registrar_ready,
    get_project_data,
    list_project_activity_data,
    list_projects_data,
    normalize_contract_segs,
    normalize_inspection_types,
    normalize_km_interval,
    normalize_perm_template,
    normalize_project_patch,
    normalize_request,
    normalize_seg_type,
    normalize_structures,
    normalize_zero_equipment,
    normalize_zero_materials,
    normalize_zero_personnel,
    normalize_zero_sign_status,
    normalize_zero_subcontracts,
    process_gitpeg_webhook,
    run_project_autoreg_sync_safe,
    sync_project_autoreg_flow,
    to_bool,
    update_project_data,
    upsert_autoreg,
)

__all__ = [
    "list_projects_router_flow",
    "list_activity_router_flow",
    "export_projects_csv_router_flow",
    "create_project_router_domain_flow",
    "sync_project_autoreg_router_flow",
    "complete_project_gitpeg_registration_flow",
    "gitpeg_registrar_webhook_flow",
    "get_project_router_flow",
    "update_project_router_flow",
    "delete_project_router_flow",
]


def slugify(name: str) -> str:
    raw = str(name or "").strip().lower()
    compact = re.sub(r"\s+", "", raw, flags=re.UNICODE)
    return re.sub(r"[^\w-]+", "", compact, flags=re.UNICODE)[:20] or "project"


def load_enterprise(sb: Client, enterprise_id: str) -> dict[str, Any]:
    ent = sb.table("enterprises").select("id,v_uri,name").eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")
    return ent.data


def load_sync_custom(sb: Client, enterprise_id: str) -> dict[str, Any]:
    cfg = (
        sb.table("enterprise_configs")
        .select("custom_fields")
        .eq("enterprise_id", enterprise_id)
        .limit(1)
        .execute()
    )
    if not cfg.data:
        return {}
    custom = cfg.data[0].get("custom_fields") or {}
    return custom if isinstance(custom, dict) else {}


def autoreg_enabled(custom: dict[str, Any]) -> bool:
    return bool(custom.get("erpnext_sync") or custom.get("gitpeg_enabled"))


def build_autoreg_input(project: dict[str, Any], enterprise: dict[str, Any]) -> AutoRegisterProjectRequest:
    project_name = str(project.get("name") or "").strip()
    project_code = (
        str(project.get("erp_project_code") or "").strip()
        or str(project.get("contract_no") or "").strip()
        or str(project.get("id") or "").strip()
    )
    site_code = slugify(project_name)
    site_name = project_name
    namespace_uri = str(enterprise.get("v_uri") or "").strip() or None
    return AutoRegisterProjectRequest(
        project_code=project_code,
        project_name=project_name,
        site_code=site_code,
        site_name=site_name,
        namespace_uri=namespace_uri,
        source_system="qcspec",
    )


async def sync_project_autoreg_internal(
    *,
    sb: Client,
    project: dict[str, Any],
    force: bool = False,
    writeback: bool = True,
) -> dict[str, Any]:
    return await sync_project_autoreg_flow(
        sb=sb,
        project=project,
        force=force,
        writeback=writeback,
        load_sync_custom=load_sync_custom,
        autoreg_enabled=autoreg_enabled,
        load_enterprise=load_enterprise,
        build_autoreg_input=build_autoreg_input,
        normalize_request=normalize_request,
        gitpeg_registrar_config=gitpeg_registrar_config,
        gitpeg_registrar_ready=gitpeg_registrar_ready,
        gitpeg_create_registration_session=gitpeg_create_registration_session,
        upsert_autoreg=upsert_autoreg,
    )


def list_projects_router_flow(
    *,
    enterprise_id: str,
    status: str | None,
    project_type: str | None,
    sb: Client,
) -> dict[str, Any]:
    data = list_projects_data(
        sb,
        enterprise_id=enterprise_id,
        status=status,
        project_type=project_type,
    )
    return {"data": data}


def list_activity_router_flow(*, enterprise_id: str, limit: int, sb: Client) -> dict[str, Any]:
    items = list_project_activity_data(
        sb,
        enterprise_id=enterprise_id,
        limit=limit,
    )
    return {"data": items}


def export_projects_csv_router_flow(
    *,
    enterprise_id: str,
    status: str | None,
    project_type: str | None,
    sb: Client,
) -> StreamingResponse:
    csv_text = export_projects_csv_text(
        sb,
        enterprise_id=enterprise_id,
        status=status,
        project_type=project_type,
    )
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="projects.csv"'},
    )


async def create_project_router_domain_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return await create_project_flow(
        sb=sb,
        body=body,
        load_enterprise=load_enterprise,
        load_sync_custom=load_sync_custom,
        to_bool=to_bool,
        slugify=slugify,
        fetch_erpnext_project_basics=fetch_erpnext_project_basics,
        run_project_autoreg_sync_safe=run_project_autoreg_sync_safe,
        sync_project_autoreg=sync_project_autoreg_internal,
        normalize_seg_type=normalize_seg_type,
        normalize_km_interval=normalize_km_interval,
        normalize_inspection_types=normalize_inspection_types,
        normalize_contract_segs=normalize_contract_segs,
        normalize_structures=normalize_structures,
        normalize_zero_personnel=normalize_zero_personnel,
        normalize_zero_equipment=normalize_zero_equipment,
        normalize_zero_subcontracts=normalize_zero_subcontracts,
        normalize_zero_materials=normalize_zero_materials,
        normalize_zero_sign_status=normalize_zero_sign_status,
        normalize_perm_template=normalize_perm_template,
    )


async def sync_project_autoreg_router_flow(*, project_id: str, body: Any, sb: Client) -> dict[str, Any]:
    enterprise_id = str(getattr(body, "enterprise_id", "") or "").strip() or None
    force = bool(getattr(body, "force", True))
    writeback = bool(getattr(body, "writeback", True))

    project = get_project_data(
        sb,
        project_id=project_id,
        enterprise_id=enterprise_id,
    )
    if not project:
        raise HTTPException(404, "project not found")

    result = await run_project_autoreg_sync_safe(
        sb=sb,
        project=project,
        force=force,
        writeback=writeback,
        sync_project_autoreg=sync_project_autoreg_internal,
        include_http_exception_detail=True,
    )
    return {
        "ok": bool(result.get("success")),
        "project_id": project_id,
        "result": result,
    }


async def complete_project_gitpeg_registration_flow(*, project_id: str, body: Any, sb: Client) -> dict[str, Any]:
    return await complete_gitpeg_registration_flow(
        sb=sb,
        project_id=project_id,
        body=body,
        get_project_data=get_project_data,
        load_sync_custom=load_sync_custom,
        gitpeg_registrar_config=gitpeg_registrar_config,
        gitpeg_registrar_ready=gitpeg_registrar_ready,
        gitpeg_exchange_token=gitpeg_exchange_token,
        gitpeg_get_registration_session=gitpeg_get_registration_session,
        gitpeg_get_registration_result=gitpeg_get_registration_result,
        load_enterprise=load_enterprise,
        normalize_request=normalize_request,
        build_autoreg_input=build_autoreg_input,
        to_bool=to_bool,
    )


async def gitpeg_registrar_webhook_flow(*, request: Request, sb: Client) -> dict[str, Any]:
    return await process_gitpeg_webhook(
        request=request,
        sb=sb,
        get_project_data=get_project_data,
        load_enterprise=load_enterprise,
        normalize_request=normalize_request,
        build_autoreg_input=build_autoreg_input,
        load_sync_custom=load_sync_custom,
        gitpeg_registrar_config=gitpeg_registrar_config,
        gitpeg_registrar_ready=gitpeg_registrar_ready,
        gitpeg_exchange_token=gitpeg_exchange_token,
        gitpeg_get_registration_session=gitpeg_get_registration_session,
        gitpeg_get_registration_result=gitpeg_get_registration_result,
        to_bool=to_bool,
    )


def get_project_router_flow(*, project_id: str, sb: Client) -> dict[str, Any]:
    data = get_project_data(sb, project_id=project_id)
    if not data:
        raise HTTPException(404, "project not found")
    return data


def update_project_router_flow(*, project_id: str, updates: dict[str, Any], sb: Client) -> dict[str, Any]:
    patch = normalize_project_patch(
        updates,
        normalize_seg_type=normalize_seg_type,
        normalize_perm_template=normalize_perm_template,
        normalize_km_interval=normalize_km_interval,
        normalize_inspection_types=normalize_inspection_types,
        normalize_contract_segs=normalize_contract_segs,
        normalize_structures=normalize_structures,
        normalize_zero_personnel=normalize_zero_personnel,
        normalize_zero_equipment=normalize_zero_equipment,
        normalize_zero_subcontracts=normalize_zero_subcontracts,
        normalize_zero_materials=normalize_zero_materials,
        normalize_zero_sign_status=normalize_zero_sign_status,
    )
    return update_project_data(
        sb,
        project_id=project_id,
        patch=patch,
    )


def delete_project_router_flow(*, project_id: str, enterprise_id: str | None, sb: Client) -> dict[str, Any]:
    result = delete_project_data(
        sb,
        project_id=project_id,
        enterprise_id=enterprise_id,
    )
    if not result.get("found"):
        raise HTTPException(404, "project not found")
    if not result.get("deleted"):
        raise HTTPException(500, "failed to delete project")
    return {"ok": True, "id": project_id}
