"""
DID credential gate helpers for TripRole admission control.
"""

from __future__ import annotations

from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import re
from typing import Any


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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    text = _to_text(value).strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _item_code_from_boq_uri(boq_item_uri: str) -> str:
    uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not uri:
        return ""
    return uri.split("/")[-1]


def _normalize_required(raw: Any) -> str:
    token = _to_text(raw).strip().lower()
    token = re.sub(r"[^a-z0-9_.:\-]+", "_", token)
    return token[:80]


def resolve_required_credential(*, action: str, boq_item_uri: str, payload: Any = None) -> str:
    p = _as_dict(payload)
    explicit = _normalize_required(
        p.get("required_credential")
        or p.get("required_role")
        or p.get("required_vc")
    )
    if explicit:
        return explicit

    act = _to_text(action).strip().lower()
    item_code = _item_code_from_boq_uri(boq_item_uri)
    chapter = item_code.split("-")[0] if item_code else ""

    if chapter == "403":
        if act in {"quality.check", "measure.record", "variation.record", "variation.delta.apply", "settlement.confirm"}:
            return "rebar_special_operator"
    return ""


def _vc_role_tokens(vc: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for key in ("credential_role", "role", "credential_type", "type", "name", "code"):
        val = _normalize_required(vc.get(key))
        if val:
            tokens.add(val)
    for arr_key in ("roles", "credential_roles", "tags", "abilities", "skills"):
        for item in _as_list(vc.get(arr_key)):
            val = _normalize_required(item)
            if val:
                tokens.add(val)
    return tokens


def _vc_scope_match(vc: dict[str, Any], *, project_uri: str, boq_item_uri: str) -> bool:
    scope = _as_dict(vc.get("scope"))
    allowed_project = _to_text(
        scope.get("project_uri")
        or vc.get("scope_project_uri")
        or ""
    ).strip()
    if allowed_project and allowed_project != project_uri:
        return False

    patterns = []
    patterns.extend(_as_list(scope.get("boq_patterns")))
    patterns.extend(_as_list(vc.get("scope_boq_patterns")))
    one_pattern = _to_text(scope.get("boq_pattern") or vc.get("scope_boq_pattern") or "").strip()
    if one_pattern:
        patterns.append(one_pattern)
    if not patterns:
        return True
    return any(fnmatch.fnmatch(boq_item_uri, _to_text(p).strip()) for p in patterns if _to_text(p).strip())


def _vc_time_match(vc: dict[str, Any], *, now_dt: datetime) -> bool:
    valid_from = _parse_dt(
        vc.get("valid_from")
        or vc.get("issued_at")
        or vc.get("not_before")
    )
    valid_to = _parse_dt(
        vc.get("valid_to")
        or vc.get("expires_at")
        or vc.get("not_after")
    )
    if valid_from and now_dt < valid_from:
        return False
    if valid_to and now_dt > valid_to:
        return False
    status = _to_text(vc.get("status") or "active").strip().lower()
    if status and status not in {"active", "valid", "ok"}:
        return False
    return True


def _vc_holder_match(vc: dict[str, Any], *, user_did: str) -> bool:
    holder = _to_text(
        vc.get("holder_did")
        or vc.get("subject_did")
        or vc.get("did")
        or vc.get("holder")
    ).strip()
    if holder and holder != user_did:
        return False
    return True


def _vc_match(
    vc: dict[str, Any],
    *,
    user_did: str,
    required_credential: str,
    project_uri: str,
    boq_item_uri: str,
    now_dt: datetime,
) -> bool:
    if not _vc_holder_match(vc, user_did=user_did):
        return False
    if not _vc_time_match(vc, now_dt=now_dt):
        return False
    if not _vc_scope_match(vc, project_uri=project_uri, boq_item_uri=boq_item_uri):
        return False
    if required_credential:
        tokens = _vc_role_tokens(vc)
        if required_credential not in tokens:
            return False
    return True


def _normalize_local_credential(row: dict[str, Any]) -> dict[str, Any]:
    vc = {
        "credential_id": _to_text(row.get("credential_id") or row.get("id") or "").strip(),
        "holder_did": _to_text(row.get("holder_did") or "").strip(),
        "credential_role": _to_text(row.get("credential_role") or "").strip(),
        "credential_type": _to_text(row.get("credential_type") or "").strip(),
        "status": _to_text(row.get("status") or "active").strip().lower(),
        "issuer_did": _to_text(row.get("issuer_did") or "").strip(),
        "valid_from": _to_text(row.get("valid_from") or "").strip(),
        "valid_to": _to_text(row.get("valid_to") or "").strip(),
        "scope_project_uri": _to_text(row.get("scope_project_uri") or "").strip(),
        "scope_boq_patterns": _as_list(row.get("scope_boq_patterns")),
    }
    return vc


def _load_registry_credentials(*, sb: Any, user_did: str) -> list[dict[str, Any]]:
    did = _to_text(user_did).strip()
    if not did:
        return []
    try:
        rows = (
            sb.table("proof_did_credential")
            .select("*")
            .eq("holder_did", did)
            .limit(500)
            .execute()
            .data
            or []
        )
    except Exception:
        return []
    return [_normalize_local_credential(x) for x in rows if isinstance(x, dict)]


def verify_credential(
    *,
    sb: Any,
    user_did: str,
    required_credential: str,
    project_uri: str,
    boq_item_uri: str,
    payload_credentials: Any = None,
) -> dict[str, Any]:
    did = _to_text(user_did).strip()
    req = _normalize_required(required_credential)
    now_dt = _utc_now()
    now_iso = now_dt.isoformat()

    if not req:
        return {
            "ok": True,
            "reason": "no_required_credential",
            "user_did": did,
            "required_credential": req,
            "checked_at": now_iso,
            "source": "bypass",
            "matched_credential": {},
            "did_gate_hash": hashlib.sha256(
                json.dumps(
                    {
                        "ok": True,
                        "reason": "no_required_credential",
                        "user_did": did,
                        "required_credential": req,
                        "checked_at": now_iso,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                ).encode("utf-8")
            ).hexdigest(),
        }

    if not did.startswith("did:"):
        return {
            "ok": False,
            "reason": "user_did_invalid",
            "user_did": did,
            "required_credential": req,
            "checked_at": now_iso,
            "source": "",
        }

    registry = _load_registry_credentials(sb=sb, user_did=did)
    payload_vc = [_as_dict(x) for x in _as_list(payload_credentials)]

    matched: dict[str, Any] = {}
    source = ""

    for vc in registry:
        if _vc_match(
            vc,
            user_did=did,
            required_credential=req,
            project_uri=project_uri,
            boq_item_uri=boq_item_uri,
            now_dt=now_dt,
        ):
            matched = vc
            source = "registry"
            break

    if not matched:
        for vc in payload_vc:
            if _vc_match(
                vc,
                user_did=did,
                required_credential=req,
                project_uri=project_uri,
                boq_item_uri=boq_item_uri,
                now_dt=now_dt,
            ):
                matched = vc
                source = "payload_vc"
                break

    ok = bool(matched)
    gate_payload = {
        "user_did": did,
        "required_credential": req,
        "project_uri": _to_text(project_uri).strip(),
        "boq_item_uri": _to_text(boq_item_uri).strip(),
        "source": source,
        "credential_id": _to_text(matched.get("credential_id") or "").strip() if matched else "",
        "checked_at": now_iso,
        "ok": ok,
    }
    gate_hash = hashlib.sha256(
        json.dumps(gate_payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return {
        "ok": ok,
        "reason": "ok" if ok else "credential_not_found_or_invalid",
        "user_did": did,
        "required_credential": req,
        "source": source,
        "matched_credential": matched,
        "checked_at": now_iso,
        "did_gate_hash": gate_hash,
    }
