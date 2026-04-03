"""Consensus signature and biometric helpers for TripRole execution."""

from __future__ import annotations

import re
from typing import Any

from services.api.domain.execution.triprole_common import (
    as_dict,
    as_list,
    normalize_role,
    sha256_json,
    to_bool,
    to_float,
    to_text,
    utc_iso,
)

CONSENSUS_REQUIRED_ROLES = ("contractor", "supervisor", "owner")


def _looks_like_sig_hash(value: Any) -> bool:
    text = to_text(value).strip().lower()
    return bool(re.fullmatch(r"[a-f0-9]{64}", text))


def _normalize_consensus_signatures(raw: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return normalized
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = normalize_role(item.get("role"))
        did = to_text(item.get("did") or "").strip()
        sig = to_text(item.get("signature_hash") or item.get("signature") or "").strip().lower()
        if not role:
            continue
        normalized.append(
            {
                "role": role,
                "did": did,
                "signature_hash": sig,
                "signed_at": to_text(item.get("signed_at") or utc_iso()).strip(),
            }
        )
    return normalized


def _validate_consensus_signatures(
    signatures: list[dict[str, Any]],
    *,
    required_roles: tuple[str, ...] = CONSENSUS_REQUIRED_ROLES,
) -> dict[str, Any]:
    by_role: dict[str, dict[str, Any]] = {}
    for sig in signatures:
        role = normalize_role(sig.get("role"))
        if not role:
            continue
        by_role[role] = sig

    missing = [r for r in required_roles if r not in by_role]
    invalid: list[str] = []
    for role, sig in by_role.items():
        did = to_text(sig.get("did") or "").strip()
        sig_hash = to_text(sig.get("signature_hash") or "").strip()
        if not did.startswith("did:"):
            invalid.append(f"{role}:did_invalid")
        if not _looks_like_sig_hash(sig_hash):
            invalid.append(f"{role}:signature_hash_invalid")

    ok = (not missing) and (not invalid)
    consensus_payload = {
        "required_roles": list(required_roles),
        "signatures": [by_role[r] for r in required_roles if r in by_role],
    }
    return {
        "ok": ok,
        "missing_roles": missing,
        "invalid": invalid,
        "consensus_hash": sha256_json(consensus_payload) if ok else "",
        "consensus_payload": consensus_payload,
    }


def _normalize_signer_metadata(raw: Any) -> dict[str, Any]:
    payload = as_dict(raw)
    signers_raw = payload.get("signers")
    if not isinstance(signers_raw, list):
        if isinstance(raw, list):
            signers_raw = raw
        elif payload:
            signers_raw = [payload]
        else:
            signers_raw = []

    signers: list[dict[str, Any]] = []
    for item in signers_raw:
        if not isinstance(item, dict):
            continue
        did = to_text(item.get("did") or item.get("signer_did") or "").strip()
        role = normalize_role(item.get("role") or item.get("signer_role"))
        biometric_passed = to_bool(
            item.get("biometric_passed")
            if "biometric_passed" in item
            else (
                item.get("verified")
                if "verified" in item
                else (
                    item.get("liveness_passed")
                    if "liveness_passed" in item
                    else item.get("fingerprint_passed")
                )
            )
        )
        verified_at = to_text(item.get("verified_at") or item.get("timestamp") or item.get("checked_at") or "").strip()
        signers.append(
            {
                "did": did,
                "role": role,
                "biometric_passed": bool(biometric_passed),
                "verified_at": verified_at,
                "method": to_text(item.get("method") or item.get("biometric_type") or "").strip().lower(),
                "provider": to_text(item.get("provider") or "").strip(),
                "confidence": to_float(item.get("confidence")),
                "device_id": to_text(item.get("device_id") or "").strip(),
            }
        )

    normalized = {
        "signers": signers,
        "captured_at": to_text(payload.get("captured_at") or "").strip(),
        "metadata_hash": sha256_json(signers),
    }
    return normalized


def _extract_consensus_values(raw: Any, payload: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []

    def _push(item: dict[str, Any], source: str) -> None:
        if not isinstance(item, dict):
            return
        role = normalize_role(item.get("role") or item.get("signer_role"))
        did = to_text(item.get("did") or item.get("signer_did") or "").strip()
        for key in ("measured_value", "value", "quantity", "amount", "measured", "reported_value"):
            val = to_float(item.get(key))
            if val is not None:
                values.append(
                    {
                        "role": role,
                        "did": did,
                        "value": float(val),
                        "source": source,
                        "field": key,
                    }
                )
                return

    consensus_values = payload.get("consensus_values")
    if isinstance(consensus_values, list):
        for item in consensus_values:
            if isinstance(item, dict):
                _push(item, "payload.consensus_values")

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                _push(item, "signer_metadata")
    elif isinstance(raw, dict):
        signers = raw.get("signers")
        if isinstance(signers, list):
            for item in signers:
                if isinstance(item, dict):
                    _push(item, "signer_metadata.signers")
        else:
            _push(raw, "signer_metadata")

    return values


def detect_consensus_deviation(
    *,
    signer_metadata_raw: Any,
    payload: dict[str, Any],
    input_sd: dict[str, Any],
) -> dict[str, Any]:
    values = _extract_consensus_values(signer_metadata_raw, payload)
    if len(values) < 2:
        return {"ok": True, "conflict": False, "reason": "insufficient_values", "values": values}

    raw_allowed = (
        payload.get("allowed_deviation")
        or payload.get("tolerance")
        or payload.get("deviation_limit")
        or as_dict(input_sd.get("norm_evaluation")).get("tolerance")
    )
    allowed_abs = to_float(raw_allowed)
    allowed_pct = to_float(
        payload.get("allowed_deviation_percent")
        or payload.get("deviation_percent")
        or payload.get("tolerance_percent")
    )

    series = [v.get("value") for v in values if isinstance(v.get("value"), (int, float))]
    if not series:
        return {"ok": True, "conflict": False, "reason": "no_numeric_values", "values": values}

    min_v = min(series)
    max_v = max(series)
    diff = max_v - min_v
    avg = (max_v + min_v) / 2 if (max_v + min_v) != 0 else max_v
    pct = (diff / avg * 100.0) if avg else 0.0

    conflict = False
    if allowed_abs is not None and diff > float(allowed_abs):
        conflict = True
    if allowed_pct is not None and pct > float(allowed_pct):
        conflict = True

    if allowed_abs is None and allowed_pct is None:
        # Default: allow small numeric jitter up to 0.5% if no threshold is configured.
        conflict = pct > 0.5 if avg else diff > 0

    return {
        "ok": True,
        "conflict": conflict,
        "min_value": min_v,
        "max_value": max_v,
        "deviation": diff,
        "deviation_percent": round(pct, 4),
        "allowed_deviation": allowed_abs,
        "allowed_deviation_percent": allowed_pct,
        "values": values,
    }


def verify_biometric_status(
    *,
    signer_metadata: dict[str, Any] | list[dict[str, Any]] | None,
    consensus_signatures: list[dict[str, Any]],
    required_roles: tuple[str, ...] = CONSENSUS_REQUIRED_ROLES,
) -> dict[str, Any]:
    normalized = _normalize_signer_metadata(signer_metadata or {})
    signers = as_list(normalized.get("signers"))
    by_did: dict[str, dict[str, Any]] = {}
    by_role: dict[str, dict[str, Any]] = {}
    for item in signers:
        if not isinstance(item, dict):
            continue
        did = to_text(item.get("did") or "").strip()
        role = normalize_role(item.get("role"))
        if did:
            by_did[did] = item
        if role and role not in by_role:
            by_role[role] = item

    required = [
        sig
        for sig in consensus_signatures
        if normalize_role(sig.get("role")) in required_roles
    ]
    missing: list[str] = []
    failed: list[str] = []
    passed: list[str] = []

    for sig in required:
        role = normalize_role(sig.get("role"))
        did = to_text(sig.get("did") or "").strip()
        ref = by_did.get(did) or by_role.get(role)
        tag = f"{role}:{did or '-'}"
        if not isinstance(ref, dict):
            missing.append(tag)
            continue
        if not to_bool(ref.get("biometric_passed")):
            failed.append(f"{tag}:biometric_failed")
            continue
        if not to_text(ref.get("verified_at") or "").strip():
            failed.append(f"{tag}:missing_timestamp")
            continue
        passed.append(tag)

    ok = (not missing) and (not failed)
    return {
        "ok": ok,
        "required_count": len(required),
        "verified_count": len(passed),
        "missing": missing,
        "failed": failed,
        "passed": passed,
        "metadata_hash": to_text(normalized.get("metadata_hash") or "").strip(),
        "signers": signers,
    }


__all__ = [
    "CONSENSUS_REQUIRED_ROLES",
    "_looks_like_sig_hash",
    "_normalize_consensus_signatures",
    "_validate_consensus_signatures",
    "_normalize_signer_metadata",
    "_extract_consensus_values",
    "detect_consensus_deviation",
    "verify_biometric_status",
]
