from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services.api.dependencies import get_normref_resolver, require_auth_identity
from services.api.infrastructure.http.app_factory import create_app


class _FakeNormRefResolver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def resolve_protocol(self, *, uri: str) -> dict[str, Any]:
        self.calls.append(("resolve", {"uri": uri}))
        if uri != "v://normref.com/qc/rebar-processing@v1":
            return {"ok": False, "error": "protocol_not_found", "uri": uri}
        return {
            "ok": True,
            "uri": uri,
            "source": "specir_registry",
            "schema_uri": "v://normref.com/schema/qc-v1",
            "protocol": {
                "uri": uri,
                "version": "v1",
                "gates": [
                    {
                        "check_id": "spacing",
                        "label": "钢筋间距偏差",
                        "severity": "mandatory",
                        "threshold": {"operator": "lte", "value": 10, "unit": "mm"},
                    }
                ],
            },
        }

    def verify_protocol(
        self,
        *,
        uri: str,
        actual_data: dict[str, Any] | None = None,
        design_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "verify",
                {
                    "uri": uri,
                    "actual_data": dict(actual_data or {}),
                    "design_data": dict(design_data or {}),
                    "context": dict(context or {}),
                },
            )
        )
        if uri != "v://normref.com/qc/rebar-processing@v1":
            return {"ok": False, "error": "protocol_not_found", "uri": uri}
        spacing = float((actual_data or {}).get("spacing") or 0)
        result = "PASS" if spacing <= 10 else "FAIL"
        failed = [] if result == "PASS" else ["spacing"]
        return {
            "ok": True,
            "uri": uri,
            "result": result,
            "failed_gates": failed,
            "proof_hash": "fake-proof-hash",
            "sealed_at": "2026-04-07T00:00:00+00:00",
        }


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://normref.com/executor/test-user"}


def _build_client(fake_resolver: _FakeNormRefResolver) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_normref_resolver] = lambda: fake_resolver
    return TestClient(app)


def test_normref_resolve_route() -> None:
    fake = _FakeNormRefResolver()
    with _build_client(fake) as client:
        response = client.get(
            "/v1/normref/resolve",
            params={"uri": "v://normref.com/qc/rebar-processing@v1"},
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["uri"] == "v://normref.com/qc/rebar-processing@v1"
    assert payload["schema_uri"] == "v://normref.com/schema/qc-v1"


def test_normref_resolve_route_api_alias() -> None:
    fake = _FakeNormRefResolver()
    with _build_client(fake) as client:
        response = client.get(
            "/api/normref/resolve",
            params={"uri": "v://normref.com/qc/rebar-processing@v1"},
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["uri"] == "v://normref.com/qc/rebar-processing@v1"


def test_normref_verify_route_supports_spu_uri_auto_mapping() -> None:
    fake = _FakeNormRefResolver()
    with _build_client(fake) as client:
        response = client.post(
            "/v1/normref/verify",
            json={
                "spu_uri": "v://normref.com/spu/rebar-processing@v1",
                "actual_data": {"spacing": 8},
                "design_data": {"spacing": 10},
                "context": {"dtorole": "SUPERVISOR"},
            },
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["result"] == "PASS"

    verify_call = next((data for name, data in fake.calls if name == "verify"), {})
    assert verify_call.get("uri") == "v://normref.com/qc/rebar-processing@v1"
