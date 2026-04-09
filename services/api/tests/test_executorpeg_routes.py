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

    async def register_executorpeg(self, *, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("register", {"body": payload}))
        return {
            "ok": True,
            "executor_uri": "v://cn.中北/executor/zhang-san",
            "executor_id": "EXEC-001",
            "registration_proof": "PROOF-EXEC-A1B2C3D4",
            "status": "available",
        }

    async def import_executors(self, *, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("import", {"body": payload}))
        return {"ok": True, "count": len(payload.get("items") or []), "items": payload.get("items") or []}

    async def get_executor_by_id(self, *, executor_id: str) -> dict[str, Any]:
        self.calls.append(("get", {"executor_id": executor_id}))
        return {"ok": True, "executor": {"executor_id": executor_id, "name": "张三"}}

    async def get_executor_status(self, *, executor_id: str) -> dict[str, Any]:
        self.calls.append(("status", {"executor_id": executor_id}))
        return {"ok": True, "executor_id": executor_id, "status": "available", "certificates_valid": True, "expiring_soon": []}

    async def list_executors(self, *, org_uri: str = "") -> dict[str, Any]:
        self.calls.append(("list", {"org_uri": org_uri}))
        return {"ok": True, "items": []}

    async def search_executors(self, *, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("search", {"body": payload}))
        return {"ok": True, "items": [{"executor_id": "EXEC-001"}]}

    async def get_org_members(self, *, org_uri: str) -> dict[str, Any]:
        self.calls.append(("org_members", {"org_uri": org_uri}))
        return {"ok": True, "org_uri": org_uri, "members": []}

    async def get_org_branches(self, *, org_uri: str) -> dict[str, Any]:
        self.calls.append(("org_branches", {"org_uri": org_uri}))
        return {"ok": True, "org_uri": org_uri, "branches": [], "branch_count": 0}

    async def add_org_member(self, *, org_uri: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("add_org_member", {"org_uri": org_uri, "body": payload}))
        return {"ok": True, "org_uri": org_uri, "member_executor_uri": payload.get("member_executor_uri")}

    async def add_org_project(self, *, org_uri: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("add_org_project", {"org_uri": org_uri, "body": payload}))
        return {"ok": True, "org_uri": org_uri, "project_uris": [payload.get("project_uri")]}

    async def add_executor_certificate(self, *, executor_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("add_certificate", {"executor_id": executor_id, "body": payload}))
        return {"ok": True, "executor": {"executor_id": executor_id}}

    async def add_executor_skill(self, *, executor_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("add_skill", {"executor_id": executor_id, "body": payload}))
        return {"ok": True, "executor": {"executor_id": executor_id}}

    async def add_executor_requires(self, *, executor_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("add_requires", {"executor_id": executor_id, "body": payload}))
        return {"ok": True, "executor": {"executor_id": executor_id, "requires": payload.get("tool_executor_uris") or []}}

    async def use_executor(self, *, executor_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("use_executor", {"executor_id": executor_id, "body": payload}))
        return {"ok": True, "executor": {"executor_id": executor_id}, "smu_entries": []}

    async def maintain_executor(self, *, executor_id: str, body: Any) -> dict[str, Any]:
        payload = self._payload(body)
        self.calls.append(("maintain_executor", {"executor_id": executor_id, "body": payload}))
        return {"ok": True, "executor": {"executor_id": executor_id}, "maintenance_proof": "PROOF-EXEC-MAINT-001"}


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://cn.demo/executor/test-user"}


def _build_client(fake_service: _FakeSignPegService) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_signpeg_service] = lambda: fake_service
    return TestClient(app)


