"""Offline replay helpers for TripRole execution."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from fastapi import HTTPException
from services.api.domain.execution.triprole_common import as_dict, as_list, parse_iso_epoch_ms, to_float, to_text
from services.api.domain.execution.integrations import ProofUTXOEngine
from services.api.domain.execution.lineage.triprole_lineage import _resolve_boq_item_uri

DEFAULT_OFFLINE_PACKET_SORT_EPOCH = 253402300799000


def _resolve_existing_offline_result(*, sb: Any, offline_packet_id: str) -> dict[str, Any] | None:
    packet_id = to_text(offline_packet_id).strip()
    if not packet_id:
        return None
    try:
        tx_rows = (
            sb.table("proof_transaction")
            .select("*")
            .filter("trigger_data->>offline_packet_id", "eq", packet_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return None
    if not tx_rows:
        return None
    tx_row = tx_rows[0] if isinstance(tx_rows[0], dict) else {}
    output_ids = [to_text(x).strip() for x in as_list(tx_row.get("output_proofs")) if to_text(x).strip()]
    output_id = output_ids[0] if output_ids else ""
    output_row = ProofUTXOEngine(sb).get_by_id(output_id) if output_id else None
    state_data = as_dict((output_row or {}).get("state_data"))
    return {
        "offline_packet_id": packet_id,
        "tx_id": to_text(tx_row.get("tx_id") or "").strip(),
        "tx_type": to_text(tx_row.get("tx_type") or "").strip(),
        "tx_status": to_text(tx_row.get("status") or "").strip(),
        "trigger_action": to_text(tx_row.get("trigger_action") or "").strip(),
        "trigger_data": as_dict(tx_row.get("trigger_data")),
        "output_proof_id": output_id,
        "proof_hash": to_text((output_row or {}).get("proof_hash") or "").strip(),
        "result": to_text((output_row or {}).get("result") or "").strip(),
        "proof_type": to_text((output_row or {}).get("proof_type") or "").strip(),
        "boq_item_uri": _resolve_boq_item_uri(output_row) if isinstance(output_row, dict) else "",
        "spatiotemporal_anchor_hash": to_text(state_data.get("spatiotemporal_anchor_hash") or "").strip(),
        "did_gate": as_dict(state_data.get("did_gate")),
        "credit_endorsement": as_dict(state_data.get("credit_endorsement")),
        "mirror_sync": as_dict(state_data.get("shadow_mirror_sync")),
        "available_balance": to_float(state_data.get("available_quantity")),
    }


def _offline_replay_sort_key(packet: dict[str, Any]) -> tuple[int, int, str]:
    st = as_dict(packet.get("server_timestamp_proof"))
    ntp_client_ts = to_text(st.get("client_timestamp") or st.get("captured_at") or "").strip()
    ntp_epoch = parse_iso_epoch_ms(ntp_client_ts)
    if ntp_epoch is None:
        ntp_epoch = DEFAULT_OFFLINE_PACKET_SORT_EPOCH
    local_created = parse_iso_epoch_ms(packet.get("local_created_at"))
    if local_created is None:
        local_created = DEFAULT_OFFLINE_PACKET_SORT_EPOCH
    packet_id = to_text(packet.get("offline_packet_id") or "").strip()
    return (int(ntp_epoch), int(local_created), packet_id)


def replay_offline_packet(
    *,
    sb: Any,
    packet: dict[str, Any],
    default_executor_uri: str,
    default_executor_role: str,
    apply_variation_fn: Any,
    execute_triprole_action_fn: Any,
) -> dict[str, Any]:
    offline_packet_id = to_text(packet.get("offline_packet_id") or "").strip()
    if not offline_packet_id:
        offline_packet_id = hashlib.sha256(
            json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    packet_type = to_text(packet.get("packet_type") or packet.get("type") or "triprole.execute").strip().lower()
    executor_uri = to_text(packet.get("executor_uri") or default_executor_uri).strip() or default_executor_uri
    executor_did = to_text(packet.get("executor_did") or "").strip()
    executor_role = to_text(packet.get("executor_role") or default_executor_role).strip() or default_executor_role
    geo_location = as_dict(packet.get("geo_location"))
    server_timestamp_proof = as_dict(packet.get("server_timestamp_proof"))

    if packet_type in {"variation.apply", "variation", "delta.apply", "variation.apply.delta"}:
        result = apply_variation_fn(
            sb=sb,
            boq_item_uri=to_text(packet.get("boq_item_uri") or "").strip(),
            delta_amount=float(packet.get("delta_amount")),
            reason=to_text(packet.get("reason") or "").strip(),
            project_uri=to_text(packet.get("project_uri") or "").strip() or None,
            executor_uri=executor_uri,
            executor_did=executor_did,
            executor_role=executor_role,
            offline_packet_id=offline_packet_id,
            metadata=as_dict(packet.get("metadata")),
            credentials_vc=[as_dict(x) for x in as_list(packet.get("credentials_vc"))],
            geo_location=geo_location,
            server_timestamp_proof=server_timestamp_proof,
        )
    else:
        result = execute_triprole_action_fn(
            sb=sb,
            body={
                "action": to_text(packet.get("action") or "").strip(),
                "input_proof_id": to_text(packet.get("input_proof_id") or "").strip(),
                "executor_uri": executor_uri,
                "executor_did": executor_did,
                "executor_role": executor_role,
                "result": to_text(packet.get("result") or "").strip() or None,
                "segment_uri": to_text(packet.get("segment_uri") or "").strip() or None,
                "boq_item_uri": to_text(packet.get("boq_item_uri") or "").strip() or None,
                "signatures": as_list(packet.get("signatures")),
                "consensus_signatures": as_list(packet.get("consensus_signatures")),
                "signer_metadata": as_dict(packet.get("signer_metadata")),
                "payload": as_dict(packet.get("payload")),
                "credentials_vc": [as_dict(x) for x in as_list(packet.get("credentials_vc"))],
                "geo_location": geo_location,
                "server_timestamp_proof": server_timestamp_proof,
                "offline_packet_id": offline_packet_id,
            },
        )

    return {
        "offline_packet_id": offline_packet_id,
        "packet_type": packet_type,
        "result": result,
    }


def replay_offline_packets_batch(
    *,
    sb: Any,
    packets: list[dict[str, Any]],
    stop_on_error: bool = False,
    default_executor_uri: str = "v://executor/system/",
    default_executor_role: str = "TRIPROLE",
    apply_variation_fn: Any,
    execute_triprole_action_fn: Any,
    replay_offline_packet_fn: Callable[..., dict[str, Any]] = replay_offline_packet,
    sort_key_fn: Callable[[dict[str, Any]], tuple[int, int, str]] = _offline_replay_sort_key,
) -> dict[str, Any]:
    normalized_packets = [x for x in packets if isinstance(x, dict)]
    normalized_packets.sort(key=sort_key_fn)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, packet in enumerate(normalized_packets, start=1):
        offline_packet_id = to_text(packet.get("offline_packet_id") or "").strip()
        packet_type = to_text(packet.get("packet_type") or packet.get("type") or "triprole.execute").strip().lower()
        try:
            replayed = replay_offline_packet_fn(
                sb=sb,
                packet=packet,
                default_executor_uri=default_executor_uri,
                default_executor_role=default_executor_role,
                apply_variation_fn=apply_variation_fn,
                execute_triprole_action_fn=execute_triprole_action_fn,
            )
            offline_packet_id = to_text(replayed.get("offline_packet_id") or "").strip()
            packet_type = to_text(replayed.get("packet_type") or "").strip().lower()
            result = replayed.get("result")
            results.append(
                {
                    "offline_packet_id": offline_packet_id,
                    "packet_index": idx,
                    "packet_type": packet_type,
                    "ok": True,
                    "result": result,
                }
            )
        except HTTPException as exc:
            errors.append(
                {
                    "offline_packet_id": offline_packet_id,
                    "packet_index": idx,
                    "packet_type": packet_type,
                    "status_code": exc.status_code,
                    "detail": to_text(exc.detail).strip(),
                }
            )
            if stop_on_error:
                break
        except Exception as exc:  # pragma: no cover
            errors.append(
                {
                    "offline_packet_id": offline_packet_id,
                    "packet_index": idx,
                    "packet_type": packet_type,
                    "status_code": 500,
                    "detail": to_text(exc).strip() or "offline replay failed",
                }
            )
            if stop_on_error:
                break

    return {
        "ok": len(errors) == 0,
        "replayed_count": len(results),
        "error_count": len(errors),
        "stop_on_error": bool(stop_on_error),
        "results": results,
        "errors": errors,
    }


__all__ = [
    "DEFAULT_OFFLINE_PACKET_SORT_EPOCH",
    "_resolve_existing_offline_result",
    "_offline_replay_sort_key",
    "replay_offline_packet",
    "replay_offline_packets_batch",
]
