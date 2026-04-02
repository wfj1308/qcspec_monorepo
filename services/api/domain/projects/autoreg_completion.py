"""Canonical projects autoreg completion and webhook flows."""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Optional

from fastapi import HTTPException
from supabase import Client

from services.api.domain.projects.gitpeg_integration import (
    _extract_gitpeg_callback_fields,
    _extract_project_id_from_external_reference,
    _find_value_recursive,
    _persist_gitpeg_activation,
    _register_webhook_event_once,
    _resolve_project_by_webhook_refs,
    _upsert_project_registry_status,
    _verify_webhook_headers_and_signature,
)
from services.api.domain.projects.erp_writeback import _erp_writeback_autoreg


async def complete_gitpeg_registration_flow(
    *,
    sb: Client,
    project_id: str,
    body: Any,
    get_project_data: Callable[..., Optional[dict[str, Any]]],
    load_sync_custom: Callable[..., dict[str, Any]],
    gitpeg_registrar_config: Callable[[dict[str, Any]], dict[str, Any]],
    gitpeg_registrar_ready: Callable[[dict[str, Any]], bool],
    gitpeg_exchange_token: Callable[..., Awaitable[dict[str, Any]]],
    gitpeg_get_registration_session: Callable[..., Awaitable[dict[str, Any]]],
    gitpeg_get_registration_result: Callable[..., Awaitable[dict[str, Any]]],
    load_enterprise: Callable[..., dict[str, Any]],
    normalize_request: Callable[[Any], dict[str, Any]],
    build_autoreg_input: Callable[[dict[str, Any], dict[str, Any]], Any],
    to_bool: Callable[[Any], bool],
) -> dict[str, Any]:
    project = get_project_data(
        sb,
        project_id=project_id,
        enterprise_id=getattr(body, "enterprise_id", None),
    )
    if not project:
        raise HTTPException(404, "project not found")

    enterprise_id = str(project.get("enterprise_id") or "").strip()
    if not enterprise_id:
        raise HTTPException(400, "project enterprise_id missing")

    custom = load_sync_custom(sb, enterprise_id)
    cfg = gitpeg_registrar_config(custom)
    if not gitpeg_registrar_ready(cfg):
        raise HTTPException(400, "gitpeg registrar config incomplete")

    token_payload = await gitpeg_exchange_token(cfg, getattr(body, "code"))
    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(502, "gitpeg token exchange missing access_token")

    session_id = str(getattr(body, "session_id", None) or token_payload.get("session_id") or "").strip() or None
    registration_id = str(getattr(body, "registration_id", None) or "").strip() or None
    if not registration_id and session_id:
        session_payload = await gitpeg_get_registration_session(
            cfg,
            session_id,
            access_token=access_token or None,
        )
        registration_id = str(
            session_payload.get("registration_id")
            or _find_value_recursive(session_payload, {"registration_id", "registrationId"})
            or ""
        ).strip() or None
    if not registration_id:
        raise HTTPException(400, "registration_id is required (or resolvable from session_id)")

    result_payload = await gitpeg_get_registration_result(cfg, access_token, registration_id)
    node_uri = str(result_payload.get("node_uri") or "").strip()
    shell_uri = str(
        result_payload.get("shell_uri")
        or (result_payload.get("payload") or {}).get("shell_uri")
        or ""
    ).strip()
    proof_hash = str(result_payload.get("proof_hash") or "").strip()
    industry_code = str(
        result_payload.get("industry_code")
        or (result_payload.get("payload") or {}).get("industry_code")
        or ""
    ).strip()
    industry_profile_id = str(result_payload.get("industry_profile_id") or "").strip()
    payload = result_payload.get("payload") if isinstance(result_payload.get("payload"), dict) else {}

    enterprise = load_enterprise(sb, enterprise_id)
    normalized = normalize_request(build_autoreg_input(project, enterprise))
    if node_uri.startswith("v://"):
        normalized["project_uri"] = node_uri
    if isinstance(payload, dict):
        site_uri = str(payload.get("site_uri") or "").strip()
        if site_uri.startswith("v://"):
            normalized["site_uri"] = site_uri
        executor_uri = str(payload.get("executor_uri") or "").strip()
        if executor_uri.startswith("v://"):
            normalized["executor_uri"] = executor_uri

    _persist_gitpeg_activation(
        sb,
        project=project,
        normalized=normalized,
        session_id=session_id,
        registration_id=registration_id,
        node_uri=node_uri or normalized.get("project_uri"),
        shell_uri=shell_uri or None,
        proof_hash=proof_hash or None,
        industry_code=industry_code or None,
        industry_profile_id=industry_profile_id or None,
        token_payload=token_payload,
        registration_result=result_payload,
        activation_payload=payload if isinstance(payload, dict) else {},
    )

    erp_writeback = {"attempted": False, "success": False, "reason": "erpnext_sync_disabled"}
    if to_bool(custom.get("erpnext_sync")):
        erp_writeback = await _erp_writeback_autoreg(
            custom,
            project,
            {
                "project_code": normalized["project_code"],
                "project_name": normalized["project_name"],
                "site_code": normalized["site_code"],
                "site_name": normalized["site_name"],
                "gitpeg_project_uri": node_uri or normalized.get("project_uri"),
                "gitpeg_site_uri": normalized.get("site_uri"),
                "gitpeg_executor_uri": normalized.get("executor_uri"),
                "gitpeg_status": "active",
                "node_uri": node_uri or normalized.get("project_uri"),
                "shell_uri": shell_uri,
                "registration_id": registration_id,
                "proof_hash": proof_hash,
                "industry_profile_id": industry_profile_id,
                "industry_code": industry_code,
            },
        )

    return {
        "ok": True,
        "project_id": project_id,
        "registration_id": registration_id,
        "node_uri": node_uri or normalized["project_uri"],
        "shell_uri": shell_uri,
        "proof_hash": proof_hash,
        "industry_code": industry_code,
        "industry_profile_id": industry_profile_id,
        "token_type": token_payload.get("token_type"),
        "expires_in": token_payload.get("expires_in"),
        "session_id": session_id,
        "payload": payload,
        "erp_writeback": erp_writeback,
    }


