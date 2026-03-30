"""
Flow helpers for public verify router.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import io
import json
import re
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from supabase import Client

from services.api.archive_service import create_dsp_package
from services.api.normpeg_engine import NormPegEngine
from services.api.specir_engine import (
    normalize_spec_uri as specir_normalize_spec_uri,
    resolve_spec_rule as specir_resolve_spec_rule,
    result_cn as specir_result_cn,
    threshold_text as specir_threshold_text,
)
from services.api.verify_service import (
    get_project_name_by_id,
    get_proof_ancestry as svc_get_proof_ancestry,
    get_proof_descendants as svc_get_proof_descendants,
)
from services.api.verify_facade_service import (
    build_chain_fingerprints,
    build_public_verify_detail,
)
from services.api.unit_merkle_service import build_unit_merkle_snapshot
from services.api.verify_enrich_service import build_enriched_row as svc_build_enriched_row
from services.api.verify_evidence_service import build_evidence_items as svc_build_evidence_items
from services.api.verify_view_service import (
    build_audit_rows as svc_build_audit_rows,
    build_chain as svc_build_chain,
    build_context as svc_build_context,
    build_gitpeg_status as svc_build_gitpeg_status,
    build_qcgate as svc_build_qcgate,
    build_remediation_info as svc_build_remediation_info,
    build_timeline as svc_build_timeline,
)

from services.api.proof_utxo_engine import ProofUTXOEngine
from services.api.workers.gitpeg_anchor_worker import GitPegAnchorWorker


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = str(value).strip()
        if not text:
            return None
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _parse_limit(value: Any) -> float | None:
    text = _to_text(value).strip()
    if not text:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return abs(float(m.group(0)))
    except Exception:
        return None


def _display_time(value: Any) -> str:
    text = _to_text(value).strip()
    if not text:
        return "-"
    normalized = text
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
        return dt.replace(tzinfo=None, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    cleaned = text.replace("T", " ").strip()
    cleaned = re.sub(r"\.\d+", "", cleaned)
    cleaned = re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", cleaned).strip()
    sec_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", cleaned)
    if sec_match:
        return sec_match.group(1).replace("  ", " ")
    min_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})$", cleaned)
    if min_match:
        return f"{min_match.group(1).replace('  ', ' ')}:00"
    return cleaned


def _result_cn(value: Any) -> str:
    return specir_result_cn(value)


def _stake_from_row(row: dict[str, Any]) -> str:
    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    stake = _to_text(sd.get("stake") or sd.get("location") or "").strip()
    if stake:
        return stake
    segment_uri = _to_text(row.get("segment_uri") or sd.get("segment_uri") or "").strip().rstrip("/")
    if segment_uri and "/" in segment_uri:
        return segment_uri.split("/")[-1]
    return "-"


def _hash_payload_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof_id": _to_text(row.get("proof_id") or ""),
        "owner_uri": _to_text(row.get("owner_uri") or ""),
        "project_uri": _to_text(row.get("project_uri") or ""),
        "project_id": row.get("project_id"),
        "segment_uri": row.get("segment_uri"),
        "proof_type": _to_text(row.get("proof_type") or "inspection").lower(),
        "result": _to_text(row.get("result") or "PENDING").upper(),
        "state_data": row.get("state_data") if isinstance(row.get("state_data"), dict) else {},
        "conditions": row.get("conditions") if isinstance(row.get("conditions"), list) else [],
        "parent_proof_id": row.get("parent_proof_id"),
        "norm_uri": row.get("norm_uri"),
    }


def _hash_json(payload: dict[str, Any]) -> tuple[str, str]:
    source = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return digest, source


def _get_proof_ancestry(
    engine: ProofUTXOEngine,
    proof_id: str,
    *,
    max_depth: int = 128,
    _seen: set[str] | None = None,
) -> list[dict[str, Any]]:
    return svc_get_proof_ancestry(engine, proof_id, max_depth=max_depth, _seen=_seen)


def _get_proof_descendants(
    engine: ProofUTXOEngine,
    proof_id: str,
    *,
    max_depth: int = 8,
    max_nodes: int = 256,
) -> list[dict[str, Any]]:
    return svc_get_proof_descendants(engine, proof_id, max_depth=max_depth, max_nodes=max_nodes)


def _remediation_info(
    *,
    root_proof_id: str,
    descendants_enriched: list[dict[str, Any]],
) -> dict[str, Any]:
    return svc_build_remediation_info(
        root_proof_id=root_proof_id,
        descendants_enriched=descendants_enriched,
        result_cn=_result_cn,
    )


def _enriched_row(row: dict[str, Any], *, sb: Client | None = None) -> dict[str, Any]:
    return svc_build_enriched_row(
        row,
        sb=sb,
        to_text=_to_text,
        to_float=_to_float,
        parse_limit=_parse_limit,
        display_time=_display_time,
        hash_payload_from_row=_hash_payload_from_row,
        hash_json=_hash_json,
        result_cn=_result_cn,
    )


def _build_qcgate(ancestry_enriched: list[dict[str, Any]], stake: str) -> dict[str, Any]:
    return svc_build_qcgate(ancestry_enriched, stake)


def _build_timeline(ancestry_enriched: list[dict[str, Any]], qcgate: dict[str, Any]) -> list[dict[str, Any]]:
    return svc_build_timeline(
        ancestry_enriched,
        qcgate,
        result_cn=_result_cn,
    )


def _build_chain(ancestry_enriched: list[dict[str, Any]], current_proof_id: str) -> list[dict[str, Any]]:
    return svc_build_chain(ancestry_enriched, current_proof_id)


def _build_audit_rows(ancestry_enriched: list[dict[str, Any]], qcgate: dict[str, Any]) -> list[dict[str, Any]]:
    return svc_build_audit_rows(ancestry_enriched, qcgate)


def _build_context(row: dict[str, Any], stake: str, executor_uri: str) -> dict[str, str]:
    return svc_build_context(row, stake, executor_uri)


def _build_gitpeg_status(gitpeg_anchor: str) -> dict[str, Any]:
    return svc_build_gitpeg_status(gitpeg_anchor)


def _collect_evidence(
    *,
    sb: Client,
    latest_row: dict[str, Any],
    chain_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return svc_build_evidence_items(
        sb=sb,
        latest_row=latest_row,
        chain_rows=chain_rows,
        display_time=_display_time,
    )


def _mock_signer_cert(executor_uri: str) -> dict[str, str]:
    seed = hashlib.sha256(_to_text(executor_uri).encode("utf-8")).hexdigest()
    pub = f"MOCK-ED25519-{seed[:64]}"
    pem = (
        "-----BEGIN PUBLIC KEY-----\n"
        f"{pub}\n"
        "-----END PUBLIC KEY-----\n"
    )
    return {"algorithm": "ed25519-mock", "public_key": pub, "public_key_pem": pem}


async def resolve_spec_rule_public_flow(
    *,
    spec_uri: str,
    metric: str,
    component_type: str,
    sb: Client,
) -> dict[str, Any]:
    resolved = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=metric,
        test_type=metric,
        test_name=metric,
        context={"component_type": component_type},
        sb=sb,
    )
    return {
        "ok": True,
        "input_spec_uri": specir_normalize_spec_uri(spec_uri),
        "resolved": resolved,
        "threshold_text": specir_threshold_text(
            resolved.get("operator"),
            _to_float(resolved.get("threshold")),
            _to_float(resolved.get("tolerance")),
            resolved.get("unit"),
        ),
    }


async def resolve_normpeg_threshold_public_flow(
    *,
    spec_uri: str,
    context: str = "",
    value: float | None = None,
    design: float | None = None,
    sb: Client,
) -> dict[str, Any]:
    engine = NormPegEngine.from_sources(sb=sb)
    threshold = engine.get_threshold(
        spec_uri,
        {
            "context": context,
            "component_type": context,
        },
    )

    payload: dict[str, Any] = {
        "ok": bool(threshold.get("found")),
        "input_spec_uri": spec_uri,
        "context": context,
        "threshold": threshold,
    }
    if value is not None:
        evaluated = engine.evaluate(
            spec_uri=spec_uri,
            context={"context": context, "component_type": context},
            values=[float(value)],
            design_value=design,
        )
        payload["evaluation"] = evaluated
    return payload


async def run_mock_anchor_once_flow() -> dict[str, Any]:
    worker = GitPegAnchorWorker()
    result = worker.anchor_once()
    return {"ok": True, "worker_enabled": worker.enabled, "result": result}


async def get_public_verify_detail_flow(
    *,
    proof_id: str,
    lineage_depth: str,
    sb: Client,
    verify_base_url: str,
) -> dict[str, Any]:
    engine = ProofUTXOEngine(sb)
    depth = _to_text(lineage_depth or "item").strip().lower()
    if depth not in {"item", "unit", "project"}:
        depth = "item"
    detail = build_public_verify_detail(
        proof_id=proof_id,
        sb=sb,
        engine=engine,
        verify_base_url=verify_base_url,
        to_text=_to_text,
        stake_from_row=_stake_from_row,
        enriched_row=_enriched_row,
        get_project_name_by_id=get_project_name_by_id,
        build_context=_build_context,
        build_qcgate=_build_qcgate,
        result_cn=_result_cn,
        hash_payload_from_row=_hash_payload_from_row,
        hash_json=_hash_json,
        build_gitpeg_status=_build_gitpeg_status,
        get_proof_ancestry=_get_proof_ancestry,
        get_proof_descendants=_get_proof_descendants,
        remediation_info=_remediation_info,
        build_timeline=_build_timeline,
        build_chain=_build_chain,
        build_audit_rows=_build_audit_rows,
        collect_evidence=_collect_evidence,
    )
    context = detail.get("context") if isinstance(detail.get("context"), dict) else {}
    project_uri = _to_text(context.get("project_uri") or "").strip()
    merkle_snapshot: dict[str, Any] = {}
    if project_uri:
        try:
            merkle_snapshot = build_unit_merkle_snapshot(
                sb=sb,
                project_uri=project_uri,
                proof_id=proof_id,
            )
        except Exception:
            merkle_snapshot = {}
    detail["lineage_depth"] = depth
    detail["lineage_merkle"] = {
        "mode": depth,
        "project_uri": project_uri,
        "requested_proof_id": _to_text(proof_id).strip(),
        "requested_item_uri": _to_text(merkle_snapshot.get("requested_item_uri") or "").strip(),
        "resolved_unit_code": _to_text(merkle_snapshot.get("resolved_unit_code") or "").strip(),
        "unit_root_hash": _to_text(merkle_snapshot.get("unit_root_hash") or "").strip(),
        "project_root_hash": _to_text(merkle_snapshot.get("project_root_hash") or "").strip(),
        "global_project_fingerprint": _to_text(merkle_snapshot.get("global_project_fingerprint") or "").strip(),
        "item_index": merkle_snapshot.get("item_index"),
        "unit_index": merkle_snapshot.get("unit_index"),
        "leaf_count": merkle_snapshot.get("leaf_count"),
        "item_merkle_path": merkle_snapshot.get("item_merkle_path") if isinstance(merkle_snapshot.get("item_merkle_path"), list) else [],
        "unit_merkle_path": merkle_snapshot.get("unit_merkle_path") if isinstance(merkle_snapshot.get("unit_merkle_path"), list) else [],
    }
    return detail


async def download_dsp_package_flow(
    *,
    proof_id: str,
    sb: Client,
    verify_base_url: str,
) -> StreamingResponse:
    normalized_proof_id = _to_text(proof_id).strip()
    if not normalized_proof_id:
        raise HTTPException(400, "proof_id is required")

    engine = ProofUTXOEngine(sb)
    detail = await get_public_verify_detail_flow(
        proof_id=normalized_proof_id,
        lineage_depth="item",
        sb=sb,
        verify_base_url=verify_base_url,
    )

    ancestry = _get_proof_ancestry(engine, normalized_proof_id)
    descendants = _get_proof_descendants(engine, normalized_proof_id, max_depth=12, max_nodes=512)
    raw_chain = ancestry + descendants

    chain_fingerprints = build_chain_fingerprints(
        raw_chain=raw_chain,
        hash_payload_from_row=_hash_payload_from_row,
        hash_json=_hash_json,
        to_text=_to_text,
        display_time=_display_time,
    )

    person = detail.get("person") if isinstance(detail.get("person"), dict) else {}
    cert = _mock_signer_cert(_to_text(person.get("uri") or "v://executor/system"))

    dsp_bytes = create_dsp_package(
        proof_id=normalized_proof_id,
        verify_detail=detail,
        chain_fingerprints=chain_fingerprints,
        signer_certificate=cert,
    )
    filename = f"DSP-{normalized_proof_id}.zip"
    return StreamingResponse(
        io.BytesIO(dsp_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
