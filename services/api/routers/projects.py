"""
QCSpec project routes.
services/api/routers/projects.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Optional
from postgrest.exceptions import APIError
from supabase import create_client, Client
from functools import lru_cache
from datetime import datetime, timedelta, timezone
import csv
import hmac
import hashlib
import json
import os
import re
from io import StringIO
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import httpx

from .autoreg import AutoRegisterProjectRequest, _normalize_request, _upsert_autoreg
from .erpnext import fetch_erpnext_project_basics

router = APIRouter()
public_router = APIRouter()
WEBHOOK_TS_TOLERANCE_S = 300
WEBHOOK_EVENT_WINDOW_S = 24 * 60 * 60
_WEBHOOK_EVENT_CACHE: dict[str, datetime] = {}

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

def slugify(name: str) -> str:
    """Project name -> stable v:// slug segment."""
    raw = str(name or "").strip().lower()
    compact = re.sub(r"\s+", "", raw, flags=re.UNICODE)
    return re.sub(r"[^\w-]+", "", compact, flags=re.UNICODE)[:20] or "project"


def _normalize_activity_summary(summary: Any, object_type: str, action: str) -> str:
    text = str(summary or "").strip()
    if not text:
        return f"{object_type or 'object'} {action or 'update'}"

    # 历史数据中曾用 "?" 代表未填桩号，这里统一替换成可读文案。
    if object_type == "photo" and action == "upload":
        text = re.sub(r"(照片上传\s*[·•]\s*)\?(\s*[·•])", r"\1未知桩号\2", text)
    return text

class ProjectCreate(BaseModel):
    name:          str
    type:          str
    owner_unit:    str
    erp_project_code: Optional[str] = None
    erp_project_name: Optional[str] = None
    contractor:    Optional[str] = None
    supervisor:    Optional[str] = None
    contract_no:   Optional[str] = None
    start_date:    Optional[str] = None
    end_date:      Optional[str] = None
    description:   Optional[str] = None
    seg_type:      str = 'km'
    seg_start:     Optional[str] = None
    seg_end:       Optional[str] = None
    km_interval:   Optional[int] = 20
    inspection_types: Optional[list[str]] = None
    contract_segs: Optional[list[dict[str, Any]]] = None
    structures: Optional[list[dict[str, Any]]] = None
    zero_personnel: Optional[list[dict[str, Any]]] = None
    zero_equipment: Optional[list[dict[str, Any]]] = None
    zero_subcontracts: Optional[list[dict[str, Any]]] = None
    zero_materials: Optional[list[dict[str, Any]]] = None
    zero_sign_status: Optional[str] = "pending"
    qc_ledger_unlocked: Optional[bool] = False
    # Backward compatible aliases for older frontend payloads (camelCase).
    zeroPersonnel: Optional[list[dict[str, Any]]] = None
    zeroEquipment: Optional[list[dict[str, Any]]] = None
    zeroSubcontracts: Optional[list[dict[str, Any]]] = None
    zeroMaterials: Optional[list[dict[str, Any]]] = None
    zeroSignStatus: Optional[str] = None
    qcLedgerUnlocked: Optional[bool] = None
    perm_template: str = 'standard'
    enterprise_id: str


class ProjectAutoregSyncRequest(BaseModel):
    enterprise_id: Optional[str] = None
    force: bool = True
    writeback: bool = True


class ProjectGitPegCompleteRequest(BaseModel):
    code: str
    registration_id: Optional[str] = None
    session_id: Optional[str] = None
    enterprise_id: Optional[str] = None


VALID_SEG_TYPES = {"km", "contract", "structure"}
VALID_PERM_TEMPLATES = {"standard", "strict", "open", "custom"}
VALID_INSPECTION_TYPES = {"flatness", "crack", "rut", "compaction", "settlement"}
VALID_DTO_ROLES = {"OWNER", "SUPERVISOR", "AI", "PUBLIC"}
VALID_ZERO_SIGN_STATUS = {"pending", "approved", "rejected"}


def _normalize_seg_type(value: Any) -> str:
    text = str(value or "km").strip().lower()
    return text if text in VALID_SEG_TYPES else "km"


def _normalize_perm_template(value: Any) -> str:
    text = str(value or "standard").strip().lower()
    return text if text in VALID_PERM_TEMPLATES else "standard"


def _normalize_km_interval(value: Any) -> int:
    try:
        interval = int(value)
    except Exception:
        interval = 20
    return max(1, min(interval, 500))


