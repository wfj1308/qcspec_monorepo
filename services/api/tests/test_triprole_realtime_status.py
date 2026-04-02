from __future__ import annotations

from services.api.domain.execution.triprole_realtime_status import build_boq_realtime_status


def test_build_boq_realtime_status_aggregates_and_sorts_items() -> None:
    rows = [
        {
            "proof_id": "g2",
            "created_at": "2026-01-01T00:00:00Z",
            "proof_type": "zero_ledger",
            "result": "PASS",
            "state_data": {
                "boq_item_uri": "v://boq/10-1",
                "is_leaf": True,
                "item_name": "Item 10",
                "unit": "m3",
                "design_quantity": 5,
                "unit_price": 2.0,
            },
        },
        {
            "proof_id": "v2",
            "created_at": "2026-01-01T03:00:00Z",
            "proof_type": "triprole",
            "result": "PASS",
            "spent": False,
            "state_data": {
                "boq_item_uri": "v://boq/10-1",
                "is_leaf": True,
                "lifecycle_stage": "VARIATION",
            },
        },
        {
            "proof_id": "s2",
            "created_at": "2026-01-01T04:00:00Z",
            "proof_type": "triprole",
            "result": "PASS",
            "state_data": {
                "boq_item_uri": "v://boq/10-1",
                "is_leaf": True,
                "lifecycle_stage": "SETTLEMENT",
                "settlement": {},
            },
        },
        {
            "proof_id": "g1",
            "created_at": "2026-01-02T00:00:00Z",
            "proof_type": "zero_ledger",
            "result": "PASS",
            "state_data": {
                "boq_item_uri": "v://boq/2-1",
                "is_leaf": True,
                "item_name": "Item 2",
                "unit": "m",
                "design_quantity": 10,
                "approved_quantity": 8,
                "contract_quantity": 9,
                "unit_price": 5.0,
            },
        },
        {
            "proof_id": "s1",
            "created_at": "2026-01-02T01:00:00Z",
            "proof_type": "triprole",
            "result": "PASS",
            "state_data": {
                "boq_item_uri": "v://boq/2-1",
                "is_leaf": True,
                "lifecycle_stage": "SETTLEMENT",
                "settlement": {"settled_quantity": 4},
            },
        },
        {
            "proof_id": "i1",
            "created_at": "2026-01-02T02:00:00Z",
            "proof_type": "triprole",
            "result": "PASS",
            "spent": False,
            "state_data": {
                "boq_item_uri": "v://boq/2-1",
                "is_leaf": True,
                "lifecycle_stage": "INSTALLATION",
                "measurement": {"quantity": 2},
            },
        },
    ]

    status = build_boq_realtime_status(
        rows=rows,
        project_uri="v://project/demo",
        aggregate_provenance_chain_fn=lambda utxo_id: {"gate": {"blocked": utxo_id == "v2", "reason": "locked"}},
    )

    assert status["ok"] is True
    assert status["project_uri"] == "v://project/demo"

    items = status["items"]
    assert [item["item_no"] for item in items] == ["2-1", "10-1"]

    first = items[0]
    assert first["boq_item_uri"] == "v://boq/2-1"
    assert first["design_quantity"] == 9.0
    assert first["approved_quantity"] == 8.0
    assert first["contract_quantity"] == 9.0
    assert first["design_total"] == 50.0
    assert first["contract_total"] == 45.0
    assert first["settled_quantity"] == 4.0
    assert first["consumed_quantity"] == 2.0
    assert first["remaining_quantity"] == 5.0
    assert first["consumption_percent"] == 50.0
    assert first["settlement_count"] == 1
    assert first["latest_settlement_proof_id"] == "s1"
    assert first["sign_candidate_proof_id"] == "i1"
    assert first["sign_ready"] is True
    assert first["sign_block_reason"] == ""
    assert first["proof_chain_view"] == "/v1/proof/docfinal/context?boq_item_uri=v://boq/2-1"

    second = items[1]
    assert second["boq_item_uri"] == "v://boq/10-1"
    assert second["settled_quantity"] == 5.0
    assert second["sign_candidate_proof_id"] == "v2"
    assert second["sign_ready"] is False
    assert second["sign_block_reason"] == "gate_locked:locked"

    summary = status["summary"]
    assert summary["boq_item_count"] == 2
    assert summary["design_total"] == 14.0
    assert summary["approved_total"] == 8.0
    assert summary["settled_total"] == 9.0
    assert summary["consumed_total"] == 2.0
    assert summary["progress_percent"] == 100.0


def test_build_boq_realtime_status_filters_invalid_rows_and_handles_gate_exception() -> None:
    rows = [
        "not-a-row",
        {
            "proof_id": "ignore-nonleaf",
            "state_data": {"boq_item_uri": "v://boq/x", "is_leaf": False},
        },
        {
            "proof_id": "ignore-bad-uri",
            "state_data": {"boq_item_uri": "boq/x", "is_leaf": True},
        },
        {
            "proof_id": "g1",
            "created_at": "2026-01-01T00:00:00Z",
            "proof_type": "zero_ledger",
            "result": "PASS",
            "state_data": {
                "boq_item_uri": "v://boq/1-1",
                "is_leaf": True,
                "design_quantity": 3,
            },
        },
        {
            "proof_id": "i1",
            "created_at": "2026-01-01T01:00:00Z",
            "proof_type": "triprole",
            "result": "PASS",
            "spent": False,
            "state_data": {
                "boq_item_uri": "v://boq/1-1",
                "is_leaf": True,
                "lifecycle_stage": "INSTALLATION",
                "measurement": {"quantity": 1.5},
            },
        },
    ]

    status = build_boq_realtime_status(
        rows=rows,
        project_uri="v://project/demo",
        aggregate_provenance_chain_fn=lambda _utxo_id: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    assert status["summary"]["boq_item_count"] == 1
    item = status["items"][0]
    assert item["boq_item_uri"] == "v://boq/1-1"
    assert item["sign_ready"] is False
    assert item["sign_block_reason"] == "gate_check_failed:RuntimeError"
