from __future__ import annotations

import hashlib
import re
from typing import Any

from fastapi import HTTPException


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _extract_boq_item_uri(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    for key in ("boq_item_uri", "item_uri", "boq_uri"):
        uri = _to_text(sd.get(key) or "").strip()
        if uri.startswith("v://"):
            return uri
    seg = _to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in seg:
        return seg
    return ""


def _is_leaf_boq_row(row: dict[str, Any]) -> bool:
    sd = _as_dict(row.get("state_data"))
    if "is_leaf" in sd:
        return bool(sd.get("is_leaf"))
    tree = _as_dict(sd.get("hierarchy_tree"))
    if "is_leaf" in tree:
        return bool(tree.get("is_leaf"))
    children = tree.get("children")
    if isinstance(children, list) and children:
        return False
    children_codes = tree.get("children_codes")
    if isinstance(children_codes, list) and children_codes:
        return False
    return True


def _item_code_from_uri(boq_item_uri: str) -> str:
    uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not uri:
        return ""
    token = uri.split("/")[-1]
    return token


def _unit_code_from_item_code(item_code: str) -> str:
    code = _to_text(item_code).strip()
    if not code:
        return ""
    m = re.match(r"^(\d{3})", code)
    if m:
        return m.group(1)
    if "-" in code:
        return code.split("-")[0]
    return code


def _leaf_hash(item_uri: str, proof_id: str, proof_hash: str) -> str:
    return hashlib.sha256(f"{item_uri}|{proof_id}|{proof_hash}".encode("utf-8")).hexdigest()


def _pair_hash(left: str, right: str) -> str:
    return hashlib.sha256(f"{left}|{right}".encode("utf-8")).hexdigest()


def _merkle_levels(leaf_hashes: list[str]) -> list[list[str]]:
    if not leaf_hashes:
        return []
    levels: list[list[str]] = [leaf_hashes]
    cur = leaf_hashes
    while len(cur) > 1:
        nxt: list[str] = []
        for i in range(0, len(cur), 2):
            left = cur[i]
            right = cur[i + 1] if i + 1 < len(cur) else cur[i]
            nxt.append(_pair_hash(left, right))
        levels.append(nxt)
        cur = nxt
    return levels


def _merkle_root(leaf_hashes: list[str]) -> str:
    levels = _merkle_levels(leaf_hashes)
    if not levels:
        return ""
    return levels[-1][0]


def _merkle_path(leaf_hashes: list[str], index: int) -> list[dict[str, Any]]:
    if not leaf_hashes or index < 0 or index >= len(leaf_hashes):
        return []
    levels = _merkle_levels(leaf_hashes)
    path: list[dict[str, Any]] = []
    idx = index
    for depth, level in enumerate(levels[:-1]):
        if idx % 2 == 0:
            sib_idx = idx + 1 if idx + 1 < len(level) else idx
            sibling_pos = "right"
        else:
            sib_idx = idx - 1
            sibling_pos = "left"
        path.append(
            {
                "depth": depth,
                "position": sibling_pos,
                "sibling_hash": level[sib_idx],
            }
        )
        idx //= 2
    return path


def build_unit_merkle_snapshot(
    *,
    sb: Any,
    project_uri: str,
    unit_code: str = "",
    proof_id: str = "",
    max_rows: int = 20000,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    normalized_proof_id = _to_text(proof_id).strip()

    if not normalized_project_uri and normalized_proof_id:
        row_by_id = sb.table("proof_utxo").select("project_uri").eq("proof_id", normalized_proof_id).limit(1).execute().data or []
        if row_by_id and isinstance(row_by_id[0], dict):
            normalized_project_uri = _to_text(row_by_id[0].get("project_uri") or "").strip()

    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", normalized_project_uri)
        .order("created_at", desc=True)
        .limit(max(1, min(int(max_rows), 50000)))
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(404, "no proof rows found for project_uri")

    latest_by_item: dict[str, dict[str, Any]] = {}
    requested_row: dict[str, Any] | None = None

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_pid = _to_text(row.get("proof_id") or "").strip()
        if normalized_proof_id and row_pid == normalized_proof_id and requested_row is None:
            requested_row = row
        if not _is_leaf_boq_row(row):
            continue
        item_uri = _extract_boq_item_uri(row)
        if not item_uri:
            continue
        if item_uri not in latest_by_item:
            latest_by_item[item_uri] = row

    if not latest_by_item:
        raise HTTPException(404, "no boq-linked proof rows found")

    requested_item_uri = _extract_boq_item_uri(requested_row or {}) if requested_row else ""
    resolved_unit_code = _to_text(unit_code).strip()
    if not resolved_unit_code and requested_item_uri:
        resolved_unit_code = _unit_code_from_item_code(_item_code_from_uri(requested_item_uri))
    if not resolved_unit_code:
        first_item = sorted(latest_by_item.keys())[0]
        resolved_unit_code = _unit_code_from_item_code(_item_code_from_uri(first_item))

    leaves: list[dict[str, Any]] = []
    for item_uri, row in latest_by_item.items():
        item_code = _item_code_from_uri(item_uri)
        item_unit = _unit_code_from_item_code(item_code)
        if item_unit != resolved_unit_code:
            continue
        pid = _to_text(row.get("proof_id") or "").strip()
        ph = _to_text(row.get("proof_hash") or "").strip()
        leaf = _leaf_hash(item_uri, pid, ph)
        leaves.append(
            {
                "item_uri": item_uri,
                "item_code": item_code,
                "unit_code": item_unit,
                "proof_id": pid,
                "proof_hash": ph,
                "created_at": _to_text(row.get("created_at") or "").strip(),
                "result": _to_text(row.get("result") or "").strip().upper(),
                "leaf_hash": leaf,
            }
        )
    leaves.sort(key=lambda x: _to_text(x.get("item_uri") or ""))

    if not leaves:
        raise HTTPException(404, f"no leaves found for unit_code={resolved_unit_code}")

    leaf_hashes = [_to_text(x.get("leaf_hash") or "") for x in leaves]
    unit_root_hash = _merkle_root(leaf_hashes)

    item_index = -1
    if requested_item_uri:
        for idx, leaf in enumerate(leaves):
            if _to_text(leaf.get("item_uri") or "") == requested_item_uri:
                item_index = idx
                break
    elif normalized_proof_id:
        for idx, leaf in enumerate(leaves):
            if _to_text(leaf.get("proof_id") or "") == normalized_proof_id:
                item_index = idx
                break
    item_merkle_path = _merkle_path(leaf_hashes, item_index) if item_index >= 0 else []

    unit_groups: dict[str, list[str]] = {}
    unit_counts: dict[str, int] = {}
    for item_uri, row in latest_by_item.items():
        code = _item_code_from_uri(item_uri)
        ucode = _unit_code_from_item_code(code)
        pid = _to_text(row.get("proof_id") or "").strip()
        ph = _to_text(row.get("proof_hash") or "").strip()
        lh = _leaf_hash(item_uri, pid, ph)
        unit_groups.setdefault(ucode, []).append(lh)
        unit_counts[ucode] = int(unit_counts.get(ucode, 0)) + 1

    units: list[dict[str, Any]] = []
    for ucode in sorted(unit_groups.keys()):
        roots = sorted(unit_groups.get(ucode) or [])
        root_hash = _merkle_root(roots)
        unit_leaf = hashlib.sha256(f"unit:{ucode}|{root_hash}".encode("utf-8")).hexdigest()
        units.append(
            {
                "unit_code": ucode,
                "item_count": int(unit_counts.get(ucode, 0)),
                "unit_root_hash": root_hash,
                "unit_leaf_hash": unit_leaf,
            }
        )

    unit_leaf_hashes = [_to_text(x.get("unit_leaf_hash") or "") for x in units]
    project_root_hash = _merkle_root(unit_leaf_hashes)

    unit_index = -1
    for idx, unit in enumerate(units):
        if _to_text(unit.get("unit_code") or "") == resolved_unit_code:
            unit_index = idx
            break
    unit_merkle_path = _merkle_path(unit_leaf_hashes, unit_index) if unit_index >= 0 else []

    requested_leaf = leaves[item_index] if 0 <= item_index < len(leaves) else {}

    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "requested_unit_code": _to_text(unit_code).strip(),
        "resolved_unit_code": resolved_unit_code,
        "requested_proof_id": normalized_proof_id,
        "requested_item_uri": requested_item_uri,
        "requested_leaf": requested_leaf,
        "leaf_count": len(leaves),
        "unit_root_hash": unit_root_hash,
        "project_root_hash": project_root_hash,
        "global_project_fingerprint": project_root_hash,
        "item_index": item_index,
        "unit_index": unit_index,
        "item_merkle_path": item_merkle_path,
        "unit_merkle_path": unit_merkle_path,
        "leaves": leaves,
        "units": units,
    }
