"""Governance context resolution helpers for SMU flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)


@dataclass(slots=True)
class ContainerState:
    status: str
    stage: str
    boq_item_uri: str
    smu_id: str


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = _to_text(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def resolve_governance_payload(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    component_type: str,
    measured_value: float | None,
    latest_unspent_leaf: Callable[..., dict[str, Any]],
    resolve_spu_template: Callable[[str, str], dict[str, Any]],
    resolve_norm_refs: Callable[..., list[str]],
    build_spu_formula_audit: Callable[..., dict[str, Any]],
    resolve_allowed_roles: Callable[[str, str], list[str]],
    resolve_docpeg_template: Callable[[str, str], dict[str, Any]],
    resolve_dynamic_threshold: Callable[..., dict[str, Any]],
    eval_threshold: Callable[[str, Any, float | None], dict[str, Any]],
    container_status_from_stage: Callable[[str, str], str],
    smu_id_from_item_code: Callable[[str], str],
    is_smu_frozen: Callable[..., dict[str, Any]],
    derive_display_metadata: Callable[..., dict[str, Any]],
    resolve_lab_status: Callable[..., dict[str, Any]],
    resolve_dual_pass_gate: Callable[..., dict[str, Any]],
    build_gatekeeper: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    row = latest_unspent_leaf(sb, project_uri=project_uri, boq_item_uri=boq_item_uri)
    if not row:
        return {}

    sd = _as_dict(row.get("state_data"))
    item_no = _to_text(sd.get("item_no") or boq_item_uri.split("/")[-1]).strip()
    item_name = _to_text(sd.get("item_name") or "").strip()
    spu = resolve_spu_template(item_no, item_name)
    template = {"formula": _as_dict(spu.get("spu_formula"))}
    norm_refs = resolve_norm_refs(
        item_no,
        item_name,
        template_norm_refs=[str(x).strip() for x in _as_list(spu.get("spu_normpeg_refs")) if str(x).strip()],
    )
    formula_validation = build_spu_formula_audit(
        template=template,
        measurement={},
        design_quantity=_to_float(sd.get("design_quantity")),
        approved_quantity=_to_float(sd.get("approved_quantity")),
    )
    if formula_validation:
        spu["formula_validation"] = formula_validation
    allowed_roles = resolve_allowed_roles(item_no, _to_text(spu.get("spu_template_id") or "").strip())
    docpeg_template = _as_dict(sd.get("docpeg_template"))
    if not docpeg_template:
        docpeg_template = resolve_docpeg_template(item_no, item_name)

    gate_id = _to_text(sd.get("linked_gate_id") or "").strip()
    threshold_pack: dict[str, Any] = {}
    if gate_id:
        try:
            threshold_pack = _as_dict(resolve_dynamic_threshold(sb=sb, gate_id=gate_id, context={"context": component_type}))
        except Exception:
            threshold_pack = {}
    threshold_eval = eval_threshold(
        _to_text(_as_dict(threshold_pack).get("operator") or "").strip(),
        _as_dict(threshold_pack).get("threshold"),
        measured_value,
    )

    stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    container = ContainerState(
        status=container_status_from_stage(stage, _to_text(row.get("result") or "").strip()),
        stage=stage or "INITIAL",
        boq_item_uri=boq_item_uri,
        smu_id=smu_id_from_item_code(item_no),
    )
    freeze_state = _as_dict(is_smu_frozen(sb=sb, project_uri=project_uri, smu_id=container.smu_id))
    if bool(freeze_state.get("frozen")):
        container.status = "Frozen"
        container.stage = "SMU_FREEZE"

    display_metadata = _as_dict(derive_display_metadata(sd, item_no=item_no, item_name=item_name))
    lab_status = _as_dict(resolve_lab_status(sb=sb, project_uri=project_uri, boq_item_uri=boq_item_uri))
    dual_gate = _as_dict(resolve_dual_pass_gate(sb=sb, project_uri=project_uri, boq_item_uri=boq_item_uri))
    gatekeeper = _as_dict(build_gatekeeper(dual_gate))
    return {
        "row": row,
        "sd": sd,
        "item_no": item_no,
        "item_name": item_name,
        "spu": spu,
        "norm_refs": norm_refs,
        "formula_validation": formula_validation,
        "allowed_roles": allowed_roles,
        "docpeg_template": docpeg_template,
        "gate_id": gate_id,
        "threshold_pack": threshold_pack,
        "threshold_eval": threshold_eval,
        "container": container,
        "freeze_state": freeze_state,
        "display_metadata": display_metadata,
        "lab_status": lab_status,
        "gatekeeper": gatekeeper,
    }


def build_governance_context_response_from_payload(
    *,
    payload: dict[str, Any],
    boq_item_uri: str,
    component_type: str,
    smu_id_from_item_code: Callable[[str], str],
    build_governance_context_response: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    normalized = normalize_governance_payload(
        payload=payload,
        boq_item_uri=boq_item_uri,
        smu_id_from_item_code=smu_id_from_item_code,
    )
    row = _as_dict(normalized.get("row"))
    sd = _as_dict(normalized.get("sd"))
    item_no = _to_text(normalized.get("item_no") or "").strip()
    item_name = _to_text(normalized.get("item_name") or "").strip()
    spu = _as_dict(normalized.get("spu"))
    norm_refs = [str(x).strip() for x in _as_list(normalized.get("norm_refs")) if str(x).strip()]
    formula_validation = _as_dict(normalized.get("formula_validation"))
    allowed_roles = [str(x).strip() for x in _as_list(normalized.get("allowed_roles")) if str(x).strip()]
    docpeg_template = _as_dict(normalized.get("docpeg_template"))
    gate_id = _to_text(normalized.get("gate_id") or "").strip()
    threshold_pack = _as_dict(normalized.get("threshold_pack"))
    threshold_eval = _as_dict(normalized.get("threshold_eval"))
    container_raw = normalized.get("container")
    container = (
        container_raw
        if isinstance(container_raw, ContainerState)
        else ContainerState(
            status="Pending",
            stage="INITIAL",
            boq_item_uri=boq_item_uri,
            smu_id=smu_id_from_item_code(item_no),
        )
    )
    freeze_state = _as_dict(normalized.get("freeze_state"))
    display_metadata = _as_dict(normalized.get("display_metadata"))
    lab_status = _as_dict(normalized.get("lab_status"))
    gatekeeper = _as_dict(normalized.get("gatekeeper"))
    return build_governance_context_response(
        component_type=component_type,
        row=row,
        sd=sd,
        item_no=item_no,
        item_name=item_name,
        docpeg_template=docpeg_template,
        display_metadata=display_metadata,
        lab_status=lab_status,
        norm_refs=norm_refs,
        formula_validation=formula_validation,
        spu=spu,
        gate_id=gate_id,
        threshold_pack=threshold_pack,
        threshold_eval=threshold_eval,
        freeze_state=freeze_state,
        gatekeeper=gatekeeper,
        allowed_roles=allowed_roles,
        container_status=container.status,
        container_stage=container.stage,
        container_boq_item_uri=container.boq_item_uri,
        container_smu_id=container.smu_id,
    )


def normalize_governance_payload(
    *,
    payload: dict[str, Any],
    boq_item_uri: str,
    smu_id_from_item_code: Callable[[str], str],
) -> dict[str, Any]:
    row = _as_dict(payload.get("row"))
    sd = _as_dict(payload.get("sd"))
    item_no = _to_text(payload.get("item_no") or "").strip()
    item_name = _to_text(payload.get("item_name") or "").strip()
    spu = _as_dict(payload.get("spu"))
    norm_refs = [str(x).strip() for x in _as_list(payload.get("norm_refs")) if str(x).strip()]
    formula_validation = _as_dict(payload.get("formula_validation"))
    allowed_roles = [str(x).strip() for x in _as_list(payload.get("allowed_roles")) if str(x).strip()]
    docpeg_template = _as_dict(payload.get("docpeg_template"))
    gate_id = _to_text(payload.get("gate_id") or "").strip()
    threshold_pack = _as_dict(payload.get("threshold_pack"))
    threshold_eval = _as_dict(payload.get("threshold_eval"))
    container_raw = payload.get("container")
    container = (
        container_raw
        if isinstance(container_raw, ContainerState)
        else ContainerState(
            status="Pending",
            stage="INITIAL",
            boq_item_uri=boq_item_uri,
            smu_id=smu_id_from_item_code(item_no),
        )
    )
    freeze_state = _as_dict(payload.get("freeze_state"))
    display_metadata = _as_dict(payload.get("display_metadata"))
    lab_status = _as_dict(payload.get("lab_status"))
    gatekeeper = _as_dict(payload.get("gatekeeper"))
    return {
        "row": row,
        "sd": sd,
        "item_no": item_no,
        "item_name": item_name,
        "spu": spu,
        "norm_refs": norm_refs,
        "formula_validation": formula_validation,
        "allowed_roles": allowed_roles,
        "docpeg_template": docpeg_template,
        "gate_id": gate_id,
        "threshold_pack": threshold_pack,
        "threshold_eval": threshold_eval,
        "container": container,
        "freeze_state": freeze_state,
        "display_metadata": display_metadata,
        "lab_status": lab_status,
        "gatekeeper": gatekeeper,
    }


__all__ = [
    "build_governance_context_response_from_payload",
    "ContainerState",
    "normalize_governance_payload",
    "resolve_governance_payload",
]

