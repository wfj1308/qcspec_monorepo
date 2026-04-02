"""Common helpers shared by TripRole execution flows."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

CONSENSUS_ROLE_ALIASES = {
    "施工": "contractor",
    "施工方": "contractor",
    "承包方": "contractor",
    "contractor": "contractor",
    "监理": "supervisor",
    "监理方": "supervisor",
    "supervisor": "supervisor",
    "业主": "owner",
    "业主方": "owner",
    "甲方": "owner",
    "owner": "owner",
}


def to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_action(raw: Any) -> str:
    text = to_text(raw).strip().lower()
    if text.startswith("triprole(") and text.endswith(")"):
        text = text[len("triprole(") : -1].strip()
    return text


def safe_path_token(raw: Any, *, fallback: str = "node") -> str:
    text = to_text(raw).strip()
    if not text:
        return fallback
    token = re.sub(r"[^a-zA-Z0-9_\-]+", "-", text).strip("-")
    return token[:80] or fallback


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def safe_json_loads(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    text = to_text(raw).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def normalize_role(value: Any) -> str:
    text = to_text(value).strip().lower()
    if not text:
        return ""
    mapped = CONSENSUS_ROLE_ALIASES.get(text)
    if mapped:
        return mapped
    mapped = CONSENSUS_ROLE_ALIASES.get(to_text(value).strip())
    if mapped:
        return mapped
    return text


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = to_text(value).strip()
        if not text:
            return None
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except Exception:
            return None


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return to_text(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_iso_epoch_ms(value: Any) -> int | None:
    text = to_text(value).strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def decode_base64url_json(raw: Any) -> dict[str, Any]:
    text = to_text(raw).strip()
    if not text:
        return {}
    if text.startswith("{"):
        return safe_json_loads(text)
    padded = text + "=" * (-len(text) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return {}
    return safe_json_loads(decoded)


__all__ = [
    "CONSENSUS_ROLE_ALIASES",
    "to_text",
    "utc_iso",
    "sha256_json",
    "normalize_action",
    "safe_path_token",
    "as_dict",
    "as_list",
    "safe_json_loads",
    "normalize_role",
    "to_float",
    "to_bool",
    "parse_iso_epoch_ms",
    "decode_base64url_json",
]
