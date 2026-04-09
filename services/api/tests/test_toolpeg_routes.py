from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services.api.dependencies import get_signpeg_service, require_auth_identity
from services.api.infrastructure.http.app_factory import create_app


class _FakeSignPegService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    @staticmethod
    def _payload(body: Any) -> dict[str, Any]:
        if hasattr(body, "model_dump"):
            return body.model_dump(mode="json")
        return body if isinstance(body, dict) else {}

    async def register_tool(self, *, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("register_tool", {"body": payload}))
        return {
            "ok": True,
            "tool_id": "TOOL-001",
            "tool_uri": "v://cn.中北/executor/zhang-san/tool/welder-miller-03",
            "registration_proof": "PROOF-TOOL-A1B2C3D4",
            "status": "available",
        }

    async def get_tool(self, *, tool_id: str) -> dict[str, Any]:
        self.calls.append(("get_tool", {"tool_id": tool_id}))
        return {"ok": True, "tool": {"tool_id": tool_id}}

    async def get_tool_status(self, *, tool_id: str) -> dict[str, Any]:
        self.calls.append(("tool_status", {"tool_id": tool_id}))
        return {"ok": True, "tool_id": tool_id, "status": "available", "certificates_valid": True, "expiring_soon": []}

    async def list_tools(self, *, project_uri: str = "", owner_uri: str = "", tool_type: str = "", status: str = "") -> dict[str, Any]:
        self.calls.append(("list_tools", {"project_uri": project_uri, "owner_uri": owner_uri, "tool_type": tool_type, "status": status}))
        return {"ok": True, "items": []}

    async def use_tool(self, *, tool_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("use_tool", {"tool_id": tool_id, "body": payload}))
        return {"ok": True, "tool": {"tool_id": tool_id, "status": "in_use"}, "smu_entries": []}

    async def maintain_tool(self, *, tool_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("maintain_tool", {"tool_id": tool_id, "body": payload}))
        return {"ok": True, "tool": {"tool_id": tool_id, "status": "available"}}

    async def retire_tool(self, *, tool_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("retire_tool", {"tool_id": tool_id, "body": payload}))
        return {"ok": True, "tool": {"tool_id": tool_id, "status": "retired"}}


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://cn.demo/executor/test-user"}


def _build_client(fake_service: _FakeSignPegService) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_signpeg_service] = lambda: fake_service
    return TestClient(app)


def test_toolpeg_routes() -> None:
    fake = _FakeSignPegService()
    with _build_client(fake) as client:
        reg_res = client.post(
            "/api/v1/tools/register",
            json={
                "tool_name": "电焊机Miller-03",
                "tool_code": "welder-miller-03",
                "tool_type": "reusable",
                "owner_type": "executor",
                "owner_uri": "v://cn.中北/executor/zhang-san",
                "project_uri": "v://cn.大锦/DJGS",
                "certificates": [],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        list_res = client.get(
            "/api/v1/tools/list?project_uri=v://cn.大锦/DJGS&tool_type=reusable",
            headers={"Authorization": "Bearer test-token"},
        )
        status_res = client.get("/api/v1/tools/TOOL-001/status", headers={"Authorization": "Bearer test-token"})
        get_res = client.get("/api/v1/tools/TOOL-001", headers={"Authorization": "Bearer test-token"})
        use_res = client.post(
            "/api/v1/tools/TOOL-001/use",
            json={"trip_id": "NINST-1", "trip_role": "construction.welding", "shifts": 1},
            headers={"Authorization": "Bearer test-token"},
        )
        maintain_res = client.post(
            "/api/v1/tools/TOOL-001/maintain",
            json={"note": "月度维保"},
            headers={"Authorization": "Bearer test-token"},
        )
        retire_res = client.post(
            "/api/v1/tools/TOOL-001/retire",
            json={"reason": "报废"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert reg_res.status_code == 200
    assert list_res.status_code == 200
    assert status_res.status_code == 200
    assert get_res.status_code == 200
    assert use_res.status_code == 200
    assert maintain_res.status_code == 200
    assert retire_res.status_code == 200

    call_names = [name for name, _ in fake.calls]
    assert "register_tool" in call_names
    assert "list_tools" in call_names
    assert "tool_status" in call_names
    assert "get_tool" in call_names
    assert "use_tool" in call_names
    assert "maintain_tool" in call_names
    assert "retire_tool" in call_names

