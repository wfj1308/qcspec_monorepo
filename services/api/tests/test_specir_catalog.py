from __future__ import annotations

from services.api.domain.specir.integrations import list_builtin_specir_catalog


def test_list_builtin_specir_catalog_basic() -> None:
    payload = list_builtin_specir_catalog()
    assert payload["ok"] is True
    assert int(payload["count"]) > 0
    items = payload["items"]
    assert isinstance(items, list)
    uris = [str(item.get("uri") or "") for item in items]
    assert all(uri.startswith("v://norm/") for uri in uris)
    assert len(uris) == len(set(uris))


def test_builtin_spu_items_use_ultimate_schema_modules() -> None:
    payload = list_builtin_specir_catalog()
    items = payload["items"]
    spu_items = [item for item in items if str(item.get("kind") or "").strip() == "spu"]
    assert spu_items
    for row in spu_items:
        content = row.get("content") or {}
        assert isinstance(content, dict)
        assert "identity" in content
        assert "measure_rule" in content
        assert "consumption" in content
        assert "qc_gate" in content
        modules = content.get("schema_modules")
        assert modules == ["Identity", "MeasureRule", "Consumption", "QCGate"]
