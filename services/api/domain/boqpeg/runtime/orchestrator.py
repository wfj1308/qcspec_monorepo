"""BOQPeg end-to-end orchestration for upload -> BOQ items -> UTXO chain."""

from __future__ import annotations

from typing import Any

from services.api.core.docpeg import DTORole
from services.api.domain.boqpeg.runtime.genesis import initialize_boq_genesis_chain
from services.api.domain.boqpeg.runtime.parser import parse_boq_upload
from services.api.domain.boqpeg.runtime.spu_smu_models import build_spu_boq_smu_graph


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


def _bridge_name_from_uri(bridge_uri: str) -> str:
    text = _to_text(bridge_uri).strip().rstrip("/")
    if not text:
        return ""
    return text.split("/")[-1]


def _build_scan_pairs(chain: dict[str, Any]) -> list[dict[str, Any]]:
    preview_rows = chain.get("preview") if isinstance(chain.get("preview"), list) else []
    created_rows = chain.get("created") if isinstance(chain.get("created"), list) else []
    created_by_id: dict[str, dict[str, Any]] = {}
    for row in created_rows:
        if not isinstance(row, dict):
            continue
        pid = _to_text(row.get("proof_id")).strip()
        if pid:
            created_by_id[pid] = row

    mapping_by_boq_uri: dict[str, list[dict[str, Any]]] = {}
    mapping_payload = chain.get("spu_boq_mapping") if isinstance(chain.get("spu_boq_mapping"), dict) else {}
    for boq_uri, items in (mapping_payload.get("mapping_by_boq_uri") or {}).items():
        key = _to_text(boq_uri).strip()
        if not key:
            continue
        mapping_by_boq_uri[key] = [row for row in items if isinstance(row, dict)]

    pairs: list[dict[str, Any]] = []
    for row in preview_rows:
        if not isinstance(row, dict):
            continue
        sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
        if not bool(sd.get("is_leaf")):
            continue
        boq_v_uri = _to_text(
            sd.get("boq_item_canonical_uri")
            or sd.get("boq_item_v_uri")
            or sd.get("boq_item_uri")
            or ""
        ).strip()
        boq_legacy_uri = _to_text(sd.get("boq_item_uri") or "").strip()
        proof_id = _to_text(row.get("proof_id")).strip()
        created = created_by_id.get(proof_id, {})
        proof_hash = _to_text(created.get("proof_hash") or "").strip() or _to_text(sd.get("genesis_hash") or "").strip()
        boq_item = {
            "boq_item_id": _to_text(sd.get("item_no") or "").strip(),
            "description": _to_text(sd.get("item_name") or "").strip(),
            "unit": _to_text(sd.get("unit") or "").strip(),
            "boq_quantity": sd.get("contract_quantity"),
            "project_uri": _to_text(row.get("project_uri") or "").strip() or _to_text(sd.get("project_uri") or "").strip(),
            "bridge_uri": _to_text(sd.get("bridge_uri") or "").strip(),
            "spec_uri": _to_text(sd.get("spec_uri") or sd.get("linked_spec_uri") or "").strip(),
            "v_uri": boq_v_uri,
            "legacy_v_uri": boq_legacy_uri,
            "full_line_v_uri": _to_text(sd.get("boq_item_full_line_uri") or "").strip(),
            "bridge_scoped_v_uri": _to_text(sd.get("boq_item_bridge_scoped_uri") or "").strip(),
            "uri_aliases": _as_list(sd.get("boq_item_uri_aliases")),
            "unit_price": sd.get("contract_unit_price"),
            "total_amount": sd.get("contract_total"),
            "bridge_name": _bridge_name_from_uri(_to_text(sd.get("bridge_uri") or "").strip()),
            "norm_refs": _as_list(sd.get("norm_refs")),
            "settlement_rules": [
                _to_text(sd.get("ref_meter_rule_uri") or "").strip(),
            ]
            if _to_text(sd.get("ref_meter_rule_uri") or "").strip()
            else [],
            "genesis_hash": _to_text(sd.get("genesis_hash") or "").strip(),
        }
        item_mappings = mapping_by_boq_uri.get(boq_item["v_uri"], [])
        if not item_mappings and boq_legacy_uri:
            item_mappings = mapping_by_boq_uri.get(boq_legacy_uri, [])
        attached_spus = []
        for mapping in item_mappings:
            uri = _to_text(mapping.get("spu_uri")).strip()
            if uri and uri not in attached_spus:
                attached_spus.append(uri)
        boq_item["spu_mappings"] = item_mappings
        initial_utxo = {
            "utxo_id": proof_id,
            "boq_item_id": boq_item["boq_item_id"],
            "kind": _to_text(sd.get("utxo_kind") or "BOQ_INITIAL").strip(),
            "state": _to_text(sd.get("utxo_state") or "UNSPENT").strip(),
            "quantity": sd.get("utxo_quantity"),
            "parent_utxo": sd.get("utxo_parent"),
            "bridge_uri": boq_item["bridge_uri"],
            "proof_hash": proof_hash,
            "timestamp": _to_text(sd.get("genesis_at") or "").strip(),
            "attached_spus": attached_spus,
        }
        pairs.append({"boq_item": boq_item, "initial_utxo": initial_utxo})
    return pairs


