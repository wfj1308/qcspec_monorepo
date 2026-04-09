from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi.testclient import TestClient

from services.api.dependencies import (
    get_boqpeg_service,
    get_docpeg_execution_gate_service,
    require_auth_identity,
)
from services.api.infrastructure.http.app_factory import create_app


class _FakeGate:
    def enforce_execution(self, **kwargs: Any) -> None:
        _ = kwargs


class _FakeBOQPegService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def submit_welding_trip(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("welding", kwargs))
        return {"ok": True, "trip": {"trip_role": "construction.welding"}, "gate_passed": True}

    async def submit_formwork_use_trip(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("formwork", kwargs))
        return {"ok": True, "trip": {"trip_role": "construction.formwork"}, "gate_passed": True}

    async def submit_prestressing_trip(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("prestressing", kwargs))
        return {"ok": True, "trip": {"trip_role": "construction.prestressing"}, "gate_passed": False}

    async def calculate_component_cost(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("cost", kwargs))
        return {"ok": True, "component_uri": kwargs.get("component_uri"), "total": 123.45}

    async def register_tool_asset(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("equipment-register", kwargs))
        body = kwargs.get("body") or {}
        return {
            "ok": True,
            "asset": {
                "v_uri": body.get("v_uri"),
                "project_uri": body.get("project_uri"),
                "name": body.get("name"),
                "asset_mode": body.get("asset_mode", "owned"),
            },
        }

    async def submit_equipment_trip(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("equipment-trip", kwargs))
        body = kwargs.get("body") or {}
        return {
            "ok": True,
            "trip": {
                "equipment_uri": body.get("equipment_uri"),
                "component_uri": body.get("component_uri"),
                "machine_cost": 1200.0,
            },
            "gate_passed": True,
            "warnings": [],
        }

    async def get_equipment_status(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("equipment-status", kwargs))
        return {
            "ok": True,
            "equipment_uri": kwargs.get("equipment_uri"),
            "ready": True,
            "status": "in_service",
            "warnings": [],
            "gate_reasons": [],
        }

    async def get_equipment_history(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("equipment-history", kwargs))
        return {
            "ok": True,
            "equipment_uri": kwargs.get("equipment_uri"),
            "trips": [],
            "asset_snapshots": [],
            "warnings": [],
        }


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://cn.demo/executor/test-user"}


def _build_client(fake_service: _FakeBOQPegService) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_docpeg_execution_gate_service] = lambda: _FakeGate()
    app.dependency_overrides[get_boqpeg_service] = lambda: fake_service
    return TestClient(app)


def test_trip_routes() -> None:
    fake = _FakeBOQPegService()
    component_uri = "v://cn.大锦/DJGS/pile/K12-340-1#"
    encoded_component = quote(component_uri, safe="")
    with _build_client(fake) as client:
        welding_res = client.post(
            "/api/v1/trip/welding?commit=true",
            json={
                "project_uri": "v://cn.大锦/DJGS",
                "component_uri": component_uri,
                "executor_uri": "v://cn.中北/executor/zhang-san",
                "equipment_uri": "v://cn.大锦/DJGS/equipment/welding-001",
                "consumables": [
                    {
                        "name": "焊条E5015",
                        "batch_ref": "v://cost/iqc/electrode-e5015-b456",
                        "quantity_used": 3.2,
                        "quantity_unit": "kg",
                        "standard_qty": 2.8,
                        "over_reason": "补焊",
                    }
                ],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        formwork_res = client.post(
            "/api/v1/trip/formwork-use?commit=true",
            json={
                "project_uri": "v://cn.大锦/DJGS",
                "component_uri": component_uri,
                "executor_uri": "v://cn.中北/executor/li-si",
                "equipment_uri": "v://cn.大锦/DJGS/equipment/formwork-a",
                "formwork_asset_uri": "v://cn.大锦/DJGS/formwork/set-a",
                "expected_uses": 50,
                "purchase_price": 5000,
                "consumables": [],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        prestress_res = client.post(
            "/api/v1/trip/prestressing?commit=true",
            json={
                "project_uri": "v://cn.大锦/DJGS",
                "component_uri": component_uri,
                "executor_uri": "v://cn.中北/executor/wang-wu",
                "equipment_uri": "v://cn.大锦/DJGS/equipment/prestress-001",
                "theoretical_elongation": 100,
                "actual_elongation": 110,
                "consumables": [],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        equipment_uri = "v://cn.澶ч敠/DJGS/equipment/XRS365-01"
        encoded_equipment = quote(equipment_uri, safe="")
        equipment_register_res = client.post(
            "/api/v1/equipment/register?commit=true",
            json={
                "project_uri": "v://cn.澶ч敠/DJGS",
                "v_uri": equipment_uri,
                "name": "鏃嬫尓閽绘満XRS365-01",
                "asset_mode": "rental",
                "executor_uri": "v://cn.涓寳/executor/admin",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        equipment_trip_res = client.post(
            "/api/v1/equipment/trip?commit=true",
            json={
                "project_uri": "v://cn.澶ч敠/DJGS",
                "component_uri": component_uri,
                "equipment_uri": equipment_uri,
                "operator_executor_uri": "v://cn.涓寳/executor/zhang-san",
                "shift_count": 1.5,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        equipment_status_res = client.get(
            f"/api/v1/equipment/{encoded_equipment}/status?operator_executor_uri=v://cn.%E4%B8%AD%E5%8C%97/executor/zhang-san",
            headers={"Authorization": "Bearer test-token"},
        )
        equipment_history_res = client.get(
            f"/api/v1/equipment/{encoded_equipment}/history",
            headers={"Authorization": "Bearer test-token"},
        )
        cost_res = client.get(
            f"/api/v1/cost/component/{encoded_component}?overhead_ratio=0.12",
            headers={"Authorization": "Bearer test-token"},
        )

    assert welding_res.status_code == 200
    assert formwork_res.status_code == 200
    assert prestress_res.status_code == 200
    assert equipment_register_res.status_code == 200
    assert equipment_trip_res.status_code == 200
    assert equipment_status_res.status_code == 200
    assert equipment_history_res.status_code == 200
    assert cost_res.status_code == 200

    call_names = [item[0] for item in fake.calls]
    assert "welding" in call_names
    assert "formwork" in call_names
    assert "prestressing" in call_names
    assert "equipment-register" in call_names
    assert "equipment-trip" in call_names
    assert "equipment-status" in call_names
    assert "equipment-history" in call_names
    assert "cost" in call_names
