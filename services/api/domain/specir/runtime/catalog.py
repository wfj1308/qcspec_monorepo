"""Built-in SpecIR baseline catalog and seeding helpers."""

from __future__ import annotations

from typing import Any

from services.api.domain.specir.runtime.registry import (
    ensure_specir_object,
    upsert_specir_object,
)
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


BUILTIN_QCSPEC_SPECIR_CATALOG: list[dict[str, Any]] = [
    {
        "uri": "v://norm/spec-rule/gb50204-rebar-diameter@v1",
        "kind": "spec_rule",
        "title": "GB50204 rebar diameter tolerance",
        "content": {
            "authority": "GB50204-2015",
            "rule_code": "5.3.2",
            "operator": "range",
            "unit": "mm",
            "threshold": {"default": [-2, 2], "main_beam": [-1, 1], "pier": [-2, 2]},
        },
    },
    {
        "uri": "v://norm/spec-rule/gb50204-rebar-spacing@v1",
        "kind": "spec_rule",
        "title": "GB50204 rebar spacing tolerance",
        "content": {
            "authority": "GB50204-2015",
            "rule_code": "5.3.3",
            "operator": "range",
            "unit": "mm",
            "threshold": {"default": [-10, 10], "main_beam": [-8, 8], "pier": [-10, 10]},
        },
    },
    {
        "uri": "v://norm/spec-rule/gb50204-concrete-strength@v1",
        "kind": "spec_rule",
        "title": "GB50204 concrete strength",
        "content": {
            "authority": "GB50204-2015",
            "rule_code": "7.4",
            "operator": ">=",
            "unit": "MPa",
            "threshold": {"default": 30},
        },
    },
    {
        "uri": "v://norm/spec-rule/jtgf80-pavement-flatness@v1",
        "kind": "spec_rule",
        "title": "JTG F80 pavement flatness",
        "content": {
            "authority": "JTG F80/1-2017",
            "rule_code": "10.2",
            "operator": "<=",
            "unit": "mm",
            "threshold": {"default": 3.0},
        },
    },
    {
        "uri": "v://norm/meter-rule/by-weight@v1",
        "kind": "meter_rule",
        "title": "By weight",
        "content": {"unit": "t", "expression": "quantity_ton"},
    },
    {
        "uri": "v://norm/meter-rule/by-volume@v1",
        "kind": "meter_rule",
        "title": "By volume",
        "content": {"unit": "m3", "expression": "length*width*height"},
    },
    {
        "uri": "v://norm/meter-rule/by-area@v1",
        "kind": "meter_rule",
        "title": "By area",
        "content": {"unit": "m2", "expression": "length*width"},
    },
    {
        "uri": "v://norm/meter-rule/contract-payment@v1",
        "kind": "meter_rule",
        "title": "Contract payment metering",
        "content": {"unit": "CNY", "expression": "claimed_amount"},
    },
    {
        "uri": "v://norm/meter-rule/landscape-work@v1",
        "kind": "meter_rule",
        "title": "Landscape metering",
        "content": {"unit": "m2", "expression": "length*width"},
    },
    {
        "uri": "v://norm/quota/rebar-processing@v1",
        "kind": "quota",
        "title": "Rebar processing quota",
        "content": {"unit": "t", "labor_cost_per_unit": 210.0},
    },
    {
        "uri": "v://norm/quota/concrete-casting@v1",
        "kind": "quota",
        "title": "Concrete casting quota",
        "content": {"unit": "m3", "labor_cost_per_unit": 120.0},
    },
    {
        "uri": "v://norm/quota/pavement-laying@v1",
        "kind": "quota",
        "title": "Pavement laying quota",
        "content": {"unit": "m2", "labor_cost_per_unit": 38.0},
    },
    {
        "uri": "v://norm/quota/contract-payment@v1",
        "kind": "quota",
        "title": "Contract payment quota",
        "content": {"unit": "CNY", "labor_cost_per_unit": 0.0},
    },
    {
        "uri": "v://norm/quota/landscape-work@v1",
        "kind": "quota",
        "title": "Landscape quota",
        "content": {"unit": "m2", "labor_cost_per_unit": 30.0},
    },
    {
        "uri": "v://norm/gate/rebar-diameter-check@v1",
        "kind": "gate",
        "title": "Rebar diameter gate",
        "content": {"strategy": "all_pass", "spec_rule_refs": ["v://norm/spec-rule/gb50204-rebar-diameter@v1"]},
    },
    {
        "uri": "v://norm/gate/rebar-spacing-check@v1",
        "kind": "gate",
        "title": "Rebar spacing gate",
        "content": {"strategy": "all_pass", "spec_rule_refs": ["v://norm/spec-rule/gb50204-rebar-spacing@v1"]},
    },
    {
        "uri": "v://norm/gate/concrete-strength-check@v1",
        "kind": "gate",
        "title": "Concrete strength gate",
        "content": {"strategy": "all_pass", "spec_rule_refs": ["v://norm/spec-rule/gb50204-concrete-strength@v1"]},
    },
    {
        "uri": "v://norm/gate/pavement-flatness-check@v1",
        "kind": "gate",
        "title": "Pavement flatness gate",
        "content": {"strategy": "all_pass", "spec_rule_refs": ["v://norm/spec-rule/jtgf80-pavement-flatness@v1"]},
    },
    {
        "uri": "v://norm/spu/rebar-processing@v1",
        "kind": "spu",
        "title": "Rebar processing and installation",
        "content": build_spu_ultimate_content(
            spu_uri="v://norm/spu/rebar-processing@v1",
            title="Rebar processing and installation",
            content={
                "industry": "Highway",
                "norm_refs": ["GB50204-2015"],
                "unit": "t",
                "measure_statement": "Meter by net rebar weight.",
                "measure_operator": "weight-net",
                "measure_expression": "quantity_ton",
                "gate_refs": [
                    "v://norm/gate/rebar-diameter-check@v1",
                    "v://norm/gate/rebar-spacing-check@v1",
                ],
                "quota_ref": "v://norm/quota/rebar-processing@v1",
                "meter_rule_ref": "v://norm/meter-rule/by-weight@v1",
                "materials": [{"name": "Rebar", "unit": "t", "quantity_per_unit": 1.0}],
            },
        ),
    },
    {
        "uri": "v://norm/spu/pier-concrete-casting@v1",
        "kind": "spu",
        "title": "Bridge pier concrete casting",
        "content": build_spu_ultimate_content(
            spu_uri="v://norm/spu/pier-concrete-casting@v1",
            title="Bridge pier concrete casting",
            content={
                "industry": "Highway",
                "norm_refs": ["GB50204-2015"],
                "unit": "m3",
                "measure_statement": "Volume by design section and pile length; over-pour not payable.",
                "measure_operator": "design-section-volume",
                "measure_expression": "design_area * design_length",
                "measure_exclusions": ["over-pour-not-payable"],
                "gate_refs": ["v://norm/gate/concrete-strength-check@v1"],
                "quota_ref": "v://norm/quota/concrete-casting@v1",
                "meter_rule_ref": "v://norm/meter-rule/by-volume@v1",
                "materials": [
                    {"name": "Cement", "unit": "kg", "quantity_per_unit": 350.0},
                    {"name": "Water", "unit": "kg", "quantity_per_unit": 180.0},
                ],
                "machinery": [{"name": "Concrete pump shift", "unit": "shift", "quantity_per_unit": 0.05}],
                "qc_rules": [
                    {"metric": "slump", "operator": "range", "threshold": [180, 220], "unit": "mm"},
                    {"metric": "pile-position-offset", "operator": "<=", "threshold": 50, "unit": "mm"},
                ],
            },
        ),
    },
    {
        "uri": "v://norm/spu/pavement-laying@v1",
        "kind": "spu",
        "title": "Pavement laying",
        "content": build_spu_ultimate_content(
            spu_uri="v://norm/spu/pavement-laying@v1",
            title="Pavement laying",
            content={
                "industry": "Highway",
                "norm_refs": ["JTG F80/1-2017"],
                "unit": "m2",
                "measure_statement": "Meter by designed paving area.",
                "measure_operator": "area-design",
                "measure_expression": "length * width",
                "gate_refs": ["v://norm/gate/pavement-flatness-check@v1"],
                "quota_ref": "v://norm/quota/pavement-laying@v1",
                "meter_rule_ref": "v://norm/meter-rule/by-area@v1",
            },
        ),
    },
    {
        "uri": "v://norm/spu/contract-payment@v1",
        "kind": "spu",
        "title": "Contract payment item",
        "content": build_spu_ultimate_content(
            spu_uri="v://norm/spu/contract-payment@v1",
            title="Contract payment item",
            content={
                "industry": "Highway",
                "norm_refs": ["Contract-Clauses"],
                "unit": "CNY",
                "measure_statement": "Meter by approved claimed amount.",
                "measure_operator": "contract-claim",
                "measure_expression": "claimed_amount",
                "gate_refs": [],
                "quota_ref": "v://norm/quota/contract-payment@v1",
                "meter_rule_ref": "v://norm/meter-rule/contract-payment@v1",
            },
        ),
    },
    {
        "uri": "v://norm/spu/landscape-work@v1",
        "kind": "spu",
        "title": "Landscape work",
        "content": build_spu_ultimate_content(
            spu_uri="v://norm/spu/landscape-work@v1",
            title="Landscape work",
            content={
                "industry": "Municipal",
                "norm_refs": ["Landscape-Acceptance"],
                "unit": "m2",
                "measure_statement": "Meter by planted/covered area.",
                "measure_operator": "landscape-area",
                "measure_expression": "length * width",
                "gate_refs": [],
                "quota_ref": "v://norm/quota/landscape-work@v1",
                "meter_rule_ref": "v://norm/meter-rule/landscape-work@v1",
            },
        ),
    },
]


