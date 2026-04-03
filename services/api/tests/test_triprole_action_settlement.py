from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution import triprole_action_settlement as settlement_mod
from services.api.domain.execution.triprole_action_settlement import apply_settlement_confirm_transition


class _ExecResult:
    def __init__(self, data: list[dict[str, object]]) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, data: list[dict[str, object]]) -> None:
        self._data = data

    def select(self, *_args: object, **_kwargs: object) -> "_FakeQuery":
        return self

    def eq(self, *_args: object, **_kwargs: object) -> "_FakeQuery":
        return self

    def limit(self, *_args: object, **_kwargs: object) -> "_FakeQuery":
        return self

    def execute(self) -> _ExecResult:
        return _ExecResult(self._data)


class _FakeSB:
    def __init__(self, dispute_rows: list[dict[str, object]]) -> None:
        self.dispute_rows = dispute_rows

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self.dispute_rows)


def test_apply_settlement_confirm_transition_blocks_open_dispute() -> None:
    with pytest.raises(HTTPException) as exc:
        apply_settlement_confirm_transition(
            sb=_FakeSB([{"proof_id": "GP-DSP-1"}]),
            body={},
            input_row={},
            input_sd={},
            input_proof_id="GP-IN-1",
            payload={"allow_legacy_settlement": True},
            project_uri="v://project/demo",
            boq_item_uri="v://boq/1-1",
            segment_uri="v://segment/1",
            executor_uri="v://executor/system/",
            signer_metadata_raw={},
            normalized_signer_metadata={},
            now_iso="2026-01-01T00:00:00Z",
            next_state={},
            consensus_required_roles=("contractor", "supervisor", "owner"),
            aggregate_provenance_chain_fn=lambda *_: {},
            resolve_dual_pass_gate_fn=lambda **_: {},
            normalize_consensus_signatures_fn=lambda _raw: [],
            validate_consensus_signatures_fn=lambda _sigs: {"ok": True},
            verify_biometric_status_fn=lambda **_: {"ok": True},
            detect_consensus_deviation_fn=lambda **_: {"conflict": False},
            create_consensus_dispute_fn=lambda **_: {},
        )
    assert exc.value.status_code == 409
    assert "consensus_dispute_open" in str(exc.value.detail)


def test_apply_settlement_confirm_transition_success_path() -> None:
    result = apply_settlement_confirm_transition(
        sb=_FakeSB([]),
        body={},
        input_row={"proof_id": "GP-IN-1"},
        input_sd={},
        input_proof_id="GP-IN-1",
        payload={"consensus_signatures": [{"role": "contractor"}], "allow_legacy_settlement": True},
        project_uri="v://project/demo",
        boq_item_uri="v://boq/1-1",
        segment_uri="v://segment/1",
        executor_uri="v://executor/system/",
        signer_metadata_raw={"signers": []},
        normalized_signer_metadata={"signers": [], "metadata_hash": "mh1"},
        now_iso="2026-01-01T00:00:00Z",
        next_state={"existing": "v1"},
        consensus_required_roles=("contractor", "supervisor", "owner"),
        aggregate_provenance_chain_fn=lambda *_: {
            "gate": {"blocked": False},
            "total_proof_hash": "tph1",
        },
        resolve_dual_pass_gate_fn=lambda **_: {
            "ok": True,
            "qc_pass_count": 2,
            "lab_pass_count": 2,
        },
        normalize_consensus_signatures_fn=lambda raw: list(raw or []),
        validate_consensus_signatures_fn=lambda _sigs: {
            "ok": True,
            "consensus_hash": "ch1",
            "consensus_payload": {"signatures": [{"role": "contractor"}]},
        },
        verify_biometric_status_fn=lambda **_: {"ok": True, "metadata_hash": "mh1"},
        detect_consensus_deviation_fn=lambda **_: {"conflict": False},
        create_consensus_dispute_fn=lambda **_: {"ok": True, "proof_id": "GP-DSP-2"},
    )

    assert result["next_proof_type"] == "payment"
    assert result["tx_type"] == "settle"
    assert result["biometric_check"]["ok"] is True
    state = result["next_state"]
    assert state["existing"] == "v1"
    assert state["lifecycle_stage"] == "SETTLEMENT"
    assert state["status"] == "SETTLEMENT"
    assert state["pre_settlement_total_hash"] == "tph1"
    assert state["consensus"]["consensus_hash"] == "ch1"
    assert state["dual_pass_gate"]["ok"] is True
    assert state["artifact_uri"].startswith("v://project/demo/artifact/")


