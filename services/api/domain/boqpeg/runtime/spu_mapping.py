"""SPU <-> BOQItem mapping runtime for BOQPeg scan pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any

from services.api.domain.utxo.integrations import ProofUTXOEngine


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalize_weight(value: Any) -> str:
    raw = _to_text(value, "1.0").strip() or "1.0"
    try:
        val = Decimal(raw)
    except (InvalidOperation, ValueError):
        return "1.0"
    if val <= Decimal("0"):
        return "1.0"
    return format(val.normalize(), "f")


def _resolve_default_quantity_per_unit(state_data: dict[str, Any]) -> str:
    for key in ("default_quantity_per_unit", "spu_quantity_per_unit", "spu_weight", "weight"):
        val = _normalize_weight(state_data.get(key))
        if val:
            return val
    return "1.0"


def _resolve_default_norm_ref(state_data: dict[str, Any]) -> str:
    direct_candidates = (
        state_data.get("ref_spec_uri"),
        state_data.get("linked_spec_uri"),
    )
    for candidate in direct_candidates:
        text = _to_text(candidate).strip()
        if text:
            return text
    for item in _as_list(state_data.get("norm_refs")):
        if isinstance(item, str):
            text = _to_text(item).strip()
            if text:
                return text
        if isinstance(item, dict):
            for key in ("uri", "ref_uri", "spec_uri"):
                text = _to_text(item.get(key)).strip()
                if text:
                    return text
    return ""


def _collect_spu_uris(state_data: dict[str, Any]) -> list[str]:
    uris: list[str] = []
    for candidate in (
        state_data.get("ref_spu_uri"),
        state_data.get("spu_uri"),
        state_data.get("spu_ref"),
    ):
        text = _to_text(candidate).strip()
        if text:
            uris.append(text)
    for key in ("ref_spu_uris", "spu_refs"):
        for candidate in _as_list(state_data.get(key)):
            text = _to_text(candidate).strip()
            if text:
                uris.append(text)
    for candidate in _as_list(state_data.get("norm_refs")):
        text = _to_text(candidate).strip()
        if "/spu/" in text:
            uris.append(text)
    deduped: list[str] = []
    seen: set[str] = set()
    for uri in uris:
        norm = uri.rstrip("/")
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(norm)
    return deduped


def _mapping_candidates(state_data: dict[str, Any]) -> list[dict[str, str]]:
    default_norm_ref = _resolve_default_norm_ref(state_data)
    primary_spu = _to_text(state_data.get("ref_spu_uri")).strip().rstrip("/")
    rows: list[dict[str, str]] = []
    if primary_spu:
        rows.append(
            {
                "spu_uri": primary_spu,
                "capability_type": "construction_method",
                "norm_ref": default_norm_ref,
            }
        )
        quota_uri = _to_text(state_data.get("ref_quota_uri")).strip()
        if quota_uri:
            rows.append(
                {
                    "spu_uri": primary_spu,
                    "capability_type": "material_spec",
                    "norm_ref": quota_uri,
                }
            )
        meter_rule_uri = _to_text(state_data.get("ref_meter_rule_uri")).strip()
        if meter_rule_uri:
            rows.append(
                {
                    "spu_uri": primary_spu,
                    "capability_type": "quantity_check",
                    "norm_ref": meter_rule_uri,
                }
            )
    for candidate in _collect_spu_uris(state_data):
        if candidate == primary_spu:
            continue
        rows.append(
            {
                "spu_uri": candidate,
                "capability_type": "quantity_check",
                "norm_ref": default_norm_ref,
            }
        )
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        spu_uri = _to_text(row.get("spu_uri")).strip().rstrip("/")
        capability_type = _to_text(row.get("capability_type")).strip() or "quantity_check"
        norm_ref = _to_text(row.get("norm_ref")).strip()
        key = (spu_uri, capability_type, norm_ref)
        if not spu_uri or key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "spu_uri": spu_uri,
                "capability_type": capability_type,
                "norm_ref": norm_ref,
            }
        )
    return deduped


def _resolve_boq_v_uri(state_data: dict[str, Any]) -> str:
    for key in (
        "boq_item_canonical_uri",
        "boq_item_v_uri",
        "boq_item_uri",
        "item_uri",
        "boq_uri",
    ):
        text = _to_text(state_data.get(key)).strip()
        if text:
            return text
    return ""


def _create_mapping_proof(
    *,
    sb: Any,
    commit: bool,
    owner_uri: str,
    project_uri: str,
    mapping_row: dict[str, Any],
) -> dict[str, Any]:
    now_iso = datetime.now(UTC).isoformat()
    state_data = {
        "proof_kind": "spu_boq_mapping",
        "action": "spu_boq_mapping",
        "mapping_id": _to_text(mapping_row.get("mapping_id")).strip(),
        "project_uri": project_uri,
        "boq_item_id": _to_text(mapping_row.get("boq_item_id")).strip(),
        "boq_v_uri": _to_text(mapping_row.get("boq_v_uri")).strip(),
        "boq_full_line_uri": _to_text(mapping_row.get("boq_full_line_uri")).strip(),
        "boq_bridge_scoped_uri": _to_text(mapping_row.get("boq_bridge_scoped_uri")).strip(),
        "bridge_uri": _to_text(mapping_row.get("bridge_uri")).strip(),
        "spu_uri": _to_text(mapping_row.get("spu_uri")).strip(),
        "capability_type": _to_text(mapping_row.get("capability_type")).strip(),
        "norm_ref": _to_text(mapping_row.get("norm_ref")).strip(),
        "default_quantity_per_unit": _to_text(mapping_row.get("default_quantity_per_unit")).strip() or "1.0",
        "weight": _to_text(mapping_row.get("weight")).strip() or "1.0",
        "source_file": _to_text(mapping_row.get("source_file")).strip(),
        "timestamp": now_iso,
    }
    proof_hash = _stable_hash(state_data)
    proof_id = f"GP-SPUMAP-{proof_hash[:18].upper()}"
    boq_v_uri = _to_text(mapping_row.get("boq_v_uri")).strip()
    segment_uri = f"{boq_v_uri.rstrip('/')}/spu-mapping/{proof_hash[:12]}" if boq_v_uri else ""
    preview = {
        "proof_id": proof_id,
        "proof_hash": proof_hash,
        "segment_uri": segment_uri,
        "state_data": state_data,
        "committed": False,
    }
    if not commit or sb is None:
        return preview
    row = ProofUTXOEngine(sb).create(
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type="inspection",
        result="PASS",
        state_data=state_data,
        norm_uri="v://norm/NormPeg/BOQPeg/SPU-BOQ-Mapping/1.0",
        segment_uri=segment_uri,
        signer_uri=owner_uri,
        signer_role="SYSTEM",
    )
    preview["committed"] = True
    preview["row"] = row
    preview["proof_hash"] = _to_text(row.get("proof_hash")).strip() or proof_hash
    return preview


def _persist_mapping_rows(*, sb: Any, commit: bool, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"ok": True, "status": "empty", "persisted": 0}
    if not commit or sb is None:
        return {"ok": True, "status": "skipped", "persisted": 0}
    payload = []
    for row in rows:
        default_quantity_per_unit = _normalize_weight(
            row.get("default_quantity_per_unit")
            if row.get("default_quantity_per_unit") is not None
            else row.get("weight")
        )
        payload.append(
            {
                "mapping_id": _to_text(row.get("mapping_id")).strip(),
                "project_uri": _to_text(row.get("project_uri")).strip(),
                "boq_item_id": _to_text(row.get("boq_item_id")).strip(),
                "boq_v_uri": _to_text(row.get("boq_v_uri")).strip(),
                "bridge_uri": _to_text(row.get("bridge_uri")).strip() or None,
                "spu_uri": _to_text(row.get("spu_uri")).strip(),
                "capability_type": _to_text(row.get("capability_type")).strip(),
                "norm_ref": _to_text(row.get("norm_ref")).strip(),
                "default_quantity_per_unit": default_quantity_per_unit,
                "weight": default_quantity_per_unit,
                "proof_id": _to_text(row.get("proof_id")).strip(),
                "proof_hash": _to_text(row.get("proof_hash")).strip(),
                "source_file": _to_text(row.get("source_file")).strip(),
            }
        )
    try:
        sb.table("spu_boq_mappings").upsert(
            payload,
            on_conflict="project_uri,boq_v_uri,spu_uri,capability_type",
        ).execute()
        return {"ok": True, "status": "persisted", "persisted": len(payload)}
    except Exception as exc:
        try:
            legacy_payload: list[dict[str, Any]] = []
            for row in payload:
                legacy_row = dict(row)
                legacy_row.pop("default_quantity_per_unit", None)
                legacy_payload.append(legacy_row)
            sb.table("spu_boq_mappings").upsert(
                legacy_payload,
                on_conflict="project_uri,boq_v_uri,spu_uri,capability_type",
            ).execute()
            return {
                "ok": True,
                "status": "persisted_legacy",
                "persisted": len(legacy_payload),
                "warning": f"fallback without default_quantity_per_unit: {exc.__class__.__name__}: {exc}",
            }
        except Exception as legacy_exc:
            return {
                "ok": False,
                "status": "failed",
                "persisted": 0,
                "error": f"{legacy_exc.__class__.__name__}: {legacy_exc}",
            }


def map_spu_to_boq_preview_rows(
    *,
    sb: Any,
    commit: bool,
    project_uri: str,
    owner_uri: str,
    source_file: str,
    preview_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    mappings: list[dict[str, Any]] = []
    mapping_by_boq_uri: dict[str, list[dict[str, Any]]] = {}

    for row in preview_rows:
        if not isinstance(row, dict):
            continue
        state_data = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
        if not bool(state_data.get("is_leaf")):
            continue
        boq_item_id = _to_text(state_data.get("item_no")).strip()
        boq_v_uri = _resolve_boq_v_uri(state_data)
        if not boq_item_id or not boq_v_uri:
            continue
        bridge_uri = _to_text(state_data.get("bridge_uri")).strip()
        boq_full_line_uri = _to_text(state_data.get("boq_item_full_line_uri")).strip()
        boq_bridge_scoped_uri = _to_text(state_data.get("boq_item_bridge_scoped_uri")).strip()
        default_quantity_per_unit = _resolve_default_quantity_per_unit(state_data)
        for candidate in _mapping_candidates(state_data):
            mapping_core = {
                "project_uri": _to_text(project_uri).strip(),
                "boq_item_id": boq_item_id,
                "boq_v_uri": boq_v_uri,
                "boq_full_line_uri": boq_full_line_uri,
                "boq_bridge_scoped_uri": boq_bridge_scoped_uri,
                "bridge_uri": bridge_uri,
                "spu_uri": _to_text(candidate.get("spu_uri")).strip(),
                "capability_type": _to_text(candidate.get("capability_type")).strip() or "quantity_check",
                "norm_ref": _to_text(candidate.get("norm_ref")).strip(),
                "default_quantity_per_unit": default_quantity_per_unit,
                "weight": default_quantity_per_unit,
                "source_file": _to_text(source_file).strip(),
            }
            core_hash = _stable_hash(mapping_core)
            mapping_id = f"SPUMAP-{core_hash[:20].upper()}"
            mapping_row = {
                "mapping_id": mapping_id,
                **mapping_core,
            }
            proof = _create_mapping_proof(
                sb=sb,
                commit=bool(commit),
                owner_uri=_to_text(owner_uri).strip(),
                project_uri=_to_text(project_uri).strip(),
                mapping_row=mapping_row,
            )
            mapping_record = {
                **mapping_row,
                "proof_id": _to_text(proof.get("proof_id")).strip(),
                "proof_hash": _to_text(proof.get("proof_hash")).strip(),
                "proof": proof,
            }
            mappings.append(mapping_record)
            mapping_by_boq_uri.setdefault(boq_v_uri, []).append(mapping_record)

    persist = _persist_mapping_rows(
        sb=sb,
        commit=bool(commit),
        rows=mappings,
    )
    return {
        "ok": persist.get("ok", True),
        "count": len(mappings),
        "mappings": mappings,
        "mapping_by_boq_uri": mapping_by_boq_uri,
        "persist": persist,
    }


__all__ = ["map_spu_to_boq_preview_rows"]
