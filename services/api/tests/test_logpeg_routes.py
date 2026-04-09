from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services.api.dependencies import get_logpeg_service, require_auth_identity
from services.api.infrastructure.http.app_factory import create_app


class _FakeLogPegService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def daily(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("daily", kwargs))
        return {"ok": True, "log": {"log_date": kwargs.get("date"), "project_uri": "v://cn.大锦/DJGS"}}

    async def weekly(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("weekly", kwargs))
        return {"ok": True, "week_start": kwargs.get("week_start"), "daily_logs": []}

    async def monthly(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("monthly", kwargs))
        return {"ok": True, "month": kwargs.get("month"), "daily_logs": []}

    async def sign(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("sign", kwargs))
        return {"ok": True, "log": {"locked": True, "v_uri": "v://cn.大锦/DJGS/log/2026-04-06"}, "sign_proof": "GP-LOGPEG-TEST"}

    async def export(self, **kwargs: Any) -> tuple[bytes, str, str]:
        self.calls.append(("export", kwargs))
        fmt = kwargs.get("format") or "pdf"
        if fmt == "json":
            return (b"{}", "logpeg.json", "application/json")
        if fmt == "word":
            return (b"PK\x03\x04mock", "logpeg.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        return (b"%PDF-1.4\n%mock\n", "logpeg.pdf", "application/pdf")


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://cn.demo/executor/test-user"}


def _build_client(fake_service: _FakeLogPegService) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_logpeg_service] = lambda: fake_service
    return TestClient(app)


def test_logpeg_routes_v2_and_legacy() -> None:
    fake = _FakeLogPegService()
    with _build_client(fake) as client:
        daily = client.get(
            "/api/v1/logpeg/33333333-3333-4333-8333-333333333333/daily?date=2026-04-06",
            headers={"Authorization": "Bearer test-token"},
        )
        weekly = client.get(
            "/api/v1/logpeg/33333333-3333-4333-8333-333333333333/weekly?week_start=2026-04-01&language=en",
            headers={"Authorization": "Bearer test-token"},
        )
        monthly = client.get(
            "/api/v1/logpeg/33333333-3333-4333-8333-333333333333/monthly?month=2026-04",
            headers={"Authorization": "Bearer test-token"},
        )
        sign = client.post(
            "/api/v1/logpeg/33333333-3333-4333-8333-333333333333/daily/sign",
            json={"date": "2026-04-06", "executor_uri": "v://cn.中北/executor/li-gong", "weather": "晴", "temperature_range": "12-24℃"},
            headers={"Authorization": "Bearer test-token"},
        )
        export_pdf = client.get(
            "/api/v1/logpeg/33333333-3333-4333-8333-333333333333/daily/export?date=2026-04-06&format=pdf",
            headers={"Authorization": "Bearer test-token"},
        )
        legacy_sign = client.post(
            "/api/v1/logpeg/sign/33333333-3333-4333-8333-333333333333?date=2026-04-06",
            json={"executor_uri": "v://cn.中北/executor/li-gong", "weather": "晴"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert daily.status_code == 200
    assert weekly.status_code == 200
    assert monthly.status_code == 200
    assert sign.status_code == 200
    assert export_pdf.status_code == 200
    assert export_pdf.headers.get("content-type", "").startswith("application/pdf")
    assert legacy_sign.status_code == 200

    call_names = [name for name, _ in fake.calls]
    assert "daily" in call_names
    assert "weekly" in call_names
    assert "monthly" in call_names
    assert "sign" in call_names
    assert "export" in call_names
