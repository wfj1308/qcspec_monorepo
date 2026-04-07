"""Lineage and provenance helpers for TripRole execution."""

from __future__ import annotations

import hashlib
from typing import Any

from services.api.domain.execution.integrations import resolve_linked_gates
from services.api.domain.execution.triprole_common import (
    as_dict,
    as_list,
    safe_path_token,
    to_float,
    to_text,
)


def _collect_norm_refs_from_row(row: dict[str, Any]) -> list[str]:
    refs: set[str] = set()
    sd = as_dict(row.get("state_data"))
    norm_eval = as_dict(sd.get("norm_evaluation"))
    threshold = as_dict(norm_eval.get("threshold"))
    for candidate in (
        row.get("norm_uri"),
        sd.get("norm_uri"),
        sd.get("spec_uri"),
        sd.get("spec_snapshot_uri"),
        threshold.get("effective_spec_uri"),
        threshold.get("spec_uri"),
    ):
        uri = to_text(candidate).strip()
        if uri.startswith("v://norm"):
            refs.add(uri)
    return sorted(refs)


def _collect_evidence_hashes_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    sd = as_dict(row.get("state_data"))
    evidence = as_list(sd.get("evidence"))
    out: list[dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        url = to_text(item.get("url") or "").strip()
        hash_value = to_text(
            item.get("sha256")
            or item.get("hash")
            or item.get("photo_hash")
            or item.get("fingerprint")
            or ""
        ).strip()
        if not hash_value and url:
            hash_value = hashlib.sha256(url.encode("utf-8")).hexdigest()
        if not hash_value:
            continue
        out.append(
            {
                "evidence_id": to_text(item.get("id") or "").strip(),
                "file_name": to_text(item.get("file_name") or "").strip(),
                "source_url": url,
                "hash": hash_value,
                "proof_id": to_text(row.get("proof_id") or "").strip(),
                "geo_location": as_dict(item.get("geo_location")),
                "server_timestamp_proof": as_dict(item.get("server_timestamp_proof")),
            }
        )
    return out


def _extract_qc_conclusion(row: dict[str, Any]) -> dict[str, Any]:
    sd = as_dict(row.get("state_data"))
    norm_eval = as_dict(sd.get("norm_evaluation"))
    stage = to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper() or _stage_from_row(row)
    conclusion = to_text(norm_eval.get("result") or row.get("result") or "").strip().upper()
    return {
        "proof_id": to_text(row.get("proof_id") or "").strip(),
        "stage": stage,
        "action": to_text(sd.get("trip_action") or "").strip().lower(),
        "result": to_text(row.get("result") or "").strip().upper(),
        "qc_conclusion": conclusion,
        "deviation_percent": norm_eval.get("deviation_percent"),
        "spec_uri": to_text(sd.get("spec_uri") or "").strip(),
        "spec_snapshot": to_text(sd.get("spec_snapshot") or "").strip(),
        "created_at": to_text(row.get("created_at") or "").strip(),
    }


def _boq_item_from_row(row: dict[str, Any]) -> str:
    sd = as_dict(row.get("state_data"))
    uri = to_text(sd.get("boq_item_uri") or sd.get("item_uri") or sd.get("boq_uri") or "").strip()
    if uri.startswith("v://"):
        return uri
    seg = to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in seg:
        return seg
    return ""


def _is_leaf_boq_row(row: dict[str, Any]) -> bool:
    sd = as_dict(row.get("state_data"))
    if "is_leaf" in sd:
        return bool(sd.get("is_leaf"))
    tree = as_dict(sd.get("hierarchy_tree"))
    if "is_leaf" in tree:
        return bool(tree.get("is_leaf"))
    children = as_list(tree.get("children")) or as_list(tree.get("children_codes"))
    if children:
        return False
    return True


def _item_no_from_boq_uri(boq_item_uri: str) -> str:
    uri = to_text(boq_item_uri).strip().rstrip("/")
    if not uri:
        return ""
    return uri.split("/")[-1]


def _smu_id_from_item_no(item_no: str) -> str:
    token = to_text(item_no).strip().rstrip("/").split("/")[-1]
    if "-" in token:
        return token.split("-")[0]
    return token or "misc"


def _resolve_subitem_gate_binding(
    *,
    sb: Any,
    input_row: dict[str, Any],
    boq_item_uri: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    sd = as_dict(input_row.get("state_data"))
    item_code = to_text(sd.get("item_no") or _item_no_from_boq_uri(boq_item_uri)).strip()
    fallback_spec_uri = to_text(
        sd.get("linked_spec_uri")
        or sd.get("spec_uri")
        or payload.get("spec_uri")
        or payload.get("norm_uri")
        or input_row.get("norm_uri")
        or ""
    ).strip()
    binding = resolve_linked_gates(
        item_code=item_code,
        fallback_spec_uri=fallback_spec_uri,
        sb=sb,
    )
    linked_gate_ids = as_list(sd.get("linked_gate_ids"))
    linked_gate_rules = as_list(sd.get("linked_gate_rules"))
    linked_gate_id = to_text(sd.get("linked_gate_id") or "").strip()
    linked_spec_uri = to_text(sd.get("linked_spec_uri") or "").strip()
    spec_dict_key = to_text(sd.get("spec_dict_key") or "").strip()
    spec_item = to_text(sd.get("spec_item") or "").strip()
    ref_gate_uri = to_text(sd.get("ref_gate_uri") or "").strip()
    ref_gate_uris = as_list(sd.get("ref_gate_uris"))
    ref_spec_uri = to_text(sd.get("ref_spec_uri") or "").strip()
    ref_spec_dict_uri = to_text(sd.get("ref_spec_dict_uri") or "").strip()
    ref_spec_item_uri = to_text(sd.get("ref_spec_item_uri") or "").strip()

    if linked_gate_id and linked_gate_ids:
        binding["linked_gate_id"] = linked_gate_id
        binding["linked_gate_ids"] = linked_gate_ids
        if linked_gate_rules:
            binding["linked_gate_rules"] = linked_gate_rules
    if linked_spec_uri:
        binding["linked_spec_uri"] = linked_spec_uri
    if spec_dict_key:
        binding["spec_dict_key"] = spec_dict_key
    if spec_item:
        binding["spec_item"] = spec_item
    if ref_gate_uri:
        binding["ref_gate_uri"] = ref_gate_uri
    if ref_gate_uris:
        binding["ref_gate_uris"] = ref_gate_uris
    if ref_spec_uri:
        binding["ref_spec_uri"] = ref_spec_uri
    if ref_spec_dict_uri:
        binding["ref_spec_dict_uri"] = ref_spec_dict_uri
    if ref_spec_item_uri:
        binding["ref_spec_item_uri"] = ref_spec_item_uri
    if sd.get("gate_template_lock") is not None:
        binding["gate_template_lock"] = bool(sd.get("gate_template_lock"))
    return binding


def _extract_settled_quantity(row: dict[str, Any], *, fallback_design: float | None = None) -> float:
    sd = as_dict(row.get("state_data"))
    settlement = as_dict(sd.get("settlement"))
    measurement = as_dict(sd.get("measurement"))

    for path in (
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        settlement.get("confirmed_quantity"),
        sd.get("settled_quantity"),
        measurement.get("quantity"),
        measurement.get("used_quantity"),
        sd.get("quantity"),
    ):
        q = to_float(path)
        if q is not None:
            return max(0.0, float(q))

    values = as_list(measurement.get("values"))
    nums = [x for x in (to_float(v) for v in values) if x is not None]
    if nums:
        return max(0.0, float(sum(nums) / len(nums)))

    if fallback_design is not None:
        return max(0.0, float(fallback_design))
    return 0.0


def _effective_design_quantity(genesis_row: dict[str, Any], bucket: list[dict[str, Any]]) -> float:
    gsd = as_dict(genesis_row.get("state_data"))
    base_design = to_float(gsd.get("contract_quantity"))
    if base_design is None:
        base_design = to_float(gsd.get("approved_quantity"))
    if base_design is None:
        base_design = to_float(gsd.get("design_quantity"))
    if base_design is None:
        base_design = to_float(as_dict(gsd.get("ledger")).get("initial_balance"))
    if base_design is None:
        base_design = 0.0

    latest_merged_total: float | None = None
    latest_delta_total: float | None = None
    for row in sorted(bucket, key=lambda r: to_text(r.get("created_at") or "")):
        sd = as_dict(row.get("state_data"))
        ledger = as_dict(sd.get("ledger"))
        merged_total = to_float(ledger.get("merged_total"))
        if merged_total is not None:
            latest_merged_total = float(merged_total)
        delta_total = to_float(ledger.get("delta_total"))
        if delta_total is not None:
            latest_delta_total = float(delta_total)

    if latest_merged_total is not None:
        return max(0.0, latest_merged_total)
    if latest_delta_total is not None:
        return max(0.0, float(base_design + latest_delta_total))
    return max(0.0, float(base_design))


def _stage_from_row(row: dict[str, Any]) -> str:
    sd = as_dict(row.get("state_data"))
    stage = to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    if stage in {"INITIAL", "ENTRY", "INSTALLATION", "VARIATION", "SETTLEMENT"}:
        return stage
    if to_text(row.get("proof_type")).lower() == "zero_ledger":
        return "INITIAL"
    return "UNKNOWN"


def _resolve_boq_item_uri(row: dict[str, Any], override: Any = None) -> str:
    if to_text(override).strip().startswith("v://"):
        return to_text(override).strip()
    sd = as_dict(row.get("state_data"))
    for key in ("boq_item_uri", "item_uri", "boq_uri"):
        uri = to_text(sd.get(key)).strip()
        if uri.startswith("v://"):
            return uri
    segment_uri = to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in segment_uri:
        return segment_uri
    return ""


def _resolve_segment_uri(row: dict[str, Any], payload: dict[str, Any], override: Any = None) -> str:
    if to_text(override).strip().startswith("v://"):
        return to_text(override).strip()
    incoming = to_text(payload.get("segment_uri") or payload.get("location_uri") or "").strip()
    if incoming.startswith("v://"):
        return incoming
    existing = to_text(row.get("segment_uri") or "").strip()
    if existing:
        return existing

    project_uri = to_text(row.get("project_uri") or "").strip().rstrip("/")
    stake = to_text(payload.get("stake") or payload.get("location") or payload.get("station") or "").strip()
    part = to_text(payload.get("part") or payload.get("position") or "").strip()
    if project_uri and stake:
        suffix = f"/{safe_path_token(part)}" if part else ""
        return f"{project_uri}/segment/{safe_path_token(stake)}{suffix}"
    return existing


def _build_variation_compensates(payload: dict[str, Any], input_proof_id: str) -> list[str]:
    vals = payload.get("compensates")
    if isinstance(vals, list):
        out = [to_text(x).strip() for x in vals if to_text(x).strip()]
        if out:
            return out
    direct = to_text(payload.get("source_fail_proof_id") or "").strip()
    if direct:
        return [direct]
    return [input_proof_id]


def _build_provenance_nodes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        pid = to_text(row.get("proof_id")).strip()
        if pid:
            by_id[pid] = row

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = as_dict(row.get("state_data"))
        pid = to_text(row.get("proof_id") or "").strip()
        parent_id = to_text(row.get("parent_proof_id") or "").strip()

        parent_hash = to_text(sd.get("parent_hash") or "").strip()
        if not parent_hash and parent_id and parent_id in by_id:
            parent_hash = to_text(by_id[parent_id].get("proof_hash") or "").strip()

        stage = to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper() or _stage_from_row(row)

        out.append(
            {
                "proof_id": pid,
                "proof_hash": to_text(row.get("proof_hash") or "").strip(),
                "parent_proof_id": parent_id,
                "parent_hash": parent_hash,
                "proof_type": to_text(row.get("proof_type") or "").strip().lower(),
                "result": to_text(row.get("result") or "").strip().upper(),
                "lifecycle_stage": stage,
                "trip_action": to_text(sd.get("trip_action") or "").strip().lower(),
                "segment_uri": to_text(row.get("segment_uri") or "").strip(),
                "boq_item_uri": to_text(sd.get("boq_item_uri") or sd.get("item_uri") or "").strip(),
                "norm_uri": to_text(row.get("norm_uri") or sd.get("norm_uri") or "").strip(),
                "gitpeg_anchor": to_text(row.get("gitpeg_anchor") or "").strip(),
                "created_at": to_text(row.get("created_at") or "").strip(),
                "geo_location": as_dict(sd.get("geo_location")),
                "server_timestamp_proof": as_dict(sd.get("server_timestamp_proof")),
                "spatiotemporal_anchor_hash": to_text(sd.get("spatiotemporal_anchor_hash") or "").strip(),
                "compensates": [
                    to_text(x).strip()
                    for x in as_list(sd.get("compensates"))
                    if to_text(x).strip()
                ],
            }
        )

    return out


def _gate_lock(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    fail_ids = [
        to_text(node.get("proof_id") or "").strip()
        for node in nodes
        if to_text(node.get("result") or "").strip().upper() == "FAIL"
    ]
    fail_ids = [x for x in fail_ids if x]

    variation_nodes = [
        node
        for node in nodes
        if to_text(node.get("lifecycle_stage") or "").strip().upper() == "VARIATION"
    ]

    compensated: set[str] = set()
    compensation_links: list[dict[str, Any]] = []
    for node in variation_nodes:
        variation_id = to_text(node.get("proof_id") or "").strip()
        targets = set(as_list(node.get("compensates")))
        parent_id = to_text(node.get("parent_proof_id") or "").strip()
        if parent_id:
            targets.add(parent_id)

        matched = sorted(
            {
                to_text(t).strip()
                for t in targets
                if to_text(t).strip() and to_text(t).strip() in fail_ids
            }
        )
        for proof_id in matched:
            compensated.add(proof_id)
        compensation_links.append(
            {
                "variation_proof_id": variation_id,
                "compensates": matched,
            }
        )

    uncompensated = sorted([proof_id for proof_id in fail_ids if proof_id not in compensated])
    blocked = bool(uncompensated)

    return {
        "blocked": blocked,
        "reason": "fail_without_variation" if blocked else "clear",
        "fail_proof_ids": sorted(set(fail_ids)),
        "variation_count": len(variation_nodes),
        "variation_compensations": compensation_links,
        "uncompensated_fail_proof_ids": uncompensated,
    }


__all__ = [
    "_collect_norm_refs_from_row",
    "_collect_evidence_hashes_from_row",
    "_extract_qc_conclusion",
    "_boq_item_from_row",
    "_is_leaf_boq_row",
    "_item_no_from_boq_uri",
    "_smu_id_from_item_no",
    "_resolve_subitem_gate_binding",
    "_extract_settled_quantity",
    "_effective_design_quantity",
    "_stage_from_row",
    "_resolve_boq_item_uri",
    "_resolve_segment_uri",
    "_build_variation_compensates",
    "_build_provenance_nodes",
    "_gate_lock",
]
