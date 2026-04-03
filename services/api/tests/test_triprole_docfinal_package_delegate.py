from __future__ import annotations

from services.api.domain.execution.runtime import triprole_engine as engine


def test_build_docfinal_package_for_boq_delegates_to_runtime(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def _runtime_stub(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True, "boq_item_uri": kwargs.get("boq_item_uri")}

    monkeypatch.setattr(  # type: ignore[attr-defined]
        engine,
        "_build_docfinal_package_for_boq_runtime",
        _runtime_stub,
    )

    out = engine.build_docfinal_package_for_boq(
        boq_item_uri="v://boq/1-1",
        sb=object(),
        aggregate_anchor_code="1",
        aggregate_direction="down",
        aggregate_level="item",
    )

    assert out["ok"] is True
    assert out["boq_item_uri"] == "v://boq/1-1"
    assert captured["boq_item_uri"] == "v://boq/1-1"
    assert captured["module_file"] == engine.__file__
    assert callable(captured["get_boq_realtime_status_fn"])
    assert callable(captured["get_full_lineage_fn"])
    assert callable(captured["trace_asset_origin_fn"])
    assert callable(captured["transfer_asset_fn"])
