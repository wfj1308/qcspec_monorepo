from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

from services.api.domain.boqpeg.models import EquipmentTripRequest, ToolAssetRegisterRequest
from services.api.domain.boqpeg.runtime.cost_engine import calculate_component_cost
from services.api.domain.boqpeg.runtime.equipment import (
    get_equipment_status,
    register_tool_asset,
    submit_equipment_trip,
)


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
                    "enterprise_id": "11111111-1111-4111-8111-111111111111",
                    "v_uri": "v://cn.大锦/DJGS",
                    "name": "大锦高速",
                    "status": "active",
                }
            ],
            "enterprise_configs": [
                {
                    "enterprise_id": "11111111-1111-4111-8111-111111111111",
                    "custom_fields": {},
                }
            ],
            "san_executors": [
                {
                    "executor_uri": "v://cn.中北/executor/zhang-san",
                    "skills": [
                        {
                            "skill_uri": "v://normref.com/skill/drill-operator@v1",
                            "scope": ["drill", "pile"],
                            "level": "senior",
                        }
                    ],
                }
            ],
            "proof_utxo": [],
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


async def _fake_send_equipment_alert(**kwargs: Any) -> dict[str, Any]:
    _ = kwargs
    return {"attempted": True, "success": True, "status_code": 200}


def test_equipment_runtime_gate_and_cost(monkeypatch) -> None:
    fixed_now = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    sb = _FakeSupabase()
    monkeypatch.setattr("services.api.domain.boqpeg.runtime.equipment.ProofUTXOEngine", _FakeProofEngine)
    monkeypatch.setattr("services.api.domain.boqpeg.runtime.equipment._send_equipment_alert", _fake_send_equipment_alert)
    monkeypatch.setattr("services.api.domain.boqpeg.runtime.equipment._utc_now", lambda: fixed_now)

    register_req = ToolAssetRegisterRequest(
        project_uri="v://cn.大锦/DJGS",
        v_uri="v://cn.大锦/DJGS/equipment/XRS365-01",
        name="旋挖钻机XRS365-01",
        asset_mode="rental",
        calibration_cert_no="CAL-2026-XRS365",
        calibration_valid_until=date(2026, 6, 30),
        annual_inspection_status="valid",
        annual_inspection_valid_until=date(2026, 12, 31),
        operator_skill_required=["drill"],
        maintenance_status="normal",
        rental_shift_rate=1200.0,
        executor_uri="v://cn.中北/executor/admin",
    )
    asset = register_tool_asset(sb=sb, body=register_req, commit=True)
    assert asset.v_uri == "v://cn.大锦/DJGS/equipment/XRS365-01"

    status = __import__("asyncio").run(
        get_equipment_status(
            sb=sb,
            equipment_uri=asset.v_uri,
            operator_executor_uri="v://cn.中北/executor/zhang-san",
        )
    )
    assert status.ready is True
    assert status.gate_reasons == []

    trip_req = EquipmentTripRequest(
        project_uri="v://cn.大锦/DJGS",
        component_uri="v://cn.大锦/DJGS/pile/K12-340-1#",
        equipment_uri=asset.v_uri,
        operator_executor_uri="v://cn.中北/executor/zhang-san",
        shift_count=1.0,
    )
    trip = __import__("asyncio").run(submit_equipment_trip(sb=sb, body=trip_req, commit=True))
    assert trip.ok is True
    assert trip.gate_passed is True
    assert trip.trip.machine_cost == 1200.0

    breakdown = calculate_component_cost(
        sb=sb,
        component_uri="v://cn.大锦/DJGS/pile/K12-340-1#",
        overhead_ratio=0.0,
    )
    assert breakdown.equipment_cost == 1200.0
    assert breakdown.labor == 0.0
    assert breakdown.total == 1200.0


def test_equipment_warning_thresholds(monkeypatch) -> None:
    fixed_now = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    sb = _FakeSupabase()
    alerts: list[dict[str, Any]] = []

    async def _capture_alert(**kwargs: Any) -> dict[str, Any]:
        alerts.append(dict(kwargs))
        return {"attempted": True, "success": True, "status_code": 200}

    monkeypatch.setattr("services.api.domain.boqpeg.runtime.equipment.ProofUTXOEngine", _FakeProofEngine)
    monkeypatch.setattr("services.api.domain.boqpeg.runtime.equipment._send_equipment_alert", _capture_alert)
    monkeypatch.setattr("services.api.domain.boqpeg.runtime.equipment._utc_now", lambda: fixed_now)

    register_req = ToolAssetRegisterRequest(
        project_uri="v://cn.大锦/DJGS",
        v_uri="v://cn.大锦/DJGS/equipment/XRS365-02",
        name="旋挖钻机XRS365-02",
        asset_mode="owned",
        calibration_valid_until=date(2026, 5, 1),  # 30天内
        annual_inspection_status="valid",
        annual_inspection_valid_until=date(2026, 12, 31),
        maintenance_status="normal",
        maintenance_due_at=datetime(2026, 4, 14, 9, 0, tzinfo=UTC),  # 7天内
    )
    register_tool_asset(sb=sb, body=register_req, commit=True)
    status = __import__("asyncio").run(
        get_equipment_status(sb=sb, equipment_uri=register_req.v_uri, operator_executor_uri="")
    )

    assert any(item.startswith("calibration_expiring_in_") for item in status.warnings)
    assert any(item.startswith("maintenance_due_in_") for item in status.warnings)
    assert len(alerts) == 1
