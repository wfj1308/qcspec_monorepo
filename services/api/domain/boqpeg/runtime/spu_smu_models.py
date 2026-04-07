"""Three-layer SPU + BOQItem + SMU model builders for BOQPeg."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
from typing import Any


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    text = _to_text(value, default).strip() or default
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _decimal_to_str(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _infer_component_type(*, boq_item_id: str, description: str) -> str:
    code = _to_text(boq_item_id).strip()
    name = _to_text(description).strip().lower()
    if "pile" in name or "桩" in name or code.startswith(("401", "402", "403")):
        return "pile"
    if "pier" in name or "墩" in name:
        return "pier"
    if "cap" in name or "承台" in name:
        return "cap"
    return "boq_item"


def _default_smu_id(project_uri: str, boq_item_id: str, bridge_uri: str) -> str:
    seed = f"{_to_text(project_uri).strip()}|{_to_text(bridge_uri).strip()}|{_to_text(boq_item_id).strip()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16].upper()
    return f"SMU-{digest}"


@dataclass(slots=True)
class SPU:
    spu_uri: str
    name: str
    category: str
    unit: str
    norm_ref: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "spu_uri": self.spu_uri,
            "name": self.name,
            "category": self.category,
            "unit": self.unit,
            "norm_ref": self.norm_ref,
            "description": self.description,
        }


@dataclass(slots=True)
class BOQItemModel:
    boq_item_id: str
    v_uri: str
    description: str
    unit: str
    boq_quantity: Decimal
    unit_price: Decimal
    total_amount: Decimal
    project_uri: str
    bridge_uri: str
    bridge_name: str
    genesis_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "boq_item_id": self.boq_item_id,
            "v_uri": self.v_uri,
            "description": self.description,
            "unit": self.unit,
            "boq_quantity": _decimal_to_str(self.boq_quantity),
            "unit_price": _decimal_to_str(self.unit_price),
            "total_amount": _decimal_to_str(self.total_amount),
            "project_uri": self.project_uri,
            "bridge_uri": self.bridge_uri,
            "bridge_name": self.bridge_name,
            "genesis_hash": self.genesis_hash,
        }


@dataclass(slots=True)
class SPUBOQMapping:
    mapping_id: str
    boq_item_id: str
    boq_v_uri: str
    spu_uri: str
    default_quantity_per_unit: Decimal
    norm_ref: str
    capability_type: str
    proof_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "boq_item_id": self.boq_item_id,
            "boq_v_uri": self.boq_v_uri,
            "spu_uri": self.spu_uri,
            "default_quantity_per_unit": _decimal_to_str(self.default_quantity_per_unit),
            "norm_ref": self.norm_ref,
            "capability_type": self.capability_type,
            "proof_hash": self.proof_hash,
        }


@dataclass(slots=True)
class SMU:
    smu_id: str
    name: str
    component_type: str
    bridge_uri: str | None
    spu_composition: list[dict[str, Any]]
    total_settlement_value: Decimal = Decimal("0")
    settlement_proof_hash: str = ""
    sealed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "smu_id": self.smu_id,
            "name": self.name,
            "component_type": self.component_type,
            "bridge_uri": self.bridge_uri or "",
            "spu_composition": list(self.spu_composition),
            "total_settlement_value": _decimal_to_str(self.total_settlement_value),
            "settlement_proof_hash": self.settlement_proof_hash,
            "sealed_at": self.sealed_at,
        }


def _spu_from_mapping(mapping: SPUBOQMapping) -> SPU:
    token = _to_text(mapping.spu_uri).strip().rstrip("/").split("/")[-1]
    name = token.split("@")[0].replace("-", " ").strip() or token
    category = token.split("@")[0].split("-")[0] if token else "generic"
    unit = ""
    capability = _to_text(mapping.capability_type).strip().lower()
    if "quantity" in capability:
        unit = "unit"
    elif "material" in capability:
        unit = "kg"
    return SPU(
        spu_uri=mapping.spu_uri,
        name=name,
        category=category,
        unit=unit,
        norm_ref=mapping.norm_ref,
        description=f"Derived from BOQ mapping {mapping.mapping_id}",
    )


def _mapping_models(mapping_rows: list[dict[str, Any]]) -> list[SPUBOQMapping]:
    out: list[SPUBOQMapping] = []
    for row in mapping_rows:
        if not isinstance(row, dict):
            continue
        out.append(
            SPUBOQMapping(
                mapping_id=_to_text(row.get("mapping_id")).strip(),
                boq_item_id=_to_text(row.get("boq_item_id")).strip(),
                boq_v_uri=_to_text(row.get("boq_v_uri")).strip(),
                spu_uri=_to_text(row.get("spu_uri")).strip(),
                default_quantity_per_unit=_to_decimal(
                    row.get("default_quantity_per_unit")
                    if row.get("default_quantity_per_unit") is not None
                    else row.get("weight"),
                    "1",
                ),
                norm_ref=_to_text(row.get("norm_ref")).strip(),
                capability_type=_to_text(row.get("capability_type")).strip() or "quantity_check",
                proof_hash=_to_text(row.get("proof_hash")).strip(),
            )
        )
    return out


def build_spu_boq_smu_graph(
    *,
    scan_results: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    mappings = _mapping_models(mapping_rows)
    mappings_by_boq_uri: dict[str, list[SPUBOQMapping]] = {}
    for row in mappings:
        mappings_by_boq_uri.setdefault(row.boq_v_uri, []).append(row)

    spu_index: dict[str, SPU] = {}
    boq_items: list[BOQItemModel] = []
    smu_units: list[SMU] = []

    for pair in scan_results:
        if not isinstance(pair, dict):
            continue
        boq = pair.get("boq_item") if isinstance(pair.get("boq_item"), dict) else {}
        utxo = pair.get("initial_utxo") if isinstance(pair.get("initial_utxo"), dict) else {}
        boq_item = BOQItemModel(
            boq_item_id=_to_text(boq.get("boq_item_id")).strip(),
            v_uri=_to_text(boq.get("v_uri") or boq.get("boq_v_uri")).strip(),
            description=_to_text(boq.get("description")).strip(),
            unit=_to_text(boq.get("unit")).strip(),
            boq_quantity=_to_decimal(boq.get("boq_quantity"), "0"),
            unit_price=_to_decimal(boq.get("unit_price"), "0"),
            total_amount=_to_decimal(boq.get("total_amount"), "0"),
            project_uri=_to_text(boq.get("project_uri")).strip(),
            bridge_uri=_to_text(boq.get("bridge_uri")).strip(),
            bridge_name=_to_text(boq.get("bridge_name")).strip(),
            genesis_hash=_to_text(boq.get("genesis_hash") or utxo.get("proof_hash")).strip(),
        )
        boq_items.append(boq_item)

        row_mappings = mappings_by_boq_uri.get(boq_item.v_uri, [])
        composition: list[dict[str, Any]] = []
        for mapping in row_mappings:
            spu_obj = _spu_from_mapping(mapping)
            spu_index[spu_obj.spu_uri] = spu_obj
            quantity = boq_item.boq_quantity * mapping.default_quantity_per_unit
            composition.append(
                {
                    "spu_uri": mapping.spu_uri,
                    "quantity": _decimal_to_str(quantity),
                    "unit": boq_item.unit,
                    "norm_ref": mapping.norm_ref,
                }
            )
        smu_name = _to_text(boq_item.bridge_name).strip()
        if smu_name:
            smu_name = f"{smu_name} {boq_item.description}".strip()
        else:
            smu_name = boq_item.description or boq_item.boq_item_id
        smu_units.append(
            SMU(
                smu_id=_default_smu_id(boq_item.project_uri, boq_item.boq_item_id, boq_item.bridge_uri),
                name=smu_name,
                component_type=_infer_component_type(
                    boq_item_id=boq_item.boq_item_id,
                    description=boq_item.description,
                ),
                bridge_uri=boq_item.bridge_uri or None,
                spu_composition=composition,
                total_settlement_value=boq_item.total_amount,
                settlement_proof_hash="",
                sealed_at="",
            )
        )

    return {
        "ok": True,
        "counts": {
            "spu": len(spu_index),
            "boq_items": len(boq_items),
            "spu_boq_mappings": len(mappings),
            "smu": len(smu_units),
        },
        "spu_library": [item.to_dict() for item in sorted(spu_index.values(), key=lambda x: x.spu_uri)],
        "boq_items": [item.to_dict() for item in boq_items],
        "spu_boq_mappings": [item.to_dict() for item in mappings],
        "smu_units": [item.to_dict() for item in smu_units],
    }


__all__ = [
    "BOQItemModel",
    "SMU",
    "SPU",
    "SPUBOQMapping",
    "build_spu_boq_smu_graph",
]

