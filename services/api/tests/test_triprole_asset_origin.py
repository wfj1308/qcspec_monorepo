from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.triprole_asset_origin import trace_asset_origin


def test_trace_asset_origin_requires_target() -> None:
    with pytest.raises(HTTPException) as exc:
        trace_asset_origin(
            sb=object(),
            get_by_id_fn=lambda _pid: None,
            get_chain_fn=lambda _pid, _depth: [],
            get_proof_chain_fn=lambda _uri, _sb, _depth: [],
            resolve_latest_boq_row_fn=lambda _sb, _boq, _project: None,
            get_boq_realtime_status_fn=lambda _sb, _project, _limit: {},
        )
    assert exc.value.status_code == 400


def test_trace_asset_origin_computes_variation_and_settlement_summary() -> None:
    rows = [
        {
            "proof_id": "s1",
            "proof_hash": "hs1",
            "proof_type": "triprole",
            "result": "PASS",
            "created_at": "2026-01-01T03:00:00Z",
            "project_uri": "v://project/demo",
            "state_data": {
                "boq_item_uri": "v://boq/1-1",
                "lifecycle_stage": "SETTLEMENT",
                "settlement": {"settled_quantity": 11},
            },
        },
        {
            "proof_id": "g1",
            "proof_hash": "hg1",
            "proof_type": "zero_ledger",
            "result": "PASS",
            "created_at": "2026-01-01T01:00:00Z",
            "project_uri": "v://project/demo",
            "state_data": {
                "boq_item_uri": "v://boq/1-1",
                "contract_quantity": 10,
            },
        },
        {
            "proof_id": "v1",
            "proof_hash": "hv1",
            "proof_type": "triprole",
            "result": "PASS",
            "created_at": "2026-01-01T02:00:00Z",
            "project_uri": "v://project/demo",
            "state_data": {
                "boq_item_uri": "v://boq/1-1",
                "lifecycle_stage": "VARIATION",
                "trip_action": "variation.record",
                "variation": {
                    "delta_amount": 2,
                    "design_change_no": "DC-001",
                    "design_change_date": "2026-01-01",
                },
            },
        },
    ]

    payload = trace_asset_origin(
        sb=object(),
        utxo_id="s1",
        get_by_id_fn=lambda _pid: rows[0],
        get_chain_fn=lambda _pid, _depth: [],
        get_proof_chain_fn=lambda _uri, _sb, _depth: rows,
        resolve_latest_boq_row_fn=lambda _sb, _boq, _project: None,
        get_boq_realtime_status_fn=lambda _sb, _project, _limit: {},
    )

    assert payload["ok"] is True
    assert payload["boq_item_uri"] == "v://boq/1-1"
    assert payload["genesis_utxo_id"] == "g1"
    assert payload["contract_quantity"] == 10.0
    assert payload["measured_quantity"] == 11.0
    assert payload["delta_vs_contract"] == 1.0
    assert payload["variation_total_delta"] == 2.0
    assert payload["unexplained_delta"] == -1.0
    assert len(payload["variation_sources"]) == 1
    assert payload["variation_sources"][0]["reference_no"] == "DC-001"
    assert len(payload["lineage_path"]) == 3
    assert "本表实测量为 11" in payload["statement"]
    assert payload["lineage_proof_hash"]


def test_trace_asset_origin_falls_back_to_status_snapshot() -> None:
    latest = {
        "proof_id": "p1",
        "project_uri": "v://project/demo",
        "state_data": {
            "boq_item_uri": "v://boq/2-1",
            "lifecycle_stage": "INSTALLATION",
        },
        "created_at": "2026-01-01T00:00:00Z",
        "result": "PASS",
    }
    chain_rows = [
        {
            "proof_id": "p1",
            "proof_hash": "hp1",
            "proof_type": "triprole",
            "result": "PASS",
            "created_at": "2026-01-01T00:00:00Z",
            "project_uri": "v://project/demo",
            "state_data": {
                "boq_item_uri": "v://boq/2-1",
                "lifecycle_stage": "INSTALLATION",
                "measurement": {},
            },
        }
    ]

    payload = trace_asset_origin(
        sb=object(),
        utxo_id="p1",
        get_by_id_fn=lambda _pid: latest,
        get_chain_fn=lambda _pid, _depth: chain_rows,
        get_proof_chain_fn=lambda _uri, _sb, _depth: [],
        resolve_latest_boq_row_fn=lambda _sb, _boq, _project: None,
        get_boq_realtime_status_fn=lambda _sb, _project, _limit: {
            "items": [
                {
                    "boq_item_uri": "v://boq/2-1",
                    "settled_quantity": 7,
                }
            ]
        },
    )

    assert payload["boq_item_uri"] == "v://boq/2-1"
    assert payload["contract_quantity"] == 0.0
    assert payload["measured_quantity"] == 7.0
    assert payload["delta_vs_contract"] == 7.0
