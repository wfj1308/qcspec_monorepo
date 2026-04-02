from __future__ import annotations

from services.api.domain.execution.triprole_action_dispute import apply_dispute_resolve_transition


def test_apply_dispute_resolve_transition_pass() -> None:
    out = apply_dispute_resolve_transition(
        payload={"note": "resolved"},
        override_result="",
        now_iso="2026-01-01T00:00:00Z",
        next_state={"existing": "v1"},
    )
    assert out["next_proof_type"] == "dispute_resolution"
    assert out["next_result"] == "PASS"
    state = out["next_state"]
    assert state["existing"] == "v1"
    assert state["lifecycle_stage"] == "DISPUTE_RESOLUTION"
    assert state["status"] == "RESOLVED"
    assert state["resolution"]["resolved_at"] == "2026-01-01T00:00:00Z"
    assert state["resolution_hash"]


def test_apply_dispute_resolve_transition_override_fail() -> None:
    out = apply_dispute_resolve_transition(
        payload={},
        override_result="FAIL",
        now_iso="2026-01-01T00:00:00Z",
        next_state={},
    )
    assert out["next_result"] == "FAIL"
    assert out["next_state"]["status"] == "REJECTED"
