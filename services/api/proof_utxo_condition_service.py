"""
Condition evaluation helpers for proof UTXO engine.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple


def load_inputs(sb: Any, proof_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    rows = (
        sb.table("proof_utxo")
        .select("*")
        .in_("proof_id", proof_ids)
        .limit(max(1, min(len(proof_ids), 500)))
        .execute()
        .data
        or []
    )
    return {str(row.get("proof_id")): row for row in rows}


def log_condition(
    sb: Any,
    *,
    proof_id: str,
    condition: Dict[str, Any],
    checked_by: str,
    passed: bool,
    detail: str,
) -> None:
    if not proof_id:
        return
    try:
        sb.table("proof_condition_log").insert(
            {
                "proof_id": proof_id,
                "condition": condition or {},
                "checked_by": checked_by,
                "passed": bool(passed),
                "detail": detail,
            }
        ).execute()
    except Exception:
        pass


def check_conditions(
    *,
    sb: Any,
    proof: Dict[str, Any],
    executor_uri: str,
    executor_role: str,
    normalize_type: Callable[[str], str],
    normalize_result: Callable[[str], str],
) -> Tuple[bool, str]:
    proof_id = str(proof.get("proof_id") or "")
    conditions = proof.get("conditions") or []
    if not conditions:
        return True, "ok"
    for cond in conditions:
        ctype = str((cond or {}).get("type") or "").strip()
        if ctype == "role":
            role_value = str((cond or {}).get("value") or "").strip().upper()
            if str(executor_role or "").strip().upper() != role_value:
                log_condition(
                    sb,
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=False,
                    detail=f"role_required:{role_value}",
                )
                return False, f"role_required:{role_value}"
            log_condition(
                sb,
                proof_id=proof_id,
                condition=cond,
                checked_by=executor_uri,
                passed=True,
                detail="role_ok",
            )
        elif ctype == "ordosign_required":
            role_value = str((cond or {}).get("role") or "").strip().upper()
            if str(executor_role or "").strip().upper() != role_value:
                log_condition(
                    sb,
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=False,
                    detail=f"ordosign_role_required:{role_value}",
                )
                return False, f"ordosign_role_required:{role_value}"
            log_condition(
                sb,
                proof_id=proof_id,
                condition=cond,
                checked_by=executor_uri,
                passed=True,
                detail="ordosign_role_ok",
            )
        elif ctype == "proof_required":
            query = (
                sb.table("proof_utxo")
                .select("proof_id", count="exact")
                .eq("project_uri", proof.get("project_uri"))
                .eq("spent", False)
                .eq("proof_type", normalize_type((cond or {}).get("proof_type")))
                .eq("result", normalize_result((cond or {}).get("result") or "PASS"))
            )
            if proof.get("segment_uri"):
                query = query.eq("segment_uri", proof.get("segment_uri"))
            res = query.limit(1).execute()
            if int(res.count or 0) <= 0:
                log_condition(
                    sb,
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=False,
                    detail="proof_required_unsatisfied",
                )
                return False, "proof_required_unsatisfied"
            log_condition(
                sb,
                proof_id=proof_id,
                condition=cond,
                checked_by=executor_uri,
                passed=True,
                detail="proof_required_ok",
            )
        elif ctype == "min_count":
            min_need = int((cond or {}).get("min") or 0)
            query = (
                sb.table("proof_utxo")
                .select("proof_id", count="exact")
                .eq("project_uri", proof.get("project_uri"))
                .eq("spent", False)
                .eq("proof_type", normalize_type((cond or {}).get("proof_type")))
                .eq("result", normalize_result((cond or {}).get("result") or "PASS"))
            )
            if proof.get("segment_uri"):
                query = query.eq("segment_uri", proof.get("segment_uri"))
            res = query.limit(max(1, min_need)).execute()
            if int(res.count or 0) < min_need:
                log_condition(
                    sb,
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=False,
                    detail="min_count_unsatisfied",
                )
                return False, "min_count_unsatisfied"
            log_condition(
                sb,
                proof_id=proof_id,
                condition=cond,
                checked_by=executor_uri,
                passed=True,
                detail="min_count_ok",
            )
    return True, "ok"
