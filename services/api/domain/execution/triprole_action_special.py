"""Special TripRole action handlers for scan and gateway-style records."""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.integrations import (
    resolve_required_credential,
    verify_credential,
)
from services.api.domain.execution.triprole_boundary import _resolve_project_boundary
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    sha256_json as _sha256_json,
    to_text as _to_text,
    utc_iso as _utc_iso,
)
from services.api.domain.execution.triprole_geo_sensor import (
    build_spatiotemporal_anchor as _build_spatiotemporal_anchor,
)
from services.api.domain.execution.triprole_geofence import (
    check_location_compliance,
)
from services.api.domain.execution.triprole_lineage import (
    _resolve_boq_item_uri,
    _resolve_segment_uri,
)


def _build_special_action_context(
    *,
    sb: Any,
    input_row: dict[str, Any],
    payload: dict[str, Any],
    action: str,
    input_proof_id: str,
    executor_uri: str,
    executor_did: str,
    credentials_vc_raw: Any,
    segment_uri_override: str,
    boq_item_uri_override: str,
    body_geo_location_raw: Any,
    body_server_timestamp_raw: Any,
    resolve_required_credential_fn: Callable[..., str] = resolve_required_credential,
    verify_credential_fn: Callable[..., dict[str, Any]] = verify_credential,
    resolve_segment_uri_fn: Callable[[dict[str, Any], dict[str, Any], Any], str] = _resolve_segment_uri,
    resolve_boq_item_uri_fn: Callable[[dict[str, Any], Any], str] = _resolve_boq_item_uri,
    build_spatiotemporal_anchor_fn: Callable[..., dict[str, Any]] = _build_spatiotemporal_anchor,
    resolve_project_boundary_fn: Callable[..., dict[str, Any]] = _resolve_project_boundary,
    check_location_compliance_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = check_location_compliance,
    utc_iso_fn: Callable[[], str] = _utc_iso,
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

    parent_hash = _to_text(input_row.get("proof_hash") or "").strip()
    now_iso = utc_iso_fn()
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

    return {
        "input_sd": input_sd,
        "project_uri": project_uri,
        "project_id": project_id,
        "owner_uri": owner_uri,
        "segment_uri": segment_uri,
        "boq_item_uri": boq_item_uri,
        "did_gate": did_gate,
        "parent_hash": parent_hash,
        "now_iso": now_iso,
        "anchor": anchor,
        "geo_compliance": geo_compliance,
    }


def execute_scan_entry_action(
    *,
    sb: Any,
    engine: Any,
    input_row: dict[str, Any],
    payload: dict[str, Any],
    input_proof_id: str,
    executor_uri: str,
    executor_role: str,
    executor_did: str,
    credentials_vc_raw: Any,
    segment_uri_override: str,
    boq_item_uri_override: str,
    body_geo_location_raw: Any,
    body_server_timestamp_raw: Any,
) -> dict[str, Any]:
    context = _build_special_action_context(
        sb=sb,
        input_row=input_row,
        payload=payload,
        action="scan.entry",
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        executor_did=executor_did,
        credentials_vc_raw=credentials_vc_raw,
        segment_uri_override=segment_uri_override,
        boq_item_uri_override=boq_item_uri_override,
        body_geo_location_raw=body_geo_location_raw,
        body_server_timestamp_raw=body_server_timestamp_raw,
    )
    input_sd = _as_dict(context.get("input_sd"))
    project_uri = _to_text(context.get("project_uri") or "").strip()
    project_id = context.get("project_id")
    owner_uri = _to_text(context.get("owner_uri") or "").strip() or executor_uri
    segment_uri = _to_text(context.get("segment_uri") or "").strip()
    boq_item_uri = _to_text(context.get("boq_item_uri") or "").strip()
    did_gate = _as_dict(context.get("did_gate"))
    parent_hash = _to_text(context.get("parent_hash") or "").strip()
    now_iso = _to_text(context.get("now_iso") or "").strip()
    anchor = _as_dict(context.get("anchor"))
    geo_compliance = _as_dict(context.get("geo_compliance"))

    scan_status = _to_text(payload.get("status") or "ok").strip().lower()
    scan_result = "PASS" if scan_status in {"ok", "pass", "success"} else "FAIL"
    scan_entry = dict(payload)
    if not scan_entry.get("scan_entry_at"):
        scan_entry["scan_entry_at"] = now_iso
    scan_entry["geo_compliance"] = geo_compliance

    state_data = dict(input_sd)
    state_data.update(
        {
            "trip_action": "scan.entry",
            "trip_executor": executor_uri,
            "executor_did": executor_did,
            "trip_executed_at": now_iso,
            "lifecycle_stage": "SCAN_ENTRY",
            "status": "SCAN_ENTRY",
            "parent_proof_id": input_proof_id,
            "parent_hash": parent_hash,
            "boq_item_uri": boq_item_uri or _to_text(input_sd.get("boq_item_uri") or "").strip(),
            "scan_entry": scan_entry,
            "scan_entry_hash": _sha256_json(scan_entry),
            "did_gate": did_gate,
            "geo_location": anchor.get("geo_location"),
            "server_timestamp_proof": anchor.get("server_timestamp_proof"),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "geo_compliance": geo_compliance,
            "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
        }
    )
    proof_id_seed = hashlib.sha256(f"{input_proof_id}|scan.entry|{now_iso}".encode("utf-8")).hexdigest()[:16].upper()
    proof_id = f"GP-SCAN-{proof_id_seed}"
    created = engine.create(
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_id=project_id,
        project_uri=project_uri,
        segment_uri=segment_uri or boq_item_uri,
        proof_type="scan_entry",
        result=scan_result,
        state_data=state_data,
        conditions=_as_list(input_row.get("conditions")),
        parent_proof_id=input_proof_id,
        norm_uri="v://norm/CoordOS/ScanEntry/1.0",
        signer_uri=_to_text(executor_uri).strip(),
        signer_role=_to_text(executor_role).strip() or "TRIPROLE",
    )
    return {
        "ok": True,
        "action": "scan.entry",
        "input_proof_id": input_proof_id,
        "output_proof_id": _to_text(created.get("proof_id") or "").strip(),
        "proof_hash": _to_text(created.get("proof_hash") or "").strip(),
        "proof_type": "scan_entry",
        "result": scan_result,
        "boq_item_uri": boq_item_uri,
        "did_gate": did_gate,
        "geo_compliance": geo_compliance,
        "spatiotemporal_anchor_hash": _to_text(anchor.get("spatiotemporal_anchor_hash") or "").strip(),
    }


def execute_gateway_style_action(
    *,
    sb: Any,
    engine: Any,
    input_row: dict[str, Any],
    payload: dict[str, Any],
    action: str,
    input_proof_id: str,
    executor_uri: str,
    executor_role: str,
    executor_did: str,
    credentials_vc_raw: Any,
    segment_uri_override: str,
    boq_item_uri_override: str,
    body_geo_location_raw: Any,
    body_server_timestamp_raw: Any,
) -> dict[str, Any]:
    context = _build_special_action_context(
        sb=sb,
        input_row=input_row,
        payload=payload,
        action=action,
        input_proof_id=input_proof_id,
        executor_uri=executor_uri,
        executor_did=executor_did,
        credentials_vc_raw=credentials_vc_raw,
        segment_uri_override=segment_uri_override,
        boq_item_uri_override=boq_item_uri_override,
        body_geo_location_raw=body_geo_location_raw,
        body_server_timestamp_raw=body_server_timestamp_raw,
    )
    input_sd = _as_dict(context.get("input_sd"))
    project_uri = _to_text(context.get("project_uri") or "").strip()
    project_id = context.get("project_id")
    owner_uri = _to_text(context.get("owner_uri") or "").strip() or executor_uri
    segment_uri = _to_text(context.get("segment_uri") or "").strip()
    boq_item_uri = _to_text(context.get("boq_item_uri") or "").strip()
    did_gate = _as_dict(context.get("did_gate"))
    parent_hash = _to_text(context.get("parent_hash") or "").strip()
    now_iso = _to_text(context.get("now_iso") or "").strip()
    anchor = _as_dict(context.get("anchor"))
    geo_compliance = _as_dict(context.get("geo_compliance"))

    status = _to_text(payload.get("status") or payload.get("result") or "PASS").strip().upper()
    result = "PASS" if status in {"PASS", "OK", "SUCCESS"} else "FAIL"
    if action == "meshpeg.verify":
        lifecycle = "MESHPEG"
        proof_type = "meshpeg"
        norm_uri = "v://norm/CoordOS/MeshPeg/1.0"
        record_key = "meshpeg"
    elif action == "formula.price":
        lifecycle = "PRICING"
        proof_type = "railpact"
        norm_uri = "v://norm/CoordOS/FormulaPeg/1.0"
        record_key = "railpact"
    else:
        lifecycle = "GATEWAY_SYNC"
        proof_type = "gateway_sync"
        norm_uri = "v://norm/CoordOS/Gateway/1.0"
        record_key = "gateway_sync"

    record = dict(payload)
    record.setdefault("created_at", now_iso)
    state_data = dict(input_sd)
    state_data.update(
        {
            "trip_action": action,
            "trip_executor": executor_uri,
            "executor_did": executor_did,
            "trip_executed_at": now_iso,
            "lifecycle_stage": lifecycle,
            "status": lifecycle,
            "parent_proof_id": input_proof_id,
            "parent_hash": parent_hash,
            "boq_item_uri": boq_item_uri or _to_text(input_sd.get("boq_item_uri") or "").strip(),
            record_key: record,
            f"{record_key}_hash": _sha256_json(record),
            "did_gate": did_gate,
            "geo_location": anchor.get("geo_location"),
            "server_timestamp_proof": anchor.get("server_timestamp_proof"),
            "spatiotemporal_anchor_hash": anchor.get("spatiotemporal_anchor_hash"),
            "geo_compliance": geo_compliance,
            "geo_fence_warning": _to_text(geo_compliance.get("warning") or "").strip(),
        }
    )
    proof_id_seed = hashlib.sha256(f"{input_proof_id}|{action}|{now_iso}".encode("utf-8")).hexdigest()[:16].upper()
    proof_id = f"GP-{record_key.upper()}-{proof_id_seed}"
    created = engine.create(
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_id=project_id,
        project_uri=project_uri,
        segment_uri=segment_uri or boq_item_uri,
        proof_type=proof_type,
        result=result,
        state_data=state_data,
        conditions=_as_list(input_row.get("conditions")),
        parent_proof_id=input_proof_id,
        norm_uri=norm_uri,
        signer_uri=_to_text(executor_uri).strip(),
        signer_role=_to_text(executor_role).strip() or "TRIPROLE",
    )
    return {
        "ok": True,
        "action": action,
        "input_proof_id": input_proof_id,
        "output_proof_id": _to_text(created.get("proof_id") or "").strip(),
        "proof_hash": _to_text(created.get("proof_hash") or "").strip(),
        "proof_type": proof_type,
        "result": result,
        "boq_item_uri": boq_item_uri,
        "did_gate": did_gate,
        "geo_compliance": geo_compliance,
        "spatiotemporal_anchor_hash": _to_text(anchor.get("spatiotemporal_anchor_hash") or "").strip(),
    }


def maybe_execute_special_action(
    *,
    action: str,
    sb: Any,
    engine: Any,
    input_row: dict[str, Any],
    payload: dict[str, Any],
    input_proof_id: str,
    executor_uri: str,
    executor_role: str,
    executor_did: str,
    credentials_vc_raw: Any,
    segment_uri_override: str,
    boq_item_uri_override: str,
    body_geo_location_raw: Any,
    body_server_timestamp_raw: Any,
    execute_scan_entry_action_fn: Callable[..., dict[str, Any]] = execute_scan_entry_action,
    execute_gateway_style_action_fn: Callable[..., dict[str, Any]] = execute_gateway_style_action,
) -> dict[str, Any] | None:
    if action == "scan.entry":
        return execute_scan_entry_action_fn(
            sb=sb,
            engine=engine,
            input_row=input_row,
            payload=payload,
            input_proof_id=input_proof_id,
            executor_uri=executor_uri,
            executor_role=executor_role,
            executor_did=executor_did,
            credentials_vc_raw=credentials_vc_raw,
            segment_uri_override=segment_uri_override,
            boq_item_uri_override=boq_item_uri_override,
            body_geo_location_raw=body_geo_location_raw,
            body_server_timestamp_raw=body_server_timestamp_raw,
        )

    if action in {"meshpeg.verify", "formula.price", "gateway.sync"}:
        return execute_gateway_style_action_fn(
            sb=sb,
            engine=engine,
            input_row=input_row,
            payload=payload,
            action=action,
            input_proof_id=input_proof_id,
            executor_uri=executor_uri,
            executor_role=executor_role,
            executor_did=executor_did,
            credentials_vc_raw=credentials_vc_raw,
            segment_uri_override=segment_uri_override,
            boq_item_uri_override=boq_item_uri_override,
            body_geo_location_raw=body_geo_location_raw,
            body_server_timestamp_raw=body_server_timestamp_raw,
        )

    return None


__all__ = [
    "execute_scan_entry_action",
    "execute_gateway_style_action",
    "maybe_execute_special_action",
]
