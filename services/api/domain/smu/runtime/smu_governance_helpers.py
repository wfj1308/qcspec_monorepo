"""Shared helper functions for SMU governance context assembly."""

from __future__ import annotations

from typing import Any

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    to_float as _to_float,
    to_text as _to_text,
)


def container_status_from_stage(stage: str, result: str) -> str:
    s = _to_text(stage).strip().upper()
    r = _to_text(result).strip().upper()
    if s in {"INITIAL", "PRECHECK"}:
        return "Unspent"
    if s in {"ENTRY", "INSTALLATION", "VARIATION"}:
        return "Reviewing"
    if s in {"SETTLEMENT"} and r == "PASS":
        return "Approved"
    if r == "FAIL":
        return "Failed"
    return "Reviewing"


def eval_threshold(operator: str, threshold: Any, measured_value: float | None) -> dict[str, Any]:
    op = _to_text(operator).strip().lower()
    val = measured_value
    if val is None:
        return {"status": "PENDING", "ok": False}
    if isinstance(threshold, list) and len(threshold) >= 2:
        lo = _to_float(threshold[0])
        hi = _to_float(threshold[1])
        if lo is None or hi is None:
            return {"status": "PENDING", "ok": False}
        ok = (val >= min(lo, hi)) and (val <= max(lo, hi))
        return {
            "status": "SUCCESS" if ok else "FAIL",
            "ok": ok,
            "normalized_operator": "range",
            "threshold": [min(lo, hi), max(lo, hi)],
        }
    t = _to_float(threshold)
    if t is None:
        return {"status": "PENDING", "ok": False}
    if op in {">=", "gte"}:
        ok = val >= t
    elif op in {"<=", "lte"}:
        ok = val <= t
    elif op == ">":
        ok = val > t
    elif op == "<":
        ok = val < t
    else:
        ok = val == t
    return {"status": "SUCCESS" if ok else "FAIL", "ok": ok, "normalized_operator": op or "=", "threshold": t}


def derive_display_metadata(sd: dict[str, Any], *, item_no: str, item_name: str) -> dict[str, str]:
    raw_meta = _as_dict(sd.get("metadata"))
    hierarchy = _as_dict(sd.get("hierarchy"))
    chapter_code = _to_text(hierarchy.get("chapter_code") or "").strip()
    section_code = _to_text(hierarchy.get("section_code") or "").strip()
    subgroup_code = _to_text(hierarchy.get("subgroup_code") or "").strip()
    wbs_path = _to_text(raw_meta.get("wbs_path") or hierarchy.get("wbs_path") or "").strip()

    unit_project = _to_text(raw_meta.get("unit_project") or sd.get("division") or "").strip()
    if not unit_project:
        if chapter_code:
            unit_project = f"{chapter_code}章"
        else:
            head = _to_text(item_no).strip().split("-")[0] if _to_text(item_no).strip() else ""
            unit_project = f"{head}章" if head else "单位工程未命名"

    subdivision_project = _to_text(raw_meta.get("subdivision_project") or sd.get("subdivision") or "").strip()
    if not subdivision_project:
        if section_code and subgroup_code and section_code != subgroup_code:
            subdivision_project = f"{section_code}节/ {subgroup_code}"
        elif subgroup_code:
            subdivision_project = subgroup_code
        elif section_code:
            subdivision_project = section_code
        elif _to_text(item_no).strip():
            subdivision_project = _to_text(item_no).strip()
    if _to_text(item_name).strip():
        subdivision_project = f"{subdivision_project} {item_name}".strip() if subdivision_project else _to_text(item_name).strip()

    return {
        "unit_project": unit_project,
        "subdivision_project": subdivision_project,
        "wbs_path": wbs_path,
    }


def build_gatekeeper(dual_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_compliant": bool(dual_gate.get("qc_pass_count")),
        "lab_ok": bool(dual_gate.get("lab_pass_count")),
        "dual_ok": bool(dual_gate.get("ok")),
        "qc_pass_count": int(dual_gate.get("qc_pass_count") or 0),
        "lab_pass_count": int(dual_gate.get("lab_pass_count") or 0),
        "latest_lab_pass_proof_id": _to_text(dual_gate.get("latest_lab_pass_proof_id") or "").strip(),
    }


__all__ = [
    "build_gatekeeper",
    "container_status_from_stage",
    "derive_display_metadata",
    "eval_threshold",
]

