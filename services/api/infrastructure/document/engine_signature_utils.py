"""
Signature helpers for docx_engine.
services/api/docx_engine_signature_utils.py
"""

from __future__ import annotations

import base64
import io
import json
import os

import httpx
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from services.api.infrastructure.document.engine_utils import bool_env, is_uri_like, to_text


def resolve_signature_url(executor_id: str) -> str:
    eid = to_text(executor_id).strip()
    if not eid:
        return ""

    raw_map = to_text(os.getenv("QCSPEC_SIGNATURE_URL_MAP") or "").strip()
    if raw_map:
        try:
            parsed = json.loads(raw_map)
            if isinstance(parsed, dict):
                mapped = to_text(parsed.get(eid) or parsed.get(eid.lower()) or "").strip()
                if mapped and is_uri_like(mapped):
                    return mapped
        except Exception:
            pass

    tpl = to_text(os.getenv("QCSPEC_SIGNATURE_URL_TEMPLATE") or "").strip()
    if tpl:
        try:
            url = tpl.format(executor_id=eid)
            if is_uri_like(url):
                return url
        except Exception:
            pass

    base = to_text(os.getenv("QCSPEC_SIGNATURE_BASE_URL") or "").strip().rstrip("/")
    if base and is_uri_like(base):
        return f"{base}/{eid}.png"
    return ""


def decrypt_signature_blob(blob: bytes) -> bytes:
    key = to_text(os.getenv("QCSPEC_SIGNATURE_XOR_KEY") or "").encode("utf-8")
    if not key:
        return blob
    out = bytearray(len(blob))
    for idx, b in enumerate(blob):
        out[idx] = b ^ key[idx % len(key)]
    return bytes(out)


def fallback_signature_stamp(tpl: DocxTemplate, size_mm: int = 18) -> InlineImage | str:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return "-"

    px = 180
    img = Image.new("RGBA", (px, px), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    border = (148, 163, 184, 255)
    fill = (241, 245, 249, 230)
    draw.rounded_rectangle([(2, 2), (px - 3, px - 3)], radius=14, fill=fill, outline=border, width=3)
    draw.ellipse([(26, 26), (px - 27, px - 27)], outline=border, width=3)
    text_color = (100, 116, 139, 255)
    draw.text((46, 74), "NO SIGN", fill=text_color)
    draw.text((40, 102), "UNAVAILABLE", fill=text_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return InlineImage(tpl, buf, width=Mm(size_mm))


def fetch_signature_bytes(url: str) -> bytes | None:
    if not is_uri_like(url):
        return None
    headers: dict[str, str] = {}
    token = to_text(os.getenv("QCSPEC_SIGNATURE_AUTH_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=6.0, follow_redirects=True) as client:
            res = client.get(url, headers=headers)
            if res.status_code >= 400:
                return None
            content_type = to_text(res.headers.get("content-type") or "").lower()
            if content_type.startswith("image/"):
                return res.content
            payload = res.json()
            if isinstance(payload, dict):
                nested_url = to_text(payload.get("url") or payload.get("image_url") or "").strip()
                if nested_url and nested_url != url:
                    return fetch_signature_bytes(nested_url)
                b64 = to_text(
                    payload.get("signature_b64")
                    or payload.get("image_b64")
                    or payload.get("encrypted_b64")
                    or ""
                ).strip()
                if b64:
                    raw = base64.b64decode(b64)
                    return decrypt_signature_blob(raw)
    except Exception:
        return None
    return None


def insert_signature(
    executor_id: str,
    *,
    tpl: DocxTemplate | None = None,
    size_mm: int = 18,
) -> tuple[InlineImage | bytes | str, str]:
    eid = to_text(executor_id).strip()
    if not eid:
        return "-", "none"
    url = resolve_signature_url(eid)
    if not url:
        if tpl is not None and bool_env("QCSPEC_SIGNATURE_FALLBACK_STAMP", default=True):
            fallback = fallback_signature_stamp(tpl, size_mm=size_mm)
            if fallback != "-":
                return fallback, "fallback"
        return "-", "none"
    blob = fetch_signature_bytes(url)
    if not blob:
        if tpl is not None and bool_env("QCSPEC_SIGNATURE_FALLBACK_STAMP", default=True):
            fallback = fallback_signature_stamp(tpl, size_mm=size_mm)
            if fallback != "-":
                return fallback, "fallback"
        return "-", "none"
    if tpl is None:
        return blob, "loaded"
    buf = io.BytesIO(blob)
    buf.seek(0)
    return InlineImage(tpl, buf, width=Mm(size_mm)), "loaded"
