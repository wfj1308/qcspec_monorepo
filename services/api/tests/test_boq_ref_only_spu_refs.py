from __future__ import annotations

from services.api.domain.boq.runtime.utxo import BoqItem, initialize_boq_utxos
from services.api.domain.specir.runtime.refs import resolve_spu_ref_pack


def test_resolve_spu_ref_pack_by_prefix() -> None:
    rebar = resolve_spu_ref_pack(item_code="403-1-2", item_name="钢筋加工及安装", quantity_unit="t")
    assert rebar["ref_spu_uri"] == "v://norm/spu/rebar-processing@v1"
    assert rebar["ref_quota_uri"] == "v://norm/quota/rebar-processing@v1"
    assert rebar["ref_meter_rule_uri"] == "v://norm/meter-rule/by-weight@v1"

    contract = resolve_spu_ref_pack(item_code="101-1", item_name="合同支付", quantity_unit="CNY")
    assert contract["ref_spu_uri"] == "v://norm/spu/contract-payment@v1"
    assert contract["ref_quota_uri"] == "v://norm/quota/contract-payment@v1"
    assert contract["ref_meter_rule_uri"] == "v://norm/meter-rule/contract-payment@v1"


def test_initialize_boq_utxos_preview_contains_spu_refs() -> None:
    items = [
        BoqItem(
            item_no="403-1-2",
            name="钢筋加工及安装",
            unit="t",
            division="桥梁工程",
            subdivision="钢筋工程",
            hierarchy_raw="桥梁/钢筋",
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
    result = initialize_boq_utxos(
        sb=None,
        project_uri="v://project/demo",
        project_id=None,
        boq_items=items,
        commit=False,
    )
    assert result["preview"]
    leaf_state = {}
    for row in result["preview"]:
        state = row["state_data"]
        if bool(state.get("is_leaf")) and str(state.get("item_no") or "").strip() == "403-1-2":
            leaf_state = state
            break
    assert leaf_state
    state = leaf_state
    assert state["ref_spu_uri"] == "v://norm/spu/rebar-processing@v1"
    assert state["ref_quota_uri"] == "v://norm/quota/rebar-processing@v1"
    assert state["ref_meter_rule_uri"] == "v://norm/meter-rule/by-weight@v1"
    project_ref = state.get("project_boq_item_ref") or {}
    assert project_ref["boq_item_id"] == "403-1-2"
    assert project_ref["ref_spu_uri"] == "v://norm/spu/rebar-processing@v1"
    assert project_ref["ref_quota_uri"] == "v://norm/quota/rebar-processing@v1"
    assert project_ref["ref_meter_rule_uri"] == "v://norm/meter-rule/by-weight@v1"
