"""
Verify evidence aggregation helpers.
services/api/verify_evidence_service.py
"""

from __future__ import annotations

from typing import Any, Callable

from supabase import Client

from services.api.verify_service import list_photos_for_inspection


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    return str(value)


def _extract_evidence_hash(raw: dict[str, Any]) -> str:
    for key in ("evidence_hash", "sha256", "file_sha256", "hash"):
        text = _to_text(raw.get(key) if isinstance(raw, dict) else "").strip().lower()
        if text:
            return text
    return ""


def _extract_media_type(raw: dict[str, Any]) -> str:
    content_type = _to_text(raw.get("content_type") if isinstance(raw, dict) else "").strip().lower()
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    file_name = _to_text(raw.get("file_name") if isinstance(raw, dict) else "").strip().lower()
    if file_name.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic")):
        return "image"
    if file_name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")):
        return "video"
    return "file"


def build_evidence_items(
    *,
    sb: Client,
    latest_row: dict[str, Any],
    chain_rows: list[dict[str, Any]],
    display_time: Callable[[Any], str],
) -> list[dict[str, Any]]:
    inspection_ids: set[str] = set()
    expected_hashes: set[str] = set()
    expected_proofs: set[str] = set()
    inline_items: list[dict[str, Any]] = []

    for row in chain_rows:
        if not isinstance(row, dict):
            continue
        sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
        insp_id = _to_text(sd.get("inspection_id")).strip()
        if insp_id:
            inspection_ids.add(insp_id)
        for h in sd.get("evidence_hashes") if isinstance(sd.get("evidence_hashes"), list) else []:
            text = _to_text(h).strip().lower()
            if text:
                expected_hashes.add(text)
        for p in sd.get("evidence_proof_ids") if isinstance(sd.get("evidence_proof_ids"), list) else []:
            text = _to_text(p).strip()
            if text:
                expected_proofs.add(text)

        inline = sd.get("evidence") if isinstance(sd.get("evidence"), list) else []
        for item in inline:
            if not isinstance(item, dict):
                continue
            ehash = _extract_evidence_hash(item)
            pid = _to_text(item.get("proof_id")).strip()
            if ehash:
                expected_hashes.add(ehash)
            if pid:
                expected_proofs.add(pid)
            inline_items.append(
                {
                    "id": _to_text(item.get("id") or ""),
                    "file_name": _to_text(item.get("file_name") or item.get("name") or "-"),
                    "url": _to_text(item.get("url") or item.get("storage_url") or ""),
                    "media_type": _extract_media_type(item),
                    "evidence_hash": ehash,
                    "proof_id": pid,
                    "proof_hash": _to_text(item.get("proof_hash") or "").lower(),
                    "size": item.get("size") or item.get("file_size"),
                    "time": display_time(item.get("taken_at") or item.get("created_at") or ""),
                    "source": "proof_state",
                }
            )

    latest_sd = latest_row.get("state_data") if isinstance(latest_row.get("state_data"), dict) else {}
    latest_insp = _to_text(latest_sd.get("inspection_id")).strip()
    if latest_insp:
        inspection_ids.add(latest_insp)

    db_items: list[dict[str, Any]] = []
    for inspection_id in inspection_ids:
        rows = list_photos_for_inspection(sb, inspection_id, limit=100)
        for photo in rows:
            ehash = _extract_evidence_hash(photo)
            proof_id = _to_text(photo.get("proof_id")).strip()
            proof_hash = _to_text(photo.get("proof_hash")).strip().lower()
            if ehash:
                expected_hashes.add(ehash)
            if proof_id:
                expected_proofs.add(proof_id)
            url = _to_text(photo.get("storage_url") or "")
            if not url:
                path = _to_text(photo.get("storage_path") or "")
                if path:
                    url = path
            db_items.append(
                {
                    "id": _to_text(photo.get("id") or ""),
                    "file_name": _to_text(photo.get("file_name") or "-"),
                    "url": url,
                    "media_type": _extract_media_type(photo),
                    "evidence_hash": ehash,
                    "proof_id": proof_id,
                    "proof_hash": proof_hash,
                    "size": photo.get("file_size"),
                    "time": display_time(photo.get("taken_at") or photo.get("created_at")),
                    "source": "photos_table",
                }
            )

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in db_items + inline_items:
        key = "|".join(
            [
                _to_text(item.get("id") or ""),
                _to_text(item.get("proof_id") or ""),
                _to_text(item.get("evidence_hash") or ""),
                _to_text(item.get("url") or ""),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        eh = _to_text(item.get("evidence_hash") or "").lower()
        pid = _to_text(item.get("proof_id") or "")
        ph = _to_text(item.get("proof_hash") or "").lower()
        hash_matched = bool(
            (eh and eh in expected_hashes)
            or (pid and pid in expected_proofs)
            or (ph and ph in expected_hashes)
        )
        merged.append(
            {
                **item,
                "hash_matched": hash_matched,
                "hash_match_text": "文件哈希已匹配" if hash_matched else "文件哈希待核验",
            }
        )
    return merged
