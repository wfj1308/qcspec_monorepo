from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from services.api.domain.boqpeg.models import (
    ConsumableItem,
    FormworkUseTripRequest,
    PrestressingTripRequest,
    WeldingTripRequest,
)
from services.api.domain.boqpeg.runtime.consumption_trip import (
    submit_formwork_use_trip,
    submit_prestressing_trip,
    submit_welding_trip,
)
from services.api.domain.boqpeg.runtime.cost_engine import calculate_component_cost

TEST_ENTERPRISE_ID = "11111111-1111-4111-8111-111111111111"


@dataclass
class _Op:
    kind: str
    payload: Any = None


class _FakeTable:
    def __init__(self, sb: "_FakeSupabase", name: str) -> None:
        self._sb = sb
        self._name = name
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None
        self._order_field: str | None = None
        self._order_desc: bool = False
        self._op = _Op(kind="select")

    def select(self, _cols: str = "*"):
        self._op = _Op(kind="select")
        return self

    def eq(self, field: str, value: Any):
        self._filters.append((field, value))
        return self

    def limit(self, value: int):
        self._limit = int(value)
        return self

    def order(self, field: str, desc: bool = False):
        self._order_field = field
        self._order_desc = bool(desc)
        return self

    def insert(self, payload: Any):
        self._op = _Op(kind="insert", payload=payload)
        return self

    def upsert(self, payload: Any, on_conflict: str = ""):
        _ = on_conflict
        self._op = _Op(kind="insert", payload=payload)
        return self

    def _apply_filters(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = rows
        for field, value in self._filters:
            out = [row for row in out if row.get(field) == value]
        return out

    def execute(self):
        rows = self._sb._data.setdefault(self._name, [])
        if self._op.kind == "insert":
            payload = self._op.payload
            inserted = [deepcopy(dict(item)) for item in (payload if isinstance(payload, list) else [payload])]
            rows.extend(inserted)
            return SimpleNamespace(data=inserted)

        out = self._apply_filters([deepcopy(row) for row in rows])
        if self._order_field:
            out = sorted(out, key=lambda row: row.get(self._order_field), reverse=self._order_desc)
        if self._limit is not None:
            out = out[: self._limit]
        return SimpleNamespace(data=out)


class _FakeSupabase:
    def __init__(self) -> None:
        self._data: dict[str, list[dict[str, Any]]] = {
            "projects": [
                {
                    "id": "33333333-3333-4333-8333-333333333333",
                    "enterprise_id": TEST_ENTERPRISE_ID,
                    "v_uri": "v://cn.大锦/DJGS",
                    "name": "大锦高速",
                    "contract_no": "DJ-DA-01",
                    "status": "active",
                    "created_at": "2026-04-01T00:00:00+00:00",
                }
            ],
            "enterprise_configs": [
                {
                    "enterprise_id": TEST_ENTERPRISE_ID,
                    "custom_fields": {},
                }
            ],
            "proof_utxo": [
                {
                    "proof_id": "GP-IQC-ELE",
                    "proof_hash": "hash-iqc-ele",
                    "project_uri": "v://cn.大锦/DJGS",
                    "proof_type": "inspection",
                    "created_at": "2026-04-06T01:00:00+00:00",
                    "state_data": {
                        "proof_kind": "iqc_material_submit",
                        "iqc_uri": "v://cost/iqc/electrode-e5015-b456",
                        "material_code": "electrode-e5015",
                        "material_name": "焊条E5015",
                        "batch_no": "B456",
                        "total_qty": 10.0,
                        "unit": "kg",
                        "unit_price": 100.0,
                        "status": "approved",
                        "project_uri": "v://cn.大锦/DJGS",
                    },
                },
                {
                    "proof_id": "GP-M-UTXO-1",
                    "proof_hash": "hash-m-u1",
                    "project_uri": "v://cn.大锦/DJGS",
                    "proof_type": "inspection",
                    "created_at": "2026-04-06T01:20:00+00:00",
                    "state_data": {
                        "proof_kind": "material_inspection_batch",
                        "material_code": "concrete-c50",
                        "quantity": 28.0,
                        "unit_price": 580.0,
                        "iqc_uri": "v://cost/iqc/concrete-c50-001",
                        "inspection_uri": "v://cost/inspection-batch/jyp-001",
                        "utxo_id": "UTXO-001",
                        "component_uri": "v://cn.大锦/DJGS/pile/K12-340-1#",
                        "inspection_result": "approved",
                    },
                },
            ],
            "gate_trips": [],
            "railpact_settlements": [],
        }

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


class _FakeProofEngine:
    def __init__(self, sb: _FakeSupabase) -> None:
        self.sb = sb

    def create(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "proof_id": kwargs.get("proof_id"),
            "proof_hash": kwargs.get("state_data", {}).get("data_hash") or f"hash-{kwargs.get('proof_id')}",
            "project_uri": kwargs.get("project_uri"),
            "proof_type": kwargs.get("proof_type", "inspection"),
            "result": kwargs.get("result", "PASS"),
            "state_data": kwargs.get("state_data") or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.sb._data.setdefault("proof_utxo", []).append(row)
        return row


async def _fake_send_overuse_alert(**kwargs: Any) -> dict[str, Any]:
    _ = kwargs
    return {"attempted": True, "success": True, "status_code": 200}


def test_consumption_trip_runtime(monkeypatch) -> None:
    sb = _FakeSupabase()
    monkeypatch.setattr("services.api.domain.boqpeg.runtime.consumption_trip.ProofUTXOEngine", _FakeProofEngine)
    monkeypatch.setattr("services.api.domain.boqpeg.runtime.consumption_trip._send_overuse_alert", _fake_send_overuse_alert)

    welding_req = WeldingTripRequest(
        project_uri="v://cn.大锦/DJGS",
        component_uri="v://cn.大锦/DJGS/pile/K12-340-1#",
        location="K12+340",
        executor_uri="v://cn.中北/executor/zhang-san",
        equipment_uri="v://cn.大锦/DJGS/equipment/welding-001",
        consumables=[
            ConsumableItem(
                name="焊条E5015",
                batch_ref="v://cost/iqc/electrode-e5015-b456",
                quantity_used=3.2,
                quantity_unit="kg",
                standard_qty=2.8,
                over_reason="现场返工补焊",
            )
        ],
        process_params={"labor_hours": 2.0, "labor_rate": 50.0},
    )
    welding = __import__("asyncio").run(submit_welding_trip(sb=sb, body=welding_req, commit=True))
    assert welding.ok is True
    assert welding.batch_usage[0]["used_after"] == 3.2
    assert float(welding.trip.cost_aggregate) == 420.0
    assert any("overuse_alert" in item for item in welding.warnings)

    formwork_req = FormworkUseTripRequest(
        project_uri="v://cn.大锦/DJGS",
        component_uri="v://cn.大锦/DJGS/pile/K12-340-1#",
        location="K12+340",
        executor_uri="v://cn.中北/executor/li-si",
        equipment_uri="v://cn.大锦/DJGS/equipment/formwork-a",
        formwork_asset_uri="v://cn.大锦/DJGS/formwork/set-a",
        formwork_asset_name="主梁模板Set-A",
        purchase_price=5000.0,
        expected_uses=50,
        consumables=[],
        process_params={},
    )
    formwork = __import__("asyncio").run(submit_formwork_use_trip(sb=sb, body=formwork_req, commit=True))
    assert formwork.ok is True
    assert formwork.formwork_asset is not None
    assert formwork.formwork_asset.current_uses == 1
    assert formwork.formwork_asset.remaining_uses == 49
    assert float(formwork.trip.cost_aggregate) == 100.0

    prestress_req = PrestressingTripRequest(
        project_uri="v://cn.大锦/DJGS",
        component_uri="v://cn.大锦/DJGS/pile/K12-340-1#",
        location="K12+340",
        executor_uri="v://cn.中北/executor/wang-wu",
        equipment_uri="v://cn.大锦/DJGS/equipment/prestress-001",
        consumables=[],
        process_params={},
        theoretical_elongation=100.0,
        actual_elongation=110.0,
    )
    prestress = __import__("asyncio").run(submit_prestressing_trip(sb=sb, body=prestress_req, commit=True))
    assert prestress.ok is True
    assert prestress.gate_passed is False
    assert prestress.trip.result == "不合格"
    assert "deviation" in prestress.gate_reason

    breakdown = calculate_component_cost(
        sb=sb,
        component_uri="v://cn.大锦/DJGS/pile/K12-340-1#",
        overhead_ratio=0.0,
    )
    assert breakdown.direct_materials == 16240.0
    assert breakdown.consumables == 320.0
    assert breakdown.equipment_depreciation == 100.0
    assert breakdown.labor == 100.0
    assert breakdown.total == 16760.0
    assert len(breakdown.proof_refs) > 0

