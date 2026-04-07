from __future__ import annotations

from services.api.domain.specir.integrations import (
    is_spu_ultimate_content,
    normalize_spu_content,
    validate_spu_content,
)


def test_normalize_legacy_spu_content_to_ultimate_schema() -> None:
    legacy = {
        "industry": "highway",
        "unit": "m3",
        "norm_refs": ["GB50204-2015"],
        "gate_refs": ["v://norm/gate/concrete-strength-check@v1"],
        "quota_ref": "v://norm/quota/concrete-casting@v1",
        "meter_rule_ref": "v://norm/meter-rule/by-volume@v1",
        "materials": [
            {"name": "Cement", "unit": "kg", "quantity_per_unit": 350},
            {"name": "Water", "unit": "kg", "quantity_per_unit": 180},
        ],
        "qc_rules": [{"metric": "slump", "operator": "range", "threshold": [180, 220], "unit": "mm"}],
    }
    out = normalize_spu_content(
        spu_uri="v://norm/spu/highway/bridge/bored_pile_concrete@v2024",
        title="Bored pile concrete",
        content=legacy,
    )
    assert is_spu_ultimate_content(out) is True
    assert out["identity"]["spu_uri"] == "v://norm/spu/highway/bridge/bored_pile_concrete@v2024"
    assert out["identity"]["standard_codes"] == ["GB50204-2015"]
    assert out["measure_rule"]["unit"] == "m3"
    assert out["consumption"]["quota_ref"] == "v://norm/quota/concrete-casting@v1"
    assert out["qc_gate"]["gate_refs"] == ["v://norm/gate/concrete-strength-check@v1"]
    assert out["schema_modules"] == ["Identity", "MeasureRule", "Consumption", "QCGate"]


def test_validate_spu_content_rejects_missing_modules() -> None:
    invalid = {
        "identity": {"spu_uri": "v://norm/spu/x@v1"},
        "measure_rule": {"unit": "m3"},
    }
    result = validate_spu_content(
        spu_uri="v://norm/spu/x@v1",
        title="x",
        content=invalid,
    )
    assert result["ok"] is False
    assert result["error"] == "invalid_spu_schema"
