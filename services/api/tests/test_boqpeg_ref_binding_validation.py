from __future__ import annotations

from services.api.domain.boqpeg.runtime.ref_binding import validate_ref_only_rows


def _leaf_row(*, include_project_ref: bool, include_legacy_logic: bool) -> dict:
    state_data = {
        "is_leaf": True,
        "item_no": "403-1-2",
        "boq_item_uri": "v://cn.zhongbei/YADGS/boq/403-1-2",
        "ref_spu_uri": "v://norm/spu/rebar-processing@v1",
        "ref_quota_uri": "v://norm/quota/rebar-processing@v1",
        "ref_meter_rule_uri": "v://norm/meter-rule/by-weight@v1",
    }
    if include_project_ref:
        state_data["project_boq_item_ref"] = {
            "boq_v_uri": "v://cn.zhongbei/YADGS/boq/403-1-2",
            "boq_item_id": "403-1-2",
            "description": "Rebar processing and install",
            "quantity": "185.6",
            "unit": "t",
            "bridge_uri": "v://cn.zhongbei/YADGS/bridge/yk0-500-main",
            "ref_spu_uri": "v://norm/spu/rebar-processing@v1",
            "ref_quota_uri": "v://norm/quota/rebar-processing@v1",
            "ref_meter_rule_uri": "v://norm/meter-rule/by-weight@v1",
            "custom_params": {},
        }
    if include_legacy_logic:
        state_data["spu_formula"] = {"legacy": True}
    return {"proof_id": "GP-BOQ-1", "state_data": state_data}


def test_validate_ref_only_rows_accepts_ref_only_project_payload() -> None:
    out = validate_ref_only_rows([_leaf_row(include_project_ref=True, include_legacy_logic=False)])
    assert out["ok"] is True
    assert int(out.get("invalid_leaf_rows") or 0) == 0
    assert int(out.get("invalid_project_ref_rows") or 0) == 0
    assert int(out.get("legacy_inline_logic_rows") or 0) == 0


def test_validate_ref_only_rows_rejects_legacy_inline_logic_and_missing_project_ref() -> None:
    out = validate_ref_only_rows([_leaf_row(include_project_ref=False, include_legacy_logic=True)])
    assert out["ok"] is False
    assert int(out.get("invalid_leaf_rows") or 0) == 1
    assert int(out.get("invalid_project_ref_rows") or 0) == 1
    assert int(out.get("legacy_inline_logic_rows") or 0) == 1

