from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.triprole_realtime_query import (
    fetch_boq_realtime_status,
)


class _ExecResult:
    def __init__(self, data: list[dict[str, object]]) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, data: list[dict[str, object]], *, fail: bool = False) -> None:
        self._data = data
        self._fail = fail
        self.limit_value: int | None = None
        self.eq_args: tuple[str, str] | None = None

    def select(self, _value: str) -> "_FakeQuery":
        return self

    def eq(self, key: str, value: str) -> "_FakeQuery":
        self.eq_args = (key, value)
        return self

    def order(self, _column: str, *, desc: bool = False) -> "_FakeQuery":
        _ = desc
        return self

    def limit(self, value: int) -> "_FakeQuery":
        self.limit_value = value
        return self

    def execute(self) -> _ExecResult:
        if self._fail:
            raise RuntimeError("db down")
        return _ExecResult(self._data)


class _FakeSb:
    def __init__(self, query: _FakeQuery) -> None:
        self.query = query

    def table(self, _name: str) -> _FakeQuery:
        return self.query


def test_fetch_boq_realtime_status_requires_project_uri() -> None:
    with pytest.raises(HTTPException) as exc:
        fetch_boq_realtime_status(
            sb=_FakeSb(_FakeQuery([])),
            project_uri="  ",
            aggregate_provenance_chain_fn=lambda _utxo_id: {},
        )
    assert exc.value.status_code == 400
    assert "project_uri is required" in str(exc.value.detail)


def test_fetch_boq_realtime_status_wraps_query_error() -> None:
    with pytest.raises(HTTPException) as exc:
        fetch_boq_realtime_status(
            sb=_FakeSb(_FakeQuery([], fail=True)),
            project_uri="v://project/demo",
            aggregate_provenance_chain_fn=lambda _utxo_id: {},
        )
    assert exc.value.status_code == 502
    assert "failed to load proof_utxo" in str(exc.value.detail)


def test_fetch_boq_realtime_status_queries_rows_and_builds_payload() -> None:
    query = _FakeQuery([{"proof_id": "P1"}])
    captured: dict[str, object] = {}

    out = fetch_boq_realtime_status(
        sb=_FakeSb(query),
        project_uri="v://project/demo",
        limit=20001,
        aggregate_provenance_chain_fn=lambda _utxo_id: {"ok": True},
        build_boq_realtime_status_fn=lambda **kwargs: (
            captured.update(kwargs) or {"ok": True, "items": []}
        ),
    )

    assert out["ok"] is True
    assert query.eq_args == ("project_uri", "v://project/demo")
    assert query.limit_value == 10000
    assert captured["project_uri"] == "v://project/demo"
    assert captured["rows"] == [{"proof_id": "P1"}]
