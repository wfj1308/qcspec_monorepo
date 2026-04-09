from __future__ import annotations

import json
from pathlib import Path

from services.api.core.norm.service import NormRefResolverService


class _FakePort:
    def resolve_threshold(self, **_: object) -> dict[str, object]:
        return {}

    def get_spec_dict(self, **_: object) -> dict[str, object]:
        return {}


def _write_rule(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_normref_rule_scope_priority_and_conflicts(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "docs" / "normref"
    rule_root = root / "rule"

    rule_id = "bridge.pile-hole-check.hole-diameter-tolerance"

    national = {
        "rule_id": rule_id,
        "version": "2026-04",
        "uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04",
        "category": "bridge/pile-hole-check",
        "scope": "national",
        "source_level": "national",
        "source_std_code": "GB-TEST-2026",
        "gates": [
            {
                "check_id": "hole_diameter",
                "label": "孔径",
                "severity": "mandatory",
                "threshold": {"operator": "lte", "value": 0.05, "unit": "%"},
                "norm_ref": "GB-TEST 7.1",
            }
        ],
    }

    local = {
        "rule_id": rule_id,
        "version": "2026-04",
        "uri": "v://normref.com/rule/bridge/pile-hole-check/hole-diameter-tolerance@2026-04-local",
        "category": "bridge/pile-hole-check",
        "scope": "local",
        "source_level": "local",
        "source_std_code": "DB-TEST-2026",
        "gates": [
            {
                "check_id": "hole_diameter",
                "label": "孔径",
                "severity": "mandatory",
                "threshold": {"operator": "lte", "value": 0.03, "unit": "%"},
                "norm_ref": "DB-TEST 5.2",
            }
        ],
    }

    _write_rule(rule_root / "bridge" / "pile-hole-check" / "hole-diameter-tolerance@2026-04-national.json", national)
    _write_rule(rule_root / "bridge" / "pile-hole-check" / "hole-diameter-tolerance@2026-04-local.json", local)

    monkeypatch.setattr(NormRefResolverService, "_normref_docs_root", staticmethod(lambda: root.resolve()))
    NormRefResolverService.clear_rule_catalog_cache()

    svc = NormRefResolverService(sb=None, port=_FakePort())

    picked = svc.get_rule(rule_id=rule_id, version="2026-04")
    assert picked["ok"] is True
    assert picked["resolved_scope"] == "national"
    assert picked["source_std_code"] == "GB-TEST-2026"

    picked_local = svc.get_rule(rule_id=rule_id, version="2026-04", scope="local")
    assert picked_local["ok"] is True
    assert picked_local["resolved_scope"] == "local"
    assert picked_local["source_std_code"] == "DB-TEST-2026"

    conflicts = svc.list_rule_conflicts(category="bridge/pile-hole-check", version="2026-04")
    assert conflicts["ok"] is True
    assert conflicts["count"] == 1
    assert conflicts["conflicts"][0]["selected_scope"] == "national"

    validate_out = svc.validate_rules(
        rules=[rule_id],
        data={"actual_data": {"hole_diameter": 1.52}, "design_data": {"hole_diameter": 1.5}},
        normref_version="2026-04",
    )
    assert validate_out["ok"] is True
    assert validate_out["passed"] is True
    assert validate_out["results"][0]["resolved_scope"] == "national"
