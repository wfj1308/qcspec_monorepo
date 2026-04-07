from __future__ import annotations

from services.api.domain.specir.integrations import (
    is_spu_ultimate_content,
    list_builtin_full_spu_library,
)


def test_list_builtin_full_spu_library_basic() -> None:
    payload = list_builtin_full_spu_library()
    assert payload["ok"] is True
    assert int(payload["count"]) >= 9
    items = payload["items"]
    uris = [str(item.get("uri") or "") for item in items]
    assert len(uris) == len(set(uris))
    assert all(uri.startswith("v://norm/spu/") for uri in uris)
    assert all("@v2024" in uri for uri in uris)


def test_full_spu_library_items_are_ultimate_schema() -> None:
    payload = list_builtin_full_spu_library()
    items = payload["items"]
    for row in items:
        content = row.get("content") or {}
        assert is_spu_ultimate_content(content) is True
        assert "schema_modules" in content
        assert content["schema_modules"] == ["Identity", "MeasureRule", "Consumption", "QCGate"]


def test_full_spu_library_contains_bored_pile_concrete() -> None:
    payload = list_builtin_full_spu_library()
    found = None
    for row in payload["items"]:
        if str(row.get("uri") or "").strip() == "v://norm/spu/highway/bridge/bored_pile_concrete@v2024":
            found = row
            break
    assert found is not None
    content = found["content"]
    assert content["measure_rule"]["unit"] == "m3"
    assert content["consumption"]["quota_ref"] == "v://norm/quota/concrete-casting@v1"
    metrics = [str(rule.get("metric") or "") for rule in content["qc_gate"]["rules"]]
    assert "slump" in metrics
