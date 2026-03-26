"""
ERPNext integration routes and helpers for QCSpec.
services/api/routers/erpnext.py
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional
from urllib.parse import quote, urlparse, urlunparse
from uuid import UUID
import json
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client, create_client

router = APIRouter()

ERP_METHOD_PREFIX_DEFAULT = "zbgc_integration.qcspec"
ERP_PROJECT_BASICS_PATH_DEFAULT = f"/api/method/{ERP_METHOD_PREFIX_DEFAULT}.get_project_basics"
ERP_METERING_REQUESTS_PATH_DEFAULT = f"/api/method/{ERP_METHOD_PREFIX_DEFAULT}.get_metering_requests"
ERP_NOTIFY_PATH_DEFAULT = f"/api/method/{ERP_METHOD_PREFIX_DEFAULT}.notify"


@lru_cache(maxsize=1)
def _supabase_client_cached(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase() -> Client:
    url = str(os.getenv("SUPABASE_URL") or "").strip()
    key = str(
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        raise HTTPException(500, "Supabase not configured")
    return _supabase_client_cached(url, key)


class ERPNextNotifyRequest(BaseModel):
    enterprise_id: str
    project_id: Optional[str] = None
    stake: str
    subitem: Optional[str] = None
    result: str
    amount: Optional[float] = None
    reason: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


def _unwrap_frappe_payload(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    if "message" in data:
        return data.get("message")
    if "data" in data:
        return data.get("data")
    return data


def _pick_string(mapping: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_project_basics_payload(raw: Any) -> dict[str, str]:
    payload = _unwrap_frappe_payload(raw)
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        payload = payload[0]
    if not isinstance(payload, dict):
        return {}

    out = {
        "project_code": _pick_string(payload, ["project_code", "project_id", "project_code_id", "project", "name"]),
        "project_name": _pick_string(payload, ["project_name", "project_title", "display_name", "title"]),
        "owner_unit": _pick_string(payload, ["owner_unit", "owner", "employer", "client"]),
        "contractor": _pick_string(payload, ["contractor", "construction_unit", "builder"]),
        "supervisor": _pick_string(payload, ["supervisor", "supervision_unit", "consultant"]),
        "contract_no": _pick_string(payload, ["contract_no", "contract_code", "contract_id", "contract"]),
        "start_date": _pick_string(payload, ["start_date", "planned_start_date", "expected_start_date", "from_date"]),
        "end_date": _pick_string(payload, ["end_date", "planned_end_date", "expected_end_date", "to_date"]),
        "description": _pick_string(payload, ["description", "project_desc", "remark", "remarks"]),
    }
    return {k: v for k, v in out.items() if v}


def _normalize_metering_items(raw: Any) -> list[dict[str, Any]]:
    payload = _unwrap_frappe_payload(raw)
    if isinstance(payload, dict):
        rows = payload.get("items")
        if not isinstance(rows, list):
            rows = payload.get("rows")
        if not isinstance(rows, list):
            rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        amount = row.get("amount")
        if amount is None:
            amount = row.get("apply_amount")
        if amount is None:
            amount = row.get("request_amount")
        stake = _pick_string(row, ["stake", "stake_no", "pile_no", "segment"])
        subitem = _pick_string(row, ["subitem", "sub_item", "item", "part"])
        status = _pick_string(row, ["status", "workflow_state", "state"])
        out.append(
            {
                "id": _pick_string(row, ["name", "id", "request_id"]),
                "stake": stake,
                "subitem": subitem,
                "status": status,
                "amount": amount,
                "raw": row,
            }
        )
        if len(out) >= 200:
            break
    return out


def _evaluate_metering_gate(
    *,
    erp_sync_enabled: bool,
    inspection_result: str,
    metering_lookup: dict[str, Any],
) -> dict[str, Any]:
    result = str(inspection_result or "").strip().lower()
    success = bool(metering_lookup.get("success"))
    items = metering_lookup.get("items") if isinstance(metering_lookup.get("items"), list) else []
    count = len(items)
    matched = items[0] if items else None

    if not erp_sync_enabled:
        return {
            "enabled": False,
            "allow_submit": True,
            "can_release": True,
            "action": "skip",
            "reason": "erpnext_sync_disabled",
            "count": count,
            "matched": matched,
        }

    if result != "pass":
        return {
            "enabled": True,
            "allow_submit": True,
            "can_release": False,
            "action": "block",
            "reason": "inspection_not_passed",
            "count": count,
            "matched": matched,
        }

    if not success:
        return {
            "enabled": True,
            "allow_submit": False,
            "can_release": False,
            "action": "block",
            "reason": "metering_lookup_failed",
            "count": count,
            "matched": matched,
        }

    if count <= 0:
        return {
            "enabled": True,
            "allow_submit": False,
            "can_release": False,
            "action": "block",
            "reason": "no_pending_metering_request",
            "count": 0,
            "matched": None,
        }

    return {
        "enabled": True,
        "allow_submit": True,
        "can_release": True,
        "action": "release",
        "reason": "ready_to_release",
        "count": count,
        "matched": matched,
    }


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_erp_url(raw: Optional[str]) -> str:
    value = str(raw or "").strip().rstrip("/")
    if not value:
        return ""
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f"http://{value}"
    parsed = urlparse(value)
    # Users often paste Desk URL like https://host/app .
    # API base must be site root: https://host
    path = str(parsed.path or "").strip()
    if path in {"/app", "/desk"}:
        parsed = parsed._replace(path="")
        value = urlunparse(parsed).rstrip("/")
    return value


def _erp_should_trust_env(url: str) -> bool:
    host = str(urlparse(url).hostname or "").strip().lower()
    if not host:
        return True
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    if host.endswith(".localhost"):
        return False
    return True


def _rewrite_localhost_alias_url(url: str) -> str:
    parsed = urlparse(url)
    host = str(parsed.hostname or "").strip().lower()
    if not host or not host.endswith(".localhost"):
        return url

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        auth = f"{auth}@"
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{auth}127.0.0.1{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def _erp_headers(site_name: Optional[str], auth_header: Optional[str], *, as_json: bool = True) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "QCSpec-ERPNext-Bridge/1.0",
    }
    if as_json:
        headers["Content-Type"] = "application/json"
    site = str(site_name or "").strip()
    if site:
        headers["Host"] = site
        headers["X-Forwarded-Host"] = site
        headers["X-Frappe-Site-Name"] = site
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


def _erp_auth_candidates(api_key: Optional[str], api_secret: Optional[str]) -> list[tuple[str, str]]:
    key = str(api_key or "").strip()
    secret = str(api_secret or "").strip()
    out: list[tuple[str, str]] = []
    if key and secret:
        out.append(("token", f"token {key}:{secret}"))
    elif key:
        low = key.lower()
        if low.startswith("token "):
            out.append(("token", key))
        elif low.startswith("bearer "):
            out.append(("bearer", key))
        elif ":" in key:
            out.append(("token", f"token {key}"))
        else:
            out.append(("bearer", f"Bearer {key}"))
    return out


def load_erpnext_custom(sb: Client, enterprise_id: str) -> dict[str, Any]:
    cfg = (
        sb.table("enterprise_configs")
        .select("custom_fields")
        .eq("enterprise_id", enterprise_id)
        .limit(1)
        .execute()
    )
    if not cfg.data:
        return {}
    custom = cfg.data[0].get("custom_fields") or {}
    return custom if isinstance(custom, dict) else {}


def _erp_endpoint(base_url: str, path: str) -> str:
    raw = str(path or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if not raw.startswith("/"):
        raw = f"/{raw}"
    return f"{base_url}{raw}"


def _erp_method_label(path: str) -> str:
    text = str(path or "").strip()
    if text.startswith("/api/method/"):
        return text[len("/api/method/") :]
    return text or "unknown_method"


def _safe_json_or_text(res: httpx.Response) -> Any:
    try:
        return res.json()
    except Exception:
        return (res.text or "").strip()


def _compact_errors(errors: Any, limit: int = 2) -> list[str]:
    if not isinstance(errors, list):
        return []
    out: list[str] = []
    for item in errors[: max(1, min(limit, 10))]:
        text = str(item or "").strip().replace("\n", " ")
        if len(text) > 280:
            text = text[:280] + "..."
        out.append(text)
    return out


def _is_qcspec_method_missing(errors: Any) -> bool:
    text = " ".join(str(x or "") for x in (errors if isinstance(errors, list) else []))
    text = text.lower()
    return "app qcspec is not installed" in text or "failed to get method for command qcspec." in text


async def _erp_request(
    custom: dict[str, Any],
    *,
    method: str,
    path: str,
    params: Optional[dict[str, Any]] = None,
    body: Optional[dict[str, Any]] = None,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    base_url = _normalize_erp_url(custom.get("erpnext_url"))
    if not base_url:
        return {"attempted": False, "success": False, "reason": "erpnext_url_not_configured"}

    base_host = str(urlparse(base_url).hostname or "").strip()
    site_name = str(custom.get("erpnext_site_name") or "").strip() or None
    if not site_name and base_host.endswith(".localhost"):
        site_name = base_host
    site_candidates: list[Optional[str]] = [None]
    if site_name:
        site_candidates.append(site_name)

    request_base_url = _rewrite_localhost_alias_url(base_url)
    endpoint = _erp_endpoint(request_base_url, path)
    auth_candidates = _erp_auth_candidates(custom.get("erpnext_api_key"), custom.get("erpnext_api_secret"))
    session_user = str(custom.get("erpnext_username") or "").strip()
    session_pass = str(custom.get("erpnext_password") or "").strip()
    has_session = bool(session_user and session_pass)
    if not auth_candidates and not has_session:
        return {"attempted": False, "success": False, "reason": "erpnext_credentials_not_configured"}

    errors: list[str] = []
    async with httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        trust_env=_erp_should_trust_env(endpoint),
    ) as client:
        for site_name_try in site_candidates:
            site_tag = site_name_try or "site:auto"
            for mode, auth_header in auth_candidates:
                headers = _erp_headers(site_name_try, auth_header, as_json=body is not None)
                try:
                    res = await client.request(
                        method.upper(),
                        endpoint,
                        headers=headers,
                        params=params,
                        json=body if body is not None else None,
                    )
                    if res.status_code < 400:
                        return {
                            "attempted": True,
                            "success": True,
                            "authMode": mode,
                            "statusCode": res.status_code,
                            "data": _safe_json_or_text(res),
                        }
                    detail = _safe_json_or_text(res)
                    errors.append(f"{site_tag}:{mode}:{res.status_code}:{detail}")
                except Exception as exc:
                    errors.append(f"{site_tag}:{mode}:{exc.__class__.__name__}")

            if has_session:
                try:
                    login = await client.post(
                        f"{request_base_url}/api/method/login",
                        headers=_erp_headers(site_name_try, None, as_json=False),
                        data={"usr": session_user, "pwd": session_pass},
                    )
                    if login.status_code >= 400:
                        errors.append(f"{site_tag}:session_login:{login.status_code}:{_safe_json_or_text(login)}")
                    else:
                        headers = _erp_headers(site_name_try, None, as_json=body is not None)
                        csrf = str(
                            login.headers.get("x-frappe-csrf-token")
                            or login.headers.get("X-Frappe-CSRF-Token")
                            or ""
                        ).strip()
                        if csrf:
                            headers["X-Frappe-CSRF-Token"] = csrf
                        res = await client.request(
                            method.upper(),
                            endpoint,
                            headers=headers,
                            params=params,
                            json=body if body is not None else None,
                        )
                        if res.status_code < 400:
                            return {
                                "attempted": True,
                                "success": True,
                                "authMode": "session",
                                "statusCode": res.status_code,
                                "data": _safe_json_or_text(res),
                            }
                        errors.append(f"{site_tag}:session:{res.status_code}:{_safe_json_or_text(res)}")
                except Exception as exc:
                    errors.append(f"{site_tag}:session:{exc.__class__.__name__}")

    return {"attempted": True, "success": False, "errors": errors}


async def fetch_erpnext_project_basics(
    custom: dict[str, Any],
    *,
    project_code: Optional[str] = None,
    project_name: Optional[str] = None,
) -> dict[str, Any]:
    path = str(custom.get("erpnext_project_basics_path") or ERP_PROJECT_BASICS_PATH_DEFAULT).strip()
    params: dict[str, Any] = {}
    if project_code:
        params["project_code"] = project_code
    if project_name:
        params["project_name"] = project_name

    res = await _erp_request(custom, method="GET", path=path, params=params, timeout_s=10.0)
    if not res.get("success"):
        return res
    payload = res.get("data")
    return {
        **res,
        "project_basics": _normalize_project_basics_payload(payload),
    }


async def fetch_erpnext_metering_requests(
    custom: dict[str, Any],
    *,
    project_code: Optional[str] = None,
    stake: Optional[str] = None,
    subitem: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    path = str(custom.get("erpnext_metering_requests_path") or ERP_METERING_REQUESTS_PATH_DEFAULT).strip()
    params: dict[str, Any] = {}
    if project_code:
        params["project_code"] = project_code
    if stake:
        params["stake"] = stake
    if subitem:
        params["subitem"] = subitem
    if status:
        params["status"] = status

    res = await _erp_request(custom, method="GET", path=path, params=params, timeout_s=10.0)
    if not res.get("success"):
        return res
    payload = res.get("data")
    items = _normalize_metering_items(payload)
    return {
        **res,
        "items": items,
        "count": len(items),
    }


async def evaluate_erpnext_gate_for_inspection(
    custom: dict[str, Any],
    *,
    project_code: Optional[str] = None,
    stake: str,
    subitem: str,
    result: str,
) -> dict[str, Any]:
    erp_sync_enabled = _to_bool(custom.get("erpnext_sync"))
    if not erp_sync_enabled:
        gate = _evaluate_metering_gate(
            erp_sync_enabled=False,
            inspection_result=result,
            metering_lookup={"success": False, "items": []},
        )
        return {
            "gate": gate,
            "metering_lookup": {"attempted": False, "success": False, "count": 0, "reason": "erpnext_sync_disabled", "items": []},
        }
    code = str(project_code or "").strip()
    if not code:
        gate = _evaluate_metering_gate(
            erp_sync_enabled=erp_sync_enabled,
            inspection_result=result,
            metering_lookup={"success": False, "items": []},
        )
        gate.update(
            {
                "allow_submit": False if str(result or "").strip().lower() == "pass" else True,
                "can_release": False,
                "action": "block",
                "reason": "missing_erp_project_code_binding",
                "count": 0,
                "matched": None,
            }
        )
        return {
            "gate": gate,
            "metering_lookup": {
                "attempted": False,
                "success": False,
                "count": 0,
                "reason": "missing_erp_project_code_binding",
                "items": [],
            },
        }

    metering = await fetch_erpnext_metering_requests(
        custom,
        project_code=code,
        stake=str(stake or "").strip() or None,
        subitem=str(subitem or "").strip() or None,
        status=str(custom.get("erpnext_metering_status") or "pending").strip() or None,
    )
    gate = _evaluate_metering_gate(
        erp_sync_enabled=erp_sync_enabled,
        inspection_result=result,
        metering_lookup=metering,
    )
    return {
        "gate": gate,
        "metering_lookup": {
            "attempted": metering.get("attempted", False),
            "success": metering.get("success", False),
            "count": gate.get("count", 0),
            "reason": metering.get("reason") or metering.get("errors"),
            "items": (metering.get("items") if isinstance(metering.get("items"), list) else [])[:5],
        },
    }


async def notify_erpnext_for_inspection(
    custom: dict[str, Any],
    *,
    project: dict[str, Any],
    inspection: dict[str, Any],
    proof_id: str,
) -> dict[str, Any]:
    if not _to_bool(custom.get("erpnext_sync")):
        return {"attempted": False, "success": False, "reason": "erpnext_sync_disabled"}

    erp_project_code = str(project.get("erp_project_code") or "").strip() or None
    erp_project_name = str(project.get("erp_project_name") or project.get("name") or "").strip() or None
    gate_pack = await evaluate_erpnext_gate_for_inspection(
        custom,
        project_code=erp_project_code,
        stake=str(inspection.get("location") or "").strip(),
        subitem=str(inspection.get("type_name") or inspection.get("type") or "").strip(),
        result=str(inspection.get("result") or "").strip(),
    )
    gate = gate_pack.get("gate") if isinstance(gate_pack.get("gate"), dict) else {}
    metering_lookup = gate_pack.get("metering_lookup") if isinstance(gate_pack.get("metering_lookup"), dict) else {}
    metering_items = metering_lookup.get("items") if isinstance(metering_lookup.get("items"), list) else []
    matched_metering = gate.get("matched") if isinstance(gate.get("matched"), dict) else None

    notify_path = str(custom.get("erpnext_notify_path") or ERP_NOTIFY_PATH_DEFAULT).strip()
    result = str(inspection.get("result") or "").strip().lower()
    quality_passed = result == "pass"
    payload = {
        "enterprise_id": project.get("enterprise_id"),
        "project_id": project.get("id"),
        "project_name": project.get("name"),
        "erp_project_code": erp_project_code,
        "erp_project_name": erp_project_name,
        "contract_no": project.get("contract_no"),
        "project_uri": project.get("v_uri"),
        "inspection_id": inspection.get("id"),
        "stake": inspection.get("location"),
        "subitem": inspection.get("type_name") or inspection.get("type"),
        "result": result,
        "value": inspection.get("value"),
        "standard": inspection.get("standard"),
        "unit": inspection.get("unit"),
        "proof_id": proof_id,
        "quality_passed": quality_passed,
        "metering_action": gate.get("action") or ("release" if quality_passed else "block"),
        "reason": "" if gate.get("can_release") else (gate.get("reason") or "inspection_not_passed"),
        "metering_request_id": matched_metering.get("id") if isinstance(matched_metering, dict) else None,
        "metering_amount": matched_metering.get("amount") if isinstance(matched_metering, dict) else None,
        "metering_context": metering_items[:5],
    }
    notify_res = await _erp_request(custom, method="POST", path=notify_path, body=payload, timeout_s=10.0)
    notify_res["metering_lookup"] = metering_lookup
    notify_res["gate"] = {
        "enabled": bool(gate.get("enabled")),
        "allow_submit": bool(gate.get("allow_submit")),
        "can_release": bool(gate.get("can_release")),
        "action": gate.get("action"),
        "reason": gate.get("reason"),
    }
    return notify_res


@router.get("/gate-check")
async def check_metering_gate(
    enterprise_id: str,
    stake: str,
    subitem: str,
    result: str = "pass",
    project_id: Optional[str] = None,
    project_code: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    custom = load_erpnext_custom(sb, enterprise_id)
    resolved_project_code = str(project_code or "").strip() or None
    if project_id:
        try:
            UUID(str(project_id))
        except Exception:
            raise HTTPException(400, "invalid project_id")
        proj_res = (
            sb.table("projects")
            .select("id,enterprise_id,erp_project_code")
            .eq("id", project_id)
            .eq("enterprise_id", enterprise_id)
            .limit(1)
            .execute()
        )
        if not proj_res.data:
            raise HTTPException(404, "project not found")
        row = proj_res.data[0]
        resolved_project_code = str(row.get("erp_project_code") or resolved_project_code or "").strip() or None
    pack = await evaluate_erpnext_gate_for_inspection(
        custom,
        project_code=resolved_project_code,
        stake=stake,
        subitem=subitem,
        result=result,
    )
    return {
        "ok": True,
        "project_code": resolved_project_code,
        "gate": pack.get("gate"),
        "metering_lookup": pack.get("metering_lookup"),
    }


@router.get("/project-basics")
async def get_project_basics(
    enterprise_id: str,
    project_code: Optional[str] = None,
    project_name: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    custom = load_erpnext_custom(sb, enterprise_id)
    res = await fetch_erpnext_project_basics(custom, project_code=project_code, project_name=project_name)
    if not res.get("success"):
        raise HTTPException(502, f"erpnext project basics failed: {json.dumps(res, ensure_ascii=False)[:400]}")
    return res


@router.get("/metering-requests")
async def get_metering_requests(
    enterprise_id: str,
    project_code: Optional[str] = None,
    stake: Optional[str] = None,
    subitem: Optional[str] = None,
    status: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    custom = load_erpnext_custom(sb, enterprise_id)
    res = await fetch_erpnext_metering_requests(
        custom,
        project_code=project_code,
        stake=stake,
        subitem=subitem,
        status=status,
    )
    if not res.get("success"):
        raise HTTPException(502, f"erpnext metering requests failed: {json.dumps(res, ensure_ascii=False)[:400]}")
    return res


@router.post("/notify")
async def notify_erpnext(
    body: ERPNextNotifyRequest,
    sb: Client = Depends(get_supabase),
):
    custom = load_erpnext_custom(sb, body.enterprise_id)
    path = str(custom.get("erpnext_notify_path") or ERP_NOTIFY_PATH_DEFAULT).strip()
    passed = str(body.result or "").strip().lower() == "pass"
    payload = {
        "enterprise_id": body.enterprise_id,
        "project_id": body.project_id,
        "stake": body.stake,
        "subitem": body.subitem,
        "result": body.result,
        "amount": body.amount,
        "quality_passed": passed,
        "metering_action": "release" if passed else "block",
        "reason": body.reason or ("" if passed else "inspection_not_passed"),
        **(body.extra or {}),
    }
    res = await _erp_request(custom, method="POST", path=path, body=payload, timeout_s=10.0)
    if not res.get("success"):
        raise HTTPException(502, f"erpnext notify failed: {json.dumps(res, ensure_ascii=False)[:400]}")
    return res


@router.get("/probe")
async def probe_erpnext(
    enterprise_id: str,
    sample_project_name: str = "QCSpec联调样例项目",
    sample_stake: str = "K22+500",
    sample_subitem: str = "压实度",
    sb: Client = Depends(get_supabase),
):
    custom = load_erpnext_custom(sb, enterprise_id)

    ping = await _erp_request(custom, method="GET", path="/api/method/ping", timeout_s=10.0)
    basics_path = str(custom.get("erpnext_project_basics_path") or ERP_PROJECT_BASICS_PATH_DEFAULT).strip()
    metering_path = str(custom.get("erpnext_metering_requests_path") or ERP_METERING_REQUESTS_PATH_DEFAULT).strip()
    notify_path = str(custom.get("erpnext_notify_path") or ERP_NOTIFY_PATH_DEFAULT).strip()
    basics_label = _erp_method_label(basics_path)
    metering_label = _erp_method_label(metering_path)
    notify_label = _erp_method_label(notify_path)

    basics = await _erp_request(
        custom,
        method="GET",
        path=basics_path,
        params={"project_name": sample_project_name},
        timeout_s=10.0,
    )
    metering = await _erp_request(
        custom,
        method="GET",
        path=metering_path,
        params={"stake": sample_stake, "subitem": sample_subitem, "status": "pending"},
        timeout_s=10.0,
    )
    notify = await _erp_request(
        custom,
        method="POST",
        path=notify_path,
        body={
            "stake": sample_stake,
            "subitem": sample_subitem,
            "result": "pass",
            "quality_passed": True,
            "metering_action": "release",
        },
        timeout_s=10.0,
    )

    methods_ready = bool(basics.get("success")) and bool(metering.get("success")) and bool(notify.get("success"))
    blocker = None
    if _is_qcspec_method_missing(basics.get("errors")) or _is_qcspec_method_missing(metering.get("errors")) or _is_qcspec_method_missing(notify.get("errors")):
        blocker = "erpnext_missing_qcspec_methods"

    return {
        "ok": True,
        "enterprise_id": enterprise_id,
        "erpnext_url": custom.get("erpnext_url"),
        "auth_connectivity": {
            "success": bool(ping.get("success")),
            "auth_mode": ping.get("authMode"),
            "status_code": ping.get("statusCode"),
            "errors": _compact_errors(ping.get("errors"), limit=2),
        },
        "methods": {
            basics_label: {
                "success": bool(basics.get("success")),
                "status_code": basics.get("statusCode"),
                "errors": _compact_errors(basics.get("errors"), limit=2),
            },
            metering_label: {
                "success": bool(metering.get("success")),
                "status_code": metering.get("statusCode"),
                "errors": _compact_errors(metering.get("errors"), limit=2),
            },
            notify_label: {
                "success": bool(notify.get("success")),
                "status_code": notify.get("statusCode"),
                "errors": _compact_errors(notify.get("errors"), limit=2),
            },
        },
        "ready_for_qcspec": bool(ping.get("success")) and methods_ready,
        "blocker": blocker,
    }
