"""
Sovereign credit scoring helpers.
"""

from __future__ import annotations

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


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = _to_text(value).strip()
        if not text:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _score_grade(score: float) -> str:
    if score >= 95:
        return "S"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    return "C"


def _executor_did_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    did_gate = _as_dict(sd.get("did_gate"))
    for candidate in (
        did_gate.get("user_did"),
        sd.get("executor_did"),
        sd.get("operator_did"),
        sd.get("actor_did"),
    ):
        text = _to_text(candidate).strip()
        if text.startswith("did:"):
            return text
    return ""


def calculate_sovereign_credit(
    *,
    sb: Any,
    project_uri: str,
    participant_did: str,
    near_excellent_threshold_percent: float = 0.5,
    limit: int = 5000,
) -> dict[str, Any]:
    did = _to_text(participant_did).strip()
    project = _to_text(project_uri).strip()
    if not project or not did.startswith("did:"):
        return {
            "available": False,
            "participant_did": did,
            "project_uri": project,
            "reason": "invalid_inputs",
            "score": 0.0,
            "grade": "C",
            "fast_track_eligible": False,
            "stats": {},
            "credit_hash": "",
        }

    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", project)
        .order("created_at", desc=True)
        .limit(max(1, min(limit, 20000)))
        .execute()
        .data
        or []
    )

    sample_count = 0
    pass_count = 0
    elite_count = 0
    action_count = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        if _executor_did_from_row(row) != did:
            continue
        action_count += 1
        result = _to_text(row.get("result") or "").strip().upper()
        sd = _as_dict(row.get("state_data"))
        norm_eval = _as_dict(sd.get("norm_evaluation"))
        deviation = _to_float(
            norm_eval.get("deviation_percent")
            if norm_eval
            else sd.get("deviation_percent")
        )
        if deviation is None:
            continue
        sample_count += 1
        if result == "PASS":
            pass_count += 1
        if abs(float(deviation)) <= abs(float(near_excellent_threshold_percent)):
            elite_count += 1

    if sample_count <= 0:
        payload = {
            "available": True,
            "participant_did": did,
            "project_uri": project,
            "score": 60.0,
            "grade": "B",
            "fast_track_eligible": False,
            "stats": {
                "sample_count": 0,
                "action_count": int(action_count),
                "pass_count": 0,
                "elite_count": 0,
                "pass_rate": 0.0,
                "elite_rate": 0.0,
                "near_excellent_threshold_percent": float(near_excellent_threshold_percent),
            },
        }
        payload["credit_hash"] = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return payload

    pass_rate = float(pass_count / sample_count)
    elite_rate = float(elite_count / sample_count)
    score = 50.0 + pass_rate * 30.0 + elite_rate * 20.0
    if sample_count >= 100 and elite_rate >= 0.90:
        score += 5.0
    score = max(0.0, min(100.0, score))
    fast_track = bool(sample_count >= 100 and elite_rate >= 0.95 and pass_rate >= 0.98)

    payload = {
        "available": True,
        "participant_did": did,
        "project_uri": project,
        "score": round(score, 2),
        "grade": _score_grade(score),
        "fast_track_eligible": fast_track,
        "stats": {
            "sample_count": int(sample_count),
            "action_count": int(action_count),
            "pass_count": int(pass_count),
            "elite_count": int(elite_count),
            "pass_rate": round(pass_rate, 6),
            "elite_rate": round(elite_rate, 6),
            "near_excellent_threshold_percent": float(near_excellent_threshold_percent),
        },
    }
    payload["credit_hash"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return payload

