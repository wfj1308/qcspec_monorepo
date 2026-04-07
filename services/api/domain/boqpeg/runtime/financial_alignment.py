"""BOQPeg financial-alignment engines for contract, cost, proof, and cashflow."""

from __future__ import annotations

from datetime import UTC, datetime
from statistics import median
from typing import Any

from services.api.domain.boqpeg.runtime.parser import parse_boq_upload


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


def _round(value: float, ndigits: int = 6) -> float:
    return round(float(value), ndigits)


def _month_labels(body: dict[str, Any]) -> list[str]:
    months = body.get("months")
    if isinstance(months, list):
        out = [str(x).strip() for x in months if str(x).strip()]
        if out:
            return out
    return [datetime.now(UTC).strftime("%Y-%m")]


def _normalize_distribution(raw: Any, n: int) -> list[float]:
    if n <= 0:
        return []
    if isinstance(raw, list):
        vals = [_to_float(x, 0.0) for x in raw]
    else:
        vals = []
    if len(vals) < n:
        vals.extend([0.0] * (n - len(vals)))
    vals = vals[:n]
    total = sum(max(v, 0.0) for v in vals)
    if total <= 1e-9:
        return [_round(1.0 / n, 10) for _ in range(n)]
    return [_round(max(v, 0.0) / total, 10) for v in vals]


def parse_contract_rows_from_upload(*, upload_file_name: str, upload_content: bytes) -> dict[str, Any]:
    items = parse_boq_upload(upload_file_name, upload_content)
    rows: list[dict[str, Any]] = []
    for item in items:
        quantity = item.approved_quantity
        if quantity is None:
            quantity = item.design_quantity
        qty = _to_float(quantity, 0.0)
        price = _to_float(item.unit_price, 0.0)
        amount = _round(qty * price, 2)
        rows.append(
            {
                "code": item.item_no,
                "description": item.name,
                "unit": item.unit,
                "quantity": _round(qty, 6),
                "unit_price": _round(price, 6),
                "amount": amount,
            }
        )
    return {
        "ok": True,
        "count": len(rows),
        "rows": rows,
    }


def forward_expand_bom(*, body: dict[str, Any]) -> dict[str, Any]:
    node_uri = _to_text(body.get("node_uri")).strip()
    boq_item = body.get("boq_item") if isinstance(body.get("boq_item"), dict) else {}
    quantity = _to_float((boq_item or {}).get("quantity"), 0.0)
    unit_price = _to_float((boq_item or {}).get("unit_price"), 0.0)
    months = _month_labels(body)
    quota_lines = body.get("quota_lines") if isinstance(body.get("quota_lines"), list) else []

    material_rows: list[dict[str, Any]] = []
    funding_curve = {m: 0.0 for m in months}
    total_cost = 0.0
    for line in quota_lines:
        if not isinstance(line, dict):
            continue
        material_code = _to_text(line.get("material_code")).strip()
        material_name = _to_text(line.get("material_name")).strip() or material_code or "material"
        unit = _to_text(line.get("unit")).strip()
        quota_per_unit = _to_float(line.get("quota_per_unit"), 0.0)
        material_price = _to_float(line.get("unit_price"), 0.0)
        total_qty = quantity * quota_per_unit
        total_line_cost = total_qty * material_price
        total_cost += total_line_cost

        dist = _normalize_distribution(line.get("monthly_distribution"), len(months))
        monthly_plan: list[dict[str, Any]] = []
        for idx, month in enumerate(months):
            month_qty = total_qty * dist[idx]
            month_cost = total_line_cost * dist[idx]
            funding_curve[month] = funding_curve.get(month, 0.0) + month_cost
            monthly_plan.append(
                {
                    "month": month,
                    "quantity": _round(month_qty, 6),
                    "cost": _round(month_cost, 2),
                }
            )

        material_rows.append(
            {
                "material_code": material_code,
                "material_name": material_name,
                "unit": unit,
                "quota_per_unit": _round(quota_per_unit, 6),
                "unit_price": _round(material_price, 6),
                "total_quantity": _round(total_qty, 6),
                "total_cost": _round(total_line_cost, 2),
                "monthly_plan": monthly_plan,
            }
        )

    contract_income = quantity * unit_price
    return {
        "ok": True,
        "node_uri": node_uri,
        "contract": {
            "quantity": _round(quantity, 6),
            "unit_price": _round(unit_price, 6),
            "income": _round(contract_income, 2),
        },
        "bom": {
            "materials": material_rows,
            "total_cost": _round(total_cost, 2),
            "funding_curve": [{"month": m, "cost": _round(funding_curve[m], 2)} for m in months],
        },
    }


