"""
Flow helpers for projects router.
"""

from __future__ import annotations

from typing import Any
import re

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.projects_autoreg_service import (
    complete_gitpeg_registration_flow,
    process_gitpeg_webhook,
    run_project_autoreg_sync_safe,
    sync_project_autoreg_flow,
)
from services.api.projects_create_flow_service import create_project_flow
from services.api.projects_gitpeg_client_service import (
    _gitpeg_create_registration_session,
    _gitpeg_exchange_token,
    _gitpeg_get_registration_result,
    _gitpeg_get_registration_session,
    _gitpeg_registrar_config,
    _gitpeg_registrar_ready,
    _to_bool,
)
from services.api.projects_profile_normalize_service import (
    _normalize_contract_segs,
    _normalize_inspection_types,
    _normalize_km_interval,
    _normalize_perm_template,
    _normalize_seg_type,
    _normalize_structures,
    _normalize_zero_equipment,
    _normalize_zero_materials,
    _normalize_zero_personnel,
    _normalize_zero_sign_status,
    _normalize_zero_subcontracts,
)
from services.api.projects_service import (
    delete_project_data,
    export_projects_csv_text,
    get_project_data,
    list_project_activity_data,
    list_projects_data,
    normalize_project_patch,
    update_project_data,
)
from services.api.autoreg_service import (
    AutoRegisterProjectRequest,
    normalize_request as _normalize_request,
    upsert_autoreg as _upsert_autoreg,
)
from services.api.erpnext_service import fetch_erpnext_project_basics


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
        normalize_request=_normalize_request,
        gitpeg_registrar_config=_gitpeg_registrar_config,
        gitpeg_registrar_ready=_gitpeg_registrar_ready,
        gitpeg_create_registration_session=_gitpeg_create_registration_session,
        upsert_autoreg=_upsert_autoreg,
    )


def list_projects_flow(*, enterprise_id: str, status: str | None, project_type: str | None, sb: Client) -> dict[str, Any]:
    data = list_projects_data(
        sb,
        enterprise_id=enterprise_id,
        status=status,
        project_type=project_type,
    )
    return {"data": data}


def list_activity_flow(*, enterprise_id: str, limit: int, sb: Client) -> dict[str, Any]:
    items = list_project_activity_data(
        sb,
        enterprise_id=enterprise_id,
        limit=limit,
    )
    return {"data": items}


def export_projects_csv_flow(*, enterprise_id: str, status: str | None, project_type: str | None, sb: Client) -> StreamingResponse:
    csv_text = export_projects_csv_text(
        sb,
        enterprise_id=enterprise_id,
        status=status,
        project_type=project_type,
    )
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="projects.csv"',
        },
    )


async def create_project_router_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return await create_project_flow(
        sb=sb,
        body=body,
        load_enterprise=load_enterprise,
        load_sync_custom=load_sync_custom,
        to_bool=_to_bool,
        slugify=slugify,
        fetch_erpnext_project_basics=fetch_erpnext_project_basics,
        run_project_autoreg_sync_safe=run_project_autoreg_sync_safe,
        sync_project_autoreg=sync_project_autoreg_internal,
        normalize_seg_type=_normalize_seg_type,
        normalize_km_interval=_normalize_km_interval,
        normalize_inspection_types=_normalize_inspection_types,
        normalize_contract_segs=_normalize_contract_segs,
        normalize_structures=_normalize_structures,
        normalize_zero_personnel=_normalize_zero_personnel,
        normalize_zero_equipment=_normalize_zero_equipment,
        normalize_zero_subcontracts=_normalize_zero_subcontracts,
        normalize_zero_materials=_normalize_zero_materials,
        normalize_zero_sign_status=_normalize_zero_sign_status,
        normalize_perm_template=_normalize_perm_template,
    )


async def sync_project_autoreg_endpoint_flow(*, project_id: str, body: Any, sb: Client) -> dict[str, Any]:
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


async def complete_project_gitpeg_registration_router_flow(*, project_id: str, body: Any, sb: Client) -> dict[str, Any]:
    return await complete_gitpeg_registration_flow(
        sb=sb,
        project_id=project_id,
        body=body,
        get_project_data=get_project_data,
        load_sync_custom=load_sync_custom,
        gitpeg_registrar_config=_gitpeg_registrar_config,
        gitpeg_registrar_ready=_gitpeg_registrar_ready,
        gitpeg_exchange_token=_gitpeg_exchange_token,
        gitpeg_get_registration_session=_gitpeg_get_registration_session,
        gitpeg_get_registration_result=_gitpeg_get_registration_result,
        load_enterprise=load_enterprise,
        normalize_request=_normalize_request,
        build_autoreg_input=build_autoreg_input,
        to_bool=_to_bool,
    )


async def gitpeg_registrar_webhook_router_flow(*, request: Request, sb: Client) -> dict[str, Any]:
    return await process_gitpeg_webhook(
        request=request,
        sb=sb,
        get_project_data=get_project_data,
        load_enterprise=load_enterprise,
        normalize_request=_normalize_request,
        build_autoreg_input=build_autoreg_input,
        load_sync_custom=load_sync_custom,
        gitpeg_registrar_config=_gitpeg_registrar_config,
        gitpeg_registrar_ready=_gitpeg_registrar_ready,
        gitpeg_exchange_token=_gitpeg_exchange_token,
        gitpeg_get_registration_session=_gitpeg_get_registration_session,
        gitpeg_get_registration_result=_gitpeg_get_registration_result,
        to_bool=_to_bool,
    )


def get_project_flow(*, project_id: str, sb: Client) -> dict[str, Any]:
    data = get_project_data(sb, project_id=project_id)
    if not data:
        raise HTTPException(404, "project not found")
    return data


def update_project_flow(*, project_id: str, updates: dict[str, Any], sb: Client) -> dict[str, Any]:
    patch = normalize_project_patch(
        updates,
        normalize_seg_type=_normalize_seg_type,
        normalize_perm_template=_normalize_perm_template,
        normalize_km_interval=_normalize_km_interval,
        normalize_inspection_types=_normalize_inspection_types,
        normalize_contract_segs=_normalize_contract_segs,
        normalize_structures=_normalize_structures,
        normalize_zero_personnel=_normalize_zero_personnel,
        normalize_zero_equipment=_normalize_zero_equipment,
        normalize_zero_subcontracts=_normalize_zero_subcontracts,
        normalize_zero_materials=_normalize_zero_materials,
        normalize_zero_sign_status=_normalize_zero_sign_status,
    )
    return update_project_data(
        sb,
        project_id=project_id,
        patch=patch,
    )


def delete_project_flow(*, project_id: str, enterprise_id: str | None, sb: Client) -> dict[str, Any]:
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
