from __future__ import annotations

import pytest

from services.api.domain.execution.asset import triprole_variation as variation_mod


class _FakeEngine:
    created_payload: dict[str, object] | None = None

    def __init__(self, _sb: object) -> None:
        pass

    def create(self, **kwargs: object) -> dict[str, object]:
        _FakeEngine.created_payload = dict(kwargs)
        return {
            "proof_id": str(kwargs.get("proof_id") or "GP-PROOF-OUT-1"),
            "proof_hash": "hash-created",
            "state_data": dict(kwargs.get("state_data") or {}),
        }

    def get_by_id(self, proof_id: str) -> dict[str, object]:
        created = dict(_FakeEngine.created_payload or {})
        return {
            "proof_id": proof_id,
            "proof_hash": "hash-output",
            "project_id": "P1",
            "project_uri": str(created.get("project_uri") or ""),
            "state_data": dict(created.get("state_data") or {}),
        }


def test_apply_variation_creates_fork_delta_utxo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(variation_mod, "_resolve_existing_offline_result", lambda **_: None)
    monkeypatch.setattr(
        variation_mod,
        "_resolve_transfer_input_row",
        lambda **_: {
            "proof_id": "GP-IN-1",
            "proof_hash": "hash-in",
            "owner_uri": "v://owner/demo/",
            "project_id": "P1",
            "project_uri": "v://project/demo",
            "segment_uri": "v://project/demo/boq/403-1-2",
            "proof_type": "approval",
            "result": "PASS",
            "state_data": {
                "boq_item_uri": "v://project/demo/boq/403-1-2",
                "ledger": {"current_balance": 100.0},
                "norm_uri": "v://norm/spec/1",
            },
        },
    )
    monkeypatch.setattr(variation_mod, "resolve_required_credential", lambda **_: "vc://triprole/variation")
    monkeypatch.setattr(
        variation_mod,
        "verify_credential",
        lambda **_: {"ok": True, "did_gate_hash": "dg1", "required_credential": "vc://triprole/variation"},
    )
    monkeypatch.setattr(
        variation_mod,
        "_compute_delta_merge",
        lambda **_: {
            "initial_balance": 100.0,
            "delta_total_after": 20.0,
            "merged_total_after": 120.0,
            "transferred_total": 0.0,
            "previous_balance": 100.0,
            "balance_after": 120.0,
            "delta_amount": 20.0,
            "merged_total_before": 100.0,
        },
    )
    monkeypatch.setattr(variation_mod, "_build_spatiotemporal_anchor", lambda **_: {"spatiotemporal_anchor_hash": "a1"})
    monkeypatch.setattr(variation_mod, "ProofUTXOEngine", _FakeEngine)
    monkeypatch.setattr(variation_mod, "calculate_sovereign_credit", lambda **_: {"score": 91.2})
    monkeypatch.setattr(variation_mod, "sync_to_mirrors", lambda **_: {"attempted": True, "synced": True})
    monkeypatch.setattr(
        variation_mod,
        "_patch_state_data_fields",
        lambda **kwargs: {
            **dict((kwargs.get("patch") or {})),
            "status": "VARIATION",
        },
    )

    out = variation_mod.apply_variation(
        sb=object(),
        boq_item_uri="v://project/demo/boq/403-1-2",
        delta_amount=20.0,
        reason="design update",
        project_uri="v://project/demo",
        executor_uri="v://executor/system/",
        executor_did="did:example:supervisor",
        executor_role="TRIPROLE",
        metadata={"source": "manual"},
    )

    assert out["ok"] is True
    assert out["variation_mode"] == "fork_delta_utxo"
    assert out["available_balance"] == 120.0
    assert out["did_gate"]["ok"] is True
    assert out["tx"]["tx_type"] == "fork"
    assert out["tx"]["tx_semantics"] == "fork_delta_utxo"
    assert out["tx"]["trigger_action"] == "TripRole.apply_variation.fork"

    created = _FakeEngine.created_payload or {}
    state_data = dict(created.get("state_data") or {})
    assert state_data["delta_utxo"]["merge_strategy"] == "fork_delta_then_aggregate"
    assert state_data["delta_utxo"]["approved_total_with_deltas"] == 120.0
    assert state_data["variation"]["reason"] == "design update"
    assert state_data["parent_proof_id"] == "GP-IN-1"


def test_apply_variation_reuses_existing_offline_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        variation_mod,
        "_resolve_existing_offline_result",
        lambda **_: {
            "boq_item_uri": "v://project/demo/boq/403-1-2",
            "output_proof_id": "GP-OUT-1",
            "proof_hash": "hash-out-1",
            "did_gate": {"ok": True},
            "credit_endorsement": {"score": 90},
            "mirror_sync": {"synced": True},
            "spatiotemporal_anchor_hash": "anchor-1",
            "available_balance": 88.0,
            "tx_id": "TX-1",
            "tx_type": "fork",
            "tx_status": "success",
        },
    )

    out = variation_mod.apply_variation(
        sb=object(),
        boq_item_uri="v://project/demo/boq/403-1-2",
        delta_amount=8.0,
        offline_packet_id="OFFLINE-1",
    )

    assert out["ok"] is True
    assert out["replayed"] is True
    assert out["output_proof_id"] == "GP-OUT-1"
    assert out["tx"]["reused"] is True
