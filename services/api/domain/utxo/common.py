"""Common utilities for proof UTXO operations."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

PROOF_TYPES = {
    "inspection",
    "lab",
    "photo",
    "approval",
    "payment",
    "payment_instruction",
    "archive",
    "remediation",
    "node",
    "document",
    "ordosign",
    "zero_ledger",
}

PROOF_RESULTS = {"PASS", "FAIL", "OBSERVE", "PENDING", "CANCELLED"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_tx_id() -> str:
    return f"TX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def ordosign(target_id: str, signer_uri: str) -> str:
    payload = f"{target_id}:{signer_uri}:{utc_now_iso()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def normalize_result(value: str) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in PROOF_RESULTS else "PENDING"


def normalize_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in PROOF_TYPES else "inspection"


__all__ = [
    "PROOF_TYPES",
    "PROOF_RESULTS",
    "utc_now_iso",
    "gen_tx_id",
    "ordosign",
    "normalize_result",
    "normalize_type",
]
