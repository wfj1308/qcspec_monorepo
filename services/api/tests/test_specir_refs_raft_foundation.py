from __future__ import annotations

from services.api.domain.specir.runtime.refs import resolve_spu_ref_pack


def test_resolve_spu_ref_pack_prefers_raft_foundation_for_raft_item_name() -> None:
    out = resolve_spu_ref_pack(
        item_code="403-RAFT",
        item_name="筏基础混凝土浇筑",
        quantity_unit="m3",
    )
    assert out["ref_spu_uri"] == "v://normref.com/spu/raft-foundation@v1"
    assert out["ref_quota_uri"] == "v://normref.com/quota/raft-foundation@v1"
    assert out["ref_meter_rule_uri"] == "v://norm/meter-rule/by-volume@v1"
