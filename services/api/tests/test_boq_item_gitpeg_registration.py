from __future__ import annotations

from services.api.domain.boq.runtime.utxo import BoqItem, initialize_boq_utxos
from services.api.domain.projects.gitpeg_sdk import register_boq_item, register_uri


def test_register_boq_item_preview_returns_canonical_and_alias_uris() -> None:
    out = register_boq_item(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        identifier="403-1-2",
        metadata={
            "description": "Rebar processing and install",
            "unit": "t",
            "boq_quantity": 185.6,
        },
        bridge_uri="v://cn.zhongbei/YADGS/bridge/yk0-500-main",
        commit=False,
    )
    assert out["ok"] is True
    assert out["canonical_uri"] == "v://cn.zhongbei/YADGS/boq/403-1-2"
    assert out["full_line_uri"] == "v://cn.zhongbei/YADGS/full-line/boq/403-1-2"
    assert out["bridge_scoped_uri"] == "v://cn.zhongbei/YADGS/bridge/yk0-500-main/boq/403-1-2"
    assert out["committed"] is False


def test_register_uri_preview_supports_normref_core_uri() -> None:
    out = register_uri(
        sb=None,
        uri="v://normref.com/core@v1",
        uri_type="normref_core",
        commit=False,
    )
    assert out["ok"] is True
    assert out["uri"] == "v://normref.com/core@v1"
    assert out["uri_type"] == "normref_core"
    assert out["committed"] is False


def test_initialize_boq_utxos_leaf_contains_gitpeg_registration_uris() -> None:
    items = [
        BoqItem(
            item_no="403-1-2",
            name="Rebar processing and install",
            unit="t",
            division="Bridge",
            subdivision="Rebar",
            hierarchy_raw="Bridge/Rebar",
            design_quantity=10.0,
            design_quantity_raw="10",
            unit_price=100.0,
            unit_price_raw="100",
            approved_quantity=9.8,
            approved_quantity_raw="9.8",
            remark="",
            row_index=1,
            sheet_name="Sheet1",
        )
    ]
    out = initialize_boq_utxos(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        project_id=None,
        boq_items=items,
        bridge_mappings={"403-1-2": "yk0-500-main"},
        commit=False,
    )
    leaf_state = {}
    for row in out.get("preview") or []:
        sd = row.get("state_data") or {}
        if bool(sd.get("is_leaf")):
            leaf_state = sd
            break

    assert leaf_state
    assert leaf_state["boq_item_canonical_uri"] == "v://cn.zhongbei/YADGS/boq/403-1-2"
    assert leaf_state["boq_item_full_line_uri"] == "v://cn.zhongbei/YADGS/full-line/boq/403-1-2"
    assert leaf_state["boq_item_bridge_scoped_uri"] == "v://cn.zhongbei/YADGS/bridge/yk0-500-main/boq/403-1-2"
    assert (leaf_state.get("boq_item_registration") or {}).get("ok") is True
    assert (leaf_state.get("boq_item") or {}).get("v_uri") == "v://cn.zhongbei/YADGS/boq/403-1-2"
