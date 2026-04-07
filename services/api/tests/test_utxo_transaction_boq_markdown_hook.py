from __future__ import annotations

from typing import Any

from services.api.domain.utxo.runtime import transaction as tx_runtime


class _FakeQuery:
    def __init__(self, table_name: str, sink: dict[str, list[dict[str, Any]]]) -> None:
        self.table_name = table_name
        self.sink = sink
        self.payload: dict[str, Any] = {}

    def insert(self, payload: dict[str, Any]) -> "_FakeQuery":
        self.sink.setdefault(self.table_name, []).append(dict(payload))
        return self

    def update(self, payload: dict[str, Any]) -> "_FakeQuery":
        self.payload = dict(payload)
        return self

    def eq(self, key: str, value: Any) -> "_FakeQuery":
        row = dict(self.payload)
        row[f"eq_{key}"] = value
        self.sink.setdefault(f"{self.table_name}_updates", []).append(row)
        return self

    def execute(self) -> Any:
        class _Res:
            data: list[dict[str, Any]] = []

        return _Res()


class _FakeSB:
    def __init__(self) -> None:
        self.sink: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(name, self.sink)


def test_consume_proofs_triggers_boq_markdown_sync(monkeypatch) -> None:
    sb = _FakeSB()
    captured: list[dict[str, Any]] = []

    def _fake_sync(**kwargs: Any) -> None:
        captured.append(dict(kwargs))

    monkeypatch.setattr(tx_runtime, "_sync_boq_markdown_after_consume", _fake_sync)

    proof_map = {
        "P-IN-1": {
            "proof_id": "P-IN-1",
            "spent": False,
            "project_uri": "v://cn.zhongbei/YADGS",
            "segment_uri": "v://cn.zhongbei/YADGS/boq/403-1-2",
            "state_data": {"boq_item_canonical_uri": "v://cn.zhongbei/YADGS/boq/403-1-2"},
        }
    }

    def _load_inputs(_proof_ids: list[str]) -> dict[str, dict[str, Any]]:
        return proof_map

    def _check_conditions(_proof: dict[str, Any], _executor_uri: str, _executor_role: str) -> tuple[bool, str]:
        return True, ""

    def _create_callback(**kwargs: Any) -> dict[str, Any]:
        return {"proof_id": kwargs.get("proof_id", "P-OUT-1")}

    tx_runtime.consume_proofs(
        sb=sb,  # type: ignore[arg-type]
        input_proof_ids=["P-IN-1"],
        output_states=[
            {
                "proof_id": "P-OUT-1",
                "project_uri": "v://cn.zhongbei/YADGS",
                "segment_uri": "v://cn.zhongbei/YADGS/boq/403-1-2",
                "state_data": {"utxo_quantity": "142.8"},
            }
        ],
        executor_uri="v://cn.zhongbei/executor/person/renxiang",
        executor_role="SUPERVISOR",
        trigger_action="boq.consume",
        trigger_data={"source": "test"},
        tx_type="consume",
        anchor_config=None,
        load_inputs=_load_inputs,
        check_conditions=_check_conditions,
        create_callback=_create_callback,
        gen_tx_id=lambda: "TX-1",
        utc_now_iso=lambda: "2026-04-07T09:00:00Z",
        ordosign=lambda tx_id, executor_uri: f"sig:{tx_id}:{executor_uri}",
    )

    assert captured
    call = captured[0]
    assert call["project_uri"] == "v://cn.zhongbei/YADGS"
    assert "v://cn.zhongbei/YADGS/boq/403-1-2" in call["boq_v_uris"]

