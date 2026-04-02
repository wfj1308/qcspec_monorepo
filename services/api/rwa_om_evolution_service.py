"""
RWA tokenization, sovereign O&M handover, and norm evolution report services.
"""

from __future__ import annotations

from datetime import datetime, timezone
import base64
import hashlib
import io
import json
import re
from typing import Any
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException

from services.api.domain.execution.flows import get_full_lineage
from services.api.domain.utxo.integrations import ProofUTXOEngine
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


def _stage(row: dict[str, Any]) -> str:
    sd = _as_dict(row.get("state_data"))
    stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    if stage:
        return stage
    if _to_text(row.get("proof_type") or "").strip().lower() == "zero_ledger":
        return "INITIAL"
    return ""


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


def _extract_item_no(row: dict[str, Any], boq_item_uri: str) -> str:
    sd = _as_dict(row.get("state_data"))
    item_no = _to_text(sd.get("item_no") or "").strip()
    if item_no:
        return item_no
    uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not uri:
        return ""
    return uri.split("/")[-1]


def _extract_settled_quantity(row: dict[str, Any], *, fallback_design: float | None = None) -> float:
    sd = _as_dict(row.get("state_data"))
    settlement = _as_dict(sd.get("settlement"))
    measurement = _as_dict(sd.get("measurement"))
    for path in (
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        settlement.get("confirmed_quantity"),
        sd.get("settled_quantity"),
        measurement.get("quantity"),
        measurement.get("used_quantity"),
        sd.get("quantity"),
    ):
        q = _to_float(path)
        if q is not None:
            return max(0.0, float(q))
    values = _as_list(measurement.get("values"))
    nums = [x for x in (_to_float(v) for v in values) if x is not None]
    if nums:
        return max(0.0, float(sum(nums) / len(nums)))
    if fallback_design is not None:
        return max(0.0, float(fallback_design))
    return 0.0


def _has_tripartite_consensus(row: dict[str, Any]) -> bool:
    sd = _as_dict(row.get("state_data"))
    consensus = _as_dict(sd.get("consensus"))
    signatures = _as_list(consensus.get("signatures"))
    role_set: set[str] = set()
    for sig in signatures:
        if not isinstance(sig, dict):
            continue
        role = _to_text(sig.get("role") or "").strip().lower()
        did = _to_text(sig.get("did") or "").strip()
        sig_hash = _to_text(sig.get("signature_hash") or "").strip().lower()
        if role and did.startswith("did:") and re.fullmatch(r"[a-f0-9]{64}", sig_hash):
            role_set.add(role)
    return {"contractor", "supervisor", "owner"}.issubset(role_set)


def _in_group(item_no: str, group_id: str) -> bool:
    token = _to_text(group_id).strip()
    if not token:
        return True
    normalized_item = _to_text(item_no).strip()
    return normalized_item == token or normalized_item.startswith(f"{token}-") or normalized_item.startswith(f"{token}.")


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _encrypt_aes256(payload_bytes: bytes, passphrase: str) -> dict[str, Any]:
    key = hashlib.sha256(_to_text(passphrase).encode("utf-8")).digest()
    nonce = hashlib.sha256(payload_bytes + key).digest()[:12]
    aad = b"QCSpec-RWA-OM-v1"
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, payload_bytes, aad)
    return {
        "algorithm": "AES-256-GCM",
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "aad": aad.decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "cipher_hash": hashlib.sha256(ciphertext).hexdigest(),
    }


