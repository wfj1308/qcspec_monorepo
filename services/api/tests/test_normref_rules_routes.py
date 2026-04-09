from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services.api.dependencies import get_normref_resolver, require_auth_identity
from services.api.infrastructure.http.app_factory import create_app


class _FakeNormRefRuleResolver:
    def __init__(self) -> None:
        self.refresh_calls = 0
        self._overrides: dict[str, dict[str, Any]] = {}

    def get_rule(self, *, rule_id: str, version: str = "latest", scope: str = "") -> dict[str, Any]:
        if rule_id != "bridge.pile-hole-check.hole-diameter-tolerance":
            return {"ok": False, "error": "rule_not_found"}
        if version not in {"latest", "2026-04"}:
            return {"ok": False, "error": "rule_version_not_found"}
        return {
            "ok": True,
            "rule_id": rule_id,
            "requested_version": version,
            "requested_scope": scope,
            "resolved_version": "2026-04",
            "resolved_scope": scope or "industry",
            "uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04",
            "category": "bridge/pile-hole-check",
            "hash": "sha256:test",
            "rule": {"rule_id": rule_id, "version": "2026-04"},
        }

    def list_rules(self, *, category: str = "", version: str = "latest", scope: str = "") -> dict[str, Any]:
        return {
            "ok": True,
            "category": category,
            "requested_version": version,
            "requested_scope": scope,
            "count": 1,
            "rules": [
                {
                    "rule_id": "bridge.pile-hole-check.hole-diameter-tolerance",
                    "version": "2026-04",
                    "uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04",
                    "category": "bridge/pile-hole-check",
                    "hash": "sha256:test",
                    "scope": scope or "industry",
                }
            ],
        }

    def validate_rules(
        self,
        *,
        rules: list[str],
        data: dict[str, Any] | None = None,
        normref_version: str = "latest",
        scope: str = "",
    ) -> dict[str, Any]:
        if not rules:
            return {"ok": False, "error": "rules_required"}
        return {
            "ok": True,
            "requested_version": normref_version,
            "requested_scope": scope,
            "passed": True,
            "failed_rules": [],
            "results": [{"rule_id": rules[0], "passed": True, "result": "PASS"}],
            "rule_snapshots": [{"rule_id": rules[0], "version": "2026-04", "hash": "sha256:test"}],
            "normref_snapshot_hash": "sha256:aggregate",
        }

    def list_rule_conflicts(self, *, category: str = "", version: str = "latest", scope: str = "") -> dict[str, Any]:
        return {
            "ok": True,
            "category": category,
            "requested_version": version,
            "requested_scope": scope,
            "count": 1,
            "conflicts": [
                {
                    "rule_id": "bridge.pile-hole-check.hole-diameter-tolerance",
                    "version": "2026-04",
                    "selected_uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04",
                    "selected_scope": "industry",
                    "candidate_count": 2,
                    "candidates": [
                        {
                            "uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04",
                            "scope": "industry",
                            "source_std_code": "JTG-F80-1-2017",
                            "hash": "sha256:test",
                        },
                        {
                            "uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04-local",
                            "scope": "local",
                            "source_std_code": "DB-TEST-2026",
                            "hash": "sha256:test2",
                        },
                    ],
                }
            ],
        }

    def refresh_rule_catalog(self) -> dict[str, Any]:
        self.refresh_calls += 1
        return {"ok": True, "count": 1}

    def list_rule_overrides(self) -> dict[str, Any]:
        rows = sorted(self._overrides.values(), key=lambda x: (str(x.get("rule_id")), str(x.get("version"))))
        return {"ok": True, "count": len(rows), "overrides": rows}

    def set_rule_override(
        self,
        *,
        rule_id: str,
        version: str,
        selected_uri: str,
        reason: str = "",
        updated_by: str = "",
    ) -> dict[str, Any]:
        key = f"{rule_id}@{version}"
        row = {
            "rule_id": rule_id,
            "version": version,
            "selected_uri": selected_uri,
            "reason": reason,
            "updated_by": updated_by,
            "updated_at": "2026-04-09T10:00:00Z",
        }
        self._overrides[key] = row
        return {"ok": True, "override": row}

    def clear_rule_override(self, *, rule_id: str, version: str) -> dict[str, Any]:
        key = f"{rule_id}@{version}"
        existed = key in self._overrides
        self._overrides.pop(key, None)
        return {"ok": True, "removed": existed, "rule_id": rule_id, "version": version}


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://normref.com/executor/test-user"}


