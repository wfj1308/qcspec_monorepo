"""
Utility helpers for docx_engine.
services/api/docx_engine_utils.py
"""

from __future__ import annotations

from datetime import datetime
import os
import re
from typing import Any

from docxtpl import Listing


def to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return str(value)


def normalize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            out[to_text(k)] = normalize_payload(v)
        return out
    if isinstance(value, list):
        return [normalize_payload(x) for x in value]
    if isinstance(value, tuple):
        return tuple(normalize_payload(x) for x in value)
    if isinstance(value, (str, bytes)):
        return to_text(value)
    return value


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = str(value).strip()
        if not text:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def parse_limit(limit: Any) -> float | None:
    text = str(limit or "").strip()
    if not text:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return abs(float(match.group(0)))
    except Exception:
        return None


def coerce_values(values_raw: Any, fallback_value: Any = None) -> list[float]:
    def _num(raw: Any) -> float | None:
        try:
            return float(raw)
        except Exception:
            text = str(raw or "").strip()
            if not text:
                return None
            m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
            if not m:
                return None
            try:
                return float(m.group(0))
            except Exception:
                return None

    values: list[float] = []
    if isinstance(values_raw, list):
        for item in values_raw:
            parsed = _num(item)
            if parsed is not None:
                values.append(parsed)
    fallback_num: float | None = None
    if fallback_value is not None:
        fallback_num = _num(fallback_value)

    if values and fallback_num is not None:
        if len(values) == 1 and abs(values[0]) < 1e-9 and abs(fallback_num) >= 1e-9:
            return [fallback_num]
        return values

    if not values and fallback_num is not None:
        return [fallback_num]
    return values


def safe_label(label: Any, *, fallback: str) -> str:
    text = to_text(label).strip()
    return text or fallback


def safe_limit(limit_raw: Any) -> str:
    text = to_text(limit_raw).strip()
    if not text:
        return "-"
    if text.startswith("?") and len(text) > 1:
        return f"\u00b1{text[1:]}"
    return text


def extract_unit(state_data: dict[str, Any]) -> str:
    for key in ("unit", "value_unit", "standard_unit"):
        text = to_text(state_data.get(key)).strip()
        if text:
            return text

    for key in ("standard", "value"):
        raw = to_text(state_data.get(key)).strip()
        if not raw:
            continue
        m = re.match(r"^\s*[-+]?\d+(?:\.\d+)?\s*([^\d\s].*)$", raw)
        if m:
            unit = m.group(1).strip()
            if unit:
                return unit
    return ""


def with_unit(value_text: str, unit: str, *, force_inline: bool = False) -> str:
    base = to_text(value_text).strip()
    u = to_text(unit).strip()
    if not base or base == "-" or not u:
        return base or "-"
    if not force_inline and u.lower() == "mm":
        return base
    return f"{base} {u}"


def format_num(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def format_values_multiline(
    values: list[float],
    *,
    chunk: int = 10,
    unit: str = "",
    force_inline_unit: bool = False,
    separator: str = "\u3001",
) -> str | Listing:
    if not values:
        return "-"
    pieces = [with_unit(format_num(v), unit, force_inline=force_inline_unit) for v in values]
    if len(pieces) <= chunk:
        return separator.join(pieces)
    lines = []
    for idx in range(0, len(pieces), chunk):
        lines.append(separator.join(pieces[idx : idx + chunk]))
    return Listing("\n".join(lines))


def bool_env(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def is_uri_like(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def format_display_time(value: Any) -> str:
    text = to_text(value).strip()
    if not text:
        return ""

    normalized = text
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        dt = datetime.fromisoformat(normalized)
        return dt.replace(tzinfo=None, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    cleaned = text.replace("T", " ").strip()
    cleaned = re.sub(r"\.\d+", "", cleaned)
    cleaned = re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", cleaned).strip()
    sec_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", cleaned)
    if sec_match:
        return sec_match.group(1).replace("  ", " ")
    min_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})$", cleaned)
    if min_match:
        return f"{min_match.group(1).replace('  ', ' ')}:00"
    return cleaned


def format_signed_at(value: Any) -> str:
    return format_display_time(value)