def test_apply_settlement_confirm_transition_blocks_conservation_mismatch() -> None:
    with pytest.raises(HTTPException) as exc:
        apply_settlement_confirm_transition(
            sb=_FakeSB([]),
            body={},
            input_row={"proof_id": "GP-IN-1"},
            input_sd={},
            input_proof_id="GP-IN-1",
            payload={
                "consensus_signatures": [{"role": "contractor"}],
                "approved_total": 100.0,
                "used_total": 99.0,
                "allow_legacy_settlement": True,
            },
            project_uri="v://project/demo",
            boq_item_uri="v://boq/1-1",
            segment_uri="v://segment/1",
            executor_uri="v://executor/system/",
            signer_metadata_raw={"signers": []},
            normalized_signer_metadata={"signers": [], "metadata_hash": "mh1"},
            now_iso="2026-01-01T00:00:00Z",
            next_state={},
            consensus_required_roles=("contractor", "supervisor", "owner"),
            aggregate_provenance_chain_fn=lambda *_: {
                "gate": {"blocked": False},
                "total_proof_hash": "tph1",
            },
            resolve_dual_pass_gate_fn=lambda **_: {
                "ok": True,
                "qc_pass_count": 2,
                "lab_pass_count": 2,
            },
            normalize_consensus_signatures_fn=lambda raw: list(raw or []),
            validate_consensus_signatures_fn=lambda _sigs: {
                "ok": True,
                "consensus_hash": "ch1",
                "consensus_payload": {"signatures": [{"role": "contractor"}]},
            },
            verify_biometric_status_fn=lambda **_: {"ok": True, "metadata_hash": "mh1"},
            detect_consensus_deviation_fn=lambda **_: {"conflict": False},
            create_consensus_dispute_fn=lambda **_: {"ok": True},
        )
    assert exc.value.status_code == 409
    assert "conservation_mismatch" in str(exc.value.detail)


def test_apply_settlement_confirm_transition_blocks_used_without_qc() -> None:
    with pytest.raises(HTTPException) as exc:
        apply_settlement_confirm_transition(
            sb=_FakeSB([]),
            body={},
            input_row={"proof_id": "GP-IN-1"},
            input_sd={},
            input_proof_id="GP-IN-1",
            payload={
                "consensus_signatures": [{"role": "contractor"}],
                "approved_total": 20.0,
                "used_total": 20.0,
                "allow_legacy_settlement": True,
            },
            project_uri="v://project/demo",
            boq_item_uri="v://boq/1-1",
            segment_uri="v://segment/1",
            executor_uri="v://executor/system/",
            signer_metadata_raw={"signers": []},
            normalized_signer_metadata={"signers": [], "metadata_hash": "mh1"},
            now_iso="2026-01-01T00:00:00Z",
            next_state={},
            consensus_required_roles=("contractor", "supervisor", "owner"),
            aggregate_provenance_chain_fn=lambda *_: {
                "gate": {"blocked": False},
                "total_proof_hash": "tph1",
            },
            resolve_dual_pass_gate_fn=lambda **_: {
                "ok": True,
                "qc_pass_count": 2,
                "lab_pass_count": 2,
            },
            normalize_consensus_signatures_fn=lambda raw: list(raw or []),
            validate_consensus_signatures_fn=lambda _sigs: {
                "ok": True,
                "consensus_hash": "ch1",
                "consensus_payload": {"signatures": [{"role": "contractor"}]},
            },
            verify_biometric_status_fn=lambda **_: {"ok": True, "metadata_hash": "mh1"},
            detect_consensus_deviation_fn=lambda **_: {"conflict": False},
            create_consensus_dispute_fn=lambda **_: {"ok": True},
        )
    assert exc.value.status_code == 409
    assert "used_without_quality_proof" in str(exc.value.detail)


