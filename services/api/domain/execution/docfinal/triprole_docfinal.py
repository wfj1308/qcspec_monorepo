"""DocFinal-oriented hierarchy aggregation and archive crypto helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.api.domain.execution.triprole_common import (
    to_float as _to_float,
    to_text as _to_text,
)


def boq_item_code_parts(item_no: str) -> list[str]:
    return [seg.strip() for seg in _to_text(item_no).split("-") if seg.strip()]


def hierarchy_node_type(depth: int, max_depth: int) -> str:
    if depth <= 1:
        return "chapter"
    if depth == 2:
        return "section"
    if depth == 3:
        return "item"
    if depth >= max_depth:
        return "detail"
    return f"level_{depth}"


def merkle_root_from_hashes(hashes: list[str]) -> str:
    layer = [_to_text(x).strip().lower() for x in hashes if _to_text(x).strip()]
    if not layer:
        return ""
    while len(layer) > 1:
        next_layer: list[str] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            next_layer.append(hashlib.sha256(f"{left}|{right}".encode("utf-8")).hexdigest())
        layer = next_layer
    return layer[0]


def build_recursive_hierarchy_summary(
    *,
    items: list[dict[str, Any]],
    focus_item_no: str = "",
) -> dict[str, Any]:
    node_map: dict[str, dict[str, Any]] = {}
    children_map: dict[str, set[str]] = {}

    for leaf in items:
        if not isinstance(leaf, dict):
            continue
        item_no = _to_text(leaf.get("item_no") or "").strip()
        if not item_no:
            continue
        parts = boq_item_code_parts(item_no)
        if not parts:
            continue
        design_qty = float(_to_float(leaf.get("design_quantity")) or 0.0)
        settled_qty = float(_to_float(leaf.get("settled_quantity")) or 0.0)
        item_name = _to_text(leaf.get("item_name") or "").strip()
        unit = _to_text(leaf.get("unit") or "").strip()
        max_depth = len(parts)

        for depth in range(1, max_depth + 1):
            code = "-".join(parts[:depth])
            parent_code = "-".join(parts[: depth - 1]) if depth > 1 else ""
            node = node_map.setdefault(
                code,
                {
                    "code": code,
                    "parent_code": parent_code,
                    "depth": depth,
                    "max_depth": max_depth,
                    "design_quantity": 0.0,
                    "settled_quantity": 0.0,
                    "leaf_count": 0,
                    "item_name": "",
                    "unit": "",
                },
            )
            node["max_depth"] = max(int(node.get("max_depth") or depth), max_depth)
            node["design_quantity"] = float(node.get("design_quantity") or 0.0) + design_qty
            node["settled_quantity"] = float(node.get("settled_quantity") or 0.0) + settled_qty
            node["leaf_count"] = int(node.get("leaf_count") or 0) + 1
            if depth == max_depth:
                node["item_name"] = item_name or _to_text(node.get("item_name") or "").strip()
                node["unit"] = unit or _to_text(node.get("unit") or "").strip()
            if parent_code:
                children_map.setdefault(parent_code, set()).add(code)
            children_map.setdefault(code, set())

    if not node_map:
        return {"rows": [], "root_hash": "", "chapter_progress": {}}

    subtree_hash: dict[str, str] = {}
    child_merkle: dict[str, str] = {}

    def _code_key(raw: str) -> tuple[int, list[int], str]:
        nums = [int(x) if x.isdigit() else 9999 for x in re.findall(r"\d+", raw)]
        return (len(nums), nums, raw)

    for code, node in sorted(
        node_map.items(),
        key=lambda kv: (int(kv[1].get("depth") or 0), kv[0]),
        reverse=True,
    ):
        child_codes = sorted(children_map.get(code) or set(), key=_code_key)
        child_hashes = [subtree_hash.get(c, "") for c in child_codes if subtree_hash.get(c, "")]
        merkle = merkle_root_from_hashes(child_hashes)
        child_merkle[code] = merkle
        canonical = {
            "code": code,
            "depth": int(node.get("depth") or 0),
            "design_quantity": round(float(node.get("design_quantity") or 0.0), 6),
            "settled_quantity": round(float(node.get("settled_quantity") or 0.0), 6),
            "leaf_count": int(node.get("leaf_count") or 0),
            "children_merkle_root": merkle,
            "node_type": hierarchy_node_type(int(node.get("depth") or 0), int(node.get("max_depth") or 0)),
        }
        subtree_hash[code] = hashlib.sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    rows: list[dict[str, Any]] = []
    for code, node in sorted(
        node_map.items(),
        key=lambda kv: (
            int(kv[1].get("depth") or 0),
            [int(x) if x.isdigit() else 9999 for x in re.findall(r"\d+", kv[0])],
            kv[0],
        ),
    ):
        depth = int(node.get("depth") or 0)
        design_qty = float(node.get("design_quantity") or 0.0)
        settled_qty = float(node.get("settled_quantity") or 0.0)
        progress = 0.0 if design_qty <= 1e-9 else max(0.0, min(1.0, settled_qty / design_qty))
        rows.append(
            {
                "code": code,
                "depth": depth,
                "parent_code": _to_text(node.get("parent_code") or "").strip(),
                "node_type": hierarchy_node_type(depth, int(node.get("max_depth") or depth)),
                "is_leaf": len(children_map.get(code) or set()) == 0,
                "item_name": _to_text(node.get("item_name") or "").strip(),
                "unit": _to_text(node.get("unit") or "").strip(),
                "design_quantity": round(design_qty, 6),
                "settled_quantity": round(settled_qty, 6),
                "remaining_quantity": round(max(0.0, design_qty - settled_qty), 6),
                "progress_percent": round(progress * 100.0, 2),
                "leaf_count": int(node.get("leaf_count") or 0),
                "children_count": len(children_map.get(code) or set()),
                "children_merkle_root": child_merkle.get(code, ""),
                "subtree_hash": subtree_hash.get(code, ""),
            }
        )

    root_codes = [row["code"] for row in rows if not _to_text(row.get("parent_code") or "").strip()]
    root_hash = merkle_root_from_hashes([subtree_hash.get(code, "") for code in root_codes if subtree_hash.get(code, "")])

    focus_chapter = ""
    focus_parts = boq_item_code_parts(focus_item_no)
    if focus_parts:
        focus_chapter = focus_parts[0]
    chapter_progress = {}
    if focus_chapter:
        chapter_row = next((row for row in rows if row["code"] == focus_chapter), {})
        if chapter_row:
            chapter_progress = {
                "chapter_code": focus_chapter,
                "progress_percent": chapter_row.get("progress_percent"),
                "design_quantity": chapter_row.get("design_quantity"),
                "settled_quantity": chapter_row.get("settled_quantity"),
                "remaining_quantity": chapter_row.get("remaining_quantity"),
                "leaf_count": chapter_row.get("leaf_count"),
            }

    return {
        "rows": rows,
        "root_hash": root_hash,
        "chapter_progress": chapter_progress,
        "root_codes": root_codes,
    }


def normalize_aggregate_direction(raw: Any) -> str:
    text = _to_text(raw).strip().lower()
    alias = {
        "": "all",
        "all": "all",
        "full": "all",
        "up": "up",
        "ancestor": "up",
        "ancestors": "up",
        "down": "down",
        "descendant": "down",
        "descendants": "down",
        "both": "both",
        "lineage": "both",
    }
    return alias.get(text, "all")


def normalize_aggregate_level(raw: Any) -> str:
    text = _to_text(raw).strip().lower()
    alias = {
        "": "all",
        "all": "all",
        "chapter": "chapter",
        "section": "section",
        "item": "item",
        "detail": "detail",
        "leaf": "leaf",
        "group": "group",
    }
    return alias.get(text, "all")


def filtered_hierarchy_root_hash(rows: list[dict[str, Any]]) -> str:
    row_map = {
        _to_text(row.get("code") or "").strip(): row
        for row in rows
        if isinstance(row, dict) and _to_text(row.get("code") or "").strip()
    }
    if not row_map:
        return ""
    codes = set(row_map.keys())
    root_codes = [
        code
        for code, row in row_map.items()
        if not _to_text(row.get("parent_code") or "").strip()
        or _to_text(row.get("parent_code") or "").strip() not in codes
    ]
    root_hashes = [
        _to_text(row_map.get(code, {}).get("subtree_hash") or "").strip()
        for code in root_codes
        if _to_text(row_map.get(code, {}).get("subtree_hash") or "").strip()
    ]
    return merkle_root_from_hashes(root_hashes)


def apply_hierarchy_asset_filter(
    *,
    rows: list[dict[str, Any]],
    focus_item_no: str,
    anchor_code: str = "",
    direction: str = "all",
    level: str = "all",
) -> dict[str, Any]:
    normalized_direction = normalize_aggregate_direction(direction)
    normalized_level = normalize_aggregate_level(level)
    normalized_anchor = _to_text(anchor_code).strip() or _to_text(focus_item_no).strip()
    filtered = [row for row in rows if isinstance(row, dict)]

    if normalized_anchor and normalized_direction in {"up", "down", "both"}:
        selected_codes: set[str] = set()
        for row in filtered:
            code = _to_text(row.get("code") or "").strip()
            if not code:
                continue
            if normalized_direction in {"up", "both"}:
                if normalized_anchor == code or normalized_anchor.startswith(f"{code}-"):
                    selected_codes.add(code)
            if normalized_direction in {"down", "both"}:
                if code == normalized_anchor or code.startswith(f"{normalized_anchor}-"):
                    selected_codes.add(code)
        filtered = [row for row in filtered if _to_text(row.get("code") or "").strip() in selected_codes]

    if normalized_level != "all":
        if normalized_level == "leaf":
            filtered = [row for row in filtered if bool(row.get("is_leaf"))]
        elif normalized_level == "group":
            filtered = [row for row in filtered if not bool(row.get("is_leaf"))]
        else:
            filtered = [
                row
                for row in filtered
                if _to_text(row.get("node_type") or "").strip().lower() == normalized_level
            ]

    return {
        "rows": filtered,
        "filter": {
            "anchor_code": normalized_anchor,
            "direction": normalized_direction,
            "level": normalized_level,
            "source_row_count": len(rows),
            "filtered_row_count": len(filtered),
        },
        "filtered_root_hash": filtered_hierarchy_root_hash(filtered),
    }


def encrypt_aes256(payload_bytes: bytes, passphrase: str) -> dict[str, Any]:
    key = hashlib.sha256(_to_text(passphrase).encode("utf-8")).digest()
    nonce = os.urandom(12)
    aad = b"QCSpec-Master-DSP-v1"
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, payload_bytes, aad)
    return {
        "algorithm": "AES-256-GCM",
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "aad": aad.decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "cipher_hash": hashlib.sha256(ciphertext).hexdigest(),
    }


__all__ = [
    "boq_item_code_parts",
    "hierarchy_node_type",
    "merkle_root_from_hashes",
    "build_recursive_hierarchy_summary",
    "normalize_aggregate_direction",
    "normalize_aggregate_level",
    "filtered_hierarchy_root_hash",
    "apply_hierarchy_asset_filter",
    "encrypt_aes256",
]
