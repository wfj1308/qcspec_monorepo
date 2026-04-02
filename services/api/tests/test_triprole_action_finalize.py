from __future__ import annotations

from services.api.domain.execution.triprole_action_finalize import (
    finalize_triprole_action,
)


def test_finalize_triprole_action_runs_pipeline_and_builds_response() -> None:
    trace: dict[str, object] = {}

    out = finalize_triprole_action(
        sb=object(),
        engine=object(),
        input_row={"proof_id": "GP-IN-1"},
        input_sd={"seed": 1},
        input_proof_id="GP-IN-1",
        action="quality.check",
        payload={"k": "v"},
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        executor_did="did:example:1",
        offline_packet_id="off-1",
        owner_uri="v://owner/demo",
        project_id="p1",
        project_uri="v://project/demo",
        segment_uri="v://segment/1",
        boq_item_uri="v://boq/1-1",
        parent_hash="hash-parent",
        now_iso="2026-01-01T00:00:00Z",
        did_gate={"ok": True},
        anchor={"spatiotemporal_anchor_hash": "a1"},
        geo_compliance={"trust_level": "HIGH"},
        next_proof_type="inspection",
        next_result="PASS",
        tx_type="consume",
        next_state={"phase": "after"},
        biometric_check={"ok": True},
        consume_triprole_transition_fn=lambda **kwargs: (
            trace.__setitem__("consume", kwargs) or {"tx": {"tx_id": "TX-1"}, "output_proof_id": "GP-OUT-1", "output_row": {"proof_id": "GP-OUT-1"}}
        ),
        materialize_execution_io_fn=lambda **kwargs: kwargs["execution_io"],  # type: ignore[index]
        run_triprole_postprocess_fn=lambda **kwargs: (
            trace.__setitem__("postprocess", kwargs)
            or {
                "output_row": {"proof_id": "GP-OUT-1"},
                "quality_chain_writeback": {"ok": True},
                "remediation": {"opened": False},
                "credit_endorsement": {"score": 90},
                "mirror_sync": {"synced": True},
            }
        ),
        materialize_postprocess_fn=lambda **kwargs: kwargs["postprocess"],  # type: ignore[index]
        aggregate_provenance_chain_fn=lambda proof_id, _sb: {"proof_id": proof_id, "ok": True},
        build_triprole_action_response_fn=lambda **kwargs: kwargs,
        update_chain_with_result_fn=lambda **_: {"ok": True},
        open_remediation_trip_fn=lambda **_: {"ok": True},
        calculate_sovereign_credit_fn=lambda **_: {"ok": True},
        sync_to_mirrors_fn=lambda **_: {"ok": True},
        build_shadow_packet_fn=lambda **_: {"ok": True},
        patch_state_data_fields_fn=lambda **_: {"ok": True},
    )

    assert "consume" in trace
    assert "postprocess" in trace
    assert out["output_proof_id"] == "GP-OUT-1"
    assert out["credit_endorsement"]["score"] == 90
    assert out["provenance"]["proof_id"] == "GP-OUT-1"
    assert out["tx"]["tx_id"] == "TX-1"


def test_finalize_triprole_action_tolerates_empty_materialized_sections() -> None:
    out = finalize_triprole_action(
        sb=object(),
        engine=object(),
        input_row={},
        input_sd={},
        input_proof_id="GP-IN-2",
        action="measure.record",
        payload={},
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        executor_did="did:example:2",
        offline_packet_id="",
        owner_uri="",
        project_id=None,
        project_uri="",
        segment_uri="",
        boq_item_uri="",
        parent_hash="",
        now_iso="",
        did_gate={},
        anchor={},
        geo_compliance={},
        next_proof_type="approval",
        next_result="PASS",
        tx_type="consume",
        next_state={},
        biometric_check={},
        consume_triprole_transition_fn=lambda **_: {},
        materialize_execution_io_fn=lambda **_: {},
        run_triprole_postprocess_fn=lambda **_: {},
        materialize_postprocess_fn=lambda **_: {},
        aggregate_provenance_chain_fn=lambda proof_id, _sb: {"proof_id": proof_id},
        build_triprole_action_response_fn=lambda **kwargs: kwargs,
        update_chain_with_result_fn=lambda **_: {},
        open_remediation_trip_fn=lambda **_: {},
        calculate_sovereign_credit_fn=lambda **_: {},
        sync_to_mirrors_fn=lambda **_: {},
        build_shadow_packet_fn=lambda **_: {},
        patch_state_data_fields_fn=lambda **_: {},
    )
    assert out["output_proof_id"] == ""
    assert out["tx"] == {}
    assert out["provenance"]["proof_id"] == ""
