"""Request parsing helpers for TripRole action execution."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    normalize_action as _normalize_action,
    to_text as _to_text,
)


def _read_body_value(body: Any, key: str) -> Any:
    if isinstance(body, dict):
        return body.get(key)
    return getattr(body, key, None)


def parse_triprole_action_request(*, body: Any, valid_actions: set[str]) -> dict[str, Any]:
    action = _normalize_action(_read_body_value(body, "action"))
    if action not in valid_actions:
        raise HTTPException(400, f"unsupported action: {action}")

    input_proof_id = _to_text(_read_body_value(body, "input_proof_id")).strip()
    if not input_proof_id:
        raise HTTPException(400, "input_proof_id is required")

    executor_uri = _to_text(_read_body_value(body, "executor_uri")).strip()
    if not executor_uri:
        raise HTTPException(400, "executor_uri is required")

    executor_role = _to_text(_read_body_value(body, "executor_role")).strip() or "TRIPROLE"
    executor_did = _to_text(_read_body_value(body, "executor_did")).strip()
    override_result = _to_text(_read_body_value(body, "result")).strip()
    offline_packet_id = _to_text(_read_body_value(body, "offline_packet_id")).strip()

    payload_raw = _read_body_value(body, "payload")
    payload = _as_dict(payload_raw)
    credentials_vc_raw = _read_body_value(body, "credentials_vc")
    signer_metadata_raw = _read_body_value(body, "signer_metadata")

    if not executor_did:
        executor_did = _to_text(
            payload.get("executor_did")
            or payload.get("operator_did")
            or payload.get("actor_did")
            or ""
        ).strip()
    if credentials_vc_raw is None:
        credentials_vc_raw = payload.get("credentials_vc")
    if signer_metadata_raw is None:
        signer_metadata_raw = payload.get("signer_metadata")

    body_geo_location_raw = _read_body_value(body, "geo_location")
    body_server_timestamp_raw = _read_body_value(body, "server_timestamp_proof")
    boq_item_uri_override = _to_text(_read_body_value(body, "boq_item_uri")).strip()
    segment_uri_override = _to_text(_read_body_value(body, "segment_uri")).strip()

    return {
        "action": action,
        "input_proof_id": input_proof_id,
        "executor_uri": executor_uri,
        "executor_role": executor_role,
        "executor_did": executor_did,
        "override_result": override_result,
        "offline_packet_id": offline_packet_id,
        "payload": payload,
        "credentials_vc_raw": credentials_vc_raw,
        "signer_metadata_raw": signer_metadata_raw,
        "body_geo_location_raw": body_geo_location_raw,
        "body_server_timestamp_raw": body_server_timestamp_raw,
        "boq_item_uri_override": boq_item_uri_override,
        "segment_uri_override": segment_uri_override,
    }


def build_triprole_replayed_response(
    *,
    action: str,
    offline_packet_id: str,
    reused: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "replayed": True,
        "action": action,
        "input_proof_id": _to_text(reused.get("trigger_data", {}).get("input_proof_id") or "").strip(),
        "output_proof_id": reused.get("output_proof_id") or "",
        "proof_hash": reused.get("proof_hash") or "",
        "proof_type": reused.get("proof_type") or "",
        "result": reused.get("result") or "",
        "boq_item_uri": reused.get("boq_item_uri") or "",
        "did_gate": reused.get("did_gate") or {},
        "credit_endorsement": reused.get("credit_endorsement") or {},
        "mirror_sync": reused.get("mirror_sync") or {},
        "spatiotemporal_anchor_hash": reused.get("spatiotemporal_anchor_hash") or "",
        "available_balance": reused.get("available_balance"),
        "offline_packet_id": offline_packet_id,
        "tx": {
            "tx_id": reused.get("tx_id") or "",
            "tx_type": reused.get("tx_type") or "",
            "status": reused.get("tx_status") or "success",
            "reused": True,
        },
    }


__all__ = [
    "parse_triprole_action_request",
    "build_triprole_replayed_response",
]
