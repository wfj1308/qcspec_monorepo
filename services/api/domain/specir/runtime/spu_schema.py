"""Ultimate SPU schema for SpecIR standard-library objects.

Defines the production-grade protocol object with four mandatory modules:
- Identity
- MeasureRule
- Consumption
- QCGate
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


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


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_to_text(item).strip() for item in value if _to_text(item).strip()]


def _uri_path_segments(uri: str) -> list[str]:
    normalized = _to_text(uri).strip()
    if not normalized:
        return []
    no_scheme = normalized.replace("v://", "", 1)
    before_version = no_scheme.split("@", 1)[0]
    return [seg.strip() for seg in before_version.split("/") if seg.strip()]


def _infer_category_path_from_uri(uri: str) -> list[str]:
    segs = _uri_path_segments(uri)
    if not segs:
        return []
    if "spu" in segs:
        idx = segs.index("spu")
        return segs[idx + 1 :]
    return segs


def _infer_industry(category_path: list[str]) -> str:
    if not category_path:
        return ""
    head = _to_text(category_path[0]).strip().lower()
    mapping = {
        "highway": "公路",
        "road": "公路",
        "bridge": "桥梁",
        "municipal": "市政",
        "building": "房建",
        "housing": "房建",
        "water": "水利",
        "railway": "铁路",
    }
    return mapping.get(head, head)


class IdentityModule(BaseModel):
    model_config = ConfigDict(extra="allow")

    spu_uri: str
    sovereignty_uri: str = "v://norm"
    industry: str = ""
    standard_codes: list[str] = Field(default_factory=list)
    category_path: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    authority_refs: list[str] = Field(default_factory=list)

    @field_validator("spu_uri", "sovereignty_uri", mode="before")
    @classmethod
    def _trim_uri(cls, v: Any) -> str:
        return _to_text(v).strip()

    @field_validator("standard_codes", "category_path", "aliases", "authority_refs", mode="before")
    @classmethod
    def _normalize_str_list(cls, v: Any) -> list[str]:
        return _as_str_list(v)


class MeasureOperator(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str = ""
    expression: str = ""
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    exclusion_rules: list[str] = Field(default_factory=list)

    @field_validator("key", "expression", "description", mode="before")
    @classmethod
    def _trim_text(cls, v: Any) -> str:
        return _to_text(v).strip()

    @field_validator("exclusion_rules", mode="before")
    @classmethod
    def _normalize_exclusions(cls, v: Any) -> list[str]:
        return _as_str_list(v)


class MeasureRuleModule(BaseModel):
    model_config = ConfigDict(extra="allow")

    unit: str
    payable_unit: str = ""
    meter_rule_ref: str = ""
    statement: str = ""
    algorithm: MeasureOperator = Field(default_factory=MeasureOperator)
    settlement_clauses: list[str] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("unit", "payable_unit", "meter_rule_ref", "statement", mode="before")
    @classmethod
    def _trim_text(cls, v: Any) -> str:
        return _to_text(v).strip()

    @field_validator("settlement_clauses", mode="before")
    @classmethod
    def _normalize_clauses(cls, v: Any) -> list[str]:
        return _as_str_list(v)


class ConsumptionLine(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str = ""
    name: str
    unit: str
    quantity_per_unit: float = Field(default=0.0, ge=0.0)
    remark: str = ""
    source_ref: str = ""

    @field_validator("code", "name", "unit", "remark", "source_ref", mode="before")
    @classmethod
    def _trim_text(cls, v: Any) -> str:
        return _to_text(v).strip()


class ConsumptionModule(BaseModel):
    model_config = ConfigDict(extra="allow")

    unit_basis: str = ""
    quota_ref: str = ""
    materials: list[ConsumptionLine] = Field(default_factory=list)
    machinery: list[ConsumptionLine] = Field(default_factory=list)
    labor: list[ConsumptionLine] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("unit_basis", "quota_ref", mode="before")
    @classmethod
    def _trim_text(cls, v: Any) -> str:
        return _to_text(v).strip()

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, v: Any) -> list[str]:
        return _as_str_list(v)


class QCGateRule(BaseModel):
    model_config = ConfigDict(extra="allow")

    metric: str
    operator: str = ""
    threshold: Any = None
    unit: str = ""
    spec_ref: str = ""
    gate_ref: str = ""
    sample_frequency: str = ""
    required: bool = True

    @field_validator("metric", "operator", "unit", "spec_ref", "gate_ref", "sample_frequency", mode="before")
    @classmethod
    def _trim_text(cls, v: Any) -> str:
        return _to_text(v).strip()


class QCGateModule(BaseModel):
    model_config = ConfigDict(extra="allow")

    strategy: str = "all_pass"
    fail_action: str = "trigger_review_trip"
    gate_refs: list[str] = Field(default_factory=list)
    rules: list[QCGateRule] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)

    @field_validator("strategy", "fail_action", mode="before")
    @classmethod
    def _trim_text(cls, v: Any) -> str:
        return _to_text(v).strip()

    @field_validator("gate_refs", "checklist", mode="before")
    @classmethod
    def _normalize_str_list(cls, v: Any) -> list[str]:
        return _as_str_list(v)


class SPUUltimateSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    schema_id: str = Field(default="qcspec.specir.spu.ultimate", alias="schema")
    schema_version: str = "1.0.0"
    identity: IdentityModule
    measure_rule: MeasureRuleModule
    consumption: ConsumptionModule
    qc_gate: QCGateModule
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_id", "schema_version", mode="before")
    @classmethod
    def _trim_text(cls, v: Any) -> str:
        return _to_text(v).strip()


def is_spu_ultimate_content(content: Any) -> bool:
    payload = _as_dict(content)
    return all(key in payload for key in ("identity", "measure_rule", "consumption", "qc_gate"))


def _coerce_legacy_qc_rules(raw_rules: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_rules, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw_rules:
        row = _as_dict(item)
        metric = _to_text(row.get("metric") or row.get("field") or row.get("name")).strip()
        if not metric:
            continue
        out.append(
            {
                "metric": metric,
                "operator": _to_text(row.get("operator") or row.get("op")).strip(),
                "threshold": row.get("threshold"),
                "unit": _to_text(row.get("unit")).strip(),
                "spec_ref": _to_text(row.get("spec_ref") or row.get("spec_uri")).strip(),
                "gate_ref": _to_text(row.get("gate_ref")).strip(),
                "sample_frequency": _to_text(row.get("sample_frequency") or row.get("frequency")).strip(),
                "required": bool(row.get("required", True)),
            }
        )
    return out


def _coerce_legacy_consumption_lines(raw_lines: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_lines, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw_lines:
        row = _as_dict(item)
        name = _to_text(row.get("name") or row.get("material") or row.get("label")).strip()
        unit = _to_text(row.get("unit")).strip()
        if not name or not unit:
            continue
        quantity_raw = row.get("quantity_per_unit", row.get("qty_per_unit", row.get("qty", 0)))
        try:
            quantity = float(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0.0
        out.append(
            {
                "code": _to_text(row.get("code")).strip(),
                "name": name,
                "unit": unit,
                "quantity_per_unit": max(quantity, 0.0),
                "remark": _to_text(row.get("remark")).strip(),
                "source_ref": _to_text(row.get("source_ref")).strip(),
            }
        )
    return out


def build_spu_ultimate_content(
    *,
    spu_uri: str,
    title: str = "",
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    legacy = _as_dict(content)
    category_path = _as_str_list(legacy.get("category_path")) or _infer_category_path_from_uri(spu_uri)
    unit = _to_text(legacy.get("unit") or _as_dict(legacy.get("measure_rule")).get("unit")).strip()
    gate_refs = _as_str_list(legacy.get("gate_refs"))
    quota_ref = _to_text(legacy.get("quota_ref")).strip()
    meter_rule_ref = _to_text(legacy.get("meter_rule_ref")).strip()
    standard_codes = _as_str_list(legacy.get("norm_refs") or legacy.get("standard_codes"))
    identity_block = {
        "spu_uri": _to_text(spu_uri).strip(),
        "sovereignty_uri": _to_text(legacy.get("sovereignty_uri") or "v://norm").strip(),
        "industry": _to_text(legacy.get("industry") or _infer_industry(category_path)).strip(),
        "standard_codes": standard_codes,
        "category_path": category_path,
        "aliases": _as_str_list(legacy.get("aliases")),
        "authority_refs": _as_str_list(legacy.get("authority_refs")),
    }
    measure_rule = _as_dict(legacy.get("measure_rule"))
    algorithm = _as_dict(measure_rule.get("algorithm"))
    measure_rule_block = {
        "unit": unit,
        "payable_unit": _to_text(measure_rule.get("payable_unit") or unit).strip(),
        "meter_rule_ref": _to_text(measure_rule.get("meter_rule_ref") or meter_rule_ref).strip(),
        "statement": _to_text(measure_rule.get("statement") or legacy.get("measure_statement")).strip(),
        "algorithm": {
            "key": _to_text(algorithm.get("key") or legacy.get("measure_operator")).strip(),
            "expression": _to_text(algorithm.get("expression") or legacy.get("measure_expression")).strip(),
            "description": _to_text(algorithm.get("description")).strip(),
            "parameters": _as_dict(algorithm.get("parameters")),
            "exclusion_rules": _as_str_list(algorithm.get("exclusion_rules") or legacy.get("measure_exclusions")),
        },
        "settlement_clauses": _as_str_list(measure_rule.get("settlement_clauses") or legacy.get("settlement_clauses")),
        "examples": measure_rule.get("examples") if isinstance(measure_rule.get("examples"), list) else [],
    }
    consumption = _as_dict(legacy.get("consumption"))
    consumption_block = {
        "unit_basis": _to_text(consumption.get("unit_basis") or unit).strip(),
        "quota_ref": _to_text(consumption.get("quota_ref") or quota_ref).strip(),
        "materials": _coerce_legacy_consumption_lines(consumption.get("materials") or legacy.get("materials")),
        "machinery": _coerce_legacy_consumption_lines(consumption.get("machinery") or legacy.get("machinery")),
        "labor": _coerce_legacy_consumption_lines(consumption.get("labor") or legacy.get("labor")),
        "notes": _as_str_list(consumption.get("notes") or legacy.get("consumption_notes")),
    }
    qc_gate = _as_dict(legacy.get("qc_gate"))
    qc_gate_block = {
        "strategy": _to_text(qc_gate.get("strategy") or legacy.get("execution_strategy") or "all_pass").strip(),
        "fail_action": _to_text(qc_gate.get("fail_action") or legacy.get("fail_action") or "trigger_review_trip").strip(),
        "gate_refs": _as_str_list(qc_gate.get("gate_refs") or gate_refs),
        "rules": _coerce_legacy_qc_rules(qc_gate.get("rules") or legacy.get("qc_rules")),
        "checklist": _as_str_list(qc_gate.get("checklist")),
    }

    raw = {
        "schema": _to_text(legacy.get("schema") or "qcspec.specir.spu.ultimate").strip(),
        "schema_version": _to_text(legacy.get("schema_version") or "1.0.0").strip(),
        "identity": identity_block,
        "measure_rule": measure_rule_block,
        "consumption": consumption_block,
        "qc_gate": qc_gate_block,
        "extensions": _as_dict(legacy.get("extensions")),
    }
    model = SPUUltimateSchema.model_validate(raw)
    normalized = model.model_dump(mode="python", by_alias=True)

    # Compatibility aliases for existing runtime readers during migration.
    normalized["label"] = _to_text(legacy.get("label") or title).strip()
    normalized["unit"] = model.measure_rule.unit
    normalized["norm_refs"] = list(model.identity.standard_codes)
    normalized["gate_refs"] = list(model.qc_gate.gate_refs)
    normalized["quota_ref"] = model.consumption.quota_ref
    normalized["meter_rule_ref"] = model.measure_rule.meter_rule_ref
    normalized["quota_refs"] = [model.consumption.quota_ref] if model.consumption.quota_ref else []
    normalized["meter_rule_refs"] = [model.measure_rule.meter_rule_ref] if model.measure_rule.meter_rule_ref else []
    normalized["schema_modules"] = ["Identity", "MeasureRule", "Consumption", "QCGate"]
    return normalized


def normalize_spu_content(
    *,
    spu_uri: str,
    title: str = "",
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = _as_dict(content)
    if is_spu_ultimate_content(raw):
        model = SPUUltimateSchema.model_validate(raw)
        normalized = model.model_dump(mode="python", by_alias=True)
        normalized["label"] = _to_text(raw.get("label") or title).strip()
        normalized["unit"] = model.measure_rule.unit
        normalized["norm_refs"] = list(model.identity.standard_codes)
        normalized["gate_refs"] = list(model.qc_gate.gate_refs)
        normalized["quota_ref"] = model.consumption.quota_ref
        normalized["meter_rule_ref"] = model.measure_rule.meter_rule_ref
        normalized["quota_refs"] = [model.consumption.quota_ref] if model.consumption.quota_ref else []
        normalized["meter_rule_refs"] = [model.measure_rule.meter_rule_ref] if model.measure_rule.meter_rule_ref else []
        normalized["schema_modules"] = ["Identity", "MeasureRule", "Consumption", "QCGate"]
        return normalized
    return build_spu_ultimate_content(spu_uri=spu_uri, title=title, content=raw)


def validate_spu_content(
    *,
    spu_uri: str,
    title: str = "",
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        raw = _as_dict(content)
        module_keys = ("identity", "measure_rule", "consumption", "qc_gate")
        present = [key for key in module_keys if key in raw]
        if present and len(present) != len(module_keys):
            return {
                "ok": False,
                "error": "invalid_spu_schema",
                "detail": [{"msg": "partial_module_blocks", "present_modules": present}],
            }
        normalized = normalize_spu_content(spu_uri=spu_uri, title=title, content=content)
        return {"ok": True, "content": normalized}
    except ValidationError as exc:
        return {
            "ok": False,
            "error": "invalid_spu_schema",
            "detail": exc.errors(include_url=False),
        }


__all__ = [
    "SPUUltimateSchema",
    "build_spu_ultimate_content",
    "is_spu_ultimate_content",
    "normalize_spu_content",
    "validate_spu_content",
]
