"""
Report evaluation and statistics helpers.
services/api/reports_eval_service.py
"""

from __future__ import annotations

import re
from typing import Any

from services.api.specir_engine import derive_spec_uri as specir_derive_spec_uri
from services.api.specir_engine import evaluate_measurements as specir_evaluate_measurements
from services.api.specir_engine import resolve_spec_rule as specir_resolve_spec_rule


def report_stats_from_proofs(proofs: list[dict[str, Any]]) -> tuple[int, int, int, int, float]:
    total = len(proofs or [])
    pass_count = 0
    fail_count = 0
    warn_count = 0
    for proof in proofs or []:
        result = effective_result_from_proof(proof)
        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
        elif result == "OBSERVE":
            warn_count += 1
    pass_rate = round(pass_count / total * 100, 1) if total else 0
    return total, pass_count, warn_count, fail_count, pass_rate


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        text = str(value or "").strip()
        if not text:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _effective_operator(sd: dict[str, Any], *, default: str = "<=") -> str:
    op = str(
        sd.get("standard_op")
        or sd.get("standard_operator")
        or sd.get("operator")
        or sd.get("comparator")
        or sd.get("compare")
        or ""
    ).strip().lower()
    if op in {"+-", "+/-", "\u00b1", "±", "plusminus", "plus_minus"}:
        return "±"
    return op or default


def _parse_limit(limit: Any) -> float | None:
    text = str(limit or "").strip()
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return abs(float(m.group(0)))
    except Exception:
        return None


def _coerce_values(values_raw: Any, fallback_value: Any = None) -> list[float]:
    values: list[float] = []
    if isinstance(values_raw, list):
        for item in values_raw:
            v = _to_float(item)
            if v is not None:
                values.append(v)
    fb = _to_float(fallback_value)
    if values and fb is not None:
        # Keep in sync with docx_engine: repair legacy [0] placeholder values.
        if len(values) == 1 and abs(values[0]) < 1e-9 and abs(fb) >= 1e-9:
            return [fb]
        return values
    if not values and fb is not None:
        return [fb]
    return values


def effective_result_from_proof(proof: dict[str, Any]) -> str:
    sd = proof.get("state_data") if isinstance(proof.get("state_data"), dict) else {}
    values = _coerce_values(sd.get("values"), fallback_value=sd.get("value"))
    spec_uri = specir_derive_spec_uri(
        sd,
        row_norm_uri=proof.get("norm_uri"),
        fallback_norm_ref=sd.get("norm_ref"),
    )
    resolved = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=sd.get("type_name") or sd.get("test_name") or sd.get("type"),
        test_type=sd.get("type") or sd.get("test_type"),
        test_name=sd.get("type_name") or sd.get("test_name"),
        context={
            "component_type": sd.get("component_type") or sd.get("structure_type"),
            "stake": sd.get("stake") or sd.get("location"),
        },
        sb=None,
    )
    op = str(resolved.get("operator") or _effective_operator(sd)).strip()
    threshold = resolved.get("threshold")
    if threshold is None:
        threshold = _to_float(sd.get("standard_value"))
    if threshold is None:
        threshold = _to_float(sd.get("standard"))
    if threshold is None:
        threshold = _to_float(sd.get("design"))
    tolerance = resolved.get("tolerance")
    if tolerance is None:
        tolerance = _parse_limit(sd.get("standard_tolerance"))
    if tolerance is None:
        tolerance = _parse_limit(sd.get("tolerance"))
    if tolerance is None:
        tolerance = _parse_limit(sd.get("limit"))
    evaluated = specir_evaluate_measurements(
        values=values,
        operator=op,
        threshold=_to_float(threshold),
        tolerance=_to_float(tolerance),
        fallback_result=proof.get("result") or "PENDING",
    )
    return str(evaluated.get("result") or proof.get("result") or "PENDING").upper()


def conclusion_from_counts(*, pass_count: int, warn_count: int, fail_count: int) -> str:
    if fail_count == 0 and warn_count == 0:
        return "全部合格：本次检测所有项目均符合规范要求"
    if fail_count == 0:
        return f"基本合格：{warn_count}项需持续观察"
    return f"存在不合格项：{fail_count}项不合格，需整改后复测"
