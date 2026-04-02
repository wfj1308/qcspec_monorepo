"""
BOQ progress-payment and sovereign audit helpers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from services.api.boq_audit_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    canonical_hash as _canonical_hash,
    extract_boq_item_uri as _extract_boq_item_uri,
    item_code_from_boq_uri as _item_no_from_uri,
    to_text as _to_text,
    verify_uri as _verify_uri,
)
from services.api.boq_payment_certificate_helpers import (
    chapter_from_item_no as _chapter_from_item_no,
    effective_design_quantity as _effective_design_quantity,
    extract_settled_quantity as _extract_settled_quantity,
    has_any_fail as _has_any_fail,
    has_tripartite_consensus as _has_tripartite_consensus,
    in_period as _in_period,
    is_leaf_boq_row as _is_leaf_boq_row,
    parse_period as _parse_period,
    safe_period_token as _safe_period_token,
    stage as _stage,
    to_float as _to_float,
)
from services.api.domain.boq.integrations import docpeg_get_proof_chain
from services.api.domain.execution.integrations import resolve_dual_pass_gate
from services.api.labpeg_frequency_remediation_service import (
    generate_railpact_payment_instruction,
)
from services.api.domain.execution.flows import export_doc_final, get_full_lineage
from services.api.domain.utxo.integrations import ProofUTXOEngine
from services.api.workers.gitpeg_anchor_worker import GitPegAnchorWorker


def generate_payment_certificate(
    *,
    sb: Any,
    project_uri: str,
    period: str,
    project_name: str | None = None,
    verify_base_url: str = "https://verify.qcspec.com",
    create_proof: bool = True,
    executor_uri: str = "v://executor/system/",
    enforce_dual_pass: bool = True,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    period_start, period_end, period_label = _parse_period(period)
    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .order("created_at", desc=False)
            .limit(20000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to query proof_utxo: {exc}") from exc

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_leaf_boq_row(row):
            continue
        boq_item_uri = _extract_boq_item_uri(row)
        if not boq_item_uri.startswith("v://"):
            continue
        grouped.setdefault(boq_item_uri, []).append(row)

    line_items: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    locks: list[dict[str, Any]] = []
    chapter_totals: dict[str, dict[str, Any]] = {}

    payable_qty_total = 0.0
    payable_amount_total = 0.0
    excluded_count = 0
    dual_pass_blocked_count = 0

    for boq_item_uri, bucket in grouped.items():
        bucket.sort(key=lambda r: _to_text(r.get("created_at") or ""))
        genesis_rows: list[dict[str, Any]] = []
        settlement_rows: list[dict[str, Any]] = []
        for row in bucket:
            st = _stage(row)
            ptype = _to_text(row.get("proof_type") or "").strip().lower()
            if st == "INITIAL" or ptype == "zero_ledger":
                genesis_rows.append(row)
            if st == "SETTLEMENT" and _to_text(row.get("result") or "").strip().upper() == "PASS":
                settlement_rows.append(row)

        genesis = genesis_rows[0] if genesis_rows else (bucket[0] if bucket else {})
        gsd = _as_dict(genesis.get("state_data"))
        design_qty = float(_effective_design_quantity(genesis, bucket))
        unit_price = _to_float(gsd.get("unit_price"))
        if unit_price is None:
            unit_price = _to_float(_as_dict(gsd.get("genesis_proof")).get("unit_price"))

        consensus_ok_rows: list[dict[str, Any]] = []
        consensus_fail_details: list[dict[str, Any]] = []
        for row in settlement_rows:
            ok, detail = _has_tripartite_consensus(row)
            if ok:
                consensus_ok_rows.append(row)
            else:
                consensus_fail_details.append(
                    {
                        "proof_id": _to_text(row.get("proof_id") or "").strip(),
                        "detail": detail,
                    }
                )

        cumulative_qty = 0.0
        period_qty = 0.0
        period_proof_ids: list[str] = []
        for row in consensus_ok_rows:
            qty = _extract_settled_quantity(row, fallback_design=None)
            cumulative_qty += qty
            if _in_period(row.get("created_at"), period_start, period_end):
                period_qty += qty
                pid = _to_text(row.get("proof_id") or "").strip()
                if pid:
                    period_proof_ids.append(pid)

        chain_rows = docpeg_get_proof_chain(boq_item_uri, sb)
        has_fail = _has_any_fail(chain_rows)
        overrun_locked = (design_qty > 0.0) and (cumulative_qty > design_qty + 1e-9)
        dual_gate = (
            resolve_dual_pass_gate(
                sb=sb,
                project_uri=normalized_project_uri,
                boq_item_uri=boq_item_uri,
                rows=rows,
            )
            if enforce_dual_pass
            else {
                "ok": True,
                "qc_pass_count": 0,
                "lab_pass_count": 0,
                "latest_lab_pass_proof_id": "",
            }
        )

        exclusion_reasons: list[str] = []
        if has_fail:
            exclusion_reasons.append("has_fail_proof")
        if overrun_locked:
            exclusion_reasons.append("overrun_locked")
            locks.append(
                {
                    "boq_item_uri": boq_item_uri,
                    "design_quantity": design_qty,
                    "cumulative_settled_quantity": round(cumulative_qty, 6),
                    "overflow_quantity": round(cumulative_qty - design_qty, 6),
                    "reason": "cumulative_settlement_exceeds_design_quantity",
                }
            )
        if enforce_dual_pass and not bool(dual_gate.get("ok")):
            exclusion_reasons.append("dual_pass_gate_failed")
            dual_pass_blocked_count += 1
            locks.append(
                {
                    "boq_item_uri": boq_item_uri,
                    "reason": "dual_pass_gate_failed",
                    "qc_pass_count": int(dual_gate.get("qc_pass_count") or 0),
                    "lab_pass_count": int(dual_gate.get("lab_pass_count") or 0),
                }
            )
        if unit_price is None:
            exclusion_reasons.append("unit_price_missing")
        if period_qty <= 0:
            exclusion_reasons.append("no_period_settlement")

        if consensus_fail_details:
            warnings.append(
                {
                    "boq_item_uri": boq_item_uri,
                    "type": "consensus_incomplete_settlement_excluded",
                    "details": consensus_fail_details,
                }
            )

        include_for_payment = not exclusion_reasons
        line_amount = round(period_qty * float(unit_price or 0.0), 2) if include_for_payment else 0.0

        item_no = _to_text(gsd.get("item_no") or _item_no_from_uri(boq_item_uri)).strip()
        item_name = _to_text(gsd.get("item_name") or "").strip()
        chapter = _chapter_from_item_no(item_no)

        line = {
            "boq_item_uri": boq_item_uri,
            "item_no": item_no,
            "item_name": item_name,
            "chapter": chapter,
            "unit": _to_text(gsd.get("unit") or "").strip(),
            "design_quantity": round(design_qty, 6),
            "unit_price": unit_price,
            "cumulative_settled_quantity": round(cumulative_qty, 6),
            "period_settled_quantity": round(period_qty, 6),
            "payable_quantity": round(period_qty if include_for_payment else 0.0, 6),
            "payable_amount": line_amount,
            "include_for_payment": include_for_payment,
            "excluded_reasons": exclusion_reasons,
            "has_fail_proof": has_fail,
            "overrun_locked": overrun_locked,
            "dual_pass_gate": dual_gate,
            "settlement_proof_ids": period_proof_ids,
            "settlement_verify_uris": [_verify_uri(verify_base_url, pid) for pid in period_proof_ids],
            "latest_lab_pass_proof_id": _to_text(dual_gate.get("latest_lab_pass_proof_id") or "").strip(),
        }
        line_items.append(line)

        if include_for_payment:
            payable_qty_total += period_qty
            payable_amount_total += line_amount
            chapter_total = chapter_totals.setdefault(
                chapter,
                {
                    "chapter": chapter,
                    "item_count": 0,
                    "payable_quantity": 0.0,
                    "payable_amount": 0.0,
                },
            )
            chapter_total["item_count"] += 1
            chapter_total["payable_quantity"] = float(chapter_total["payable_quantity"]) + period_qty
            chapter_total["payable_amount"] = float(chapter_total["payable_amount"]) + line_amount
        else:
            excluded_count += 1

    line_items.sort(key=lambda x: (_chapter_from_item_no(_to_text(x.get("item_no") or "")), _to_text(x.get("item_no") or "")))
    chapter_rows = list(chapter_totals.values())
    chapter_rows.sort(key=lambda x: _to_text(x.get("chapter") or ""))
    for chapter in chapter_rows:
        chapter["payable_quantity"] = round(float(chapter["payable_quantity"]), 6)
        chapter["payable_amount"] = round(float(chapter["payable_amount"]), 2)

    locked = len(locks) > 0
    summary = {
        "project_uri": normalized_project_uri,
        "project_name": _to_text(project_name or "").strip(),
        "period": period_label,
        "line_count": len(line_items),
        "included_count": len(line_items) - excluded_count,
        "excluded_count": excluded_count,
        "locked": locked,
        "dual_pass_required": bool(enforce_dual_pass),
        "dual_pass_blocked_count": dual_pass_blocked_count,
        "payable_quantity_total": round(payable_qty_total, 6),
        "payable_amount_total": round(payable_amount_total, 2),
    }

    certificate_payload = {
        "summary": summary,
        "chapters": chapter_rows,
        "line_items": line_items,
        "warnings": warnings,
        "locks": locks,
    }
    certificate_hash = _canonical_hash(certificate_payload)

    proof_row: dict[str, Any] | None = None
    proof_id = ""
    if create_proof:
        proof_id = f"GP-PAYCERT-{certificate_hash[:16].upper()}"
        proof_state = {
            "certificate_type": "interim_progress_payment",
            "period": period_label,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project_uri": normalized_project_uri,
            "project_name": _to_text(project_name or "").strip(),
            "root_hash": certificate_hash,
            "summary": summary,
            "chapters": chapter_rows,
            "lines": line_items,
            "warnings": warnings,
            "locks": locks,
            "status": "LOCKED" if locked else "READY",
            "artifact_uri": f"{normalized_project_uri.rstrip('/')}/payment/certificate/{period_label}/{certificate_hash[:16]}",
        }
        engine = ProofUTXOEngine(sb)
        create_kwargs = {
            "owner_uri": _to_text(executor_uri).strip() or "v://executor/system/",
            "project_uri": normalized_project_uri,
            "project_id": None,
            "proof_type": "payment",
            "result": "FAIL" if locked else "PASS",
            "state_data": proof_state,
            "conditions": [],
            "parent_proof_id": None,
            "norm_uri": "v://norm/CoordOS/BOQProgressPayment/1.0#payment_certificate",
            "segment_uri": f"{normalized_project_uri.rstrip('/')}/boq/payment/{_safe_period_token(period_label)}",
            "signer_uri": _to_text(executor_uri).strip() or "v://executor/system/",
            "signer_role": "DOCPEG",
        }
        try:
            proof_row = engine.create(
                proof_id=proof_id,
                **create_kwargs,
            )
        except Exception:
            fallback_id = f"{proof_id}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
            proof_row = engine.create(
                proof_id=fallback_id,
                **create_kwargs,
            )
        proof_id = _to_text((proof_row or {}).get("proof_id") or proof_id).strip()

    return {
        "ok": True,
        "payment_id": proof_id,
        "payment_certificate": certificate_payload,
        "payment_certificate_hash": certificate_hash,
        "proof": proof_row or {},
    }


def audit_trace(*, sb: Any, payment_id: str, verify_base_url: str = "https://verify.qcspec.com") -> dict[str, Any]:
    pid = _to_text(payment_id).strip()
    if not pid:
        raise HTTPException(400, "payment_id is required")

    row = ProofUTXOEngine(sb).get_by_id(pid)
    if not row:
        raise HTTPException(404, "payment certificate not found")

    sd = _as_dict(row.get("state_data"))
    lines = _as_list(sd.get("lines"))
    if not lines:
        raise HTTPException(409, "payment certificate has no line details")

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    lineage_by_proof: dict[str, Any] = {}

    def add_node(node_id: str, payload: dict[str, Any]) -> None:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, **payload}

    def add_edge(src: str, dst: str, relation: str) -> None:
        edges.append({"from": src, "to": dst, "relation": relation})

    root_id = f"payment:{pid}"
    add_node(
        root_id,
        {
            "type": "payment_certificate",
            "label": pid,
            "proof_id": pid,
            "verify_uri": _verify_uri(verify_base_url, pid),
            "amount_total": _as_dict(sd.get("summary")).get("payable_amount_total"),
            "period": _to_text(sd.get("period") or ""),
        },
    )
    tree_root = {"id": root_id, "label": pid, "type": "payment_certificate", "children": []}

    for line in lines:
        if not isinstance(line, dict):
            continue
        item_no = _to_text(line.get("item_no") or "").strip() or "unknown"
        line_node_id = f"amount:{item_no}"
        add_node(
            line_node_id,
            {
                "type": "amount",
                "label": f"{item_no}: {line.get('payable_amount')} CNY",
                "boq_item_uri": _to_text(line.get("boq_item_uri") or "").strip(),
                "excluded_reasons": _as_list(line.get("excluded_reasons")),
            },
        )
        add_edge(root_id, line_node_id, "amount")
        line_tree = {"id": line_node_id, "label": nodes[line_node_id]["label"], "type": "amount", "children": []}

        for proof_id in _as_list(line.get("settlement_proof_ids")):
            settlement_id = _to_text(proof_id).strip()
            if not settlement_id:
                continue
            qty_node_id = f"quantity:{settlement_id}"
            add_node(
                qty_node_id,
                {
                    "type": "quantity",
                    "label": f"Settled {line.get('period_settled_quantity')} {line.get('unit') or ''}",
                    "proof_id": settlement_id,
                    "verify_uri": _verify_uri(verify_base_url, settlement_id),
                },
            )
            add_edge(line_node_id, qty_node_id, "quantity")
            qty_tree = {"id": qty_node_id, "label": nodes[qty_node_id]["label"], "type": "quantity", "children": []}

            try:
                lineage = get_full_lineage(settlement_id, sb)
            except Exception:
                lineage = {}
            lineage_by_proof[settlement_id] = lineage

            quality_nodes_added: set[str] = set()
            for qc in _as_list(lineage.get("qc_conclusions")):
                if not isinstance(qc, dict):
                    continue
                qc_id = _to_text(qc.get("proof_id") or "").strip() or settlement_id
                qc_node_id = f"quality:{qc_id}"
                add_node(
                    qc_node_id,
                    {
                        "type": "quality",
                        "label": f"{_to_text(qc.get('stage') or '-')}: {_to_text(qc.get('qc_conclusion') or qc.get('result') or '-')}",
                        "proof_id": qc_id,
                        "verify_uri": _verify_uri(verify_base_url, qc_id),
                    },
                )
                add_edge(qty_node_id, qc_node_id, "quality")
                quality_nodes_added.add(qc_node_id)
                qty_tree["children"].append(
                    {"id": qc_node_id, "label": nodes[qc_node_id]["label"], "type": "quality", "children": []}
                )

            for norm_uri in _as_list(lineage.get("norm_refs")):
                uri = _to_text(norm_uri).strip()
                if not uri:
                    continue
                norm_node_id = f"norm:{uri}"
                add_node(norm_node_id, {"type": "norm", "label": uri, "norm_uri": uri})
                if quality_nodes_added:
                    for qid in quality_nodes_added:
                        add_edge(qid, norm_node_id, "norm")
                else:
                    add_edge(qty_node_id, norm_node_id, "norm")

            for evidence in _as_list(lineage.get("evidence_hashes")):
                if not isinstance(evidence, dict):
                    continue
                h = _to_text(evidence.get("hash") or "").strip().lower()
                if not h:
                    continue
                evidence_node_id = f"evidence:{h}"
                add_node(
                    evidence_node_id,
                    {
                        "type": "evidence",
                        "label": h[:20],
                        "hash": h,
                        "source_url": _to_text(evidence.get("source_url") or "").strip(),
                        "proof_id": _to_text(evidence.get("proof_id") or "").strip(),
                    },
                )
                if quality_nodes_added:
                    for qid in quality_nodes_added:
                        add_edge(qid, evidence_node_id, "evidence")
                else:
                    add_edge(qty_node_id, evidence_node_id, "evidence")

            for sig in _as_list(lineage.get("consensus_signatures")):
                if not isinstance(sig, dict):
                    continue
                did = _to_text(sig.get("did") or "").strip()
                sig_hash = _to_text(sig.get("signature_hash") or "").strip().lower()
                role = _to_text(sig.get("role") or "").strip().lower()
                signer_id = sig_hash or did or role
                if not signer_id:
                    continue
                signer_node_id = f"signer:{signer_id}"
                add_node(
                    signer_node_id,
                    {
                        "type": "signer",
                        "label": f"{role}:{did or '-'}",
                        "did": did,
                        "role": role,
                        "signature_hash": sig_hash,
                    },
                )
                add_edge(qty_node_id, signer_node_id, "signed_by")

            line_tree["children"].append(qty_tree)
        tree_root["children"].append(line_tree)

    return {
        "ok": True,
        "payment_id": pid,
        "project_uri": _to_text(row.get("project_uri") or "").strip(),
        "period": _to_text(sd.get("period") or "").strip(),
        "summary": _as_dict(sd.get("summary")),
        "lines": lines,
        "nodes": list(nodes.values()),
        "edges": edges,
        "tree": tree_root,
        "lineage_by_proof": lineage_by_proof,
    }


def generate_railpact_instruction(
    *,
    sb: Any,
    payment_id: str,
    executor_uri: str = "v://executor/owner/system/",
    auto_submit: bool = False,
) -> dict[str, Any]:
    return generate_railpact_payment_instruction(
        sb=sb,
        payment_id=payment_id,
        executor_uri=executor_uri,
        auto_submit=auto_submit,
    )


def finalize_docfinal_delivery(
    *,
    sb: Any,
    project_uri: str,
    project_name: str | None = None,
    passphrase: str = "",
    verify_base_url: str = "https://verify.qcspec.com",
    include_unsettled: bool = False,
    run_anchor_rounds: int = 1,
) -> dict[str, Any]:
    result = export_doc_final(
        sb=sb,
        project_uri=project_uri,
        project_name=project_name,
        passphrase=passphrase,
        verify_base_url=verify_base_url,
        include_unsettled=include_unsettled,
    )
    proof_id = _to_text(_as_dict(result.get("birth_certificate")).get("proof_id") or "").strip()

    anchor_runs: list[dict[str, Any]] = []
    rounds = max(0, min(int(run_anchor_rounds or 0), 5))
    if rounds > 0:
        worker = GitPegAnchorWorker()
        for _ in range(rounds):
            try:
                anchor_runs.append(worker.anchor_once())
            except Exception as exc:
                anchor_runs.append({"ok": False, "error": f"{exc.__class__.__name__}: {exc}"})

    final_anchor = ""
    if proof_id:
        proof_row = ProofUTXOEngine(sb).get_by_id(proof_id)
        final_anchor = _to_text((proof_row or {}).get("gitpeg_anchor") or "").strip()

    birth_certificate = dict(_as_dict(result.get("birth_certificate")))
    if final_anchor:
        birth_certificate["gitpeg_anchor"] = final_anchor

    return {
        **result,
        "birth_certificate": birth_certificate,
        "final_gitpeg_anchor": final_anchor,
        "anchor_runs": anchor_runs,
    }
