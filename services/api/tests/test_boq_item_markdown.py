from __future__ import annotations

from pathlib import Path
from typing import Any

from services.api.domain.boq.runtime.boq_item_markdown import sync_boq_item_markdown


class _ExecResult:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._eq: list[tuple[str, Any]] = []
        self._like: list[tuple[str, str]] = []
        self._order_key: str = ""
        self._order_desc: bool = False

    def select(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def eq(self, key: str, value: Any) -> "_FakeQuery":
        self._eq.append((key, value))
        return self

    def like(self, key: str, pattern: str) -> "_FakeQuery":
        self._like.append((key, pattern))
        return self

    def order(self, key: str, **kwargs: Any) -> "_FakeQuery":
        self._order_key = key
        self._order_desc = bool(kwargs.get("desc"))
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def execute(self) -> _ExecResult:
        rows = [dict(r) for r in self._rows]
        for key, value in self._eq:
            rows = [r for r in rows if str(r.get(key) or "") == str(value)]
        for key, pattern in self._like:
            prefix = pattern[:-1] if pattern.endswith("%") else pattern
            rows = [r for r in rows if str(r.get(key) or "").startswith(prefix)]
        if self._order_key:
            rows.sort(key=lambda r: str(r.get(self._order_key) or ""), reverse=self._order_desc)
        return _ExecResult(rows)


class _FakeSB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self.rows)


def test_sync_boq_item_markdown_v2_sections_and_normref_mount(tmp_path: Path) -> None:
    boq_uri = "v://cn.zhongbei/YADGS/boq/403-1-2"
    out = sync_boq_item_markdown(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        boq_v_uri=boq_uri,
        state_data={
            "item_no": "403-1-2",
            "item_name": "钢筋加工及安装",
            "division": "400章 桥梁工程 - 钢筋工程",
            "unit": "t",
            "contract_quantity": "185.6",
            "contract_unit_price": "5800",
            "contract_total": "1076480",
            "bridge_uri": "v://cn.zhongbei/YADGS/bridge/YK0+500-main",
            "ref_spu_uri": "v://norm/spu/rebar-processing@v1",
            "ref_qc_protocol_uri": "v://normref.com/qc/rebar-processing@v1",
            "ref_meter_rule_uri": "v://norm/meter-rule/by-weight@v1",
            "linked_gate_ids": ["diameter<=2%", "spacing<=10mm"],
            "norm_refs": ["GB50204-2015", "JTG F80/1-2017"],
            "topology_component_count": 52,
            "forms_per_component": 2,
            "generated_qc_table_count": 3,
            "signed_pass_table_count": 0,
            "genesis_proof": {"proof_id": "PF-BOQ-SCAN-20260403-XXXX"},
        },
        actor_uri="v://cn.zhongbei/executor/person/renxiang",
        reason="boq.scan_complete",
        write_file=True,
        output_root=tmp_path,
    )
    assert out["ok"] is True
    content = Path(out["path"]).read_text(encoding="utf-8")

    assert "**Layer 1: Header（身份层）**" in content
    assert "doc_type: v://normref.com/doc-type/boq-item@v1" in content
    assert "doc_id: BOQ-403-1-2-001" in content
    assert "version: v2.1" in content
    assert "v://cn.zhongbei/YADGS/bridge/YK0+500-main/boq/403-1-2" in content
    assert "**Layer 2: Gate（门槛层）**" in content
    assert "v://normref.com/qc/rebar-processing@v1" in content
    assert "required_trip_roles: [\"inspector.quality.check\", \"supervisor.approve\"]" in content
    assert "design_diameter" in content
    assert "measured_spacing" in content
    assert "**Layer 5: State（状态层）**" in content
    assert "total_qc_tables: 104" in content
    assert "generated: 3" in content
    assert "pending: 101" in content


def test_sync_boq_item_markdown_auto_refresh_after_consumption(tmp_path: Path) -> None:
    boq_uri = "v://cn.zhongbei/YADGS/boq/403-1-2"
    rows = [
        {
            "proof_id": "UTXO-BOQ-403-1-2-001",
            "project_uri": "v://cn.zhongbei/YADGS",
            "proof_type": "zero_ledger",
            "result": "PENDING",
            "spent": False,
            "spend_tx_id": None,
            "segment_uri": boq_uri,
            "created_at": "2026-04-03T11:45:22Z",
            "state_data": {
                "item_no": "403-1-2",
                "item_name": "钢筋加工及安装",
                "unit": "t",
                "contract_quantity": "185.6",
                "utxo_kind": "BOQ_INITIAL",
                "utxo_quantity": "185.6",
                "ref_spu_uri": "v://norm/spu/rebar-processing@v1",
            },
        }
    ]
    sb = _FakeSB(rows)
    first = sync_boq_item_markdown(
        sb=sb,
        project_uri="v://cn.zhongbei/YADGS",
        boq_v_uri=boq_uri,
        write_file=True,
        output_root=tmp_path,
    )
    assert first["ok"] is True

    rows[0]["spent"] = True
    rows.append(
        {
            "proof_id": "UTXO-BOQ-403-1-2-OUT-1",
            "project_uri": "v://cn.zhongbei/YADGS",
            "proof_type": "inspection",
            "result": "PASS",
            "spent": False,
            "spend_tx_id": None,
            "segment_uri": boq_uri,
            "created_at": "2026-04-10T14:32:18Z",
            "state_data": {
                "item_no": "403-1-2",
                "item_name": "钢筋加工及安装",
                "unit": "t",
                "utxo_quantity": "142.8",
                "ref_spu_uri": "v://norm/spu/rebar-processing@v1",
            },
        }
    )

    second = sync_boq_item_markdown(
        sb=sb,
        project_uri="v://cn.zhongbei/YADGS",
        boq_v_uri=boq_uri,
        write_file=True,
        output_root=tmp_path,
    )
    assert second["ok"] is True
    content = Path(second["path"]).read_text(encoding="utf-8")
    assert "已消耗数量：42.8 t" in content
    assert "剩余数量：142.8 t" in content
    assert "当前状态：`PARTIALLY_CONSUMED`" in content