def test_apply_settlement_confirm_transition_blocks_consensus_incomplete() -> None:
    with pytest.raises(HTTPException) as exc:
        apply_settlement_confirm_transition(
            sb=_FakeSB([]),
            body={},
            input_row={"proof_id": "GP-IN-1"},
            input_sd={},
            input_proof_id="GP-IN-1",
            payload={
                "consensus_signatures": [{"role": "contractor"}],
                "approved_total": 20.0,
                "used_total": 20.0,
                "allow_legacy_settlement": True,
            },
            project_uri="v://project/demo",
            boq_item_uri="v://boq/1-1",
            segment_uri="v://segment/1",
            executor_uri="v://executor/system/",
            signer_metadata_raw={"signers": []},
            normalized_signer_metadata={"signers": [], "metadata_hash": "mh1"},
            now_iso="2026-01-01T00:00:00Z",
            next_state={},
            consensus_required_roles=("contractor", "supervisor", "owner"),
            aggregate_provenance_chain_fn=lambda *_: {
                "gate": {"blocked": False},
                "total_proof_hash": "tph1",
            },
            resolve_dual_pass_gate_fn=lambda **_: {
                "ok": True,
                "qc_pass_count": 2,
                "lab_pass_count": 2,
            },
            normalize_consensus_signatures_fn=lambda raw: list(raw or []),
            validate_consensus_signatures_fn=lambda _sigs: {
                "ok": False,
                "missing_roles": ["owner"],
                "invalid": [],
            },
            verify_biometric_status_fn=lambda **_: {"ok": True, "metadata_hash": "mh1"},
            detect_consensus_deviation_fn=lambda **_: {"conflict": False},
            create_consensus_dispute_fn=lambda **_: {"ok": True},
        )
    assert exc.value.status_code == 409
    assert "consensus_signatures_incomplete" in str(exc.value.detail)


def test_apply_settlement_confirm_transition_accepts_used_with_entry_ancestor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settlement_mod,
        "_load_rows_for_boq",
        lambda **_: [
            {
                "proof_id": "GP-QC-ENTRY-1",
                "parent_proof_id": "",
                "result": "PASS",
                "state_data": {"lifecycle_stage": "ENTRY"},
            },
            {
                "proof_id": "GP-USE-1",
                "parent_proof_id": "GP-QC-ENTRY-1",
                "result": "PASS",
                "state_data": {
                    "lifecycle_stage": "INSTALLATION",
                    "settlement": {"settled_quantity": 10.0},
                },
            },
        ],
    )

    result = apply_settlement_confirm_transition(
        sb=_FakeSB([]),
        body={},
        input_row={"proof_id": "GP-IN-1"},
        input_sd={"ledger": {"merged_total": 10.0}},
        input_proof_id="GP-IN-1",
        payload={"consensus_signatures": [{"role": "contractor"}], "allow_legacy_settlement": True},
        project_uri="v://project/demo",
        boq_item_uri="v://boq/1-1",
        segment_uri="v://segment/1",
        executor_uri="v://executor/system/",
        signer_metadata_raw={"signers": []},
        normalized_signer_metadata={"signers": [], "metadata_hash": "mh1"},
        now_iso="2026-01-01T00:00:00Z",
        next_state={},
        consensus_required_roles=("contractor", "supervisor", "owner"),
        aggregate_provenance_chain_fn=lambda *_: {
            "gate": {"blocked": False},
            "total_proof_hash": "tph1",
        },
        resolve_dual_pass_gate_fn=lambda **_: {
            "ok": True,
            "qc_pass_count": 2,
            "lab_pass_count": 2,
        },
        normalize_consensus_signatures_fn=lambda raw: list(raw or []),
        validate_consensus_signatures_fn=lambda _sigs: {
            "ok": True,
            "consensus_hash": "ch1",
            "consensus_payload": {"signatures": [{"role": "contractor"}]},
        },
        verify_biometric_status_fn=lambda **_: {"ok": True, "metadata_hash": "mh1"},
        detect_consensus_deviation_fn=lambda **_: {"conflict": False},
        create_consensus_dispute_fn=lambda **_: {"ok": True},
    )
    preconditions = result["next_state"]["settlement_preconditions"]
    assert preconditions["approved_total"] == 10.0
    assert preconditions["used_total"] == 10.0
    assert preconditions["used_qc_ok"] is True
    assert result["next_state"]["final_proof_ready"] is True


