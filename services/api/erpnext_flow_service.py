"""
Flow helpers for ERPNext router.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID
import json

from fastapi import HTTPException
from supabase import Client

from services.api.erpnext_service import (
    ERP_METERING_REQUESTS_PATH_DEFAULT,
    ERP_NOTIFY_PATH_DEFAULT,
    ERP_PROJECT_BASICS_PATH_DEFAULT,
    _compact_errors,
    _erp_method_label,
    _erp_request,
    _is_qcspec_method_missing,
    evaluate_erpnext_gate_for_inspection,
    fetch_erpnext_metering_requests,
    fetch_erpnext_project_basics,
    load_erpnext_custom,
)


async def check_metering_gate_flow(
    *,
    enterprise_id: str,
    stake: str,
    subitem: str,
    result: str,
    project_id: Optional[str],
    project_code: Optional[str],
    sb: Client,
) -> dict[str, Any]:
    custom = load_erpnext_custom(sb, enterprise_id)
    resolved_project_code = str(project_code or "").strip() or None
    if project_id:
        try:
            UUID(str(project_id))
        except Exception:
            raise HTTPException(400, "invalid project_id")
        proj_res = (
            sb.table("projects")
            .select("id,enterprise_id,erp_project_code")
            .eq("id", project_id)
            .eq("enterprise_id", enterprise_id)
            .limit(1)
            .execute()
        )
        if not proj_res.data:
            raise HTTPException(404, "project not found")
        row = proj_res.data[0]
        resolved_project_code = str(row.get("erp_project_code") or resolved_project_code or "").strip() or None

    pack = await evaluate_erpnext_gate_for_inspection(
        custom,
        project_code=resolved_project_code,
        stake=stake,
        subitem=subitem,
        result=result,
    )
    return {
        "ok": True,
        "project_code": resolved_project_code,
        "gate": pack.get("gate"),
        "metering_lookup": pack.get("metering_lookup"),
    }


async def get_project_basics_flow(
    *,
    enterprise_id: str,
    project_code: Optional[str],
    project_name: Optional[str],
    sb: Client,
) -> dict[str, Any]:
    custom = load_erpnext_custom(sb, enterprise_id)
    res = await fetch_erpnext_project_basics(custom, project_code=project_code, project_name=project_name)
    if not res.get("success"):
        raise HTTPException(502, f"erpnext project basics failed: {json.dumps(res, ensure_ascii=False)[:400]}")
    return res


async def get_metering_requests_flow(
    *,
    enterprise_id: str,
    project_code: Optional[str],
    stake: Optional[str],
    subitem: Optional[str],
    status: Optional[str],
    sb: Client,
) -> dict[str, Any]:
    custom = load_erpnext_custom(sb, enterprise_id)
    res = await fetch_erpnext_metering_requests(
        custom,
        project_code=project_code,
        stake=stake,
        subitem=subitem,
        status=status,
    )
    if not res.get("success"):
        raise HTTPException(502, f"erpnext metering requests failed: {json.dumps(res, ensure_ascii=False)[:400]}")
    return res


async def notify_erpnext_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    custom = load_erpnext_custom(sb, body.enterprise_id)
    path = str(custom.get("erpnext_notify_path") or ERP_NOTIFY_PATH_DEFAULT).strip()
    passed = str(body.result or "").strip().lower() == "pass"
    payload = {
        "enterprise_id": body.enterprise_id,
        "project_id": body.project_id,
        "stake": body.stake,
        "subitem": body.subitem,
        "result": body.result,
        "amount": body.amount,
        "quality_passed": passed,
        "metering_action": "release" if passed else "block",
        "reason": body.reason or ("" if passed else "inspection_not_passed"),
        **(body.extra or {}),
    }
    res = await _erp_request(custom, method="POST", path=path, body=payload, timeout_s=10.0)
    if not res.get("success"):
        raise HTTPException(502, f"erpnext notify failed: {json.dumps(res, ensure_ascii=False)[:400]}")
    return res


async def probe_erpnext_flow(
    *,
    enterprise_id: str,
    sample_project_name: str,
    sample_stake: str,
    sample_subitem: str,
    sb: Client,
) -> dict[str, Any]:
    custom = load_erpnext_custom(sb, enterprise_id)

    ping = await _erp_request(custom, method="GET", path="/api/method/ping", timeout_s=10.0)
    basics_path = str(custom.get("erpnext_project_basics_path") or ERP_PROJECT_BASICS_PATH_DEFAULT).strip()
    metering_path = str(custom.get("erpnext_metering_requests_path") or ERP_METERING_REQUESTS_PATH_DEFAULT).strip()
    notify_path = str(custom.get("erpnext_notify_path") or ERP_NOTIFY_PATH_DEFAULT).strip()
    basics_label = _erp_method_label(basics_path)
    metering_label = _erp_method_label(metering_path)
    notify_label = _erp_method_label(notify_path)

    basics = await _erp_request(
        custom,
        method="GET",
        path=basics_path,
        params={"project_name": sample_project_name},
        timeout_s=10.0,
    )
    metering = await _erp_request(
        custom,
        method="GET",
        path=metering_path,
        params={"stake": sample_stake, "subitem": sample_subitem, "status": "pending"},
        timeout_s=10.0,
    )
    notify = await _erp_request(
        custom,
        method="POST",
        path=notify_path,
        body={
            "stake": sample_stake,
            "subitem": sample_subitem,
            "result": "pass",
            "quality_passed": True,
            "metering_action": "release",
        },
        timeout_s=10.0,
    )

    methods_ready = bool(basics.get("success")) and bool(metering.get("success")) and bool(notify.get("success"))
    blocker = None
    if _is_qcspec_method_missing(basics.get("errors")) or _is_qcspec_method_missing(metering.get("errors")) or _is_qcspec_method_missing(notify.get("errors")):
        blocker = "erpnext_missing_qcspec_methods"

    return {
        "ok": True,
        "enterprise_id": enterprise_id,
        "erpnext_url": custom.get("erpnext_url"),
        "auth_connectivity": {
            "success": bool(ping.get("success")),
            "auth_mode": ping.get("authMode"),
            "status_code": ping.get("statusCode"),
            "errors": _compact_errors(ping.get("errors"), limit=2),
        },
        "methods": {
            basics_label: {
                "success": bool(basics.get("success")),
                "status_code": basics.get("statusCode"),
                "errors": _compact_errors(basics.get("errors"), limit=2),
            },
            metering_label: {
                "success": bool(metering.get("success")),
                "status_code": metering.get("statusCode"),
                "errors": _compact_errors(metering.get("errors"), limit=2),
            },
            notify_label: {
                "success": bool(notify.get("success")),
                "status_code": notify.get("statusCode"),
                "errors": _compact_errors(notify.get("errors"), limit=2),
            },
        },
        "ready_for_qcspec": bool(ping.get("success")) and methods_ready,
        "blocker": blocker,
    }
