"""Recursive ComponentUTXO model and conservation-proof engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import json
import time
from typing import Any, Callable

from fastapi import HTTPException

from services.api.core.norm.normpeg_engine import resolve_norm_rule
from services.api.domain.execution.integrations import ProofUTXOEngine
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_float as _to_float,
    to_text as _to_text,
)

_EPS = Decimal("0.000000001")


def _to_decimal(value: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = _to_text(value).strip()
    if not text:
        return default
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        parsed = _to_float(text)
        if parsed is None:
            return default
        return Decimal(str(parsed))


def _norm_material_role(value: Any) -> str:
    return _to_text(value).strip().lower().replace(" ", "_")


def _hash_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _merge_dict_decimal(target: dict[str, Decimal], source: dict[str, Decimal]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, Decimal("0")) + value


def _extract_material_qty_from_row(row: dict[str, Any]) -> Decimal:
    sd = _as_dict(row.get("state_data"))
    settlement = _as_dict(sd.get("settlement"))
    measurement = _as_dict(sd.get("measurement"))
    for candidate in (
        sd.get("material_quantity"),
        sd.get("quantity"),
        sd.get("used_quantity"),
        sd.get("consumed_quantity"),
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        measurement.get("quantity"),
        measurement.get("used_quantity"),
    ):
        qty = _to_decimal(candidate, default=Decimal("-1"))
        if qty >= 0:
            return qty
    return Decimal("0")


def _extract_material_role_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    for candidate in (
        sd.get("material_role"),
        sd.get("material_type"),
        sd.get("material_code"),
        sd.get("material_name"),
        sd.get("material"),
        sd.get("resource_type"),
    ):
        role = _norm_material_role(candidate)
        if role:
            return role
    return "unknown"


def _resolve_tolerance_ratio(
    *,
    material_role: str,
    tolerance_spec_uri: str,
    tolerance_override: Decimal | None,
    planned_qty: Decimal,
    default_tolerance_ratio: Decimal,
    resolve_norm_rule_fn: Callable[[Any, Any], dict[str, Any]],
) -> tuple[Decimal, str]:
    if tolerance_override is not None and tolerance_override >= 0:
        if tolerance_override <= Decimal("1"):
            return tolerance_override, "binding_ratio"
        if planned_qty > _EPS:
            return tolerance_override / planned_qty, "binding_absolute"

    normalized_uri = _to_text(tolerance_spec_uri).strip()
    if normalized_uri.startswith("v://norm/"):
        try:
            threshold = _as_dict(resolve_norm_rule_fn(normalized_uri, {"material_role": material_role}))
        except Exception:
            threshold = {}
        tolerance = _to_decimal(threshold.get("tolerance"), default=Decimal("-1"))
        if Decimal("0") <= tolerance <= Decimal("1"):
            return tolerance, normalized_uri
        limit = _to_decimal(threshold.get("threshold"), default=Decimal("-1"))
        if Decimal("0") <= limit <= Decimal("1"):
            return limit, normalized_uri
    return default_tolerance_ratio, "default"


@dataclass(slots=True)
class BOQItem:
    item_id: str
    description: str
    unit: str
    qty: Decimal
    unit_price: Decimal
    spec_uri: str


@dataclass(slots=True)
class MaterialInputUTXO:
    utxo_id: str
    material_role: str
    qty: Decimal
    proof_hash: str = ""
    boq_item_id: str = ""
    material_type: str = ""


@dataclass(slots=True)
class ComponentMaterialBinding:
    material_utxo_id: str
    material_role: str
    planned_qty: Decimal
    actual_qty: Decimal
    tolerance: Decimal | None = None
    proof_hash: str = ""
    tolerance_spec_uri: str = ""
    boq_item_id: str = ""


@dataclass(slots=True)
class ComponentUTXO:
    component_id: str
    component_uri: str
    project_uri: str
    kind: str
    bom: dict[str, Decimal]
    bom_constraints: dict[str, dict[str, Any]] = field(default_factory=dict)
    material_inputs: list[MaterialInputUTXO] = field(default_factory=list)
    material_bindings: list[ComponentMaterialBinding] = field(default_factory=list)
    child_components: list[str] = field(default_factory=list)
    parent_component: str | None = None
    status: str = "PENDING"
    version: int = 1
    proof_hash: str = ""
    last_trip_id: str | None = None
    last_action: str | None = None
    timestamp: float = field(default_factory=time.time)
    boq_items: list[BOQItem] = field(default_factory=list)

    def compute_proof(self) -> str:
        payload = {
            "component_uri": self.component_uri,
            "kind": self.kind,
            "bom": {k: float(v) for k, v in sorted(self.bom.items())},
            "boq_items": [
                {
                    "item_id": b.item_id,
                    "description": b.description,
                    "unit": b.unit,
                    "qty": float(b.qty),
                    "unit_price": float(b.unit_price),
                    "spec_uri": b.spec_uri,
                }
                for b in self.boq_items
            ],
            "material_inputs": [
                {
                    "utxo_id": m.utxo_id,
                    "material_role": m.material_role,
                    "material_type": m.material_type,
                    "qty": float(m.qty),
                    "proof_hash": m.proof_hash,
                    "boq_item_id": m.boq_item_id,
                }
                for m in self.material_inputs
            ],
            "materials": [
                {
                    "utxo": m.material_utxo_id,
                    "role": m.material_role,
                    "planned": float(m.planned_qty),
                    "actual": float(m.actual_qty),
                    "tolerance": float(m.tolerance) if m.tolerance is not None else None,
                    "proof_hash": m.proof_hash,
                }
                for m in self.material_bindings
            ],
            "children": list(self.child_components),
            "status": self.status,
            "version": self.version,
            "last_trip": self.last_trip_id,
            "action": self.last_action,
            "timestamp": self.timestamp,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        self.proof_hash = "COMP-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()
        return self.proof_hash


@dataclass(slots=True)
class TripRoleAction:
    trip_id: str
    action: str
    executor_uri: str
    component_uri: str
    norm_ref: str | None = None
    timestamp: float = field(default_factory=time.time)

    def execute(self, component: ComponentUTXO) -> ComponentUTXO:
        new_component = ComponentUTXO(
            component_id=component.component_id,
            component_uri=component.component_uri,
            project_uri=component.project_uri,
            kind=component.kind,
            bom=dict(component.bom),
            bom_constraints=dict(component.bom_constraints),
            material_inputs=list(component.material_inputs),
            material_bindings=list(component.material_bindings),
            child_components=list(component.child_components),
            parent_component=component.parent_component,
            status=component.status,
            version=component.version + 1,
            boq_items=list(component.boq_items),
        )

        normalized_action = _to_text(self.action).strip().lower()
        if normalized_action == "quality.check":
            result = evaluate_component_conservation(new_component)
            new_component.status = "QUALIFIED" if bool(result.get("within_tolerance")) else "FAILED"
        elif normalized_action in {"structure.accept", "structural.accept", "accept"}:
            new_component.status = "ACCEPTED"

        new_component.last_trip_id = self.trip_id
        new_component.last_action = self.action
        new_component.timestamp = self.timestamp
        new_component.compute_proof()
        return new_component


def validate_component_conservation(component: ComponentUTXO) -> dict[str, Any]:
    by_role_inputs: dict[str, list[MaterialInputUTXO]] = {}
    for item in component.material_inputs:
        role = _norm_material_role(item.material_role or item.material_type)
        if not role:
            role = "unknown"
        by_role_inputs.setdefault(role, []).append(item)

    by_role_binding: dict[str, list[ComponentMaterialBinding]] = {}
    for item in component.material_bindings:
        role = _norm_material_role(item.material_role)
        if not role:
            role = "unknown"
        by_role_binding.setdefault(role, []).append(item)

    result = {
        "component_uri": component.component_uri,
        "materials": [],
        "within_tolerance": True,
        "total_delta": 0.0,
        "by_role": {},
    }

    all_roles = sorted(set(component.bom.keys()) | set(by_role_inputs.keys()) | set(by_role_binding.keys()))
    for role in all_roles:
        role_inputs = by_role_inputs.get(role, [])
        role_bindings = by_role_binding.get(role, [])

        planned_qty = component.bom.get(role, Decimal("0"))
        if planned_qty <= _EPS and role_bindings:
            planned_qty = sum(binding.planned_qty for binding in role_bindings)

        if role_inputs:
            actual_qty = sum(item.qty for item in role_inputs)
        else:
            actual_qty = sum(binding.actual_qty for binding in role_bindings)

        tolerance_values = [binding.tolerance for binding in role_bindings if binding.tolerance is not None]
        tolerance = max(tolerance_values) if tolerance_values else None

        tolerance_spec_uri = ""
        if role_bindings:
            tolerance_spec_uri = _to_text(role_bindings[0].tolerance_spec_uri).strip()
        if not tolerance_spec_uri:
            tolerance_spec_uri = _to_text(component.bom_constraints.get(role, {}).get("tolerance_spec_uri") or "").strip()

        role_proof_hashes = [
            _to_text(item.proof_hash).strip().lower()
            for item in role_inputs
            if _to_text(item.proof_hash).strip()
        ]
        if not role_proof_hashes and role_bindings:
            role_proof_hashes = [
                _to_text(binding.proof_hash).strip().lower()
                for binding in role_bindings
                if _to_text(binding.proof_hash).strip()
            ]

        role_utxo_ids = [
            _to_text(item.utxo_id).strip()
            for item in role_inputs
            if _to_text(item.utxo_id).strip()
        ]
        if not role_utxo_ids and role_bindings:
            role_utxo_ids = [
                _to_text(binding.material_utxo_id).strip()
                for binding in role_bindings
                if _to_text(binding.material_utxo_id).strip()
            ]

        role_boq_item_ids = [
            _to_text(item.boq_item_id).strip()
            for item in role_inputs
            if _to_text(item.boq_item_id).strip()
        ]
        if not role_boq_item_ids and role_bindings:
            role_boq_item_ids = [
                _to_text(binding.boq_item_id).strip()
                for binding in role_bindings
                if _to_text(binding.boq_item_id).strip()
            ]

        delta_decimal = actual_qty - planned_qty
        delta = float(delta_decimal)
        ok = True
        if tolerance is not None:
            ok = abs(delta) <= float(tolerance)
            if not ok:
                result["within_tolerance"] = False

        result["materials"].append(
            {
                "material_utxo_id": role_utxo_ids[0] if role_utxo_ids else f"group:{role}",
                "material_role": role,
                "planned": float(planned_qty),
                "actual": float(actual_qty),
                "delta": delta,
                "tolerance": float(tolerance) if tolerance is not None else None,
                "within_tolerance": ok,
                "proof_hash": role_proof_hashes[0] if role_proof_hashes else "",
                "proof_hashes": role_proof_hashes,
                "material_input_utxo_ids": role_utxo_ids,
                "boq_item_id": role_boq_item_ids[0] if role_boq_item_ids else "",
                "boq_item_ids": role_boq_item_ids,
                "tolerance_spec_uri": tolerance_spec_uri,
                "source_input_count": len(role_inputs),
            }
        )
        result["total_delta"] += delta
        result["by_role"][role] = {
            "material_role": role,
            "planned": float(planned_qty),
            "actual": float(actual_qty),
            "delta": delta,
            "input_count": len(role_inputs),
        }

    return result


def evaluate_component_conservation(
    component: ComponentUTXO,
    *,
    default_tolerance_ratio: Decimal = Decimal("0.05"),
    resolve_norm_rule_fn: Callable[[Any, Any], dict[str, Any]] = resolve_norm_rule,
) -> dict[str, Any]:
    result = validate_component_conservation(component)
    result["within_tolerance"] = True
    normalized_default_ratio = _to_decimal(default_tolerance_ratio, default=Decimal("0.05"))

    by_role_details: dict[str, list[dict[str, Any]]] = {}
    for item in result["materials"]:
        role = _norm_material_role(item.get("material_role"))
        planned = _to_decimal(item.get("planned"))
        actual = _to_decimal(item.get("actual"))
        deviation = actual - planned
        deviation_ratio = Decimal("0") if planned <= _EPS else abs(deviation) / planned

        tolerance_override = _to_decimal(item.get("tolerance"), default=Decimal("-1"))
        tolerance_spec_uri = _to_text(item.get("tolerance_spec_uri") or "").strip()
        if tolerance_override < 0:
            bom_rule = _as_dict(component.bom_constraints.get(role))
            bom_ratio = _to_float(bom_rule.get("tolerance_ratio"))
            if bom_ratio is not None:
                tolerance_override = _to_decimal(bom_ratio)
            if not tolerance_spec_uri:
                tolerance_spec_uri = _to_text(bom_rule.get("tolerance_spec_uri") or "").strip()
        resolved_tolerance, tolerance_source = _resolve_tolerance_ratio(
            material_role=role,
            tolerance_spec_uri=tolerance_spec_uri,
            tolerance_override=tolerance_override if tolerance_override >= 0 else None,
            planned_qty=planned,
            default_tolerance_ratio=normalized_default_ratio,
            resolve_norm_rule_fn=resolve_norm_rule_fn,
        )
        passed = deviation_ratio <= resolved_tolerance
        item["deviation_ratio"] = float(deviation_ratio) if planned > _EPS else 0.0
        item["tolerance_ratio"] = float(resolved_tolerance)
        item["tolerance_source"] = tolerance_source
        item["within_tolerance"] = passed
        if not passed:
            result["within_tolerance"] = False

        by_role_details.setdefault(role, []).append(item)

    for role, group in by_role_details.items():
        role_planned = sum(_to_decimal(row.get("planned")) for row in group)
        role_actual = sum(_to_decimal(row.get("actual")) for row in group)
        role_delta = role_actual - role_planned
        role_ratio = Decimal("0") if role_planned <= _EPS else abs(role_delta) / role_planned
        role_tolerance = max(_to_decimal(row.get("tolerance_ratio")) for row in group)
        role_passed = role_ratio <= role_tolerance
        role_bucket = _as_dict(result["by_role"].get(role))
        role_bucket["deviation_ratio"] = float(role_ratio) if role_planned > _EPS else 0.0
        role_bucket["tolerance_ratio"] = float(role_tolerance)
        role_bucket["within_tolerance"] = role_passed
        result["by_role"][role] = role_bucket

    return result


def aggregate_child_components(
    components: dict[str, ComponentUTXO],
    root_uri: str,
    *,
    _visited: set[str] | None = None,
) -> dict[str, Any]:
    if root_uri not in components:
        raise HTTPException(404, f"component not found: {root_uri}")

    visited = _visited if _visited is not None else set()
    if root_uri in visited:
        raise HTTPException(409, f"component recursion cycle detected: {root_uri}")
    visited.add(root_uri)

    root = components[root_uri]
    aggregate = {
        "component_uri": root_uri,
        "children": [],
        "total_materials": {},
    }
    totals: dict[str, Decimal] = {}
    if root.material_inputs:
        for item in root.material_inputs:
            role = _norm_material_role(item.material_role or item.material_type) or "unknown"
            totals[role] = totals.get(role, Decimal("0")) + item.qty
    else:
        for binding in root.material_bindings:
            role = _norm_material_role(binding.material_role) or "unknown"
            totals[role] = totals.get(role, Decimal("0")) + binding.actual_qty

    for child_uri in root.child_components:
        child_aggregate = aggregate_child_components(components, child_uri, _visited=visited)
        aggregate["children"].append(child_aggregate)
        child_totals = {
            role: _to_decimal(value)
            for role, value in _as_dict(child_aggregate.get("total_materials")).items()
        }
        _merge_dict_decimal(totals, child_totals)

    aggregate["total_materials"] = {role: float(qty) for role, qty in sorted(totals.items())}
    visited.remove(root_uri)
    return aggregate


def build_component_doc_context(
    component: ComponentUTXO,
    validation_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "component_id": component.component_id,
        "component_uri": component.component_uri,
        "kind": component.kind,
        "status": component.status,
        "version": component.version,
        "boq_items": [
            {
                "item_id": item.item_id,
                "description": item.description,
                "unit": item.unit,
                "qty": float(item.qty),
                "unit_price": float(item.unit_price),
                "spec_uri": item.spec_uri,
            }
            for item in component.boq_items
        ],
        "bom": {role: float(qty) for role, qty in sorted(component.bom.items())},
        "material_inputs": [
            {
                "utxo_id": item.utxo_id,
                "material_role": item.material_role,
                "material_type": item.material_type,
                "qty": float(item.qty),
                "proof_hash": item.proof_hash,
                "boq_item_id": item.boq_item_id,
            }
            for item in component.material_inputs
        ],
        "materials": _as_list(validation_result.get("materials")),
        "within_tolerance": bool(validation_result.get("within_tolerance")),
        "total_delta": float(validation_result.get("total_delta") or 0.0),
        "proof_hash": component.proof_hash,
        "last_trip": component.last_trip_id,
        "action": component.last_action,
    }


def build_component_docpeg_request(
    component: ComponentUTXO,
    validation_result: dict[str, Any],
) -> dict[str, Any]:
    context = build_component_doc_context(component, validation_result)
    return {
        "template_key": "component_conservation_report",
        "document_type": "component_report",
        "payload": context,
        "options": {
            "embed_proof": True,
            "generate_qr": True,
            "output_formats": ["docx", "pdf"],
        },
    }


def _normalize_component_uri(component_id: str, project_uri: str, component_uri: str) -> str:
    normalized_uri = _to_text(component_uri).strip()
    if normalized_uri.startswith("v://"):
        return normalized_uri
    normalized_project = _to_text(project_uri).strip().rstrip("/")
    normalized_component_id = _to_text(component_id).strip()
    if normalized_project and normalized_component_id:
        return f"{normalized_project}/component/{normalized_component_id}"
    return normalized_component_id or normalized_uri


def _material_binding_from_inputs(
    *,
    material_inputs: list[dict[str, Any]],
    bom_by_role: dict[str, Decimal],
) -> list[ComponentMaterialBinding]:
    by_role_actual: dict[str, Decimal] = {}
    proof_hash_by_role: dict[str, str] = {}
    boq_item_id_by_role: dict[str, str] = {}

    for item in material_inputs:
        role = _norm_material_role(item.get("material_role") or item.get("material_type"))
        if not role:
            role = "unknown"
        actual_qty = _to_decimal(item.get("actual_qty", item.get("qty")), default=Decimal("0"))
        by_role_actual[role] = by_role_actual.get(role, Decimal("0")) + actual_qty
        if role not in proof_hash_by_role:
            proof_hash_by_role[role] = _to_text(item.get("proof_hash") or "").strip().lower()
        if role not in boq_item_id_by_role:
            boq_item_id_by_role[role] = _to_text(item.get("boq_item_id") or "").strip()

    out: list[ComponentMaterialBinding] = []
    for role in sorted(set(bom_by_role.keys()) | set(by_role_actual.keys())):
        out.append(
            ComponentMaterialBinding(
                material_utxo_id=f"group:{role}",
                material_role=role,
                planned_qty=bom_by_role.get(role, Decimal("0")),
                actual_qty=by_role_actual.get(role, Decimal("0")),
                proof_hash=proof_hash_by_role.get(role, ""),
                boq_item_id=boq_item_id_by_role.get(role, ""),
            )
        )
    return out


def _build_component_nodes_map(
    *,
    root_component: ComponentUTXO,
    component_nodes: list[dict[str, Any]],
) -> dict[str, ComponentUTXO]:
    nodes = {root_component.component_uri: root_component}
    for node in component_nodes:
        if not isinstance(node, dict):
            continue
        comp = _build_component_from_payload(node)
        if comp.component_uri:
            nodes[comp.component_uri] = comp
    return nodes


def _build_component_from_payload(payload: dict[str, Any]) -> ComponentUTXO:
    component_id = _to_text(payload.get("component_id") or "").strip()
    project_uri = _to_text(payload.get("project_uri") or "").strip()
    component_uri = _normalize_component_uri(
        component_id=component_id,
        project_uri=project_uri,
        component_uri=_to_text(payload.get("component_uri") or "").strip(),
    )
    kind = _to_text(payload.get("kind") or "").strip() or "component"

    raw_bom = payload.get("bom")
    bom_by_role: dict[str, Decimal] = {}
    bom_constraints: dict[str, dict[str, Any]] = {}
    if isinstance(raw_bom, dict):
        for role, qty in raw_bom.items():
            normalized_role = _norm_material_role(role)
            if not normalized_role:
                continue
            bom_by_role[normalized_role] = _to_decimal(qty)
            bom_constraints[normalized_role] = {}
    elif isinstance(raw_bom, list):
        for item in raw_bom:
            if not isinstance(item, dict):
                continue
            normalized_role = _norm_material_role(item.get("material_role") or item.get("material_type"))
            if not normalized_role:
                continue
            bom_by_role[normalized_role] = bom_by_role.get(normalized_role, Decimal("0")) + _to_decimal(item.get("qty"))
            existing = _as_dict(bom_constraints.get(normalized_role))
            tolerance_ratio = _to_float(item.get("tolerance_ratio"))
            tolerance_spec_uri = _to_text(item.get("tolerance_spec_uri") or "").strip()
            if tolerance_ratio is not None:
                existing["tolerance_ratio"] = max(float(tolerance_ratio), float(existing.get("tolerance_ratio") or 0.0))
            if tolerance_spec_uri and not _to_text(existing.get("tolerance_spec_uri") or "").strip():
                existing["tolerance_spec_uri"] = tolerance_spec_uri
            bom_constraints[normalized_role] = existing

    boq_items: list[BOQItem] = []
    for item in _as_list(payload.get("boq_items")):
        if not isinstance(item, dict):
            continue
        boq_items.append(
            BOQItem(
                item_id=_to_text(item.get("item_id") or "").strip(),
                description=_to_text(item.get("description") or "").strip(),
                unit=_to_text(item.get("unit") or "").strip(),
                qty=_to_decimal(item.get("qty")),
                unit_price=_to_decimal(item.get("unit_price")),
                spec_uri=_to_text(item.get("spec_uri") or "").strip(),
            )
        )

    material_inputs: list[MaterialInputUTXO] = []
    for item in _as_list(payload.get("material_inputs")):
        if not isinstance(item, dict):
            continue
        role = _norm_material_role(item.get("material_role") or item.get("material_type"))
        if not role:
            role = "unknown"
        qty = _to_decimal(item.get("actual_qty", item.get("qty")))
        material_inputs.append(
            MaterialInputUTXO(
                utxo_id=_to_text(item.get("utxo_id") or item.get("material_utxo_id") or "").strip(),
                material_role=role,
                material_type=_to_text(item.get("material_type") or "").strip(),
                qty=qty,
                proof_hash=_to_text(item.get("proof_hash") or "").strip().lower(),
                boq_item_id=_to_text(item.get("boq_item_id") or "").strip(),
            )
        )

    material_bindings: list[ComponentMaterialBinding] = []
    raw_bindings = _as_list(payload.get("material_bindings"))
    if not material_inputs:
        for item in raw_bindings:
            if not isinstance(item, dict):
                continue
            role = _norm_material_role(item.get("material_role") or item.get("material_type"))
            if not role:
                role = "unknown"
            material_inputs.append(
                MaterialInputUTXO(
                    utxo_id=_to_text(item.get("material_utxo_id") or item.get("utxo_id") or "").strip(),
                    material_role=role,
                    material_type=_to_text(item.get("material_type") or "").strip(),
                    qty=_to_decimal(item.get("actual_qty", item.get("qty"))),
                    proof_hash=_to_text(item.get("proof_hash") or "").strip().lower(),
                    boq_item_id=_to_text(item.get("boq_item_id") or "").strip(),
                )
            )

    for item in raw_bindings:
        if not isinstance(item, dict):
            continue
        role = _norm_material_role(item.get("material_role") or item.get("material_type"))
        if not role:
            role = "unknown"
        material_bindings.append(
            ComponentMaterialBinding(
                material_utxo_id=_to_text(item.get("material_utxo_id") or item.get("utxo_id") or "").strip(),
                material_role=role,
                planned_qty=_to_decimal(item.get("planned_qty"), default=bom_by_role.get(role, Decimal("0"))),
                actual_qty=_to_decimal(item.get("actual_qty", item.get("qty"))),
                tolerance=_to_decimal(item.get("tolerance"), default=Decimal("-1"))
                if item.get("tolerance") is not None
                else None,
                proof_hash=_to_text(item.get("proof_hash") or "").strip().lower(),
                tolerance_spec_uri=_to_text(item.get("tolerance_spec_uri") or "").strip(),
                boq_item_id=_to_text(item.get("boq_item_id") or "").strip(),
            )
        )

    if not material_bindings:
        material_bindings = _material_binding_from_inputs(
            material_inputs=[
                {
                    "material_role": item.material_role,
                    "actual_qty": float(item.qty),
                    "proof_hash": item.proof_hash,
                    "boq_item_id": item.boq_item_id,
                    "utxo_id": item.utxo_id,
                }
                for item in material_inputs
            ],
            bom_by_role=bom_by_role,
        )

    component = ComponentUTXO(
        component_id=component_id,
        component_uri=component_uri,
        project_uri=project_uri,
        kind=kind,
        bom=bom_by_role,
        bom_constraints=bom_constraints,
        material_inputs=material_inputs,
        material_bindings=material_bindings,
        child_components=[
            _to_text(x).strip()
            for x in _as_list(payload.get("child_components"))
            if _to_text(x).strip()
        ],
        parent_component=_to_text(payload.get("parent_component") or "").strip() or None,
        status=_to_text(payload.get("status") or "PENDING").strip().upper() or "PENDING",
        version=max(1, int(payload.get("version") or 1)),
        proof_hash=_to_text(payload.get("proof_hash") or "").strip(),
        last_trip_id=_to_text(payload.get("last_trip_id") or "").strip() or None,
        last_action=_to_text(payload.get("last_action") or "").strip() or None,
        timestamp=float(payload.get("timestamp") or time.time()),
        boq_items=boq_items,
    )
    if not component.proof_hash:
        component.compute_proof()
    return component


def build_component_utxo_verification(
    *,
    sb: Any,
    component_id: str,
    component_uri: str = "",
    project_uri: str = "",
    kind: str = "component",
    boq_items: list[dict[str, Any]] | None = None,
    bom: list[dict[str, Any]] | dict[str, Any] | None = None,
    material_bindings: list[dict[str, Any]] | None = None,
    material_inputs: list[dict[str, Any]] | None = None,
    material_input_proof_ids: list[str] | None = None,
    child_components: list[str] | None = None,
    parent_component: str | None = None,
    status: str = "PENDING",
    version: int = 1,
    last_trip_id: str | None = None,
    last_action: str | None = None,
    timestamp: float | None = None,
    trip_id: str = "",
    trip_action: str = "",
    trip_executor_uri: str = "",
    norm_ref: str = "",
    component_nodes: list[dict[str, Any]] | None = None,
    default_tolerance_ratio: float = 0.05,
    render_docpeg: bool = True,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: str | None = None,
    include_docx_base64: bool = True,
    resolve_norm_rule_fn: Callable[[Any, Any], dict[str, Any]] = resolve_norm_rule,
    proof_utxo_engine_cls: Callable[[Any], Any] = ProofUTXOEngine,
) -> dict[str, Any]:
    normalized_component_id = _to_text(component_id).strip()
    if not normalized_component_id:
        raise HTTPException(400, "component_id is required")

    resolved_inputs = [item for item in _as_list(material_inputs) if isinstance(item, dict)]
    proof_ids = [_to_text(pid).strip() for pid in _as_list(material_input_proof_ids) if _to_text(pid).strip()]
    if proof_ids:
        engine = proof_utxo_engine_cls(sb)
        for proof_id in proof_ids:
            row = _as_dict(engine.get_by_id(proof_id))
            if not row:
                raise HTTPException(404, f"material input proof not found: {proof_id}")
            row_project = _to_text(row.get("project_uri") or "").strip()
            if _to_text(project_uri).strip() and row_project != _to_text(project_uri).strip():
                raise HTTPException(409, f"material input proof project mismatch: {proof_id}")
            sd = _as_dict(row.get("state_data"))
            resolved_inputs.append(
                {
                    "utxo_id": _to_text(row.get("proof_id") or proof_id).strip(),
                    "material_role": _extract_material_role_from_row(row),
                    "actual_qty": float(_extract_material_qty_from_row(row)),
                    "proof_hash": _to_text(row.get("proof_hash") or "").strip().lower(),
                    "boq_item_id": _to_text(sd.get("boq_item_id") or "").strip(),
                }
            )

    payload = {
        "component_id": normalized_component_id,
        "component_uri": component_uri,
        "project_uri": project_uri,
        "kind": kind,
        "boq_items": _as_list(boq_items),
        "bom": bom if bom is not None else [],
        "material_bindings": _as_list(material_bindings),
        "material_inputs": resolved_inputs,
        "child_components": _as_list(child_components),
        "parent_component": parent_component,
        "status": status,
        "version": version,
        "last_trip_id": last_trip_id,
        "last_action": last_action,
        "timestamp": timestamp if timestamp is not None else time.time(),
    }
    component = _build_component_from_payload(payload)
    if not component.material_inputs and not component.material_bindings:
        raise HTTPException(400, "material_inputs is required")
    if not component.bom:
        raise HTTPException(400, "bom is required")

    default_ratio = _to_decimal(default_tolerance_ratio, default=Decimal("0.05"))
    material_checks = evaluate_component_conservation(
        component,
        default_tolerance_ratio=default_ratio,
        resolve_norm_rule_fn=resolve_norm_rule_fn,
    )
    within_tolerance = bool(material_checks["within_tolerance"])

    working_component = component
    trip_execution: dict[str, Any] = {}
    if _to_text(trip_action).strip():
        action = TripRoleAction(
            trip_id=_to_text(trip_id).strip() or f"TRIP-{int(time.time())}",
            action=_to_text(trip_action).strip(),
            executor_uri=_to_text(trip_executor_uri).strip() or "v://executor/system/",
            component_uri=component.component_uri,
            norm_ref=_to_text(norm_ref).strip() or None,
        )
        next_component = action.execute(component)
        next_validation = evaluate_component_conservation(
            next_component,
            default_tolerance_ratio=default_ratio,
            resolve_norm_rule_fn=resolve_norm_rule_fn,
        )
        trip_execution = {
            "action": action.action,
            "trip_id": action.trip_id,
            "executor_uri": action.executor_uri,
            "before": {
                "status": component.status,
                "version": component.version,
                "proof_hash": component.proof_hash,
            },
            "after": {
                "status": next_component.status,
                "version": next_component.version,
                "proof_hash": next_component.proof_hash,
            },
            "validation": next_validation,
        }
        working_component = next_component
        material_checks = next_validation
        within_tolerance = bool(next_validation.get("within_tolerance"))

    component_nodes_map = _build_component_nodes_map(
        root_component=working_component,
        component_nodes=[item for item in _as_list(component_nodes) if isinstance(item, dict)],
    )
    recursive_totals = aggregate_child_components(component_nodes_map, working_component.component_uri)
    doc_context = build_component_doc_context(working_component, material_checks)
    docpeg_request = build_component_docpeg_request(working_component, material_checks)

    proof_factors = {
        "material_chain_root_hash": _hash_json(
            [
                {
                    "utxo_id": item.utxo_id,
                    "material_role": item.material_role,
                    "qty": float(item.qty),
                    "proof_hash": item.proof_hash,
                }
                for item in sorted(
                    working_component.material_inputs,
                    key=lambda row: (
                        _to_text(row.material_role).strip(),
                        _to_text(row.utxo_id).strip(),
                        _to_text(row.proof_hash).strip(),
                    ),
                )
            ]
        ),
        "bom_deviation_hash": _hash_json(
            [
                {
                    "material_role": item.get("material_role"),
                    "planned": item.get("planned"),
                    "actual": item.get("actual"),
                    "delta": item.get("delta"),
                    "deviation_ratio": item.get("deviation_ratio"),
                }
                for item in material_checks["materials"]
            ]
        ),
        "norm_acceptance_hash": _hash_json(
            [
                {
                    "material_role": item.get("material_role"),
                    "tolerance_ratio": item.get("tolerance_ratio"),
                    "within_tolerance": item.get("within_tolerance"),
                }
                for item in material_checks["materials"]
            ]
        ),
    }

    response_payload = {
        "ok": True,
        "passed": within_tolerance,
        "component_id": working_component.component_id,
        "component_uri": working_component.component_uri,
        "project_uri": working_component.project_uri,
        "kind": working_component.kind,
        "status": working_component.status,
        "version": working_component.version,
        "proof_hash": working_component.compute_proof(),
        "last_trip_id": working_component.last_trip_id,
        "last_action": working_component.last_action,
        "timestamp": working_component.timestamp,
        "materials": material_checks["materials"],
        "within_tolerance": material_checks["within_tolerance"],
        "total_delta": material_checks["total_delta"],
        "by_role": material_checks["by_role"],
        "recursive_totals": recursive_totals,
        "doc_context": doc_context,
        "docpeg_request": docpeg_request,
        "proof_factors": proof_factors,
        "trip_execution": trip_execution,
        "boq_items": [
            {
                "item_id": item.item_id,
                "description": item.description,
                "unit": item.unit,
                "qty": float(item.qty),
                "unit_price": float(item.unit_price),
                "spec_uri": item.spec_uri,
            }
            for item in working_component.boq_items
        ],
        "bom": {role: float(qty) for role, qty in sorted(working_component.bom.items())},
        "material_inputs": [
            {
                "utxo_id": item.utxo_id,
                "material_role": item.material_role,
                "material_type": item.material_type,
                "qty": float(item.qty),
                "proof_hash": item.proof_hash,
                "boq_item_id": item.boq_item_id,
            }
            for item in working_component.material_inputs
        ],
        "material_bindings": [
            {
                "material_utxo_id": item.material_utxo_id,
                "material_role": item.material_role,
                "planned_qty": float(item.planned_qty),
                "actual_qty": float(item.actual_qty),
                "tolerance": float(item.tolerance) if item.tolerance is not None else None,
                "proof_hash": item.proof_hash,
                "tolerance_spec_uri": item.tolerance_spec_uri,
                "boq_item_id": item.boq_item_id,
            }
            for item in working_component.material_bindings
        ],
    }

    docpeg_bundle: dict[str, Any] = {}
    if render_docpeg:
        from services.api.domain.execution.triprole_component_docpeg import (
            build_component_docpeg_bundle as _build_component_docpeg_bundle,
        )

        docpeg_bundle = _build_component_docpeg_bundle(
            verification=response_payload,
            verify_base_url=_to_text(verify_base_url).strip() or "https://verify.qcspec.com",
            template_path=template_path,
            include_docx_base64=bool(include_docx_base64),
        )
    response_payload["docpeg_bundle"] = docpeg_bundle

    return response_payload


__all__ = [
    "BOQItem",
    "MaterialInputUTXO",
    "ComponentMaterialBinding",
    "ComponentUTXO",
    "TripRoleAction",
    "validate_component_conservation",
    "evaluate_component_conservation",
    "aggregate_child_components",
    "build_component_doc_context",
    "build_component_docpeg_request",
    "build_component_utxo_verification",
]
