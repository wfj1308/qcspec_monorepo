from __future__ import annotations

from services.api.domain.execution.actions.triprole_action_runtime import (
    materialize_action_context,
    materialize_execution_io,
    materialize_parsed_request,
    materialize_postprocess,
    materialize_transition,
)


def test_materialize_action_context_patches_offline_packet_and_defaults_owner() -> None:
    out = materialize_action_context(
        action_context={
            "input_sd": {"seed": 1},
            "project_uri": "v://project/demo",
            "project_id": "p1",
            "owner_uri": "",
            "segment_uri": "v://segment/1",
            "boq_item_uri": "v://boq/1-1",
            "did_gate": {"ok": True},
            "gate_binding": {"linked_gate_id": "g1"},
            "parent_hash": "h1",
            "now_iso": "2026-01-01T00:00:00Z",
            "anchor": {"spatiotemporal_anchor_hash": "a1"},
            "normalized_signer_metadata": {"signers": []},
            "geo_compliance": {"trust_level": "HIGH"},
            "next_state": {"k": "v"},
        },
        executor_uri="v://executor/system/",
        offline_packet_id="off-1",
    )
    assert out["owner_uri"] == "v://executor/system/"
    assert out["next_state"]["offline_packet_id"] == "off-1"
    assert out["did_gate"]["ok"] is True


def test_materialize_transition_normalizes_defaults() -> None:
    out = materialize_transition(
        transition={
            "next_result": "pass",
            "next_state": {"x": 1},
        },
        payload={},
    )
    assert out["next_proof_type"] == "inspection"
    assert out["next_result"] == "PASS"
    assert out["tx_type"] == "consume"
    assert out["next_state"] == {"x": 1}
    assert out["biometric_check"] == {}


def test_materialize_parsed_request_applies_role_default() -> None:
    out = materialize_parsed_request(
        parsed_request={
            "action": "quality.check",
            "input_proof_id": "GP-IN-1",
            "executor_uri": "v://executor/system/",
            "executor_role": "",
            "executor_did": "did:example:1",
            "override_result": "",
            "offline_packet_id": "off-1",
            "payload": {"a": 1},
            "credentials_vc_raw": [{"id": "vc1"}],
            "signer_metadata_raw": {"signers": []},
            "body_geo_location_raw": {"lat": 1},
            "body_server_timestamp_raw": {"ts": "1"},
            "boq_item_uri_override": "v://boq/1-1",
            "segment_uri_override": "v://segment/1",
        }
    )
    assert out["executor_role"] == "TRIPROLE"
    assert out["payload"] == {"a": 1}
    assert out["offline_packet_id"] == "off-1"


def test_materialize_execution_io_reads_defaults() -> None:
    out = materialize_execution_io(
        execution_io={
            "tx": {"tx_id": "TX-1"},
            "output_proof_id": "GP-OUT-1",
            "output_row": {"proof_id": "GP-OUT-1"},
        }
    )
    assert out["tx"]["tx_id"] == "TX-1"
    assert out["output_proof_id"] == "GP-OUT-1"
    assert out["output_row"]["proof_id"] == "GP-OUT-1"


def test_materialize_postprocess_reads_sections() -> None:
    out = materialize_postprocess(
        postprocess={
            "output_row": {"proof_id": "GP-OUT-1"},
            "quality_chain_writeback": {"ok": True},
            "remediation": {"opened": False},
            "credit_endorsement": {"score": 88},
            "mirror_sync": {"synced": True},
        }
    )
    assert out["output_row"]["proof_id"] == "GP-OUT-1"
    assert out["quality_chain_writeback"]["ok"] is True
    assert out["credit_endorsement"]["score"] == 88
