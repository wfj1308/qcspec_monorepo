from __future__ import annotations

from services.api.domain.specir.runtime.layering import (
    build_project_boq_item_ref,
    resolve_standard_spu_snapshot,
)


def test_build_project_boq_item_ref_uses_ref_only_shape() -> None:
    payload = build_project_boq_item_ref(
        boq_v_uri="v://cn.zhongbei/YADGS/boq/403-1-2",
        boq_item_id="403-1-2",
        description="Rebar processing and install",
        quantity="185.6",
        unit="t",
        bridge_uri="v://cn.zhongbei/YADGS/bridge/yk0-500-main",
        ref_spu_uri="v://norm/spu/rebar-processing@v1",
        ref_quota_uri="v://norm/quota/rebar-processing@v1",
        ref_meter_rule_uri="v://norm/meter-rule/by-weight@v1",
    )
    assert payload["boq_v_uri"] == "v://cn.zhongbei/YADGS/boq/403-1-2"
    assert payload["boq_item_id"] == "403-1-2"
    assert payload["quantity"] == "185.6"
    assert payload["ref_spu_uri"] == "v://norm/spu/rebar-processing@v1"
    assert "qc_gates" not in payload
    assert "consumption_rates" not in payload


def test_resolve_standard_spu_snapshot_preview_without_db() -> None:
    snapshot = resolve_standard_spu_snapshot(
        sb=None,
        ref_spu_uri="v://norm/spu/rebar-processing@v1",
    )
    assert snapshot["spu_uri"] == "v://norm/spu/rebar-processing@v1"
    assert snapshot["version"] == "v1"

