"""Curated full SPU library for QCSpec on top of SpecIR."""

from __future__ import annotations

from typing import Any

from services.api.domain.specir.runtime.registry import ensure_specir_object, upsert_specir_object
from services.api.domain.specir.runtime.spu_schema import build_spu_ultimate_content


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _spu(uri: str, title: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "uri": uri,
        "kind": "spu",
        "title": title,
        "content": build_spu_ultimate_content(spu_uri=uri, title=title, content=payload),
    }


BUILTIN_QCSPEC_FULL_SPU_LIBRARY: list[dict[str, Any]] = [
    _spu(
        "v://norm/spu/highway/bridge/bored_pile_concrete@v2024",
        "Bored pile concrete casting",
        {
            "industry": "Highway",
            "standard_codes": ["GB50204-2015", "JTG/T 3650-2020"],
            "unit": "m3",
            "measure_statement": "Use design section area * effective pile length; over-pour not payable.",
            "measure_operator": "design-volume-effective-length",
            "measure_expression": "design_section_area * effective_length",
            "measure_exclusions": ["over-pour-not-payable"],
            "meter_rule_ref": "v://norm/meter-rule/by-volume@v1",
            "quota_ref": "v://norm/quota/concrete-casting@v1",
            "gate_refs": ["v://norm/gate/concrete-strength-check@v1"],
            "materials": [
                {"code": "MAT-CEM", "name": "Cement", "unit": "kg", "quantity_per_unit": 350.0},
                {"code": "MAT-WAT", "name": "Water", "unit": "kg", "quantity_per_unit": 180.0},
            ],
            "machinery": [{"code": "MAC-PUMP", "name": "Concrete pump shift", "unit": "shift", "quantity_per_unit": 0.05}],
            "qc_rules": [
                {"metric": "slump", "operator": "range", "threshold": [180, 220], "unit": "mm"},
                {"metric": "pile-position-offset", "operator": "<=", "threshold": 50, "unit": "mm"},
            ],
        },
    ),
    _spu(
        "v://norm/spu/highway/bridge/rebar_processing_install@v2024",
        "Rebar processing and installation",
        {
            "industry": "Highway",
            "standard_codes": ["GB50204-2015"],
            "unit": "t",
            "measure_statement": "Use approved net weight by weighing records.",
            "measure_operator": "weight-net",
            "measure_expression": "quantity_ton",
            "meter_rule_ref": "v://norm/meter-rule/by-weight@v1",
            "quota_ref": "v://norm/quota/rebar-processing@v1",
            "gate_refs": [
                "v://norm/gate/rebar-diameter-check@v1",
                "v://norm/gate/rebar-spacing-check@v1",
            ],
            "materials": [{"code": "MAT-REB", "name": "Rebar", "unit": "t", "quantity_per_unit": 1.0}],
            "qc_rules": [{"metric": "spacing", "operator": "range", "threshold": [-10, 10], "unit": "mm"}],
        },
    ),
    _spu(
        "v://norm/spu/highway/bridge/pier_column_concrete@v2024",
        "Pier column concrete",
        {
            "industry": "Highway",
            "standard_codes": ["GB50204-2015"],
            "unit": "m3",
            "measure_statement": "Use approved cast volume from geometric dimensions.",
            "measure_operator": "geometry-volume",
            "measure_expression": "section_area * height",
            "meter_rule_ref": "v://norm/meter-rule/by-volume@v1",
            "quota_ref": "v://norm/quota/concrete-casting@v1",
            "gate_refs": ["v://norm/gate/concrete-strength-check@v1"],
            "materials": [{"code": "MAT-CON", "name": "Concrete", "unit": "m3", "quantity_per_unit": 1.0}],
            "qc_rules": [{"metric": "compressive-strength", "operator": ">=", "threshold": 30, "unit": "MPa"}],
        },
    ),
    _spu(
        "v://norm/spu/highway/bridge/cap_beam_casting@v2024",
        "Cap beam casting",
        {
            "industry": "Highway",
            "standard_codes": ["GB50204-2015"],
            "unit": "m3",
            "measure_statement": "Use design beam volume with approved drawing dimensions.",
            "measure_operator": "design-beam-volume",
            "measure_expression": "beam_length * beam_width * beam_height",
            "meter_rule_ref": "v://norm/meter-rule/by-volume@v1",
            "quota_ref": "v://norm/quota/concrete-casting@v1",
            "gate_refs": ["v://norm/gate/concrete-strength-check@v1"],
            "materials": [{"code": "MAT-CON", "name": "Concrete", "unit": "m3", "quantity_per_unit": 1.0}],
            "qc_rules": [{"metric": "cover-thickness", "operator": ">=", "threshold": 35, "unit": "mm"}],
        },
    ),
    _spu(
        "v://norm/spu/highway/bridge/box_girder_precast_erect@v2024",
        "Precast box girder erection",
        {
            "industry": "Highway",
            "standard_codes": ["JTG/T F50-2011"],
            "unit": "piece",
            "measure_statement": "Count accepted girder pieces erected and aligned.",
            "measure_operator": "accepted-piece-count",
            "measure_expression": "accepted_piece_count",
            "meter_rule_ref": "v://norm/meter-rule/contract-payment@v1",
            "quota_ref": "v://norm/quota/contract-payment@v1",
            "gate_refs": [],
            "materials": [],
            "machinery": [{"code": "MAC-CRANE", "name": "Launching crane shift", "unit": "shift", "quantity_per_unit": 0.2}],
            "qc_rules": [{"metric": "line-alignment-offset", "operator": "<=", "threshold": 10, "unit": "mm"}],
        },
    ),
    _spu(
        "v://norm/spu/highway/subgrade/compaction_fill@v2024",
        "Subgrade compaction fill",
        {
            "industry": "Highway",
            "standard_codes": ["JTG F80/1-2017"],
            "unit": "m3",
            "measure_statement": "Use compacted fill volume by accepted layer geometry.",
            "measure_operator": "compacted-fill-volume",
            "measure_expression": "layer_area * compacted_thickness",
            "meter_rule_ref": "v://norm/meter-rule/by-volume@v1",
            "quota_ref": "v://norm/quota/pavement-laying@v1",
            "gate_refs": [],
            "materials": [{"code": "MAT-FILL", "name": "Fill material", "unit": "m3", "quantity_per_unit": 1.0}],
            "qc_rules": [{"metric": "compaction-degree", "operator": ">=", "threshold": 0.95, "unit": "ratio"}],
        },
    ),
    _spu(
        "v://norm/spu/highway/pavement/asphalt_surface_course@v2024",
        "Asphalt surface course",
        {
            "industry": "Highway",
            "standard_codes": ["JTG F40-2004", "JTG F80/1-2017"],
            "unit": "m2",
            "measure_statement": "Use accepted paving area multiplied by approved thickness factors.",
            "measure_operator": "asphalt-area-thickness",
            "measure_expression": "paving_area * thickness_factor",
            "meter_rule_ref": "v://norm/meter-rule/by-area@v1",
            "quota_ref": "v://norm/quota/pavement-laying@v1",
            "gate_refs": ["v://norm/gate/pavement-flatness-check@v1"],
            "materials": [{"code": "MAT-ASP", "name": "Asphalt mix", "unit": "t", "quantity_per_unit": 0.12}],
            "qc_rules": [
                {"metric": "flatness", "operator": "<=", "threshold": 3.0, "unit": "mm"},
                {"metric": "void-ratio", "operator": "range", "threshold": [3.0, 6.0], "unit": "%"},
            ],
        },
    ),
    _spu(
        "v://norm/spu/highway/drainage/side_ditch_masonry@v2024",
        "Side ditch masonry",
        {
            "industry": "Highway",
            "standard_codes": ["JTG/T 3610-2019"],
            "unit": "m",
            "measure_statement": "Use accepted side ditch centerline length.",
            "measure_operator": "ditch-length",
            "measure_expression": "accepted_centerline_length",
            "meter_rule_ref": "v://norm/meter-rule/contract-payment@v1",
            "quota_ref": "v://norm/quota/landscape-work@v1",
            "gate_refs": [],
            "materials": [{"code": "MAT-MAS", "name": "Masonry block", "unit": "m3", "quantity_per_unit": 0.18}],
            "qc_rules": [{"metric": "cross-slope", "operator": "range", "threshold": [1.0, 3.0], "unit": "%"}],
        },
    ),
    _spu(
        "v://norm/spu/highway/safety/guardrail_installation@v2024",
        "Guardrail installation",
        {
            "industry": "Highway",
            "standard_codes": ["JT/T 281-2007"],
            "unit": "m",
            "measure_statement": "Use accepted installed guardrail length.",
            "measure_operator": "guardrail-length",
            "measure_expression": "accepted_length",
            "meter_rule_ref": "v://norm/meter-rule/contract-payment@v1",
            "quota_ref": "v://norm/quota/contract-payment@v1",
            "gate_refs": [],
            "materials": [{"code": "MAT-GUA", "name": "Guardrail beam", "unit": "m", "quantity_per_unit": 1.0}],
            "qc_rules": [{"metric": "post-spacing", "operator": "range", "threshold": [1.9, 2.1], "unit": "m"}],
        },
    ),
]


