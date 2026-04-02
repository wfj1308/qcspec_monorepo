from __future__ import annotations

from services.api.domain.execution.triprole_full_lineage import build_full_lineage


def test_build_full_lineage_filters_by_project_and_deduplicates() -> None:
    rows = [
        {
            "proof_id": "P1",
            "project_uri": "v://project/demo",
            "created_at": "2026-01-01T00:00:00Z",
            "state_data": {
                "spatiotemporal_anchor_hash": "A1",
                "geo_location": {"lat": 1},
                "server_timestamp_proof": {"ts": "1"},
                "trip_action": "quality.check",
                "consensus": {
                    "signatures": [{"signature_hash": "H1", "role": "owner"}],
                },
            },
            "norms": ["v://norm/a"],
            "evidence": [{"proof_id": "P1", "hash": "E2"}],
            "qc": {"created_at": "2026-01-02T00:00:00Z", "result": "PASS"},
        },
        {
            "proof_id": "P2",
            "project_uri": "v://project/demo",
            "created_at": "2026-01-03T00:00:00Z",
            "state_data": {
                "spatiotemporal_anchor_hash": "A1",
                "geo_location": {"lat": 2},
                "server_timestamp_proof": {"ts": "2"},
                "trip_action": "measure.record",
                "consensus": {
                    "signatures": [
                        {"signature_hash": "H1", "role": "owner"},
                        {"signature_hash": "H2", "role": "supervisor"},
                    ],
                },
            },
            "norms": ["v://norm/b"],
            "evidence": [{"proof_id": "P2", "hash": "E1"}],
            "qc": {"created_at": "2026-01-01T00:00:00Z", "result": "PASS"},
        },
        {
            "proof_id": "P3",
            "project_uri": "v://project/other",
            "created_at": "2026-01-04T00:00:00Z",
            "state_data": {},
            "norms": ["v://norm/other"],
            "evidence": [{"proof_id": "P3", "hash": "EX"}],
            "qc": {"created_at": "2026-01-04T00:00:00Z", "result": "FAIL"},
        },
    ]

    out = build_full_lineage(
        utxo_id="GP-1",
        sb=object(),
        max_depth=64,
        aggregate_provenance_chain_fn=lambda **_: {
            "ok": True,
            "utxo_id": "GP-1",
            "boq_item_uri": "v://boq/1-1",
            "project_uri": "v://project/demo",
        },
        get_proof_chain_fn=lambda _boq_uri, _sb: rows,
        get_chain_fn=lambda _utxo, max_depth: [],
        collect_norm_refs_from_row_fn=lambda row: list(row.get("norms") or []),
        collect_evidence_hashes_from_row_fn=lambda row: list(row.get("evidence") or []),
        extract_qc_conclusion_fn=lambda row: dict(row.get("qc") or {}),
    )

    assert out["norm_refs"] == ["v://norm/a", "v://norm/b"]
    assert out["evidence_hashes"] == [
        {"proof_id": "P1", "hash": "E2"},
        {"proof_id": "P2", "hash": "E1"},
    ]
    assert [x["created_at"] for x in out["qc_conclusions"]] == [
        "2026-01-01T00:00:00Z",
        "2026-01-02T00:00:00Z",
    ]
    assert [x["signature_hash"] for x in out["consensus_signatures"]] == ["H1", "H2"]
    assert len(out["spatiotemporal_anchors"]) == 1
    assert out["spatiotemporal_anchors"][0]["spatiotemporal_anchor_hash"] == "A1"


def test_build_full_lineage_falls_back_to_utxo_chain_when_proof_chain_empty() -> None:
    calls = {"proof_chain": 0, "utxo_chain": 0}

    out = build_full_lineage(
        utxo_id="GP-2",
        sb=object(),
        max_depth=32,
        aggregate_provenance_chain_fn=lambda **_: {
            "ok": True,
            "utxo_id": "GP-2",
            "boq_item_uri": "v://boq/2-1",
            "project_uri": "v://project/demo",
        },
        get_proof_chain_fn=lambda _boq_uri, _sb: (calls.__setitem__("proof_chain", calls["proof_chain"] + 1) or []),
        get_chain_fn=lambda _utxo, max_depth: (
            calls.__setitem__("utxo_chain", calls["utxo_chain"] + 1)
            or [
                {
                    "proof_id": "PX",
                    "project_uri": "v://project/demo",
                    "created_at": "2026-01-01T00:00:00Z",
                    "state_data": {},
                }
            ]
        ),
    )

    assert calls["proof_chain"] == 1
    assert calls["utxo_chain"] == 1
    assert out["utxo_id"] == "GP-2"
    assert out["norm_refs"] == []
    assert out["consensus_signatures"] == []
