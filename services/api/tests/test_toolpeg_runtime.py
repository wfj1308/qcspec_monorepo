from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

from services.api.domain.signpeg.flows import (
    check_tool_status_flow,
    get_tool_status_flow,
    register_tool_flow,
    use_tool_flow,
)
from services.api.domain.signpeg.models import (
    ToolCertificate,
    ToolRegisterRequest,
    ToolUseRequest,
)
from services.api.domain.signpeg.runtime.toolpeg import validate_tool


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
        self._op = _Op(kind="upsert", payload={"row": payload, "on_conflict": on_conflict})
        return self

    def _apply_filters(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = rows
        for field, value in self._filters:
            out = [row for row in out if row.get(field) == value]
        return out

    def execute(self):
        table_rows = self._sb._data.setdefault(self._name, [])
        if self._op.kind == "insert":
            payload = self._op.payload
            rows = payload if isinstance(payload, list) else [payload]
            inserted = [deepcopy(dict(row)) for row in rows]
            table_rows.extend(inserted)
            return SimpleNamespace(data=inserted)

        if self._op.kind == "upsert":
            op = dict(self._op.payload or {})
            row = deepcopy(dict(op.get("row") or {}))
            on_conflict = str(op.get("on_conflict") or "").strip()
            keys = [k.strip() for k in on_conflict.split(",") if k.strip()]
            if not keys:
                table_rows.append(row)
                return SimpleNamespace(data=[row])
            hit = -1
            for idx, item in enumerate(table_rows):
                if all(item.get(key) == row.get(key) for key in keys):
                    hit = idx
                    break
            if hit >= 0:
                merged = {**table_rows[hit], **row}
                table_rows[hit] = merged
                return SimpleNamespace(data=[merged])
            table_rows.append(row)
            return SimpleNamespace(data=[row])

        rows = self._apply_filters([deepcopy(row) for row in table_rows])
        if self._order_field:
            rows = sorted(rows, key=lambda row: row.get(self._order_field), reverse=self._order_desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self) -> None:
        self._data: dict[str, list[dict[str, Any]]] = {
            "san_tools": [],
            "san_tool_alerts": [],
            "railpact_settlements": [],
        }

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


def _tool_cert(days: int = 365) -> ToolCertificate:
    return ToolCertificate(
        cert_type="检定证书",
        cert_no="JD-2026-001",
        valid_until=date.today() + timedelta(days=days),
        issued_by="v://cn.计量院/",
        status="active",
        scan_hash="sha256:jd-2026-001",
    )


def test_toolpeg_register_use_and_status() -> None:
    sb = _FakeSupabase()
    out = register_tool_flow(
        sb=sb,
        body=ToolRegisterRequest(
            tool_name="电焊机Miller-03",
            tool_code="welder-miller-03",
            tool_type="reusable",
            owner_type="executor",
            owner_uri="v://cn.中北/executor/zhang-san",
            project_uri="v://cn.大锦/DJGS",
            certificates=[_tool_cert(300)],
            reusable_spec={
                "purchase_price": 450000,
                "expected_life": 200,
                "current_uses": 89,
                "maintenance_cycle": 50,
                "next_maintenance_at": 150,
                "depreciation_per_use": 2250,
            },
            tool_energy={"energy_type": "electric", "unit": "台班", "rate": 1, "cost_per_unit": 12, "smu_type": "equipment"},
        ),
    )
    assert out["ok"] is True
    tool_id = str(out["tool_id"])
    status = get_tool_status_flow(sb=sb, tool_id=tool_id)
    assert status["ok"] is True
    assert status["certificates_valid"] is True

    used = use_tool_flow(
        sb=sb,
        tool_id=tool_id,
        body=ToolUseRequest(
            trip_id="NINST-90219204",
            trip_uri="v://cn.大锦/DJGS/trip/2026/0408/TRIP-TOOL-001",
            trip_role="construction.welding",
            shifts=1,
            duration_hours=8,
        ),
    )
    assert used["ok"] is True
    assert used["tool"]["reusable_spec"]["current_uses"] == 90
    assert len(sb._data["railpact_settlements"]) >= 1


def test_toolpeg_gate_and_expiry_checker() -> None:
    sb = _FakeSupabase()
    out = register_tool_flow(
        sb=sb,
        body=ToolRegisterRequest(
            tool_name="钻头φ1500",
            tool_code="drill-bit-1500",
            tool_type="consumable",
            owner_type="pool",
            owner_uri="v://cn.中北/tool-pool/main",
            project_uri="v://cn.大锦/DJGS",
            certificates=[_tool_cert(100)],
            consumable_spec={
                "sku_uri": "v://cn.中北/sku/DRILL-BIT-1500",
                "initial_qty": 2,
                "remaining_qty": 2,
                "unit": "个",
                "replenish_threshold": 1,
                "unit_price": 45,
            },
        ),
    )
    tool_uri = str(out["tool_uri"])
    tool_id = str(out["tool_id"])

    gate_ok = validate_tool(sb, tool_uri=tool_uri, trip_role="construction.drilling", consumed_qty=1)
    assert gate_ok["passed"] is True

    use_tool_flow(
        sb=sb,
        tool_id=tool_id,
        body=ToolUseRequest(
            trip_id="NINST-90219205",
            trip_role="construction.drilling",
            consumed_qty=2,
        ),
    )
    gate_fail = validate_tool(sb, tool_uri=tool_uri, trip_role="construction.drilling", consumed_qty=1)
    assert gate_fail["passed"] is False

    sb._data["san_tools"][0]["certificates"][0]["valid_until"] = (date.today() - timedelta(days=1)).isoformat()
    checked = check_tool_status_flow(sb=sb)
    assert checked["ok"] is True
    assert len(checked["suspended"]) >= 1
