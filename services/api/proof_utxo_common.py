"""
Common utilities for proof UTXO operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import uuid

PROOF_TYPES = {
    "inspection",
    "lab",
    "photo",
    "approval",
    "payment",
    "archive",
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
    t = str(value or "").strip().upper()
    return t if t in PROOF_RESULTS else "PENDING"


def normalize_type(value: str) -> str:
    t = str(value or "").strip().lower()
    return t if t in PROOF_TYPES else "inspection"
