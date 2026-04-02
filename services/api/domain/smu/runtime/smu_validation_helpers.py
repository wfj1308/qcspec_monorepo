"""Shared helper functions for SMU validation/risk scoring."""

from __future__ import annotations

import json
from typing import Any
import hashlib
from fastapi import HTTPException

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    to_float as _to_float,
    to_text as _to_text,
)


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def collect_validate_counts_and_issues(
    scoped_rows: list[dict[str, Any]],
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = {
        "missing_geo": 0,
        "missing_ntp": 0,
        "fail_count": 0,
        "low_trust_count": 0,
    }
    issues: list[dict[str, Any]] = []
    for row in scoped_rows:
        pid = _to_text(row.get("proof_id") or "").strip()
        result = _to_text(row.get("result") or "").strip().upper()
        sd = _as_dict(row.get("state_data"))
        geo = _as_dict(sd.get("geo_location"))
        ntp = _as_dict(sd.get("server_timestamp_proof"))
        if not geo or (_to_float(geo.get("lat")) is None or _to_float(geo.get("lng")) is None):
            counts["missing_geo"] += 1
            issues.append({"proof_id": pid, "severity": "medium", "issue": "missing_geo_location"})
        if not ntp or not _to_text(ntp.get("ntp_server") or ntp.get("proof_hash") or "").strip():
            counts["missing_ntp"] += 1
            issues.append({"proof_id": pid, "severity": "medium", "issue": "missing_ntp_proof"})
        if result == "FAIL":
            counts["fail_count"] += 1
            issues.append({"proof_id": pid, "severity": "high", "issue": "fail_result_in_chain"})
        trust = _to_text(_as_dict(sd.get("geo_compliance")).get("trust_level") or "").strip().upper()
        if trust in {"LOW", "OUTSIDE"}:
            counts["low_trust_count"] += 1
            issues.append({"proof_id": pid, "severity": "high", "issue": "low_geo_trust"})
    return counts, issues


def filter_rows_by_smu_id(rows: list[dict[str, Any]], smu_id: str) -> list[dict[str, Any]]:
    s_id = _to_text(smu_id).strip()
    if not s_id:
        return []
    scoped: list[dict[str, Any]] = []
    for row in rows:
        seg = _to_text(row.get("segment_uri") or "").strip()
        if "/boq/" not in seg:
            continue
        code = seg.rstrip("/").split("/")[-1]
        if code.startswith(s_id):
            scoped.append(row)
    return scoped


def build_did_reputation_issues(did_reputation: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for did in _as_dict(did_reputation).get("high_risk_dids") or []:
        d = _as_dict(did)
        issues.append(
            {
                "proof_id": "",
                "severity": "medium",
                "issue": "did_reputation_low",
                "participant_did": _to_text(d.get("participant_did") or "").strip(),
                "identity_uri": _to_text(d.get("identity_uri") or "").strip(),
                "score": _to_float(d.get("score")),
            }
        )
    return issues


def calculate_qualification_ratio(qualification: dict[str, Any]) -> float:
    leaf_total = int(_as_dict(qualification).get("leaf_total") or 0)
    if leaf_total <= 0:
        return 0.0
    qualified_leaf_count = int(_as_dict(qualification).get("qualified_leaf_count") or 0)
    return float(qualified_leaf_count) / float(leaf_total)


def build_unqualified_leaf_issue(qualification: dict[str, Any]) -> dict[str, Any] | None:
    q = _as_dict(qualification)
    if bool(q.get("all_qualified")):
        return None
    return {
        "proof_id": "",
        "severity": "high",
        "issue": "smu_unqualified_leaf_exists",
        "pending_leaf_count": int(q.get("unqualified_leaf_count") or 0),
    }


def calculate_validate_risk_score(
    *,
    total: int,
    fail_count: int,
    low_trust_count: int,
    missing_geo: int,
    missing_ntp: int,
    rep_penalty: float,
) -> float:
    risk_score = 100.0
    if total > 0:
        risk_score -= 35.0 * (fail_count / total)
        risk_score -= 25.0 * (low_trust_count / total)
        risk_score -= 20.0 * (missing_geo / total)
        risk_score -= 20.0 * (missing_ntp / total)
    if rep_penalty > 0:
        risk_score -= min(25.0, rep_penalty)
    return max(0.0, min(100.0, round(risk_score, 2)))


def build_validate_summary(
    *,
    total: int,
    counts: dict[str, int],
    risk_score: float,
    qualification: dict[str, Any],
    qualification_ratio: float,
    did_reputation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "total_proofs": total,
        "missing_geo": int(counts.get("missing_geo") or 0),
        "missing_ntp": int(counts.get("missing_ntp") or 0),
        "fail_count": int(counts.get("fail_count") or 0),
        "low_trust_count": int(counts.get("low_trust_count") or 0),
        "risk_score": risk_score,
        "qualified_leaf_count": int(qualification.get("qualified_leaf_count") or 0),
        "leaf_total": int(qualification.get("leaf_total") or 0),
        "qualification_ratio": round(qualification_ratio, 6),
        "all_qualified": bool(qualification.get("all_qualified")),
        "did_reputation_score": _to_float(_as_dict(did_reputation).get("aggregate_score")) or 0.0,
        "did_sampling_multiplier": _to_float(_as_dict(did_reputation).get("sampling_multiplier")) or 1.0,
        "did_count": int(_to_float(_as_dict(did_reputation).get("did_count")) or 0),
    }


def build_validate_logic_hash(
    *,
    project_uri: str,
    smu_id: str,
    summary: dict[str, Any],
) -> str:
    # Keep hash input stable for compatibility with existing downstream checks.
    summary_for_hash = {
        "total_proofs": int(summary.get("total_proofs") or 0),
        "missing_geo": int(summary.get("missing_geo") or 0),
        "missing_ntp": int(summary.get("missing_ntp") or 0),
        "fail_count": int(summary.get("fail_count") or 0),
        "low_trust_count": int(summary.get("low_trust_count") or 0),
        "risk_score": _to_float(summary.get("risk_score")) or 0.0,
        "qualified_leaf_count": int(summary.get("qualified_leaf_count") or 0),
        "leaf_total": int(summary.get("leaf_total") or 0),
        "all_qualified": bool(summary.get("all_qualified")),
        "did_reputation_score": _to_float(summary.get("did_reputation_score")) or 0.0,
        "did_sampling_multiplier": _to_float(summary.get("did_sampling_multiplier")) or 1.0,
    }
    return _sha(
        {
            "project_uri": project_uri,
            "smu_id": smu_id,
            "summary": summary_for_hash,
        }
    )


def resolve_validate_logic(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
    boq_rows: Any,
    build_did_reputation_summary: Any,
    collect_smu_qualification: Any,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    s_id = _to_text(smu_id).strip()
    if not p_uri or not s_id:
        raise HTTPException(400, "project_uri and smu_id are required")
    rows = boq_rows(sb, project_uri=p_uri, boq_item_uri="", only_unspent=False, limit=50000)
    scoped = filter_rows_by_smu_id(rows, s_id)
    if not scoped:
        raise HTTPException(404, f"No proof rows found under smu_id={s_id}")

    counts, issues = collect_validate_counts_and_issues(scoped)
    total = len(scoped)
    did_reputation = _as_dict(
        build_did_reputation_summary(
            sb=sb,
            project_uri=p_uri,
            chain_rows=scoped,
            window_days=90,
        )
    )
    rep_penalty = _to_float(_as_dict(did_reputation).get("risk_penalty")) or 0.0
    risk_score = calculate_validate_risk_score(
        total=total,
        fail_count=int(counts.get("fail_count") or 0),
        low_trust_count=int(counts.get("low_trust_count") or 0),
        missing_geo=int(counts.get("missing_geo") or 0),
        missing_ntp=int(counts.get("missing_ntp") or 0),
        rep_penalty=rep_penalty,
    )
    issues.extend(build_did_reputation_issues(did_reputation))
    qualification = _as_dict(collect_smu_qualification(sb=sb, project_uri=p_uri, smu_id=s_id))
    qualification_ratio = calculate_qualification_ratio(qualification)
    unqualified_issue = build_unqualified_leaf_issue(qualification)
    if unqualified_issue:
        issues.append(unqualified_issue)
    summary = build_validate_summary(
        total=total,
        counts=counts,
        risk_score=risk_score,
        qualification=qualification,
        qualification_ratio=qualification_ratio,
        did_reputation=did_reputation,
    )
    logic_hash = build_validate_logic_hash(
        project_uri=p_uri,
        smu_id=s_id,
        summary=summary,
    )
    return {
        "ok": True,
        "phase": "SMU & Risk Audit",
        "smu_id": s_id,
        "project_uri": p_uri,
        "summary": summary,
        "did_reputation": did_reputation,
        "qualification": qualification,
        "issues": issues[:500],
        "logic_hash": logic_hash,
    }


__all__ = [
    "build_validate_logic_hash",
    "build_did_reputation_issues",
    "build_unqualified_leaf_issue",
    "build_validate_summary",
    "calculate_qualification_ratio",
    "calculate_validate_risk_score",
    "collect_validate_counts_and_issues",
    "filter_rows_by_smu_id",
    "resolve_validate_logic",
]