def _run_anchor_rounds(rounds: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    total = max(0, min(int(rounds or 0), 5))
    if total <= 0:
        return runs
    worker = GitPegAnchorWorker()
    for _ in range(total):
        try:
            runs.append(worker.anchor_once())
        except Exception as exc:
            runs.append({"ok": False, "error": f"{exc.__class__.__name__}: {exc}"})
    return runs


def convert_to_finance_asset(
    *,
    sb: Any,
    project_uri: str,
    boq_group_id: str,
    project_name: str | None = None,
    bank_code: str = "",
    passphrase: str = "",
    run_anchor_rounds: int = 1,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    group_id = _to_text(boq_group_id).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")
    if not group_id:
        raise HTTPException(400, "boq_group_id is required")

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
        boq_item_uri = _extract_boq_item_uri(row)
        if not boq_item_uri.startswith("v://"):
            continue
        grouped.setdefault(boq_item_uri, []).append(row)

    underlying_assets: list[dict[str, Any]] = []
    quality_hashes: set[str] = set()
    gitpeg_anchors: set[str] = set()
    total_amount = 0.0
    total_quantity = 0.0

    for boq_item_uri, bucket in grouped.items():
        bucket.sort(key=lambda r: _to_text(r.get("created_at") or ""))
        genesis_rows = [row for row in bucket if _stage(row) == "INITIAL" or _to_text(row.get("proof_type") or "").strip().lower() == "zero_ledger"]
        genesis = genesis_rows[0] if genesis_rows else bucket[0]
        item_no = _extract_item_no(genesis, boq_item_uri)
        if not _in_group(item_no, group_id):
            continue

        gsd = _as_dict(genesis.get("state_data"))
        unit = _to_text(gsd.get("unit") or "").strip()
        unit_price = _to_float(gsd.get("unit_price"))
        if unit_price is None:
            unit_price = _to_float(_as_dict(gsd.get("genesis_proof")).get("unit_price"))

        settlement_rows = [
            row
            for row in bucket
            if _stage(row) == "SETTLEMENT"
            and _to_text(row.get("result") or "").strip().upper() == "PASS"
            and _has_tripartite_consensus(row)
        ]
        if not settlement_rows:
            continue

        settled_qty = 0.0
        settlement_ids: list[str] = []
        for row in settlement_rows:
            settled_qty += _extract_settled_quantity(row, fallback_design=None)
            pid = _to_text(row.get("proof_id") or "").strip()
            if pid:
                settlement_ids.append(pid)
            anchor = _to_text(row.get("gitpeg_anchor") or "").strip()
            if anchor:
                gitpeg_anchors.add(anchor)
        if settled_qty <= 0:
            continue

        amount = round(settled_qty * float(unit_price or 0.0), 2)
        total_quantity += settled_qty
        total_amount += amount

        lineage_snapshots: list[dict[str, Any]] = []
        for settlement_id in settlement_ids[-4:]:
            try:
                lineage = get_full_lineage(settlement_id, sb)
            except Exception:
                lineage = {}
            total_hash = _to_text(lineage.get("total_proof_hash") or "").strip()
            if total_hash:
                quality_hashes.add(total_hash)
            for node in _as_list(lineage.get("nodes")):
                if not isinstance(node, dict):
                    continue
                anchor = _to_text(node.get("gitpeg_anchor") or "").strip()
                if anchor:
                    gitpeg_anchors.add(anchor)
            lineage_snapshots.append(
                {
                    "settlement_proof_id": settlement_id,
                    "total_proof_hash": total_hash,
                    "norm_refs": _as_list(lineage.get("norm_refs")),
                    "evidence_hash_count": len(_as_list(lineage.get("evidence_hashes"))),
                    "consensus_signatures": _as_list(lineage.get("consensus_signatures")),
                }
            )

        underlying_assets.append(
            {
                "boq_item_uri": boq_item_uri,
                "item_no": item_no,
                "item_name": _to_text(gsd.get("item_name") or "").strip(),
                "unit": unit,
                "unit_price": unit_price,
                "settled_quantity": round(settled_qty, 6),
                "credit_amount": amount,
                "settlement_proof_ids": settlement_ids,
                "lineage_snapshots": lineage_snapshots,
            }
        )

    if not underlying_assets:
        raise HTTPException(404, "no eligible settled assets found for boq_group_id")

    certificate_payload = {
        "format": "QCSpec-RWA-Asset-Certificate",
        "version": "1.0",
        "generated_at": _utc_iso(),
        "project_uri": normalized_project_uri,
        "project_name": _to_text(project_name or "").strip(),
        "boq_group_id": group_id,
        "bank_code": _to_text(bank_code).strip(),
        "summary": {
            "asset_count": len(underlying_assets),
            "total_quantity": round(total_quantity, 6),
            "total_credit_amount": round(total_amount, 2),
        },
        "underlying_assets": underlying_assets,
        "quality_hashes": sorted(quality_hashes),
        "gitpeg_anchors": sorted(gitpeg_anchors),
    }
    cert_hash = _canonical_hash(certificate_payload)
    canonical = json.dumps(certificate_payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    encrypted = _encrypt_aes256(canonical, passphrase or cert_hash)

    engine = ProofUTXOEngine(sb)
    rwa_proof_id = f"GP-RWA-{cert_hash[:16].upper()}"
    rwa_state = {
        "artifact_type": "rwa_finance_asset",
        "boq_group_id": group_id,
        "certificate_hash": cert_hash,
        "asset_count": len(underlying_assets),
        "total_credit_amount": round(total_amount, 2),
        "quality_hashes": sorted(quality_hashes),
        "generated_at": _utc_iso(),
    }
    try:
        rwa_row = engine.create(
            proof_id=rwa_proof_id,
            owner_uri="v://executor/system/",
            project_uri=normalized_project_uri,
            project_id=None,
            proof_type="archive",
            result="PASS",
            state_data=rwa_state,
            conditions=[],
            parent_proof_id=None,
            norm_uri="v://norm/CoordOS/RWA/1.0#finance_asset",
            segment_uri=f"{normalized_project_uri.rstrip('/')}/rwa/{group_id}",
            signer_uri="v://executor/system/",
            signer_role="DOCPEG",
        )
    except Exception:
        rwa_row = engine.create(
            proof_id=f"{rwa_proof_id}-{datetime.now(timezone.utc).strftime('%H%M%S')}",
            owner_uri="v://executor/system/",
            project_uri=normalized_project_uri,
            project_id=None,
            proof_type="archive",
            result="PASS",
            state_data=rwa_state,
            conditions=[],
            parent_proof_id=None,
            norm_uri="v://norm/CoordOS/RWA/1.0#finance_asset",
            segment_uri=f"{normalized_project_uri.rstrip('/')}/rwa/{group_id}",
            signer_uri="v://executor/system/",
            signer_role="DOCPEG",
        )

    anchor_runs = _run_anchor_rounds(run_anchor_rounds)
    refreshed = engine.get_by_id(_to_text(rwa_row.get("proof_id") or "").strip()) or rwa_row
    final_anchor = _to_text(refreshed.get("gitpeg_anchor") or "").strip()

    blob = json.dumps(
        {
            "meta": {
                "format": certificate_payload["format"],
                "version": certificate_payload["version"],
                "project_uri": normalized_project_uri,
                "boq_group_id": group_id,
                "certificate_hash": cert_hash,
                "rwa_proof_id": _to_text(refreshed.get("proof_id") or "").strip(),
                "rwa_gitpeg_anchor": final_anchor,
            },
            "encryption": encrypted,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "boq_group_id": group_id,
        "rwa_proof_id": _to_text(refreshed.get("proof_id") or "").strip(),
        "certificate_hash": cert_hash,
        "rwa_gitpeg_anchor": final_anchor,
        "anchor_runs": anchor_runs,
        "blob_bytes": blob,
        "filename": f"RWA-ASSET-{group_id}-{cert_hash[:12]}.qcrwa",
    }


def export_sovereign_om_bundle(
    *,
    sb: Any,
    project_uri: str,
    project_name: str | None = None,
    om_owner_uri: str = "v://operator/om/default",
    passphrase: str = "",
    run_anchor_rounds: int = 1,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri).strip()
    if not normalized_project_uri:
        raise HTTPException(400, "project_uri is required")

    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", normalized_project_uri)
            .order("created_at", desc=False)
            .limit(30000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise HTTPException(502, f"failed to load proof_utxo: {exc}") from exc

    if not rows:
        raise HTTPException(404, "no proof_utxo rows found for project")

    source_docfinal = None
    for row in reversed(rows):
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        if _to_text(sd.get("artifact_type") or "").strip() == "docfinal_master_dsp":
            source_docfinal = row
            break
    if source_docfinal is None:
        source_docfinal = rows[-1] if rows else None

    identity_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        signer = _to_text(row.get("signer_uri") or "").strip()
        if not signer:
            signer = _to_text(_as_dict(row.get("state_data")).get("inspector") or "").strip()
        if not signer:
            continue
        if signer in identity_map:
            continue
        digest = hashlib.sha256(signer.encode("utf-8")).hexdigest()[:12]
        identity_map[signer] = {
            "construction_identity": signer,
            "om_identity": f"{_to_text(om_owner_uri).rstrip('/')}/identity/{digest}",
            "mapping_hash": hashlib.sha256(f"{signer}|{om_owner_uri}".encode("utf-8")).hexdigest(),
        }

    lightweight_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        lightweight_rows.append(
            {
                "proof_id": _to_text(row.get("proof_id") or "").strip(),
                "parent_proof_id": _to_text(row.get("parent_proof_id") or "").strip(),
                "proof_hash": _to_text(row.get("proof_hash") or "").strip(),
                "proof_type": _to_text(row.get("proof_type") or "").strip(),
                "result": _to_text(row.get("result") or "").strip().upper(),
                "stage": _stage(row),
                "boq_item_uri": _extract_boq_item_uri(row),
                "signer_uri": _to_text(row.get("signer_uri") or "").strip(),
                "norm_uri": _to_text(row.get("norm_uri") or "").strip(),
                "gitpeg_anchor": _to_text(row.get("gitpeg_anchor") or "").strip(),
                "created_at": _to_text(row.get("created_at") or "").strip(),
                "spec_uri": _to_text(sd.get("spec_uri") or "").strip(),
                "deviation_percent": _as_dict(sd.get("norm_evaluation")).get("deviation_percent"),
            }
        )

    om_root_uri = f"{normalized_project_uri.rstrip('/')}/om/root"
    handover_payload = {
        "format": "QCSpec-Sovereign-OM-Handover",
        "version": "1.0",
        "generated_at": _utc_iso(),
        "project_uri": normalized_project_uri,
        "project_name": _to_text(project_name or "").strip(),
        "construction_owner_uri": _to_text(rows[-1].get("owner_uri") or "").strip(),
        "om_owner_uri": _to_text(om_owner_uri).strip(),
        "om_root_uri": om_root_uri,
        "source_docfinal_proof_id": _to_text((source_docfinal or {}).get("proof_id") or "").strip(),
        "identity_mapping": list(identity_map.values()),
        "construction_chain": lightweight_rows,
        "mount_protocol": {
            "next_event_api": "/v1/proof/om/event/register",
            "rule": "new O&M event proof MUST set parent_proof_id=om_root_proof_id",
            "segment_uri_prefix": om_root_uri,
        },
    }

    payload_json = json.dumps(handover_payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    payload_hash = hashlib.sha256(payload_json).hexdigest()
    encrypted = _encrypt_aes256(payload_json, passphrase or payload_hash)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handover.json", json.dumps(handover_payload, ensure_ascii=False, indent=2, default=str))
        zf.writestr("handover.encrypted.json", json.dumps(encrypted, ensure_ascii=False, sort_keys=True, default=str))
        zf.writestr(
            "README.txt",
            (
                "QCSpec Sovereign O&M Bundle\n"
                f"Project URI: {normalized_project_uri}\n"
                f"OM Root URI: {om_root_uri}\n"
                f"Payload Hash: {payload_hash}\n"
                "Use /v1/proof/om/event/register to append O&M events.\n"
            ),
        )
    zip_bytes = zip_buf.getvalue()

    engine = ProofUTXOEngine(sb)
    om_proof_id = f"GP-OM-{payload_hash[:16].upper()}"
    parent_id = _to_text((source_docfinal or {}).get("proof_id") or "").strip() or None
    om_state = {
        "artifact_type": "sovereign_om_handover",
        "payload_hash": payload_hash,
        "om_root_uri": om_root_uri,
        "source_docfinal_proof_id": _to_text((source_docfinal or {}).get("proof_id") or "").strip(),
        "identity_map_count": len(identity_map),
        "generated_at": _utc_iso(),
    }
    try:
        om_row = engine.create(
            proof_id=om_proof_id,
            owner_uri=_to_text(om_owner_uri).strip() or "v://operator/om/default",
            project_uri=normalized_project_uri,
            project_id=None,
            proof_type="archive",
            result="PASS",
            state_data=om_state,
            conditions=[],
            parent_proof_id=parent_id,
            norm_uri="v://norm/CoordOS/OM/1.0#handover",
            segment_uri=om_root_uri,
            signer_uri=_to_text(om_owner_uri).strip() or "v://operator/om/default",
            signer_role="OM",
        )
    except Exception:
        om_row = engine.create(
            proof_id=f"{om_proof_id}-{datetime.now(timezone.utc).strftime('%H%M%S')}",
            owner_uri=_to_text(om_owner_uri).strip() or "v://operator/om/default",
            project_uri=normalized_project_uri,
            project_id=None,
            proof_type="archive",
            result="PASS",
            state_data=om_state,
            conditions=[],
            parent_proof_id=parent_id,
            norm_uri="v://norm/CoordOS/OM/1.0#handover",
            segment_uri=om_root_uri,
            signer_uri=_to_text(om_owner_uri).strip() or "v://operator/om/default",
            signer_role="OM",
        )

    anchor_runs = _run_anchor_rounds(run_anchor_rounds)
    refreshed = engine.get_by_id(_to_text(om_row.get("proof_id") or "").strip()) or om_row

    return {
        "ok": True,
        "project_uri": normalized_project_uri,
        "om_root_uri": om_root_uri,
        "om_root_proof_id": _to_text(refreshed.get("proof_id") or "").strip(),
        "om_gitpeg_anchor": _to_text(refreshed.get("gitpeg_anchor") or "").strip(),
        "payload_hash": payload_hash,
        "anchor_runs": anchor_runs,
        "zip_bytes": zip_bytes,
        "filename": f"OM-HANDOVER-{payload_hash[:12]}.zip",
    }


def register_om_event(
    *,
    sb: Any,
    om_root_proof_id: str,
    title: str,
    event_type: str = "maintenance",
    payload: dict[str, Any] | None = None,
    executor_uri: str = "v://operator/om/default",
) -> dict[str, Any]:
    root_id = _to_text(om_root_proof_id).strip()
    if not root_id:
        raise HTTPException(400, "om_root_proof_id is required")
    engine = ProofUTXOEngine(sb)
    root_row = engine.get_by_id(root_id)
    if not root_row:
        raise HTTPException(404, "om_root_proof_id not found")

    root_sd = _as_dict(root_row.get("state_data"))
    om_root_uri = _to_text(root_sd.get("om_root_uri") or root_row.get("segment_uri") or "").strip()
    if not om_root_uri:
        raise HTTPException(409, "om_root_uri missing in root proof")

    event_payload = {
        "title": _to_text(title).strip() or "OM Event",
        "event_type": _to_text(event_type).strip().lower() or "maintenance",
        "payload": _as_dict(payload),
        "recorded_at": _utc_iso(),
        "executor_uri": _to_text(executor_uri).strip(),
    }
    event_hash = _canonical_hash({"root": root_id, "event": event_payload})
    event_id = f"GP-OMEV-{event_hash[:16].upper()}"
    row = engine.create(
        proof_id=event_id,
        owner_uri=_to_text(executor_uri).strip() or "v://operator/om/default",
        project_uri=_to_text(root_row.get("project_uri") or "").strip(),
        project_id=root_row.get("project_id"),
        proof_type="archive",
        result="PASS",
        state_data={
            "artifact_type": "sovereign_om_event",
            "om_root_proof_id": root_id,
            "om_root_uri": om_root_uri,
            "event_hash": event_hash,
            **event_payload,
        },
        conditions=[],
        parent_proof_id=root_id,
        norm_uri="v://norm/CoordOS/OM/1.0#event",
        segment_uri=f"{om_root_uri.rstrip('/')}/event/{event_hash[:12]}",
        signer_uri=_to_text(executor_uri).strip() or "v://operator/om/default",
        signer_role="OM",
    )
    return {
        "ok": True,
        "om_root_proof_id": root_id,
        "event_proof_id": _to_text(row.get("proof_id") or "").strip(),
        "event_hash": event_hash,
    }


def generate_norm_evolution_report(
    *,
    sb: Any,
    project_uris: list[str] | None = None,
    min_samples: int = 5,
    near_threshold_ratio: float = 0.9,
    anonymize: bool = True,
    create_proof: bool = True,
) -> dict[str, Any]:
    selected_projects = [x.strip() for x in (_as_list(project_uris) if project_uris else []) if _to_text(x).strip()]

    try:
        if selected_projects:
            rows = (
                sb.table("proof_utxo")
                .select("*")
                .in_("project_uri", selected_projects)
                .order("created_at", desc=False)
                .limit(50000)
                .execute()
                .data
                or []
            )
        else:
            rows = (
                sb.table("proof_utxo")
                .select("*")
                .order("created_at", desc=False)
                .limit(50000)
                .execute()
                .data
                or []
            )
    except Exception as exc:
        raise HTTPException(502, f"failed to load proof_utxo for norm report: {exc}") from exc

    min_n = max(3, min(int(min_samples or 0), 100))
    near_ratio = max(0.5, min(float(near_threshold_ratio or 0.0), 0.995))
    salt = hashlib.sha256(f"norm-evo|{_utc_iso()}".encode("utf-8")).hexdigest()[:16]

    grouped: dict[str, dict[str, Any]] = {}
    total_samples = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        norm_eval = _as_dict(sd.get("norm_evaluation"))
        norm_uri = _to_text(row.get("norm_uri") or sd.get("spec_uri") or "").strip()
        if not norm_uri:
            continue
        threshold_pack = _as_dict(norm_eval.get("threshold"))
        context_key = _to_text(
            threshold_pack.get("context_key")
            or sd.get("component_type")
            or sd.get("structure_type")
            or "default"
        ).strip()
        key = f"{norm_uri}|{context_key}"
        g = grouped.setdefault(
            key,
            {
                "norm_uri": norm_uri,
                "context_key": context_key,
                "samples": [],
                "project_refs": set(),
                "pass_count": 0,
                "fail_count": 0,
                "critical_candidates": [],
            },
        )
        deviation = _to_float(norm_eval.get("deviation_percent"))
        if deviation is None:
            deviation = _to_float(sd.get("deviation_percent"))
        if deviation is None:
            continue
        critical = _to_float(norm_eval.get("critical_threshold"))
        if critical is None:
            raw_threshold = threshold_pack.get("threshold")
            if isinstance(raw_threshold, list) and len(raw_threshold) >= 2:
                lo = _to_float(raw_threshold[0])
                hi = _to_float(raw_threshold[1])
                if lo is not None and hi is not None:
                    critical = max(abs(lo), abs(hi))
        if critical is None:
            critical = _to_float(_as_dict(sd.get("spec_rule")).get("tolerance"))
        critical = abs(float(critical if critical is not None else 2.0))

        result = _to_text(row.get("result") or norm_eval.get("result") or "").strip().upper()
        g["samples"].append(abs(float(deviation)))
        g["critical_candidates"].append(critical)
        g["project_refs"].add(_to_text(row.get("project_uri") or "").strip())
        if result == "FAIL":
            g["fail_count"] += 1
        elif result == "PASS":
            g["pass_count"] += 1
        total_samples += 1

    findings: list[dict[str, Any]] = []
    for _, g in grouped.items():
        samples = list(g["samples"])
        if len(samples) < min_n:
            continue
        critical = max(0.001, float(sum(g["critical_candidates"]) / max(1, len(g["critical_candidates"]))))
        mean_abs = sum(samples) / len(samples)
        variance = sum((x - mean_abs) ** 2 for x in samples) / len(samples)
        near_threshold = critical * near_ratio
        near_count = sum(1 for x in samples if x >= near_threshold)
        near_share = near_count / len(samples)
        fail_share = float(g["fail_count"]) / max(1, len(samples))

        suggestion = "keep_threshold"
        rationale = "distribution_stable"
        if near_share >= 0.6 and fail_share >= 0.2:
            suggestion = "consider_relaxing_threshold"
            rationale = "high_near_critical_and_high_fail_share"
        elif near_share <= 0.1 and fail_share <= 0.02 and mean_abs <= critical * 0.35:
            suggestion = "consider_tightening_threshold"
            rationale = "persistently_low_deviation_and_low_fail_share"
        elif near_share >= 0.55 and fail_share < 0.1:
            suggestion = "add_intermediate_warning_band"
            rationale = "many_borderline_passes"

        project_refs_raw = sorted([x for x in g["project_refs"] if x])
        if anonymize:
            project_refs = [
                f"proj_{hashlib.sha256(f'{salt}|{ref}'.encode('utf-8')).hexdigest()[:10]}"
                for ref in project_refs_raw
            ]
        else:
            project_refs = project_refs_raw

        findings.append(
            {
                "norm_uri": g["norm_uri"],
                "context_key": g["context_key"],
                "sample_count": len(samples),
                "project_count": len(project_refs_raw),
                "project_refs": project_refs,
                "mean_abs_deviation": round(mean_abs, 6),
                "variance": round(variance, 6),
                "critical_threshold": round(critical, 6),
                "near_threshold": round(near_threshold, 6),
                "near_share": round(near_share, 6),
                "pass_share": round(float(g["pass_count"]) / max(1, len(samples)), 6),
                "fail_share": round(fail_share, 6),
                "suggestion": suggestion,
                "rationale": rationale,
            }
        )

    findings.sort(key=lambda x: (-int(x["sample_count"]), -float(x["near_share"]), -float(x["fail_share"])))

    report_payload = {
        "format": "QCSpec-Norm-Evolution-Report",
        "version": "1.0",
        "generated_at": _utc_iso(),
        "anonymize": anonymize,
        "privacy_method": "salted_hash_project_ref" if anonymize else "raw_project_ref",
        "k_anonymity_min_samples": min_n,
        "near_threshold_ratio": near_ratio,
        "total_samples": total_samples,
        "finding_count": len(findings),
        "findings": findings,
    }
    report_hash = _canonical_hash(report_payload)

    proof_row: dict[str, Any] | None = None
    if create_proof:
        engine = ProofUTXOEngine(sb)
        proof_id = f"GP-NORMEVO-{report_hash[:16].upper()}"
        state = {
            "artifact_type": "norm_evolution_report",
            "report_hash": report_hash,
            "finding_count": len(findings),
            "total_samples": total_samples,
            "generated_at": _utc_iso(),
            "anonymize": anonymize,
        }
        try:
            proof_row = engine.create(
                proof_id=proof_id,
                owner_uri="v://executor/system/",
                project_uri="v://meta/norm-evolution/",
                project_id=None,
                proof_type="archive",
                result="PASS",
                state_data=state,
                conditions=[],
                parent_proof_id=None,
                norm_uri="v://norm/CoordOS/NormEvolution/1.0#report",
                segment_uri="v://meta/norm-evolution/report",
                signer_uri="v://executor/system/",
                signer_role="AI",
            )
        except Exception:
            proof_row = engine.create(
                proof_id=f"{proof_id}-{datetime.now(timezone.utc).strftime('%H%M%S')}",
                owner_uri="v://executor/system/",
                project_uri="v://meta/norm-evolution/",
                project_id=None,
                proof_type="archive",
                result="PASS",
                state_data=state,
                conditions=[],
                parent_proof_id=None,
                norm_uri="v://norm/CoordOS/NormEvolution/1.0#report",
                segment_uri="v://meta/norm-evolution/report",
                signer_uri="v://executor/system/",
                signer_role="AI",
            )

    return {
        "ok": True,
        "report_hash": report_hash,
        "proof_id": _to_text((proof_row or {}).get("proof_id") or "").strip(),
        "report": report_payload,
    }
