from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution import triprole_docfinal_runtime as runtime


def test_load_docfinal_chain_validates_and_scopes() -> None:
    with pytest.raises(HTTPException) as exc:
        runtime.load_docfinal_chain(
            boq_item_uri="",
            sb=object(),
            project_meta={},
            load_chain=lambda *_: [],
        )
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        runtime.load_docfinal_chain(
            boq_item_uri="v://boq/1",
            sb=object(),
            project_meta={},
            load_chain=lambda *_: [],
        )
    assert exc.value.status_code == 404

    normalized, chain = runtime.load_docfinal_chain(
        boq_item_uri=" v://boq/1 ",
        sb=object(),
        project_meta={"project_uri": "v://project/a"},
        load_chain=lambda *_: [
            {"project_uri": "v://project/a", "proof_id": "p1"},
            {"project_uri": "v://project/b", "proof_id": "p2"},
        ],
    )
    assert normalized == "v://boq/1"
    assert len(chain) == 1
    assert chain[0]["proof_id"] == "p1"


def test_resolve_docfinal_lineage_and_asset_origin_handles_failures() -> None:
    lineage, origin = runtime.resolve_docfinal_lineage_and_asset_origin(
        latest_proof_id="p1",
        sb=object(),
        boq_item_uri="v://boq/1",
        project_uri="v://project/a",
        get_full_lineage=lambda *_: {"total_proof_hash": "h1"},
        trace_asset_origin=lambda **_: {"statement": "ok"},
    )
    assert lineage and lineage["total_proof_hash"] == "h1"
    assert origin and origin["statement"] == "ok"

    lineage, origin = runtime.resolve_docfinal_lineage_and_asset_origin(
        latest_proof_id="p1",
        sb=object(),
        boq_item_uri="v://boq/1",
        project_uri="v://project/a",
        get_full_lineage=lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),
        trace_asset_origin=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert lineage is None
    assert origin is None

    lineage, origin = runtime.resolve_docfinal_lineage_and_asset_origin(
        latest_proof_id="",
        sb=object(),
        boq_item_uri="v://boq/1",
        project_uri="v://project/a",
        get_full_lineage=lambda *_: {"x": 1},
        trace_asset_origin=lambda **_: {"y": 1},
    )
    assert lineage is None
    assert origin is None


def test_resolve_docfinal_transfer_receipt_paths() -> None:
    assert (
        runtime.resolve_docfinal_transfer_receipt(
            apply_asset_transfer=False,
            sb=object(),
            transfer_amount=None,
            latest_row={},
            boq_item_uri="v://boq/1",
            transfer_executor_uri="v://executor/system/",
            verify_uri="",
            settled_quantity=lambda *_: 1.0,
            transfer_asset=lambda **_: {"ok": True},
        )
        is None
    )

    no_amount = runtime.resolve_docfinal_transfer_receipt(
        apply_asset_transfer=True,
        sb=object(),
        transfer_amount=0.0,
        latest_row={},
        boq_item_uri="v://boq/1",
        transfer_executor_uri="v://executor/system/",
        verify_uri="",
        settled_quantity=lambda *_: 0.0,
        transfer_asset=lambda **_: {"ok": True},
    )
    assert no_amount and no_amount["ok"] is False
    assert no_amount["error"] == "no_valid_transfer_amount"

    success = runtime.resolve_docfinal_transfer_receipt(
        apply_asset_transfer=True,
        sb=object(),
        transfer_amount=2.0,
        latest_row={"proof_id": "p1", "proof_hash": "h1", "project_uri": "v://project/a"},
        boq_item_uri="v://boq/1",
        transfer_executor_uri="v://executor/system/",
        verify_uri="v://verify/a",
        settled_quantity=lambda *_: 0.0,
        transfer_asset=lambda **kwargs: {"ok": True, "amount": kwargs["amount"]},
    )
    assert success and success["ok"] is True
    assert success["amount"] == 2.0

    failed = runtime.resolve_docfinal_transfer_receipt(
        apply_asset_transfer=True,
        sb=object(),
        transfer_amount=2.0,
        latest_row={"proof_id": "p1", "proof_hash": "h1", "project_uri": "v://project/a"},
        boq_item_uri="v://boq/1",
        transfer_executor_uri="v://executor/system/",
        verify_uri="v://verify/a",
        settled_quantity=lambda *_: 0.0,
        transfer_asset=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert failed and failed["ok"] is False
    assert "RuntimeError" in failed["error"]
