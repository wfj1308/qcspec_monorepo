"""Canonical projects create flow orchestration."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from supabase import Client

from services.api.domain.projects.persistence import (
    create_project_record,
    reconcile_created_project,
)
from services.api.domain.projects.payloads import build_project_create_payload


async def create_project_flow(
    *,
    sb: Client,
    body: Any,
    load_enterprise: Callable[[Client, str], dict[str, Any]],
    load_sync_custom: Callable[[Client, str], dict[str, Any]],
    to_bool: Callable[[Any], bool],
    slugify: Callable[[str], str],
    fetch_erpnext_project_basics: Callable[..., Awaitable[dict[str, Any]]],
    run_project_autoreg_sync_safe: Callable[..., Awaitable[dict[str, Any]]],
    sync_project_autoreg: Callable[..., Awaitable[dict[str, Any]]],
    normalize_seg_type: Callable[[Any], str],
    normalize_km_interval: Callable[[Any], int],
    normalize_inspection_types: Callable[[Any], list[str]],
    normalize_contract_segs: Callable[[Any], list[dict[str, Any]]],
    normalize_structures: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_personnel: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_equipment: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_subcontracts: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_materials: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_sign_status: Callable[[Any], str],
    normalize_perm_template: Callable[[Any], str],
) -> dict[str, Any]:
    enterprise = load_enterprise(sb, body.enterprise_id)
    root_uri = str(enterprise.get("v_uri") or "").strip() or "v://cn.enterprise/"
    if not root_uri.endswith("/"):
        root_uri += "/"

    slug = slugify(body.name)
    v_uri = f"{root_uri}{body.type}/{slug}/"
    exist = sb.table("projects").select("id").eq("v_uri", v_uri).execute()
    if exist.data:
        raise HTTPException(409, f"node already exists: {v_uri}")

    custom = load_sync_custom(sb, body.enterprise_id)
    erp_project_basics: dict[str, Any] = {
        "attempted": False,
        "success": False,
        "reason": "erpnext_sync_disabled",
    }
    basics_patch: dict[str, str] = {}
    erp_sync_enabled = to_bool(custom.get("erpnext_sync"))
    if erp_sync_enabled:
        erp_lookup_code = str(body.erp_project_code or "").strip() or None
        erp_lookup_name = str(body.erp_project_name or "").strip() or None
        if not erp_lookup_code:
            raise HTTPException(422, "erp_project_binding_required:missing_project_code")
        try:
            basics_res = await fetch_erpnext_project_basics(
                custom,
                project_code=erp_lookup_code,
                project_name=erp_lookup_name,
            )
            erp_project_basics = {
                "attempted": bool(basics_res.get("attempted", True)),
                "success": bool(basics_res.get("success")),
            }
            if basics_res.get("success"):
                raw_patch = basics_res.get("project_basics")
                if isinstance(raw_patch, dict):
                    basics_patch = {
                        key: str(value).strip()
                        for key, value in raw_patch.items()
                        if str(value or "").strip()
                    }
                    erp_project_basics["project_basics"] = basics_patch
            else:
                erp_project_basics["reason"] = basics_res.get("reason") or basics_res.get("errors")
        except Exception as exc:
            erp_project_basics = {
                "attempted": True,
                "success": False,
                "reason": f"erpnext_project_basics_error:{exc.__class__.__name__}",
            }
        if not erp_project_basics.get("success"):
            reason = str(erp_project_basics.get("reason") or "erp_project_basics_required")
            raise HTTPException(422, f"erp_project_binding_required:{reason}")

    create_payload = build_project_create_payload(
        body,
        v_uri=v_uri,
        enterprise_name=str(enterprise.get("name") or "").strip(),
        basics_patch=basics_patch,
        erp_sync_enabled=erp_sync_enabled,
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
    erp_project_code = create_payload.get("erp_project_code")
    erp_project_name = create_payload.get("erp_project_name")
    if erp_sync_enabled and not erp_project_code:
        raise HTTPException(422, "erp_project_binding_required:missing_project_code")
    if erp_sync_enabled and not erp_project_name:
        raise HTTPException(422, "erp_project_binding_required:missing_project_name")

    rec = dict(create_payload.get("record") or {})
    zero_ledger_patch = dict(create_payload.get("zero_ledger_patch") or {})
    proj = create_project_record(
        sb,
        record=rec,
        erp_sync_enabled=erp_sync_enabled,
    )
    proj = reconcile_created_project(
        sb,
        project_row=proj,
        zero_ledger_patch=zero_ledger_patch,
        erp_sync_enabled=erp_sync_enabled,
        erp_project_code=erp_project_code,
        erp_project_name=erp_project_name,
    )

    sync_result = await run_project_autoreg_sync_safe(
        sb=sb,
        project=proj,
        force=False,
        writeback=True,
        sync_project_autoreg=sync_project_autoreg,
        include_http_exception_detail=False,
    )
    return {
        "id": proj["id"],
        "v_uri": proj["v_uri"],
        "name": proj["name"],
        "erp_project_code": proj.get("erp_project_code"),
        "erp_project_name": proj.get("erp_project_name"),
        "erp_project_basics": erp_project_basics,
        "autoreg_sync": sync_result,
    }


__all__ = ["create_project_flow"]
