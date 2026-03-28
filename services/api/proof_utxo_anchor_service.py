"""
Anchor helpers for proof_utxo_engine.
services/api/proof_utxo_anchor_service.py
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

import httpx


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _to_base_url(value: Any) -> str:
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return ""
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = f"https://{raw}"
    return raw


def _extract_anchor_hash(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in (
        "anchor",
        "anchor_hash",
        "proof_anchor",
        "proof_hash",
        "hash",
        "tx_hash",
        "anchorHash",
        "proofHash",
    ):
        value = payload.get(key)
        text = str(value or "").strip()
        if text:
            return text
    nested = payload.get("data")
    if isinstance(nested, dict):
        return _extract_anchor_hash(nested)
    return ""


def resolve_anchor_config(
    anchor_config: Dict[str, Any],
    *,
    project_id: Optional[str],
    load_project_custom_fields: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    db_custom: Dict[str, Any] = {}
    if project_id:
        db_custom = load_project_custom_fields(str(project_id))
    base_url = _to_base_url(
        anchor_config.get("base_url")
        or db_custom.get("gitpeg_registrar_base_url")
        or anchor_config.get("gitpeg_registrar_base_url")
        or os.getenv("GITPEG_REGISTRAR_BASE_URL")
        or "https://gitpeg.cn"
    )
    path = str(
        anchor_config.get("anchor_path")
        or db_custom.get("gitpeg_proof_anchor_path")
        or anchor_config.get("gitpeg_proof_anchor_path")
        or os.getenv("GITPEG_PROOF_ANCHOR_PATH")
        or ""
    ).strip()
    endpoint = str(anchor_config.get("anchor_endpoint") or db_custom.get("gitpeg_proof_anchor_endpoint") or "").strip()
    if not endpoint and base_url and path:
        endpoint = f"{base_url}{path if path.startswith('/') else '/' + path}"
    enabled = _to_bool(
        anchor_config.get("enabled")
        or anchor_config.get("gitpeg_anchor_enabled")
        or anchor_config.get("proof_utxo_gitpeg_anchor_enabled")
        or db_custom.get("proof_utxo_gitpeg_anchor_enabled")
        or os.getenv("PROOF_UTXO_GITPEG_ANCHOR_ENABLED")
    )
    auth_token = str(
        anchor_config.get("auth_token")
        or db_custom.get("gitpeg_anchor_token")
        or db_custom.get("gitpeg_token")
        or db_custom.get("gitpeg_client_secret")
        or anchor_config.get("gitpeg_token")
        or anchor_config.get("gitpeg_client_secret")
        or os.getenv("GITPEG_PROOF_ANCHOR_TOKEN")
        or ""
    ).strip()
    timeout_s = (
        anchor_config.get("timeout_s")
        or db_custom.get("gitpeg_proof_anchor_timeout_s")
        or os.getenv("GITPEG_PROOF_ANCHOR_TIMEOUT_S")
        or 6
    )
    return {
        "enabled": enabled,
        "endpoint": endpoint,
        "auth_token": auth_token,
        "timeout_s": timeout_s,
    }


def load_project_custom_fields_from_db(sb: Any, project_id: str) -> Dict[str, Any]:
    try:
        proj = (
            sb.table("projects")
            .select("enterprise_id")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        rows = proj.data or []
        if not rows:
            return {}
        enterprise_id = str(rows[0].get("enterprise_id") or "").strip()
        if not enterprise_id:
            return {}
        cfg = (
            sb.table("enterprise_configs")
            .select("custom_fields")
            .eq("enterprise_id", enterprise_id)
            .limit(1)
            .execute()
        )
        cfg_rows = cfg.data or []
        if not cfg_rows:
            return {}
        custom = cfg_rows[0].get("custom_fields") or {}
        return custom if isinstance(custom, dict) else {}
    except Exception:
        return {}


def try_gitpeg_anchor(
    *,
    proof_hash: str,
    proof_id: str,
    project_id: Optional[str],
    project_uri: str,
    owner_uri: str,
    proof_type: str,
    result: str,
    state_data: Dict[str, Any],
    anchor_config: Optional[Dict[str, Any]],
    load_project_custom_fields: Callable[[str], Dict[str, Any]],
) -> str:
    cfg = resolve_anchor_config(
        anchor_config or {},
        project_id=project_id,
        load_project_custom_fields=load_project_custom_fields,
    )
    if not cfg.get("enabled"):
        return ""
    endpoint = str(cfg.get("endpoint") or "").strip()
    if not endpoint:
        return ""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "QCSpec-ProofUTXO/1.0",
    }
    token = str(cfg.get("auth_token") or "").strip()
    if token:
        if token.lower().startswith("bearer "):
            headers["Authorization"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"
    body = {
        "proof_hash": proof_hash,
        "proof_id": proof_id,
        "project_uri": project_uri,
        "owner_uri": owner_uri,
        "proof_type": proof_type,
        "result": result,
        "state_data": state_data or {},
    }
    try:
        timeout_s = float(cfg.get("timeout_s") or 6.0)
    except Exception:
        timeout_s = 6.0
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            res = client.post(endpoint, headers=headers, json=body)
            if res.status_code >= 400:
                return ""
            payload = {}
            try:
                payload = res.json()
            except Exception:
                payload = {}
            return _extract_anchor_hash(payload)
    except Exception:
        return ""
