"""
Project persistence and schema-compat helpers.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client


def _extract_missing_column_name(exc: APIError) -> Optional[str]:
    raw = exc.args[0] if exc.args else ""
    if isinstance(raw, dict):
        message = str(raw.get("message") or "")
    else:
        message = str(raw or exc)
    m = re.search(r"Could not find the '([^']+)' column", message)
    if not m:
        return None
    return m.group(1).strip() or None


def _insert_project_with_schema_fallback(
    sb: Client,
    rec: dict[str, Any],
    *,
    allow_schema_fallback: bool = True,
) -> Any:
    payload = dict(rec)
    if not allow_schema_fallback:
        return sb.table("projects").insert(payload).execute()
    max_attempts = max(1, len(payload))
    for _ in range(max_attempts):
        try:
            return sb.table("projects").insert(payload).execute()
        except APIError as exc:
            missing_col = _extract_missing_column_name(exc)
            if not missing_col or missing_col not in payload:
                raise
            payload.pop(missing_col, None)
    return sb.table("projects").insert(payload).execute()


def _project_zero_ledger_mismatch(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return True
    zero_keys = (
        "zero_personnel",
        "zero_equipment",
        "zero_subcontracts",
        "zero_materials",
    )
    for key in zero_keys:
        if row.get(key) != expected.get(key):
            return True
    if str(row.get("zero_sign_status") or "pending") != str(expected.get("zero_sign_status") or "pending"):
        return True
    if bool(row.get("qc_ledger_unlocked")) != bool(expected.get("qc_ledger_unlocked")):
        return True
    return False


def create_project_record(
    sb: Client,
    *,
    record: dict[str, Any],
    erp_sync_enabled: bool,
) -> dict[str, Any]:
    try:
        res = _insert_project_with_schema_fallback(
            sb,
            record,
            allow_schema_fallback=not erp_sync_enabled,
        )
    except APIError as exc:
        missing_col = _extract_missing_column_name(exc)
        if missing_col in {"erp_project_code", "erp_project_name"}:
            raise HTTPException(
                500,
                "projects table missing ERP binding columns; run infra/supabase/010_projects_erp_binding.sql",
            ) from exc
        raw = exc.args[0] if exc.args else ""
        if isinstance(raw, dict):
            message = str(raw.get("message") or "failed to create project")
        else:
            message = str(raw or "failed to create project")
        raise HTTPException(500, message) from exc

    if not res.data:
        raise HTTPException(500, "failed to create project")
    return res.data[0]


def reconcile_created_project(
    sb: Client,
    *,
    project_row: dict[str, Any],
    zero_ledger_patch: dict[str, Any],
    erp_sync_enabled: bool,
    erp_project_code: Optional[str],
    erp_project_name: Optional[str],
) -> dict[str, Any]:
    proj = dict(project_row or {})
    try:
        should_reconcile_zero_ledger = (
            bool(zero_ledger_patch.get("zero_personnel"))
            or bool(zero_ledger_patch.get("zero_equipment"))
            or bool(zero_ledger_patch.get("zero_subcontracts"))
            or bool(zero_ledger_patch.get("zero_materials"))
            or zero_ledger_patch.get("zero_sign_status", "pending") != "pending"
            or bool(zero_ledger_patch.get("qc_ledger_unlocked"))
        )
        if should_reconcile_zero_ledger and _project_zero_ledger_mismatch(proj, zero_ledger_patch):
            sb.table("projects").update(zero_ledger_patch).eq("id", proj["id"]).execute()
            latest = sb.table("projects").select("*").eq("id", proj["id"]).limit(1).execute()
            if latest.data:
                proj = latest.data[0]
    except APIError:
        pass

    if not erp_sync_enabled:
        return proj

    bind_code = str(erp_project_code or "").strip()
    bind_name = str(erp_project_name or "").strip()
    if (
        str(proj.get("erp_project_code") or "").strip() != bind_code
        or str(proj.get("erp_project_name") or "").strip() != bind_name
    ):
        try:
            sb.table("projects").update(
                {
                    "erp_project_code": bind_code,
                    "erp_project_name": bind_name,
                }
            ).eq("id", proj["id"]).execute()
            refreshed = sb.table("projects").select("*").eq("id", proj["id"]).limit(1).execute()
            if refreshed.data:
                proj = refreshed.data[0]
        except APIError as exc:
            missing_col = _extract_missing_column_name(exc)
            if missing_col in {"erp_project_code", "erp_project_name"}:
                raise HTTPException(
                    500,
                    "projects table missing ERP binding columns; run infra/supabase/010_projects_erp_binding.sql",
                ) from exc
            raise
    if (
        str(proj.get("erp_project_code") or "").strip() != bind_code
        or str(proj.get("erp_project_name") or "").strip() != bind_name
    ):
        raise HTTPException(500, "erp_project_binding_persist_failed")

    return proj
