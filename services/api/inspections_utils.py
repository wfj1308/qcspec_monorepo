"""
Utility helpers for inspections service.
services/api/inspections_utils.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
import hashlib
import json
import os
import re

import httpx


def is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def run_with_retry(fn, retries: int = 1):
    last_err = None
    for _ in range(retries + 1):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout) as e:
            last_err = e
            continue
    if last_err:
        raise last_err


def gen_proof(v_uri: str, data: dict) -> str:
    payload = json.dumps(
        {
            "uri": v_uri,
            "data": data,
            "ts": datetime.utcnow().isoformat(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    h = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
    return f"GP-PROOF-{h}"


def guess_owner_uri(project_uri: str, person: Optional[str]) -> str:
    person_name = str(person or "").strip()
    root = str(project_uri or "").strip()
    for marker in ("/highway/", "/bridge/", "/urban/", "/road/", "/tunnel/"):
        idx = root.find(marker)
        if idx > 0:
            root = root[: idx + 1]
            break
    if not root.endswith("/"):
        root += "/"
    if person_name:
        return f"{root}executor/{person_name}/"
    return f"{root}executor/system/"


def to_utxo_result(result: str) -> str:
    text = str(result or "").strip().lower()
    if text == "pass":
        return "PASS"
    if text == "fail":
        return "FAIL"
    if text == "warn":
        return "OBSERVE"
    return "PENDING"


def parse_limit_value(limit_text: Optional[str]) -> Optional[float]:
    text = str(limit_text or "").strip()
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return abs(float(m.group(0)))
    except Exception:
        return None


def evaluate_design_limit_result(
    *,
    design: Optional[float],
    limit_text: Optional[str],
    values: Optional[list[float]],
) -> Optional[str]:
    if design is None:
        return None
    limit_value = parse_limit_value(limit_text)
    if limit_value is None:
        return None
    clean_values = [float(v) for v in (values or [])]
    if not clean_values:
        return None
    lower = float(design) - float(limit_value)
    upper = float(design) + float(limit_value)
    out_of_range = any(v < lower or v > upper for v in clean_values)
    return "fail" if out_of_range else "pass"


def extract_photo_hash(photo: dict[str, Any]) -> str:
    for key in ("evidence_hash", "sha256", "file_sha256", "hash"):
        text = str(photo.get(key) or "").strip().lower()
        if text:
            return text
    return ""


def extract_photo_media_type(photo: dict[str, Any]) -> str:
    ctype = str(photo.get("content_type") or "").strip().lower()
    if ctype.startswith("image/"):
        return "image"
    if ctype.startswith("video/"):
        return "video"
    name = str(photo.get("file_name") or "").lower()
    if name.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic")):
        return "image"
    if name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")):
        return "video"
    return "file"


def utxo_anchor_config(custom: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": custom.get("proof_utxo_gitpeg_anchor_enabled"),
        "base_url": custom.get("gitpeg_registrar_base_url"),
        "anchor_path": custom.get("gitpeg_proof_anchor_path") or "/api/v1/proof/anchor",
        "anchor_endpoint": custom.get("gitpeg_proof_anchor_endpoint"),
        "auth_token": custom.get("gitpeg_anchor_token")
        or custom.get("gitpeg_token")
        or custom.get("gitpeg_client_secret"),
        "timeout_s": custom.get("gitpeg_proof_anchor_timeout_s") or 6,
    }


def utxo_auto_consume_enabled(custom: dict[str, Any]) -> bool:
    value = custom.get("proof_utxo_auto_consume")
    if isinstance(value, bool):
        return value
    text = str(value or os.getenv("PROOF_UTXO_AUTO_CONSUME") or "").strip().lower()
    return text in {"1", "true", "yes", "on"}
