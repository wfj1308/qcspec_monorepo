from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.boqpeg.runtime.process_chain import (
    create_process_chain,
    get_process_materials,
    pile_component_uri,
    submit_process_table,
)


def _all_required_material_state(chain: dict[str, object]) -> dict[str, dict[str, str]]:
    state: dict[str, dict[str, str]] = {}
    for step in chain.get("steps", []):  # type: ignore[union-attr]
        if not isinstance(step, dict):
            continue
        for item in step.get("material_requirements", []):  # type: ignore[union-attr]
            if not isinstance(item, dict):
                continue
            code = str(item.get("material_code") or "").strip()
            if not code:
                continue
            state[code.lower()] = {"status": "approved", "iqc_uri": f"v://cost/iqc/{code}-batch"}
    return state


def _ordered_tables_from_chain(chain: dict[str, object]) -> list[str]:
    ordered: list[str] = []
    steps = chain.get("steps", [])
    if not isinstance(steps, list):
        return ordered
    for step in steps:
        if not isinstance(step, dict):
            continue
        required_tables = step.get("required_tables", [])
        if not isinstance(required_tables, list):
            continue
        for table_name in required_tables:
            text = str(table_name or "").strip()
            if text:
                ordered.append(text)
    return ordered


def test_create_process_chain_preview_defaults_to_drilled_pile_steps() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    out = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        chain_kind="drilled_pile",
        boq_item_ref="v://cn.zhongbei/YADGS/boq/403-1-2",
        commit=False,
    )
    assert out["ok"] is True
    assert out["chain"]["current_step"] == "pile-prepare-01"
    assert out["chain"]["state_matrix"]["total_steps"] == 6
    assert out["chain"]["state_matrix"]["completed_steps"] == 0
    assert out["chain"]["state_matrix"]["finalproof_ready"] is False
    assert out["chain"]["state_matrix"]["total_required_materials"] >= 1


def test_submit_process_table_requires_preconditions() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    created = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        commit=False,
    )
    chain = created["chain"]
    material_state = _all_required_material_state(chain)
    table_from_step_2 = str(chain["steps"][1]["required_tables"][0])

    with pytest.raises(HTTPException) as exc:
        submit_process_table(
            sb=None,
            project_uri="v://cn.zhongbei/YADGS",
            component_uri=component_uri,
            table_name=table_from_step_2,
            proof_hash="proof-hole",
            result="PASS",
            chain_snapshot={**chain, "material_state": material_state},
            commit=False,
        )
    assert exc.value.status_code == 409


def test_submit_process_table_requires_material_iqc() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    created = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        commit=False,
    )
    chain = created["chain"]
    first_table = str(chain["steps"][0]["required_tables"][0])
    with pytest.raises(HTTPException) as exc:
        submit_process_table(
            sb=None,
            project_uri="v://cn.zhongbei/YADGS",
            component_uri=component_uri,
            table_name=first_table,
            proof_hash="proof-step-1",
            result="PASS",
            chain_snapshot=chain,
            commit=False,
        )
    assert exc.value.status_code == 409
    assert "material iqc not approved" in str(exc.value.detail)


def test_submit_process_table_advances_step_and_finalproof_ready() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    state = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        boq_item_ref="v://cn.zhongbei/YADGS/boq/403-1-2",
        commit=False,
    )["chain"]
    material_state = _all_required_material_state(state)
    state["material_state"] = material_state

    ordered_tables = _ordered_tables_from_chain(state)
    assert len(ordered_tables) > 0
    for idx, table_name in enumerate(ordered_tables, start=1):
        out = submit_process_table(
            sb=None,
            project_uri="v://cn.zhongbei/YADGS",
            component_uri=component_uri,
            table_name=table_name,
            proof_hash=f"proof-{idx}",
            result="PASS",
            chain_snapshot=state,
            commit=False,
        )
        state = out["chain"]
        state["material_state"] = material_state

    assert state["state_matrix"]["completed_steps"] == 6
    assert state["state_matrix"]["pending_tables"] == 0
    assert state["state_matrix"]["finalproof_ready"] is True
    assert out["proofs"]["finalproof"] is not None
    assert out["boq_state_update"]["state_matrix_delta"]["signed"] == 1


def test_get_process_materials_aggregates_step_status() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    created = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        commit=False,
    )
    chain = created["chain"]
    chain["material_state"] = {
        "steel-casing": {"status": "approved", "iqc_uri": "v://cost/iqc/steel-casing-batch001"},
    }
    out = get_process_materials(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        chain_snapshot=chain,
    )
    assert out["ok"] is True
    assert out["summary"]["total_required"] >= 1
    assert out["summary"]["approved"] >= 1
    assert isinstance(out["materials"], list)


def test_submit_process_table_requires_inspection_batch(monkeypatch) -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    created = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        commit=False,
    )
    chain = created["chain"]
    chain["material_state"] = _all_required_material_state(chain)
    first_table = str(chain["steps"][0]["required_tables"][0])

    monkeypatch.setattr(
        "services.api.domain.boqpeg.runtime.process_chain._step_inspection_batch_gaps",
        lambda **_: [{"material_code": "concrete-c50", "required_qty": 25.0, "actual_qty": 0.0}],
    )

    with pytest.raises(HTTPException) as exc:
        submit_process_table(
            sb=None,
            project_uri="v://cn.zhongbei/YADGS",
            component_uri=component_uri,
            table_name=first_table,
            proof_hash="proof-step-1",
            result="PASS",
            chain_snapshot=chain,
            commit=False,
        )

    assert exc.value.status_code == 409
    assert "inspection batch material_qty not satisfied" in str(exc.value.detail)


def test_submit_process_table_writes_step_material_cost(monkeypatch) -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    created = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        commit=False,
    )
    chain = created["chain"]
    chain["material_state"] = _all_required_material_state(chain)
    first_table = str(chain["steps"][0]["required_tables"][0])

    monkeypatch.setattr(
        "services.api.domain.boqpeg.runtime.process_chain._step_inspection_batch_gaps",
        lambda **_: [],
    )
    monkeypatch.setattr(
        "services.api.domain.boqpeg.runtime.process_chain.summarize_component_step_materials",
        lambda **_: {
            "concrete-c50": {
                "material_code": "concrete-c50",
                "qty": 28.0,
                "unit": "m3",
                "cost": 16240.0,
                "records": [],
            }
        },
    )

    out = submit_process_table(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        table_name=first_table,
        proof_hash="proof-step-1",
        result="PASS",
        chain_snapshot=chain,
        commit=False,
    )

    state_data = out["proofs"]["table_submission_proof"]["state_data"]
    assert float(state_data["material_cost"]) == 16240.0
    assert isinstance(state_data["material_cost_items"], list)
    assert state_data["material_cost_items"][0]["material_code"] == "concrete-c50"
