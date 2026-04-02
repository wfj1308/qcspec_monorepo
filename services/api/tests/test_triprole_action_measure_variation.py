from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.triprole_action_measure_variation import (
    apply_measure_record_transition,
    apply_variation_record_transition,
)


def test_apply_measure_record_transition_sets_state_and_sensor_fingerprint() -> None:
    out = apply_measure_record_transition(
        input_proof_id="GP-1",
        payload={
            "value": 12.3,
            "sensor_hardware": {"device_id": "d1", "firmware": "v1"},
        },
        segment_uri="v://segment/1",
        boq_item_uri="v://boq/1-1",
        geo_compliance={"outside": False, "warning": ""},
        next_state={},
    )
    assert out["next_proof_type"] == "approval"
    state = out["next_state"]
    assert state["lifecycle_stage"] == "INSTALLATION"
    assert state["trust_level"] == "HIGH"
    assert state["measurement_hash"]
    assert state["sensor_hardware"]["device_id"] == "d1"
    assert state["sensor_hardware_fingerprint"]


def test_apply_measure_record_transition_blocks_strict_geofence() -> None:
    with pytest.raises(HTTPException) as exc:
        apply_measure_record_transition(
            input_proof_id="GP-1",
            payload={},
            segment_uri="v://segment/1",
            boq_item_uri="v://boq/1-1",
            geo_compliance={"outside": True, "strict_mode": True, "warning": "outside"},
            next_state={},
        )
    assert exc.value.status_code == 409
    assert "geo-fence violation" in str(exc.value.detail)


def test_apply_variation_record_transition_merges_delta_ledger() -> None:
    out = apply_variation_record_transition(
        input_row={"state_data": {"ledger": {"current_balance": 100}}},
        input_proof_id="GP-1",
        payload={"reason": "delta", "delta_amount": 2},
        override_result="",
        now_iso="2026-01-01T00:00:00Z",
        executor_uri="v://executor/system/",
        next_state={},
        extract_variation_delta_amount_fn=lambda _payload: 2.0,
        build_variation_compensates_fn=lambda _payload, _pid: ["GP-1"],
        compute_delta_merge_fn=lambda **_: {
            "initial_balance": 100.0,
            "delta_total_after": 2.0,
            "merged_total_after": 102.0,
            "transferred_total": 0.0,
            "previous_balance": 100.0,
            "balance_after": 102.0,
            "delta_amount": 2.0,
            "merged_total_before": 100.0,
        },
    )
    assert out["next_proof_type"] == "archive"
    assert out["next_result"] == "PASS"
    state = out["next_state"]
    assert state["lifecycle_stage"] == "VARIATION"
    assert state["variation"]["delta_amount"] == 2.0
    assert state["ledger"]["current_balance"] == 102.0
    assert state["available_quantity"] == 102.0
    assert state["delta_utxo"]["merged_total_after"] == 102.0
