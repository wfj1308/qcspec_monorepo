"""Shared BOQ audit/payment helper utilities."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def to_float(value: Any, *, allow_commas: bool = False, regex_fallback: bool = False) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = to_text(value).strip()
        if allow_commas:
            text = text.replace(",", "")
        if not text:
            return None
        if regex_fallback:
            match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
            if not match:
                return None
            text = match.group(0)
        try:
            return float(text)
        except Exception:
            return None


def extract_boq_item_uri(row: dict[str, Any]) -> str:
    sd = as_dict(row.get("state_data"))
    for key in ("boq_item_uri", "item_uri", "boq_uri"):
        uri = to_text(sd.get(key) or "").strip()
        if uri.startswith("v://"):
            return uri
    segment_uri = to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in segment_uri:
        return segment_uri
    return ""


def item_code_from_boq_uri(boq_item_uri: str) -> str:
    uri = to_text(boq_item_uri).strip().rstrip("/")
    if not uri:
        return ""
    return uri.split("/")[-1]


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def chain_root_hash(fingerprints: list[dict[str, Any]]) -> str:
    return canonical_hash(fingerprints)


def verify_uri(verify_base_url: str, proof_id: str) -> str:
    pid = to_text(proof_id).strip()
    if not pid:
        return ""
    return f"{verify_base_url.rstrip('/')}/v/{pid}?trace=true"
