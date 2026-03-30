"""
Data Sovereignty Package (DSP) archive builder.
services/api/archive_service.py
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import io
import json
import mimetypes
import re
from typing import Any
from urllib import request as urlrequest
import zipfile

from services.api.archive_pdf_utils import pdf_report_bytes as _pdf_report_bytes
from services.api.archive_snapshot_utils import (
    offline_snapshot_html as _offline_snapshot_html,
    pdf_html_template as _pdf_html_template,
)


SOVEREIGN_BLOCK_HEIGHT = 8847001


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _safe_file_name(name: str, fallback: str) -> str:
    text = _to_text(name).strip() or fallback
    text = re.sub(r"[^\w.\-]+", "_", text, flags=re.ASCII)
    return text[:180] or fallback


def _clean_no_qmark(value: Any, fallback: str = "-") -> str:
    text = _to_text(value).strip()
    if not text:
        return fallback
    text = text.replace("???", "").replace("??", "")
    text = text.replace("?", "")
    text = text.strip()
    return text or fallback


def _result_cn_from_summary(summary: dict[str, Any]) -> str:
    token = _to_text(summary.get("result") or "").strip().upper()
    raw_cn = _to_text(summary.get("result_cn") or "").strip()
    if token == "PASS":
        return "合格"
    if token == "FAIL":
        return "不合格"
    if "不合格" in raw_cn or "未合格" in raw_cn:
        return "不合格"
    if "合格" in raw_cn and "不" not in raw_cn and "未" not in raw_cn:
        return "合格"
    if raw_cn:
        return _clean_no_qmark(raw_cn, fallback="待判定")
    return "待判定"


def _signer_from_payload(sovereignty: dict[str, Any], person: dict[str, Any]) -> str:
    # Mandatory mapping preference: sovereignty.signed_by
    primary = _to_text(sovereignty.get("signed_by")).strip()
    if primary:
        return _clean_no_qmark(primary, fallback="未知执行体")
    fallback = _to_text(person.get("name")).strip()
    return _clean_no_qmark(fallback, fallback="未知执行体")


def _first_rule_spec_excerpt(verify_detail: dict[str, Any]) -> str:
    qcgate = verify_detail.get("qcgate") if isinstance(verify_detail.get("qcgate"), dict) else {}
    rules = qcgate.get("rules") if isinstance(qcgate.get("rules"), list) else []
    if rules and isinstance(rules[0], dict):
        text = _to_text(rules[0].get("spec_excerpt")).strip()
        if text:
            return _clean_no_qmark(text, fallback="无可用规范摘要")
    return ""


def _spec_snapshot_bundle(verify_detail: dict[str, Any]) -> dict[str, Any]:
    summary = verify_detail.get("summary") if isinstance(verify_detail.get("summary"), dict) else {}
    timeline = verify_detail.get("timeline") if isinstance(verify_detail.get("timeline"), list) else []
    qcgate = verify_detail.get("qcgate") if isinstance(verify_detail.get("qcgate"), dict) else {}

    specs: list[dict[str, str]] = []
    seen: set[str] = set()

    def push(uri: Any, excerpt: Any):
        u = _to_text(uri).strip()
        e = _clean_no_qmark(excerpt, fallback="")
        key = f"{u}|{e}"
        if not u and not e:
            return
        if key in seen:
            return
        seen.add(key)
        specs.append({"spec_uri": u, "snapshot_text": e})

    push(summary.get("spec_uri"), _first_rule_spec_excerpt(verify_detail) or summary.get("spec_snapshot"))
    for node in timeline:
        if isinstance(node, dict):
            push(node.get("spec_uri"), node.get("spec_excerpt"))
    for rule in qcgate.get("rules") if isinstance(qcgate.get("rules"), list) else []:
        if isinstance(rule, dict):
            push(rule.get("spec_uri"), rule.get("spec_excerpt"))

    primary_text = _first_rule_spec_excerpt(verify_detail) or _to_text(summary.get("spec_snapshot"))
    primary_text = _clean_no_qmark(primary_text, fallback="无可用规范摘要")
    return {
        "primary_spec_uri": _to_text(summary.get("spec_uri")),
        "primary_snapshot_text": primary_text,
        "spec_snapshots": specs,
    }


def _collect_spatiotemporal_anchors(evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        anchor_hash = _to_text(item.get("spatiotemporal_anchor_hash") or "").strip()
        geo = item.get("geo_location") if isinstance(item.get("geo_location"), dict) else {}
        ts = item.get("server_timestamp_proof") if isinstance(item.get("server_timestamp_proof"), dict) else {}
        if not anchor_hash and not geo and not ts:
            continue
        key = anchor_hash or hashlib.sha256(
            json.dumps(
                {
                    "proof_id": _to_text(item.get("proof_id") or ""),
                    "geo": geo,
                    "ts": ts,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        anchors.append(
            {
                "proof_id": _to_text(item.get("proof_id") or "").strip(),
                "evidence_id": _to_text(item.get("id") or "").strip(),
                "spatiotemporal_anchor_hash": anchor_hash,
                "geo_location": geo,
                "server_timestamp_proof": ts,
                "captured_at": _to_text(item.get("time") or "").strip(),
            }
        )
    return anchors


def _fetch_binary(url: str, timeout: float = 10.0) -> bytes | None:
    target = _to_text(url).strip()
    if not target or not (target.startswith("http://") or target.startswith("https://")):
        return None
    req = urlrequest.Request(
        target,
        method="GET",
        headers={"User-Agent": "QCSpec-DSP/1.0"},
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None




def create_dsp_package(
    *,
    proof_id: str,
    verify_detail: dict[str, Any],
    chain_fingerprints: list[dict[str, Any]],
    signer_certificate: dict[str, str],
) -> bytes:
    summary = verify_detail.get("summary") if isinstance(verify_detail.get("summary"), dict) else {}
    sovereignty = verify_detail.get("sovereignty") if isinstance(verify_detail.get("sovereignty"), dict) else {}
    person = verify_detail.get("person") if isinstance(verify_detail.get("person"), dict) else {}
    evidence = verify_detail.get("evidence") if isinstance(verify_detail.get("evidence"), list) else []
    evidence_manifest: list[dict[str, Any]] = []
    evidence_files: list[tuple[str, bytes]] = []
    for idx, item in enumerate(evidence):
        if not isinstance(item, dict):
            continue
        url = _to_text(item.get("url")).strip()
        file_name = _safe_file_name(_to_text(item.get("file_name")), f"evidence_{idx + 1}.bin")
        blob = _fetch_binary(url)
        if blob is None:
            evidence_manifest.append(
                {
                    "index": idx + 1,
                    "file_name": file_name,
                    "source_url": url,
                    "status": "unavailable",
                    "reason": "download_failed_or_non_http_url",
                    "evidence_hash": _to_text(item.get("evidence_hash")),
                }
            )
            continue
        ext = ""
        guessed = mimetypes.guess_extension(_to_text(item.get("content_type")))
        if guessed:
            ext = guessed
        if "." not in file_name and ext:
            file_name = f"{file_name}{ext}"
        evidence_manifest.append(
            {
                "index": idx + 1,
                "file_name": file_name,
                "source_url": url,
                "status": "ok",
                "downloaded_sha256": hashlib.sha256(blob).hexdigest(),
                "size": len(blob),
                "evidence_hash": _to_text(item.get("evidence_hash")) or hashlib.sha256(blob).hexdigest(),
                "proof_id": _to_text(item.get("proof_id")),
            }
        )
        evidence_files.append((f"evidence/{file_name}", blob))
    spatiotemporal_anchors = _collect_spatiotemporal_anchors(evidence)
    spatiotemporal_anchor_payload = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "proof_id": _to_text(verify_detail.get("proof_id") or proof_id),
        "anchor_count": len(spatiotemporal_anchors),
        "anchors": spatiotemporal_anchors,
    }
    spatiotemporal_anchor_payload["anchors_hash"] = hashlib.sha256(
        json.dumps(spatiotemporal_anchor_payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    result_cn = _result_cn_from_summary(summary)
    signed_by = _signer_from_payload(sovereignty, person)
    signed_at = _clean_no_qmark(_to_text(sovereignty.get("signed_at") or person.get("time")), fallback="-")
    spec_bundle = _spec_snapshot_bundle(verify_detail)
    spec_snapshot = _clean_no_qmark(spec_bundle.get("primary_snapshot_text"), fallback="无可用规范摘要")
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    matches = bool((verify_detail.get("hash_verification") or {}).get("matches"))
    trust_label = "鍙俊鏉ユ簮" if matches else "鐤戜技绡℃敼"
    evidence_count = len(evidence_manifest) if evidence_manifest else len(evidence)

    report_lines = [
        f"QCSpec Data Sovereignty Report [{trust_label}]",
        f"Proof ID: {_to_text(verify_detail.get('proof_id') or proof_id)}",
        f"Proof Hash: {_to_text(sovereignty.get('proof_hash') or '-')}",
        f"Business Result (CN): {_clean_no_qmark(result_cn, fallback='待判定')}",
        f"Signer: {signed_by}",
        f"Signed At: {signed_at}",
        f"Archive At: {generated_at}",
        f"Spec URI: {_to_text(summary.get('spec_uri') or '-')}",
        f"Spec Snapshot: {spec_snapshot}",
        f"GitPeg Anchor: {_to_text(sovereignty.get('gitpeg_anchor') or '-')}",
        f"Block Height: {SOVEREIGN_BLOCK_HEIGHT}",
        f"Evidence Count: {evidence_count}",
        "Issued by verify.qcspec.com",
    ]
    pdf_bytes = _pdf_report_bytes(
        report_lines,
        watermark=f"{trust_label} | block {SOVEREIGN_BLOCK_HEIGHT}",
        trust_ok=matches,
    )

    verify_detail_aligned = json.loads(json.dumps(verify_detail, ensure_ascii=False, default=str))
    if not isinstance(verify_detail_aligned.get("summary"), dict):
        verify_detail_aligned["summary"] = {}
    if not isinstance(verify_detail_aligned.get("sovereignty"), dict):
        verify_detail_aligned["sovereignty"] = {}
    if not isinstance(verify_detail_aligned.get("qcgate"), dict):
        verify_detail_aligned["qcgate"] = {}
    if not isinstance(verify_detail_aligned.get("qcgate").get("rules"), list):
        verify_detail_aligned["qcgate"]["rules"] = []
    if not verify_detail_aligned["qcgate"]["rules"]:
        verify_detail_aligned["qcgate"]["rules"].append({})
    if not isinstance(verify_detail_aligned["qcgate"]["rules"][0], dict):
        verify_detail_aligned["qcgate"]["rules"][0] = {}

    verify_detail_aligned["summary"]["result_cn"] = _clean_no_qmark(result_cn, fallback="待判定")
    verify_detail_aligned["summary"]["spec_snapshot"] = spec_snapshot
    verify_detail_aligned["sovereignty"]["signed_by"] = signed_by
    verify_detail_aligned["sovereignty"]["signed_at"] = signed_at
    verify_detail_aligned["qcgate"]["rules"][0]["spec_excerpt"] = spec_snapshot

    dsp_json = {
        "proof_id": _to_text(verify_detail.get("proof_id") or proof_id),
        "generated_at": generated_at,
        "verify_detail": verify_detail_aligned,
        "proof_chain": chain_fingerprints,
        "spec_snapshot_bundle": spec_bundle,
        "signer_certificate": signer_certificate,
        "sovereign_watermark": {
            "label": trust_label,
            "block_height": SOVEREIGN_BLOCK_HEIGHT,
            "hash_matches": matches,
        },
        "evidence": {
            "count": evidence_count,
            "items": evidence_manifest,
        },
        "spatiotemporal_anchor": spatiotemporal_anchor_payload,
    }
    dsp_json["package_hash"] = hashlib.sha256(
        json.dumps(dsp_json, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    verify_snapshot_html = _offline_snapshot_html(dsp_json)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("report.pdf", pdf_bytes)
        # Backward-compatible alias for legacy consumers.
        zf.writestr("verify_snapshot.pdf", pdf_bytes)
        payload_json = json.dumps(dsp_json, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        zf.writestr("provenance_chain.json", payload_json)
        # Compatibility alias for old consumers.
        zf.writestr("proof_chain.json", payload_json)
        zf.writestr("index.html", verify_snapshot_html)
        zf.writestr("verify_snapshot.html", verify_snapshot_html)
        # Backward-compatible alias for legacy consumers.
        zf.writestr("verify_offline.html", verify_snapshot_html)
        zf.writestr("templates/report_template.html", _pdf_html_template())
        zf.writestr("signer_certificate.pem", _to_text(signer_certificate.get("public_key_pem")))
        zf.writestr(
            "evidence/manifest.json",
            json.dumps(evidence_manifest, ensure_ascii=False, sort_keys=True, indent=2, default=str),
        )
        zf.writestr(
            "spatiotemporal_anchor.json",
            json.dumps(spatiotemporal_anchor_payload, ensure_ascii=False, sort_keys=True, indent=2, default=str),
        )
        for path, blob in evidence_files:
            zf.writestr(path, blob)
        zf.writestr(
            "README.txt",
            "DSP includes report.pdf, provenance_chain.json, verify_snapshot.html, signer_certificate.pem, evidence/.\n",
        )

    buf.seek(0)
    return buf.read()
