from __future__ import annotations

from services.api.domain.specir.integrations import (
    collect_ref_uris_from_state_data,
    infer_specir_kind,
)


def test_infer_specir_kind() -> None:
    assert infer_specir_kind("v://norm/gate/a@v1") == "gate"
    assert infer_specir_kind("v://norm/spec-rule/a@v1") == "spec_rule"
    assert infer_specir_kind("v://norm/specdict/a@v1") == "spec_dict"
    assert infer_specir_kind("v://norm/specdict/a@v1#x") == "spec_item"
    assert infer_specir_kind("v://norm/spu/a@v1") == "spu"
    assert infer_specir_kind("v://norm/quota/a@v1") == "quota"
    assert infer_specir_kind("v://norm/meter-rule/a@v1") == "meter_rule"
    assert infer_specir_kind("v://other/x") == "unknown"


def test_collect_ref_uris_from_state_data() -> None:
    state = {
        "ref_gate_uri": "v://norm/gate/a@v1",
        "ref_gate_uris": ["v://norm/gate/a@v1", "v://norm/gate/b@v1"],
        "ref_spec_uri": "v://norm/spec-rule/s@v1",
        "ref_spu_uri": "v://norm/spu/rebar-processing@v1",
        "ref_quota": "v://norm/quota/rebar-processing@v1",
    }
    uris = collect_ref_uris_from_state_data(state)
    assert "v://norm/gate/a@v1" in uris
    assert "v://norm/gate/b@v1" in uris
    assert "v://norm/spec-rule/s@v1" in uris
    assert "v://norm/spu/rebar-processing@v1" in uris
    assert "v://norm/quota/rebar-processing@v1" in uris
