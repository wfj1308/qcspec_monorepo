"""
Phygital sealing helpers: derive printable geometric anti-counterfeit pattern
from total_proof_hash.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _normalize_hash(value: Any) -> str:
    text = _to_text(value).strip().lower()
    text = re.sub(r"[^0-9a-f]+", "", text)
    if len(text) >= 32:
        return text[:64]
    return hashlib.sha256(_to_text(value).encode("utf-8")).hexdigest()


def _chunk(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size) if text[i : i + size]]


def build_sealing_pattern(*, total_proof_hash: str, grid_size: int = 13) -> dict[str, Any]:
    seed = _normalize_hash(total_proof_hash)
    n = max(9, min(int(grid_size), 21))
    half = (n + 1) // 2
    axis_mode = int(seed[0], 16) % 3  # 0: vertical, 1: horizontal, 2: quad

    matrix = [[0 for _ in range(n)] for _ in range(n)]
    for r in range(n):
        for c in range(half):
            idx = (r * half + c) % len(seed)
            val = int(seed[idx], 16)
            matrix[r][c] = 1 if (val % 3 == 0 or val >= 13) else 0

    if axis_mode == 0:
        for r in range(n):
            for c in range(half):
                matrix[r][n - 1 - c] = matrix[r][c]
        symmetry = "vertical"
    elif axis_mode == 1:
        half_rows = (n + 1) // 2
        for r in range(half_rows):
            for c in range(n):
                idx = (r * n + c) % len(seed)
                val = int(seed[idx], 16)
                matrix[r][c] = 1 if (val % 2 == 0) else 0
        for r in range(half_rows):
            matrix[n - 1 - r] = list(matrix[r])
        symmetry = "horizontal"
    else:
        q = (n + 1) // 2
        for r in range(q):
            for c in range(q):
                idx = (r * q + c) % len(seed)
                val = int(seed[idx], 16)
                bit = 1 if (val % 4 <= 1) else 0
                matrix[r][c] = bit
                matrix[r][n - 1 - c] = bit
                matrix[n - 1 - r][c] = bit
                matrix[n - 1 - r][n - 1 - c] = bit
        symmetry = "quadrant"

    rows = ["".join("#" if cell else "." for cell in row) for row in matrix]
    microtext = _chunk(seed.upper(), 8)[:8]
    on_count = sum(sum(row) for row in matrix)

    payload = {
        "pattern_id": seed[:16].upper(),
        "seed_hash": seed,
        "grid_size": n,
        "symmetry": symmetry,
        "density_ratio": round(on_count / float(n * n), 6),
        "microtext": microtext,
        "ascii_rows": rows,
    }
    payload["pattern_hash"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return payload


def build_sealing_trip(
    *,
    total_proof_hash: str,
    project_uri: str,
    boq_item_uri: str,
    smu_id: str = "",
) -> dict[str, Any]:
    pattern = build_sealing_pattern(total_proof_hash=total_proof_hash)
    pattern_id = _to_text(pattern.get("pattern_id") or "").strip()
    proof_hash = _normalize_hash(total_proof_hash)
    scan_payload = {
        "pattern_id": pattern_id,
        "proof_hash_prefix": proof_hash[:20],
        "project_uri": _to_text(project_uri).strip(),
        "boq_item_uri": _to_text(boq_item_uri).strip(),
        "smu_id": _to_text(smu_id).strip(),
    }
    scan_token = hashlib.sha256(
        json.dumps(scan_payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24].upper()
    seal_uri = f"v://seal/{pattern_id.lower()}/"
    return {
        "trip_name": "Sealing_Trip",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seal_uri": seal_uri,
        "pattern_id": pattern_id,
        "watermark": f"SEAL-{pattern_id}",
        "margin_microtext": pattern.get("microtext") or [],
        "symmetry": _to_text(pattern.get("symmetry") or "").strip(),
        "grid_size": pattern.get("grid_size"),
        "density_ratio": pattern.get("density_ratio"),
        "ascii_pattern": pattern.get("ascii_rows") or [],
        "pattern_hash": _to_text(pattern.get("pattern_hash") or "").strip(),
        "scan_payload": scan_payload,
        "scan_token": scan_token,
        "scan_hint": f"QCSPEC-SEAL://{pattern_id}/{scan_token}",
    }

