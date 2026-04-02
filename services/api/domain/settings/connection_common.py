"""Shared helpers for settings connection verification flows."""

from __future__ import annotations

import math
from typing import Any


def body_field(body: Any, name: str, default: Any = None) -> Any:
    if isinstance(body, dict):
        return body.get(name, default)
    return getattr(body, name, default)


def body_text(body: Any, name: str, default: str = "") -> str:
    return str(body_field(body, name, default) or "").strip()


def clamp_timeout_seconds(raw_timeout_ms: Any, *, default_ms: int) -> float:
    try:
        timeout_ms = float(raw_timeout_ms if raw_timeout_ms is not None else default_ms)
    except Exception:
        timeout_ms = float(default_ms)
    if not math.isfinite(timeout_ms) or timeout_ms <= 0:
        timeout_ms = float(default_ms)
    return min(max(timeout_ms / 1000, 2.0), 30.0)


__all__ = [
    "body_field",
    "body_text",
    "clamp_timeout_seconds",
]
