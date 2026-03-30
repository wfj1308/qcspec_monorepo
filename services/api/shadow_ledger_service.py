"""
Shadow ledger mirroring service.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import httpx


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


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _to_text(value).strip().lower() in {"1", "true", "yes", "on"}


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(raw: Any) -> Any:
    text = _to_text(raw).strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}


def _normalize_endpoint(raw: Any) -> str:
    text = _to_text(raw).strip().rstrip("/")
    if not text:
        return ""
    if not text.startswith("http://") and not text.startswith("https://"):
        text = f"https://{text}"
    return text


def _load_targets_from_env() -> list[dict[str, Any]]:
    raw = _to_text(os.getenv("QCSPEC_SHADOW_MIRROR_TARGETS") or "").strip()
    if not raw:
        return []
    parsed = _safe_json_loads(raw)
    if not isinstance(parsed, list):
        return []
    out: list[dict[str, Any]] = []
    for item in parsed:
        if isinstance(item, dict):
            out.append(item)
    return out


def _load_targets_from_config(*, sb: Any, project_id: str, project_uri: str) -> list[dict[str, Any]]:
    enterprise_id = ""
    if project_id:
        try:
            rows = (
                sb.table("projects")
                .select("enterprise_id")
                .eq("id", project_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if rows and isinstance(rows[0], dict):
                enterprise_id = _to_text(rows[0].get("enterprise_id") or "").strip()
        except Exception:
            enterprise_id = ""
    if (not enterprise_id) and project_uri:
        try:
            rows = (
                sb.table("projects")
                .select("enterprise_id")
                .eq("v_uri", project_uri)
                .limit(1)
                .execute()
                .data
                or []
            )
            if rows and isinstance(rows[0], dict):
                enterprise_id = _to_text(rows[0].get("enterprise_id") or "").strip()
        except Exception:
            enterprise_id = ""
    if not enterprise_id:
        return []
    try:
        cfg_rows = (
            sb.table("enterprise_configs")
            .select("custom_fields")
            .eq("enterprise_id", enterprise_id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception:
        return []
    if not cfg_rows:
        return []
    custom = _as_dict(cfg_rows[0].get("custom_fields"))
    targets = custom.get("shadow_mirror_targets")
    return [x for x in _as_list(targets) if isinstance(x, dict)]


def _normalize_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, t in enumerate(targets, start=1):
        endpoint = _normalize_endpoint(t.get("endpoint") or t.get("url"))
        if not endpoint:
            continue
        key = endpoint.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "mirror_id": _to_text(t.get("mirror_id") or t.get("id") or f"mirror-{i}").strip(),
                "name": _to_text(t.get("name") or f"mirror-{i}").strip(),
                "endpoint": endpoint,
                "auth_token": _to_text(t.get("auth_token") or t.get("token") or "").strip(),
                "enabled": _to_bool(t.get("enabled", True)),
                "required": _to_bool(t.get("required", False)),
            }
        )
    return out


def _resolve_targets(*, sb: Any | None, project_id: str, project_uri: str) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    if sb is not None:
        merged.extend(_load_targets_from_config(sb=sb, project_id=project_id, project_uri=project_uri))
    merged.extend(_load_targets_from_env())
    return _normalize_targets(merged)


def _derive_key(*, project_uri: str) -> bytes:
    secret = _to_text(
        os.getenv("QCSPEC_SHADOW_MIRROR_SECRET")
        or os.getenv("SHADOW_MIRROR_SECRET")
        or "qcspec-shadow-ledger-v1"
    ).strip()
    material = f"{secret}|{_to_text(project_uri).strip()}".encode("utf-8")
    return hashlib.sha256(material).digest()


def _encrypt_packet(*, packet: dict[str, Any], project_uri: str) -> dict[str, Any]:
    payload_raw = json.dumps(packet, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    packet_hash = hashlib.sha256(payload_raw).hexdigest()
    nonce = os.urandom(12)
    aad = b"QCSpec-Shadow-Ledger-v1"
    aes = AESGCM(_derive_key(project_uri=project_uri))
    ciphertext = aes.encrypt(nonce, payload_raw, aad)
    return {
        "algorithm": "AES-256-GCM",
        "packet_hash": packet_hash,
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "aad": aad.decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "cipher_hash": hashlib.sha256(ciphertext).hexdigest(),
    }


def _persist_log(*, sb: Any | None, rows: list[dict[str, Any]]) -> None:
    if sb is None or not rows:
        return
    try:
        sb.table("proof_shadow_mirror_log").insert(rows).execute()
    except Exception:
        return


def sync_to_mirrors(
    *,
    proof_packet: dict[str, Any],
    sb: Any | None = None,
    project_id: str = "",
    project_uri: str = "",
    timeout_s: float = 1.5,
) -> dict[str, Any]:
    normalized_project_uri = _to_text(project_uri or proof_packet.get("project_uri") or "").strip()
    targets = _resolve_targets(sb=sb, project_id=_to_text(project_id).strip(), project_uri=normalized_project_uri)
    targets = [t for t in targets if bool(t.get("enabled"))]

    if not targets:
        return {
            "attempted": False,
            "synced": False,
            "project_uri": normalized_project_uri,
            "target_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "results": [],
        }

    envelope = _encrypt_packet(packet=proof_packet, project_uri=normalized_project_uri)
    now_iso = _utc_iso()
    results: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []

    for target in targets:
        endpoint = _to_text(target.get("endpoint") or "").strip()
        if not endpoint:
            continue
        token = _to_text(target.get("auth_token") or "").strip()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "QCSpec-ShadowMirror/1.0",
        }
        if token:
            headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        post_body = {
            "mirror_id": _to_text(target.get("mirror_id") or "").strip(),
            "name": _to_text(target.get("name") or "").strip(),
            "project_uri": normalized_project_uri,
            "proof_id": _to_text(proof_packet.get("proof_id") or "").strip(),
            "created_at": now_iso,
            "encrypted_packet": envelope,
        }
        status = "failed"
        http_status = None
        error_msg = ""
        try:
            with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
                response = client.post(endpoint, headers=headers, json=post_body)
                http_status = int(response.status_code)
                if 200 <= response.status_code < 300:
                    status = "success"
                else:
                    error_msg = f"http_{response.status_code}"
        except Exception as exc:
            error_msg = _to_text(exc).strip() or "request_failed"

        item = {
            "mirror_id": _to_text(target.get("mirror_id") or "").strip(),
            "name": _to_text(target.get("name") or "").strip(),
            "endpoint": endpoint,
            "status": status,
            "http_status": http_status,
            "error": error_msg,
            "required": bool(target.get("required")),
        }
        results.append(item)
        logs.append(
            {
                "proof_id": _to_text(proof_packet.get("proof_id") or "").strip(),
                "project_uri": normalized_project_uri,
                "mirror_id": item["mirror_id"] or item["name"],
                "mirror_endpoint": endpoint,
                "status": status,
                "http_status": http_status,
                "error_msg": error_msg,
                "packet_hash": _to_text(envelope.get("packet_hash") or "").strip(),
                "cipher_hash": _to_text(envelope.get("cipher_hash") or "").strip(),
                "response_summary": {
                    "required": item["required"],
                },
                "created_at": now_iso,
            }
        )

    _persist_log(sb=sb, rows=logs)
    success_count = sum(1 for x in results if _to_text(x.get("status") or "") == "success")
    failed_count = len(results) - success_count
    required_failed = any(bool(x.get("required")) and _to_text(x.get("status") or "") != "success" for x in results)

    return {
        "attempted": True,
        "synced": failed_count == 0,
        "required_failed": required_failed,
        "project_uri": normalized_project_uri,
        "target_count": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "packet_hash": _to_text(envelope.get("packet_hash") or "").strip(),
        "cipher_hash": _to_text(envelope.get("cipher_hash") or "").strip(),
        "results": results,
    }

