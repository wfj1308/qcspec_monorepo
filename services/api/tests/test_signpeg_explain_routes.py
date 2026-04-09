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

    async def explain_gate(self, *, body: dict[str, Any]) -> dict[str, Any]:
        body = self._payload(body)
        self.calls.append(("explain_gate", {"body": body}))
        return {
            "ok": True,
            "result": {
                "passed": False,
                "summary": "成孔检查不合格",
                "issues": [{"field": "孔径检查", "severity": "blocking"}],
                "next_steps": ["重新成孔后复检"],
                "norm_refs": ["JTG F80/1-2017 第7.1条"],
                "language": body.get("language", "zh"),
            },
        }

    async def explain_process(self, *, body: dict[str, Any]) -> dict[str, Any]:
        body = self._payload(body)
        self.calls.append(("explain_process", {"body": body}))
        return {
            "ok": True,
            "result": {
                "step": "水下混凝土灌注（桥施9表）",
                "status": "locked",
                "summary": "当前无法进行",
                "blocking_reasons": [{"type": "material_iqc_missing"}],
                "estimated_unblock": "完成后自动解锁",
                "language": body.get("language", "zh"),
            },
        }

    async def validate_field(self, *, body: dict[str, Any]) -> dict[str, Any]:
        body = self._payload(body)
        self.calls.append(("validate_field", {"body": body}))
        return {
            "ok": True,
            "result": {
                "field": body.get("field_key"),
                "value": body.get("value"),
                "status": "blocking",
                "message": "孔径偏差超标",
                "norm_ref": "JTG F80/1-2017 第7.1条",
                "language": body.get("language", "zh"),
            },
        }


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://cn.demo/executor/test-user"}


def _build_client(fake_service: _FakeSignPegService) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_signpeg_service] = lambda: fake_service
    return TestClient(app)


def test_signpeg_explain_routes() -> None:
    fake = _FakeSignPegService()
    with _build_client(fake) as client:
        gate_res = client.post(
            "/api/v1/explain/gate",
            json={
                "form_code": "桥施7表",
                "gate_result": {"result": "FAIL"},
                "norm_context": {"protocol_uri": "v://normref.com/doc-type/bridge/pile-hole-check@v1"},
                "language": "zh",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        process_res = client.post(
            "/api/v1/explain/process",
            json={
                "project_uri": "v://project/demo",
                "component_uri": "v://project/demo/pile/P3",
                "step_id": "pile-pour-04",
                "current_status": "locked",
                "language": "zh",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        field_res = client.post(
            "/api/v1/explain/field-validate",
            json={
                "form_code": "桥施7表",
                "field_key": "hole_diameter",
                "value": 1.38,
                "context": {"design_diameter": 1.5, "tolerance_pct": 5},
                "language": "zh",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert gate_res.status_code == 200
    assert gate_res.json()["result"]["passed"] is False
    assert process_res.status_code == 200
    assert process_res.json()["result"]["status"] == "locked"
    assert field_res.status_code == 200
    assert field_res.json()["result"]["status"] == "blocking"

    call_names = [name for name, _ in fake.calls]
    assert "explain_gate" in call_names
    assert "explain_process" in call_names
    assert "validate_field" in call_names
