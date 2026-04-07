"""BOQPeg product-level orchestration helpers.

These helpers package BOQPeg engines into an independent product surface while
keeping DocPeg Core + GitPeg as the foundational runtime.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import re
from typing import Any

from fastapi import HTTPException

from services.api.domain.boqpeg.runtime.bridge_entity import (
    get_bridge_pile_detail,
    get_full_line_pile_summary,
)
from services.api.domain.utxo.integrations import ProofUTXOEngine


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _to_text(value).strip().lower()
    if not text:
        return bool(default)
    return text in {"1", "true", "yes", "on"}


def _slug(value: str) -> str:
    text = re.sub(r"\s+", "-", _to_text(value).strip().lower())
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "bridge"


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def boqpeg_product_manifest() -> dict[str, Any]:
    return {
        "ok": True,
        "product": {
            "name": "BOQPeg",
            "aliases": ["ListPeg", "清单主权引擎"],
            "positioning": "独立清单解析 + 图纸闭合 + 自动出表产品，底层统一走 DocPeg Core API + GitPeg。",
            "core_engine": "DocPeg Core API",
            "registry_engine": "GitPeg",
            "closed_loop": [
                "正向(BOQ->BOM)",
                "反向(图纸/消耗->BOQ校核)",
                "Proof闭合",
                "FinalProof",
            ],
        },
        "foundation": {
            "normref_logic_scaffold": {
                "status": "ready",
                "l0": "v://normref.com/core@v1",
                "l1": "v://normref.com/construction/highway@v1",
                "l2": "v://normref.com/qc/raft-foundation@v1",
                "schema": "v://normref.com/schema/qc-v1",
                "first_case_spu": "v://normref.com/spu/raft-foundation@v1",
                "entry": {
                    "bootstrap": "/product/normref/logic-scaffold",
                    "tab_to_peg": "/product/normref/tab-to-peg",
                },
            }
        },
        "mvp": {
            "phase1": {
                "done": True,
                "scope": [
                    "上传 BOQ 并解析",
                    "桥名节点注册与映射",
                    "全线 vs 单桥桩基对比表",
                    "对比表 Proof Hash + v:// 报告地址",
                ],
                "entry": {
                    "manifest": "/product/manifest",
                    "phase1_report": "/product/mvp/phase1/bridge-pile-report",
                },
            },
            "phase2": {
                "done": True,
                "scope": [
                    "图纸解析(PDF/IFC/DWG)",
                    "BOQ-图纸匹配与偏差 Proof",
                    "双向闭环(设计变更->BOQ调整)",
                ],
                "entry": {
                    "design_parse": "/boqpeg/engine/design/parse",
                    "design_match": "/boqpeg/engine/design-boq/match",
                    "bidirectional_closure": "/boqpeg/engine/design-boq/closure",
                },
            },
            "phase3": {
                "done": True,
                "scope": [
                    "正向 BOM 展开",
                    "反向守恒核算",
                    "进度款与统一财务对齐",
                ],
                "entry": {
                    "forward_bom": "/boqpeg/engine/forward-bom",
                    "reverse_conservation": "/boqpeg/engine/reverse-conservation",
                    "payment_progress": "/boqpeg/engine/payment-progress",
                    "unified_alignment": "/boqpeg/engine/unified-align",
                },
            },
        },
    }


def boqpeg_phase1_bridge_pile_report(
    *,
    sb: Any,
    body: dict[str, Any],
    commit: bool = False,
) -> dict[str, Any]:
    project_uri = _to_text(body.get("project_uri")).strip()
    bridge_name = _to_text(body.get("bridge_name")).strip()
    if not project_uri:
        raise HTTPException(400, "project_uri is required")
    if not bridge_name:
        raise HTTPException(400, "bridge_name is required")

    full_line = get_full_line_pile_summary(sb=sb, project_uri=project_uri)
    bridge = get_bridge_pile_detail(sb=sb, project_uri=project_uri, bridge_name=bridge_name)

    bridge_uri = _to_text(bridge.get("bridge_uri")).strip() or f"{project_uri.rstrip('/')}/bridge/{_slug(bridge_name)}"
    report_uri = f"{project_uri.rstrip('/')}/boqpeg/reports/bridge-pile/{_slug(bridge_name)}"

    compare_table = [
        {
            "scope": "full_line",
            "node_uri": _to_text(full_line.get("full_line_uri")).strip() or f"{project_uri.rstrip('/')}/full-line",
            "label": "全线",
            "pile_total": int(full_line.get("pile_total") or 0),
            "bridge_count": int(full_line.get("bridge_count") or 0),
        },
        {
            "scope": "single_bridge",
            "node_uri": bridge_uri,
            "label": bridge_name,
            "pile_total": int(bridge.get("total_piles") or 0),
            "bridge_count": 1,
        },
    ]
    delta = compare_table[0]["pile_total"] - compare_table[1]["pile_total"]

    generated_at = datetime.now(UTC).isoformat()
    report_payload = {
        "product": "BOQPeg",
        "phase": "phase1",
        "report_kind": "full-line-vs-bridge-piles",
        "project_uri": project_uri,
        "bridge_name": bridge_name,
        "bridge_uri": bridge_uri,
        "report_uri": report_uri,
        "generated_at": generated_at,
        "compare_table": compare_table,
        "delta_piles": delta,
        "pile_items": bridge.get("pile_items") if isinstance(bridge.get("pile_items"), list) else [],
    }
    preview_hash = _stable_hash(report_payload)

    owner_uri = _to_text(body.get("owner_uri")).strip() or f"{project_uri.rstrip('/')}/role/system/"
    proof_id = f"GP-BOQPEG-RPT-{_sha16(f'{project_uri}:{bridge_uri}:{generated_at}').upper()}"
    proof = {
        "proof_id": proof_id,
        "proof_hash": preview_hash,
        "segment_uri": report_uri,
        "committed": False,
    }
    if _to_bool(commit, default=False) and sb is not None:
        row = ProofUTXOEngine(sb).create(
            proof_id=proof_id,
            owner_uri=owner_uri,
            project_uri=project_uri,
            proof_type="report",
            result="PASS",
            state_data={
                "proof_kind": "BOQPeg Phase1 Bridge Pile Report",
                "report_payload": report_payload,
            },
            norm_uri="v://norm/NormPeg/BOQPeg/Phase1BridgePileReport/1.0",
            segment_uri=report_uri,
            signer_uri=owner_uri,
            signer_role="SYSTEM",
        )
        proof["committed"] = True
        proof["row"] = row
        proof["proof_hash"] = _to_text(row.get("proof_hash")).strip() or preview_hash

    return {
        "ok": True,
        "report_uri": report_uri,
        "project_uri": project_uri,
        "bridge_uri": bridge_uri,
        "bridge_name": bridge_name,
        "generated_at": generated_at,
        "tables": {
            "full_line_vs_bridge_piles": compare_table,
            "bridge_pile_items": report_payload["pile_items"],
        },
        "summary": {
            "full_line_piles": compare_table[0]["pile_total"],
            "bridge_piles": compare_table[1]["pile_total"],
            "delta_piles": delta,
        },
        "proof": proof,
    }


__all__ = [
    "boqpeg_phase1_bridge_pile_report",
    "boqpeg_product_manifest",
]