def test_executorpeg_routes() -> None:
    fake = _FakeSignPegService()
    with _build_client(fake) as client:
        register_res = client.post(
            "/api/v1/executors/register",
            json={
                "name": "张三",
                "executor_type": "human",
                "org_uri": "v://cn.中北/",
                "capacity": {"maximum": 10, "unit": "tasks"},
                "energy": {"billing_unit": "工时", "rate": 280, "currency": "CNY", "billing_formula": "trip.duration * rate"},
                "certificates": [],
                "skills": [],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        import_res = client.post(
            "/api/v1/executors/import",
            json={"items": [{"name": "石玉山", "executor_type": "human", "org_uri": "v://cn.中北/"}]},
            headers={"Authorization": "Bearer test-token"},
        )
        list_res = client.get("/api/v1/executors/list?org_uri=v://cn.中北/", headers={"Authorization": "Bearer test-token"})
        search_res = client.get(
            "/api/v1/executors/search?skill_uri=v://normref.com/skill/bridge-inspection@v1&type=human&available=true",
            headers={"Authorization": "Bearer test-token"},
        )
        org_members_res = client.get(
            "/api/v1/executors/orgs/v://cn.%E4%B8%AD%E5%8C%97/members",
            headers={"Authorization": "Bearer test-token"},
        )
        org_branches_res = client.get(
            "/api/v1/executors/orgs/v://cn.%E4%B8%AD%E5%8C%97/branches",
            headers={"Authorization": "Bearer test-token"},
        )
        org_add_member_res = client.post(
            "/api/v1/executors/orgs/v://cn.%E4%B8%AD%E5%8C%97/members/add",
            json={"member_executor_uri": "v://cn.涓寳/executor/zhang-san"},
            headers={"Authorization": "Bearer test-token"},
        )
        org_add_project_res = client.post(
            "/api/v1/executors/orgs/v://cn.%E4%B8%AD%E5%8C%97/projects/add",
            json={"project_uri": "v://cn.澶ч敠/DJGS"},
            headers={"Authorization": "Bearer test-token"},
        )
        status_res = client.get("/api/v1/executors/EXEC-001/status", headers={"Authorization": "Bearer test-token"})
        get_res = client.get("/api/v1/executors/EXEC-001", headers={"Authorization": "Bearer test-token"})
        cert_res = client.post(
            "/api/v1/executors/EXEC-001/certificates/add",
            json={
                "certificate": {
                    "cert_id": "c1",
                    "cert_type": "监理工程师证",
                    "cert_no": "CERT-001",
                    "issued_by": "v://cn.住建部/",
                    "issued_date": "2026-01-01",
                    "valid_until": "2028-12-31",
                    "v_uri": "v://cn.中北/cert/c1",
                    "status": "active",
                    "scan_hash": "sha256:c1",
                }
            },
            headers={"Authorization": "Bearer test-token"},
        )
        skill_res = client.post(
            "/api/v1/executors/EXEC-001/skills/add",
            json={
                "skill": {
                    "skill_uri": "v://normref.com/skill/bridge-inspection@v1",
                    "skill_name": "桥梁监理",
                    "level": 3,
                    "verified_by": "v://normref.com/",
                    "valid_until": "2028-12-31",
                    "proof_uri": "v://proof/skill/1",
                }
            },
            headers={"Authorization": "Bearer test-token"},
        )
        requires_res = client.post(
            "/api/v1/executors/EXEC-001/requires/add",
            json={"tool_executor_uris": ["v://cn.涓寳/executor/welder-miller-03"]},
            headers={"Authorization": "Bearer test-token"},
        )
        use_res = client.post(
            "/api/v1/executors/EXEC-001/use",
            json={
                "trip_id": "TRIP-001",
                "trip_uri": "v://cn.demo/trip/2026/0408/TRIP-001",
                "trip_role": "constructor.sign",
                "duration_hours": 2,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        maintain_res = client.post(
            "/api/v1/executors/EXEC-001/maintain",
            json={"note": "routine"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert register_res.status_code == 200
    assert import_res.status_code == 200
    assert list_res.status_code == 200
    assert search_res.status_code == 200
    assert org_members_res.status_code == 200
    assert org_branches_res.status_code == 200
    assert org_add_member_res.status_code == 200
    assert org_add_project_res.status_code == 200
    assert status_res.status_code == 200
    assert get_res.status_code == 200
    assert cert_res.status_code == 200
    assert skill_res.status_code == 200
    assert requires_res.status_code == 200
    assert use_res.status_code == 200
    assert maintain_res.status_code == 200

    call_names = [name for name, _ in fake.calls]
    assert "register" in call_names
    assert "import" in call_names
    assert "list" in call_names
    assert "search" in call_names
    assert "org_members" in call_names
    assert "org_branches" in call_names
    assert "add_org_member" in call_names
    assert "add_org_project" in call_names
    assert "status" in call_names
    assert "get" in call_names
    assert "add_certificate" in call_names
    assert "add_skill" in call_names
    assert "add_requires" in call_names
    assert "use_executor" in call_names
    assert "maintain_executor" in call_names
