"""
Mock Trip document generation endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
import base64
import hashlib
import io
import json
from math import asin, cos, radians, sin, sqrt
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
import qrcode

router = APIRouter()

_DOC_CACHE: dict[str, dict[str, Any]] = {}
_DOC_CACHE_LIMIT = 200


class NormRowInput(BaseModel):
    field: str = ""
    label: str = ""
    operator: str = "present"
    threshold: str = ""
    measured_value: Any = None
    unit: str = ""


class TripGenerateDocBody(BaseModel):
    project_uri: str
    boq_item_uri: str = ""
    smu_id: str = ""
    subitem_code: str = ""
    item_name: str = ""
    unit: str = ""
    executor_did: str = ""
    geo_location: dict[str, Any] = Field(default_factory=dict)
    anchor_location: dict[str, Any] = Field(default_factory=dict)
    norm_rows: list[NormRowInput] = Field(default_factory=list)
    measurements: dict[str, Any] = Field(default_factory=dict)
    evidence_hashes: list[str] = Field(default_factory=list)
    report_template: str = "3、桥施表.docx"
    verify_base_url: str = "https://verify.qcspec.com"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None


def _parse_range(threshold: str) -> tuple[float, float] | None:
    raw = str(threshold or "").strip().replace(" ", "")
    if "~" not in raw:
        return None
    left, right = raw.split("~", 1)
    a = _to_float(left)
    b = _to_float(right)
    if a is None or b is None:
        return None
    return (min(a, b), max(a, b))


def _eval_norm(operator: str, threshold: str, measured: Any) -> tuple[str, str]:
    op = str(operator or "").strip().lower()
    raw = str(threshold or "").strip()
    if op == "present":
        ok = str(measured or "").strip() != ""
        return ("pass" if ok else "fail", "required" if ok else "missing")

    value = _to_float(measured)
    if value is None:
        return ("fail", "invalid_number")

    if "±" in raw:
        lim = _to_float(raw.split("±", 1)[1])
        if lim is None:
            return ("fail", "invalid_threshold")
        ok = -abs(lim) <= value <= abs(lim)
        return ("pass" if ok else "fail", f"range_±{abs(lim)}")

    ranged = _parse_range(raw)
    if ranged is not None:
        ok = ranged[0] <= value <= ranged[1]
        return ("pass" if ok else "fail", f"range_{ranged[0]}~{ranged[1]}")

    target = _to_float(raw)
    if target is None:
        return ("fail", "invalid_threshold")
    if op == ">=":
        ok = value >= target
    elif op == "<=":
        ok = value <= target
    else:
        ok = value == target
    return ("pass" if ok else "fail", op or "==")


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # Great-circle distance in meters.
    r = 6371000.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2.0) ** 2
    c = 2.0 * asin(sqrt(max(0.0, min(1.0, a))))
    return r * c


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\n", " ")


def _build_pdf_bytes(lines: list[str]) -> bytes:
    content_lines = []
    y = 760
    for line in lines[:36]:
        content_lines.append(f"BT /F1 11 Tf 48 {y} Td ({_escape_pdf_text(line)}) Tj ET")
        y -= 18
    content = "\n".join(content_lines).encode("utf-8")
    header = b"%PDF-1.4\n"
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\n"
        b"endobj\n"
    )
    obj4 = b"4 0 obj\n<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream\nendobj\n"
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    objects = [obj1, obj2, obj3, obj4, obj5]
    offsets = [0]
    cursor = len(header)
    for obj in objects:
        offsets.append(cursor)
        cursor += len(obj)
    xref = [f"xref\n0 {len(objects) + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{cursor}\n%%EOF".encode("ascii")
    )
    return header + b"".join(objects) + b"".join(xref) + trailer


def _trim_cache() -> None:
    if len(_DOC_CACHE) <= _DOC_CACHE_LIMIT:
        return
    keys = sorted(
        _DOC_CACHE.keys(),
        key=lambda k: str((_DOC_CACHE.get(k) or {}).get("created_at") or ""),
    )
    overflow = len(keys) - _DOC_CACHE_LIMIT
    for key in keys[:overflow]:
        _DOC_CACHE.pop(key, None)


@router.post("/generate-doc")
async def generate_doc_trip(body: TripGenerateDocBody):
    norm_rows = body.norm_rows or []
    measured_map = body.measurements or {}
    norm_result_rows: list[dict[str, Any]] = []
    fail_count = 0
    for row in norm_rows:
        measured = row.measured_value
        if measured is None and row.field:
            measured = measured_map.get(row.field)
        status, reason = _eval_norm(row.operator, row.threshold, measured)
        if status != "pass":
            fail_count += 1
        norm_result_rows.append(
            {
                "field": row.field,
                "label": row.label or row.field,
                "operator": row.operator,
                "threshold": row.threshold,
                "measured_value": measured,
                "status": status,
                "reason": reason,
                "unit": row.unit,
            }
        )

    lat = _to_float((body.geo_location or {}).get("lat"))
    lng = _to_float((body.geo_location or {}).get("lng"))
    anchor_lat = _to_float((body.anchor_location or {}).get("lat"))
    anchor_lng = _to_float((body.anchor_location or {}).get("lng"))
    offset_m: float | None = None
    if lat is not None and lng is not None and anchor_lat is not None and anchor_lng is not None:
        offset_m = _haversine_m(lat, lng, anchor_lat, anchor_lng)

    risk_score = 100.0
    risk_score -= min(45.0, float(fail_count) * 12.0)
    if offset_m is not None:
        if offset_m > 120:
            risk_score -= 38.0
        elif offset_m > 60:
            risk_score -= 22.0
        elif offset_m > 30:
            risk_score -= 10.0
    if not body.evidence_hashes:
        risk_score -= 8.0
    risk_score = max(0.0, min(100.0, risk_score))
    risk_level = "green"
    if risk_score < 60 or (offset_m is not None and offset_m > 120):
        risk_level = "red"
    elif risk_score < 80:
        risk_level = "amber"

    now = datetime.now(timezone.utc).isoformat()
    trip_id = f"TRIP-{uuid4().hex[:12].upper()}"
    doc_id = uuid4().hex[:16]
    payload_for_hash = {
        "trip_action": "document.create_trip",
        "project_uri": body.project_uri,
        "boq_item_uri": body.boq_item_uri,
        "smu_id": body.smu_id,
        "subitem_code": body.subitem_code,
        "item_name": body.item_name,
        "executor_did": body.executor_did,
        "geo_location": body.geo_location,
        "anchor_location": body.anchor_location,
        "norm_rows": norm_result_rows,
        "measurements": measured_map,
        "evidence_hashes": body.evidence_hashes,
        "risk_score": round(risk_score, 2),
        "generated_at": now,
    }
    total_proof_hash = hashlib.sha256(
        json.dumps(payload_for_hash, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    verify_root = str(body.verify_base_url or "https://verify.qcspec.com").rstrip("/")
    verify_uri = f"{verify_root}/proof/{doc_id}?hash={total_proof_hash[:24]}"

    qr_img = qrcode.make(verify_uri)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_base64 = base64.b64encode(qr_buf.getvalue()).decode("ascii")

    pdf_lines = [
        "CoordOS DocPeg Mock Report",
        f"Trip Action: document.create_trip",
        f"Project URI: {body.project_uri}",
        f"BOQ Item URI: {body.boq_item_uri or '-'}",
        f"SMU ID: {body.smu_id or '-'}",
        f"Subitem: {body.subitem_code or '-'}",
        f"Item Name: {body.item_name or '-'}",
        f"Executor DID: {body.executor_did or '-'}",
        f"Risk Score: {risk_score:.2f} ({risk_level})",
        f"GPS Offset(m): {offset_m:.2f}" if offset_m is not None else "GPS Offset(m): -",
        f"Norm Pass: {len(norm_rows) - fail_count}/{len(norm_rows)}",
        f"Total Proof Hash: {total_proof_hash}",
        f"Generated At: {now}",
    ]
    if norm_result_rows:
        pdf_lines.append("---- NormPeg Details ----")
        for idx, row in enumerate(norm_result_rows[:20], start=1):
            pdf_lines.append(
                f"{idx}. {row['label']} | {row['measured_value']} | {row['operator']} {row['threshold']} | {row['status']}"
            )
    pdf_bytes = _build_pdf_bytes(pdf_lines)
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    _DOC_CACHE[doc_id] = {
        "created_at": now,
        "pdf_bytes": pdf_bytes,
        "trip_id": trip_id,
        "total_proof_hash": total_proof_hash,
    }
    _trim_cache()

    return {
        "ok": True,
        "trip_action": "document.create_trip",
        "trip_id": trip_id,
        "doc_id": doc_id,
        "total_proof_hash": total_proof_hash,
        "risk_audit": {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "gps_offset_m": round(offset_m, 3) if offset_m is not None else None,
            "is_red": risk_level == "red",
        },
        "normpeg": {
            "passed": int(len(norm_rows) - fail_count),
            "total": int(len(norm_rows)),
            "failed": int(fail_count),
            "details": norm_result_rows,
        },
        "docpeg": {
            "template_name": body.report_template or "3、桥施表.docx",
            "pdf_preview_url": f"/api/trip/preview/{doc_id}",
            "pdf_preview_b64": pdf_b64,
            "qr_png_base64": f"data:image/png;base64,{qr_base64}",
            "verify_uri": verify_uri,
        },
        "generated_at": now,
    }


@router.get("/preview/{doc_id}")
async def get_doc_preview(doc_id: str):
    key = str(doc_id or "").strip()
    if not key:
        raise HTTPException(400, "doc_id is required")
    hit = _DOC_CACHE.get(key)
    if not hit:
        raise HTTPException(404, "doc not found")
    pdf_bytes = hit.get("pdf_bytes")
    if not isinstance(pdf_bytes, (bytes, bytearray)):
        raise HTTPException(404, "doc bytes missing")
    return Response(content=bytes(pdf_bytes), media_type="application/pdf")

