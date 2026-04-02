from __future__ import annotations

from services.api.domain.execution.triprole_action_transition_runtime import (
    resolve_triprole_transition_runtime,
)


def test_resolve_triprole_transition_runtime_builds_expected_bundle() -> None:
    calls: dict[str, object] = {}

    def _validate(action: str, input_row: dict[str, object]) -> None:
        calls["validated"] = (action, input_row.get("proof_id"))

    def _build_context(**_: object) -> dict[str, object]:
        return {"ctx": True}

    def _materialize_context(**_: object) -> dict[str, object]:
        return {
            "input_sd": {"seed": 1},
            "project_uri": "v://project/demo",
            "project_id": "p1",
            "owner_uri": "v://owner/demo",
            "segment_uri": "v://segment/1",
            "boq_item_uri": "v://boq/1-1",
            "did_gate": {"ok": True},
            "gate_binding": {"linked_gate_id": "g1"},
            "parent_hash": "hash-parent",
            "now_iso": "2026-01-01T00:00:00Z",
            "anchor": {"spatiotemporal_anchor_hash": "a1"},
            "normalized_signer_metadata": {"signers": []},
            "geo_compliance": {"trust_level": "HIGH"},
            "next_state": {"phase": "before"},
        }

    def _dispatch(**kwargs: object) -> dict[str, object]:
        calls["dispatched_action"] = kwargs.get("action")
        return {
            "next_proof_type": "payment",
            "next_result": "pass",
            "tx_type": "settle",
            "next_state": {"phase": "after"},
            "biometric_check": {"ok": True},
        }

    out = resolve_triprole_transition_runtime(
        sb=object(),
        body={},
        input_row={"proof_id": "GP-IN-1"},
        action="settlement.confirm",
        input_proof_id="GP-IN-1",
        executor_uri="v://executor/system/",
        executor_did="did:example:1",
        override_result="",
        offline_packet_id="off-1",
        payload={"result": "PASS"},
        credentials_vc_raw=[],
        signer_metadata_raw={},
        body_geo_location_raw=None,
        body_server_timestamp_raw=None,
        segment_uri_override="",
        boq_item_uri_override="",
        consensus_required_roles=("contractor", "supervisor", "owner"),
        validate_transition_fn=_validate,
        build_triprole_action_context_fn=_build_context,
        materialize_action_context_fn=_materialize_context,
        dispatch_triprole_transition_fn=_dispatch,
        materialize_transition_fn=lambda **kwargs: dict(kwargs["transition"]),  # type: ignore[index]
        aggregate_provenance_chain_fn=lambda *_: {},
        resolve_dual_pass_gate_fn=lambda **_: {},
        normalize_consensus_signatures_fn=lambda _raw: [],
        validate_consensus_signatures_fn=lambda *_: {"ok": True},
        verify_biometric_status_fn=lambda **_: {"ok": True},
        detect_consensus_deviation_fn=lambda **_: {"conflict": False},
        create_consensus_dispute_fn=lambda **_: {"ok": True},
    )

    assert calls["validated"] == ("settlement.confirm", "GP-IN-1")
    assert calls["dispatched_action"] == "settlement.confirm"
    assert out["project_uri"] == "v://project/demo"
    assert out["boq_item_uri"] == "v://boq/1-1"
    assert out["next_proof_type"] == "payment"
    assert out["next_result"] == "PASS"
    assert out["tx_type"] == "settle"
    assert out["next_state"] == {"phase": "after"}
    assert out["biometric_check"] == {"ok": True}


def test_resolve_triprole_transition_runtime_uses_transition_defaults() -> None:
    out = resolve_triprole_transition_runtime(
        sb=object(),
        body={},
        input_row={},
        action="quality.check",
        input_proof_id="GP-IN-2",
        executor_uri="v://executor/system/",
        executor_did="did:example:2",
        override_result="",
        offline_packet_id="",
        payload={},
        credentials_vc_raw=[],
        signer_metadata_raw={},
        body_geo_location_raw=None,
        body_server_timestamp_raw=None,
        segment_uri_override="",
        boq_item_uri_override="",
        consensus_required_roles=("contractor", "supervisor", "owner"),
        validate_transition_fn=lambda *_: None,
        build_triprole_action_context_fn=lambda **_: {},
        materialize_action_context_fn=lambda **_: {
            "input_sd": {},
            "project_uri": "",
            "project_id": None,
            "owner_uri": "",
            "segment_uri": "",
            "boq_item_uri": "",
            "did_gate": {},
            "gate_binding": {},
            "parent_hash": "",
            "now_iso": "",
            "anchor": {},
            "normalized_signer_metadata": {},
            "geo_compliance": {},
            "next_state": {},
        },
        dispatch_triprole_transition_fn=lambda **_: {},
        materialize_transition_fn=lambda **_: {},
        aggregate_provenance_chain_fn=lambda *_: {},
        resolve_dual_pass_gate_fn=lambda **_: {},
        normalize_consensus_signatures_fn=lambda _raw: [],
        validate_consensus_signatures_fn=lambda *_: {"ok": True},
        verify_biometric_status_fn=lambda **_: {"ok": True},
        detect_consensus_deviation_fn=lambda **_: {"conflict": False},
        create_consensus_dispute_fn=lambda **_: {"ok": True},
    )
    assert out["next_proof_type"] == "inspection"
    assert out["next_result"] == "PASS"
    assert out["tx_type"] == "consume"
