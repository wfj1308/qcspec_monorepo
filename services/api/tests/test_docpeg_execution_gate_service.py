from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import HTTPException

from services.api.core.docpeg.access import DocPegExecutionGateService


@dataclass
class _ExecResult:
    data: list[dict[str, Any]]


class _FakeQuery:
    def __init__(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        self.table_name = table_name
        self.rows = rows
        self._in_filters: dict[str, set[str]] = {}

    def select(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def in_(self, field: str, values: list[str]) -> "_FakeQuery":
        self._in_filters[str(field)] = {str(v) for v in values}
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def execute(self) -> _ExecResult:
        filtered = list(self.rows)
        for field, allowed in self._in_filters.items():
            filtered = [row for row in filtered if str(row.get(field) or "") in allowed]
        return _ExecResult(data=filtered)


class _FakeSupabase:
    def __init__(self, *, project_rows: list[dict[str, Any]], node_rows: list[dict[str, Any]]) -> None:
        self.project_rows = project_rows
        self.node_rows = node_rows

    def table(self, table_name: str) -> _FakeQuery:
        if table_name == "coord_gitpeg_project_registry":
            return _FakeQuery(table_name, self.project_rows)
        if table_name == "coord_gitpeg_nodes":
            return _FakeQuery(table_name, self.node_rows)
        return _FakeQuery(table_name, [])


def test_gate_allows_write_on_active_project_with_admin_role() -> None:
    sb = _FakeSupabase(
        project_rows=[{"project_uri": "v://project/demo", "gitpeg_status": "active"}],
        node_rows=[],
    )
    gate = DocPegExecutionGateService(sb=sb)
    out = gate.enforce_execution(
        identity={"dto_role": "ADMIN", "v_uri": "v://project/demo/executor/admin"},
        operation="boqpeg_import_upload",
        access_mode="write",
        project_uri="v://project/demo",
    )
    assert out["ok"] is True
    assert out["project_registration"]["gitpeg_status"] == "active"


def test_gate_blocks_write_when_role_is_not_elevated() -> None:
    sb = _FakeSupabase(
        project_rows=[{"project_uri": "v://project/demo", "gitpeg_status": "active"}],
        node_rows=[],
    )
    gate = DocPegExecutionGateService(sb=sb)
    with pytest.raises(HTTPException) as exc:
        gate.enforce_execution(
            identity={"dto_role": "INSPECTOR"},
            operation="boqpeg_import_upload",
            access_mode="write",
            project_uri="v://project/demo",
        )
    assert exc.value.status_code == 403


def test_gate_blocks_unregistered_project() -> None:
    sb = _FakeSupabase(project_rows=[], node_rows=[])
    gate = DocPegExecutionGateService(sb=sb)
    with pytest.raises(HTTPException) as exc:
        gate.enforce_execution(
            identity={"dto_role": "ADMIN"},
            operation="boqpeg_full_line_piles",
            access_mode="read",
            project_uri="v://project/missing",
        )
    assert exc.value.status_code == 403


def test_gate_allows_node_mode_when_node_registered() -> None:
    sb = _FakeSupabase(
        project_rows=[],
        node_rows=[{"uri": "v://project/demo/boq/403-1-2", "uri_type": "artifact"}],
    )
    gate = DocPegExecutionGateService(sb=sb)
    out = gate.enforce_execution(
        identity={"roles": ["ADMIN"]},
        operation="boqpeg_forward_bom",
        access_mode="write",
        node_uri="v://project/demo/boq/403-1-2",
    )
    assert out["ok"] is True
    assert out["node_registration"]["uri"] == "v://project/demo/boq/403-1-2"