def _build_client(fake_resolver: _FakeNormRefRuleResolver) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_normref_resolver] = lambda: fake_resolver
    return TestClient(app)


def test_normref_get_rule_route() -> None:
    fake = _FakeNormRefRuleResolver()
    with _build_client(fake) as client:
        response = client.get(
            "/v1/normref/rules/bridge.pile-hole-check.hole-diameter-tolerance",
            params={"version": "latest"},
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["resolved_version"] == "2026-04"


def test_normref_list_rules_route() -> None:
    fake = _FakeNormRefRuleResolver()
    with _build_client(fake) as client:
        response = client.get(
            "/v1/normref/rules",
            params={"category": "bridge/pile-hole-check", "version": "latest"},
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["count"] == 1


def test_normref_list_rules_with_refresh_flag() -> None:
    fake = _FakeNormRefRuleResolver()
    with _build_client(fake) as client:
        response = client.get(
            "/v1/normref/rules",
            params={"category": "bridge/pile-hole-check", "version": "latest", "refresh": "true"},
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert fake.refresh_calls == 1


def test_normref_refresh_rules_route() -> None:
    fake = _FakeNormRefRuleResolver()
    with _build_client(fake) as client:
        response = client.post(
            "/api/normref/rules/refresh",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert fake.refresh_calls == 1


def test_normref_validate_rules_api_alias_route() -> None:
    fake = _FakeNormRefRuleResolver()
    with _build_client(fake) as client:
        response = client.post(
            "/api/normref/validate",
            json={
                "rules": ["bridge.pile-hole-check.hole-diameter-tolerance"],
                "data": {"actual_data": {"hole_diameter": 1.48}, "design_data": {"hole_diameter": 1.5}},
                "normref_version": "2026-04",
            },
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["passed"] is True
    assert payload["normref_snapshot_hash"].startswith("sha256:")


def test_normref_list_rule_conflicts_route() -> None:
    fake = _FakeNormRefRuleResolver()
    with _build_client(fake) as client:
        response = client.get(
            "/v1/normref/rules-conflicts",
            params={"category": "bridge/pile-hole-check", "version": "latest"},
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["conflicts"][0]["selected_scope"] == "industry"


def test_normref_rule_override_set_list_clear_routes() -> None:
    fake = _FakeNormRefRuleResolver()
    with _build_client(fake) as client:
        set_response = client.post(
            "/v1/normref/rules-overrides/set",
            json={
                "rule_id": "bridge.pile-hole-check.hole-diameter-tolerance",
                "version": "2026-04",
                "selected_uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04-local",
                "reason": "local project override",
                "updated_by": "qa-admin",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        list_response = client.get(
            "/v1/normref/rules-overrides",
            headers={"Authorization": "Bearer test-token"},
        )
        clear_response = client.post(
            "/v1/normref/rules-overrides/clear",
            json={
                "rule_id": "bridge.pile-hole-check.hole-diameter-tolerance",
                "version": "2026-04",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert set_response.status_code == 200
    set_payload = set_response.json()
    assert set_payload["ok"] is True
    assert set_payload["override"]["selected_uri"].endswith("@2026-04-local")

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["ok"] is True
    assert list_payload["count"] == 1

    assert clear_response.status_code == 200
    clear_payload = clear_response.json()
    assert clear_payload["ok"] is True
    assert clear_payload["removed"] is True
