"""SM2 signature adapter helpers for SMU signing flows."""

from __future__ import annotations

import re
from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)

_HEX_RE = re.compile(r"^[a-fA-F0-9]+$")


def _looks_hex(value: str, *, min_len: int = 1) -> bool:
    text = _to_text(value).strip()
    return len(text) >= min_len and bool(_HEX_RE.fullmatch(text))


def _normalize_sm2_entries(raw: Any) -> dict[str, dict[str, Any]]:
    by_role: dict[str, dict[str, Any]] = {}
    for item in _as_list(raw):
        row = _as_dict(item)
        role = _to_text(row.get("role") or "").strip().lower()
        if not role:
            continue
        by_role[role] = row
    return by_role


def verify_sm2_signature(
    *,
    signature_hex: str,
    public_key_hex: str,
    message: str,
    verifier: Callable[[str, str, str], bool] | None = None,
) -> dict[str, Any]:
    sig = _to_text(signature_hex).strip()
    pub = _to_text(public_key_hex).strip()
    msg = _to_text(message).strip()
    if not (_looks_hex(sig, min_len=32) and _looks_hex(pub, min_len=32) and msg):
        return {
            "ok": False,
            "mode": "material_invalid",
            "reason": "signature/public_key/message invalid",
        }

    if verifier is not None:
        try:
            return {"ok": bool(verifier(sig, pub, msg)), "mode": "custom_verifier", "reason": ""}
        except Exception as exc:
            return {"ok": False, "mode": "custom_verifier_error", "reason": str(exc)}

    try:
        from gmssl import sm2 as _gmssl_sm2  # type: ignore

        crypt = _gmssl_sm2.CryptSM2(public_key=pub, private_key="")
        ok = False
        try:
            ok = bool(crypt.verify(sig, msg.encode("utf-8").hex()))
        except Exception:
            ok = bool(crypt.verify(sig, msg.encode("utf-8")))
        return {"ok": ok, "mode": "gmssl", "reason": ""}
    except Exception:
        # Adapter remains available even when gmssl is absent.
        return {"ok": False, "mode": "format_only", "reason": "gmssl unavailable"}


def attach_sm2_signatures(
    *,
    signatures: list[dict[str, Any]],
    sm2_entries: Any,
    input_proof_id: str,
    now_iso: str,
    strict: bool = False,
    verifier: Callable[[str, str, str], bool] | None = None,
) -> list[dict[str, Any]]:
    normalized = _normalize_sm2_entries(sm2_entries)
    out: list[dict[str, Any]] = []
    missing_roles: list[str] = []

    for item in signatures:
        sig = dict(item)
        role = _to_text(sig.get("role") or "").strip().lower()
        did = _to_text(sig.get("did") or "").strip()
        message = _to_text(sig.get("signing_message") or f"{input_proof_id}|{did}|{role}|{now_iso}").strip()
        row = _as_dict(normalized.get(role))
        if not row:
            sig["signature_scheme"] = "HASH_SHA256"
            sig["sm2_verified"] = False
            sig["sm2_verify_mode"] = "not_provided"
            out.append(sig)
            missing_roles.append(role)
            continue

        row_did = _to_text(row.get("did") or "").strip()
        if row_did and did and row_did != did:
            if strict:
                raise HTTPException(409, f"sm2_signature_did_mismatch:{role}")
            sig["signature_scheme"] = "HASH_SHA256"
            sig["sm2_verified"] = False
            sig["sm2_verify_mode"] = "did_mismatch"
            out.append(sig)
            continue

        signature_hex = _to_text(row.get("signature_hex") or row.get("signature") or "").strip().lower()
        public_key_hex = _to_text(row.get("public_key_hex") or "").strip().lower()
        verify_result = verify_sm2_signature(
            signature_hex=signature_hex,
            public_key_hex=public_key_hex,
            message=message,
            verifier=verifier,
        )
        if strict and not bool(verify_result.get("ok")):
            raise HTTPException(409, f"sm2_signature_invalid:{role}:{_to_text(verify_result.get('mode'))}")

        sig["signature_scheme"] = "SM2_WITH_HASH_SHA256_FALLBACK"
        sig["sm2_signature_hex"] = signature_hex
        sig["sm2_public_key_hex"] = public_key_hex
        sig["sm2_verified"] = bool(verify_result.get("ok"))
        sig["sm2_verify_mode"] = _to_text(verify_result.get("mode") or "").strip()
        sig["sm2_verify_reason"] = _to_text(verify_result.get("reason") or "").strip()
        sig["signing_message"] = message
        out.append(sig)

    if strict and missing_roles:
        roles = ",".join(sorted(set(r for r in missing_roles if r)))
        raise HTTPException(409, f"sm2_signature_missing_roles:{roles}")
    return out


__all__ = [
    "attach_sm2_signatures",
    "verify_sm2_signature",
]