def _build_role_view(
    *,
    scan_pairs: list[dict[str, Any]],
    chain: dict[str, Any],
    smu_rows: list[dict[str, Any]],
    dto_role: str | None,
) -> dict[str, Any]:
    mapping_rows = (
        (chain.get("spu_boq_mapping") or {}).get("mappings")
        if isinstance(chain.get("spu_boq_mapping"), dict)
        else []
    )
    mapping_rows = [row for row in mapping_rows if isinstance(row, dict)] if isinstance(mapping_rows, list) else []
    return DTORole.boq_scan_bundle(
        scan_results=scan_pairs,
        mapping_rows=mapping_rows,
        smu_rows=smu_rows,
        role=dto_role,
    )


def scan_boq_and_create_utxos(
    *,
    sb: Any,
    project_uri: str,
    project_id: str | None,
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    bridge_mappings: dict[str, Any] | None = None,
    dto_role: str | None = None,
    commit: bool,
) -> dict[str, Any]:
    boq_items = parse_boq_upload(upload_file_name, upload_content)
    chain = initialize_boq_genesis_chain(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id,
        boq_items=boq_items,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        source_file=upload_file_name,
        bridge_mappings=bridge_mappings,
        commit=bool(commit),
    )
    scan_pairs = _build_scan_pairs(chain)
    mapping_rows = (
        (chain.get("spu_boq_mapping") or {}).get("mappings")
        if isinstance(chain.get("spu_boq_mapping"), dict)
        else []
    )
    mapping_rows = [row for row in mapping_rows if isinstance(row, dict)] if isinstance(mapping_rows, list) else []
    graph = build_spu_boq_smu_graph(
        scan_results=scan_pairs,
        mapping_rows=mapping_rows,
    )
    smu_rows = graph.get("smu_units") if isinstance(graph.get("smu_units"), list) else []
    role_view = _build_role_view(scan_pairs=scan_pairs, chain=chain, smu_rows=smu_rows, dto_role=dto_role)
    return {
        "ok": True,
        "boqpeg": {
            "flow": "upload->scan->boq_items+utxo_genesis",
            "upload_file_name": upload_file_name,
            "item_count": len(boq_items),
            "scan_pairs": len(scan_pairs),
            "spu_mappings": int(
                (
                    chain.get("spu_boq_mapping", {})
                    if isinstance(chain.get("spu_boq_mapping"), dict)
                    else {}
                ).get("count")
                or 0
            ),
            "commit": bool(commit),
            "view_role": _to_text(role_view.get("view_role") or "").strip(),
            "smu_units": int((graph.get("counts") or {}).get("smu") or 0),
        },
        "chain": chain,
        "scan_results": scan_pairs,
        "spu_boq_smu_graph": graph,
        "view": role_view,
    }


def import_boq_upload_chain(
    *,
    sb: Any,
    project_uri: str,
    project_id: str | None,
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    bridge_mappings: dict[str, Any] | None = None,
    dto_role: str | None = None,
    commit: bool,
) -> dict[str, Any]:
    return scan_boq_and_create_utxos(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id,
        upload_file_name=upload_file_name,
        upload_content=upload_content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        dto_role=dto_role,
        commit=bool(commit),
    )


def preview_boq_upload_chain(
    *,
    sb: Any,
    project_uri: str,
    project_id: str | None,
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str,
    norm_context_root_uri: str,
    owner_uri: str,
    bridge_mappings: dict[str, Any] | None = None,
    dto_role: str | None = None,
) -> dict[str, Any]:
    return import_boq_upload_chain(
        sb=sb,
        project_uri=project_uri,
        project_id=project_id,
        upload_file_name=upload_file_name,
        upload_content=upload_content,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        dto_role=dto_role,
        commit=False,
    )


__all__ = ["import_boq_upload_chain", "preview_boq_upload_chain", "scan_boq_and_create_utxos"]
