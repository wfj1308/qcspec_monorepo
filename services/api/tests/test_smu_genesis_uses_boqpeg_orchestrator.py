from __future__ import annotations

from services.api.domain.smu.runtime import smu_genesis_helpers as genesis_helpers


def test_initialize_genesis_chain_delegates_to_boqpeg(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_initialize_boq_genesis_chain(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "preview": [], "created": []}

    monkeypatch.setattr(genesis_helpers, "initialize_boq_genesis_chain", _fake_initialize_boq_genesis_chain)

    result = genesis_helpers.initialize_genesis_chain(
        sb=None,
        project_uri="v://project/demo",
        project_id="",
        boq_items=[],
        root_uri="v://project/demo/boq/400",
        norm_root="v://project/demo/normContext",
        owner_uri="",
        upload_file_name="demo.csv",
        commit=False,
    )
    assert result["ok"] is True
    assert captured["project_uri"] == "v://project/demo"
    assert captured["source_file"] == "demo.csv"
    assert captured["commit"] is False

