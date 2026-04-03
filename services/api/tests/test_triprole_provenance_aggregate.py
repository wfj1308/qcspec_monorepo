from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.lineage.triprole_provenance_aggregate import (
    build_provenance_aggregate,
)


def test_build_provenance_aggregate_requires_utxo_id() -> None:
    with pytest.raises(HTTPException) as exc:
        build_provenance_aggregate(
            utxo_id="",
            sb=object(),
            get_chain_fn=lambda *_args, **_kwargs: [],
        )
    assert exc.value.status_code == 400
    assert "utxo_id is required" in str(exc.value.detail)


def test_build_provenance_aggregate_requires_chain_rows() -> None:
    with pytest.raises(HTTPException) as exc:
        build_provenance_aggregate(
            utxo_id="GP-1",
            sb=object(),
            get_chain_fn=lambda *_args, **_kwargs: [],
        )
    assert exc.value.status_code == 404
    assert "proof chain not found" in str(exc.value.detail)


def test_build_provenance_aggregate_builds_expected_payload() -> None:
    chain_rows = [
        {
            "proof_id": "P1",
            "proof_hash": "H1",
            "parent_proof_id": "",
            "parent_hash": "",
            "project_uri": "v://project/demo",
            "segment_uri": "v://segment/1",
            "state_data": {"artifact_uri": "v://artifact/1"},
        },
        {
            "proof_id": "P2",
            "proof_hash": "H2",
            "parent_proof_id": "P1",
            "parent_hash": "H1",
            "project_uri": "v://project/demo",
            "segment_uri": "v://segment/1",
            "state_data": {"artifact_uri": "v://artifact/2"},
        },
    ]
    nodes = [
        {
            "proof_id": "P1",
            "proof_hash": "H1",
            "parent_proof_id": "",
            "parent_hash": "",
            "lifecycle_stage": "INITIAL",
            "trip_action": "quality.check",
            "result": "PASS",
        },
        {
            "proof_id": "P2",
            "proof_hash": "H2",
            "parent_proof_id": "P1",
            "parent_hash": "H1",
            "lifecycle_stage": "INSTALLATION",
            "trip_action": "measure.record",
            "result": "PASS",
        },
    ]

    out = build_provenance_aggregate(
        utxo_id="GP-ROOT",
        sb=object(),
        max_depth=32,
        get_chain_fn=lambda *_args, **_kwargs: chain_rows,
        build_provenance_nodes_fn=lambda _rows: nodes,
        sha256_json_fn=lambda _payload: "TOTAL-HASH",
        gate_lock_fn=lambda _nodes: {"blocked": False},
        resolve_boq_item_uri_fn=lambda _row: "v://boq/1-1",
    )

    assert out["ok"] is True
    assert out["utxo_id"] == "GP-ROOT"
    assert out["root_proof_id"] == "P1"
    assert out["latest_proof_id"] == "P2"
    assert out["project_uri"] == "v://project/demo"
    assert out["segment_uri"] == "v://segment/1"
    assert out["boq_item_uri"] == "v://boq/1-1"
    assert out["artifact_uri"] == "v://artifact/2"
    assert out["chain_depth"] == 2
    assert out["total_proof_hash"] == "TOTAL-HASH"
    assert out["nodes"] == nodes
    assert out["gate"] == {"blocked": False}
