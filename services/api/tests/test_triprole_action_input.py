from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.triprole_action_input import prepare_triprole_action_input


class _FakeEngine:
    def __init__(self, row: dict[str, object] | None) -> None:
        self._row = row

    def get_by_id(self, _proof_id: str) -> dict[str, object] | None:
        return self._row


def _engine_factory(row: dict[str, object] | None):
    def _factory(_sb: object) -> _FakeEngine:
        return _FakeEngine(row=row)

    return _factory


def test_prepare_triprole_action_input_returns_replayed_response_when_offline_hit() -> None:
    out = prepare_triprole_action_input(
        sb=object(),
        action="quality.check",
        input_proof_id="GP-IN-1",
        offline_packet_id="off-1",
        resolve_existing_offline_result_fn=lambda **_: {"output_proof_id": "GP-OUT-1"},
        build_triprole_replayed_response_fn=lambda **_: {"ok": True, "replayed": True},
        is_leaf_boq_row_fn=lambda _row: True,
        proof_utxo_engine_cls=_engine_factory(row={"proof_id": "GP-IN-1"}),
    )
    assert out["replayed_response"] == {"ok": True, "replayed": True}
    assert out["input_row"] is None


def test_prepare_triprole_action_input_rejects_missing_input_row() -> None:
    with pytest.raises(HTTPException) as exc:
        prepare_triprole_action_input(
            sb=object(),
            action="quality.check",
            input_proof_id="GP-IN-404",
            offline_packet_id="",
            resolve_existing_offline_result_fn=lambda **_: None,
            build_triprole_replayed_response_fn=lambda **_: {},
            is_leaf_boq_row_fn=lambda _row: True,
            proof_utxo_engine_cls=_engine_factory(row=None),
        )
    assert exc.value.status_code == 404
    assert "input proof_utxo not found" in str(exc.value.detail)


def test_prepare_triprole_action_input_rejects_non_leaf_row() -> None:
    with pytest.raises(HTTPException) as exc:
        prepare_triprole_action_input(
            sb=object(),
            action="quality.check",
            input_proof_id="GP-IN-1",
            offline_packet_id="",
            resolve_existing_offline_result_fn=lambda **_: None,
            build_triprole_replayed_response_fn=lambda **_: {},
            is_leaf_boq_row_fn=lambda _row: False,
            proof_utxo_engine_cls=_engine_factory(row={"proof_id": "GP-IN-1"}),
        )
    assert exc.value.status_code == 409
    assert "only allowed for leaf BOQ nodes" in str(exc.value.detail)


def test_prepare_triprole_action_input_returns_engine_and_row() -> None:
    row = {"proof_id": "GP-IN-1"}
    out = prepare_triprole_action_input(
        sb=object(),
        action="quality.check",
        input_proof_id="GP-IN-1",
        offline_packet_id="",
        resolve_existing_offline_result_fn=lambda **_: None,
        build_triprole_replayed_response_fn=lambda **_: {},
        is_leaf_boq_row_fn=lambda _row: True,
        proof_utxo_engine_cls=_engine_factory(row=row),
    )
    assert out["replayed_response"] is None
    assert out["input_row"] == row
