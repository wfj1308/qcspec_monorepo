"""Document governance flow helpers used by routers and domain services."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any
import uuid

from fastapi import HTTPException, UploadFile

from services.api.core.http import read_upload_content_async
from services.api.domain.documents.flows import (
    auto_classify_document,
    auto_generate_stake_nodes,
    create_node,
    list_node_tree,
    register_document,
    search_documents,
)

_DOC_UPLOAD_MAX_BYTES = 200 * 1024 * 1024


def _safe_name(value: str, default: str = "file.bin") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)
    return safe[:180] or default


def _parse_json_dict(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    return {}


def _parse_tags(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            value = json.loads(text)
            if isinstance(value, list):
                return [str(x).strip() for x in value if str(x).strip()]
        except Exception:
            pass
    return [x.strip() for x in text.split(",") if x.strip()]


def _extract_text_excerpt(content: bytes, mime_type: str, max_chars: int = 2000) -> str:
    if not content:
        return ""
    mt = str(mime_type or "").lower()
    if mt.startswith("text/") or mt in {"application/json", "application/xml"}:
        return content[: max_chars * 2].decode("utf-8", errors="replace")[:max_chars]
    return ""


async def doc_auto_classify_flow(*, body: Any) -> dict[str, Any]:
    payload = await auto_classify_document(
        file_name=str(body.file_name or ""),
        text_excerpt=str(body.text_excerpt or ""),
        mime_type=str(body.mime_type or ""),
    )
    return {"ok": True, "suggestion": payload}


def doc_create_node_flow(*, body: Any, sb: Any) -> dict[str, Any]:
    return create_node(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        parent_uri=str(body.parent_uri or ""),
        node_name=str(body.node_name or ""),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
        metadata=dict(body.metadata or {}),
    )


def doc_auto_generate_nodes_flow(*, body: Any, sb: Any) -> dict[str, Any]:
    return auto_generate_stake_nodes(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        parent_uri=str(body.parent_uri or "") or str(body.project_uri or ""),
        start_km=int(body.start_km),
        end_km=int(body.end_km),
        step_km=int(body.step_km or 1),
        leaf_name=str(body.leaf_name or "inspection"),
        executor_uri=str(body.executor_uri or "v://executor/system/"),
    )


def doc_tree_flow(*, project_uri: str, root_uri: str, sb: Any) -> dict[str, Any]:
    return list_node_tree(
        sb=sb,
        project_uri=project_uri,
        root_uri=root_uri,
    )


def doc_search_flow(*, body: Any, sb: Any) -> dict[str, Any]:
    return search_documents(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        node_uri=str(body.node_uri or ""),
        include_descendants=bool(body.include_descendants),
        query=str(body.query or ""),
        tags=list(body.tags or []),
        field_filters=dict(body.field_filters or {}),
        limit=int(body.limit or 200),
        dto_role=str(getattr(body, "dto_role", "") or ""),
    )


async def doc_register_upload_flow(
    *,
    file: UploadFile,
    project_uri: str,
    node_uri: str,
    source_utxo_id: str,
    executor_uri: str,
    text_excerpt: str,
    tags: str,
    custom_metadata: str,
    ai_metadata: str,
    doc_spec: str,
    dtorole_context: str,
    auto_classify: bool,
    sb: Any,
) -> dict[str, Any]:
    content = await read_upload_content_async(
        file=file,
        max_bytes=_DOC_UPLOAD_MAX_BYTES,
        empty_error="empty file",
        too_large_error="file too large, max 200MB",
    )

    mime_type = str(file.content_type or "application/octet-stream").strip().lower()
    file_name = _safe_name(file.filename or "document.bin")
    now = datetime.now(timezone.utc)
    project_key = _safe_name(project_uri.replace("v://", "v_"), "project")
    storage_path = (
        f"{project_key}/docs/{now.strftime('%Y%m%d')}/"
        f"{now.strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}_{file_name}"
    )
    sb.storage.from_("qcspec-reports").upload(
        storage_path,
        content,
        file_options={"content-type": mime_type or "application/octet-stream"},
    )
    public_url = sb.storage.from_("qcspec-reports").get_public_url(storage_path)
    storage_url = public_url if isinstance(public_url, str) else ""

    excerpt = str(text_excerpt or "").strip()
    if not excerpt:
        excerpt = _extract_text_excerpt(content, mime_type)

    ai_meta = _parse_json_dict(ai_metadata)
    if auto_classify and not ai_meta:
        ai_meta = await auto_classify_document(
            file_name=file_name,
            text_excerpt=excerpt,
            mime_type=mime_type,
        )

    return register_document(
        sb=sb,
        project_uri=project_uri,
        node_uri=node_uri or project_uri,
        source_utxo_id=source_utxo_id,
        file_name=file_name,
        file_size=len(content),
        mime_type=mime_type,
        storage_path=storage_path,
        storage_url=storage_url,
        text_excerpt=excerpt,
        ai_metadata=ai_meta,
        custom_metadata=_parse_json_dict(custom_metadata),
        tags=_parse_tags(tags),
        executor_uri=executor_uri or "v://executor/system/",
        doc_spec=_parse_json_dict(doc_spec),
        dtorole_context=str(dtorole_context or "").strip(),
    )
