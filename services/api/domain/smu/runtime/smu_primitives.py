"""Shared primitive type-coercion helpers for SMU modules."""

from __future__ import annotations

from datetime import datetime, timezone
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


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = to_text(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "as_dict",
    "as_list",
    "to_float",
    "to_text",
    "utc_iso",
]
