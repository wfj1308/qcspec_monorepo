from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.actions.triprole_action_quality import apply_quality_check_transition


def test_apply_quality_check_transition_rejects_locked_spec_mismatch() -> None:
    with pytest.raises(HTTPException) as exc:
        apply_quality_check_transition(
            sb=object(),
            input_proof_id="GP-1",
            payload={"spec_uri": "v://norm/spec/B"},
            input_sd={"spec_uri": "v://norm/spec/A"},
            gate_binding={
                "gate_template_lock": True,
                "linked_spec_uri": "v://norm/spec/A",
            },
            boq_item_uri="v://boq/1-1",
            segment_uri="v://segment/1",
            override_result="",
            now_iso="2026-01-01T00:00:00Z",
            next_state={},
            resolve_dynamic_threshold_fn=lambda **_: {},
            evaluate_with_threshold_pack_fn=lambda **_: {},
            resolve_normpeg_eval_fn=lambda **_: {},
            extract_values_fn=lambda _payload: [],
        )
    assert exc.value.status_code == 409
    assert "spec_template_locked" in str(exc.value.detail)


def test_apply_quality_check_transition_dynamic_threshold_path() -> None:
    out = apply_quality_check_transition(
        sb=object(),
        input_proof_id="GP-1",
        payload={
            "design": 10,
            "values": [10.1],
            "component_type": "beam",
            "stake": "K1+000",
        },
        input_sd={"item_no": "1-1"},
        gate_binding={
            "linked_gate_id": "gate-1",
            "linked_gate_ids": ["gate-1"],
            "linked_gate_rules": ["r1"],
            "linked_spec_uri": "v://norm/spec/1",
            "spec_dict_key": "k1",
            "spec_item": "i1",
            "gate_template_lock": False,
            "gate_binding_hash": "gbh1",
        },
        boq_item_uri="v://boq/1-1",
        segment_uri="v://segment/1",
        override_result="",
        now_iso="2026-01-01T00:00:00Z",
        next_state={},
        resolve_dynamic_threshold_fn=lambda **_: {
            "found": True,
            "effective_spec_uri": "v://norm/spec/1",
            "spec_excerpt": "excerpt",
            "context_key": "beam@K1+000",
        },
        evaluate_with_threshold_pack_fn=lambda **_: {
            "matched": True,
            "result": "PASS",
            "deviation_percent": 1.1,
            "values_for_eval": [10.1],
            "design_value": 10.0,
            "lower": 9.5,
            "upper": 10.5,
            "center": 10.0,
            "tolerance": 0.5,
        },
        resolve_normpeg_eval_fn=lambda **_: {},
        extract_values_fn=lambda _payload: [10.1],
    )

    assert out["next_result"] == "PASS"
    state = out["next_state"]
    assert state["lifecycle_stage"] == "ENTRY"
    assert state["result_source"] == "normpeg_dynamic"
    assert state["spec_uri"] == "v://norm/spec/1"
    assert state["qc_gate_status"] == "PASS"
    assert state["qc_gate_result"]["context_key"] == "beam@K1+000"
    assert state["quality_hash"]
