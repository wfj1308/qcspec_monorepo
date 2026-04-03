from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.scan.triprole_scan_confirm import (
    execute_scan_confirm_signature,
)


class _FakeEngine:
    def __init__(self, input_row: dict[str, object], output_row: dict[str, object]) -> None:
        self._rows = {
            "GP-IN-1": input_row,
            "GP-OUT-1": output_row,
        }
        self.consume_calls: list[dict[str, object]] = []

    def get_by_id(self, proof_id: str) -> dict[str, object] | None:
        return self._rows.get(proof_id)

    def consume(self, **kwargs: object) -> dict[str, object]:
        self.consume_calls.append(kwargs)
        return {
            "tx_id": "TX-1",
            "output_proofs": ["GP-OUT-1"],
        }


def test_execute_scan_confirm_signature_happy_path() -> None:
    input_row = {
        "proof_hash": "hash-in",
        "owner_uri": "v://owner/demo",
        "project_id": "p1",
        "project_uri": "v://project/demo",
        "segment_uri": "v://segment/1",
        "proof_type": "approval",
        "result": "PASS",
        "conditions": [],
        "state_data": {
            "consensus": {
                "signatures": [
                    {"role": "owner", "did": "did:owner:1", "signature_hash": "h-owner"},
                ]
            }
        },
    }
    output_row = {
        "proof_hash": "hash-out",
        "project_id": "p1",
        "project_uri": "v://project/demo",
        "state_data": {},
    }
    fake_engine = _FakeEngine(input_row=input_row, output_row=output_row)
    patch_calls: list[dict[str, object]] = []

    out = execute_scan_confirm_signature(
        sb=object(),
        input_proof_id="GP-IN-1",
        scan_payload={
            "proof_id": "GP-IN-1",
            "token_hash": "tok-1",
            "signer_role": "owner",
            "signer_did": "did:owner:1",
        },
        scanner_did="did:scanner:1",
        scanner_role="supervisor",
        consensus_required_roles=("contractor", "supervisor", "owner"),
        proof_utxo_engine_cls=lambda _sb: fake_engine,
        validate_scan_confirm_payload_fn=lambda payload: dict(payload),
        normalize_role_fn=lambda value: str(value or "").strip().lower(),
        utc_iso_fn=lambda: "2026-01-01T00:00:00Z",
        build_spatiotemporal_anchor_fn=lambda **_: {
            "geo_location": {"lat": 1},
            "server_timestamp_proof": {"ts": "1"},
            "spatiotemporal_anchor_hash": "anchor-1",
        },
        normalize_consensus_signatures_fn=lambda raw: [dict(x) for x in (raw or [])],
        looks_like_sig_hash_fn=lambda _value: False,
        validate_consensus_signatures_fn=lambda signatures: {
            "ok": True,
            "consensus_hash": "cons-1",
            "missing_roles": [],
            "invalid": [],
            "signatures_count": len(signatures),
        },
        normalize_signer_metadata_fn=lambda _raw: {
            "metadata_hash": "meta-1",
            "signers": [{"did": "did:scanner:1"}],
        },
        normalize_result_fn=lambda value: str(value or "").strip().upper(),
        calculate_sovereign_credit_fn=lambda **_: {"score": 88},
        sync_to_mirrors_fn=lambda **_: {"synced": True},
        build_shadow_packet_fn=lambda **_: {"packet": True},
        patch_state_data_fields_fn=lambda **kwargs: (
            patch_calls.append(dict(kwargs))
            or {"credit_endorsement": {"score": 88}, "shadow_mirror_sync": {"synced": True}}
        ),
    )

    assert out["ok"] is True
    assert out["input_proof_id"] == "GP-IN-1"
    assert out["output_proof_id"] == "GP-OUT-1"
    assert out["proof_hash"] == "hash-out"
    assert out["credit_endorsement"]["score"] == 88
    assert out["mirror_sync"]["synced"] is True
    assert out["consensus_complete"] is True
    assert out["spatiotemporal_anchor_hash"] == "anchor-1"
    assert out["tx"]["tx_id"] == "TX-1"
    assert fake_engine.consume_calls, "consume should be called"
    assert patch_calls and patch_calls[0]["proof_id"] == "GP-OUT-1"


def test_execute_scan_confirm_signature_rejects_invalid_scanner_did() -> None:
    with pytest.raises(HTTPException) as exc:
        execute_scan_confirm_signature(
            sb=object(),
            input_proof_id="GP-IN-1",
            scan_payload={},
            scanner_did="scanner-no-did-prefix",
            scanner_role="supervisor",
        )

    assert exc.value.status_code == 400
    assert "scanner_did must start with did:" in str(exc.value.detail)
