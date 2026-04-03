"""DocFinal risk-audit computation helpers."""

from __future__ import annotations

from typing import Any

from services.api.domain.execution.integrations import (
    build_did_reputation_summary,
    resolve_dual_pass_gate,
)
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    parse_iso_epoch_ms as _parse_iso_epoch_ms,
    to_float as _to_float,
    to_text as _to_text,
)


def compute_docfinal_risk_audit(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    chain_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(chain_rows)
    issues: list[dict[str, Any]] = []
    did_reputation: dict[str, Any] = {}

    dual_gate: dict[str, Any] = {}
    try:
        dual_gate = resolve_dual_pass_gate(
            sb=sb,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
            rows=chain_rows,
        )
    except Exception as exc:
        dual_gate = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    if not bool(dual_gate.get("ok")):
        issues.append({"severity": "high", "issue": "dual_pass_gate_missing"})

    by_id: dict[str, dict[str, Any]] = {}
    for row in chain_rows:
        pid = _to_text(row.get("proof_id") or "").strip()
        if pid:
            by_id[pid] = row

    stage_rank = {
        "INITIAL": 0,
        "GENESIS": 0,
        "ENTRY": 1,
        "INSPECTION": 1,
        "INSTALLATION": 2,
        "VARIATION": 2,
        "SETTLEMENT": 3,
    }
    max_seen_rank = -1
    stage_conflicts = 0
    for row in chain_rows:
        sd = _as_dict(row.get("state_data"))
        stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
        rank = stage_rank.get(stage, None)
        if rank is None:
            continue
        if rank < max_seen_rank:
            stage_conflicts += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "stage_order_conflict",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "stage": stage,
                    "max_seen_stage_rank": max_seen_rank,
                }
            )
        max_seen_rank = max(max_seen_rank, rank)

    timestamp_conflicts = 0
    for row in chain_rows:
        parent_id = _to_text(row.get("parent_proof_id") or "").strip()
        if not parent_id:
            continue
        parent = by_id.get(parent_id)
        if not parent:
            continue
        child_ms = _parse_iso_epoch_ms(row.get("created_at"))
        parent_ms = _parse_iso_epoch_ms(parent.get("created_at"))
        if child_ms is None or parent_ms is None:
            continue
        if child_ms < parent_ms:
            timestamp_conflicts += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "timestamp_conflict",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "parent_proof_id": parent_id,
                }
            )

    geo_outside = 0
    missing_geo = 0
    missing_ntp = 0
    for row in chain_rows:
        sd = _as_dict(row.get("state_data"))
        geo = _as_dict(sd.get("geo_compliance"))
        trust = _to_text(geo.get("trust_level") or sd.get("trust_level") or "").strip().upper()
        if trust in {"LOW", "OUTSIDE"}:
            geo_outside += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "geo_outside_boundary",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                    "trust_level": trust,
                }
            )
        geo_loc = _as_dict(sd.get("geo_location"))
        if not geo_loc or _to_float(geo_loc.get("lat")) is None or _to_float(geo_loc.get("lng")) is None:
            missing_geo += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "missing_geo_location",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                }
            )
        ntp = _as_dict(sd.get("server_timestamp_proof"))
        if not ntp or not _to_text(ntp.get("ntp_server") or ntp.get("proof_hash") or "").strip():
            missing_ntp += 1
            issues.append(
                {
                    "severity": "medium",
                    "issue": "missing_ntp_proof",
                    "proof_id": _to_text(row.get("proof_id") or "").strip(),
                }
            )

    risk_score = 100.0
    if not bool(dual_gate.get("ok")):
        risk_score -= 40.0
    if timestamp_conflicts > 0:
        risk_score -= min(30.0, 30.0 * (timestamp_conflicts / max(1, total)))
    if stage_conflicts > 0:
        risk_score -= min(20.0, 20.0 * (stage_conflicts / max(1, total)))
    if missing_geo > 0:
        risk_score -= min(20.0, 20.0 * (missing_geo / max(1, total)))
    if missing_ntp > 0:
        risk_score -= min(20.0, 20.0 * (missing_ntp / max(1, total)))
    if geo_outside > 0:
        risk_score -= min(30.0, 30.0 * (geo_outside / max(1, total)))
    try:
        did_reputation = build_did_reputation_summary(
            sb=sb,
            project_uri=project_uri,
            chain_rows=chain_rows,
            window_days=90,
        )
    except Exception:
        did_reputation = {}
    if _as_dict(did_reputation).get("available"):
        rep_penalty = _to_float(_as_dict(did_reputation).get("risk_penalty")) or 0.0
        if rep_penalty > 0:
            risk_score -= min(25.0, rep_penalty)
        for item in _as_list(did_reputation.get("high_risk_dids")):
            r = _as_dict(item)
            issues.append(
                {
                    "severity": "medium",
                    "issue": "did_reputation_low",
                    "participant_did": _to_text(r.get("participant_did") or "").strip(),
                    "identity_uri": _to_text(r.get("identity_uri") or "").strip(),
                    "score": _to_float(r.get("score")),
                }
            )
    risk_score = max(0.0, min(100.0, round(risk_score, 2)))

    return {
        "ok": True,
        "total": total,
        "risk_score": risk_score,
        "timestamp_conflicts": timestamp_conflicts,
        "stage_conflicts": stage_conflicts,
        "geo_outside_count": geo_outside,
        "missing_geo": missing_geo,
        "missing_ntp": missing_ntp,
        "dual_gate": dual_gate,
        "did_reputation": did_reputation,
        "sampling_multiplier": _to_float(_as_dict(did_reputation).get("sampling_multiplier")) or 1.0,
        "issues": issues[:500],
    }


__all__ = ["compute_docfinal_risk_audit"]
