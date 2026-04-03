from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.actions.triprole_action_request import (
    build_triprole_replayed_response,
    parse_triprole_action_request,
)


def test_parse_triprole_action_request_reads_payload_fallbacks() -> None:
    body = {
        "action": "TripRole(quality.check)",
        "input_proof_id": "GP-IN-1",
        "executor_uri": "v://executor/system/",
        "payload": {
            "executor_did": "did:example:1",
            "credentials_vc": [{"id": "vc1"}],
            "signer_metadata": {"signers": [{"did": "did:example:1"}]},
        },
    }
    out = parse_triprole_action_request(
        body=body,
        valid_actions={"quality.check", "measure.record"},
    )
    assert out["action"] == "quality.check"
    assert out["input_proof_id"] == "GP-IN-1"
    assert out["executor_uri"] == "v://executor/system/"
    assert out["executor_role"] == "TRIPROLE"
    assert out["executor_did"] == "did:example:1"
    assert out["credentials_vc_raw"] == [{"id": "vc1"}]
    assert out["signer_metadata_raw"] == {"signers": [{"did": "did:example:1"}]}


def test_parse_triprole_action_request_rejects_invalid_action() -> None:
    with pytest.raises(HTTPException) as exc:
        parse_triprole_action_request(
            body={"action": "bad.action", "input_proof_id": "x", "executor_uri": "v://e"},
            valid_actions={"quality.check"},
        )
    assert exc.value.status_code == 400
    assert "unsupported action" in str(exc.value.detail)


def test_build_triprole_replayed_response_fields() -> None:
    out = build_triprole_replayed_response(
        action="quality.check",
        offline_packet_id="off1",
        reused={
            "trigger_data": {"input_proof_id": "GP-IN-1"},
            "output_proof_id": "GP-OUT-1",
            "proof_hash": "h1",
            "proof_type": "inspection",
            "result": "PASS",
            "boq_item_uri": "v://boq/1-1",
            "did_gate": {"ok": True},
            "credit_endorsement": {"score": 90},
            "mirror_sync": {"synced": True},
            "spatiotemporal_anchor_hash": "a1",
            "available_balance": 8.5,
            "tx_id": "tx1",
            "tx_type": "consume",
            "tx_status": "success",
        },
    )
    assert out["ok"] is True
    assert out["replayed"] is True
    assert out["input_proof_id"] == "GP-IN-1"
    assert out["output_proof_id"] == "GP-OUT-1"
    assert out["tx"]["reused"] is True