async def process_gitpeg_webhook(
    *,
    request: Any,
    sb: Client,
    get_project_data: Callable[..., Optional[dict[str, Any]]],
    load_enterprise: Callable[..., dict[str, Any]],
    normalize_request: Callable[[Any], dict[str, Any]],
    build_autoreg_input: Callable[[dict[str, Any], dict[str, Any]], Any],
    load_sync_custom: Callable[..., dict[str, Any]],
    gitpeg_registrar_config: Callable[[dict[str, Any]], dict[str, Any]],
    gitpeg_registrar_ready: Callable[[dict[str, Any]], bool],
    gitpeg_exchange_token: Callable[..., Awaitable[dict[str, Any]]],
    gitpeg_get_registration_session: Callable[..., Awaitable[dict[str, Any]]],
    gitpeg_get_registration_result: Callable[..., Awaitable[dict[str, Any]]],
    to_bool: Callable[[Any], bool],
) -> dict[str, Any]:
    raw_body = await request.body()
    payload: dict[str, Any] = {}
    if raw_body:
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            raise HTTPException(400, "invalid webhook payload")

    fields = _extract_gitpeg_callback_fields(payload)

    external_reference = str(fields.get("external_reference") or "").strip()
    project_id_hint = _extract_project_id_from_external_reference(external_reference)
    if not project_id_hint:
        project_id_candidate = _find_value_recursive(payload, {"project_id", "projectId"})
        if project_id_candidate:
            project_id_hint = str(project_id_candidate).strip()

    session_id = str(fields.get("session_id") or "").strip() or None
    registration_id = str(fields.get("registration_id") or "").strip() or None
    code = str(fields.get("code") or "").strip() or None
    access_token = str(fields.get("access_token") or "").strip() or None

    project = _resolve_project_by_webhook_refs(
        sb,
        project_id_hint=project_id_hint,
        session_id=session_id,
        registration_id=registration_id,
        get_project_data=get_project_data,
    )
    if not project:
        return {
            "ok": True,
            "processed": False,
            "reason": "project_not_resolved",
            "session_id": session_id,
            "registration_id": registration_id,
        }

    enterprise_id = str(project.get("enterprise_id") or "").strip()
    if not enterprise_id:
        return {"ok": True, "processed": False, "reason": "project_enterprise_id_missing"}
    enterprise = load_enterprise(sb, enterprise_id)
    normalized = normalize_request(build_autoreg_input(project, enterprise))

    custom = load_sync_custom(sb, enterprise_id)
    cfg = gitpeg_registrar_config(custom)
    verified, verify_reason, signature, event_id = _verify_webhook_headers_and_signature(
        request,
        raw_body=raw_body,
        cfg=cfg,
    )
    if not verified:
        raise HTTPException(403, f"invalid webhook signature ({verify_reason})")

    event_fresh = await _register_webhook_event_once(
        sb,
        str(event_id or "").strip(),
        signature=str(signature or "").strip(),
        partner_code=str(fields.get("partner_code") or cfg.get("partner_code") or "").strip() or None,
    )
    if not event_fresh:
        return {
            "ok": True,
            "processed": False,
            "reason": "duplicate_event",
            "event_id": event_id,
            "session_id": session_id,
            "registration_id": registration_id,
        }

    token_payload: dict[str, Any] = {}
    if code and gitpeg_registrar_ready(cfg):
        token_payload = await gitpeg_exchange_token(cfg, code)
        access_token = str(token_payload.get("access_token") or "").strip() or access_token
        session_id = str(token_payload.get("session_id") or "").strip() or session_id

    if not registration_id and session_id and gitpeg_registrar_ready(cfg):
        session_payload = await gitpeg_get_registration_session(
            cfg,
            session_id,
            access_token=access_token or None,
        )
        registration_id = str(
            session_payload.get("registration_id")
            or _find_value_recursive(session_payload, {"registration_id", "registrationId"})
            or ""
        ).strip() or registration_id

    if access_token and registration_id and gitpeg_registrar_ready(cfg):
        result_payload = await gitpeg_get_registration_result(cfg, access_token, registration_id)
        node_uri = str(result_payload.get("node_uri") or fields.get("node_uri") or "").strip()
        shell_uri = str(
            result_payload.get("shell_uri")
            or fields.get("shell_uri")
            or (result_payload.get("payload") or {}).get("shell_uri")
            or ""
        ).strip()
        proof_hash = str(result_payload.get("proof_hash") or fields.get("proof_hash") or "").strip()
        industry_code = str(
            result_payload.get("industry_code")
            or fields.get("industry_code")
            or (result_payload.get("payload") or {}).get("industry_code")
            or ""
        ).strip()
        industry_profile_id = str(
            result_payload.get("industry_profile_id") or fields.get("industry_profile_id") or ""
        ).strip()
        activation_payload = result_payload.get("payload") if isinstance(result_payload.get("payload"), dict) else {}

        if isinstance(activation_payload, dict):
            site_uri = str(activation_payload.get("site_uri") or "").strip()
            if site_uri.startswith("v://"):
                normalized["site_uri"] = site_uri
            executor_uri = str(activation_payload.get("executor_uri") or "").strip()
            if executor_uri.startswith("v://"):
                normalized["executor_uri"] = executor_uri

        _persist_gitpeg_activation(
            sb,
            project=project,
            normalized=normalized,
            session_id=session_id,
            registration_id=registration_id,
            node_uri=node_uri or normalized.get("project_uri"),
            shell_uri=shell_uri or None,
            proof_hash=proof_hash or None,
            industry_code=industry_code or None,
            industry_profile_id=industry_profile_id or None,
            token_payload=token_payload or {"access_token": "***"},
            registration_result=result_payload,
            activation_payload=activation_payload,
        )
        erp_writeback = {"attempted": False, "success": False, "reason": "erpnext_sync_disabled"}
        if to_bool(custom.get("erpnext_sync")):
            erp_writeback = await _erp_writeback_autoreg(
                custom,
                project,
                {
                    "project_code": normalized["project_code"],
                    "project_name": normalized["project_name"],
                    "site_code": normalized["site_code"],
                    "site_name": normalized["site_name"],
                    "gitpeg_project_uri": node_uri or normalized.get("project_uri"),
                    "gitpeg_site_uri": normalized.get("site_uri"),
                    "gitpeg_executor_uri": normalized.get("executor_uri"),
                    "gitpeg_status": "active",
                    "node_uri": node_uri or normalized.get("project_uri"),
                    "shell_uri": shell_uri,
                    "registration_id": registration_id,
                    "proof_hash": proof_hash,
                    "industry_profile_id": industry_profile_id,
                    "industry_code": industry_code,
                },
            )
        return {
            "ok": True,
            "processed": True,
            "project_id": project.get("id"),
            "registration_id": registration_id,
            "session_id": session_id,
            "node_uri": node_uri or normalized.get("project_uri"),
            "shell_uri": shell_uri,
            "proof_hash": proof_hash,
            "industry_code": industry_code,
            "industry_profile_id": industry_profile_id,
            "erp_writeback": erp_writeback,
        }

    node_uri = str(fields.get("node_uri") or "").strip()
    shell_uri = str(fields.get("shell_uri") or "").strip()
    proof_hash = str(fields.get("proof_hash") or "").strip()
    industry_code = str(fields.get("industry_code") or "").strip()
    industry_profile_id = str(fields.get("industry_profile_id") or "").strip()
    if registration_id and node_uri.startswith("v://"):
        _persist_gitpeg_activation(
            sb,
            project=project,
            normalized=normalized,
            session_id=session_id,
            registration_id=registration_id,
            node_uri=node_uri,
            shell_uri=shell_uri or None,
            proof_hash=proof_hash or None,
            industry_code=industry_code or None,
            industry_profile_id=industry_profile_id or None,
            token_payload=token_payload,
            registration_result={},
            activation_payload=payload,
        )
        erp_writeback = {"attempted": False, "success": False, "reason": "erpnext_sync_disabled"}
        if to_bool(custom.get("erpnext_sync")):
            erp_writeback = await _erp_writeback_autoreg(
                custom,
                project,
                {
                    "project_code": normalized["project_code"],
                    "project_name": normalized["project_name"],
                    "site_code": normalized["site_code"],
                    "site_name": normalized["site_name"],
                    "gitpeg_project_uri": node_uri or normalized.get("project_uri"),
                    "gitpeg_site_uri": normalized.get("site_uri"),
                    "gitpeg_executor_uri": normalized.get("executor_uri"),
                    "gitpeg_status": "active",
                    "node_uri": node_uri or normalized.get("project_uri"),
                    "shell_uri": shell_uri,
                    "registration_id": registration_id,
                    "proof_hash": proof_hash,
                    "industry_profile_id": industry_profile_id,
                    "industry_code": industry_code,
                },
            )
        return {
            "ok": True,
            "processed": True,
            "project_id": project.get("id"),
            "registration_id": registration_id,
            "session_id": session_id,
            "node_uri": node_uri,
            "shell_uri": shell_uri,
            "proof_hash": proof_hash,
            "industry_code": industry_code,
            "industry_profile_id": industry_profile_id,
            "mode": "webhook_direct_result",
            "erp_writeback": erp_writeback,
        }

    _upsert_project_registry_status(
        sb,
        normalized,
        status="pending_activation",
        source_system="qcspec-registrar",
        extra={
            "project_id": project.get("id"),
            "partner_session_id": session_id,
            "registration_id": registration_id,
            "activation_payload": payload,
        },
    )
    return {
        "ok": True,
        "processed": False,
        "project_id": project.get("id"),
        "reason": "awaiting_code_or_token",
        "session_id": session_id,
        "registration_id": registration_id,
    }


__all__ = [
    "complete_gitpeg_registration_flow",
    "process_gitpeg_webhook",
]
