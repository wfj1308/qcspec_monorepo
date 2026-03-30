"""
Spatial twin mapping, proactive AI governance, and finance proof export.
"""

from __future__ import annotations

from datetime import datetime, timezone
import base64
import hashlib
import json
import re
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from services.api.docpeg_proof_chain_service import get_proof_chain
from services.api.proof_utxo_engine import ProofUTXOEngine
from services.api.triprole_engine import get_full_lineage
from services.api.workers.gitpeg_anchor_worker import GitPegAnchorWorker


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


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_boq_item_uri(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    for key in ("boq_item_uri", "item_uri", "boq_uri"):
        uri = _to_text(sd.get(key) or "").strip()
        if uri.startswith("v://"):
            return uri
    segment = _to_text(row.get("segment_uri") or "").strip()
    if "/boq/" in segment:
        return segment
    return ""


def _stage(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    if stage:
        return stage
    if _to_text(row.get("proof_type") or "").strip().lower() == "zero_ledger":
        return "INITIAL"
    return ""


def _payment_status(row: dict[str, Any]) -> str:
    st = _stage(row)
    result = _to_text(row.get("result") or "").strip().upper()
    if st == "SETTLEMENT" and result == "PASS":
        return "settled"
    if result == "FAIL":
        return "failed"
    return "in_progress"


def _spatial_color(row: dict[str, Any], has_fail: bool) -> tuple[str, str]:
    if has_fail:
        return "#DC2626", "failed"
    st = _stage(row)
    result = _to_text(row.get("result") or "").strip().upper()
    if st == "SETTLEMENT" and result == "PASS":
        return "#16A34A", "settled"
    return "#EAB308", "inspecting"


def _spatial_fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_token(value: str, fallback: str = "node") -> str:
    token = re.sub(r"[^a-zA-Z0-9_\-]+", "-", _to_text(value).strip()).strip("-")
    return token[:80] or fallback


def _extract_coordinate(coordinate: Any) -> dict[str, Any]:
    c = _as_dict(coordinate)
    lat = _to_float(c.get("lat"))
    lng = _to_float(c.get("lng"))
    alt = _to_float(c.get("alt"))
    x = _to_float(c.get("x"))
    y = _to_float(c.get("y"))
    z = _to_float(c.get("z"))
    return {
        "lat": lat,
        "lng": lng,
        "alt": alt,
        "x": x,
        "y": y,
        "z": z,
    }


def _extract_deviation_and_critical(row: dict[str, Any], default_critical_threshold: float) -> tuple[float | None, float]:
    sd = _as_dict(row.get("state_data"))
    norm_eval = _as_dict(sd.get("norm_evaluation"))
    deviation = _to_float(norm_eval.get("deviation_percent"))
    if deviation is None:
        deviation = _to_float(sd.get("deviation_percent"))

    critical = _to_float(norm_eval.get("critical_threshold"))
    threshold = _as_dict(norm_eval.get("threshold"))
    raw_threshold = threshold.get("threshold")
    if critical is None and isinstance(raw_threshold, list) and len(raw_threshold) >= 2:
        lo = _to_float(raw_threshold[0])
        hi = _to_float(raw_threshold[1])
        if lo is not None and hi is not None:
            critical = max(abs(lo), abs(hi))
    if critical is None:
        tolerance = _to_float(_as_dict(sd.get("spec_rule")).get("tolerance"))
        if tolerance is not None:
            critical = abs(tolerance)
    if critical is None or critical <= 0:
        critical = max(0.001, float(default_critical_threshold))
    return deviation, float(critical)


def _encrypt_aes256(payload_bytes: bytes, passphrase: str) -> dict[str, Any]:
    key = hashlib.sha256(_to_text(passphrase).encode("utf-8")).digest()
    nonce = hashlib.sha256(payload_bytes + key).digest()[:12]
    aad = b"QCSpec-Finance-Proof-v1"
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, payload_bytes, aad)
    return {
        "algorithm": "AES-256-GCM",
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "aad": aad.decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "cipher_hash": hashlib.sha256(ciphertext).hexdigest(),
    }


def bind_utxo_to_spatial(
    *,
    sb: Any,
    utxo_id: str,
    bim_id: str | None = None,
    coordinate: dict[str, Any] | None = None,
    project_uri: str | None = None,
    label: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proof_id = _to_text(utxo_id).strip()
    if not proof_id:
        raise HTTPException(400, "utxo_id is required")

    engine = ProofUTXOEngine(sb)
    row = engine.get_by_id(proof_id)
    if not row:
        raise HTTPException(404, "utxo not found")

    row_project_uri = _to_text(row.get("project_uri") or "").strip()
    scoped_project_uri = _to_text(project_uri or "").strip()
    if scoped_project_uri and row_project_uri and scoped_project_uri != row_project_uri:
        raise HTTPException(409, "utxo project_uri mismatch")

    coord = _extract_coordinate(coordinate or {})
    boq_item_uri = _extract_boq_item_uri(row)
    spatial_payload = {
        "utxo_id": proof_id,
        "project_uri": row_project_uri,
        "boq_item_uri": boq_item_uri,
        "bim_id": _to_text(bim_id or "").strip(),
        "coordinate": coord,
        "label": _to_text(label or "").strip(),
        "metadata": _as_dict(metadata),
        "bound_at": _utc_iso(),
    }
    fingerprint = _spatial_fingerprint(spatial_payload)
    spatial_payload["spatial_fingerprint"] = fingerprint

    sd = _as_dict(row.get("state_data"))
    updated_sd = dict(sd)
    updated_sd["spatial"] = spatial_payload
    try:
        sb.table("proof_utxo").update({"state_data": updated_sd}).eq("proof_id", proof_id).execute()
    except Exception as exc:
        raise HTTPException(502, f"failed to update proof_utxo spatial payload: {exc}") from exc

    upsert_payload = {
        "proof_id": proof_id,
        "project_uri": row_project_uri,
        "boq_item_uri": boq_item_uri,
        "bim_id": _to_text(bim_id or "").strip(),
        "label": _to_text(label or "").strip(),
        "coordinate": coord,
        "spatial_fingerprint": fingerprint,
        "status": _payment_status(row),
        "updated_at": _utc_iso(),
    }
    try:
        sb.table("proof_spatial_map").upsert(upsert_payload, on_conflict="proof_id").execute()
    except Exception:
        # Optional table: keep API functional even before migration is applied.
        pass

    return {
        "ok": True,
        "proof_id": proof_id,
        "project_uri": row_project_uri,
        "boq_item_uri": boq_item_uri,
        "spatial": spatial_payload,
    }


def get_spatial_dashboard(*, sb: Any, project_uri: str, limit: int = 5000) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .order("created_at", desc=False)
            .limit(max(1, min(int(limit or 0), 20000)))
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to load proof_utxo: {exc}") from exc

    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        proof_id = _to_text(row.get("proof_id") or "").strip()
        if not proof_id:
            continue
        boq_item_uri = _extract_boq_item_uri(row)
        sd = _as_dict(row.get("state_data"))
        spatial = _as_dict(sd.get("spatial"))
        bim_id = _to_text(spatial.get("bim_id") or "").strip()
        bucket_key = boq_item_uri or bim_id or proof_id
        buckets.setdefault(bucket_key, []).append(row)

    assets: list[dict[str, Any]] = []
    color_counts = {"green": 0, "yellow": 0, "red": 0}
    for key, bucket in buckets.items():
        bucket.sort(key=lambda r: _to_text(r.get("created_at") or ""))
        latest = bucket[-1]
        sd = _as_dict(latest.get("state_data"))
        spatial = _as_dict(sd.get("spatial"))
        chain_fail = any(_to_text((row or {}).get("result") or "").strip().upper() == "FAIL" for row in bucket)
        color_hex, status = _spatial_color(latest, has_fail=chain_fail)
        color_name = "red" if status == "failed" else ("green" if status == "settled" else "yellow")
        color_counts[color_name] += 1

        norm_eval = _as_dict(sd.get("norm_evaluation"))
        threshold = _as_dict(norm_eval.get("threshold"))
        latest_pid = _to_text(latest.get("proof_id") or "").strip()
        boq_item_uri = _extract_boq_item_uri(latest)
        item_name = _to_text(sd.get("item_name") or "").strip()
        item_no = _to_text(sd.get("item_no") or "").strip()

        assets.append(
            {
                "asset_key": key,
                "proof_id": latest_pid,
                "boq_item_uri": boq_item_uri,
                "item_no": item_no,
                "item_name": item_name,
                "bim_id": _to_text(spatial.get("bim_id") or "").strip(),
                "coordinate": _extract_coordinate(spatial.get("coordinate")),
                "spatial_fingerprint": _to_text(spatial.get("spatial_fingerprint") or "").strip(),
                "status": status,
                "color": color_hex,
                "stage": _stage(latest),
                "result": _to_text(latest.get("result") or "").strip().upper(),
                "payment_status": _payment_status(latest),
                "norm_snapshot": {
                    "spec_uri": _to_text(sd.get("spec_uri") or threshold.get("effective_spec_uri") or "").strip(),
                    "result": _to_text(norm_eval.get("result") or latest.get("result") or "").strip().upper(),
                    "deviation_percent": norm_eval.get("deviation_percent"),
                    "threshold": threshold,
                },
                "verify_uri": f"/v/{latest_pid}?trace=true" if latest_pid else "",
                "created_at": _to_text(latest.get("created_at") or "").strip(),
            }
        )

    assets.sort(key=lambda x: (_to_text(x.get("item_no") or ""), _to_text(x.get("bim_id") or ""), _to_text(x.get("proof_id") or "")))
    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "summary": {
            "asset_count": len(assets),
            "green_count": color_counts["green"],
            "yellow_count": color_counts["yellow"],
            "red_count": color_counts["red"],
        },
        "assets": assets,
    }


def predictive_quality_analysis(
    *,
    sb: Any,
    project_uri: str,
    near_threshold_ratio: float = 0.9,
    min_samples: int = 3,
    apply_dynamic_gate: bool = True,
    default_critical_threshold: float = 2.0,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    near_ratio = max(0.5, min(float(near_threshold_ratio or 0.0), 0.995))
    min_n = max(2, min(int(min_samples or 0), 50))

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
        raise HTTPException(502, f"failed to load proof_utxo: {exc}") from exc

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        norm_eval = _as_dict(sd.get("norm_evaluation"))
        has_norm = bool(_to_text(sd.get("spec_uri") or row.get("norm_uri") or "").strip()) or bool(norm_eval)
        if not has_norm:
            continue
        boq_item_uri = _extract_boq_item_uri(row)
        team_uri = _to_text(sd.get("team_uri") or row.get("signer_uri") or sd.get("inspector") or "").strip() or "team:unknown"
        norm_uri = _to_text(row.get("norm_uri") or sd.get("spec_uri") or "").strip() or "norm:unknown"
        key = f"{boq_item_uri}|{team_uri}|{norm_uri}"
        grouped.setdefault(key, []).append(row)

    warnings: list[dict[str, Any]] = []
    gate_updates: list[dict[str, Any]] = []
    total_samples = 0

    for key, bucket in grouped.items():
        deviations: list[float] = []
        proof_ids: list[str] = []
        critical = float(default_critical_threshold)
        for row in bucket:
            dev, crit = _extract_deviation_and_critical(row, default_critical_threshold=default_critical_threshold)
            if dev is None:
                continue
            deviations.append(abs(float(dev)))
            critical = max(0.001, float(crit))
            pid = _to_text(row.get("proof_id") or "").strip()
            if pid:
                proof_ids.append(pid)
        if len(deviations) < min_n:
            continue

        total_samples += len(deviations)
        mean_abs = sum(deviations) / len(deviations)
        variance = sum((x - mean_abs) ** 2 for x in deviations) / len(deviations)
        threshold = critical * near_ratio
        near_count = sum(1 for x in deviations if x >= threshold)
        near_ratio_observed = near_count / len(deviations)

        trend_up = False
        if len(deviations) >= 6:
            prev_avg = sum(deviations[-6:-3]) / 3.0
            curr_avg = sum(deviations[-3:]) / 3.0
            trend_up = curr_avg > prev_avg

        risk_level = "low"
        triggered = False
        if mean_abs >= threshold and near_ratio_observed >= 0.5:
            risk_level = "high"
            triggered = True
        elif mean_abs >= threshold or near_ratio_observed >= 0.6 or trend_up:
            risk_level = "medium"
            triggered = True

        if not triggered:
            continue

        boq_item_uri, team_uri, norm_uri = key.split("|", 2)
        warning = {
            "group_key": key,
            "boq_item_uri": boq_item_uri,
            "team_uri": team_uri,
            "norm_uri": norm_uri,
            "samples": len(deviations),
            "mean_abs_deviation": round(mean_abs, 6),
            "variance": round(variance, 6),
            "critical_threshold": round(critical, 6),
            "near_threshold": round(threshold, 6),
            "near_ratio": round(near_ratio_observed, 6),
            "trend_up": trend_up,
            "risk_level": risk_level,
            "recommendation": "Require expert manual review before next UTXO consume.",
            "proof_ids": proof_ids[-8:],
        }
        warnings.append(warning)

        if apply_dynamic_gate:
            if not boq_item_uri.startswith("v://"):
                continue
            try:
                q = sb.table("proof_utxo").select("*").eq("project_uri", normalized_project_uri).eq("spent", False)
                if boq_item_uri:
                    q = q.filter("state_data->>boq_item_uri", "eq", boq_item_uri)
                candidates = q.order("created_at", desc=True).limit(1).execute().data or []
            except Exception:
                candidates = []

            if not candidates:
                continue
            target = candidates[0]
            target_pid = _to_text(target.get("proof_id") or "").strip()
            target_conditions = _as_list(target.get("conditions"))

            condition_payload = {
                "type": "role",
                "value": "EXPERT",
                "reason": "ai_predictive_quality_warning",
                "rule": "predictive_quality_analysis",
                "warning_key": key,
                "created_at": _utc_iso(),
            }
            exists = any(
                isinstance(cond, dict)
                and _to_text(cond.get("type") or "").strip() == "role"
                and _to_text(cond.get("value") or "").strip().upper() == "EXPERT"
                for cond in target_conditions
            )
            if exists:
                gate_updates.append(
                    {
                        "proof_id": target_pid,
                        "boq_item_uri": boq_item_uri,
                        "status": "already_present",
                    }
                )
                continue

            updated_conditions = list(target_conditions) + [condition_payload]
            target_sd = _as_dict(target.get("state_data"))
            updated_sd = dict(target_sd)
            updated_sd["ai_governance"] = {
                "warning_key": key,
                "risk_level": risk_level,
                "mean_abs_deviation": round(mean_abs, 6),
                "critical_threshold": round(critical, 6),
                "near_ratio": round(near_ratio_observed, 6),
                "applied_at": _utc_iso(),
                "required_gate": "role:EXPERT",
            }
            try:
                sb.table("proof_utxo").update(
                    {
                        "conditions": updated_conditions,
                        "state_data": updated_sd,
                    }
                ).eq("proof_id", target_pid).execute()
                gate_updates.append(
                    {
                        "proof_id": target_pid,
                        "boq_item_uri": boq_item_uri,
                        "status": "applied",
                    }
                )
            except Exception as exc:
                gate_updates.append(
                    {
                        "proof_id": target_pid,
                        "boq_item_uri": boq_item_uri,
                        "status": f"failed:{exc.__class__.__name__}",
                    }
                )

    warnings.sort(key=lambda x: (str(x.get("risk_level")), -float(x.get("near_ratio") or 0.0), -float(x.get("mean_abs_deviation") or 0.0)))
    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "near_threshold_ratio": near_ratio,
        "min_samples": min_n,
        "total_samples": total_samples,
        "warning_count": len(warnings),
        "warnings": warnings,
        "gate_updates": gate_updates,
    }


def export_finance_proof(
    *,
    sb: Any,
    payment_id: str,
    bank_code: str = "",
    passphrase: str = "",
    run_anchor_rounds: int = 1,
) -> dict[str, Any]:
    pid = _to_text(payment_id).strip()
    if not pid:
        raise HTTPException(400, "payment_id is required")

    engine = ProofUTXOEngine(sb)
    payment_row = engine.get_by_id(pid)
    if not payment_row:
        raise HTTPException(404, "payment proof not found")

    sd = _as_dict(payment_row.get("state_data"))
    lines = _as_list(sd.get("lines"))
    if not lines:
        raise HTTPException(409, "payment proof has no line details")

    lineage_items: list[dict[str, Any]] = []
    for line in lines:
        if not isinstance(line, dict):
            continue
        boq_item_uri = _to_text(line.get("boq_item_uri") or "").strip()
        for proof_id in _as_list(line.get("settlement_proof_ids")):
            settlement_id = _to_text(proof_id).strip()
            if not settlement_id:
                continue
            try:
                lineage = get_full_lineage(settlement_id, sb)
            except Exception as exc:
                lineage = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
            lineage_items.append(
                {
                    "boq_item_uri": boq_item_uri,
                    "settlement_proof_id": settlement_id,
                    "lineage": lineage,
                }
            )

    payload = {
        "format": "QCSpec-Finance-Proof",
        "version": "1.0",
        "generated_at": _utc_iso(),
        "payment_id": pid,
        "project_uri": _to_text(payment_row.get("project_uri") or "").strip(),
        "project_name": _to_text(sd.get("project_name") or "").strip(),
        "bank_code": _to_text(bank_code).strip(),
        "payment_summary": _as_dict(sd.get("summary")),
        "payment_lines": lines,
        "payment_warnings": _as_list(sd.get("warnings")),
        "payment_locks": _as_list(sd.get("locks")),
        "payment_gitpeg_anchor": _to_text(payment_row.get("gitpeg_anchor") or "").strip(),
        "lineage_items": lineage_items,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    payload_hash = hashlib.sha256(canonical).hexdigest()
    encrypted = _encrypt_aes256(canonical, passphrase or payload_hash)

    finance_proof_id = f"GP-FIN-{payload_hash[:16].upper()}"
    finance_state = {
        "artifact_type": "finance_credit_proof",
        "payment_id": pid,
        "payload_hash": payload_hash,
        "bank_code": _to_text(bank_code).strip(),
        "generated_at": _utc_iso(),
        "lineage_count": len(lineage_items),
    }
    try:
        finance_row = engine.create(
            proof_id=finance_proof_id,
            owner_uri=_to_text(payment_row.get("owner_uri") or "").strip() or "v://executor/system/",
            project_uri=_to_text(payment_row.get("project_uri") or "").strip(),
            project_id=payment_row.get("project_id"),
            proof_type="archive",
            result="PASS",
            state_data=finance_state,
            conditions=[],
            parent_proof_id=pid,
            norm_uri="v://norm/CoordOS/FinanceGateway/1.0#credit_proof",
            segment_uri=f"{_to_text(payment_row.get('project_uri') or '').rstrip('/')}/finance/{_safe_token(pid, 'payment')}",
            signer_uri="v://executor/system/",
            signer_role="DOCPEG",
        )
    except Exception:
        finance_row = engine.create(
            proof_id=f"{finance_proof_id}-{datetime.now(timezone.utc).strftime('%H%M%S')}",
            owner_uri=_to_text(payment_row.get("owner_uri") or "").strip() or "v://executor/system/",
            project_uri=_to_text(payment_row.get("project_uri") or "").strip(),
            project_id=payment_row.get("project_id"),
            proof_type="archive",
            result="PASS",
            state_data=finance_state,
            conditions=[],
            parent_proof_id=pid,
            norm_uri="v://norm/CoordOS/FinanceGateway/1.0#credit_proof",
            segment_uri=f"{_to_text(payment_row.get('project_uri') or '').rstrip('/')}/finance/{_safe_token(pid, 'payment')}",
            signer_uri="v://executor/system/",
            signer_role="DOCPEG",
        )

    anchor_runs: list[dict[str, Any]] = []
    rounds = max(0, min(int(run_anchor_rounds or 0), 5))
    if rounds > 0:
        worker = GitPegAnchorWorker()
        for _ in range(rounds):
            try:
                anchor_runs.append(worker.anchor_once())
            except Exception as exc:
                anchor_runs.append({"ok": False, "error": f"{exc.__class__.__name__}: {exc}"})

    refreshed = engine.get_by_id(_to_text(finance_row.get("proof_id") or "").strip()) or finance_row
    final_anchor = _to_text(refreshed.get("gitpeg_anchor") or "").strip()

    blob = json.dumps(
        {
            "meta": {
                "format": payload["format"],
                "version": payload["version"],
                "payment_id": pid,
                "payload_hash": payload_hash,
                "finance_proof_id": _to_text(refreshed.get("proof_id") or "").strip(),
                "finance_gitpeg_anchor": final_anchor,
            },
            "encryption": encrypted,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    return {
        "ok": True,
        "payment_id": pid,
        "finance_proof_id": _to_text(refreshed.get("proof_id") or "").strip(),
        "payload_hash": payload_hash,
        "finance_gitpeg_anchor": final_anchor,
        "anchor_runs": anchor_runs,
        "blob_bytes": blob,
        "filename": f"FINANCE-PROOF-{payload_hash[:16]}.qcfp",
    }
