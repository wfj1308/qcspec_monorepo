"""
Service helpers for GitPeg auto-registration.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from supabase import Client


def _slug_segment(value: str) -> str:
    segment = re.sub(r"[^a-zA-Z0-9_-]+", "-", (value or "").strip()).strip("-").lower()
    return segment[:64]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _namespace(value: Optional[str]) -> str:
    ns = (value or os.getenv("GITPEG_AUTOREG_NAMESPACE") or "v://cn.zhongbei/").strip()
    if not ns.startswith("v://"):
        ns = f"v://{ns.lstrip('/')}"
    if not ns.endswith("/"):
        ns += "/"
    return ns


def _optional_namespace(value: Optional[str]) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    return _namespace(text)


def _resolve_filter_namespace(
    *,
    sb: Client,
    enterprise_id: Optional[str],
    namespace_uri: Optional[str],
) -> Optional[str]:
    explicit_namespace = _optional_namespace(namespace_uri)
    if explicit_namespace:
        return explicit_namespace

    enterprise = str(enterprise_id or "").strip()
    if not enterprise:
        return None
    try:
        ent_res = (
            sb.table("enterprises")
            .select("v_uri")
            .eq("id", enterprise)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(500, f"autoreg enterprise lookup failed: {exc}") from exc

    row = (ent_res.data or [None])[0] if ent_res else None
    if not isinstance(row, dict):
        return None
    return _optional_namespace(str(row.get("v_uri") or ""))


class AutoRegisterProjectRequest(BaseModel):
    project_code: Optional[str] = None
    project_name: str
    site_code: Optional[str] = None
    site_name: Optional[str] = None
    namespace_uri: Optional[str] = None
    source_system: str = "erpnext"
    executor_code: Optional[str] = None
    executor_name: Optional[str] = None
    endpoint: Optional[str] = None
    norm_refs: list[str] = Field(default_factory=list)


def normalize_request(req: AutoRegisterProjectRequest) -> dict[str, Any]:
    project_code = _slug_segment(req.project_code or req.project_name)
    if not project_code:
        raise HTTPException(400, "project_code or project_name is required")

    project_name = (req.project_name or "").strip()
    if not project_name:
        raise HTTPException(400, "project_name is required")

    site_code = _slug_segment(req.site_code or project_code)
    site_name = (req.site_name or req.project_name or site_code).strip()
    ns = _namespace(req.namespace_uri)
    source_system = (req.source_system or "erpnext").strip() or "erpnext"

    project_uri = f"{ns}project/{project_code}"
    site_uri = f"{ns}site/{site_code}"

    executor_uri = None
    if req.executor_code:
        ex = _slug_segment(req.executor_code)
        if ex:
            executor_uri = f"{ns}executor/{ex}@v1"

    return {
        "project_code": project_code,
        "project_name": project_name,
        "site_code": site_code,
        "site_name": site_name,
        "namespace_uri": ns,
        "project_uri": project_uri,
        "site_uri": site_uri,
        "executor_uri": executor_uri,
        "executor_name": (req.executor_name or "").strip(),
        "source_system": source_system,
        "endpoint": (req.endpoint or "").strip() or None,
        "norm_refs": [x.strip() for x in req.norm_refs if isinstance(x, str) and x.strip()],
    }


def upsert_autoreg(sb: Client, payload: dict[str, Any]) -> dict[str, Any]:
    now_iso = _now_iso()

    project_row = {
        "project_code": payload["project_code"],
        "project_name": payload["project_name"],
        "site_code": payload["site_code"],
        "site_name": payload["site_name"],
        "namespace_uri": payload["namespace_uri"],
        "project_uri": payload["project_uri"],
        "site_uri": payload["site_uri"],
        "executor_uri": payload["executor_uri"],
        "gitpeg_status": "active",
        "source_system": payload["source_system"],
        "updated_at": now_iso,
    }
    res_project = (
        sb.table("coord_gitpeg_project_registry")
        .upsert(project_row, on_conflict="project_code")
        .execute()
    )

    node_rows = [
        {
            "uri": payload["project_uri"],
            "uri_type": "artifact",
            "project_code": payload["project_code"],
            "display_name": payload["project_name"],
            "namespace_uri": payload["namespace_uri"],
            "source_system": payload["source_system"],
            "updated_at": now_iso,
        },
        {
            "uri": payload["site_uri"],
            "uri_type": "site",
            "project_code": payload["project_code"],
            "display_name": payload["site_name"],
            "namespace_uri": payload["namespace_uri"],
            "source_system": payload["source_system"],
            "updated_at": now_iso,
        },
    ]
    if payload["executor_uri"]:
        node_rows.append(
            {
                "uri": payload["executor_uri"],
                "uri_type": "executor",
                "project_code": payload["project_code"],
                "display_name": payload["executor_name"] or payload["executor_uri"],
                "namespace_uri": payload["namespace_uri"],
                "source_system": payload["source_system"],
                "updated_at": now_iso,
            }
        )

    res_nodes = sb.table("coord_gitpeg_nodes").upsert(node_rows, on_conflict="uri").execute()
    return {
        "project_upsert_count": len(res_project.data or []),
        "node_upsert_count": len(res_nodes.data or []),
    }


async def autoreg_project_flow(*, req: AutoRegisterProjectRequest, sb: Client) -> dict[str, Any]:
    payload = normalize_request(req)
    try:
        upsert_result = upsert_autoreg(sb, payload)
    except Exception as exc:
        raise HTTPException(500, f"autoreg upsert failed: {exc}") from exc

    return {
        "success": True,
        "mode": "autoreg_project",
        "project_code": payload["project_code"],
        "project_name": payload["project_name"],
        "site_code": payload["site_code"],
        "site_name": payload["site_name"],
        "gitpeg_project_uri": payload["project_uri"],
        "gitpeg_site_uri": payload["site_uri"],
        "gitpeg_executor_uri": payload["executor_uri"],
        "gitpeg_status": "active",
        "source_system": payload["source_system"],
        "sync": upsert_result,
    }


def autoreg_projects_flow(
    *,
    limit: int,
    sb: Client,
    enterprise_id: Optional[str] = None,
    namespace_uri: Optional[str] = None,
) -> dict[str, Any]:
    try:
        filter_namespace = _resolve_filter_namespace(
            sb=sb,
            enterprise_id=enterprise_id,
            namespace_uri=namespace_uri,
        )
        query = (
            sb.table("coord_gitpeg_project_registry")
            .select("*")
            .order("updated_at", desc=True)
        )
        if filter_namespace:
            query = query.eq("namespace_uri", filter_namespace)
        res = query.limit(limit).execute()
    except Exception as exc:
        raise HTTPException(500, f"autoreg query failed: {exc}") from exc

    items = []
    for row in res.data or []:
        items.append(
            {
                "project_code": row.get("project_code"),
                "project_name": row.get("project_name"),
                "site_code": row.get("site_code"),
                "site_name": row.get("site_name"),
                "namespace_uri": row.get("namespace_uri"),
                "project_uri": row.get("project_uri"),
                "site_uri": row.get("site_uri"),
                "executor_uri": row.get("executor_uri"),
                "gitpeg_status": row.get("gitpeg_status"),
                "source_system": row.get("source_system"),
                "updated_at": row.get("updated_at"),
            }
        )
    return {"success": True, "total": len(items), "items": items}
