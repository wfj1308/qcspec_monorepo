"""Post-execution enrichment helpers for TripRole actions."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)


def run_triprole_postprocess(
    *,
    sb: Any,
    action: str,
    payload: dict[str, Any],
    output_proof_id: str,
    output_row: dict[str, Any],
    next_state: dict[str, Any],
    input_proof_id: str,
    next_result: str,
    boq_item_uri: str,
    now_iso: str,
    executor_uri: str,
    project_uri: str,
    executor_did: str,
    did_gate: dict[str, Any],
    tx: dict[str, Any],
    update_chain_with_result_fn: Callable[..., dict[str, Any]],
    open_remediation_trip_fn: Callable[..., dict[str, Any]],
    calculate_sovereign_credit_fn: Callable[..., dict[str, Any]],
    sync_to_mirrors_fn: Callable[..., dict[str, Any]],
    build_shadow_packet_fn: Callable[..., dict[str, Any]],
    patch_state_data_fields_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    quality_chain_writeback: dict[str, Any] = {}
    remediation: dict[str, Any] = {}
    if action == "quality.check":
        quality_chain_writeback = update_chain_with_result_fn(
            sb=sb,
            gate_output={
                **_as_dict(next_state.get("qc_gate_result")),
                "input_proof_id": input_proof_id,
                "output_proof_id": output_proof_id,
                "result": _to_text(next_result or "").strip().upper(),
                "result_source": _to_text(next_state.get("result_source") or "").strip(),
                "spec_uri": _to_text(next_state.get("spec_uri") or "").strip(),
                "spec_snapshot": _to_text(next_state.get("spec_snapshot") or "").strip(),
                "quality_hash": _to_text(next_state.get("quality_hash") or "").strip(),
                "boq_item_uri": boq_item_uri,
                "linked_gate_id": _to_text(next_state.get("linked_gate_id") or "").strip(),
                "linked_gate_ids": _as_list(next_state.get("linked_gate_ids")),
                "linked_gate_rules": _as_list(next_state.get("linked_gate_rules")),
                "evaluated_at": now_iso,
            },
        )
        if _as_dict(quality_chain_writeback.get("state_data")):
            output_row["state_data"] = _as_dict(quality_chain_writeback.get("state_data"))
        if _to_text(output_row.get("result") or "").strip().upper() == "FAIL":
            try:
                remediation = open_remediation_trip_fn(
                    sb=sb,
                    fail_proof_id=output_proof_id,
                    notice=_to_text(payload.get("remediation_notice") or "Auto remediation notice").strip(),
                    executor_uri=executor_uri,
                    due_date=_to_text(payload.get("remediation_due_date") or "").strip(),
                    assignees=[
                        _to_text(x).strip()
                        for x in _as_list(payload.get("remediation_assignees"))
                        if _to_text(x).strip()
                    ],
                )
            except Exception as exc:
                remediation = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}

    credit_endorsement: dict[str, Any] = {}
    mirror_sync: dict[str, Any] = {}
    try:
        credit_endorsement = calculate_sovereign_credit_fn(
            sb=sb,
            project_uri=project_uri,
            participant_did=executor_did,
        )
    except Exception:
        credit_endorsement = {}
    try:
        mirror_sync = sync_to_mirrors_fn(
            proof_packet=build_shadow_packet_fn(
                output_row=output_row,
                tx=tx,
                action=action,
                did_gate=did_gate,
                credit_endorsement=credit_endorsement,
            ),
            sb=sb,
            project_id=_to_text(output_row.get("project_id") or "").strip(),
            project_uri=_to_text(output_row.get("project_uri") or "").strip(),
        )
    except Exception:
        mirror_sync = {"attempted": True, "synced": False, "error": "mirror_sync_failed"}

    patched_state = patch_state_data_fields_fn(
        sb=sb,
        proof_id=output_proof_id,
        patch={
            "credit_endorsement": credit_endorsement,
            "shadow_mirror_sync": mirror_sync,
        },
    )
    if patched_state:
        output_row["state_data"] = patched_state

    return {
        "output_row": output_row,
        "quality_chain_writeback": quality_chain_writeback,
        "remediation": remediation,
        "credit_endorsement": credit_endorsement,
        "mirror_sync": mirror_sync,
    }


__all__ = ["run_triprole_postprocess"]
