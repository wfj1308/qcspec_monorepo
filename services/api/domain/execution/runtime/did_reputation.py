"""
DID reputation scoring helpers for dynamic risk weighting.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


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


def _parse_dt(value: Any) -> datetime | None:
    text = _to_text(value).strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _executor_did_from_row(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    did_gate = _as_dict(sd.get("did_gate"))
    for candidate in (
        did_gate.get("user_did"),
        sd.get("executor_did"),
        sd.get("operator_did"),
        sd.get("actor_did"),
    ):
        did = _to_text(candidate).strip()
        if did.startswith("did:"):
            return did
    return ""


def _identity_uri(project_uri: str, participant_did: str) -> str:
    digest = hashlib.sha256(f"{project_uri}|{participant_did}".encode("utf-8")).hexdigest()[:20]
    return f"v://identity/{digest}/"


def _score_to_grade(score: float) -> str:
    if score >= 95:
        return "S"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    return "C"


def _score_to_penalty(score: float) -> float:
    if score >= 90:
        return 0.0
    if score >= 80:
        return 2.0
    if score >= 70:
        return 6.0
    if score >= 60:
        return 12.0
    return 18.0


def _score_to_sampling_multiplier(score: float) -> float:
    if score >= 92:
        return 0.7
    if score >= 85:
        return 0.85
    if score >= 70:
        return 1.0
    return 1.35


def compute_did_reputation(
    *,
    sb: Any,
    project_uri: str,
    participant_did: str,
    window_days: int = 90,
    limit: int = 12000,
) -> dict[str, Any]:
    project = _to_text(project_uri).strip()
    did = _to_text(participant_did).strip()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max(1, int(window_days)))
    cutoff_iso = cutoff.isoformat()
    if not project or not did.startswith("did:"):
        return {
            "available": False,
            "project_uri": project,
            "participant_did": did,
            "identity_uri": _identity_uri(project, did) if project and did else "",
            "window_days": int(window_days),
            "window_start": cutoff_iso,
            "reason": "invalid_inputs",
            "score": 0.0,
            "grade": "C",
            "risk_penalty": 18.0,
            "sampling_multiplier": 1.35,
            "stats": {},
            "reputation_proof": "",
        }

    try:
        rows = (
            sb.table("proof_utxo")
            .select("proof_id,proof_type,result,project_uri,state_data,created_at")
            .eq("project_uri", project)
            .order("created_at", desc=True)
            .limit(max(200, min(limit, 50000)))
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    sample_count = 0
    spacetime_pass = 0
    ntp_pass = 0
    geo_pass = 0
    outside_geo = 0
    missing_geo = 0
    missing_ntp = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        if _executor_did_from_row(row) != did:
            continue
        dt = _parse_dt(row.get("created_at"))
        if dt and dt < cutoff:
            continue
        sd = _as_dict(row.get("state_data"))
        trip_action = _to_text(sd.get("trip_action") or "").strip().lower()
        has_anchor = bool(_to_text(sd.get("spatiotemporal_anchor_hash") or "").strip())
        if not has_anchor and not trip_action:
            continue

        sample_count += 1
        geo = _as_dict(sd.get("geo_location"))
        lat = _to_float(geo.get("lat"))
        lng = _to_float(geo.get("lng"))
        trust = _to_text(_as_dict(sd.get("geo_compliance")).get("trust_level") or sd.get("trust_level") or "").strip().upper()
        ntp = _as_dict(sd.get("server_timestamp_proof"))
        ntp_ok = bool(_to_text(ntp.get("ntp_server") or ntp.get("proof_hash") or "").strip())
        geo_ok = lat is not None and lng is not None and trust not in {"LOW", "OUTSIDE"}
        if trust in {"LOW", "OUTSIDE"}:
            outside_geo += 1
        if lat is None or lng is None:
            missing_geo += 1
        if not ntp_ok:
            missing_ntp += 1
        if ntp_ok:
            ntp_pass += 1
        if geo_ok:
            geo_pass += 1
        if ntp_ok and geo_ok:
            spacetime_pass += 1

    if sample_count <= 0:
        score = 60.0
    else:
        pass_rate = float(spacetime_pass / sample_count)
        ntp_rate = float(ntp_pass / sample_count)
        geo_rate = float(geo_pass / sample_count)
        outside_rate = float(outside_geo / sample_count)
        score = 45.0 + pass_rate * 35.0 + ntp_rate * 10.0 + geo_rate * 10.0 - outside_rate * 20.0
        score = max(0.0, min(100.0, score))

    penalty = _score_to_penalty(score)
    multiplier = _score_to_sampling_multiplier(score)
    grade = _score_to_grade(score)

    payload = {
        "available": True,
        "project_uri": project,
        "participant_did": did,
        "identity_uri": _identity_uri(project, did),
        "window_days": int(window_days),
        "window_start": cutoff_iso,
        "score": round(score, 2),
        "grade": grade,
        "risk_penalty": penalty,
        "sampling_multiplier": multiplier,
        "fast_settlement_eligible": bool(score >= 92.0 and sample_count >= 50),
        "stats": {
            "sample_count": int(sample_count),
            "spacetime_pass_count": int(spacetime_pass),
            "ntp_pass_count": int(ntp_pass),
            "geo_pass_count": int(geo_pass),
            "outside_geo_count": int(outside_geo),
            "missing_geo_count": int(missing_geo),
            "missing_ntp_count": int(missing_ntp),
            "spacetime_pass_rate": round(float(spacetime_pass / sample_count), 6) if sample_count else 0.0,
            "ntp_pass_rate": round(float(ntp_pass / sample_count), 6) if sample_count else 0.0,
            "geo_pass_rate": round(float(geo_pass / sample_count), 6) if sample_count else 0.0,
        },
    }
    payload["reputation_proof"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return payload


def build_did_reputation_summary(
    *,
    sb: Any,
    project_uri: str,
    chain_rows: list[dict[str, Any]],
    window_days: int = 90,
) -> dict[str, Any]:
    project = _to_text(project_uri).strip()
    dids: list[str] = []
    seen: set[str] = set()
    for row in chain_rows:
        if not isinstance(row, dict):
            continue
        did = _executor_did_from_row(row)
        if not did or did in seen:
            continue
        seen.add(did)
        dids.append(did)
    if not dids:
        return {
            "available": False,
            "project_uri": project,
            "window_days": int(window_days),
            "did_count": 0,
            "items": [],
            "aggregate_score": 100.0,
            "risk_penalty": 0.0,
            "sampling_multiplier": 1.0,
            "recommended_sampling_level": "baseline",
            "summary_hash": "",
        }

    reps = [
        compute_did_reputation(
            sb=sb,
            project_uri=project,
            participant_did=did,
            window_days=window_days,
        )
        for did in dids
    ]

    weighted_score_total = 0.0
    weighted_penalty_total = 0.0
    weighted_multiplier_total = 0.0
    weight_total = 0.0
    high_risk_dids: list[dict[str, Any]] = []

    for rep in reps:
        stats = _as_dict(rep.get("stats"))
        weight = float(stats.get("sample_count") or 1.0)
        score = float(rep.get("score") or 0.0)
        penalty = float(rep.get("risk_penalty") or 0.0)
        multiplier = float(rep.get("sampling_multiplier") or 1.0)
        weighted_score_total += score * weight
        weighted_penalty_total += penalty * weight
        weighted_multiplier_total += multiplier * weight
        weight_total += weight
        if score < 70.0:
            high_risk_dids.append(
                {
                    "participant_did": _to_text(rep.get("participant_did") or "").strip(),
                    "identity_uri": _to_text(rep.get("identity_uri") or "").strip(),
                    "score": score,
                    "grade": _to_text(rep.get("grade") or "").strip(),
                    "sampling_multiplier": multiplier,
                }
            )

    aggregate_score = weighted_score_total / max(1.0, weight_total)
    risk_penalty = weighted_penalty_total / max(1.0, weight_total)
    sampling_multiplier = weighted_multiplier_total / max(1.0, weight_total)
    if sampling_multiplier >= 1.2:
        level = "high"
    elif sampling_multiplier <= 0.85:
        level = "low"
    else:
        level = "baseline"

    summary = {
        "available": True,
        "project_uri": project,
        "window_days": int(window_days),
        "did_count": len(reps),
        "items": reps,
        "aggregate_score": round(aggregate_score, 2),
        "risk_penalty": round(risk_penalty, 2),
        "sampling_multiplier": round(sampling_multiplier, 4),
        "recommended_sampling_level": level,
        "high_risk_dids": high_risk_dids,
    }
    summary["summary_hash"] = hashlib.sha256(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return summary

