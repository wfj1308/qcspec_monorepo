from __future__ import annotations

from services.api.domain.execution.lineage import triprole_lineage_entry as entry


class _FakeEngine:
    def __init__(self, _sb: object) -> None:
        self.called_get_by_id: list[str] = []
        self.called_get_chain: list[tuple[str, int]] = []

    def get_chain(self, proof_id: str, *, max_depth: int) -> list[dict[str, object]]:
        self.called_get_chain.append((proof_id, max_depth))
        return [{"proof_id": proof_id, "max_depth": max_depth}]

    def get_by_id(self, proof_id: str) -> dict[str, object]:
        self.called_get_by_id.append(proof_id)
        return {"proof_id": proof_id}


def test_aggregate_provenance_chain_wires_engine_chain(monkeypatch) -> None:
    monkeypatch.setattr(entry, "ProofUTXOEngine", _FakeEngine)

    captured: dict[str, object] = {}

    def _fake_build_provenance_aggregate(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        chain = kwargs["get_chain_fn"]("GP-IN-1", 128)
        captured["chain_probe"] = chain
        return {"ok": True}

    monkeypatch.setattr(entry, "_build_provenance_aggregate", _fake_build_provenance_aggregate)

    out = entry.aggregate_provenance_chain(utxo_id="GP-IN-1", sb=object(), max_depth=128)
    assert out == {"ok": True}
    assert captured["utxo_id"] == "GP-IN-1"
    assert captured["max_depth"] == 128
    assert captured["chain_probe"] == [{"proof_id": "GP-IN-1", "max_depth": 128}]


def test_trace_asset_origin_wires_realtime_callback(monkeypatch) -> None:
    monkeypatch.setattr(entry, "ProofUTXOEngine", _FakeEngine)

    captured: dict[str, object] = {}

    def _fake_trace_asset_origin(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        realtime = kwargs["get_boq_realtime_status_fn"](object(), "v://project/demo", 77)
        captured["realtime_probe"] = realtime
        return {"ok": True}

    monkeypatch.setattr(entry, "_trace_asset_origin", _fake_trace_asset_origin)

    def _fake_realtime(_sb: object, project_uri: str, limit: int) -> dict[str, object]:
        return {"project_uri": project_uri, "limit": limit}

    out = entry.trace_asset_origin(
        sb=object(),
        utxo_id="GP-IN-1",
        boq_item_uri="v://project/demo/boq/1-1",
        project_uri="v://project/demo",
        max_depth=64,
        get_boq_realtime_status_fn=_fake_realtime,
    )

    assert out == {"ok": True}
    assert captured["utxo_id"] == "GP-IN-1"
    assert captured["max_depth"] == 64
    assert captured["realtime_probe"] == {"project_uri": "v://project/demo", "limit": 77}
