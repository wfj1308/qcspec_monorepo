from __future__ import annotations

from services.api.domain.execution.triprole_action_dispatch import dispatch_triprole_transition


def _base_kwargs() -> dict[str, object]:
    return {
        "sb": object(),
        "body": {},
        "input_row": {},
        "input_sd": {},
        "input_proof_id": "GP-IN-1",
        "payload": {"result": "PASS"},
        "project_uri": "v://project/demo",
        "boq_item_uri": "v://boq/1-1",
        "segment_uri": "v://segment/1",
        "executor_uri": "v://executor/system/",
        "override_result": "",
        "now_iso": "2026-01-01T00:00:00Z",
        "next_state": {"seed": 1},
        "geo_compliance": {},
        "gate_binding": {},
        "signer_metadata_raw": {},
        "normalized_signer_metadata": {},
        "consensus_required_roles": ("contractor", "supervisor", "owner"),
        "aggregate_provenance_chain_fn": lambda *_: {},
        "resolve_dual_pass_gate_fn": lambda **_: {},
        "normalize_consensus_signatures_fn": lambda _raw: [],
        "validate_consensus_signatures_fn": lambda *_: {"ok": True},
        "verify_biometric_status_fn": lambda **_: {"ok": True},
        "detect_consensus_deviation_fn": lambda **_: {"conflict": False},
        "create_consensus_dispute_fn": lambda **_: {"ok": True},
    }


def test_dispatch_triprole_transition_quality_branch() -> None:
    out = dispatch_triprole_transition(
        action="quality.check",
        **_base_kwargs(),
        apply_quality_check_transition_fn=lambda **_: {
            "next_result": "FAIL",
            "next_state": {"quality": True},
        },
    )
    assert out["next_proof_type"] == "inspection"
    assert out["next_result"] == "FAIL"
    assert out["next_state"] == {"quality": True}
    assert out["tx_type"] == "consume"


def test_dispatch_triprole_transition_settlement_branch() -> None:
    out = dispatch_triprole_transition(
        action="settlement.confirm",
        **_base_kwargs(),
        apply_settlement_confirm_transition_fn=lambda **_: {
            "next_proof_type": "payment",
            "tx_type": "settle",
            "next_state": {"settled": True},
            "biometric_check": {"ok": True},
        },
    )
    assert out["next_proof_type"] == "payment"
    assert out["tx_type"] == "settle"
    assert out["next_state"] == {"settled": True}
    assert out["biometric_check"]["ok"] is True


def test_dispatch_triprole_transition_fallback_for_unknown_action() -> None:
    out = dispatch_triprole_transition(
        action="noop",
        **_base_kwargs(),
    )
    assert out["next_proof_type"] == "inspection"
    assert out["next_result"] == "PASS"
    assert out["next_state"] == {"seed": 1}
