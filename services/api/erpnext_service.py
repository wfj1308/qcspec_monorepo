"""
ERPNext integration service helpers for QCSpec.
services/api/erpnext_service.py
"""

from __future__ import annotations

from typing import Any, Optional
from supabase import Client
from services.api.erpnext_http_utils import erp_request as _erp_request

ERP_METHOD_PREFIX_DEFAULT = "zbgc_integration.qcspec"
ERP_PROJECT_BASICS_PATH_DEFAULT = f"/api/method/{ERP_METHOD_PREFIX_DEFAULT}.get_project_basics"
ERP_METERING_REQUESTS_PATH_DEFAULT = f"/api/method/{ERP_METHOD_PREFIX_DEFAULT}.get_metering_requests"
ERP_NOTIFY_PATH_DEFAULT = f"/api/method/{ERP_METHOD_PREFIX_DEFAULT}.notify"

def _unwrap_frappe_payload(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    if "message" in data:
        return data.get("message")
    if "data" in data:
        return data.get("data")
    return data


def _pick_string(mapping: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_project_basics_payload(raw: Any) -> dict[str, str]:
    payload = _unwrap_frappe_payload(raw)
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        payload = payload[0]
    if not isinstance(payload, dict):
        return {}

    out = {
        "project_code": _pick_string(payload, ["project_code", "project_id", "project_code_id", "project", "name"]),
        "project_name": _pick_string(payload, ["project_name", "project_title", "display_name", "title"]),
        "owner_unit": _pick_string(payload, ["owner_unit", "owner", "employer", "client"]),
        "contractor": _pick_string(payload, ["contractor", "construction_unit", "builder"]),
        "supervisor": _pick_string(payload, ["supervisor", "supervision_unit", "consultant"]),
        "contract_no": _pick_string(payload, ["contract_no", "contract_code", "contract_id", "contract"]),
        "start_date": _pick_string(payload, ["start_date", "planned_start_date", "expected_start_date", "from_date"]),
        "end_date": _pick_string(payload, ["end_date", "planned_end_date", "expected_end_date", "to_date"]),
        "description": _pick_string(payload, ["description", "project_desc", "remark", "remarks"]),
    }
    return {k: v for k, v in out.items() if v}


def _normalize_metering_items(raw: Any) -> list[dict[str, Any]]:
    payload = _unwrap_frappe_payload(raw)
    if isinstance(payload, dict):
        rows = payload.get("items")
        if not isinstance(rows, list):
            rows = payload.get("rows")
        if not isinstance(rows, list):
            rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        amount = row.get("amount")
        if amount is None:
            amount = row.get("apply_amount")
        if amount is None:
            amount = row.get("request_amount")
        stake = _pick_string(row, ["stake", "stake_no", "pile_no", "segment"])
        subitem = _pick_string(row, ["subitem", "sub_item", "item", "part"])
        status = _pick_string(row, ["status", "workflow_state", "state"])
        out.append(
            {
                "id": _pick_string(row, ["name", "id", "request_id"]),
                "stake": stake,
                "subitem": subitem,
                "status": status,
                "amount": amount,
                "raw": row,
            }
        )
        if len(out) >= 200:
            break
    return out


def _evaluate_metering_gate(
    *,
    erp_sync_enabled: bool,
    inspection_result: str,
    metering_lookup: dict[str, Any],
) -> dict[str, Any]:
    result = str(inspection_result or "").strip().lower()
    success = bool(metering_lookup.get("success"))
    items = metering_lookup.get("items") if isinstance(metering_lookup.get("items"), list) else []
    count = len(items)
    matched = items[0] if items else None

    if not erp_sync_enabled:
        return {
            "enabled": False,
            "allow_submit": True,
            "can_release": True,
            "action": "skip",
            "reason": "erpnext_sync_disabled",
            "count": count,
            "matched": matched,
        }

    if result != "pass":
        return {
            "enabled": True,
            "allow_submit": True,
            "can_release": False,
            "action": "block",
            "reason": "inspection_not_passed",
            "count": count,
            "matched": matched,
        }

    if not success:
        return {
            "enabled": True,
            "allow_submit": False,
            "can_release": False,
            "action": "block",
            "reason": "metering_lookup_failed",
            "count": count,
            "matched": matched,
        }

    if count <= 0:
        return {
            "enabled": True,
            "allow_submit": False,
            "can_release": False,
            "action": "block",
            "reason": "no_pending_metering_request",
            "count": 0,
            "matched": None,
        }

    return {
        "enabled": True,
        "allow_submit": True,
        "can_release": True,
        "action": "release",
        "reason": "ready_to_release",
        "count": count,
        "matched": matched,
    }


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_erpnext_custom(sb: Client, enterprise_id: str) -> dict[str, Any]:
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


def _erp_method_label(path: str) -> str:
    text = str(path or "").strip()
    if text.startswith("/api/method/"):
        return text[len("/api/method/") :]
    return text or "unknown_method"


def _compact_errors(errors: Any, limit: int = 2) -> list[str]:
    if not isinstance(errors, list):
        return []
    out: list[str] = []
    for item in errors[: max(1, min(limit, 10))]:
        text = str(item or "").strip().replace("\n", " ")
        if len(text) > 280:
            text = text[:280] + "..."
        out.append(text)
    return out


def _is_qcspec_method_missing(errors: Any) -> bool:
    text = " ".join(str(x or "") for x in (errors if isinstance(errors, list) else []))
    text = text.lower()
    return "app qcspec is not installed" in text or "failed to get method for command qcspec." in text


async def fetch_erpnext_project_basics(
    custom: dict[str, Any],
    *,
    project_code: Optional[str] = None,
    project_name: Optional[str] = None,
) -> dict[str, Any]:
    path = str(custom.get("erpnext_project_basics_path") or ERP_PROJECT_BASICS_PATH_DEFAULT).strip()
    params: dict[str, Any] = {}
    if project_code:
        params["project_code"] = project_code
    if project_name:
        params["project_name"] = project_name

    res = await _erp_request(custom, method="GET", path=path, params=params, timeout_s=10.0)
    if not res.get("success"):
        return res
    payload = res.get("data")
    return {
        **res,
        "project_basics": _normalize_project_basics_payload(payload),
    }


async def fetch_erpnext_metering_requests(
    custom: dict[str, Any],
    *,
    project_code: Optional[str] = None,
    stake: Optional[str] = None,
    subitem: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    path = str(custom.get("erpnext_metering_requests_path") or ERP_METERING_REQUESTS_PATH_DEFAULT).strip()
    params: dict[str, Any] = {}
    if project_code:
        params["project_code"] = project_code
    if stake:
        params["stake"] = stake
    if subitem:
        params["subitem"] = subitem
    if status:
        params["status"] = status

    res = await _erp_request(custom, method="GET", path=path, params=params, timeout_s=10.0)
    if not res.get("success"):
        return res
    payload = res.get("data")
    items = _normalize_metering_items(payload)
    return {
        **res,
        "items": items,
        "count": len(items),
    }


async def evaluate_erpnext_gate_for_inspection(
    custom: dict[str, Any],
    *,
    project_code: Optional[str] = None,
    stake: str,
    subitem: str,
    result: str,
) -> dict[str, Any]:
    erp_sync_enabled = _to_bool(custom.get("erpnext_sync"))
    if not erp_sync_enabled:
        gate = _evaluate_metering_gate(
            erp_sync_enabled=False,
            inspection_result=result,
            metering_lookup={"success": False, "items": []},
        )
        return {
            "gate": gate,
            "metering_lookup": {"attempted": False, "success": False, "count": 0, "reason": "erpnext_sync_disabled", "items": []},
        }
    code = str(project_code or "").strip()
    if not code:
        gate = _evaluate_metering_gate(
            erp_sync_enabled=erp_sync_enabled,
            inspection_result=result,
            metering_lookup={"success": False, "items": []},
        )
        gate.update(
            {
                "allow_submit": False if str(result or "").strip().lower() == "pass" else True,
                "can_release": False,
                "action": "block",
                "reason": "missing_erp_project_code_binding",
                "count": 0,
                "matched": None,
            }
        )
        return {
            "gate": gate,
            "metering_lookup": {
                "attempted": False,
                "success": False,
                "count": 0,
                "reason": "missing_erp_project_code_binding",
                "items": [],
            },
        }

    metering = await fetch_erpnext_metering_requests(
        custom,
        project_code=code,
        stake=str(stake or "").strip() or None,
        subitem=str(subitem or "").strip() or None,
        status=str(custom.get("erpnext_metering_status") or "pending").strip() or None,
    )
    gate = _evaluate_metering_gate(
        erp_sync_enabled=erp_sync_enabled,
        inspection_result=result,
        metering_lookup=metering,
    )
    return {
        "gate": gate,
        "metering_lookup": {
            "attempted": metering.get("attempted", False),
            "success": metering.get("success", False),
            "count": gate.get("count", 0),
            "reason": metering.get("reason") or metering.get("errors"),
            "items": (metering.get("items") if isinstance(metering.get("items"), list) else [])[:5],
        },
    }


async def notify_erpnext_for_inspection(
    custom: dict[str, Any],
    *,
    project: dict[str, Any],
    inspection: dict[str, Any],
    proof_id: str,
) -> dict[str, Any]:
    if not _to_bool(custom.get("erpnext_sync")):
        return {"attempted": False, "success": False, "reason": "erpnext_sync_disabled"}

    erp_project_code = str(project.get("erp_project_code") or "").strip() or None
    erp_project_name = str(project.get("erp_project_name") or project.get("name") or "").strip() or None
    gate_pack = await evaluate_erpnext_gate_for_inspection(
        custom,
        project_code=erp_project_code,
        stake=str(inspection.get("location") or "").strip(),
        subitem=str(inspection.get("type_name") or inspection.get("type") or "").strip(),
        result=str(inspection.get("result") or "").strip(),
    )
    gate = gate_pack.get("gate") if isinstance(gate_pack.get("gate"), dict) else {}
    metering_lookup = gate_pack.get("metering_lookup") if isinstance(gate_pack.get("metering_lookup"), dict) else {}
    metering_items = metering_lookup.get("items") if isinstance(metering_lookup.get("items"), list) else []
    matched_metering = gate.get("matched") if isinstance(gate.get("matched"), dict) else None

    notify_path = str(custom.get("erpnext_notify_path") or ERP_NOTIFY_PATH_DEFAULT).strip()
    result = str(inspection.get("result") or "").strip().lower()
    quality_passed = result == "pass"
    payload = {
        "enterprise_id": project.get("enterprise_id"),
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "erp_project_code": erp_project_code,
        "erp_project_name": erp_project_name,
        "contract_no": project.get("contract_no"),
        "project_uri": project.get("v_uri"),
        "inspection_id": inspection.get("id"),
        "stake": inspection.get("location"),
        "subitem": inspection.get("type_name") or inspection.get("type"),
        "result": result,
        "value": inspection.get("value"),
        "standard": inspection.get("standard"),
        "unit": inspection.get("unit"),
        "proof_id": proof_id,
        "quality_passed": quality_passed,
        "metering_action": gate.get("action") or ("release" if quality_passed else "block"),
        "reason": "" if gate.get("can_release") else (gate.get("reason") or "inspection_not_passed"),
        "metering_request_id": matched_metering.get("id") if isinstance(matched_metering, dict) else None,
        "metering_amount": matched_metering.get("amount") if isinstance(matched_metering, dict) else None,
        "metering_context": metering_items[:5],
    }
    notify_res = await _erp_request(custom, method="POST", path=notify_path, body=payload, timeout_s=10.0)
    notify_res["metering_lookup"] = metering_lookup
    notify_res["gate"] = {
        "enabled": bool(gate.get("enabled")),
        "allow_submit": bool(gate.get("allow_submit")),
        "can_release": bool(gate.get("can_release")),
        "action": gate.get("action"),
        "reason": gate.get("reason"),
    }
    return notify_res



