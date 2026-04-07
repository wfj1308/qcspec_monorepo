from __future__ import annotations

from typing import Any

from services.api.domain.boqpeg.runtime.spu_mapping import map_spu_to_boq_preview_rows


def _preview_leaf_row() -> dict[str, Any]:
    return {
        "proof_id": "GP-BOQ-1",
        "state_data": {
            "is_leaf": True,
            "item_no": "403-1-2",
            "boq_item_uri": "v://project/demo/boq/400/403-1-2",
            "bridge_uri": "v://project/demo/bridge/yk0-500-main",
            "ref_spu_uri": "v://norm/spu/rebar-processing@v1",
            "ref_quota_uri": "v://norm/quota/rebar-processing@v1",
            "ref_meter_rule_uri": "v://norm/meter-rule/rebar-by-ton@v1",
            "ref_spec_uri": "v://norm/spec-rule/rebar@v1",
            "norm_refs": ["v://norm/GB50204@2015"],
        },
    }


def test_map_spu_to_boq_preview_rows_generates_mapping_and_proofs() -> None:
    out = map_spu_to_boq_preview_rows(
        sb=None,
        commit=False,
        project_uri="v://project/demo",
        owner_uri="v://project/demo/role/system/",
        source_file="boq.csv",
        preview_rows=[_preview_leaf_row()],
    )
    assert out["ok"] is True
    assert int(out.get("count") or 0) == 3
    assert isinstance(out.get("mappings"), list)
    mapping = out["mappings"][0]
    assert str(mapping.get("mapping_id") or "").startswith("SPUMAP-")
    assert str(mapping.get("spu_uri") or "").startswith("v://norm/spu/")
    assert str(mapping.get("default_quantity_per_unit") or "").strip() != ""
    assert str(mapping.get("proof_id") or "").startswith("GP-SPUMAP-")
    assert str(mapping.get("proof_hash") or "").strip() != ""
    assert mapping.get("proof", {}).get("committed") is False
    by_uri = out.get("mapping_by_boq_uri") or {}
    assert isinstance(by_uri, dict)
    assert "v://project/demo/boq/400/403-1-2" in by_uri


class _ExecResult:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _FakeTable:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def upsert(self, rows: list[dict[str, Any]], **_kwargs: Any) -> "_FakeTable":
        self.rows.extend(rows)
        return self

    def execute(self) -> _ExecResult:
        return _ExecResult(self.rows)


class _FakeSB:
    def __init__(self) -> None:
        self.table_obj = _FakeTable()

    def table(self, _name: str) -> _FakeTable:
        return self.table_obj


def test_map_spu_to_boq_preview_rows_commit_persists_table_when_available(monkeypatch) -> None:
    created_calls: list[dict[str, Any]] = []

    class _FakeEngine:
        def __init__(self, _sb: Any) -> None:
            pass

        def create(self, **kwargs: Any) -> dict[str, Any]:
            created_calls.append(dict(kwargs))
            return {"proof_hash": f"hash-{len(created_calls)}"}

    monkeypatch.setattr("services.api.domain.boqpeg.runtime.spu_mapping.ProofUTXOEngine", _FakeEngine)
    sb = _FakeSB()
    out = map_spu_to_boq_preview_rows(
        sb=sb,
        commit=True,
        project_uri="v://project/demo",
        owner_uri="v://project/demo/role/system/",
        source_file="boq.csv",
        preview_rows=[_preview_leaf_row()],
    )

    assert int(out.get("count") or 0) == 3
    assert len(created_calls) == 3
    persist = out.get("persist") or {}
    assert persist.get("ok") is True
    assert persist.get("status") == "persisted"
    assert int(persist.get("persisted") or 0) == 3
    assert len(sb.table_obj.rows) == 3
    assert str((sb.table_obj.rows[0] or {}).get("default_quantity_per_unit") or "").strip() != ""
