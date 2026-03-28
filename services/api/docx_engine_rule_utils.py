"""
Rule and mapping helpers for docx_engine.
services/api/docx_engine_rule_utils.py
"""

from __future__ import annotations

import re
from typing import Any

from services.api.docx_engine_utils import format_num, parse_limit, to_float, to_text, with_unit


def resolve_schema_mode(
    state_data: dict[str, Any],
    *,
    test_type: str,
    test_type_name: str,
) -> str:
    explicit = to_text(state_data.get("schema_mode") or state_data.get("mode")).strip().lower()
    if explicit in {
        "design_limit",
        "value_standard_max",
        "value_standard_min",
        "value_standard_eq",
    }:
        return explicit

    token = f"{test_type} {test_type_name}".strip().lower()
    if any(k in token for k in ("spacing", "cover", "frame", "间距", "保护层", "骨架")):
        return "design_limit"
    if any(k in token for k in ("flatness", "iri", "crack", "rut", "平整度", "裂缝", "车辙")):
        return "value_standard_max"
    if any(k in token for k in ("compaction", "density", "压实度", "压实")):
        return "value_standard_min"
    return "value_standard_max"


def mode_default_operator(mode: str) -> str:
    if mode == "value_standard_min":
        return ">="
    if mode == "value_standard_eq":
        return "="
    return "<="


def is_flatness_like(state_data: dict[str, Any]) -> bool:
    type_token = str(state_data.get("type") or "").strip().lower()
    type_name = str(state_data.get("type_name") or "").strip().lower()
    token = f"{type_token} {type_name}"
    return any(k in token for k in ("flatness", "iri", "平整度", "路面"))


def is_compaction_like(state_data: dict[str, Any]) -> bool:
    type_token = str(state_data.get("type") or state_data.get("test_type") or "").strip().lower()
    type_name = str(state_data.get("type_name") or state_data.get("test_name") or "").strip().lower()
    token = f"{type_token} {type_name}"
    return any(k in token for k in ("compaction", "density", "压实度", "压实"))


def normalize_standard_op(raw_op: Any, *, plus_minus: str = "±") -> str:
    text = to_text(raw_op).strip().lower()
    if not text:
        return ""
    if text in {"+-", "+/-", "\u00b1", "±", "plusminus", "plus_minus"}:
        return plus_minus
    if text in {"<=", "≤", "le", "lte", "max", "upper"}:
        return "<="
    if text in {">=", "≥", "ge", "gte", "min", "lower"}:
        return ">="
    if text in {"=", "==", "eq"}:
        return "="
    if text in {"<", ">"}:
        return text
    return ""


def extract_standard_from_text(raw: Any) -> tuple[float | None, float | None]:
    text = to_text(raw).strip()
    if not text:
        return None, None
    m = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(?:\u00b1|±|\+/-)\s*([-+]?\d+(?:\.\d+)?)", text)
    if not m:
        return None, None
    try:
        base = float(m.group(1))
        tol = abs(float(m.group(2)))
        return base, tol
    except Exception:
        return None, None


def resolve_standard_rule(
    *,
    state_data: dict[str, Any],
    test_type: str,
    test_type_name: str,
    schema_mode: str,
    design: float | None,
    standard: float | None,
    plus_minus: str = "±",
) -> tuple[str, float | None, float | None]:
    raw_op = (
        state_data.get("standard_op")
        or state_data.get("standard_operator")
        or state_data.get("operator")
        or state_data.get("comparator")
        or state_data.get("compare")
        or ""
    )
    op = normalize_standard_op(raw_op, plus_minus=plus_minus)

    standard_raw = (
        state_data.get("standard_value")
        if state_data.get("standard_value") is not None
        else (
            state_data.get("standard")
            if state_data.get("standard") is not None
            else state_data.get("design")
        )
    )
    standard_value = to_float(standard_raw)
    parsed_base, parsed_tol = extract_standard_from_text(standard_raw)
    if standard_value is None and parsed_base is not None:
        standard_value = parsed_base
    if standard_value is None:
        standard_value = standard if standard is not None else design

    tol_raw = (
        state_data.get("standard_tolerance")
        if state_data.get("standard_tolerance") is not None
        else (
            state_data.get("tolerance")
            if state_data.get("tolerance") is not None
            else state_data.get("limit")
        )
    )
    tolerance = parse_limit(tol_raw)
    if tolerance is None and parsed_tol is not None:
        tolerance = parsed_tol

    if not op:
        probe = {"type": test_type, "type_name": test_type_name}
        if tolerance is not None and (standard_value is not None or design is not None):
            op = plus_minus
        elif is_compaction_like(probe) or schema_mode == "value_standard_min":
            op = ">="
        elif schema_mode == "value_standard_eq":
            op = "="
        else:
            op = "<="

    return op, standard_value, tolerance


