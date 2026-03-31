"""
Project autoreg / gitpeg orchestration service helpers.
services/api/projects_autoreg_service.py
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from supabase import Client

from services.api.projects_autoreg_completion_service import (
    complete_gitpeg_registration_flow,
    process_gitpeg_webhook,
)
from services.api.projects_erp_writeback_service import _erp_writeback_autoreg
from services.api.projects_gitpeg_integration_service import (
    _upsert_project_registry_status,
)


async def run_project_autoreg_sync_safe(
    *,
    sb: Client,
    project: dict[str, Any],
    force: bool,
    writeback: bool,
    sync_project_autoreg: Callable[..., Awaitable[dict[str, Any]]],
    include_http_exception_detail: bool,
) -> dict[str, Any]:
    try:
        return await sync_project_autoreg(
            sb=sb,
            project=project,
            force=force,
            writeback=writeback,
        )
    except HTTPException as exc:
        if include_http_exception_detail:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            return {
                "enabled": True,
                "success": False,
                "reason": detail,
            }
        raise
    except Exception as exc:
        return {
            "enabled": True,
            "success": False,
            "reason": f"autoreg_sync_failed: {exc}",
        }


async def sync_project_autoreg_flow(
    *,
    sb: Client,
    project: dict[str, Any],
    force: bool,
    writeback: bool,
    load_sync_custom: Callable[..., dict[str, Any]],
    autoreg_enabled: Callable[[dict[str, Any]], bool],
    load_enterprise: Callable[..., dict[str, Any]],
    build_autoreg_input: Callable[[dict[str, Any], dict[str, Any]], Any],
    normalize_request: Callable[[Any], dict[str, Any]],
    gitpeg_registrar_config: Callable[[dict[str, Any]], dict[str, Any]],
    gitpeg_registrar_ready: Callable[[dict[str, Any]], bool],
    gitpeg_create_registration_session: Callable[..., Awaitable[dict[str, Any]]],
    upsert_autoreg: Callable[[Client, dict[str, Any]], Any],
) -> dict[str, Any]:
    enterprise_id = str(project.get("enterprise_id") or "").strip()
    if not enterprise_id:
        return {"enabled": False, "success": False, "reason": "project_enterprise_id_missing"}

    custom = load_sync_custom(sb, enterprise_id)
    enabled = autoreg_enabled(custom)
    if not enabled and not force:
        return {"enabled": False, "success": True, "skipped": True, "reason": "autoreg_disabled"}

    enterprise = load_enterprise(sb, enterprise_id)
    req = build_autoreg_input(project, enterprise)
    normalized = normalize_request(req)
    cfg = gitpeg_registrar_config(custom)

    if cfg.get("enabled"):
        if not gitpeg_registrar_ready(cfg):
            return {
                "enabled": True,
                "success": False,
                "reason": "gitpeg_registrar_config_incomplete",
            }
        session_payload = await gitpeg_create_registration_session(
            cfg,
            project=project,
            enterprise=enterprise,
        )
        _upsert_project_registry_status(
            sb,
            normalized,
            status="pending_activation",
            source_system="qcspec-registrar",
            extra={
                "project_id": project.get("id"),
                "partner_session_id": session_payload.get("session_id"),
                "registration_id": None,
                "industry_profile_id": None,
                "proof_hash": None,
                "node_uri": normalized.get("project_uri"),
                "activation_payload": {
                    "session_id": session_payload.get("session_id"),
                    "hosted_register_url": session_payload.get("hosted_register_url"),
                    "expires_at": session_payload.get("expires_at"),
                },
            },
        )
        autoreg_response = {
            "project_code": normalized["project_code"],
            "project_name": normalized["project_name"],
            "site_code": normalized["site_code"],
            "site_name": normalized["site_name"],
            "gitpeg_project_uri": normalized["project_uri"],
            "gitpeg_site_uri": normalized["site_uri"],
            "gitpeg_executor_uri": normalized["executor_uri"],
            "gitpeg_status": "pending_activation",
            "source_system": normalized["source_system"],
            "session_id": session_payload.get("session_id"),
            "hosted_register_url": session_payload.get("hosted_register_url"),
            "expires_at": session_payload.get("expires_at"),
        }
        return {
            "enabled": True,
            "success": True,
            "pending_activation": True,
            "autoreg": autoreg_response,
            "erp_writeback": {
                "attempted": False,
                "success": False,
                "reason": "waiting_gitpeg_registration_completion",
            },
        }

    upsert_info = upsert_autoreg(sb, normalized)
    autoreg_response = {
        "project_code": normalized["project_code"],
        "project_name": normalized["project_name"],
        "site_code": normalized["site_code"],
        "site_name": normalized["site_name"],
        "gitpeg_project_uri": normalized["project_uri"],
        "gitpeg_site_uri": normalized["site_uri"],
        "gitpeg_executor_uri": normalized["executor_uri"],
        "gitpeg_status": "active",
        "source_system": normalized["source_system"],
        "sync": upsert_info,
        "mode": "local_mirror_fallback",
    }

    result = {
        "enabled": True,
        "success": True,
        "autoreg": autoreg_response,
    }
    if writeback:
        writeback_res = await _erp_writeback_autoreg(custom, project, autoreg_response)
        result["erp_writeback"] = writeback_res
        if writeback_res.get("attempted") and not writeback_res.get("success"):
            result["success"] = False
    return result


