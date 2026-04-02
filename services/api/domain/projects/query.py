"""Canonical projects query and CRUD helpers."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Callable, Optional

from supabase import Client


_EXPORT_HEADERS = [
    "id",
    "name",
    "type",
    "status",
    "owner_unit",
    "contractor",
    "supervisor",
    "contract_no",
    "erp_project_code",
    "erp_project_name",
    "start_date",
    "end_date",
    "v_uri",
    "record_count",
    "photo_count",
    "proof_count",
]

_DOT_BY_ACTION = {
    "create": "#1A56DB",
    "submit": "#1A56DB",
    "upload": "#059669",
    "generate": "#D97706",
    "verify": "#0EA5E9",
    "warn": "#DC2626",
}

_DOT_BY_TYPE = {
    "inspection": "#1A56DB",
    "photo": "#059669",
    "report": "#D97706",
}


def _normalize_activity_summary(summary: Any, object_type: str, action: str) -> str:
    text = str(summary or "").strip()
    if not text:
        return f"{object_type or 'object'} {action or 'update'}"
    # Historical fallback: unknown stake marker represented by '?'.
    if object_type == "photo" and action == "upload" and "?" in text:
        text = text.replace("?", "unknown stake", 1)
    return text


def list_projects_data(
    sb: Client,
    *,
    enterprise_id: str,
    status: Optional[str] = None,
    project_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    q = (
        sb.table("projects")
        .select("*")
        .eq("enterprise_id", enterprise_id)
        .order("created_at", desc=True)
    )
    if status:
        q = q.eq("status", status)
    if project_type:
        q = q.eq("type", project_type)
    return q.execute().data or []


def list_project_activity_data(
    sb: Client,
    *,
    enterprise_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows = (
        sb.table("proof_chain")
        .select("proof_id,object_type,action,summary,created_at,project_id")
        .eq("enterprise_id", enterprise_id)
        .order("created_at", desc=True)
        .limit(max(1, min(limit, 100)))
        .execute()
    )
    data = rows.data or []
    items: list[dict[str, Any]] = []
    for row in data:
        action = str(row.get("action") or "").lower()
        obj = str(row.get("object_type") or "").lower()
        dot = _DOT_BY_ACTION.get(action) or _DOT_BY_TYPE.get(obj) or "#64748B"
        summary = _normalize_activity_summary(row.get("summary"), obj, action)
        items.append(
            {
                "dot": dot,
                "text": summary,
                "created_at": row.get("created_at"),
                "proof_id": row.get("proof_id"),
                "project_id": row.get("project_id"),
            }
        )
    return items


def export_projects_csv_text(
    sb: Client,
    *,
    enterprise_id: str,
    status: Optional[str] = None,
    project_type: Optional[str] = None,
) -> str:
    rows = list_projects_data(
        sb,
        enterprise_id=enterprise_id,
        status=status,
        project_type=project_type,
    )
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_HEADERS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in _EXPORT_HEADERS})
    return buf.getvalue()


def get_project_data(
    sb: Client,
    *,
    project_id: str,
    enterprise_id: Optional[str] = None,
) -> dict[str, Any] | None:
    q = sb.table("projects").select("*").eq("id", project_id)
    if enterprise_id:
        q = q.eq("enterprise_id", enterprise_id)
    res = q.limit(1).execute()
    data = res.data or []
    return data[0] if data else None


def normalize_project_patch(
    updates: dict[str, Any] | None,
    *,
    normalize_seg_type: Callable[[Any], str],
    normalize_perm_template: Callable[[Any], str],
    normalize_km_interval: Callable[[Any], int],
    normalize_inspection_types: Callable[[Any], list[str]],
    normalize_contract_segs: Callable[[Any], list[dict[str, Any]]],
    normalize_structures: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_personnel: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_equipment: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_subcontracts: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_materials: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_sign_status: Callable[[Any], str],
) -> dict[str, Any]:
    patch = dict(updates or {})
    # Backward-compatible aliases for older frontend payloads (camelCase).
    if "zeroPersonnel" in patch and "zero_personnel" not in patch:
        patch["zero_personnel"] = patch.pop("zeroPersonnel")
    if "zeroEquipment" in patch and "zero_equipment" not in patch:
        patch["zero_equipment"] = patch.pop("zeroEquipment")
    if "zeroSubcontracts" in patch and "zero_subcontracts" not in patch:
        patch["zero_subcontracts"] = patch.pop("zeroSubcontracts")
    if "zeroMaterials" in patch and "zero_materials" not in patch:
        patch["zero_materials"] = patch.pop("zeroMaterials")
    if "zeroSignStatus" in patch and "zero_sign_status" not in patch:
        patch["zero_sign_status"] = patch.pop("zeroSignStatus")
    if "qcLedgerUnlocked" in patch and "qc_ledger_unlocked" not in patch:
        patch["qc_ledger_unlocked"] = patch.pop("qcLedgerUnlocked")

    if "seg_type" in patch:
        patch["seg_type"] = normalize_seg_type(patch.get("seg_type"))
    if "perm_template" in patch:
        patch["perm_template"] = normalize_perm_template(patch.get("perm_template"))
    if "km_interval" in patch:
        patch["km_interval"] = normalize_km_interval(patch.get("km_interval"))
    if "inspection_types" in patch:
        patch["inspection_types"] = normalize_inspection_types(patch.get("inspection_types"))
    if "contract_segs" in patch:
        patch["contract_segs"] = normalize_contract_segs(patch.get("contract_segs"))
    if "structures" in patch:
        patch["structures"] = normalize_structures(patch.get("structures"))
    if "zero_personnel" in patch:
        patch["zero_personnel"] = normalize_zero_personnel(patch.get("zero_personnel"))
    if "zero_equipment" in patch:
        patch["zero_equipment"] = normalize_zero_equipment(patch.get("zero_equipment"))
    if "zero_subcontracts" in patch:
        patch["zero_subcontracts"] = normalize_zero_subcontracts(patch.get("zero_subcontracts"))
    if "zero_materials" in patch:
        patch["zero_materials"] = normalize_zero_materials(patch.get("zero_materials"))
    if "zero_sign_status" in patch:
        patch["zero_sign_status"] = normalize_zero_sign_status(patch.get("zero_sign_status"))
    if "qc_ledger_unlocked" in patch:
        patch["qc_ledger_unlocked"] = bool(patch.get("qc_ledger_unlocked"))
    return patch


def update_project_data(
    sb: Client,
    *,
    project_id: str,
    patch: dict[str, Any],
) -> dict[str, Any]:
    res = sb.table("projects").update(patch).eq("id", project_id).execute()
    return res.data[0] if res.data else {}


def delete_project_data(
    sb: Client,
    *,
    project_id: str,
    enterprise_id: Optional[str] = None,
) -> dict[str, bool]:
    check = sb.table("projects").select("id").eq("id", project_id)
    if enterprise_id:
        check = check.eq("enterprise_id", enterprise_id)
    exists = check.limit(1).execute()
    if not exists.data:
        return {"found": False, "deleted": False}

    # proof_chain.project_id -> projects.id is not ON DELETE CASCADE.
    sb.table("proof_chain").delete().eq("project_id", project_id).execute()

    q = sb.table("projects").delete().eq("id", project_id)
    if enterprise_id:
        q = q.eq("enterprise_id", enterprise_id)
    q.execute()

    left = sb.table("projects").select("id").eq("id", project_id).limit(1).execute()
    return {"found": True, "deleted": not bool(left.data)}


__all__ = [
    "list_projects_data",
    "list_project_activity_data",
    "export_projects_csv_text",
    "get_project_data",
    "normalize_project_patch",
    "update_project_data",
    "delete_project_data",
]
