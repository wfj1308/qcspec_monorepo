"""Ref-only binding validation for BOQPeg preview/created rows."""

from __future__ import annotations

from typing import Any

REQUIRED_REF_FIELDS: tuple[str, ...] = ("ref_spu_uri", "ref_quota_uri", "ref_meter_rule_uri")
PROJECT_REF_REQUIRED_FIELDS: tuple[str, ...] = ("boq_v_uri", "boq_item_id", "quantity", "unit", "ref_spu_uri")
PROJECT_REF_ALLOWED_FIELDS: tuple[str, ...] = (
    "boq_v_uri",
    "boq_item_id",
    "description",
    "quantity",
    "unit",
    "bridge_uri",
    "ref_spu_uri",
    "ref_quota_uri",
    "ref_meter_rule_uri",
    "custom_params",
)
LEGACY_INLINE_LOGIC_FIELDS: tuple[str, ...] = (
    "spu_formula",
    "spu_form_schema",
    "spu_geometry",
    "linked_gate_rules",
    "qc_gates",
    "consumption_rates",
)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _state_data(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("state_data")
    return payload if isinstance(payload, dict) else {}


def _is_leaf(state_data: dict[str, Any]) -> bool:
    return bool(state_data.get("is_leaf"))


def _missing_refs(state_data: dict[str, Any]) -> list[str]:
    return [field for field in REQUIRED_REF_FIELDS if not _to_text(state_data.get(field))]


def _project_ref_payload(state_data: dict[str, Any]) -> dict[str, Any]:
    payload = state_data.get("project_boq_item_ref")
    return payload if isinstance(payload, dict) else {}


def _missing_project_ref_fields(payload: dict[str, Any]) -> list[str]:
    return [field for field in PROJECT_REF_REQUIRED_FIELDS if not _to_text(payload.get(field))]


def _project_ref_extra_fields(payload: dict[str, Any]) -> list[str]:
    extras = [key for key in payload.keys() if key not in PROJECT_REF_ALLOWED_FIELDS]
    return sorted(extras)


def _legacy_logic_fields(state_data: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in LEGACY_INLINE_LOGIC_FIELDS:
        value = state_data.get(key)
        if value in (None, "", [], {}, ()):
            continue
        out.append(key)
    return out


def validate_ref_only_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_leaf_rows = 0
    valid_leaf_rows = 0
    missing_entries: list[dict[str, Any]] = []
    invalid_project_ref_entries: list[dict[str, Any]] = []
    legacy_inline_logic_entries: list[dict[str, Any]] = []

    for row in rows:
        state_data = _state_data(row)
        if not _is_leaf(state_data):
            continue
        total_leaf_rows += 1
        missing = _missing_refs(state_data)
        project_ref = _project_ref_payload(state_data)
        project_ref_missing = _missing_project_ref_fields(project_ref)
        project_ref_extras = _project_ref_extra_fields(project_ref) if project_ref else []
        legacy_inline_logic = _legacy_logic_fields(state_data)
        if missing:
            missing_entries.append(
                {
                    "proof_id": _to_text(row.get("proof_id")),
                    "item_no": _to_text(state_data.get("item_no")),
                    "boq_item_uri": _to_text(state_data.get("boq_item_uri")),
                    "missing_fields": missing,
                }
            )
        if project_ref_missing or project_ref_extras:
            invalid_project_ref_entries.append(
                {
                    "proof_id": _to_text(row.get("proof_id")),
                    "item_no": _to_text(state_data.get("item_no")),
                    "boq_item_uri": _to_text(state_data.get("boq_item_uri")),
                    "missing_fields": project_ref_missing,
                    "extra_fields": project_ref_extras,
                }
            )
        if legacy_inline_logic:
            legacy_inline_logic_entries.append(
                {
                    "proof_id": _to_text(row.get("proof_id")),
                    "item_no": _to_text(state_data.get("item_no")),
                    "boq_item_uri": _to_text(state_data.get("boq_item_uri")),
                    "legacy_fields": legacy_inline_logic,
                }
            )
        if (not missing) and (not project_ref_missing) and (not project_ref_extras) and (not legacy_inline_logic):
            valid_leaf_rows += 1

    return {
        "ok": total_leaf_rows == valid_leaf_rows,
        "required_ref_fields": list(REQUIRED_REF_FIELDS),
        "project_ref_required_fields": list(PROJECT_REF_REQUIRED_FIELDS),
        "project_ref_allowed_fields": list(PROJECT_REF_ALLOWED_FIELDS),
        "legacy_inline_logic_fields": list(LEGACY_INLINE_LOGIC_FIELDS),
        "total_leaf_rows": total_leaf_rows,
        "valid_leaf_rows": valid_leaf_rows,
        "invalid_leaf_rows": total_leaf_rows - valid_leaf_rows,
        "missing_entries": missing_entries,
        "invalid_project_ref_rows": len(invalid_project_ref_entries),
        "invalid_project_ref_entries": invalid_project_ref_entries,
        "legacy_inline_logic_rows": len(legacy_inline_logic_entries),
        "legacy_inline_logic_entries": legacy_inline_logic_entries,
    }


__all__ = [
    "LEGACY_INLINE_LOGIC_FIELDS",
    "PROJECT_REF_ALLOWED_FIELDS",
    "PROJECT_REF_REQUIRED_FIELDS",
    "REQUIRED_REF_FIELDS",
    "validate_ref_only_rows",
]
