from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.actions.triprole_action_output import (
    build_triprole_action_response,
    consume_triprole_transition,
)


class _FakeEngine:
    def __init__(self, tx: dict[str, object], row: dict[str, object] | None) -> None:
        self._tx = tx
        self._row = row

    def consume(self, **_kwargs: object) -> dict[str, object]:
        return self._tx

    def get_by_id(self, _proof_id: str) -> dict[str, object] | None:
        return self._row


def test_consume_triprole_transition_success() -> None:
    engine = _FakeEngine(
        tx={"output_proofs": ["GP-OUT-1"], "tx_id": "tx1"},
        row={"proof_id": "GP-OUT-1", "state_data": {}},
    )
    out = consume_triprole_transition(
        engine=engine,
        input_row={"conditions": []},
        input_sd={},
        input_proof_id="GP-IN-1",
        owner_uri="v://owner/demo",
        project_id="p1",
        project_uri="v://project/demo",
        segment_uri="v://segment/1",
        next_proof_type="inspection",
        next_result="PASS",
        next_state={},
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        action="quality.check",
        boq_item_uri="v://boq/1-1",
        executor_did="did:example:1",
        did_gate={"did_gate_hash": "h1", "required_credential": "c1"},
        anchor={"spatiotemporal_anchor_hash": "a1"},
        geo_compliance={"trust_level": "HIGH", "warning": ""},
        biometric_check={"metadata_hash": "m1"},
        offline_packet_id="off1",
        tx_type="consume",
    )
    assert out["output_proof_id"] == "GP-OUT-1"
    assert out["output_row"]["proof_id"] == "GP-OUT-1"


def test_consume_triprole_transition_raises_when_no_outputs() -> None:
    engine = _FakeEngine(tx={"output_proofs": []}, row=None)
    with pytest.raises(HTTPException) as exc:
        consume_triprole_transition(
            engine=engine,
            input_row={},
            input_sd={},
            input_proof_id="GP-IN-1",
            owner_uri="v://owner/demo",
            project_id="p1",
            project_uri="v://project/demo",
            segment_uri="v://segment/1",
            next_proof_type="inspection",
            next_result="PASS",
            next_state={},
            executor_uri="v://executor/system/",
            executor_role="TRIPROLE",
            action="quality.check",
            boq_item_uri="v://boq/1-1",
            executor_did="did:example:1",
            did_gate={},
            anchor={},
            geo_compliance={},
            biometric_check={},
            offline_packet_id="off1",
            tx_type="consume",
        )
    assert exc.value.status_code == 500
    assert "produced no outputs" in str(exc.value.detail)


def test_build_triprole_action_response_fields() -> None:
    out = build_triprole_action_response(
        action="quality.check",
        input_proof_id="GP-IN-1",
        output_proof_id="GP-OUT-1",
        parent_hash="ph1",
        output_row={
            "proof_hash": "oh1",
            "proof_type": "inspection",
            "result": "PASS",
            "segment_uri": "v://segment/1",
            "gitpeg_anchor": "ga1",
            "state_data": {
                "boq_item_uri": "v://boq/1-1",
                "spatiotemporal_anchor_hash": "a1",
                "geo_compliance": {"trust_level": "HIGH"},
                "biometric_verification": {"ok": True},
                "available_quantity": 9.5,
                "artifact_uri": "v://artifact/1",
            },
        },
        did_gate={"ok": True},
        credit_endorsement={"score": 90},
        mirror_sync={"synced": True},
        quality_chain_writeback={"ok": True},
        remediation={"ok": False},
        offline_packet_id="off1",
        tx={"tx_id": "tx1"},
        provenance={"ok": True},
    )
    assert out["ok"] is True
    assert out["output_proof_id"] == "GP-OUT-1"
    assert out["boq_item_uri"] == "v://boq/1-1"
    assert out["available_balance"] == 9.5
    assert out["artifact_uri"] == "v://artifact/1"
