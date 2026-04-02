"""Sensor ingest operation for TripRole execution."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.integrations import (
    ProofUTXOEngine,
    calculate_sovereign_credit,
    resolve_required_credential,
    sync_to_mirrors,
    verify_credential,
)
from services.api.domain.execution.triprole_asset import _resolve_latest_boq_row
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
    utc_iso as _utc_iso,
)
from services.api.domain.execution.triprole_geo_sensor import (
    build_spatiotemporal_anchor as _build_spatiotemporal_anchor,
    decode_sensor_payload as _decode_sensor_payload,
    normalize_sensor_payload as _normalize_sensor_payload,
)
from services.api.domain.execution.triprole_lineage import _is_leaf_boq_row
from services.api.domain.execution.triprole_shadow import _build_shadow_packet
from services.api.domain.execution.triprole_writeback import _patch_state_data_fields


def ingest_sensor_data(
    *,
    sb: Any,
    device_id: str,
    raw_payload: Any,
    boq_item_uri: str,
    project_uri: str | None = None,
    executor_uri: str = "v://executor/system/",
    executor_did: str = "",
    executor_role: str = "TRIPROLE",
    metadata: dict[str, Any] | None = None,
    credentials_vc: list[dict[str, Any]] | None = None,
    geo_location: dict[str, Any] | None = None,
    server_timestamp_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_device_id = _to_text(device_id).strip()
    if not normalized_device_id:
        raise HTTPException(400, "device_id is required")
    normalized_boq_item_uri = _to_text(boq_item_uri).strip()
    if not normalized_boq_item_uri.startswith("v://"):
        raise HTTPException(400, "boq_item_uri is required and must start with v://")

    parsed_payload, raw_payload_hash = _decode_sensor_payload(raw_payload)
    sensor_data = _normalize_sensor_payload(normalized_device_id, parsed_payload)
    if not sensor_data["boq_item_uri"]:
        sensor_data["boq_item_uri"] = normalized_boq_item_uri
    if sensor_data["boq_item_uri"] != normalized_boq_item_uri:
        raise HTTPException(409, "sensor payload boq_item_uri mismatch")

    expected_hash = _to_text(
        parsed_payload.get("payload_hash")
        or parsed_payload.get("packet_hash")
        or parsed_payload.get("raw_payload_hash")
        or ""
    ).strip().lower()
    if expected_hash and expected_hash not in {
        _to_text(sensor_data.get("sensor_payload_hash") or "").strip().lower(),
        _to_text(raw_payload_hash).strip().lower(),
    }:
        raise HTTPException(409, "sensor payload hash mismatch")

    latest_row = _resolve_latest_boq_row(sb=sb, boq_item_uri=normalized_boq_item_uri, project_uri=project_uri)
    if isinstance(latest_row, dict) and (not _is_leaf_boq_row(latest_row)):
        raise HTTPException(409, "sensor ingest is only allowed for leaf BOQ nodes")
    resolved_project_uri = _to_text(
        project_uri
        or (latest_row or {}).get("project_uri")
        or parsed_payload.get("project_uri")
        or ""
    ).strip()
    if not resolved_project_uri.startswith("v://"):
        raise HTTPException(400, "project_uri is required for sensor ingest")
    resolved_project_id = (latest_row or {}).get("project_id")
    resolved_owner_uri = _to_text((latest_row or {}).get("owner_uri") or executor_uri).strip() or executor_uri
    resolved_segment_uri = _to_text((latest_row or {}).get("segment_uri") or normalized_boq_item_uri).strip()
    parent_proof_id = _to_text((latest_row or {}).get("proof_id") or "").strip() or None

    required_credential = resolve_required_credential(
        action="measure.record",
        boq_item_uri=normalized_boq_item_uri,
        payload=parsed_payload,
    )
    did_gate = verify_credential(
        sb=sb,
        user_did=_to_text(executor_did).strip(),
        required_credential=required_credential,
        project_uri=resolved_project_uri,
        boq_item_uri=normalized_boq_item_uri,
        payload_credentials=credentials_vc,
    )
    if not bool(did_gate.get("ok")):
        raise HTTPException(
            403,
            f"DID gate rejected: {did_gate.get('reason')}; required={did_gate.get('required_credential')}",
        )

    now_iso = _utc_iso()
    anchor = _build_spatiotemporal_anchor(
        action="sensor.ingest",
        input_proof_id=parent_proof_id or normalized_boq_item_uri,
        executor_uri=_to_text(executor_uri).strip(),
        now_iso=now_iso,
        geo_location_raw=geo_location if geo_location else parsed_payload.get("geo_location"),
        server_timestamp_raw=(
            server_timestamp_proof
            if server_timestamp_proof
            else parsed_payload.get("server_timestamp_proof")
        ),
    )

    state_data = {
        "trip_action": "sensor.ingest",
        "trip_executor": _to_text(executor_uri).strip(),
        "executor_did": _to_text(executor_did).strip(),
        "trip_executed_at": now_iso,
        "lifecycle_stage": "PRECHECK",
        "status": "PRECHECK",
        "boq_item_uri": normalized_boq_item_uri,
        "measurement": {
            "value": sensor_data.get("value"),
            "values": sensor_data.get("values"),
            "unit": sensor_data.get("unit"),
            "measured_at": sensor_data.get("measured_at"),
            "source": "iot_direct",
        },
        "sensor_hardware": sensor_data.get("sensor_hardware"),
        "sensor_payload_hash": sensor_data.get("sensor_payload_hash"),
        "sensor_reading_hash": sensor_data.get("sensor_reading_hash"),
        "sensor_raw_payload_hash": raw_payload_hash,
        "did_gate": did_gate,
        "metadata": _as_dict(metadata),
        "parent_proof_id": parent_proof_id,
        **anchor,
    }

    seed = hashlib.sha256(
        f"{normalized_device_id}|{normalized_boq_item_uri}|{now_iso}|{sensor_data.get('sensor_reading_hash')}".encode(
            "utf-8"
        )
    ).hexdigest()[:16].upper()
    proof_id = f"GP-PROOF-{seed}"
    engine = ProofUTXOEngine(sb)
    created = engine.create(
        proof_id=proof_id,
        owner_uri=resolved_owner_uri,
        project_id=resolved_project_id,
        project_uri=resolved_project_uri,
        segment_uri=resolved_segment_uri,
        proof_type="inspection",
        result="PENDING",
        state_data=state_data,
        conditions=_as_list((latest_row or {}).get("conditions")),
        parent_proof_id=parent_proof_id,
        norm_uri=_to_text((latest_row or {}).get("norm_uri") or "").strip() or None,
        signer_uri=_to_text(executor_uri).strip(),
        signer_role=_to_text(executor_role).strip() or "TRIPROLE",
    )

    credit_endorsement: dict[str, Any] = {}
    if _to_text(executor_did).strip().startswith("did:"):
        try:
            credit_endorsement = calculate_sovereign_credit(
                sb=sb,
                project_uri=resolved_project_uri,
                participant_did=_to_text(executor_did).strip(),
            )
        except Exception:
            credit_endorsement = {}
    try:
        mirror_sync = sync_to_mirrors(
            proof_packet=_build_shadow_packet(
                output_row=created,
                tx={"tx_id": "", "tx_type": "create", "trigger_action": "TripRole(sensor.ingest)", "created_at": now_iso},
                action="sensor.ingest",
                did_gate=did_gate,
                credit_endorsement=credit_endorsement,
            ),
            sb=sb,
            project_id=_to_text(created.get("project_id") or "").strip(),
            project_uri=_to_text(created.get("project_uri") or "").strip(),
        )
    except Exception:
        mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}
    patched_state = _patch_state_data_fields(
        sb=sb,
        proof_id=_to_text(created.get("proof_id") or "").strip(),
        patch={
            "credit_endorsement": credit_endorsement,
            "shadow_mirror_sync": mirror_sync,
        },
    )
    if patched_state:
        created["state_data"] = patched_state

    return {
        "ok": True,
        "action": "sensor.ingest",
        "proof_id": _to_text(created.get("proof_id") or "").strip(),
        "proof_hash": _to_text(created.get("proof_hash") or "").strip(),
        "project_uri": resolved_project_uri,
        "boq_item_uri": normalized_boq_item_uri,
        "sensor_hardware": sensor_data.get("sensor_hardware"),
        "measurement": state_data.get("measurement"),
        "did_gate": did_gate,
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
        "spatiotemporal_anchor_hash": _to_text(anchor.get("spatiotemporal_anchor_hash") or "").strip(),
    }


__all__ = [
    "ingest_sensor_data",
]
