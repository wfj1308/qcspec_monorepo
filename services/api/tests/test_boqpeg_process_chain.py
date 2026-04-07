from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.boqpeg.runtime.process_chain import (
    create_process_chain,
    pile_component_uri,
    submit_process_table,
)


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


def test_submit_process_table_requires_preconditions() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    created = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        commit=False,
    )
    with pytest.raises(HTTPException) as exc:
        submit_process_table(
            sb=None,
            project_uri="v://cn.zhongbei/YADGS",
            component_uri=component_uri,
            table_name="桥施7表",
            proof_hash="proof-hole",
            result="PASS",
            chain_snapshot=created["chain"],
            commit=False,
        )
    assert exc.value.status_code == 409


def test_submit_process_table_advances_step_and_finalproof_ready() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")
    state = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        boq_item_ref="v://cn.zhongbei/YADGS/boq/403-1-2",
        commit=False,
    )["chain"]

    ordered_tables = [
        "桥施2表",
        "桥施7表",
        "桥施46表",
        "桥施47表",
        "桥施混凝土浇筑记录表",
        "桥施坍落度检查记录",
        "桥施桩基承载力检测表",
        "桥施桩基完整性检测记录",
        "隐蔽工程验收记录",
        "分项工程质量验收记录表",
    ]
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

    assert state["state_matrix"]["completed_steps"] == 6
    assert state["state_matrix"]["pending_tables"] == 0
    assert state["state_matrix"]["finalproof_ready"] is True
    assert out["proofs"]["finalproof"] is not None
    assert out["boq_state_update"]["state_matrix_delta"]["signed"] == 1
