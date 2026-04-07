"""SpecIR (standard) vs RepoIR (project instance) layering models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from services.api.domain.specir.runtime.registry import get_specir_object


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _to_decimal_text(value: Any, default: str = "0") -> str:
    text = _to_text(value, default).strip() or default
    try:
        return format(Decimal(text).normalize(), "f")
    except (InvalidOperation, ValueError):
        return default


@dataclass(slots=True)
class StandardSPU:
    spu_uri: str
    name: str
    unit: str
    category: str
    norm_refs: list[str] = field(default_factory=list)
    qc_gates: list[dict[str, Any]] = field(default_factory=list)
    consumption_rates: dict[str, Any] = field(default_factory=dict)
    version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProjectBOQItem:
    boq_v_uri: str
    boq_item_id: str
    description: str
    quantity: str
    unit: str
    bridge_uri: str = ""
    ref_spu_uri: str = ""
    ref_quota_uri: str = ""
    ref_meter_rule_uri: str = ""
    custom_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_project_boq_item_ref(
    *,
    boq_v_uri: str,
    boq_item_id: str,
    description: str,
    quantity: Any,
    unit: str,
    bridge_uri: str = "",
    ref_spu_uri: str = "",
    ref_quota_uri: str = "",
    ref_meter_rule_uri: str = "",
    custom_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = ProjectBOQItem(
        boq_v_uri=_to_text(boq_v_uri).strip(),
        boq_item_id=_to_text(boq_item_id).strip(),
        description=_to_text(description).strip(),
        quantity=_to_decimal_text(quantity),
        unit=_to_text(unit).strip(),
        bridge_uri=_to_text(bridge_uri).strip(),
        ref_spu_uri=_to_text(ref_spu_uri).strip(),
        ref_quota_uri=_to_text(ref_quota_uri).strip(),
        ref_meter_rule_uri=_to_text(ref_meter_rule_uri).strip(),
        custom_params=_as_dict(custom_params),
    )
    return item.to_dict()


def resolve_standard_spu_snapshot(
    *,
    sb: Any,
    ref_spu_uri: str,
) -> dict[str, Any]:
    spu_uri = _to_text(ref_spu_uri).strip()
    if not spu_uri:
        return {}
    if sb is None:
        return {
            "spu_uri": spu_uri,
            "name": spu_uri.rstrip("/").split("/")[-1].split("@")[0],
            "unit": "",
            "category": "spu",
            "norm_refs": [],
            "version": spu_uri.split("@")[-1] if "@" in spu_uri else "v1",
        }
    row = get_specir_object(sb=sb, uri=spu_uri)
    if not bool(row.get("ok")):
        return {
            "spu_uri": spu_uri,
            "name": spu_uri.rstrip("/").split("/")[-1].split("@")[0],
            "unit": "",
            "category": "spu",
            "norm_refs": [],
            "version": spu_uri.split("@")[-1] if "@" in spu_uri else "v1",
            "status": "missing_in_registry",
        }
    content = _as_dict(row.get("content"))
    identity = _as_dict(content.get("identity"))
    measure_rule = _as_dict(content.get("measure_rule"))
    qc_gate = _as_dict(content.get("qc_gate"))
    consumption = _as_dict(content.get("consumption"))
    snapshot = StandardSPU(
        spu_uri=spu_uri,
        name=_to_text(row.get("title") or identity.get("name") or "").strip(),
        unit=_to_text(identity.get("unit") or measure_rule.get("unit") or "").strip(),
        category=_to_text(identity.get("category") or "spu").strip(),
        norm_refs=[_to_text(x).strip() for x in _as_list(identity.get("norm_refs")) if _to_text(x).strip()],
        qc_gates=[item for item in _as_list(qc_gate.get("gate_rules")) if isinstance(item, dict)],
        consumption_rates=_as_dict(consumption.get("materials")),
        version=_to_text(identity.get("version") or row.get("uri", "").split("@")[-1] or "v1").strip(),
    )
    payload = snapshot.to_dict()
    payload["status"] = _to_text(row.get("status") or "active").strip()
    return payload


__all__ = [
    "ProjectBOQItem",
    "StandardSPU",
    "build_project_boq_item_ref",
    "resolve_standard_spu_snapshot",
]

