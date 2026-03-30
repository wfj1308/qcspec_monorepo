"""
Verify orchestration/facade helpers.
services/api/verify_facade_service.py
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from fastapi import HTTPException


def build_public_verify_detail(
    *,
    proof_id: str,
    sb: Any,
    engine: Any,
    verify_base_url: str,
    to_text: Callable[[Any, str], str],
    stake_from_row: Callable[[dict[str, Any]], str],
    enriched_row: Callable[..., dict[str, Any]],
    get_project_name_by_id: Callable[..., str],
    build_context: Callable[[dict[str, Any], str, str], dict[str, str]],
    build_qcgate: Callable[[list[dict[str, Any]], str], dict[str, Any]],
    result_cn: Callable[[Any], str],
    hash_payload_from_row: Callable[[dict[str, Any]], dict[str, Any]],
    hash_json: Callable[[dict[str, Any]], tuple[str, str]],
    build_gitpeg_status: Callable[[str], dict[str, Any]],
    get_proof_ancestry: Callable[..., list[dict[str, Any]]],
    get_proof_descendants: Callable[..., list[dict[str, Any]]],
    remediation_info: Callable[..., dict[str, Any]],
    build_timeline: Callable[[list[dict[str, Any]], dict[str, Any]], list[dict[str, Any]]],
    build_chain: Callable[[list[dict[str, Any]], str], list[dict[str, Any]]],
    build_audit_rows: Callable[[list[dict[str, Any]], dict[str, Any]], list[dict[str, Any]]],
    collect_evidence: Callable[..., list[dict[str, Any]]],
) -> dict[str, Any]:
    proof_id_text = to_text(proof_id, "").strip()
    if not proof_id_text:
        raise HTTPException(400, "proof_id is required")

    row = engine.get_by_id(proof_id_text)
    if not isinstance(row, dict):
        raise HTTPException(404, "proof_utxo not found")

    ancestry = get_proof_ancestry(engine, proof_id_text)
    if not ancestry:
        ancestry = [row]

    ancestry_enriched = [enriched_row(x, sb=sb) for x in ancestry]
    latest = ancestry[-1]
    latest_enriched = ancestry_enriched[-1]
    sd = latest.get("state_data") if isinstance(latest.get("state_data"), dict) else {}

    project_name = "-"
    project_id = to_text(latest.get("project_id") or "", "").strip()
    if project_id:
        project_name = get_project_name_by_id(sb, project_id, default="-")

    context = build_context(latest, stake_from_row(latest), latest_enriched.get("executor_uri") or "-")
    qcgate = build_qcgate(ancestry_enriched, context["stake"])

    computed_result = to_text(latest_enriched.get("computed_result") or "PENDING", "").upper()
    result_cn_text = result_cn(computed_result)
    verify_url = f"{verify_base_url}/v/{to_text(latest.get('proof_id') or '', '')}"

    hash_payload = hash_payload_from_row(latest)
    recomputed_hash, hash_source_json = hash_json(hash_payload)
    proof_hash = to_text(latest.get("proof_hash") or "", "")
    hash_match = bool(proof_hash and recomputed_hash.lower() == proof_hash.lower())

    gitpeg_anchor = to_text(latest.get("gitpeg_anchor") or "", "")
    gitpeg_status = build_gitpeg_status(gitpeg_anchor)

    spec_uri = latest_enriched.get("spec_uri") or ""
    if not spec_uri:
        for x in ancestry_enriched:
            if to_text(x.get("spec_uri"), "").strip():
                spec_uri = to_text(x.get("spec_uri"), "")
                break

    descendants: list[dict[str, Any]] = []
    descendants_enriched: list[dict[str, Any]] = []
    remediation = {
        "issue_id": "",
        "has_remediation": False,
        "latest_pass_proof_id": "",
        "records": [],
    }
    if computed_result == "FAIL":
        descendants = get_proof_descendants(engine, proof_id_text)
        descendants_enriched = [enriched_row(x, sb=sb) for x in descendants if isinstance(x, dict)]
        remediation = remediation_info(root_proof_id=proof_id_text, descendants_enriched=descendants_enriched)

    timeline = build_timeline(ancestry_enriched, qcgate)
    if remediation.get("has_remediation"):
        timeline.append(
            {
                "step": len(timeline) + 1,
                "type": "Remediation",
                "title": f"已关联整改单 [{remediation.get('issue_id')}]",
                "description": (
                    f"整改后代记录 {len(remediation.get('records') or [])} 条；"
                    f"最近复检合格 Proof: {remediation.get('latest_pass_proof_id') or '-'}"
                ),
                "time": ((remediation.get("records") or [{}])[-1] or {}).get("time") or latest_enriched.get("created_at"),
                "executor": "RectifyFlow",
                "status": "pass" if remediation.get("latest_pass_proof_id") else "pending",
                "spec_uri": spec_uri,
                "spec_excerpt": latest_enriched.get("spec_excerpt") or "",
            }
        )
    chain_rows = ancestry_enriched + descendants_enriched
    chain = build_chain(chain_rows, proof_id_text)
    audit_rows = build_audit_rows(chain_rows, qcgate)
    evidence_items = collect_evidence(sb=sb, latest_row=latest, chain_rows=ancestry + descendants)
    spec_snapshot = to_text((latest_enriched.get("meta") or {}).get("spec_snapshot") or latest_enriched.get("spec_excerpt") or "", "").strip()

    return {
        "ok": True,
        "verified": hash_match,
        "proof_id": to_text(latest.get("proof_id") or "", ""),
        "verify_url": verify_url,
        "context": context,
        "hash_verification": {
            "algorithm": "sha256",
            "provided_hash": proof_hash,
            "recomputed_hash": recomputed_hash,
            "matches": hash_match,
            "source_json": hash_source_json,
        },
        "hash_payload": hash_payload,
        "summary": {
            "project_name": project_name,
            "project_uri": context["project_uri"],
            "segment_uri": context["segment_uri"],
            "stake": context["stake"],
            "test_name": latest_enriched.get("test_name") or "检测项",
            "value": latest_enriched.get("measured") or "-",
            "standard": latest_enriched.get("threshold") or "-",
            "result": computed_result,
            "result_cn": result_cn_text,
            "deviation_percent": latest_enriched.get("deviation_percent"),
            "created_at": latest_enriched.get("created_at") or "-",
            "spec_uri": spec_uri,
            "spec_version": latest_enriched.get("spec_version") or "",
            "rule_source_uri": latest_enriched.get("rule_source_uri") or "",
            "spec_snapshot": spec_snapshot,
            "action_item_id": remediation.get("issue_id") if computed_result == "FAIL" else "",
        },
        "sovereignty": {
            "proof_id": to_text(latest.get("proof_id") or "", ""),
            "proof_hash": proof_hash,
            "v_uri": to_text(sd.get("v_uri") or context["project_uri"] or "", ""),
            "gitpeg_anchor": gitpeg_anchor,
            "gitpeg_status": gitpeg_status,
            "ordosign_hash": latest_enriched.get("ordosign_hash") or "-",
            "executor_uri": latest_enriched.get("executor_uri") or "-",
            "signed_by": latest_enriched.get("executor_name") or "-",
            "signed_role": latest_enriched.get("executor_role") or "AI",
            "signed_at": latest_enriched.get("signed_at") or "-",
            "spatiotemporal_anchor_hash": latest_enriched.get("spatiotemporal_anchor_hash") or "",
            "geo_location": latest_enriched.get("geo_location") or {},
            "server_timestamp_proof": latest_enriched.get("server_timestamp_proof") or {},
        },
        "exec": {
            "test_type": latest_enriched.get("test_name") or "检测项",
            "stake": context["stake"],
            "value": latest_enriched.get("measured") or "-",
            "standard": latest_enriched.get("threshold") or "-",
            "norm": spec_uri or "-",
            "operator": latest_enriched.get("operator") or "-",
            "threshold": latest_enriched.get("threshold") or "-",
        },
        "person": {
            "name": latest_enriched.get("executor_name") or "-",
            "uri": latest_enriched.get("executor_uri") or "-",
            "role": latest_enriched.get("executor_role") or "AI",
            "time": latest_enriched.get("signed_at") or "-",
            "sign": latest_enriched.get("ordosign_hash") or "-",
        },
        "qcgate": qcgate,
        "remediation": remediation,
        "timeline": timeline,
        "chain": chain,
        "evidence": evidence_items,
        "audit": {
            "depth": max(len(ancestry) - 1, 0) + len(descendants_enriched),
            "rows": audit_rows,
        },
    }


def build_chain_fingerprints(
    *,
    raw_chain: list[dict[str, Any]],
    hash_payload_from_row: Callable[[dict[str, Any]], dict[str, Any]],
    hash_json: Callable[[dict[str, Any]], tuple[str, str]],
    to_text: Callable[[Any, str], str],
    display_time: Callable[[Any], str],
) -> list[dict[str, Any]]:
    chain_fingerprints: list[dict[str, Any]] = []
    for row in raw_chain:
        if not isinstance(row, dict):
            continue
        payload = hash_payload_from_row(row)
        digest, source = hash_json(payload)
        chain_fingerprints.append(
            {
                "proof_id": to_text(row.get("proof_id") or "", ""),
                "proof_hash": to_text(row.get("proof_hash") or "", ""),
                "recomputed_hash": digest,
                "hash_valid": to_text(row.get("proof_hash") or "", "").lower() == digest.lower(),
                "proof_type": to_text(row.get("proof_type") or "", ""),
                "parent_proof_id": to_text(row.get("parent_proof_id") or "", ""),
                "created_at": display_time(row.get("created_at")),
                "source_fingerprint": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            }
        )
    return chain_fingerprints
