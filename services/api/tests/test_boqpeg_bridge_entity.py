from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import HTTPException

from services.api.domain.boqpeg.runtime.bridge_entity import (
    bind_bridge_sub_items,
    create_bridge_entity,
    create_pile_entity,
    get_bridge_pile_detail,
    get_full_line_pile_summary,
    get_pile_entity_detail,
    update_pile_state_matrix,
)


def test_create_bridge_entity_preview() -> None:
    out = create_bridge_entity(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        bridge_name="YK0+500 main",
        parent_section="K0~K20",
        boq_chapter="403-1-2",
        commit=False,
    )
    assert out["ok"] is True
    assert out["bridge_uri"].startswith("v://cn.zhongbei/YADGS/bridge/")
    assert out["entity"]["bridge_name"] == "YK0+500 main"
    assert out["entity"]["total_piles"] == 0
    assert out["proofs"]["mapping_proof"]["state_data"]["proof_kind"] == "bridge_mapping"


def test_bind_bridge_sub_items_recomputes_pile_totals() -> None:
    out = bind_bridge_sub_items(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        bridge_name="YK0+500 main",
        sub_items=[
            {"component_uri": "v://cn.zhongbei/YADGS/bridge/YK0+500/pile/1", "component_type": "pile"},
            {"component_uri": "v://cn.zhongbei/YADGS/bridge/YK0+500/cap/1", "component_type": "cap"},
            {"component_uri": "v://cn.zhongbei/YADGS/bridge/YK0+500/pile/2", "component_type": "pile"},
        ],
        commit=False,
    )
    assert out["ok"] is True
    assert out["entity"]["total_piles"] == 2
    assert len(out["entity"]["sub_items"]) == 3


def test_create_pile_entity_preview_has_independent_uri() -> None:
    out = create_pile_entity(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        bridge_name="YK0+500-main",
        pile_id="P3",
        pile_type="bored-pile",
        length_m=28.5,
        commit=False,
    )
    assert out["ok"] is True
    assert out["pile_uri"].endswith("/bridge/yk0-500-main/pile/P3")
    assert out["pile_entity"]["entity_type"] == "pile_entity"
    assert out["proofs"]["mapping_proof"]["state_data"]["proof_kind"] == "pile_mapping"


def test_update_pile_state_preview_updates_state_matrix() -> None:
    out = update_pile_state_matrix(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        bridge_name="YK0+500-main",
        pile_id="P3",
        updates={"total_qc_tables": 4, "generated": 2, "signed": 1},
        commit=False,
    )
    assert out["ok"] is True
    matrix = out["pile_entity"]["state_matrix"]
    assert matrix["total_qc_tables"] == 4
    assert matrix["generated"] == 2
    assert matrix["pending"] == 2


@dataclass
class _ExecResult:
    data: list[dict[str, Any]]


class _FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def select(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def eq(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def execute(self) -> _ExecResult:
        return _ExecResult(data=self.rows)


class _FakeSupabase:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self.rows)


def test_full_line_and_bridge_views_from_latest_bridge_nodes() -> None:
    rows = [
        {
            "state_data": {
                "entity_type": "bridge_entity",
                "bridge_slug": "yk0-500-main",
                "bridge_name": "YK0+500 main",
                "bridge_uri": "v://cn.zhongbei/YADGS/bridge/yk0-500-main",
                "parent_section": "K0~K20",
                "total_piles": 3,
                "sub_items": [
                    {"component_uri": "v://.../pile/1", "component_type": "pile"},
                    {"component_uri": "v://.../pile/2", "component_type": "pile"},
                    {"component_uri": "v://.../pile/3", "component_type": "pile"},
                ],
                "version": 2,
            }
        },
        {
            "state_data": {
                "entity_type": "bridge_entity",
                "bridge_slug": "yk1-200-side",
                "bridge_name": "YK1+200 side",
                "bridge_uri": "v://cn.zhongbei/YADGS/bridge/yk1-200-side",
                "parent_section": "K0~K20",
                "total_piles": 1,
                "sub_items": [
                    {"component_uri": "v://.../pile/9", "component_type": "pile"},
                    {"component_uri": "v://.../cap/1", "component_type": "cap"},
                ],
                "version": 1,
            }
        },
    ]
    sb = _FakeSupabase(rows)
    full = get_full_line_pile_summary(sb=sb, project_uri="v://cn.zhongbei/YADGS")
    assert full["ok"] is True
    assert full["pile_total"] == 4
    assert full["bridge_count"] == 2

    single = get_bridge_pile_detail(sb=sb, project_uri="v://cn.zhongbei/YADGS", bridge_name="YK0+500 main")
    assert single["ok"] is True
    assert single["total_piles"] == 3
    assert len(single["pile_items"]) == 3


def test_bridge_detail_not_found() -> None:
    sb = _FakeSupabase([])
    with pytest.raises(HTTPException) as exc:
        get_bridge_pile_detail(sb=sb, project_uri="v://cn.zhongbei/YADGS", bridge_name="missing-bridge")
    assert exc.value.status_code == 404


def test_get_pile_entity_detail_found_from_latest_rows() -> None:
    sb = _FakeSupabase(
        [
            {
                "state_data": {
                    "entity_type": "pile_entity",
                    "pile_uri": "v://cn.zhongbei/YADGS/bridge/yk0-500-main/pile/P3",
                    "pile_id": "P3",
                    "bridge_uri": "v://cn.zhongbei/YADGS/bridge/yk0-500-main",
                    "bridge_name": "YK0+500-main",
                    "state_matrix": {"total_qc_tables": 2, "generated": 1, "signed": 0, "pending": 1},
                    "lifecycle_stage": "in_progress",
                    "version": 1,
                }
            }
        ]
    )
    out = get_pile_entity_detail(
        sb=sb,
        project_uri="v://cn.zhongbei/YADGS",
        bridge_name="YK0+500-main",
        pile_id="P3",
    )
    assert out["ok"] is True
    assert out["pile_entity"]["pile_id"] == "P3"
