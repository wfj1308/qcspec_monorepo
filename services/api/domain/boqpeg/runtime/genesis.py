"""BOQPeg genesis builder based on BOQ UTXO runtime."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any

from services.api.domain.boq.runtime.utxo import BoqItem, initialize_boq_utxos
from services.api.domain.boq.runtime.boq_item_markdown import sync_boq_item_markdowns_from_chain
from services.api.domain.boqpeg.runtime.bridge_entity import bind_bridge_sub_items, create_bridge_entity
from services.api.domain.boqpeg.runtime.ref_binding import validate_ref_only_rows
from services.api.domain.boqpeg.runtime.spu_mapping import map_spu_to_boq_preview_rows
from services.api.domain.utxo.integrations import ProofUTXOEngine


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _slug_token(value: Any) -> str:
    text = re.sub(r"\s+", "-", _to_text(value).strip().lower())
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "bridge"


def _stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _derive_bridge_meta(*, project_uri: str, raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        bridge_uri = _to_text(raw.get("bridge_uri") or "").strip()
        bridge_name = _to_text(raw.get("bridge_name") or "").strip()
        parent_section = _to_text(raw.get("parent_section") or "").strip()
        boq_chapter = _to_text(raw.get("boq_chapter") or "").strip()
    else:
        text = _to_text(raw).strip()
        bridge_uri = text if text.startswith("v://") else ""
        bridge_name = "" if bridge_uri else text
        parent_section = ""
        boq_chapter = ""

    if not bridge_uri and bridge_name:
        bridge_uri = f"{project_uri.rstrip('/')}/bridge/{_slug_token(bridge_name)}"
    if bridge_uri and not bridge_name:
        bridge_name = bridge_uri.rstrip("/").split("/")[-1]
    return {
        "bridge_uri": bridge_uri.rstrip("/"),
        "bridge_name": bridge_name or bridge_uri.rstrip("/").split("/")[-1],
        "parent_section": parent_section,
        "boq_chapter": boq_chapter or "400",
    }


def _normalize_bridge_mappings(
    *,
    project_uri: str,
    bridge_mappings: dict[str, Any] | None,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    item_to_bridge_uri: dict[str, str] = {}
    bridge_by_uri: dict[str, dict[str, str]] = {}

    for raw_key, raw_value in (bridge_mappings or {}).items():
        key = _to_text(raw_key).strip()
        if not key:
            continue
        bridge_meta = _derive_bridge_meta(project_uri=project_uri, raw=raw_value)
        bridge_uri = _to_text(bridge_meta.get("bridge_uri") or "").strip()
        if not bridge_uri:
            continue
        bridge_by_uri[bridge_uri] = bridge_meta

        key_candidates = {key, key.lower(), key.rstrip("/"), key.rstrip("/").lower()}
        if "/" in key:
            tail = key.rstrip("/").split("/")[-1]
            if tail:
                key_candidates.add(tail)
                key_candidates.add(tail.lower())
        for candidate in key_candidates:
            if candidate:
                item_to_bridge_uri[candidate] = bridge_uri

    return item_to_bridge_uri, list(bridge_by_uri.values())


def _create_scan_complete_proof(
    *,
    sb: Any,
    commit: bool,
    project_uri: str,
    owner_uri: str,
    source_file: str,
    total_items: int,
    total_nodes: int,
    leaf_nodes: int,
    success_count: int,
    bridge_count: int,
    ref_only_validation: dict[str, Any],
) -> dict[str, Any]:
    now_iso = datetime.now(UTC).isoformat()
    state_data = {
        "proof_kind": "boq.scan_complete",
        "action": "boq.scan_complete",
        "project_uri": project_uri,
        "source_file": source_file,
        "total_items": int(total_items),
        "total_nodes": int(total_nodes),
        "leaf_nodes": int(leaf_nodes),
        "success_count": int(success_count),
        "bridge_count": int(bridge_count),
        "ref_only_validation": ref_only_validation,
        "timestamp": now_iso,
    }
    proof_hash = _stable_hash(state_data)
    proof_id = f"GP-BOQ-SCAN-{proof_hash[:18].upper()}"
    segment_uri = f"{project_uri.rstrip('/')}/boqpeg/scan/{proof_hash[:16]}"
    proof = {
        "proof_id": proof_id,
        "proof_hash": proof_hash,
        "segment_uri": segment_uri,
        "state_data": state_data,
        "committed": False,
    }
    if not commit or sb is None:
        return proof
    row = ProofUTXOEngine(sb).create(
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type="inspection",
        result="PASS",
        state_data=state_data,
        norm_uri="v://norm/NormPeg/BOQPeg/ScanComplete/1.0",
        segment_uri=segment_uri,
        signer_uri=owner_uri,
        signer_role="SYSTEM",
    )
    proof["committed"] = True
    proof["row"] = row
    proof["proof_hash"] = _to_text(row.get("proof_hash") or "").strip() or proof_hash
    return proof


def _infer_component_type(item_no: str, item_name: str) -> str:
    code = _to_text(item_no).strip()
    name = _to_text(item_name).strip().lower()
    if "pile" in name or "妗" in name or code.startswith("401") or code.startswith("402") or code.startswith("403"):
        return "pile"
    if "cap" in name or "承台" in name:
        return "cap"
    return "boq_item"


def initialize_boq_genesis_chain(
    *,
    sb: Any,
    project_uri: str,
    project_id: str | None,
    boq_items: list[BoqItem],
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    source_file: str,
    commit: bool,
    bridge_mappings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_owner = _to_text(owner_uri).strip() or f"{project_uri.rstrip('/')}/role/system/"
    item_bridge_map, bridge_metas = _normalize_bridge_mappings(
        project_uri=project_uri,
        bridge_mappings=bridge_mappings,
    )

    registered_bridges: list[dict[str, Any]] = []
    for meta in bridge_metas:
        bridge_name = _to_text(meta.get("bridge_name") or "").strip()
        if not bridge_name:
            continue
        registered_bridges.append(
            create_bridge_entity(
                sb=sb,
                project_uri=project_uri,
                bridge_name=bridge_name,
                parent_section=_to_text(meta.get("parent_section") or "").strip(),
                boq_chapter=_to_text(meta.get("boq_chapter") or "").strip() or "400",
                owner_uri=normalized_owner,
                commit=bool(commit),
            )
        )

    result = initialize_boq_utxos(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id,
        boq_items=boq_items,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=normalized_owner,
        source_file=source_file,
        bridge_mappings=item_bridge_map,
        commit=bool(commit),
    )
    preview_rows = result.get("preview") if isinstance(result.get("preview"), list) else []
    result["ref_only_validation"] = validate_ref_only_rows(preview_rows)

    bridge_subitems: dict[str, list[dict[str, Any]]] = {}
    for row in preview_rows:
        sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
        if not bool(sd.get("is_leaf")):
            continue
        bridge_uri = _to_text(sd.get("bridge_uri") or "").strip()
        if not bridge_uri:
            continue
        boq_item_uri = _to_text(sd.get("boq_item_uri") or "").strip()
        item_no = _to_text(sd.get("item_no") or "").strip()
        item_name = _to_text(sd.get("item_name") or "").strip()
        bridge_subitems.setdefault(bridge_uri, []).append(
            {
                "boq_item_uri": boq_item_uri,
                "boq_code": item_no,
                "description": item_name,
                "component_type": _infer_component_type(item_no, item_name),
            }
        )

    bound_bridges: list[dict[str, Any]] = []
    meta_by_uri = {meta["bridge_uri"]: meta for meta in bridge_metas if _to_text(meta.get("bridge_uri")).strip()}
    for bridge_uri, sub_items in bridge_subitems.items():
        meta = meta_by_uri.get(bridge_uri) or {
            "bridge_uri": bridge_uri,
            "bridge_name": bridge_uri.rstrip("/").split("/")[-1],
            "parent_section": "",
            "boq_chapter": "400",
        }
        bound_bridges.append(
            bind_bridge_sub_items(
                sb=sb,
                project_uri=project_uri,
                bridge_name=_to_text(meta.get("bridge_name") or "").strip(),
                parent_section=_to_text(meta.get("parent_section") or "").strip(),
                boq_chapter=_to_text(meta.get("boq_chapter") or "").strip() or "400",
                sub_items=sub_items,
                owner_uri=normalized_owner,
                commit=bool(commit),
            )
        )

    scan_complete_proof = _create_scan_complete_proof(
        sb=sb,
        commit=bool(commit),
        project_uri=project_uri,
        owner_uri=normalized_owner,
        source_file=source_file,
        total_items=int(result.get("total_items") or 0),
        total_nodes=int(result.get("total_nodes") or 0),
        leaf_nodes=int(result.get("leaf_nodes") or 0),
        success_count=int(result.get("success_count") or 0),
        bridge_count=len(bridge_subitems),
        ref_only_validation=result["ref_only_validation"],
    )
    result["spu_boq_mapping"] = map_spu_to_boq_preview_rows(
        sb=sb,
        commit=bool(commit),
        project_uri=project_uri,
        owner_uri=normalized_owner,
        source_file=source_file,
        preview_rows=preview_rows,
    )
    mapping_rows = (
        result.get("spu_boq_mapping", {}).get("mappings")
        if isinstance(result.get("spu_boq_mapping"), dict)
        else []
    )
    mapping_rows = [row for row in mapping_rows if isinstance(row, dict)] if isinstance(mapping_rows, list) else []
    result["boq_item_markdown"] = sync_boq_item_markdowns_from_chain(
        sb=sb,
        project_uri=project_uri,
        preview_rows=preview_rows,
        mapping_rows=mapping_rows,
        actor_uri=normalized_owner,
        reason="boq.scan_complete",
        write_file=bool(commit and sb is not None),
    )
    result["scan_complete_proof"] = scan_complete_proof
    result["bridge_binding"] = {
        "item_bridge_mappings": item_bridge_map,
        "registered_bridges": registered_bridges,
        "bound_bridges": bound_bridges,
        "bridge_count": len(bridge_subitems),
    }
    return result


__all__ = ["initialize_boq_genesis_chain"]
