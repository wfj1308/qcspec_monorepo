"""
Transaction helpers for ProofUTXOEngine.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from postgrest.exceptions import APIError
from supabase import Client


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _normalize_boq_uri_from_segment(segment_uri: str) -> str:
    uri = _to_text(segment_uri).strip()
    if not uri.startswith("v://") or "/boq/" not in uri:
        return ""
    token = "/spu-mapping/"
    if token in uri:
        uri = uri.split(token, 1)[0]
    return uri.rstrip("/")


def _extract_boq_uri(*, segment_uri: str, state_data: Dict[str, Any]) -> str:
    for key in ("boq_item_canonical_uri", "boq_item_v_uri", "boq_item_uri"):
        text = _to_text(state_data.get(key)).strip()
        if text.startswith("v://"):
            return text.rstrip("/")
    ref = _as_dict(state_data.get("project_boq_item_ref"))
    ref_uri = _to_text(ref.get("boq_v_uri")).strip()
    if ref_uri.startswith("v://"):
        return ref_uri.rstrip("/")
    return _normalize_boq_uri_from_segment(segment_uri)


def _sync_boq_markdown_after_consume(
    *,
    sb: Client,
    project_uri: str,
    boq_v_uris: List[str],
    actor_uri: str,
    reason: str,
) -> None:
    if not boq_v_uris:
        return
    try:
        from services.api.domain.boq.runtime.boq_item_markdown import sync_boq_item_markdowns_for_uris

        sync_boq_item_markdowns_for_uris(
            sb=sb,
            project_uri=project_uri,
            boq_v_uris=boq_v_uris,
            actor_uri=actor_uri,
            reason=reason or "utxo.consume",
            write_file=True,
        )
    except Exception:
        return


def create_proof_row(
    *,
    sb: Client,
    proof_id: str,
    owner_uri: str,
    project_uri: str,
    project_id: Optional[str],
    proof_type: str,
    result: str,
    state_data: Optional[Dict[str, Any]],
    conditions: Optional[List[Dict[str, Any]]],
    parent_proof_id: Optional[str],
    norm_uri: Optional[str],
    segment_uri: Optional[str],
    signer_uri: Optional[str],
    signer_role: str,
    gitpeg_anchor: Optional[str],
    anchor_config: Optional[Dict[str, Any]],
    created_at: Optional[str],
    normalize_type: Callable[[str], str],
    normalize_result: Callable[[str], str],
    utc_now_iso: Callable[[], str],
    ordosign: Callable[[str, str], str],
    get_by_id: Callable[[str], Optional[Dict[str, Any]]],
    try_gitpeg_anchor: Callable[..., str],
) -> Dict[str, Any]:
    now_iso = str(created_at or utc_now_iso())
    ptype = normalize_type(proof_type)
    presult = normalize_result(result)
    depth = 0
    if parent_proof_id:
        parent = get_by_id(parent_proof_id)
        depth = int(parent.get("depth") or 0) + 1 if parent else 0

    payload_for_hash = {
        "proof_id": str(proof_id),
        "owner_uri": str(owner_uri),
        "project_uri": str(project_uri),
        "project_id": project_id,
        "segment_uri": segment_uri,
        "proof_type": ptype,
        "result": presult,
        "state_data": state_data or {},
        "conditions": conditions or [],
        "parent_proof_id": parent_proof_id,
        "norm_uri": norm_uri,
    }
    proof_hash = hashlib.sha256(
        json.dumps(payload_for_hash, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    signed_by: List[Dict[str, Any]] = []
    if signer_uri:
        signed_by = [
            {
                "executor_uri": signer_uri,
                "role": str(signer_role or "AI").upper(),
                "ordosign_hash": ordosign(str(proof_id), str(signer_uri)),
                "ts": now_iso,
            }
        ]

    row: Dict[str, Any] = {
        "proof_id": str(proof_id),
        "proof_hash": proof_hash,
        "owner_uri": str(owner_uri),
        "project_id": project_id,
        "project_uri": str(project_uri),
        "segment_uri": segment_uri,
        "proof_type": ptype,
        "result": presult,
        "state_data": state_data or {},
        "spent": False,
        "spend_tx_id": None,
        "spent_at": None,
        "conditions": conditions or [],
        "parent_proof_id": parent_proof_id,
        "depth": depth,
        "norm_uri": norm_uri,
        "gitpeg_anchor": gitpeg_anchor,
        "signed_by": signed_by,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    try:
        sb.table("proof_utxo").insert(row).execute()
        resolved_anchor = str(gitpeg_anchor or "").strip()
        if not resolved_anchor:
            resolved_anchor = try_gitpeg_anchor(
                proof_hash=proof_hash,
                proof_id=str(proof_id),
                project_id=project_id,
                project_uri=str(project_uri),
                owner_uri=str(owner_uri),
                proof_type=str(ptype),
                result=str(presult),
                state_data=state_data or {},
                anchor_config=anchor_config,
            )
        if resolved_anchor:
            sb.table("proof_utxo").update({"gitpeg_anchor": resolved_anchor}).eq(
                "proof_id", str(proof_id)
            ).execute()
            row["gitpeg_anchor"] = resolved_anchor
        return row
    except APIError as exc:
        if "duplicate key value" not in str(exc).lower():
            raise
        existing = get_by_id(str(proof_id))
        if existing:
            return existing
        raise


def consume_proofs(
    *,
    sb: Client,
    input_proof_ids: List[str],
    output_states: List[Dict[str, Any]],
    executor_uri: str,
    executor_role: str,
    trigger_action: Optional[str],
    trigger_data: Optional[Dict[str, Any]],
    tx_type: str,
    anchor_config: Optional[Dict[str, Any]],
    load_inputs: Callable[[List[str]], Dict[str, Dict[str, Any]]],
    check_conditions: Callable[[Dict[str, Any], str, str], Tuple[bool, str]],
    create_callback: Callable[..., Dict[str, Any]],
    gen_tx_id: Callable[[], str],
    utc_now_iso: Callable[[], str],
    ordosign: Callable[[str, str], str],
) -> Dict[str, Any]:
    if not input_proof_ids:
        raise ValueError("input_proof_ids is required")
    if not output_states:
        raise ValueError("output_states is required")

    proof_map = load_inputs(input_proof_ids)
    for pid in input_proof_ids:
        proof = proof_map.get(pid)
        if not proof:
            raise ValueError(f"proof {pid} not found")
        if bool(proof.get("spent")):
            raise ValueError(f"proof {pid} already spent")
        ok, reason = check_conditions(proof, executor_uri, executor_role)
        if not ok:
            raise PermissionError(reason)

    tx_id = gen_tx_id()
    now_iso = utc_now_iso()
    output_proofs: List[str] = []
    touched_boq_uris: List[str] = []
    first_input = proof_map[input_proof_ids[0]]
    parent_id = input_proof_ids[0]
    first_project_uri = _to_text(first_input.get("project_uri")).strip()
    for pid in input_proof_ids:
        src = proof_map.get(pid) or {}
        src_state = _as_dict(src.get("state_data"))
        boq_uri = _extract_boq_uri(
            segment_uri=_to_text(src.get("segment_uri")).strip(),
            state_data=src_state,
        )
        if boq_uri and boq_uri not in touched_boq_uris:
            touched_boq_uris.append(boq_uri)

    for output in output_states:
        created = create_callback(
            proof_id=str(output.get("proof_id") or f"GP-PROOF-{uuid.uuid4().hex[:16].upper()}"),
            owner_uri=str(output.get("owner_uri") or first_input.get("owner_uri")),
            project_id=output.get("project_id") or first_input.get("project_id"),
            project_uri=str(output.get("project_uri") or first_input.get("project_uri")),
            segment_uri=output.get("segment_uri") or first_input.get("segment_uri"),
            proof_type=str(output.get("proof_type") or "inspection"),
            result=str(output.get("result") or "PENDING"),
            state_data=output.get("state_data") or {},
            conditions=output.get("conditions") or [],
            parent_proof_id=str(output.get("parent_proof_id") or parent_id),
            norm_uri=output.get("norm_uri"),
            signer_uri=executor_uri,
            signer_role=executor_role,
            gitpeg_anchor=output.get("gitpeg_anchor"),
            anchor_config=anchor_config,
            created_at=now_iso,
        )
        output_proofs.append(str(created["proof_id"]))
        out_state = _as_dict(output.get("state_data"))
        boq_uri = _extract_boq_uri(
            segment_uri=_to_text(output.get("segment_uri") or first_input.get("segment_uri")).strip(),
            state_data=out_state,
        )
        if boq_uri and boq_uri not in touched_boq_uris:
            touched_boq_uris.append(boq_uri)

    tx_row = {
        "tx_id": tx_id,
        "tx_type": tx_type if tx_type in {"consume", "merge", "split", "settle", "archive"} else "consume",
        "input_proofs": input_proof_ids,
        "output_proofs": output_proofs,
        "trigger_action": trigger_action,
        "trigger_data": trigger_data or {},
        "executor_uri": executor_uri,
        "ordosign_hash": ordosign(tx_id, executor_uri),
        "status": "success",
        "error_msg": None,
        "created_at": now_iso,
    }
    sb.table("proof_transaction").insert(tx_row).execute()
    for pid in input_proof_ids:
        sb.table("proof_utxo").update(
            {"spent": True, "spend_tx_id": tx_id, "spent_at": now_iso}
        ).eq("proof_id", pid).execute()
    _sync_boq_markdown_after_consume(
        sb=sb,
        project_uri=first_project_uri,
        boq_v_uris=touched_boq_uris,
        actor_uri=executor_uri,
        reason=trigger_action or tx_type,
    )
    return tx_row


def auto_consume_inspection_pass_flow(
    *,
    sb: Client,
    inspection_proof_id: str,
    executor_uri: str,
    executor_role: str,
    trigger_action: str,
    anchor_config: Optional[Dict[str, Any]],
    get_by_id: Callable[[str], Optional[Dict[str, Any]]],
    consume_callback: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    inspection = get_by_id(inspection_proof_id)
    if not inspection:
        return {"attempted": False, "success": False, "reason": "inspection_proof_not_found"}
    if str(inspection.get("proof_type") or "") != "inspection":
        return {"attempted": False, "success": False, "reason": "proof_type_not_inspection"}
    if str(inspection.get("result") or "") != "PASS":
        return {"attempted": False, "success": False, "reason": "inspection_not_pass"}
    if bool(inspection.get("spent")):
        return {"attempted": False, "success": False, "reason": "inspection_already_spent"}

    project_uri = str(inspection.get("project_uri") or "").strip()
    if not project_uri:
        return {"attempted": False, "success": False, "reason": "project_uri_missing"}
    segment_uri = str(inspection.get("segment_uri") or "").strip() or None

    sdata = inspection.get("state_data") if isinstance(inspection.get("state_data"), dict) else {}
    stake = str(sdata.get("stake") or sdata.get("location") or "").strip()

    labs = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", project_uri)
        .eq("proof_type", "lab")
        .eq("result", "PASS")
        .eq("spent", False)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
        or []
    )
    if segment_uri:
        labs = [x for x in labs if str(x.get("segment_uri") or "").strip() == segment_uri]
    if stake:
        stake_matched = []
        for lab in labs:
            ld = lab.get("state_data") if isinstance(lab.get("state_data"), dict) else {}
            l_stake = str(ld.get("stake") or ld.get("location") or "").strip()
            if l_stake == stake:
                stake_matched.append(lab)
        if stake_matched:
            labs = stake_matched
    if not labs:
        return {"attempted": True, "success": False, "reason": "no_unspent_lab_pass"}

    lab = labs[0]
    output_state = {
        "proof_type": "payment",
        "result": "PASS",
        "owner_uri": inspection.get("owner_uri"),
        "project_id": inspection.get("project_id"),
        "project_uri": project_uri,
        "segment_uri": segment_uri,
        "conditions": [{"type": "role", "value": "SUPERVISOR"}],
        "state_data": {
            "source": "auto_settle_gate",
            "stake": stake,
            "inspection_proof_id": inspection.get("proof_id"),
            "lab_proof_id": lab.get("proof_id"),
            "inspection_state": sdata,
            "lab_state": lab.get("state_data") if isinstance(lab.get("state_data"), dict) else {},
        },
        "parent_proof_id": inspection.get("proof_id"),
    }
    tx = consume_callback(
        input_proof_ids=[str(lab.get("proof_id")), str(inspection.get("proof_id"))],
        output_states=[output_state],
        executor_uri=executor_uri,
        executor_role=executor_role,
        trigger_action=trigger_action,
        trigger_data={
            "source": "inspection_pass",
            "inspection_proof_id": inspection.get("proof_id"),
            "lab_proof_id": lab.get("proof_id"),
            "stake": stake,
        },
        tx_type="settle",
        anchor_config=anchor_config,
    )
    return {
        "attempted": True,
        "success": True,
        "reason": "auto_settle_ok",
        "tx": tx,
    }
