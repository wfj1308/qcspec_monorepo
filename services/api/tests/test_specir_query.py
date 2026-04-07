from __future__ import annotations

from services.api.domain.specir.integrations import list_spu_library


def test_list_spu_library_builtin_default() -> None:
    out = list_spu_library(source="builtin")
    assert out["ok"] is True
    assert int(out["count"]) >= 9
    assert all(str(item.get("uri") or "").startswith("v://norm/spu/") for item in out["items"])


def test_list_spu_library_filter_by_version_and_query() -> None:
    out = list_spu_library(source="builtin", version="v2024", q="bored_pile")
    assert out["ok"] is True
    assert out["count"] >= 1
    assert any(str(item.get("uri") or "") == "v://norm/spu/highway/bridge/bored_pile_concrete@v2024" for item in out["items"])


def test_list_spu_library_filter_by_industry() -> None:
    out = list_spu_library(source="builtin", industry="highway")
    assert out["ok"] is True
    assert out["count"] >= 1
    assert all("highway" in str(item.get("industry") or "").lower() for item in out["items"])
