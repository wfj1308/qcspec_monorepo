"""
Verify view composition helpers.
services/api/verify_view_service.py
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import re
from typing import Any, Callable


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return str(value)


def _parse_dt_for_sort(value: Any) -> datetime:
    text = _to_text(value).strip()
    if not text:
        return datetime.min
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized).replace(tzinfo=None)
    except Exception:
        return datetime.min


def _status_token(value: Any) -> str:
    token = _to_text(value).strip().upper()
    if token in {"PASS", "SUCCESS", "OK"}:
        return "pass"
    if token in {"FAIL", "REJECTED", "ERROR"}:
        return "fail"
    return "pending"


def build_remediation_info(
    *,
    root_proof_id: str,
    descendants_enriched: list[dict[str, Any]],
    result_cn: Callable[[Any], str],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    latest_pass = None
    for item in descendants_enriched:
        token = _to_text(item.get("computed_result") or "").upper()
        proof_type = _to_text(item.get("proof_type") or "").lower()
        is_remedial = (
            "rect" in proof_type
            or "repair" in proof_type
            or "reinspect" in proof_type
            or "整改" in _to_text(item.get("test_name"))
            or "复检" in _to_text(item.get("test_name"))
            or proof_type in {"inspection", "proof"}
        )
        if not is_remedial:
            continue
        rec = {
            "proof_id": item.get("proof_id"),
            "proof_type": item.get("proof_type"),
            "result": token or "PENDING",
            "result_cn": result_cn(token or "PENDING"),
            "time": item.get("created_at"),
            "executor": item.get("executor_name") or "-",
            "description": f"{item.get('test_name') or item.get('proof_type') or '整改记录'} · {item.get('measured') or '-'}",
            "proof_hash": item.get("proof_hash") or "",
            "hash_valid": bool(item.get("proof_hash_valid")),
            "parent": item.get("parent_proof_id") or "-",
        }
        records.append(rec)
        if token == "PASS":
            latest_pass = rec

    issue_seed = hashlib.sha256(f"{root_proof_id}|remediation".encode("utf-8")).hexdigest()[:8].upper()
    issue_id = f"RC-{issue_seed}"
    return {
        "issue_id": issue_id,
        "has_remediation": bool(records),
        "latest_pass_proof_id": (latest_pass or {}).get("proof_id") or "",
        "records": records,
    }


def build_qcgate(ancestry_enriched: list[dict[str, Any]], stake: str) -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    for item in ancestry_enriched:
        rule_id = f"QCRule::{item['test_type']}::{item['operator']}::{item['threshold']}"
        rules.append(
            {
                "rule_id": rule_id,
                "spec_uri": item["spec_uri"],
                "spec_excerpt": item["spec_excerpt"],
                "spec_version": item.get("spec_version"),
                "rule_source_uri": item.get("rule_source_uri"),
                "operator": item["operator"],
                "threshold": item["threshold"],
                "measured": item["measured"],
                "result": item["computed_result"],
                "result_cn": item.get("computed_result_cn"),
                "deviation_percent": item.get("deviation_percent"),
                "source_proof_id": item["proof_id"],
                "proof_hash": item.get("proof_hash"),
                "recomputed_hash": item.get("proof_hash_recomputed"),
                "hash_valid": item.get("proof_hash_valid"),
                "executed_at": item["created_at"],
            }
        )

    gate_status = "PASS"
    if any(_to_text(r.get("result") or "").upper() == "FAIL" for r in rules):
        gate_status = "FAIL"
    elif not rules:
        gate_status = "PENDING"

    gate_id = f"QCGate::{stake or 'K50+200'}"
    return {
        "gate_id": gate_id,
        "stake": stake,
        "status": gate_status,
        "pass_policy": "all_pass",
        "rule_count": len(rules),
        "all_hash_valid": all(bool(r.get("hash_valid")) for r in rules) if rules else True,
        "rules": rules,
    }


def build_timeline(
    ancestry_enriched: list[dict[str, Any]],
    qcgate: dict[str, Any],
    *,
    result_cn: Callable[[Any], str],
) -> list[dict[str, Any]]:
    if not ancestry_enriched:
        return []
    first = ancestry_enriched[0]
    latest = ancestry_enriched[-1]

    spec_uri = first.get("spec_uri") or latest.get("spec_uri") or ""
    spec_excerpt = first.get("spec_excerpt") or latest.get("spec_excerpt") or ""
    gate_status = _to_text(qcgate.get("status") or "PENDING").upper()

    return [
        {
            "step": 1,
            "type": "SpecIR",
            "title": "规范基准锚定",
            "description": spec_uri or "未绑定规范地址",
            "time": first.get("created_at"),
            "executor": "SpecIR",
            "status": "pass" if spec_uri else "pending",
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
        },
        {
            "step": 2,
            "type": "QCRule",
            "title": "AI 规则翻译",
            "description": (
                f"由 SpecIR 翻译为可执行规则：{latest.get('operator') or '-'} "
                f"{latest.get('threshold') or '-'}，实测 {latest.get('measured') or '-'}"
            ),
            "time": latest.get("created_at"),
            "executor": "QCRule Engine",
            "status": "fail" if gate_status == "FAIL" else ("pass" if gate_status == "PASS" else "pending"),
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
            "operator": latest.get("operator"),
            "threshold": latest.get("threshold"),
            "rule_source_uri": latest.get("rule_source_uri"),
        },
        {
            "step": 3,
            "type": "TripRole",
            "title": "现场实测录入",
            "description": f"{latest.get('executor_name') or '-'} 录入 {latest.get('measured') or '-'}",
            "time": latest.get("created_at"),
            "executor": latest.get("executor_name") or "-",
            "status": "pass" if _to_text(latest.get("computed_result")).upper() == "PASS" else "fail",
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
        },
        {
            "step": 4,
            "type": "Proof",
            "title": "系统判定与签名",
            "description": (
                f"系统自动判定：{result_cn(latest.get('computed_result'))}；"
                f"OrdoSign: {latest.get('ordosign_hash') or '-'}"
            ),
            "time": latest.get("signed_at") or latest.get("created_at"),
            "executor": latest.get("executor_name") or "Proof UTXO",
            "status": "pass" if _to_text(latest.get("computed_result")).upper() == "PASS" else "fail",
            "proof_id": latest.get("proof_id"),
            "spec_uri": spec_uri,
            "spec_excerpt": spec_excerpt,
        },
    ]


def build_chain(ancestry_enriched: list[dict[str, Any]], current_proof_id: str) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    for item in ancestry_enriched:
        result = _to_text(item.get("computed_result") or "PENDING").upper()
        chain.append(
            {
                "type": "Proof",
                "proof_type": item.get("proof_type"),
                "label": item.get("test_name") or item.get("proof_type") or "Proof 节点",
                "status": _status_token(result),
                "result": result,
                "time": item.get("created_at"),
                "actor": f"{item.get('executor_name')} [{item.get('executor_role')}]",
                "proof": item.get("proof_id"),
                "proof_id": item.get("proof_id"),
                "parent": item.get("parent_proof_id") or "-",
                "current": _to_text(item.get("proof_id")) == _to_text(current_proof_id),
                "executor": item.get("executor_uri"),
                "executor_name": item.get("executor_name"),
                "spec_uri": item.get("spec_uri"),
                "operator": item.get("operator"),
                "threshold": item.get("threshold"),
                "proof_hash": item.get("proof_hash"),
                "hash_valid": item.get("proof_hash_valid"),
            }
        )
    return chain


def build_audit_rows(ancestry_enriched: list[dict[str, Any]], qcgate: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in ancestry_enriched:
        rows.append(
            {
                "proof_id": item.get("proof_id"),
                "type": "Proof",
                "proof_type": item.get("proof_type"),
                "result": _to_text(item.get("computed_result") or "PENDING").upper(),
                "parent": item.get("parent_proof_id") or "-",
                "time": item.get("created_at"),
                "executor": item.get("executor_uri"),
                "executor_name": item.get("executor_name"),
                "spec_uri": item.get("spec_uri"),
                "operator": item.get("operator"),
                "threshold": item.get("threshold"),
                "proof_hash": item.get("proof_hash"),
                "recomputed_hash": item.get("proof_hash_recomputed"),
                "hash_valid": item.get("proof_hash_valid"),
                "_raw_created_at": item.get("created_at_raw"),
            }
        )
    gate_id = _to_text(qcgate.get("gate_id") or "QCGate")
    gate_rules = qcgate.get("rules") if isinstance(qcgate.get("rules"), list) else []
    for rule in gate_rules:
        if not isinstance(rule, dict):
            continue
        rows.append(
            {
                "proof_id": rule.get("source_proof_id") or "-",
                "type": "QCRule",
                "proof_type": rule.get("rule_id") or "QCRule",
                "result": _to_text(rule.get("result") or "PENDING").upper(),
                "parent": gate_id,
                "time": rule.get("executed_at") or "-",
                "executor": "QCRule Engine",
                "executor_name": "QCRule Engine",
                "spec_uri": rule.get("spec_uri"),
                "operator": rule.get("operator"),
                "threshold": rule.get("threshold"),
                "proof_hash": rule.get("proof_hash"),
                "recomputed_hash": rule.get("recomputed_hash"),
                "hash_valid": rule.get("hash_valid"),
                "_raw_created_at": rule.get("executed_at"),
            }
        )
    rows.sort(key=lambda item: _parse_dt_for_sort(item.get("_raw_created_at")), reverse=True)
    for i, row in enumerate(rows, start=1):
        row["index"] = i
        row.pop("_raw_created_at", None)
    return rows


def build_context(row: dict[str, Any], stake: str, executor_uri: str) -> dict[str, str]:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    project_uri = _to_text(row.get("project_uri") or sd.get("project_uri") or "").strip()

    resolved_stake = _to_text(stake).strip()
    if not resolved_stake or resolved_stake == "-":
        resolved_stake = "K50+200"

    segment_uri = _to_text(row.get("segment_uri") or sd.get("segment_uri") or "").strip()
    if not segment_uri:
        if project_uri:
            segment_uri = f"{project_uri.rstrip('/')}/segment/{resolved_stake}"
        else:
            segment_uri = f"v://cn/segment/{resolved_stake}"

    return {
        "project_uri": project_uri,
        "segment_uri": segment_uri,
        "stake": resolved_stake,
        "executor_uri": _to_text(executor_uri or "-") or "-",
        "contract_uri": _to_text(sd.get("contract_uri") or ""),
        "design_uri": _to_text(sd.get("design_uri") or ""),
    }


def build_gitpeg_status(gitpeg_anchor: str) -> dict[str, Any]:
    anchor = _to_text(gitpeg_anchor).strip()
    if not anchor:
        return {
            "anchored": False,
            "anchor_ref": "",
            "block_height": None,
            "message": "已在本地存证，等待全局锚定",
        }

    block_height = None
    merkle_root = ""
    m = re.search(r"(?:height|block(?:_height)?)[=: ](\d+)", anchor, flags=re.IGNORECASE)
    if m:
        try:
            block_height = int(m.group(1))
        except Exception:
            block_height = None
    merkle_match = re.search(r"(?:merkle|mr)[=: ]([a-fA-F0-9]{8,64})", anchor, flags=re.IGNORECASE)
    if merkle_match:
        merkle_root = _to_text(merkle_match.group(1)).lower()

    msg = f"已锚定：{anchor}"
    if block_height is not None:
        msg = f"已锚定，区块高度 {block_height}"

    return {
        "anchored": True,
        "anchor_ref": anchor,
        "block_height": block_height,
        "merkle_root": merkle_root,
        "message": msg,
    }