def reverse_conservation_check(*, body: dict[str, Any]) -> dict[str, Any]:
    node_uri = _to_text(body.get("node_uri")).strip()
    proof_completed_qty = _to_float(body.get("proof_completed_quantity"), 0.0)
    quota_lines = body.get("quota_lines") if isinstance(body.get("quota_lines"), list) else []
    actual_lines_raw = body.get("actual_consumption_lines") if isinstance(body.get("actual_consumption_lines"), list) else []
    actual_by_code: dict[str, float] = {}
    for row in actual_lines_raw:
        if not isinstance(row, dict):
            continue
        code = _to_text(row.get("material_code")).strip()
        if not code:
            continue
        actual_by_code[code] = actual_by_code.get(code, 0.0) + _to_float(row.get("quantity"), 0.0)

    material_checks: list[dict[str, Any]] = []
    theoretical_candidates: list[float] = []
    weighted_cost = 0.0
    for quota in quota_lines:
        if not isinstance(quota, dict):
            continue
        code = _to_text(quota.get("material_code")).strip()
        if not code:
            continue
        quota_per_unit = _to_float(quota.get("quota_per_unit"), 0.0)
        if quota_per_unit <= 0:
            continue
        actual_qty = _to_float(actual_by_code.get(code), 0.0)
        theory_qty = actual_qty / quota_per_unit
        theoretical_candidates.append(theory_qty)
        material_price = _to_float(quota.get("unit_price"), 0.0)
        weighted_cost += actual_qty * material_price
        material_checks.append(
            {
                "material_code": code,
                "actual_quantity": _round(actual_qty, 6),
                "quota_per_unit": _round(quota_per_unit, 6),
                "theoretical_completed_quantity": _round(theory_qty, 6),
            }
        )

    if theoretical_candidates:
        theoretical_qty = float(median(theoretical_candidates))
    else:
        theoretical_qty = 0.0
    base = max(abs(proof_completed_qty), 1e-9)
    deviation_ratio = abs(theoretical_qty - proof_completed_qty) / base
    deviation_percent = deviation_ratio * 100.0
    if deviation_percent <= 3.0:
        band = "normal"
        conservation_factor = 1.0
    elif deviation_percent <= 8.0:
        band = "warning"
        conservation_factor = 0.6
    else:
        band = "review"
        conservation_factor = 0.2

    return {
        "ok": True,
        "node_uri": node_uri,
        "proof_completed_quantity": _round(proof_completed_qty, 6),
        "theoretical_completed_quantity": _round(theoretical_qty, 6),
        "deviation_ratio": _round(deviation_ratio, 6),
        "deviation_percent": _round(deviation_percent, 4),
        "band": band,
        "conservation_factor": _round(conservation_factor, 4),
        "actual_cost": _round(weighted_cost, 2),
        "material_checks": material_checks,
    }


