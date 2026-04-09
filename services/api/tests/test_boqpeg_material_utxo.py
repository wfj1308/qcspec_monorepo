from __future__ import annotations

from services.api.domain.boqpeg.runtime.material_utxo import (
    create_inspection_batch,
    get_material_utxo_by_component,
    get_material_utxo_by_iqc,
    summarize_component_material_cost,
    summarize_component_step_materials,
)


def _fake_iqc_row() -> dict:
    return {
        "proof_id": "GP-IQC-001",
        "proof_hash": "hash-iqc-001",
        "created_at": "2026-04-05T08:00:00+00:00",
        "state_data": {
            "proof_kind": "iqc_material_submit",
            "project_uri": "v://project/demo",
            "component_uri": "v://project/demo/bridge/YK0+500-main/pile/P3",
            "material_code": "concrete-c50",
            "batch_no": "batch001",
            "unit": "m3",
            "total_qty": 200.0,
            "unit_price": 580.0,
            "supplier": "demo-supplier",
            "status": "approved",
            "iqc_uri": "v://cost/iqc/concrete-c50-batch001",
            "submitted_at": "2026-04-05T08:00:00+00:00",
        },
    }


def _fake_utxo_row(*, utxo_id: str, qty: float, created_at: str = "2026-04-05T09:00:00+00:00") -> dict:
    used = qty
    remaining = 200.0 - used
    return {
        "proof_id": f"GP-MATERIAL-UTXO-{utxo_id}",
        "proof_hash": f"hash-{utxo_id}",
        "created_at": created_at,
        "state_data": {
            "proof_kind": "material_inspection_batch",
            "utxo_id": utxo_id,
            "material_code": "concrete-c50",
            "batch_no": "batch001",
            "iqc_uri": "v://cost/iqc/concrete-c50-batch001",
            "total_qty": 200.0,
            "used_qty": used,
            "remaining": remaining,
            "unit": "m3",
            "unit_price": 580.0,
            "supplier": "demo-supplier",
            "inspection_batch_no": f"JYP-{utxo_id}",
            "inspection_form": "bridge9",
            "inspection_uri": f"v://cost/inspection-batch/{utxo_id.lower()}",
            "inspection_result": "approved",
            "component_uri": "v://project/demo/bridge/YK0+500-main/pile/P3",
            "process_step": "pile-pour-04",
            "quantity": qty,
            "status": "consumed",
            "v_uri": f"v://cost/material-utxo/{utxo_id}",
            "data_hash": f"data-{utxo_id}",
            "signed_by": "v://project/demo/executor/inspector-a",
            "created_at": created_at,
        },
    }


def test_create_inspection_batch_updates_remaining(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.api.domain.boqpeg.runtime.material_utxo._find_iqc_record_by_uri",
        lambda **_: _fake_iqc_row(),
    )
    monkeypatch.setattr(
        "services.api.domain.boqpeg.runtime.material_utxo._iter_material_utxo_rows",
        lambda **_: [],
    )

    out = create_inspection_batch(
        sb=None,
        iqc_uri="v://cost/iqc/concrete-c50-batch001",
        component_uri="v://project/demo/bridge/YK0+500-main/pile/P3",
        process_step="pile-pour-04",
        quantity=28.0,
        unit="m3",
        inspection_form="bridge9",
        inspection_batch_no="JYP-2026-0405-001",
        inspection_result="approved",
        test_results={"slump": 180},
        executor_uri="v://project/demo/executor/inspector-a",
        owner_uri="v://project/demo/role/system",
        commit=False,
    )

    assert out.material_code == "concrete-c50"
    assert float(out.used_qty) == 28.0
    assert float(out.remaining) == 172.0
    assert out.utxo.status == "consumed"
    assert out.inspection_uri.startswith("v://cost/inspection-batch/")


def test_material_utxo_query_and_cost_summary(monkeypatch) -> None:
    rows = [
        _fake_utxo_row(utxo_id="UTXO-001", qty=28.0, created_at="2026-04-05T09:00:00+00:00"),
        _fake_utxo_row(utxo_id="UTXO-002", qty=35.0, created_at="2026-04-06T09:00:00+00:00"),
    ]
    monkeypatch.setattr(
        "services.api.domain.boqpeg.runtime.material_utxo._find_iqc_record_by_uri",
        lambda **_: _fake_iqc_row(),
    )
    monkeypatch.setattr(
        "services.api.domain.boqpeg.runtime.material_utxo._iter_material_utxo_rows",
        lambda **_: rows,
    )

    by_iqc = get_material_utxo_by_iqc(sb=None, iqc_uri="v://cost/iqc/concrete-c50-batch001")
    assert by_iqc.scope == "iqc"
    assert float(by_iqc.summary["used_qty"]) == 63.0
    assert float(by_iqc.summary["remaining"]) == 137.0
    assert float(by_iqc.summary["material_cost"]) == 36540.0

    by_component = get_material_utxo_by_component(
        sb=None,
        component_uri="v://project/demo/bridge/YK0+500-main/pile/P3",
    )
    assert by_component.scope == "component"
    assert float(by_component.summary["total_cost"]) == 36540.0

    grouped = summarize_component_step_materials(
        sb=None,
        component_uri="v://project/demo/bridge/YK0+500-main/pile/P3",
        process_step="pile-pour-04",
    )
    assert float(grouped["concrete-c50"]["qty"]) == 63.0
    assert float(grouped["concrete-c50"]["cost"]) == 36540.0

    total = summarize_component_material_cost(
        sb=None,
        component_uri="v://project/demo/bridge/YK0+500-main/pile/P3",
    )
    assert float(total["total_material_cost"]) == 36540.0