def list_builtin_qcspec_full_spu_library() -> dict[str, Any]:
    return {
        "ok": True,
        "count": len(BUILTIN_QCSPEC_FULL_SPU_LIBRARY),
        "items": [dict(item) for item in BUILTIN_QCSPEC_FULL_SPU_LIBRARY],
    }


def seed_builtin_qcspec_full_spu_library(
    *,
    sb: Any,
    overwrite: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    op = upsert_specir_object if overwrite else ensure_specir_object
    common_metadata = {"source": "builtin_qcspec_full_spu_library", **_as_dict(metadata)}
    for item in BUILTIN_QCSPEC_FULL_SPU_LIBRARY:
        uri = _to_text(item.get("uri")).strip()
        if not uri:
            continue
        try:
            out = op(
                sb=sb,
                uri=uri,
                kind="spu",
                title=_to_text(item.get("title")).strip(),
                content=_as_dict(item.get("content")),
                status="active",
                metadata={**common_metadata, "uri": uri},
            )
            if bool(out.get("ok")):
                saved.append({"uri": uri, "kind": "spu"})
            else:
                errors.append({"uri": uri, "kind": "spu", "error": _to_text(out.get("error") or "unknown").strip()})
        except Exception as exc:
            errors.append({"uri": uri, "kind": "spu", "error": f"{exc.__class__.__name__}: {exc}"})
    return {
        "ok": len(errors) == 0,
        "saved_count": len(saved),
        "error_count": len(errors),
        "saved": saved,
        "errors": errors,
    }


__all__ = [
    "BUILTIN_QCSPEC_FULL_SPU_LIBRARY",
    "list_builtin_qcspec_full_spu_library",
    "seed_builtin_qcspec_full_spu_library",
]