def progress_payment_check(*, body: dict[str, Any]) -> dict[str, Any]:
    node_uri = _to_text(body.get("node_uri")).strip()
    proof_completed_qty = _to_float(body.get("proof_completed_quantity"), 0.0)
    boq_unit_price = _to_float(body.get("boq_unit_price"), 0.0)
    advance_recovery = _to_float(body.get("advance_recovery"), 0.0)
    retention = _to_float(body.get("retention"), 0.0)
    quality_deduction = _to_float(body.get("quality_deduction"), 0.0)
    other_deductions = _to_float(body.get("other_deductions"), 0.0)
    actual_cost = _to_float(body.get("actual_cost"), 0.0)

    receivable = proof_completed_qty * boq_unit_price
    total_deduction = advance_recovery + retention + quality_deduction + other_deductions
    declared_amount = receivable - total_deduction
    gross_profit = declared_amount - actual_cost
    gross_margin_rate = (gross_profit / declared_amount) if abs(declared_amount) > 1e-9 else 0.0

    prev_receivable = _to_float(body.get("cumulative_receivable_before"), 0.0)
    prev_cost = _to_float(body.get("cumulative_cost_before"), 0.0)
    cumulative_receivable = prev_receivable + declared_amount
    cumulative_cost = prev_cost + actual_cost
    cumulative_gross_profit = cumulative_receivable - cumulative_cost
    cumulative_gross_margin_rate = (
        cumulative_gross_profit / cumulative_receivable if abs(cumulative_receivable) > 1e-9 else 0.0
    )

    return {
        "ok": True,
        "node_uri": node_uri,
        "period": {
            "proof_completed_quantity": _round(proof_completed_qty, 6),
            "boq_unit_price": _round(boq_unit_price, 6),
            "receivable": _round(receivable, 2),
            "advance_recovery": _round(advance_recovery, 2),
            "retention": _round(retention, 2),
            "quality_deduction": _round(quality_deduction, 2),
            "other_deductions": _round(other_deductions, 2),
            "declared_amount": _round(declared_amount, 2),
            "actual_cost": _round(actual_cost, 2),
            "gross_profit": _round(gross_profit, 2),
            "gross_margin_rate": _round(gross_margin_rate, 6),
        },
        "cumulative": {
            "receivable": _round(cumulative_receivable, 2),
            "cost": _round(cumulative_cost, 2),
            "gross_profit": _round(cumulative_gross_profit, 2),
            "gross_margin_rate": _round(cumulative_gross_margin_rate, 6),
        },
    }


def unified_alignment_check(*, body: dict[str, Any]) -> dict[str, Any]:
    node_uri = _to_text(body.get("node_uri")).strip()
    boq_item = body.get("boq_item") if isinstance(body.get("boq_item"), dict) else {}
    quantity = _to_float((boq_item or {}).get("quantity"), 0.0)
    unit_price = _to_float((boq_item or {}).get("unit_price"), 0.0)

    forward = forward_expand_bom(body=body)
    reverse = reverse_conservation_check(body=body)

    payment_body = dict(body)
    payment_body["boq_unit_price"] = unit_price
    if payment_body.get("actual_cost") is None:
        payment_body["actual_cost"] = reverse.get("actual_cost")
    payment = progress_payment_check(body=payment_body)

    contract_income = quantity * unit_price
    planned_cost = _to_float(forward.get("bom", {}).get("total_cost"), 0.0)
    actual_cost = _to_float(reverse.get("actual_cost"), 0.0)
    deviation_percent = _to_float(reverse.get("deviation_percent"), 0.0)

    signals: list[dict[str, Any]] = []
    if deviation_percent > 8.0:
        signals.append(
            {
                "severity": "critical",
                "code": "proof_conservation_break",
                "message": "proof completed quantity deviates from material-theoretical quantity by more than 8%",
            }
        )
    elif deviation_percent > 3.0:
        signals.append(
            {
                "severity": "warning",
                "code": "proof_conservation_warn",
                "message": "proof completed quantity deviates from material-theoretical quantity by more than 3%",
            }
        )
    if actual_cost > contract_income and contract_income > 0:
        signals.append(
            {
                "severity": "warning",
                "code": "cost_over_contract_income",
                "message": "actual material cost exceeds contract-side income at this node",
            }
        )
    if planned_cost > contract_income and contract_income > 0:
        signals.append(
            {
                "severity": "warning",
                "code": "planned_bom_over_contract_income",
                "message": "planned BOM cost exceeds contract-side income at this node",
            }
        )
    if not signals:
        signals.append(
            {
                "severity": "info",
                "code": "alignment_healthy",
                "message": "contract income, cost side, and proof side are within configured thresholds",
            }
        )

    return {
        "ok": True,
        "node_uri": node_uri,
        "contract_income": _round(contract_income, 2),
        "planned_bom_cost": _round(planned_cost, 2),
        "actual_cost": _round(actual_cost, 2),
        "engines": {
            "forward_bom": forward,
            "reverse_conservation": reverse,
            "progress_payment": payment,
        },
        "signals": signals,
        "timestamp": datetime.now(UTC).isoformat(),
    }


__all__ = [
    "forward_expand_bom",
    "parse_contract_rows_from_upload",
    "progress_payment_check",
    "reverse_conservation_check",
    "unified_alignment_check",
]