def _normalize_inspection_types(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        key = str(item or "").strip()
        if key in VALID_INSPECTION_TYPES and key not in out:
            out.append(key)
    return out


def _normalize_contract_segs(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        seg_range = str(item.get("range") or "").strip()
        if not name and not seg_range:
            continue
        out.append({"name": name, "range": seg_range})
        if len(out) >= 200:
            break
    return out


def _normalize_structures(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").strip()
        name = str(item.get("name") or "").strip()
        code = str(item.get("code") or "").strip()
        if not kind and not name and not code:
            continue
        out.append({"kind": kind, "name": name, "code": code})
        if len(out) >= 200:
            break
    return out


def _normalize_zero_sign_status(value: Any) -> str:
    text = str(value or "pending").strip().lower()
    return text if text in VALID_ZERO_SIGN_STATUS else "pending"


def _normalize_zero_personnel(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        title = str(item.get("title") or "").strip()
        dto_role = str(item.get("dto_role") or item.get("dtoRole") or "AI").strip().upper()
        if dto_role not in VALID_DTO_ROLES:
            dto_role = "AI"
        certificate = str(item.get("certificate") or "").strip()
        executor_uri = str(item.get("executor_uri") or item.get("executorUri") or "").strip()
        if not name and not title and not certificate:
            continue
        out.append({
            "name": name,
            "title": title,
            "dto_role": dto_role,
            "certificate": certificate,
            "executor_uri": executor_uri,
        })
        if len(out) >= 500:
            break
    return out


def _normalize_zero_equipment(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        model_no = str(item.get("model_no") or item.get("modelNo") or "").strip()
        inspection_item = str(item.get("inspection_item") or item.get("inspectionItem") or "").strip()
        valid_until = str(item.get("valid_until") or item.get("validUntil") or "").strip()
        toolpeg_uri = str(item.get("toolpeg_uri") or item.get("toolpegUri") or "").strip()
        status = str(item.get("status") or "").strip()
        if not name and not model_no:
            continue
        out.append({
            "name": name,
            "model_no": model_no,
            "inspection_item": inspection_item,
            "valid_until": valid_until,
            "toolpeg_uri": toolpeg_uri,
            "status": status,
        })
        if len(out) >= 500:
            break
    return out


def _normalize_zero_subcontracts(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        unit_name = str(item.get("unit_name") or item.get("unitName") or "").strip()
        content = str(item.get("content") or "").strip()
        seg_range = str(item.get("range") or "").strip()
        node_uri = str(item.get("node_uri") or item.get("nodeUri") or "").strip()
        if not unit_name and not content and not seg_range:
            continue
        out.append({
            "unit_name": unit_name,
            "content": content,
            "range": seg_range,
            "node_uri": node_uri,
        })
        if len(out) >= 500:
            break
    return out


def _normalize_zero_materials(values: Any) -> list[dict[str, str]]:
    if not isinstance(values, list):
        return []
    out: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        spec = str(item.get("spec") or "").strip()
        supplier = str(item.get("supplier") or "").strip()
        freq = str(item.get("freq") or "").strip()
        if not name and not spec and not supplier and not freq:
            continue
        out.append({
            "name": name,
            "spec": spec,
            "supplier": supplier,
            "freq": freq,
        })
        if len(out) >= 500:
            break
    return out


def _load_enterprise(sb: Client, enterprise_id: str) -> dict[str, Any]:
    ent = sb.table("enterprises").select("id,v_uri,name").eq("id", enterprise_id).single().execute()
    if not ent.data:
        raise HTTPException(404, "enterprise not found")
    return ent.data


def _load_sync_custom(sb: Client, enterprise_id: str) -> dict[str, Any]:
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


def _autoreg_enabled(custom: dict[str, Any]) -> bool:
    return bool(custom.get("erpnext_sync") or custom.get("gitpeg_enabled"))


def _build_autoreg_input(project: dict[str, Any], enterprise: dict[str, Any]) -> AutoRegisterProjectRequest:
    project_name = str(project.get("name") or "").strip()
    project_code = (
        str(project.get("erp_project_code") or "").strip()
        or str(project.get("contract_no") or "").strip()
        or str(project.get("id") or "").strip()
    )
    site_code = slugify(project_name)
    site_name = project_name
    namespace_uri = str(enterprise.get("v_uri") or "").strip() or None
    return AutoRegisterProjectRequest(
        project_code=project_code,
        project_name=project_name,
        site_code=site_code,
        site_name=site_name,
        namespace_uri=namespace_uri,
        source_system="qcspec",
    )


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_registration_mode(value: Any) -> str:
    mode = str(value or "DOMAIN").strip().upper()
    return mode if mode in {"DOMAIN", "SHELL"} else "DOMAIN"


def _gitpeg_registrar_config(custom: dict[str, Any]) -> dict[str, Any]:
    modules = custom.get("gitpeg_module_candidates")
    if not isinstance(modules, list) or not modules:
        raw_modules = str(
            custom.get("gitpeg_module_candidates_csv")
            or os.getenv("GITPEG_MODULE_CANDIDATES")
            or "proof,utrip,openapi"
        ).strip()
        modules = [item.strip() for item in raw_modules.split(",") if item.strip()]

    base_url = str(
        custom.get("gitpeg_registrar_base_url")
        or os.getenv("GITPEG_REGISTRAR_BASE_URL")
        or "https://gitpeg.cn"
    ).strip().rstrip("/")

    return {
        "enabled": _to_bool(custom.get("gitpeg_enabled")),
        "base_url": base_url,
        "partner_code": str(
            custom.get("gitpeg_partner_code")
            or os.getenv("GITPEG_PARTNER_CODE")
            or ""
        ).strip(),
        "industry_code": str(
            custom.get("gitpeg_industry_code")
            or os.getenv("GITPEG_INDUSTRY_CODE")
            or ""
        ).strip(),
        "client_id": str(
            custom.get("gitpeg_client_id")
            or os.getenv("GITPEG_CLIENT_ID")
            or ""
        ).strip(),
        "client_secret": str(
            custom.get("gitpeg_client_secret")
            or custom.get("gitpeg_token")
            or os.getenv("GITPEG_CLIENT_SECRET")
            or ""
        ).strip(),
        "registration_mode": _normalize_registration_mode(
            custom.get("gitpeg_registration_mode")
            or os.getenv("GITPEG_REGISTRATION_MODE")
            or "DOMAIN"
        ),
        "return_url": str(
            custom.get("gitpeg_return_url")
            or os.getenv("GITPEG_RETURN_URL")
            or ""
        ).strip(),
        "webhook_url": str(
            custom.get("gitpeg_webhook_url")
            or os.getenv("GITPEG_WEBHOOK_URL")
            or ""
        ).strip(),
        "webhook_secret": str(
            custom.get("gitpeg_webhook_secret")
            or os.getenv("GITPEG_WEBHOOK_SECRET")
            or ""
        ).strip(),
        "modules": modules,
        "timeout_s": 15.0,
    }


def _append_query_params(url: str, params: dict[str, Any]) -> str:
    raw = str(url or "").strip()
    if not raw:
        return raw
    parsed = urlparse(raw)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        k = str(key or "").strip()
        v = str(value or "").strip()
        if not k or not v:
            continue
        existing.setdefault(k, v)
    next_query = urlencode(existing, doseq=True)
    return urlunparse(parsed._replace(query=next_query))


def _gitpeg_registrar_ready(cfg: dict[str, Any]) -> bool:
    return all(
        [
            cfg.get("base_url"),
            cfg.get("partner_code"),
            cfg.get("industry_code"),
            cfg.get("client_id"),
            cfg.get("client_secret"),
        ]
    )


async def _gitpeg_create_registration_session(
    cfg: dict[str, Any],
    *,
    project: dict[str, Any],
    enterprise: dict[str, Any],
) -> dict[str, Any]:
    if not _gitpeg_registrar_ready(cfg):
        raise HTTPException(400, "gitpeg registrar config incomplete")

    project_name = str(project.get("name") or "").strip() or "项目"
    prefill_domain = f"{slugify(project_name) or 'project'}.local"
    body: dict[str, Any] = {
        "partner_code": cfg["partner_code"],
        "industry_code": cfg["industry_code"],
        "registration_mode": cfg["registration_mode"] or "DOMAIN",
        "prefill_data": {
            "organization_name": str(enterprise.get("name") or project.get("owner_unit") or project_name).strip(),
            "domain": prefill_domain,
        },
        "module_candidates": cfg.get("modules") or ["proof", "utrip", "openapi"],
        "external_reference": f"qcspec-proj-{project.get('id')}",
    }
    if cfg.get("return_url"):
        body["return_url"] = _append_query_params(
            cfg["return_url"],
            {
                "project_id": project.get("id"),
                "enterprise_id": project.get("enterprise_id") or enterprise.get("id"),
            },
        )
    if cfg.get("webhook_url"):
        body["webhook_url"] = cfg["webhook_url"]

    endpoint = f"{cfg['base_url']}/api/v1/partner/registration-sessions"
    try:
        async with httpx.AsyncClient(timeout=float(cfg.get("timeout_s") or 15.0), follow_redirects=True) as client:
            res = await client.post(endpoint, json=body, headers={"Content-Type": "application/json"})
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg session create failed (network): {exc.__class__.__name__}") from exc
    if res.status_code >= 400:
        detail = ""
        try:
            detail = json.dumps(res.json(), ensure_ascii=False)
        except Exception:
            detail = res.text
        raise HTTPException(502, f"gitpeg session create failed ({res.status_code}): {detail[:300]}")
    payload = res.json() if res.content else {}
    return payload if isinstance(payload, dict) else {}


async def _gitpeg_exchange_token(cfg: dict[str, Any], code: str) -> dict[str, Any]:
    endpoint = f"{cfg['base_url']}/api/v1/partner/token/exchange"
    body = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "code": code,
    }
    try:
        async with httpx.AsyncClient(timeout=float(cfg.get("timeout_s") or 15.0), follow_redirects=True) as client:
            res = await client.post(endpoint, json=body, headers={"Content-Type": "application/json"})
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg token exchange failed (network): {exc.__class__.__name__}") from exc
    if res.status_code >= 400:
        detail = ""
        try:
            detail = json.dumps(res.json(), ensure_ascii=False)
        except Exception:
            detail = res.text
        raise HTTPException(502, f"gitpeg token exchange failed ({res.status_code}): {detail[:300]}")
    payload = res.json() if res.content else {}
    if not isinstance(payload, dict):
        raise HTTPException(502, "gitpeg token exchange returned invalid payload")
    return payload


async def _gitpeg_get_registration_result(cfg: dict[str, Any], access_token: str, registration_id: str) -> dict[str, Any]:
    reg_id = str(registration_id or "").strip()
    if not reg_id:
        raise HTTPException(400, "registration_id is required")

    endpoint = f"{cfg['base_url']}/api/v1/registrations/{quote(reg_id, safe='')}/result"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=float(cfg.get("timeout_s") or 15.0), follow_redirects=True) as client:
            res = await client.get(endpoint, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"gitpeg registration result failed (network): {exc.__class__.__name__}") from exc
    if res.status_code >= 400:
        detail = ""
        try:
            detail = json.dumps(res.json(), ensure_ascii=False)
        except Exception:
            detail = res.text
        raise HTTPException(502, f"gitpeg registration result failed ({res.status_code}): {detail[:300]}")
    payload = res.json() if res.content else {}
    if not isinstance(payload, dict):
        raise HTTPException(502, "gitpeg registration result returned invalid payload")
    return payload


async def _gitpeg_get_registration_session(
    cfg: dict[str, Any],
    session_id: str,
    *,
    access_token: Optional[str] = None,
) -> dict[str, Any]:
    sid = str(session_id or "").strip()
    if not sid:
        return {}

    endpoint = f"{cfg['base_url']}/api/v1/registration-sessions/{quote(sid, safe='')}"
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        async with httpx.AsyncClient(timeout=float(cfg.get("timeout_s") or 15.0), follow_redirects=True) as client:
            res = await client.get(endpoint, headers=headers)
    except httpx.HTTPError:
        return {}
    if res.status_code >= 400:
        return {}
    payload = res.json() if res.content else {}
    return payload if isinstance(payload, dict) else {}


def _extract_missing_column_name(exc: APIError) -> Optional[str]:
    raw = exc.args[0] if exc.args else ""
    if isinstance(raw, dict):
        message = str(raw.get("message") or "")
    else:
        message = str(raw or exc)
    m = re.search(r"Could not find the '([^']+)' column", message)
    if not m:
        return None
    return m.group(1).strip() or None


def _insert_project_with_schema_fallback(
    sb: Client,
    rec: dict[str, Any],
    *,
    allow_schema_fallback: bool = True,
) -> Any:
    payload = dict(rec)
    if not allow_schema_fallback:
        return sb.table("projects").insert(payload).execute()
    max_attempts = max(1, len(payload))
    for _ in range(max_attempts):
        try:
            return sb.table("projects").insert(payload).execute()
        except APIError as exc:
            missing_col = _extract_missing_column_name(exc)
            if not missing_col or missing_col not in payload:
                raise
            payload.pop(missing_col, None)
    return sb.table("projects").insert(payload).execute()


def _project_zero_ledger_mismatch(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return True
    zero_keys = (
        "zero_personnel",
        "zero_equipment",
        "zero_subcontracts",
        "zero_materials",
    )
    for key in zero_keys:
        if row.get(key) != expected.get(key):
            return True
    if str(row.get("zero_sign_status") or "pending") != str(expected.get("zero_sign_status") or "pending"):
        return True
    if bool(row.get("qc_ledger_unlocked")) != bool(expected.get("qc_ledger_unlocked")):
        return True
    return False


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
    request: Request,
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
) -> Optional[dict[str, Any]]:
    project_id = str(project_id_hint or "").strip()
    if project_id:
        res = sb.table("projects").select("*").eq("id", project_id).limit(1).execute()
        if res.data:
            return res.data[0]

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
            res = sb.table("projects").select("*").eq("id", pid).limit(1).execute()
            if res.data:
                return res.data[0]

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
            res = sb.table("projects").select("*").eq("id", pid).limit(1).execute()
            if res.data:
                return res.data[0]

    return None


def _erp_headers(site_name: Optional[str], auth_header: Optional[str]) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "QCSpec-Project-Autoreg/1.0",
    }
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
        lower = key.lower()
        if lower.startswith("token "):
            out.append(("token", key))
        elif lower.startswith("bearer "):
            out.append(("bearer", key))
        elif ":" in key:
            out.append(("token", f"token {key}"))
        else:
            out.append(("bearer", f"Bearer {key}"))
    return out


def _erp_should_trust_env(base_url: str) -> bool:
    host = str(urlparse(base_url).hostname or "").strip().lower()
    if not host:
        return True
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    if host.endswith(".localhost"):
        return False
    return True


def _erp_rewrite_localhost_alias(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = str(parsed.hostname or "").strip().lower()
    if not host or not host.endswith(".localhost"):
        return base_url

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        auth = f"{auth}@"
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{auth}127.0.0.1{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def _normalize_erp_base_url(raw: Any) -> str:
    value = str(raw or "").strip().rstrip("/")
    if not value:
        return ""
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f"http://{value}"
    parsed = urlparse(value)
    path = str(parsed.path or "").strip()
    if path in {"/app", "/desk"}:
        parsed = parsed._replace(path="")
        value = urlunparse(parsed).rstrip("/")
    return value


async def _erp_lookup_docname(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    doctype: str,
    lookup_field: str,
    lookup_value: str,
) -> Optional[str]:
    if lookup_field == "name":
        return lookup_value
    params = {
        "fields": json.dumps(["name"], ensure_ascii=False),
        "filters": json.dumps([[doctype, lookup_field, "=", lookup_value]], ensure_ascii=False),
        "limit_page_length": "1",
    }
    list_url = f"{base_url}/api/resource/{quote(doctype, safe='')}"
    res = await client.get(list_url, headers=headers, params=params)
    if res.status_code >= 400:
        return None
    payload = res.json() if res.content else {}
    rows = payload.get("data") if isinstance(payload, dict) else []
    if not isinstance(rows, list) or not rows:
        return None
    name = rows[0].get("name") if isinstance(rows[0], dict) else None
    return str(name or "").strip() or None


async def _erp_writeback_autoreg(
    custom: dict[str, Any],
    project: dict[str, Any],
    autoreg_response: dict[str, Any],
) -> dict[str, Any]:
    base_url = _normalize_erp_base_url(custom.get("erpnext_url"))
    if not base_url:
        return {"attempted": False, "success": False, "reason": "erpnext_url_not_configured"}

    candidates = _erp_auth_candidates(custom.get("erpnext_api_key"), custom.get("erpnext_api_secret"))
    session_user = str(custom.get("erpnext_username") or "").strip()
    session_pass = str(custom.get("erpnext_password") or "").strip()
    has_session_auth = bool(session_user and session_pass)
    if not candidates and not has_session_auth:
        return {"attempted": False, "success": False, "reason": "erpnext_credentials_not_configured"}

    doctype = str(custom.get("erpnext_project_doctype") or "Project").strip() or "Project"
    lookup_field = str(custom.get("erpnext_project_lookup_field") or "name").strip() or "name"
    lookup_values: list[str] = []
    for candidate in (
        custom.get("erpnext_project_lookup_value"),
        project.get("contract_no"),
        autoreg_response.get("project_code"),
        project.get("name"),
    ):
        value = str(candidate or "").strip()
        if value and value not in lookup_values:
            lookup_values.append(value)
    if not lookup_values:
        return {"attempted": True, "success": False, "reason": "erpnext_lookup_value_missing"}

    f_project_uri = str(custom.get("erpnext_gitpeg_project_uri_field") or "gitpeg_project_uri").strip()
    f_site_uri = str(custom.get("erpnext_gitpeg_site_uri_field") or "gitpeg_site_uri").strip()
    f_status = str(custom.get("erpnext_gitpeg_status_field") or "gitpeg_status").strip()
    f_result_json = str(custom.get("erpnext_gitpeg_result_json_field") or "gitpeg_register_result_json").strip()
    f_registration_id = str(custom.get("erpnext_gitpeg_registration_id_field") or "gitpeg_registration_id").strip()
    f_node_uri = str(custom.get("erpnext_gitpeg_node_uri_field") or "gitpeg_node_uri").strip()
    f_shell_uri = str(custom.get("erpnext_gitpeg_shell_uri_field") or "gitpeg_shell_uri").strip()
    f_proof_hash = str(custom.get("erpnext_gitpeg_proof_hash_field") or "gitpeg_proof_hash").strip()
    f_industry_profile_id = str(
        custom.get("erpnext_gitpeg_industry_profile_id_field") or "gitpeg_industry_profile_id"
    ).strip()
    site_name = str(custom.get("erpnext_site_name") or "").strip() or None
    parsed_base = urlparse(base_url)
    base_host = str(parsed_base.hostname or "").strip()
    if not site_name and base_host.endswith(".localhost"):
        site_name = base_host
    site_candidates: list[Optional[str]] = [None]
    if site_name:
        site_candidates.append(site_name)
    request_base_url = _erp_rewrite_localhost_alias(base_url)

    node_uri = str(
        autoreg_response.get("node_uri")
        or autoreg_response.get("gitpeg_project_uri")
        or ""
    ).strip()
    shell_uri = str(autoreg_response.get("shell_uri") or "").strip()
    registration_id = str(autoreg_response.get("registration_id") or "").strip()
    proof_hash = str(autoreg_response.get("proof_hash") or "").strip()
    industry_profile_id = str(autoreg_response.get("industry_profile_id") or "").strip()

    update_doc = {
        f_project_uri: autoreg_response.get("gitpeg_project_uri"),
        f_site_uri: autoreg_response.get("gitpeg_site_uri"),
        f_status: autoreg_response.get("gitpeg_status") or "active",
        f_result_json: json.dumps(autoreg_response, ensure_ascii=False),
    }
    if f_node_uri and node_uri:
        update_doc[f_node_uri] = node_uri
    if f_shell_uri and shell_uri:
        update_doc[f_shell_uri] = shell_uri
    if f_registration_id and registration_id:
        update_doc[f_registration_id] = registration_id
    if f_proof_hash and proof_hash:
        update_doc[f_proof_hash] = proof_hash
    if f_industry_profile_id and industry_profile_id:
        update_doc[f_industry_profile_id] = industry_profile_id

    errors: list[str] = []
    async with httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        trust_env=_erp_should_trust_env(request_base_url),
    ) as client:
        for lookup_value in lookup_values:
            for site_name_try in site_candidates:
                site_tag = site_name_try or "site:auto"
                for mode, auth_header in candidates:
                    headers = _erp_headers(site_name_try, auth_header)
                    try:
                        docname = await _erp_lookup_docname(
                            client=client,
                            base_url=request_base_url,
                            headers=headers,
                            doctype=doctype,
                            lookup_field=lookup_field,
                            lookup_value=lookup_value,
                        )
                        if not docname:
                            errors.append(f"{site_tag}:{mode}:{lookup_field}={lookup_value}:doc_not_found")
                            continue

                        update_url = (
                            f"{request_base_url}/api/resource/{quote(doctype, safe='')}/{quote(docname, safe='')}"
                        )
                        res = await client.put(update_url, headers=headers, json=update_doc)
                        if res.status_code >= 400:
                            errors.append(f"{site_tag}:{mode}:{lookup_field}={lookup_value}:{res.status_code}")
                            continue
                        return {
                            "attempted": True,
                            "success": True,
                            "authMode": mode,
                            "doctype": doctype,
                            "docname": docname,
                            "lookupField": lookup_field,
                            "lookupValue": lookup_value,
                        }
                    except Exception as exc:
                        errors.append(f"{site_tag}:{mode}:{lookup_field}={lookup_value}:{exc}")

                if has_session_auth:
                    try:
                        login_res = await client.post(
                            f"{request_base_url}/api/method/login",
                            headers=_erp_headers(site_name_try, None),
                            data={"usr": session_user, "pwd": session_pass},
                        )
                        if login_res.status_code >= 400:
                            errors.append(
                                f"{site_tag}:session:{lookup_field}={lookup_value}:login_{login_res.status_code}"
                            )
                            continue

                        session_headers = _erp_headers(site_name_try, None)
                        csrf_token = str(
                            login_res.headers.get("x-frappe-csrf-token")
                            or login_res.headers.get("X-Frappe-CSRF-Token")
                            or ""
                        ).strip()
                        if csrf_token:
                            session_headers["X-Frappe-CSRF-Token"] = csrf_token

                        docname = await _erp_lookup_docname(
                            client=client,
                            base_url=request_base_url,
                            headers=session_headers,
                            doctype=doctype,
                            lookup_field=lookup_field,
                            lookup_value=lookup_value,
                        )
                        if not docname:
                            errors.append(f"{site_tag}:session:{lookup_field}={lookup_value}:doc_not_found")
                            continue

                        update_url = (
                            f"{request_base_url}/api/resource/{quote(doctype, safe='')}/{quote(docname, safe='')}"
                        )
                        res = await client.put(update_url, headers=session_headers, json=update_doc)
                        if res.status_code >= 400:
                            errors.append(f"{site_tag}:session:{lookup_field}={lookup_value}:{res.status_code}")
                            continue
                        return {
                            "attempted": True,
                            "success": True,
                            "authMode": "session",
                            "doctype": doctype,
                            "docname": docname,
                            "lookupField": lookup_field,
                            "lookupValue": lookup_value,
                        }
                    except Exception as exc:
                        errors.append(f"{site_tag}:session:{lookup_field}={lookup_value}:{exc}")

    return {"attempted": True, "success": False, "errors": errors}


async def _sync_project_autoreg(
    sb: Client,
    project: dict[str, Any],
    *,
    force: bool = False,
    writeback: bool = True,
) -> dict[str, Any]:
    enterprise_id = str(project.get("enterprise_id") or "").strip()
    if not enterprise_id:
        return {"enabled": False, "success": False, "reason": "project_enterprise_id_missing"}

    custom = _load_sync_custom(sb, enterprise_id)
    enabled = _autoreg_enabled(custom)
    if not enabled and not force:
        return {"enabled": False, "success": True, "skipped": True, "reason": "autoreg_disabled"}

    enterprise = _load_enterprise(sb, enterprise_id)
    req = _build_autoreg_input(project, enterprise)
    normalized = _normalize_request(req)
    cfg = _gitpeg_registrar_config(custom)

    if cfg.get("enabled"):
        if not _gitpeg_registrar_ready(cfg):
            return {
                "enabled": True,
                "success": False,
                "reason": "gitpeg_registrar_config_incomplete",
            }
        session_payload = await _gitpeg_create_registration_session(
            cfg,
            project=project,
            enterprise=enterprise,
        )
        _upsert_project_registry_status(
            sb,
            normalized,
            status="pending_activation",
            source_system="qcspec-registrar",
            extra={
                "project_id": project.get("id"),
                "partner_session_id": session_payload.get("session_id"),
                "registration_id": None,
                "industry_profile_id": None,
                "proof_hash": None,
                "node_uri": normalized.get("project_uri"),
                "activation_payload": {
                    "session_id": session_payload.get("session_id"),
                    "hosted_register_url": session_payload.get("hosted_register_url"),
                    "expires_at": session_payload.get("expires_at"),
                },
            },
        )
        autoreg_response = {
            "project_code": normalized["project_code"],
            "project_name": normalized["project_name"],
            "site_code": normalized["site_code"],
            "site_name": normalized["site_name"],
            "gitpeg_project_uri": normalized["project_uri"],
            "gitpeg_site_uri": normalized["site_uri"],
            "gitpeg_executor_uri": normalized["executor_uri"],
            "gitpeg_status": "pending_activation",
            "source_system": normalized["source_system"],
            "session_id": session_payload.get("session_id"),
            "hosted_register_url": session_payload.get("hosted_register_url"),
            "expires_at": session_payload.get("expires_at"),
        }
        return {
            "enabled": True,
            "success": True,
            "pending_activation": True,
            "autoreg": autoreg_response,
            "erp_writeback": {
                "attempted": False,
                "success": False,
                "reason": "waiting_gitpeg_registration_completion",
            },
        }

    upsert_info = _upsert_autoreg(sb, normalized)
    autoreg_response = {
        "project_code": normalized["project_code"],
        "project_name": normalized["project_name"],
        "site_code": normalized["site_code"],
        "site_name": normalized["site_name"],
        "gitpeg_project_uri": normalized["project_uri"],
        "gitpeg_site_uri": normalized["site_uri"],
        "gitpeg_executor_uri": normalized["executor_uri"],
        "gitpeg_status": "active",
        "source_system": normalized["source_system"],
        "sync": upsert_info,
        "mode": "local_mirror_fallback",
    }

    result = {
        "enabled": True,
        "success": True,
        "autoreg": autoreg_response,
    }
    if writeback:
        writeback_res = await _erp_writeback_autoreg(custom, project, autoreg_response)
        result["erp_writeback"] = writeback_res
        if writeback_res.get("attempted") and not writeback_res.get("success"):
            result["success"] = False
    return result

@router.get("/")
async def list_projects(
    enterprise_id: str,
    status: Optional[str] = None,
    type:   Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("projects").select("*")\
          .eq("enterprise_id", enterprise_id)\
          .order("created_at", desc=True)
    if status: q = q.eq("status", status)
    if type:   q = q.eq("type", type)
    res = q.execute()
    return {"data": res.data}


@router.get("/activity")
async def list_activity(
    enterprise_id: str,
    limit: int = 20,
    sb: Client = Depends(get_supabase),
):
    rows = sb.table("proof_chain").select("proof_id,object_type,action,summary,created_at,project_id")\
             .eq("enterprise_id", enterprise_id)\
             .order("created_at", desc=True)\
             .limit(max(1, min(limit, 100))).execute()
    data = rows.data or []

    dot_by_action = {
        "create": "#1A56DB",
        "submit": "#1A56DB",
        "upload": "#059669",
        "generate": "#D97706",
        "verify": "#0EA5E9",
        "warn": "#DC2626",
    }
    dot_by_type = {
        "inspection": "#1A56DB",
        "photo": "#059669",
        "report": "#D97706",
    }

    items = []
    for row in data:
        action = str(row.get("action") or "").lower()
        obj = str(row.get("object_type") or "").lower()
        dot = dot_by_action.get(action) or dot_by_type.get(obj) or "#64748B"
        summary = _normalize_activity_summary(row.get("summary"), obj, action)
        items.append({
            "dot": dot,
            "text": summary,
            "created_at": row.get("created_at"),
            "proof_id": row.get("proof_id"),
            "project_id": row.get("project_id"),
        })

    return {"data": items}


@router.get("/export")
async def export_projects_csv(
    enterprise_id: str,
    status: Optional[str] = None,
    type: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("projects").select("*")\
          .eq("enterprise_id", enterprise_id)\
          .order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if type:
        q = q.eq("type", type)
    rows = q.execute().data or []

    headers = [
        "id", "name", "type", "status", "owner_unit", "contractor", "supervisor",
        "contract_no", "erp_project_code", "erp_project_name", "start_date", "end_date", "v_uri",
        "record_count", "photo_count", "proof_count",
    ]

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k) for k in headers})
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="projects.csv"',
        },
    )

@router.post("/", status_code=201)
async def create_project(
    body: ProjectCreate,
    sb:   Client = Depends(get_supabase),
):
    enterprise = _load_enterprise(sb, body.enterprise_id)
    root_uri = str(enterprise.get("v_uri") or "").strip() or "v://cn.enterprise/"
    if not root_uri.endswith("/"):
        root_uri += "/"

    # Generate v:// URI
    slug = slugify(body.name)
    v_uri = f"{root_uri}{body.type}/{slug}/"

    # Check duplicate v:// node.
    exist = sb.table("projects").select("id")\
               .eq("v_uri", v_uri).execute()
    if exist.data:
        raise HTTPException(409, f"node already exists: {v_uri}")

    custom = _load_sync_custom(sb, body.enterprise_id)
    erp_project_basics: dict[str, Any] = {
        "attempted": False,
        "success": False,
        "reason": "erpnext_sync_disabled",
    }
    basics_patch: dict[str, str] = {}
    erp_sync_enabled = _to_bool(custom.get("erpnext_sync"))
    if erp_sync_enabled:
        erp_lookup_code = str(body.erp_project_code or "").strip() or None
        erp_lookup_name = str(body.erp_project_name or "").strip() or None
        if not erp_lookup_code:
            raise HTTPException(422, "erp_project_binding_required:missing_project_code")
        try:
            basics_res = await fetch_erpnext_project_basics(
                custom,
                project_code=erp_lookup_code,
                project_name=erp_lookup_name,
            )
            erp_project_basics = {
                "attempted": bool(basics_res.get("attempted", True)),
                "success": bool(basics_res.get("success")),
            }
            if basics_res.get("success"):
                raw_patch = basics_res.get("project_basics")
                if isinstance(raw_patch, dict):
                    basics_patch = {
                        key: str(value).strip()
                        for key, value in raw_patch.items()
                        if str(value or "").strip()
                    }
                    erp_project_basics["project_basics"] = basics_patch
            else:
                erp_project_basics["reason"] = basics_res.get("reason") or basics_res.get("errors")
        except Exception as exc:
            erp_project_basics = {
                "attempted": True,
                "success": False,
                "reason": f"erpnext_project_basics_error:{exc.__class__.__name__}",
            }
        if not erp_project_basics.get("success"):
            reason = str(erp_project_basics.get("reason") or "erp_project_basics_required")
            raise HTTPException(422, f"erp_project_binding_required:{reason}")

    def _pick_text(*values: Any) -> Optional[str]:
        for value in values:
            text = str(value or "").strip()
            if text and text not in {"-", "--", "~", "N/A", "n/a"}:
                return text
        return None

    zero_personnel_input = body.zero_personnel if body.zero_personnel is not None else body.zeroPersonnel
    zero_equipment_input = body.zero_equipment if body.zero_equipment is not None else body.zeroEquipment
    zero_subcontracts_input = body.zero_subcontracts if body.zero_subcontracts is not None else body.zeroSubcontracts
    zero_materials_input = body.zero_materials if body.zero_materials is not None else body.zeroMaterials
    zero_sign_status_input = body.zero_sign_status if body.zero_sign_status is not None else body.zeroSignStatus
    qc_ledger_unlocked_input = body.qc_ledger_unlocked if body.qc_ledger_unlocked is not None else body.qcLedgerUnlocked

    owner_unit = _pick_text(body.owner_unit, basics_patch.get("owner_unit"), enterprise.get("name"))
    if erp_sync_enabled:
        # ERP sync mode must bind against ERP returned canonical fields.
        erp_project_code = _pick_text(basics_patch.get("project_code"))
        erp_project_name = _pick_text(basics_patch.get("project_name"))
    else:
        erp_project_code = _pick_text(body.erp_project_code, body.contract_no)
        erp_project_name = _pick_text(body.erp_project_name, body.name)
    if erp_sync_enabled and not erp_project_code:
        raise HTTPException(422, "erp_project_binding_required:missing_project_code")
    if erp_sync_enabled and not erp_project_name:
        raise HTTPException(422, "erp_project_binding_required:missing_project_name")
    contractor = _pick_text(body.contractor, basics_patch.get("contractor"))
    supervisor = _pick_text(body.supervisor, basics_patch.get("supervisor"))
    contract_no = _pick_text(body.contract_no, basics_patch.get("contract_no"))
    start_date = _pick_text(body.start_date, basics_patch.get("start_date"))
    end_date = _pick_text(body.end_date, basics_patch.get("end_date"))
    description = _pick_text(body.description, basics_patch.get("description"))

    rec = {
        "enterprise_id": body.enterprise_id,
        "v_uri":         v_uri,
        "name":          body.name,
        "type":          body.type,
        "erp_project_code": erp_project_code,
        "erp_project_name": erp_project_name,
        "owner_unit":    owner_unit or "",
        "contractor":    contractor,
        "supervisor":    supervisor,
        "contract_no":   contract_no,
        "start_date":    start_date,
        "end_date":      end_date,
        "description":   description,
        "seg_type":      _normalize_seg_type(body.seg_type),
        "seg_start":     body.seg_start,
        "seg_end":       body.seg_end,
        "km_interval":   _normalize_km_interval(body.km_interval),
        "inspection_types": _normalize_inspection_types(body.inspection_types),
        "contract_segs": _normalize_contract_segs(body.contract_segs),
        "structures":    _normalize_structures(body.structures),
        "zero_personnel": _normalize_zero_personnel(zero_personnel_input),
        "zero_equipment": _normalize_zero_equipment(zero_equipment_input),
        "zero_subcontracts": _normalize_zero_subcontracts(zero_subcontracts_input),
        "zero_materials": _normalize_zero_materials(zero_materials_input),
        "zero_sign_status": _normalize_zero_sign_status(zero_sign_status_input),
        "qc_ledger_unlocked": bool(qc_ledger_unlocked_input),
        "perm_template": _normalize_perm_template(body.perm_template),
        "status":        "active",
    }
    zero_ledger_patch = {
        "zero_personnel": rec["zero_personnel"],
        "zero_equipment": rec["zero_equipment"],
        "zero_subcontracts": rec["zero_subcontracts"],
        "zero_materials": rec["zero_materials"],
        "zero_sign_status": rec["zero_sign_status"],
        "qc_ledger_unlocked": rec["qc_ledger_unlocked"],
    }
    try:
        res = _insert_project_with_schema_fallback(sb, rec, allow_schema_fallback=not erp_sync_enabled)
    except APIError as exc:
        missing_col = _extract_missing_column_name(exc)
        if missing_col in {"erp_project_code", "erp_project_name"}:
            raise HTTPException(
                500,
                "projects table missing ERP binding columns; run infra/supabase/010_projects_erp_binding.sql",
            ) from exc
        raw = exc.args[0] if exc.args else ""
        if isinstance(raw, dict):
            message = str(raw.get("message") or "failed to create project")
        else:
            message = str(raw or "failed to create project")
        raise HTTPException(500, message) from exc
    if not res.data:
        raise HTTPException(500, "failed to create project")

    proj = res.data[0]
    try:
        # Some environments run with partially migrated schemas or stale workers.
        # Do a write-after-insert reconcile so zero-ledger payload is not silently dropped.
        should_reconcile_zero_ledger = (
            bool(zero_ledger_patch["zero_personnel"])
            or bool(zero_ledger_patch["zero_equipment"])
            or bool(zero_ledger_patch["zero_subcontracts"])
            or bool(zero_ledger_patch["zero_materials"])
            or zero_ledger_patch["zero_sign_status"] != "pending"
            or bool(zero_ledger_patch["qc_ledger_unlocked"])
        )
        if should_reconcile_zero_ledger and _project_zero_ledger_mismatch(proj, zero_ledger_patch):
            sb.table("projects").update(zero_ledger_patch).eq("id", proj["id"]).execute()
            latest = sb.table("projects").select("*").eq("id", proj["id"]).limit(1).execute()
            if latest.data:
                proj = latest.data[0]
    except APIError:
        # Keep create path backward compatible for old DB schemas.
        pass
    if erp_sync_enabled:
        bind_code = str(erp_project_code or "").strip()
        bind_name = str(erp_project_name or "").strip()
        if (
            str(proj.get("erp_project_code") or "").strip() != bind_code
            or str(proj.get("erp_project_name") or "").strip() != bind_name
        ):
            try:
                sb.table("projects").update(
                    {
                        "erp_project_code": bind_code,
                        "erp_project_name": bind_name,
                    }
                ).eq("id", proj["id"]).execute()
                refreshed = sb.table("projects").select("*").eq("id", proj["id"]).limit(1).execute()
                if refreshed.data:
                    proj = refreshed.data[0]
            except APIError as exc:
                missing_col = _extract_missing_column_name(exc)
                if missing_col in {"erp_project_code", "erp_project_name"}:
                    raise HTTPException(
                        500,
                        "projects table missing ERP binding columns; run infra/supabase/010_projects_erp_binding.sql",
                    ) from exc
                raise
        if (
            str(proj.get("erp_project_code") or "").strip() != bind_code
            or str(proj.get("erp_project_name") or "").strip() != bind_name
        ):
            raise HTTPException(500, "erp_project_binding_persist_failed")

    try:
        sync_result = await _sync_project_autoreg(
            sb,
            proj,
            force=False,
            writeback=True,
        )
    except Exception as exc:
        sync_result = {
            "enabled": True,
            "success": False,
            "reason": f"autoreg_sync_failed: {exc}",
        }
    return {
        "id":    proj["id"],
        "v_uri": proj["v_uri"],
        "name":  proj["name"],
        "erp_project_code": proj.get("erp_project_code"),
        "erp_project_name": proj.get("erp_project_name"),
        "erp_project_basics": erp_project_basics,
        "autoreg_sync": sync_result,
    }

@router.post("/{project_id}/autoreg-sync")
async def sync_project_autoreg(
    project_id: str,
    body: Optional[ProjectAutoregSyncRequest] = None,
    sb: Client = Depends(get_supabase),
):
    req = body or ProjectAutoregSyncRequest()
    q = sb.table("projects").select("*").eq("id", project_id)
    if req.enterprise_id:
        q = q.eq("enterprise_id", req.enterprise_id)
    row = q.limit(1).execute()
    if not row.data:
        raise HTTPException(404, "project not found")

    try:
        result = await _sync_project_autoreg(
            sb,
            row.data[0],
            force=req.force,
            writeback=req.writeback,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        result = {
            "enabled": True,
            "success": False,
            "reason": detail,
        }
    except Exception as exc:
        result = {
            "enabled": True,
            "success": False,
            "reason": f"autoreg_sync_failed: {exc}",
        }
    return {
        "ok": bool(result.get("success")),
        "project_id": project_id,
        "result": result,
    }


@router.post("/{project_id}/gitpeg/complete")
async def complete_project_gitpeg_registration(
    project_id: str,
    body: ProjectGitPegCompleteRequest,
    sb: Client = Depends(get_supabase),
):
    q = sb.table("projects").select("*").eq("id", project_id)
    if body.enterprise_id:
        q = q.eq("enterprise_id", body.enterprise_id)
    row = q.limit(1).execute()
    if not row.data:
        raise HTTPException(404, "project not found")
    project = row.data[0]

    enterprise_id = str(project.get("enterprise_id") or "").strip()
    if not enterprise_id:
        raise HTTPException(400, "project enterprise_id missing")

    custom = _load_sync_custom(sb, enterprise_id)
    cfg = _gitpeg_registrar_config(custom)
    if not _gitpeg_registrar_ready(cfg):
        raise HTTPException(400, "gitpeg registrar config incomplete")

    token_payload = await _gitpeg_exchange_token(cfg, body.code)
    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(502, "gitpeg token exchange missing access_token")

    session_id = str(body.session_id or token_payload.get("session_id") or "").strip() or None
    registration_id = str(body.registration_id or "").strip() or None
    if not registration_id and session_id:
        session_payload = await _gitpeg_get_registration_session(
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

    result_payload = await _gitpeg_get_registration_result(cfg, access_token, registration_id)
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

    enterprise = _load_enterprise(sb, enterprise_id)
    normalized = _normalize_request(_build_autoreg_input(project, enterprise))
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
    if _to_bool(custom.get("erpnext_sync")):
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


@public_router.post("/gitpeg/webhook")
async def gitpeg_registrar_webhook(
    request: Request,
    sb: Client = Depends(get_supabase),
):
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
    enterprise = _load_enterprise(sb, enterprise_id)
    normalized = _normalize_request(_build_autoreg_input(project, enterprise))

    custom = _load_sync_custom(sb, enterprise_id)
    cfg = _gitpeg_registrar_config(custom)
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
    if code and _gitpeg_registrar_ready(cfg):
        token_payload = await _gitpeg_exchange_token(cfg, code)
        access_token = str(token_payload.get("access_token") or "").strip() or access_token
        session_id = str(token_payload.get("session_id") or "").strip() or session_id

    if not registration_id and session_id and _gitpeg_registrar_ready(cfg):
        session_payload = await _gitpeg_get_registration_session(
            cfg,
            session_id,
            access_token=access_token or None,
        )
        registration_id = str(
            session_payload.get("registration_id")
            or _find_value_recursive(session_payload, {"registration_id", "registrationId"})
            or ""
        ).strip() or registration_id

    if access_token and registration_id and _gitpeg_registrar_ready(cfg):
        result_payload = await _gitpeg_get_registration_result(cfg, access_token, registration_id)
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
        if _to_bool(custom.get("erpnext_sync")):
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
        if _to_bool(custom.get("erpnext_sync")):
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


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    sb: Client = Depends(get_supabase),
):
    res = sb.table("projects").select("*").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(404, "project not found")
    return res.data

@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    updates: dict,
    sb: Client = Depends(get_supabase),
):
    patch = dict(updates or {})
    # Backward compatible aliases for older frontend payloads (camelCase).
    if "zeroPersonnel" in patch and "zero_personnel" not in patch:
        patch["zero_personnel"] = patch.pop("zeroPersonnel")
    if "zeroEquipment" in patch and "zero_equipment" not in patch:
        patch["zero_equipment"] = patch.pop("zeroEquipment")
    if "zeroSubcontracts" in patch and "zero_subcontracts" not in patch:
        patch["zero_subcontracts"] = patch.pop("zeroSubcontracts")
    if "zeroMaterials" in patch and "zero_materials" not in patch:
        patch["zero_materials"] = patch.pop("zeroMaterials")
    if "zeroSignStatus" in patch and "zero_sign_status" not in patch:
        patch["zero_sign_status"] = patch.pop("zeroSignStatus")
    if "qcLedgerUnlocked" in patch and "qc_ledger_unlocked" not in patch:
        patch["qc_ledger_unlocked"] = patch.pop("qcLedgerUnlocked")

    if "seg_type" in patch:
        patch["seg_type"] = _normalize_seg_type(patch.get("seg_type"))
    if "perm_template" in patch:
        patch["perm_template"] = _normalize_perm_template(patch.get("perm_template"))
    if "km_interval" in patch:
        patch["km_interval"] = _normalize_km_interval(patch.get("km_interval"))
    if "inspection_types" in patch:
        patch["inspection_types"] = _normalize_inspection_types(patch.get("inspection_types"))
    if "contract_segs" in patch:
        patch["contract_segs"] = _normalize_contract_segs(patch.get("contract_segs"))
    if "structures" in patch:
        patch["structures"] = _normalize_structures(patch.get("structures"))
    if "zero_personnel" in patch:
        patch["zero_personnel"] = _normalize_zero_personnel(patch.get("zero_personnel"))
    if "zero_equipment" in patch:
        patch["zero_equipment"] = _normalize_zero_equipment(patch.get("zero_equipment"))
    if "zero_subcontracts" in patch:
        patch["zero_subcontracts"] = _normalize_zero_subcontracts(patch.get("zero_subcontracts"))
    if "zero_materials" in patch:
        patch["zero_materials"] = _normalize_zero_materials(patch.get("zero_materials"))
    if "zero_sign_status" in patch:
        patch["zero_sign_status"] = _normalize_zero_sign_status(patch.get("zero_sign_status"))
    if "qc_ledger_unlocked" in patch:
        patch["qc_ledger_unlocked"] = bool(patch.get("qc_ledger_unlocked"))

    res = sb.table("projects").update(patch).eq("id", project_id).execute()
    return res.data[0] if res.data else {}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    enterprise_id: Optional[str] = None,
    sb: Client = Depends(get_supabase),
):
    check = sb.table("projects").select("id").eq("id", project_id)
    if enterprise_id:
        check = check.eq("enterprise_id", enterprise_id)
    exists = check.limit(1).execute()
    if not exists.data:
        raise HTTPException(404, "project not found")

    # proof_chain.project_id -> projects.id is not ON DELETE CASCADE.
    sb.table("proof_chain").delete().eq("project_id", project_id).execute()

    q = sb.table("projects").delete().eq("id", project_id)
    if enterprise_id:
        q = q.eq("enterprise_id", enterprise_id)
    q.execute()

    left = sb.table("projects").select("id").eq("id", project_id).limit(1).execute()
    if left.data:
        raise HTTPException(500, "failed to delete project")
    return {"ok": True, "id": project_id}
