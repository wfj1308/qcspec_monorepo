"""Component cost aggregation for materials, consumables, depreciation and labor."""

from __future__ import annotations

from typing import Any

from services.api.domain.boqpeg.models import CostBreakdown
from services.api.domain.boqpeg.runtime.consumption_trip import (
    sum_consumable_trips,
    sum_formwork_depreciation,
)
from services.api.domain.boqpeg.runtime.equipment import sum_equipment_trip_cost
from services.api.domain.boqpeg.runtime.material_utxo import summarize_component_material_cost


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _round6(value: float) -> float:
    return round(float(value or 0.0), 6)


def _sum_component_labor_from_settlements(*, sb: Any, component_uri: str) -> tuple[float, list[str]]:
    if sb is None:
        return 0.0, []
    rows = sb.table("railpact_settlements").select("*").order("settled_at", desc=False).limit(50000).execute().data or []
    total = 0.0
    refs: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        metadata = _as_dict(row.get("metadata"))
        if _to_text(metadata.get("component_uri")).strip().rstrip("/") != _to_text(component_uri).strip().rstrip("/"):
            continue
        if _to_text(metadata.get("kind")).strip() == "equipment_trip_machine":
            continue
        total += float(row.get("amount") or 0.0)
        trip_uri = _to_text(row.get("trip_uri")).strip()
        if trip_uri:
            refs.append(trip_uri)
    return _round6(total), refs


def calculate_component_cost(*, sb: Any, component_uri: str, overhead_ratio: float = 0.08) -> CostBreakdown:
    c_uri = _to_text(component_uri).strip().rstrip("/")
    direct = summarize_component_material_cost(sb=sb, component_uri=c_uri)
    direct_materials = float(direct.get("total_material_cost") or 0.0)
    direct_refs = []
    for item in direct.get("materials") or []:
        if not isinstance(item, dict):
            continue
        for record in item.get("records") or []:
            if not isinstance(record, dict):
                continue
            for key in ("utxo_id", "inspection_uri", "iqc_uri"):
                value = _to_text(record.get(key)).strip()
                if value:
                    direct_refs.append(value)

    consumables = sum_consumable_trips(sb=sb, component_uri=c_uri)
    consumables_cost = float(consumables.get("total_consumables_cost") or 0.0)

    depreciation = sum_formwork_depreciation(sb=sb, component_uri=c_uri)
    depreciation_cost = float(depreciation.get("total_depreciation_cost") or 0.0)

    equipment_cost_data = sum_equipment_trip_cost(sb=sb, component_uri=c_uri)
    equipment_cost = float(equipment_cost_data.get("total_equipment_cost") or 0.0)

    labor_cost, labor_refs = _sum_component_labor_from_settlements(sb=sb, component_uri=c_uri)

    subtotal = direct_materials + consumables_cost + depreciation_cost + equipment_cost + labor_cost
    overhead = max(float(overhead_ratio), 0.0) * subtotal
    total = subtotal + overhead

    proof_refs = [
        *direct_refs,
        *(_to_text(x).strip() for x in consumables.get("proof_refs") or []),
        *(_to_text(x).strip() for x in depreciation.get("proof_refs") or []),
        *(_to_text(x).strip() for x in equipment_cost_data.get("proof_refs") or []),
        *labor_refs,
    ]
    # unique and keep order
    dedup: list[str] = []
    for item in proof_refs:
        if item and item not in dedup:
            dedup.append(item)

    return CostBreakdown(
        component_uri=c_uri,
        direct_materials=_round6(direct_materials),
        consumables=_round6(consumables_cost),
        equipment_depreciation=_round6(depreciation_cost),
        equipment_cost=_round6(equipment_cost),
        labor=_round6(labor_cost),
        overhead=_round6(overhead),
        total=_round6(total),
        proof_refs=dedup,
    )


__all__ = ["calculate_component_cost"]
