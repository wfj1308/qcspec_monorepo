from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services.api.dependencies import get_normref_ingest_engine, get_normref_resolver, require_auth_identity
from services.api.domain.specir.runtime.normref_ingest import NormRefIngestEngine
from services.api.infrastructure.http.app_factory import create_app


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://normref.com/executor/test-user"}


class _FakeNormRefResolver:
    def __init__(self) -> None:
        self.refresh_calls = 0

    def refresh_rule_catalog(self) -> dict[str, Any]:
        self.refresh_calls += 1
        return {"ok": True, "count": 123}


def _build_client() -> TestClient:
    app = create_app()
    engine = NormRefIngestEngine()
    resolver = _FakeNormRefResolver()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_normref_ingest_engine] = lambda: engine
    app.dependency_overrides[get_normref_resolver] = lambda: resolver
    return TestClient(app)


def test_normref_ingest_upload_and_list_candidates() -> None:
    with _build_client() as client:
        upload = client.post(
            "/v1/normref/ingest/upload",
            headers={"Authorization": "Bearer test-token"},
            files={"file": ("JTG-F80-1-2017.txt", "7.1.2 成孔检验\n孔径允许偏差 ±5%".encode("utf-8"), "text/plain")},
            data={"std_code": "JTG-F80-1-2017", "title": "土建工程", "level": "industry"},
        )
        assert upload.status_code == 200
        payload = upload.json()
        assert payload["ok"] is True
        job_id = payload["job"]["job_id"]

        candidates = client.get(
            f"/v1/normref/ingest/jobs/{job_id}/candidates",
            headers={"Authorization": "Bearer test-token"},
        )
        assert candidates.status_code == 200
        rows = candidates.json()
        assert rows["ok"] is True
        assert rows["count"] >= 1
        assert rows["candidates"][0]["status"] == "pending"


def test_normref_ingest_publish_flow() -> None:
    with _build_client() as client:
        upload = client.post(
            "/api/normref/ingest/upload",
            headers={"Authorization": "Bearer test-token"},
            files={"file": ("JTG-2182-2020.txt", "4.2.1 机电检验\n检测强度不小于30MPa".encode("utf-8"), "text/plain")},
            data={"std_code": "JTG-2182-2020", "title": "机电工程", "level": "industry"},
        )
        assert upload.status_code == 200
        job = upload.json()["job"]
        job_id = job["job_id"]
        candidate_id = job["candidates"][0]["candidate_id"]

        patch = client.post(
            f"/api/normref/ingest/candidates/{candidate_id}/patch",
            headers={"Authorization": "Bearer test-token"},
            json={
                "job_id": job_id,
                "patch": {
                    "operator": "gte",
                    "threshold_value": "30",
                    "unit": "MPa",
                    "norm_ref": "4.2.1",
                },
            },
        )
        assert patch.status_code == 200
        patched = patch.json()["candidate"]
        assert patched["operator"] == "gte"
        assert patched["threshold_value"] == "30"
        assert patched["unit"] == "MPa"

        approve = client.post(
            f"/api/normref/ingest/candidates/{candidate_id}/approve",
            headers={"Authorization": "Bearer test-token"},
            json={"job_id": job_id},
        )
        assert approve.status_code == 200
        assert approve.json()["candidate"]["status"] == "approved"

        publish = client.post(
            "/api/normref/ingest/publish",
            headers={"Authorization": "Bearer test-token"},
            json={"job_id": job_id, "version_tag": "2026-04", "write_to_docs": True},
        )
        assert publish.status_code == 200
        payload = publish.json()
        assert payload["ok"] is True
        assert payload["published_count"] >= 1
        assert str(payload["snapshot_hash"]).startswith("sha256:")
        assert payload["rules"][0]["operator"] == "gte"
        assert payload["rule_catalog_count"] == 123
