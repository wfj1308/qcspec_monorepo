from __future__ import annotations

from services.api.domain.execution.triprole_action_execute import (
    execute_triprole_action_flow,
)


def _deps() -> dict[str, object]:
    return {
        "parse_triprole_action_request_fn": lambda **_: {},
        "materialize_parsed_request_fn": lambda **_: {
            "action": "quality.check",
            "input_proof_id": "GP-IN-1",
            "executor_uri": "v://executor/system/",
            "executor_role": "TRIPROLE",
            "executor_did": "did:example:1",
            "override_result": "",
            "offline_packet_id": "",
            "payload": {},
            "credentials_vc_raw": [],
            "signer_metadata_raw": {},
            "body_geo_location_raw": None,
            "body_server_timestamp_raw": None,
            "boq_item_uri_override": "",
            "segment_uri_override": "",
        },
        "prepare_triprole_action_input_fn": lambda **_: {
            "engine": object(),
            "input_row": {"proof_id": "GP-IN-1"},
            "replayed_response": None,
        },
        "resolve_existing_offline_result_fn": lambda **_: None,
        "build_triprole_replayed_response_fn": lambda **_: {},
        "is_leaf_boq_row_fn": lambda _row: True,
        "proof_utxo_engine_cls": lambda _sb: object(),
        "maybe_execute_special_action_fn": lambda **_: None,
        "execute_scan_entry_action_fn": lambda **_: {},
        "execute_gateway_style_action_fn": lambda **_: {},
        "resolve_triprole_transition_runtime_fn": lambda **_: {
            "input_sd": {"seed": 1},
            "project_uri": "v://project/demo",
            "project_id": "p1",
            "owner_uri": "v://owner/demo",
            "segment_uri": "v://segment/1",
            "boq_item_uri": "v://boq/1-1",
            "did_gate": {"ok": True},
            "parent_hash": "h1",
            "now_iso": "2026-01-01T00:00:00Z",
            "anchor": {"spatiotemporal_anchor_hash": "a1"},
            "geo_compliance": {"trust_level": "HIGH"},
            "next_state": {"k": "v"},
            "next_proof_type": "inspection",
            "next_result": "PASS",
            "tx_type": "consume",
            "biometric_check": {"ok": True},
        },
        "validate_transition_fn": lambda *_: None,
        "build_triprole_action_context_fn": lambda **_: {},
        "materialize_action_context_fn": lambda **_: {},
        "dispatch_triprole_transition_fn": lambda **_: {},
        "materialize_transition_fn": lambda **_: {},
        "aggregate_provenance_chain_fn": lambda *_args, **_kwargs: {},
        "resolve_dual_pass_gate_fn": lambda **_: {},
        "normalize_consensus_signatures_fn": lambda _raw: [],
        "validate_consensus_signatures_fn": lambda *_: {"ok": True},
        "verify_biometric_status_fn": lambda **_: {"ok": True},
        "detect_consensus_deviation_fn": lambda **_: {"conflict": False},
        "create_consensus_dispute_fn": lambda **_: {"ok": True},
        "finalize_triprole_action_fn": lambda **_: {"ok": True, "mode": "finalized"},
        "consume_triprole_transition_fn": lambda **_: {},
        "materialize_execution_io_fn": lambda **_: {},
        "run_triprole_postprocess_fn": lambda **_: {},
        "materialize_postprocess_fn": lambda **_: {},
        "build_triprole_action_response_fn": lambda **_: {},
        "update_chain_with_result_fn": lambda **_: {},
        "open_remediation_trip_fn": lambda **_: {},
        "calculate_sovereign_credit_fn": lambda **_: {},
        "sync_to_mirrors_fn": lambda **_: {},
        "build_shadow_packet_fn": lambda **_: {},
        "patch_state_data_fields_fn": lambda **_: {},
    }


def test_execute_triprole_action_flow_returns_replayed_response_early() -> None:
    deps = _deps()
    deps["materialize_parsed_request_fn"] = lambda **_: {
        "action": "quality.check",
        "input_proof_id": "GP-IN-1",
        "executor_uri": "v://executor/system/",
        "executor_role": "TRIPROLE",
        "executor_did": "",
        "override_result": "",
        "offline_packet_id": "off-1",
        "payload": {},
        "credentials_vc_raw": [],
        "signer_metadata_raw": {},
        "body_geo_location_raw": None,
        "body_server_timestamp_raw": None,
        "boq_item_uri_override": "",
        "segment_uri_override": "",
    }
    deps["prepare_triprole_action_input_fn"] = lambda **_: {
        "engine": object(),
        "input_row": None,
        "replayed_response": {"ok": True, "replayed": True},
    }

    out = execute_triprole_action_flow(
        sb=object(),
        body={},
        valid_actions={"quality.check"},
        consensus_required_roles=("contractor", "supervisor", "owner"),
        **deps,  # type: ignore[arg-type]
    )
    assert out == {"ok": True, "replayed": True}


def test_execute_triprole_action_flow_runs_standard_pipeline_and_finalize() -> None:
    deps = _deps()
    captured: dict[str, object] = {}

    def _finalize(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True, "mode": "finalized"}

    deps["finalize_triprole_action_fn"] = _finalize

    out = execute_triprole_action_flow(
        sb=object(),
        body={},
        valid_actions={"quality.check"},
        consensus_required_roles=("contractor", "supervisor", "owner"),
        **deps,  # type: ignore[arg-type]
    )

    assert out == {"ok": True, "mode": "finalized"}
    assert captured["action"] == "quality.check"
    assert captured["input_proof_id"] == "GP-IN-1"
    assert captured["boq_item_uri"] == "v://boq/1-1"