def auto_result_from_state_data(
    *,
    state_data: dict[str, Any],
    values: list[float],
    standard_op: str,
    standard_value: float | None,
    tolerance: float | None,
    fallback: str,
    plus_minus: str = "±",
) -> str:
    if standard_op == plus_minus and standard_value is not None and tolerance is not None and values:
        lower = standard_value - tolerance
        upper = standard_value + tolerance
        return "FAIL" if any((v < lower or v > upper) for v in values) else "PASS"

    standard = standard_value if standard_value is not None else to_float(state_data.get("standard"))
    if standard is None or not values:
        return fallback

    op = normalize_standard_op(standard_op, plus_minus=plus_minus) or "<="
    if op == "<=":
        return "PASS" if all(v <= standard for v in values) else "FAIL"
    if op == ">=":
        return "PASS" if all(v >= standard for v in values) else "FAIL"
    if op == "=":
        return "PASS" if all(abs(v - standard) < 1e-9 for v in values) else "FAIL"
    if op == "<":
        return "PASS" if all(v < standard for v in values) else "FAIL"
    if op == ">":
        return "PASS" if all(v > standard for v in values) else "FAIL"
    return fallback


def first_signing(proof: dict[str, Any]) -> dict[str, Any]:
    signed = proof.get("signed_by")
    if isinstance(signed, list) and signed and isinstance(signed[0], dict):
        return signed[0]
    return {}


def normalize_report_type(report_type: Any, *, template_by_type: dict[str, str]) -> str:
    raw = str(report_type or "").strip().lower()
    alias = {
        "inspection_report": "inspection",
        "qcspec": "inspection",
        "quality": "inspection",
        "lab_report": "lab",
        "laboratory": "lab",
        "monthly": "monthly_summary",
        "summary": "monthly_summary",
        "archive": "final_archive",
        "final": "final_archive",
        "final_archive_cover": "final_archive",
    }
    return alias.get(raw, raw if raw in template_by_type else "inspection")


def pick_template_name(project_meta: dict[str, Any], *, report_type: str, template_by_type: dict[str, str]) -> str:
    explicit = str(project_meta.get("template_name") or "").strip()
    if explicit:
        return explicit
    normalized = normalize_report_type(report_type, template_by_type=template_by_type)
    return template_by_type.get(normalized, template_by_type["inspection"])


def infer_item_key(row: dict[str, Any]) -> str | None:
    row_type = str(row.get("test_type") or row.get("type") or "").strip().lower()
    type_name = str(row.get("test_type_name") or row.get("type_name") or "").strip()
    token = f"{row_type} {type_name}".lower()
    if any(k in token for k in ["spacing", "间距"]):
        return "main_rebar"
    if any(k in token for k in ["frame", "骨架"]):
        return "frame_size"
    if any(k in token for k in ["cover", "保护层"]):
        return "cover_thickness"
    if any(k in token for k in ["flatness", "iri", "平整度", "路面"]):
        return "road_flatness"
    return None


def build_named_items(rows: list[dict[str, Any]]) -> dict[str, Any]:
    named: dict[str, Any] = {
        "main_rebar": {},
        "main_rebar_multi": {},
        "frame_size": {},
        "cover_thickness": {},
        "road_flatness": {},
    }

    spacing_rows: list[dict[str, Any]] = []
    flatness_rows: list[dict[str, Any]] = []
    for row in rows:
        row_type = str(row.get("test_type") or row.get("type") or "").strip()
        if row_type:
            named[row_type] = row

        inferred = infer_item_key(row)
        if inferred == "main_rebar":
            spacing_rows.append(row)
        elif inferred == "road_flatness":
            flatness_rows.append(row)
            named["road_flatness"] = row
        elif inferred:
            named[inferred] = row

    if spacing_rows:
        named["main_rebar"] = spacing_rows[0]
        named["main_rebar_multi"] = spacing_rows[1] if len(spacing_rows) > 1 else {}
    elif flatness_rows:
        named["main_rebar"] = flatness_rows[0]
        named["main_rebar_multi"] = {}
    elif rows:
        named["main_rebar"] = rows[0]
        named["main_rebar_multi"] = {}
    return named


def values_single_line(
    row: dict[str, Any],
    *,
    separator: str = "\u3001",
) -> str:
    values = row.get("values")
    unit = to_text(row.get("unit") or "").strip()
    if unit == "-":
        unit = ""
    force_inline = bool(unit and "/" in unit)
    if isinstance(values, list) and values:
        pieces = [with_unit(format_num(float(v)), unit, force_inline=force_inline) for v in values]
        return separator.join(pieces)
    value = to_text(row.get("value") or "").strip()
    return value or "-"


def resolve_table_headers(project_meta: dict[str, Any]) -> list[str]:
    defaults = ["检查项目", "检查项目", "规范要求", "设计值", "实测值", "判定"]
    raw = project_meta.get("table_headers")
    if isinstance(raw, list):
        vals = [to_text(x).strip() for x in raw]
        if len(vals) >= 6:
            return [vals[i] or defaults[i] for i in range(6)]
        return defaults
    if isinstance(raw, dict):
        return [
            to_text(raw.get("item")).strip() or defaults[0],
            to_text(raw.get("sub_item")).strip() or defaults[1],
            to_text(raw.get("limit")).strip() or defaults[2],
            to_text(raw.get("standard")).strip() or defaults[3],
            to_text(raw.get("value")).strip() or defaults[4],
            to_text(raw.get("result")).strip() or defaults[5],
        ]
    return defaults
