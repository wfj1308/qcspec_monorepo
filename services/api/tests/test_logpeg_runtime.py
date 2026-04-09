from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from services.api.domain.logpeg.runtime.logpeg import LogPegEngine


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

    def update(self, payload: Any):
        self._op = _Op(kind="update", payload=payload)
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
        if self._op.kind == "update":
            patch = dict(self._op.payload or {})
            matched = self._apply_filters(rows)
            out: list[dict[str, Any]] = []
            for row in matched:
                row.update(patch)
                out.append(deepcopy(row))
            return SimpleNamespace(data=out)

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
                    "v_uri": "v://cn.大锦/DJGS",
                    "name": "大锦高速",
                    "contract_no": "DJ-DA-01",
                    "status": "active",
                    "created_at": "2026-04-01T00:00:00+00:00",
                }
            ],
            "gate_trips": [
                {
                    "trip_uri": "v://cn.大锦/DJGS/trip/2026/0406/TRIP-001",
                    "doc_id": "NINST-1",
                    "trip_role": "inspector.submit",
                    "action": "submit",
                    "executor_name": "张三",
                    "verified": True,
                    "signed_at": "2026-04-06T01:30:00+00:00",
                    "metadata": {
                        "project_uri": "v://cn.大锦/DJGS",
                        "component_uri": "v://cn.大锦/DJGS/pile/K12-340-4B",
                        "form_code": "桥施2表",
                        "process_step": "护筒埋设",
                        "proof_id": "NINST-1",
                        "equipment_used": ["旋挖钻XRS365-01"],
                    },
                },
                {
                    "trip_uri": "v://cn.大锦/DJGS/trip/2026/0406/TRIP-002",
                    "doc_id": "NINST-2",
                    "trip_role": "supervisor.approve",
                    "action": "approve",
                    "executor_name": "李工",
                    "verified": True,
                    "signed_at": "2026-04-06T03:00:00+00:00",
                    "metadata": {
                        "project_uri": "v://cn.大锦/DJGS",
                        "component_uri": "v://cn.大锦/DJGS/pile/K12-340-4B",
                        "form_code": "桥施7表",
                        "process_step": "成孔检查",
                        "proof_id": "NINST-2",
                        "equipment_used": ["全站仪TS06"],
                    },
                },
            ],
            "proof_utxo": [
                {
                    "proof_id": "GP-M-1",
                    "proof_hash": "hash-m1",
                    "project_uri": "v://cn.大锦/DJGS",
                    "proof_type": "inspection",
                    "created_at": "2026-04-06T03:30:00+00:00",
                    "state_data": {
                        "proof_kind": "material_inspection_batch",
                        "material_name": "C50混凝土",
                        "material_code": "concrete-c50",
                        "quantity": 28,
                        "unit": "m3",
                        "unit_price": 580,
                        "component_uri": "v://cn.大锦/DJGS/pile/K12-340-4B",
                        "batch_no": "B001",
                    },
                },
                {
                    "proof_id": "GP-PC-1",
                    "proof_hash": "hash-pc1",
                    "project_uri": "v://cn.大锦/DJGS",
                    "proof_type": "node",
                    "created_at": "2026-04-06T10:00:00+00:00",
                    "state_data": {
                        "entity_type": "process_chain",
                        "component_uri": "v://cn.大锦/DJGS/pile/K12-340-4B",
                        "current_step": "pile-rebar-03",
                        "state_matrix": {"total_steps": 6, "completed_steps": 2},
                    },
                },
            ],
            "railpact_settlements": [
                {
                    "trip_uri": "v://cn.大锦/DJGS/trip/2026/0406/TRIP-001",
                    "amount": 120.0,
                    "smu_type": "labor",
                    "settled_at": "2026-04-06T06:00:00+00:00",
                },
                {
                    "trip_uri": "v://cn.大锦/DJGS/trip/2026/0406/TRIP-002",
                    "amount": 350.0,
                    "smu_type": "equipment",
                    "settled_at": "2026-04-06T07:00:00+00:00",
                },
            ],
            "san_executors": [
                {
                    "executor_uri": "v://cn.中北/executor/li-gong",
                    "holder_name": "李工",
                    "name": "李工",
                    "certificates": [{"cert_type": "监理证", "valid_until": "2026-04-20"}],
                }
            ],
            "enterprise_configs": [],
        }

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


