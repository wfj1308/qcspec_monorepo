"""Scan-confirm helpers for TripRole execution."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    decode_base64url_json,
    normalize_role,
    parse_iso_epoch_ms,
    to_text,
    utc_iso,
)

SCAN_CONFIRM_MAX_TTL_DAYS = 120


def scan_confirm_secret() -> str:
    return to_text(
        os.getenv("QCSPEC_SCAN_CONFIRM_SECRET")
        or os.getenv("SCAN_CONFIRM_SECRET")
        or "qcspec-scan-confirm-v1",
    ).strip()


def canonical_scan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "proof_id": to_text(payload.get("proof_id") or "").strip(),
        "signer_did": to_text(payload.get("signer_did") or "").strip(),
        "signer_role": normalize_role(payload.get("signer_role")) or to_text(payload.get("signer_role") or "").strip(),
        "issued_at": to_text(payload.get("issued_at") or "").strip(),
        "expires_at": to_text(payload.get("expires_at") or "").strip(),
        "nonce": to_text(payload.get("nonce") or "").strip(),
    }


def scan_payload_signature(payload: dict[str, Any]) -> str:
    canonical = canonical_scan_payload(payload)
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    secret = scan_confirm_secret()
    return hashlib.sha256(f"{raw}|{secret}".encode("utf-8")).hexdigest()


def validate_scan_confirm_payload(raw_payload: Any) -> dict[str, Any]:
    payload = decode_base64url_json(raw_payload)
    if not payload:
        raise HTTPException(400, "invalid scan qr payload")
    canonical = canonical_scan_payload(payload)
    if not canonical["proof_id"]:
        raise HTTPException(400, "scan payload missing proof_id")
    if not canonical["signer_did"].startswith("did:"):
        raise HTTPException(400, "scan payload signer_did invalid")
    if not canonical["issued_at"] or not canonical["expires_at"]:
        raise HTTPException(400, "scan payload missing issued_at/expires_at")

    issued_ms = parse_iso_epoch_ms(canonical["issued_at"])
    expires_ms = parse_iso_epoch_ms(canonical["expires_at"])
    now_ms = parse_iso_epoch_ms(utc_iso())
    if issued_ms is None or expires_ms is None or now_ms is None:
        raise HTTPException(400, "scan payload timestamp invalid")
    if expires_ms <= issued_ms:
        raise HTTPException(400, "scan payload expires_at must be greater than issued_at")
    if expires_ms - issued_ms > SCAN_CONFIRM_MAX_TTL_DAYS * 24 * 3600 * 1000:
        raise HTTPException(400, "scan payload ttl too long")
    if now_ms > expires_ms:
        raise HTTPException(409, "scan payload expired")

    provided_sig = to_text(payload.get("token_hash") or payload.get("token_sig") or "").strip().lower()
    expected_sig = scan_payload_signature(payload)
    if not provided_sig or provided_sig != expected_sig:
        raise HTTPException(409, "scan payload signature mismatch")
    return {**canonical, "token_hash": expected_sig}


__all__ = [
    "SCAN_CONFIRM_MAX_TTL_DAYS",
    "scan_confirm_secret",
    "canonical_scan_payload",
    "scan_payload_signature",
    "validate_scan_confirm_payload",
]
