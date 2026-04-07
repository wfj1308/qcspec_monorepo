from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.api.domain.boqpeg.runtime.productization import (
    boqpeg_phase1_bridge_pile_report,
    boqpeg_product_manifest,
)


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


def test_boqpeg_product_manifest_contains_three_phase_mvp() -> None:
    out = boqpeg_product_manifest()
    assert out["ok"] is True
    assert out["product"]["name"] == "BOQPeg"
    assert out["foundation"]["normref_logic_scaffold"]["l0"] == "v://normref.com/core@v1"
    assert out["foundation"]["normref_logic_scaffold"]["l2"] == "v://normref.com/qc/raft-foundation@v1"
    assert out["foundation"]["normref_logic_scaffold"]["first_case_spu"] == "v://normref.com/spu/raft-foundation@v1"
    assert out["foundation"]["normref_logic_scaffold"]["schema"] == "v://normref.com/schema/qc-v1"
    assert out["mvp"]["phase1"]["done"] is True
    assert out["mvp"]["phase2"]["done"] is True
    assert out["mvp"]["phase3"]["done"] is True


def test_boqpeg_phase1_bridge_report_preview_contains_proof_hash() -> None:
    sb = _FakeSupabase(
        [
            {
                "state_data": {
                    "entity_type": "bridge_entity",
                    "bridge_slug": "yk0-500-main",
                    "bridge_name": "YK0+500-main",
                    "bridge_uri": "v://project/demo/bridge/yk0-500-main",
                    "parent_section": "K0~K20",
                    "total_piles": 2,
                    "sub_items": [
                        {"component_uri": "v://project/demo/bridge/yk0-500-main/pile/1", "component_type": "pile"},
                        {"component_uri": "v://project/demo/bridge/yk0-500-main/pile/2", "component_type": "pile"},
                    ],
                    "version": 1,
                }
            },
        ]
    )
    out = boqpeg_phase1_bridge_pile_report(
        sb=sb,
        body={
            "project_uri": "v://project/demo",
            "bridge_name": "YK0+500-main",
        },
        commit=False,
    )
    assert out["ok"] is True
    assert out["summary"]["full_line_piles"] == 2
    assert out["summary"]["bridge_piles"] == 2
    assert out["proof"]["proof_hash"]
    assert out["proof"]["committed"] is False