class _FakeProofEngine:
    def __init__(self, sb: _FakeSupabase) -> None:
        self.sb = sb

    def create(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "proof_id": kwargs.get("proof_id"),
            "proof_hash": kwargs.get("state_data", {}).get("data_hash") or "hash-log",
            "project_uri": kwargs.get("project_uri"),
            "proof_type": kwargs.get("proof_type", "document"),
            "result": kwargs.get("result", "PASS"),
            "state_data": kwargs.get("state_data") or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.sb._data.setdefault("proof_utxo", []).append(row)
        return row


def test_logpeg_daily_generation_and_sign_lock(monkeypatch) -> None:
    sb = _FakeSupabase()
    monkeypatch.setattr("services.api.domain.logpeg.runtime.logpeg.ProofUTXOEngine", _FakeProofEngine)

    engine = LogPegEngine(sb=sb)
    daily = __import__("asyncio").run(engine.generate_daily_log(project_uri="v://cn.大锦/DJGS", log_date="2026-04-06"))

    assert daily.project_name == "大锦高速"
    assert daily.log_date == "2026-04-06"
    assert daily.progress_summary.completed_steps >= 2
    assert daily.cost_summary.daily_total > 0
    assert daily.v_uri == "v://cn.大锦/DJGS/log/2026-04-06"

    signed = __import__("asyncio").run(
        engine.sign_daily_log(
            project_uri="v://cn.大锦/DJGS",
            log_date="2026-04-06",
            executor_uri="v://cn.中北/executor/li-gong",
            weather="晴",
            temperature_range="12-24℃",
            wind_level="3级",
        )
    )
    assert signed.locked is True
    assert signed.signed_by == "李工"
    assert str(signed.sign_proof).startswith("GP-LOGPEG-")

    reloaded = __import__("asyncio").run(
        engine.generate_daily_log(project_uri="v://cn.大锦/DJGS", log_date="2026-04-06", weather="雨")
    )
    assert reloaded.locked is True
    assert reloaded.weather == "晴"


def test_logpeg_weekly_monthly_and_exports(monkeypatch) -> None:
    sb = _FakeSupabase()
    monkeypatch.setattr("services.api.domain.logpeg.runtime.logpeg.ProofUTXOEngine", _FakeProofEngine)
    engine = LogPegEngine(sb=sb)

    weekly = __import__("asyncio").run(
        engine.generate_weekly_log(project_uri="v://cn.大锦/DJGS", week_start="2026-04-06", language="en")
    )
    assert weekly.language == "en"
    assert len(weekly.daily_logs) == 7

    monthly = __import__("asyncio").run(
        engine.generate_monthly_log(project_uri="v://cn.大锦/DJGS", year_month="2026-04", language="zh")
    )
    assert monthly.month == "2026-04"
    assert len(monthly.daily_logs) == 30

    pdf_bytes, pdf_name, pdf_type = __import__("asyncio").run(
        engine.export_daily_log(project_uri="v://cn.大锦/DJGS", log_date="2026-04-06", format="pdf", language="zh")
    )
    assert pdf_name.endswith(".pdf")
    assert pdf_type == "application/pdf"
    assert pdf_bytes[:4] == b"%PDF"

    json_bytes, json_name, json_type = __import__("asyncio").run(
        engine.export_daily_log(project_uri="v://cn.大锦/DJGS", log_date="2026-04-06", format="json", language="zh")
    )
    assert json_name.endswith(".json")
    assert json_type == "application/json"
    assert b"log_date" in json_bytes
