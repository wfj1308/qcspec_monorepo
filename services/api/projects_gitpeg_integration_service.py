"""
Project GitPeg integration helpers.
services/api/projects_gitpeg_integration_service.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import re
from typing import Any, Callable, Optional

from fastapi import HTTPException
from supabase import Client

WEBHOOK_TS_TOLERANCE_S = 300
WEBHOOK_EVENT_WINDOW_S = 24 * 60 * 60
_WEBHOOK_EVENT_CACHE: dict[str, datetime] = {}


def _extract_project_id_from_external_reference(external_reference: str) -> Optional[str]:
    ref = str(external_reference or "").strip()
    if not ref:
        return None
    m = re.match(r"^qcspec-proj-(.+)$", ref)
    if not m:
        return None
    value = m.group(1).strip()
    return value or None


def _find_value_recursive(obj: Any, keys: set[str]) -> Any:
    def norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    normalized_keys = {norm(key) for key in keys}
    queue: list[Any] = [obj]
    while queue:
        cur = queue.pop(0)
        if isinstance(cur, dict):
            for key, value in cur.items():
                if norm(str(key)) in normalized_keys and value not in (None, "", []):
                    return value
                if isinstance(value, (dict, list)):
                    queue.append(value)
        elif isinstance(cur, list):
            queue.extend(cur)
    return None


def _extract_gitpeg_callback_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": _find_value_recursive(payload, {"session_id", "sessionId"}),
        "registration_id": _find_value_recursive(payload, {"registration_id", "registrationId"}),
        "code": _find_value_recursive(payload, {"code", "auth_code", "authorization_code"}),
        "access_token": _find_value_recursive(payload, {"access_token", "accessToken"}),
        "partner_code": _find_value_recursive(payload, {"partner_code", "partnerCode"}),
        "external_reference": _find_value_recursive(payload, {"external_reference", "externalReference"}),
        "node_uri": _find_value_recursive(payload, {"node_uri", "nodeUri"}),
        "shell_uri": _find_value_recursive(payload, {"shell_uri", "shellUri"}),
        "proof_hash": _find_value_recursive(payload, {"proof_hash", "proofHash"}),
        "industry_code": _find_value_recursive(payload, {"industry_code", "industryCode"}),
        "industry_profile_id": _find_value_recursive(payload, {"industry_profile_id", "industryProfileId"}),
    }


def _normalize_sig(sig: str) -> str:
    text = str(sig or "").strip()
    if text.lower().startswith("sha256="):
        text = text.split("=", 1)[1].strip()
    return text.lower()


def _parse_header_timestamp(value: str) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _parse_db_ts(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _event_seen_in_cache(event_id: str, now: datetime, *, window_s: int = WEBHOOK_EVENT_WINDOW_S) -> bool:
    cutoff = now - timedelta(seconds=window_s)
    stale = [key for key, ts in _WEBHOOK_EVENT_CACHE.items() if ts < cutoff]
    for key in stale:
        _WEBHOOK_EVENT_CACHE.pop(key, None)
    prev = _WEBHOOK_EVENT_CACHE.get(event_id)
    if prev and prev >= cutoff:
        return True
    _WEBHOOK_EVENT_CACHE[event_id] = now
    return False


def _verify_webhook_headers_and_signature(
    request: Any,
    *,
    raw_body: bytes,
    cfg: Optional[dict[str, Any]] = None,
) -> tuple[bool, str, Optional[str], Optional[str]]:
    signature = _normalize_sig(request.headers.get("x-gitpeg-signature", ""))
    timestamp_header = str(request.headers.get("x-gitpeg-timestamp", "")).strip()
    event_id = str(request.headers.get("x-gitpeg-event-id", "")).strip()

    if not signature:
        return False, "missing_signature", None, None
    if not timestamp_header:
        return False, "missing_timestamp", None, None
    if not event_id:
        return False, "missing_event_id", None, None

    ts = _parse_header_timestamp(timestamp_header)
    if not ts:
        return False, "invalid_timestamp", None, event_id
    now = datetime.now(timezone.utc)
    if abs((now - ts).total_seconds()) > WEBHOOK_TS_TOLERANCE_S:
        return False, "timestamp_out_of_tolerance", None, event_id

    webhook_secret = str(
        (cfg or {}).get("webhook_secret")
        or os.getenv("GITPEG_WEBHOOK_SECRET")
        or ""
    ).strip()
    if not webhook_secret:
        return False, "missing_webhook_secret", None, event_id

    # Primary spec: HMAC_SHA256(secret, "{timestamp}.{raw_body}")
    signed_payload = timestamp_header.encode("utf-8") + b"." + (raw_body or b"")
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest().lower()
    if hmac.compare_digest(signature, expected):
        return True, "ok", signature, event_id

    # Compatibility fallback for older emitters using only raw body.
    fallback = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body or b"",
        hashlib.sha256,
    ).hexdigest().lower()
    if hmac.compare_digest(signature, fallback):
        return True, "ok_compat_raw_body", signature, event_id
    return False, "signature_mismatch", signature, event_id


async def _register_webhook_event_once(
    sb: Client,
    event_id: str,
    *,
    signature: str,
    partner_code: Optional[str],
) -> bool:
    now = datetime.now(timezone.utc)
    if not event_id:
        return False

    try:
        existing = (
            sb.table("coord_gitpeg_webhook_events")
            .select("event_id,received_at")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        row = (existing.data or [None])[0]
        if row:
            received_at = _parse_db_ts(row.get("received_at"))
            if received_at and (now - received_at).total_seconds() <= WEBHOOK_EVENT_WINDOW_S:
                return False
            sb.table("coord_gitpeg_webhook_events").update(
                {
                    "received_at": now.isoformat(),
                    "signature": signature,
                    "partner_code": partner_code,
                }
            ).eq("event_id", event_id).execute()
            return True
        sb.table("coord_gitpeg_webhook_events").insert(
            {
                "event_id": event_id,
                "received_at": now.isoformat(),
                "signature": signature,
                "partner_code": partner_code,
            }
        ).execute()
        return True
    except Exception:
        return not _event_seen_in_cache(event_id, now)


def _upsert_project_registry_status(
    sb: Client,
    normalized: dict[str, Any],
    *,
    status: str,
    source_system: str = "qcspec",
    extra: Optional[dict[str, Any]] = None,
) -> None:
    row = {
        "project_code": normalized["project_code"],
        "project_name": normalized["project_name"],
        "site_code": normalized["site_code"],
        "site_name": normalized["site_name"],
        "namespace_uri": normalized["namespace_uri"],
        "project_uri": normalized["project_uri"],
        "site_uri": normalized["site_uri"],
        "executor_uri": normalized["executor_uri"],
        "gitpeg_status": status,
        "source_system": source_system,
    }
    if extra:
        row.update(extra)
    try:
        sb.table("coord_gitpeg_project_registry").upsert(row, on_conflict="project_code").execute()
    except Exception:
        # Keep compatibility when runtime columns are not migrated yet.
        base_row = {
            "project_code": normalized["project_code"],
            "project_name": normalized["project_name"],
            "site_code": normalized["site_code"],
            "site_name": normalized["site_name"],
            "namespace_uri": normalized["namespace_uri"],
            "project_uri": normalized["project_uri"],
            "site_uri": normalized["site_uri"],
            "executor_uri": normalized["executor_uri"],
            "gitpeg_status": status,
            "source_system": source_system,
        }
        sb.table("coord_gitpeg_project_registry").upsert(base_row, on_conflict="project_code").execute()


def _upsert_gitpeg_nodes(
    sb: Client,
    normalized: dict[str, Any],
    *,
    source_system: str = "qcspec-registrar",
) -> None:
    node_rows = [
        {
            "uri": normalized["project_uri"],
            "uri_type": "artifact",
            "project_code": normalized["project_code"],
            "display_name": normalized["project_name"],
            "namespace_uri": normalized["namespace_uri"],
            "source_system": source_system,
        },
        {
            "uri": normalized["site_uri"],
            "uri_type": "site",
            "project_code": normalized["project_code"],
            "display_name": normalized["site_name"],
            "namespace_uri": normalized["namespace_uri"],
            "source_system": source_system,
        },
    ]
    if normalized.get("executor_uri"):
        node_rows.append(
            {
                "uri": normalized["executor_uri"],
                "uri_type": "executor",
                "project_code": normalized["project_code"],
                "display_name": normalized.get("executor_name") or normalized["executor_uri"],
                "namespace_uri": normalized["namespace_uri"],
                "source_system": source_system,
            }
        )
    sb.table("coord_gitpeg_nodes").upsert(node_rows, on_conflict="uri").execute()


def _persist_gitpeg_activation(
    sb: Client,
    *,
    project: dict[str, Any],
    normalized: dict[str, Any],
    session_id: Optional[str],
    registration_id: Optional[str],
    node_uri: Optional[str],
    shell_uri: Optional[str],
    proof_hash: Optional[str],
    industry_code: Optional[str],
    industry_profile_id: Optional[str],
    token_payload: Optional[dict[str, Any]],
    registration_result: Optional[dict[str, Any]],
    activation_payload: Optional[dict[str, Any]],
) -> None:
    if node_uri and str(node_uri).startswith("v://"):
        normalized["project_uri"] = str(node_uri).strip()

    activation_data = dict(activation_payload or {})
    if shell_uri:
        activation_data.setdefault("shell_uri", shell_uri)
    if industry_code:
        activation_data.setdefault("industry_code", industry_code)
    if registration_id:
        activation_data.setdefault("registration_id", registration_id)
    if proof_hash:
        activation_data.setdefault("proof_hash", proof_hash)
    if node_uri:
        activation_data.setdefault("node_uri", node_uri)

    _upsert_project_registry_status(
        sb,
        normalized,
        status="active",
        source_system="qcspec-registrar",
        extra={
            "project_id": project.get("id"),
            "partner_session_id": session_id,
            "registration_id": registration_id,
            "industry_profile_id": industry_profile_id,
            "proof_hash": proof_hash,
            "node_uri": normalized.get("project_uri"),
            "token_payload": token_payload or {},
            "registration_result": registration_result or {},
            "activation_payload": activation_data,
        },
    )
    _upsert_gitpeg_nodes(sb, normalized, source_system="qcspec-registrar")

    update_patch: dict[str, Any] = {}
    if normalized.get("project_uri"):
        update_patch["v_uri"] = normalized["project_uri"]
    if update_patch:
        sb.table("projects").update(update_patch).eq("id", project["id"]).execute()


def _resolve_project_by_webhook_refs(
    sb: Client,
    *,
    project_id_hint: Optional[str],
    session_id: Optional[str],
    registration_id: Optional[str],
    get_project_data: Callable[..., Optional[dict[str, Any]]],
) -> Optional[dict[str, Any]]:
    project_id = str(project_id_hint or "").strip()
    if project_id:
        project = get_project_data(sb, project_id=project_id)
        if project:
            return project

    if session_id:
        reg = (
            sb.table("coord_gitpeg_project_registry")
            .select("project_id")
            .eq("partner_session_id", session_id)
            .limit(1)
            .execute()
        )
        if reg.data and reg.data[0].get("project_id"):
            pid = str(reg.data[0].get("project_id"))
            project = get_project_data(sb, project_id=pid)
            if project:
                return project

    if registration_id:
        reg = (
            sb.table("coord_gitpeg_project_registry")
            .select("project_id")
            .eq("registration_id", registration_id)
            .limit(1)
            .execute()
        )
        if reg.data and reg.data[0].get("project_id"):
            pid = str(reg.data[0].get("project_id"))
            project = get_project_data(sb, project_id=pid)
            if project:
                return project

    return None

