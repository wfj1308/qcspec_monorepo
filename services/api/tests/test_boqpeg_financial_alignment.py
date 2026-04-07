from __future__ import annotations

from services.api.domain.boqpeg.runtime.financial_alignment import (
    forward_expand_bom,
    parse_contract_rows_from_upload,
    progress_payment_check,
    reverse_conservation_check,
    unified_alignment_check,
)


def _sample_xlsx_bytes() -> bytes:
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BOQ"
    ws.append(
        [
            "item_no",
            "name",
            "unit",
            "division",
            "subdivision",
            "hierarchy",
            "design_quantity",
            "unit_price",
            "approved_quantity",
        ]
    )
    ws.append(["403-1-2", "Spillway concrete", "m3", "Dam", "Spillway", "Dam/Spillway", 120, 500, 100])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_contract_rows_from_upload_returns_six_fields() -> None:
    out = parse_contract_rows_from_upload(upload_file_name="BOQ.xlsx", upload_content=_sample_xlsx_bytes())
    assert out["ok"] is True
    assert out["count"] == 1
    row = out["rows"][0]
    assert row["code"] == "403-1-2"
    assert row["description"] == "Spillway concrete"
    assert row["unit"] == "m3"
    assert row["quantity"] == 100.0
    assert row["unit_price"] == 500.0
    assert row["amount"] == 50000.0


def test_forward_expand_bom_builds_monthly_plan() -> None:
    out = forward_expand_bom(
        body={
            "node_uri": "v://tz.nest-dam/bill28/spillway/concrete/",
            "months": ["2026-04", "2026-05"],
            "boq_item": {"quantity": 100, "unit_price": 500},
            "quota_lines": [
                {"material_code": "cement", "material_name": "Cement", "unit": "kg", "quota_per_unit": 350, "unit_price": 0.4},
                {"material_code": "water", "material_name": "Water", "unit": "m3", "quota_per_unit": 0.18, "unit_price": 5},
            ],
        }
    )
    assert out["ok"] is True
    assert out["contract"]["income"] == 50000.0
    assert len(out["bom"]["materials"]) == 2
    assert len(out["bom"]["funding_curve"]) == 2
    assert out["bom"]["total_cost"] > 0


def test_reverse_conservation_thresholds() -> None:
    out = reverse_conservation_check(
        body={
            "node_uri": "v://tz.nest-dam/bill28/spillway/concrete/",
            "proof_completed_quantity": 100,
            "quota_lines": [
                {"material_code": "cement", "quota_per_unit": 350, "unit_price": 0.4},
                {"material_code": "water", "quota_per_unit": 0.18, "unit_price": 5},
            ],
            "actual_consumption_lines": [
                {"material_code": "cement", "quantity": 35000},
                {"material_code": "water", "quantity": 18},
            ],
        }
    )
    assert out["ok"] is True
    assert out["band"] == "normal"
    assert out["deviation_percent"] == 0.0
    assert out["conservation_factor"] == 1.0


def test_progress_payment_check_computes_margin() -> None:
    out = progress_payment_check(
        body={
            "node_uri": "v://tz.nest-dam/bill28/spillway/concrete/",
            "proof_completed_quantity": 80,
            "boq_unit_price": 500,
            "advance_recovery": 2000,
            "retention": 1000,
            "actual_cost": 30000,
        }
    )
    assert out["ok"] is True
    assert out["period"]["receivable"] == 40000.0
    assert out["period"]["declared_amount"] == 37000.0
    assert out["period"]["gross_profit"] == 7000.0


def test_unified_alignment_emits_warning_when_cost_exceeds_income() -> None:
    out = unified_alignment_check(
        body={
            "node_uri": "v://tz.nest-dam/bill28/spillway/concrete/",
            "boq_item": {"quantity": 10, "unit_price": 100},
            "proof_completed_quantity": 10,
            "quota_lines": [
                {"material_code": "cement", "quota_per_unit": 350, "unit_price": 1.0},
            ],
            "actual_consumption_lines": [
                {"material_code": "cement", "quantity": 3500},
            ],
        }
    )
    assert out["ok"] is True
    codes = {sig["code"] for sig in out["signals"]}
    assert "cost_over_contract_income" in codes