def list_builtin_qcspec_specir_catalog() -> dict[str, Any]:
    return {
        "ok": True,
        "count": len(BUILTIN_QCSPEC_SPECIR_CATALOG),
        "items": [dict(item) for item in BUILTIN_QCSPEC_SPECIR_CATALOG],
    }


def seed_builtin_qcspec_specir_catalog(
    *,
    sb: Any,
    overwrite: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    common_metadata = {"source": "builtin_qcspec_specir_catalog", **_as_dict(metadata)}
    for item in BUILTIN_QCSPEC_SPECIR_CATALOG:
        uri = _to_text(item.get("uri") or "").strip()
        kind = _to_text(item.get("kind") or "").strip()
        if not uri or not kind:
            continue
        try:
            op = upsert_specir_object if overwrite else ensure_specir_object
            result = op(
                sb=sb,
                uri=uri,
                kind=kind,
                title=_to_text(item.get("title") or "").strip(),
                content=_as_dict(item.get("content")),
                metadata={**common_metadata, "uri": uri, "kind": kind},
                status="active",
            )
            if bool(result.get("ok")):
                saved.append({"uri": uri, "kind": kind})
            else:
                errors.append({"uri": uri, "kind": kind, "error": _to_text(result.get("error") or "unknown").strip()})
        except Exception as exc:
            errors.append({"uri": uri, "kind": kind, "error": f"{exc.__class__.__name__}: {exc}"})
    return {
        "ok": len(errors) == 0,
        "saved_count": len(saved),
        "error_count": len(errors),
        "saved": saved,
        "errors": errors,
    }


__all__ = [
    "BUILTIN_QCSPEC_SPECIR_CATALOG",
    "list_builtin_qcspec_specir_catalog",
    "seed_builtin_qcspec_specir_catalog",
]
