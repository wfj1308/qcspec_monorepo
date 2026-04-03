from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.actions.triprole_action_validate import validate_transition


def test_validate_transition_rejects_spent_input() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_transition("quality.check", {"spent": True})

    assert exc.value.status_code == 409
    assert "input_proof already spent" in str(exc.value.detail)


def test_validate_transition_rejects_measure_record_without_pass_on_entry() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_transition(
            "measure.record",
            {"result": "FAIL"},
            stage_from_row_fn=lambda _row: "ENTRY",
        )

    assert exc.value.status_code == 409
    assert "measure.record requires quality.check PASS" in str(exc.value.detail)


def test_validate_transition_rejects_dispute_resolve_on_non_dispute() -> None:
    with pytest.raises(HTTPException) as exc:
        validate_transition(
            "dispute.resolve",
            {"proof_type": "inspection"},
            stage_from_row_fn=lambda _row: "INITIAL",
        )

    assert exc.value.status_code == 409
    assert "dispute.resolve expects dispute input" in str(exc.value.detail)


def test_validate_transition_accepts_settlement_confirm_on_variation_stage() -> None:
    validate_transition(
        "settlement.confirm",
        {"result": "PASS"},
        stage_from_row_fn=lambda _row: "VARIATION",
    )
