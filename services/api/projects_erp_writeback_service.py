"""
Project ERP writeback helpers.
services/api/projects_erp_writeback_service.py
"""

from __future__ import annotations

import json
from typing import Any, Optional
from urllib.parse import quote, urlparse, urlunparse

import httpx

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