def test_apply_settlement_confirm_transition_blocks_when_component_missing_by_default() -> None:
    with pytest.raises(HTTPException) as exc:
        apply_settlement_confirm_transition(
            sb=_FakeSB([]),
            body={},
            input_row={"proof_id": "GP-IN-1"},
            input_sd={},
            input_proof_id="GP-IN-1",
            payload={"consensus_signatures": [{"role": "contractor"}]},
            project_uri="v://project/demo",
            boq_item_uri="v://boq/1-1",
            segment_uri="v://segment/1",
            executor_uri="v://executor/system/",
            signer_metadata_raw={"signers": []},
            normalized_signer_metadata={"signers": [], "metadata_hash": "mh1"},
            now_iso="2026-01-01T00:00:00Z",
            next_state={},
            consensus_required_roles=("contractor", "supervisor", "owner"),
            aggregate_provenance_chain_fn=lambda *_: {
                "gate": {"blocked": False},
                "total_proof_hash": "tph1",
            },
            resolve_dual_pass_gate_fn=lambda **_: {
                "ok": True,
                "qc_pass_count": 2,
                "lab_pass_count": 2,
            },
            normalize_consensus_signatures_fn=lambda raw: list(raw or []),
            validate_consensus_signatures_fn=lambda _sigs: {
                "ok": True,
                "consensus_hash": "ch1",
                "consensus_payload": {"signatures": [{"role": "contractor"}]},
            },
            verify_biometric_status_fn=lambda **_: {"ok": True, "metadata_hash": "mh1"},
            detect_consensus_deviation_fn=lambda **_: {"conflict": False},
            create_consensus_dispute_fn=lambda **_: {"ok": True},
        )
    assert exc.value.status_code == 409
    assert "component_utxo_missing" in str(exc.value.detail)


def test_apply_settlement_confirm_transition_embeds_component_final_proof_factors() -> None:
    result = apply_settlement_confirm_transition(
        sb=_FakeSB([]),
        body={},
        input_row={"proof_id": "GP-IN-1"},
        input_sd={},
        input_proof_id="GP-IN-1",
        payload={
            "consensus_signatures": [{"role": "contractor"}],
            "component_utxo": {
                "component_id": "BEAM-L3",
                "kind": "precast_beam",
                "boq_items": [{"item_id": "403-1-2"}],
                "bom": {"steel": 1885},
                "material_inputs": [{"utxo_id": "u1", "material_role": "steel", "qty": 1885}],
            },
        },
        project_uri="v://project/demo",
        boq_item_uri="v://boq/1-1",
        segment_uri="v://segment/1",
        executor_uri="v://executor/system/",
        signer_metadata_raw={"signers": []},
        normalized_signer_metadata={"signers": [], "metadata_hash": "mh1"},
        now_iso="2026-01-01T00:00:00Z",
        next_state={},
        consensus_required_roles=("contractor", "supervisor", "owner"),
        aggregate_provenance_chain_fn=lambda *_: {
            "gate": {"blocked": False},
            "total_proof_hash": "tph1",
        },
        resolve_dual_pass_gate_fn=lambda **_: {
            "ok": True,
            "qc_pass_count": 2,
            "lab_pass_count": 2,
        },
        normalize_consensus_signatures_fn=lambda raw: list(raw or []),
        validate_consensus_signatures_fn=lambda _sigs: {
            "ok": True,
            "consensus_hash": "ch1",
            "consensus_payload": {"signatures": [{"role": "contractor"}]},
        },
        verify_biometric_status_fn=lambda **_: {"ok": True, "metadata_hash": "mh1"},
        detect_consensus_deviation_fn=lambda **_: {"conflict": False},
        create_consensus_dispute_fn=lambda **_: {"ok": True},
        build_component_utxo_verification_fn=lambda **_: {
            "ok": True,
            "passed": True,
            "proof_hash": "COMP-1",
            "proof_factors": {
                "material_chain_root_hash": "m1",
                "bom_deviation_hash": "b1",
                "norm_acceptance_hash": "n1",
            },
        },
    )
    state = result["next_state"]
    assert state["settlement_preconditions"]["component_present"] is True
    assert state["settlement_preconditions"]["component_conservation_ok"] is True
    assert state["component_utxo"]["proof_hash"] == "COMP-1"
    assert state["final_proof_factors"]["material_chain_root_hash"] == "m1"
    assert state["final_proof_factors"]["lineage_total_hash"] == "tph1"
    assert state["final_proof_factors"]["final_proof_hash"]
