from __future__ import annotations

from services.api.domain.execution.triprole_action_postprocess import run_triprole_postprocess


def test_run_triprole_postprocess_quality_path_with_remediation() -> None:
    out = run_triprole_postprocess(
        sb=object(),
        action="quality.check",
        payload={
            "remediation_notice": "n1",
            "remediation_due_date": "2026-01-02",
            "remediation_assignees": ["did:example:a"],
        },
        output_proof_id="GP-OUT-1",
        output_row={"result": "FAIL", "project_id": "p1", "project_uri": "v://project/demo"},
        next_state={
            "qc_gate_result": {"gate_id": "g1"},
            "result_source": "manual",
            "spec_uri": "v://norm/spec/1",
            "spec_snapshot": "snap",
            "quality_hash": "qh1",
            "linked_gate_id": "g1",
            "linked_gate_ids": ["g1"],
            "linked_gate_rules": ["r1"],
        },
        input_proof_id="GP-IN-1",
        next_result="FAIL",
        boq_item_uri="v://boq/1-1",
        now_iso="2026-01-01T00:00:00Z",
        executor_uri="v://executor/system/",
        project_uri="v://project/demo",
        executor_did="did:example:1",
        did_gate={"ok": True},
        tx={"tx_id": "t1"},
        update_chain_with_result_fn=lambda **_: {"state_data": {"w": 1}},
        open_remediation_trip_fn=lambda **_: {"ok": True, "proof_id": "GP-RM-1"},
        calculate_sovereign_credit_fn=lambda **_: {"score": 88},
        sync_to_mirrors_fn=lambda **_: {"attempted": True, "synced": True},
        build_shadow_packet_fn=lambda **_: {"pkt": 1},
        patch_state_data_fields_fn=lambda **_: {"patched": True},
    )

    assert out["quality_chain_writeback"]["state_data"]["w"] == 1
    assert out["remediation"]["ok"] is True
    assert out["credit_endorsement"]["score"] == 88
    assert out["mirror_sync"]["synced"] is True
    assert out["output_row"]["state_data"]["patched"] is True


def test_run_triprole_postprocess_non_quality_skips_gate_writeback() -> None:
    out = run_triprole_postprocess(
        sb=object(),
        action="measure.record",
        payload={},
        output_proof_id="GP-OUT-2",
        output_row={"result": "PASS", "project_id": "p1", "project_uri": "v://project/demo"},
        next_state={},
        input_proof_id="GP-IN-2",
        next_result="PASS",
        boq_item_uri="v://boq/1-1",
        now_iso="2026-01-01T00:00:00Z",
        executor_uri="v://executor/system/",
        project_uri="v://project/demo",
        executor_did="did:example:2",
        did_gate={"ok": True},
        tx={"tx_id": "t2"},
        update_chain_with_result_fn=lambda **_: (_ for _ in ()).throw(RuntimeError("should-not-call")),
        open_remediation_trip_fn=lambda **_: {"ok": False},
        calculate_sovereign_credit_fn=lambda **_: {"score": 91},
        sync_to_mirrors_fn=lambda **_: {"attempted": True, "synced": False},
        build_shadow_packet_fn=lambda **_: {"pkt": 2},
        patch_state_data_fields_fn=lambda **_: {},
    )

    assert out["quality_chain_writeback"] == {}
    assert out["remediation"] == {}
    assert out["credit_endorsement"]["score"] == 91
