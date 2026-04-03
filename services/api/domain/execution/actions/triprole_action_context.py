"""Shared action-context builder for TripRole execution."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.integrations import (
    resolve_required_credential,
    verify_credential,
)
from services.api.domain.execution.geo.triprole_boundary import _resolve_project_boundary
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
    utc_iso as _utc_iso,
)
from services.api.domain.execution.actions.triprole_consensus import (
    _normalize_signer_metadata,
)
from services.api.domain.execution.geo.triprole_geo_sensor import (
    build_spatiotemporal_anchor as _build_spatiotemporal_anchor,
)
from services.api.domain.execution.geo.triprole_geofence import (
    check_location_compliance,
)
from services.api.domain.execution.lineage.triprole_lineage import (
    _resolve_boq_item_uri,
    _resolve_segment_uri,
    _resolve_subitem_gate_binding,
)


def build_triprole_action_context(
    *,
    sb: Any,
    input_row: dict[str, Any],
    payload: dict[str, Any],
    action: str,
    input_proof_id: str,
    executor_uri: str,
    executor_did: str,
    credentials_vc_raw: Any,
    signer_metadata_raw: Any,
    body_geo_location_raw: Any,
    body_server_timestamp_raw: Any,
    segment_uri_override: str,
    boq_item_uri_override: str,
    resolve_required_credential_fn: Callable[..., str] = resolve_required_credential,
    verify_credential_fn: Callable[..., dict[str, Any]] = verify_credential,
    resolve_segment_uri_fn: Callable[[dict[str, Any], dict[str, Any], Any], str] = _resolve_segment_uri,
    resolve_boq_item_uri_fn: Callable[[dict[str, Any], Any], str] = _resolve_boq_item_uri,
    resolve_subitem_gate_binding_fn: Callable[..., dict[str, Any]] = _resolve_subitem_gate_binding,
    build_spatiotemporal_anchor_fn: Callable[..., dict[str, Any]] = _build_spatiotemporal_anchor,
    normalize_signer_metadata_fn: Callable[[Any], dict[str, Any]] = _normalize_signer_metadata,
    resolve_project_boundary_fn: Callable[..., dict[str, Any]] = _resolve_project_boundary,
    check_location_compliance_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = check_location_compliance,
) -> dict[str, Any]:
    input_sd = _as_dict(input_row.get("state_data"))
    project_uri = _to_text(input_row.get("project_uri") or "").strip()
    project_id = input_row.get("project_id")
    owner_uri = _to_text(input_row.get("owner_uri") or "").strip() or executor_uri
    segment_uri = resolve_segment_uri_fn(input_row, payload, segment_uri_override)
    boq_item_uri = resolve_boq_item_uri_fn(input_row, boq_item_uri_override)
    required_credential = resolve_required_credential_fn(
        action=action,
        boq_item_uri=boq_item_uri,
        payload=payload,
    )
    did_gate = verify_credential_fn(
        sb=sb,
        user_did=executor_did,
        required_credential=required_credential,
        project_uri=project_uri,
        boq_item_uri=boq_item_uri,
        payload_credentials=credentials_vc_raw,
    )
    if not bool(did_gate.get("ok")):
        raise HTTPException(
            403,
            f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
        )
    gate_binding = resolve_subitem_gate_binding_fn(
        sb=sb,
        input_row=input_row,
        boq_item_uri=boq_item_uri,
        payload=payload,
    )

    parent_hash = _to_text(input_row.get("proof_hash") or "").strip()
    now_iso = _utc_iso()
    anchor = build_spatiotemporal_anchor_fn(
        action=action,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        now_iso=now_iso,
        geo_location_raw=body_geo_location_raw if body_geo_location_raw is not None else payload.get("geo_location"),
        server_timestamp_raw=(
            body_server_timestamp_raw if body_server_timestamp_raw is not None else payload.get("server_timestamp_proof")
        ),
    )
    normalized_signer_metadata = normalize_signer_metadata_fn(signer_metadata_raw)
    project_boundary = resolve_project_boundary_fn(
        sb=sb,
        project_id=project_id,
        project_uri=project_uri,
        override=payload.get("project_boundary") or payload.get("site_boundary"),
    )
    geo_compliance = check_location_compliance_fn(
        _as_dict(anchor.get("geo_location")),
        project_boundary,
    )

    next_state: dict[str, Any] = dict(input_sd)
    next_state.update(
        {
            "trip_action": action,
            "trip_executor": executor_uri,
            "executor_did": executor_did,
            "trip_executed_at": now_iso,
            "parent_proof_id": input_proof_id,
            "parent_hash": parent_hash,
            "boq_item_uri": boq_item_uri or _to_text(input_sd.get("boq_item_uri") or "").strip(),
            "did_gate": did_gate,
            "geo_location": anchor.get("geo_location"),
            "server_timestamp_proof": anchor.get("server_timestamp_proof"),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "geo_compliance": geo_compliance,
            "trust_level": _to_text(geo_compliance.get("trust_level") or "").strip()
            or _to_text(input_sd.get("trust_level") or "").strip(),
            "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
            "linked_gate_id": _to_text(gate_binding.get("linked_gate_id") or "").strip(),
            "linked_gate_ids": _as_list(gate_binding.get("linked_gate_ids")),
            "linked_gate_rules": _as_list(gate_binding.get("linked_gate_rules")),
            "linked_spec_uri": _to_text(gate_binding.get("linked_spec_uri") or "").strip(),
            "spec_dict_key": _to_text(gate_binding.get("spec_dict_key") or "").strip(),
            "spec_item": _to_text(gate_binding.get("spec_item") or "").strip(),
            "gate_template_lock": bool(gate_binding.get("gate_template_lock")),
            "gate_binding_hash": _to_text(gate_binding.get("gate_binding_hash") or "").strip(),
        }
    )
    if _as_list(normalized_signer_metadata.get("signers")):
        next_state["signer_metadata"] = normalized_signer_metadata

    return {
        "input_sd": input_sd,
        "project_uri": project_uri,
        "project_id": project_id,
        "owner_uri": owner_uri,
        "segment_uri": segment_uri,
        "boq_item_uri": boq_item_uri,
        "did_gate": did_gate,
        "gate_binding": gate_binding,
        "parent_hash": parent_hash,
        "now_iso": now_iso,
        "anchor": anchor,
        "normalized_signer_metadata": normalized_signer_metadata,
        "geo_compliance": geo_compliance,
        "next_state": next_state,
    }


__all__ = ["build_triprole_action_context"]
