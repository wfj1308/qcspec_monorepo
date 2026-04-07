"""
Document governance helpers:
- v:// node tree (unlimited hierarchy)
- document registration + tag persistence
- AI auto classification
- structured search
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
from typing import Any

import httpx
from fastapi import HTTPException

from services.api.domain.documents.runtime.specir_docpeg_v11 import (
    build_docpeg_specir_v11,
    project_docpeg_specir_v11_for_role,
)
from services.api.domain.utxo.integrations import ProofUTXOEngine


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


def _is_document_row(row: dict[str, Any]) -> bool:
    ptype = _to_text(_as_dict(row).get("proof_type") or "").strip().lower()
    if ptype == "document":
        return True
    if ptype != "archive":
        return False
    sd = _as_dict(_as_dict(row).get("state_data"))
    if bool(sd.get("doc_registry")):
        return True
    return _to_text(sd.get("artifact_type") or "").strip().lower() == "governance_document"


def _is_proof_type_constraint_error(exc: Exception) -> bool:
    text = f"{exc.__class__.__name__}: {exc}".lower()
    return "proof_utxo_proof_type_check" in text or "proof_type_check" in text


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_token(raw: Any) -> str:
    text = _to_text(raw).strip()
    if not text:
        return "node"
    token = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+", "-", text).strip("-")
    return token[:120] or "node"


def _normalize_uri(uri: str) -> str:
    text = _to_text(uri).strip()
    if not text:
        return ""
    if not text.startswith("v://"):
        raise HTTPException(400, "uri must start with v://")
    body = text[4:].replace("\\", "/")
    body = re.sub(r"/{2,}", "/", body).strip("/")
    normalized = f"v://{body}" if body else "v://"
    if not normalized.endswith("/"):
        normalized += "/"
    return normalized


def _join_node_uri(parent_uri: str, node_name: str) -> str:
    parent = _normalize_uri(parent_uri)
    if not parent:
        raise HTTPException(400, "parent_uri is required")
    return _normalize_uri(f"{parent.rstrip('/')}/{_safe_token(node_name)}/")


def _parent_uri(uri: str, root_uri: str) -> str:
    u = _normalize_uri(uri)
    root = _normalize_uri(root_uri)
    if not u or not root or u == root:
        return ""
    p = PurePosixPath(u.replace("v://", "/"))
    parent = str(p.parent).rstrip("/")
    parent_uri = f"v://{parent}/".replace("v:////", "v://")
    if not parent_uri.startswith(root):
        return root
    return parent_uri


def _node_name(uri: str) -> str:
    text = _normalize_uri(uri).rstrip("/")
    if "/" not in text:
        return text
    return text.split("/")[-1]


def _project_by_uri(sb: Any, project_uri: str) -> dict[str, Any]:
    uri = _normalize_uri(project_uri)
    if not uri:
        return {}
    rows = (
        sb.table("projects")
        .select("id,v_uri,name,enterprise_id")
        .eq("v_uri", uri)
        .limit(1)
        .execute()
        .data
        or []
    )
    return _as_dict(rows[0]) if rows else {}


def _heuristic_classify(file_name: str, text_excerpt: str, mime_type: str) -> dict[str, Any]:
    blob = f"{_to_text(file_name).lower()} {_to_text(text_excerpt).lower()} {_to_text(mime_type).lower()}"
    doc_type = "general_document"
    discipline = "general"
    tags: list[str] = []

    if any(x in blob for x in ("dwg", "图纸", "cad", "平面图", "详图", "竣工图")):
        doc_type = "drawing"
        discipline = "design"
        tags.extend(["drawing", "design"])
    elif any(x in blob for x in ("试验", "lab", "jtg e", "抗压", "强度报告")):
        doc_type = "lab_test_report"
        discipline = "lab"
        tags.extend(["lab", "jtg-e"])
    elif any(x in blob for x in ("质检", "inspection", "qcspec", "检验批", "验收")):
        doc_type = "inspection_record"
        discipline = "quality"
        tags.extend(["inspection", "qcspec"])
    elif any(x in blob for x in ("合同", "agreement", "支付", "payment", "结算")):
        doc_type = "contract_or_payment"
        discipline = "commercial"
        tags.extend(["contract", "payment"])

    if any(x in blob for x in ("桥梁", "bridge", "403")):
        discipline = "bridge"
        tags.append("bridge")
    if any(x in blob for x in ("路基", "subgrade", "路面", "pavement")):
        discipline = "road"
        tags.append("road")

    summary_src = _to_text(text_excerpt).strip() or _to_text(file_name).strip()
    summary = summary_src[:180]
    dedup = []
    seen = set()
    for t in tags:
        if t not in seen:
            dedup.append(t)
            seen.add(t)
    return {
        "doc_type": doc_type,
        "discipline": discipline,
        "tags": dedup[:12],
        "summary": summary,
        "confidence": 0.72,
        "provider": "heuristic",
    }


async def auto_classify_document(
    *,
    file_name: str,
    text_excerpt: str,
    mime_type: str = "",
) -> dict[str, Any]:
    prompt = (
        "You are a document classifier for engineering archive governance. "
        "Return strict JSON with keys: doc_type, discipline, tags(array), summary, confidence. "
        f"file_name={file_name}\n"
        f"mime_type={mime_type}\n"
        f"text_excerpt={text_excerpt[:2000]}\n"
    )
    provider = _to_text(os.getenv("DOC_AI_PROVIDER") or "").strip().lower()
    timeout = float(_to_text(os.getenv("DOC_AI_TIMEOUT") or "20").strip() or "20")

    if provider == "qwen":
        base_url = _to_text(os.getenv("QWEN_BASE_URL") or "").strip()
        api_key = _to_text(os.getenv("QWEN_API_KEY") or "").strip()
        model = _to_text(os.getenv("QWEN_MODEL") or "qwen-plus").strip()
        if base_url and api_key:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    res = await client.post(
                        f"{base_url.rstrip('/')}/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": model,
                            "temperature": 0.1,
                            "messages": [
                                {"role": "system", "content": "Return JSON only."},
                                {"role": "user", "content": prompt},
                            ],
                        },
                    )
                    if res.status_code < 400:
                        content = _to_text(
                            _as_dict(_as_list(_as_dict(res.json()).get("choices"))[0]).get("message", {}).get("content")
                        ).strip()
                        parsed = _as_dict(json.loads(content))
                        if parsed:
                            parsed["provider"] = "qwen"
                            return parsed
            except Exception:
                pass

    if provider == "claude":
        api_key = _to_text(os.getenv("ANTHROPIC_API_KEY") or "").strip()
        model = _to_text(os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022").strip()
        if api_key:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    res = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": model,
                            "max_tokens": 400,
                            "temperature": 0.1,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )
                    if res.status_code < 400:
                        content_blocks = _as_list(_as_dict(res.json()).get("content"))
                        content = _to_text(_as_dict(content_blocks[0]).get("text") if content_blocks else "").strip()
                        parsed = _as_dict(json.loads(content))
                        if parsed:
                            parsed["provider"] = "claude"
                            return parsed
            except Exception:
                pass

    return _heuristic_classify(file_name=file_name, text_excerpt=text_excerpt, mime_type=mime_type)


def create_node(
    *,
    sb: Any,
    project_uri: str,
    parent_uri: str,
    node_name: str,
    executor_uri: str = "v://executor/system/",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proj_uri = _normalize_uri(project_uri)
    parent = _normalize_uri(parent_uri or proj_uri)
    if not parent.startswith(proj_uri):
        raise HTTPException(409, "parent_uri must be within project_uri")
    node_uri = _join_node_uri(parent, node_name)
    proof_seed = _sha256_json({"project_uri": proj_uri, "node_uri": node_uri, "ts": _utc_iso()})
    proof_id = f"GP-NODE-{proof_seed[:16].upper()}"
    proj = _project_by_uri(sb, proj_uri)
    node_state = {
        "artifact_type": "doc_node",
        "node_registry": True,
        "node_uri": node_uri,
        "parent_uri": parent,
        "node_name": _safe_token(node_name),
        "node_kind": "folder",
        "metadata": _as_dict(metadata),
        "created_at": _utc_iso(),
    }
    engine = ProofUTXOEngine(sb)
    create_kwargs = {
        "proof_id": proof_id,
        "owner_uri": _to_text(executor_uri).strip() or "v://executor/system/",
        "project_uri": proj_uri,
        "project_id": proj.get("id"),
        "result": "PASS",
        "state_data": node_state,
        "conditions": [],
        "parent_proof_id": None,
        "norm_uri": "v://norm/CoordOS/DocNode/1.0#create",
        "segment_uri": node_uri,
        "signer_uri": _to_text(executor_uri).strip() or "v://executor/system/",
        "signer_role": "DOCPEG",
    }
    try:
        row = engine.create(proof_type="node", **create_kwargs)
    except Exception as exc:
        if not _is_proof_type_constraint_error(exc):
            raise
        row = engine.create(proof_type="archive", **create_kwargs)
    return {
        "ok": True,
        "node_uri": node_uri,
        "proof_id": _to_text(row.get("proof_id")).strip(),
        "proof_hash": _to_text(row.get("proof_hash")).strip(),
    }


def auto_generate_stake_nodes(
    *,
    sb: Any,
    project_uri: str,
    parent_uri: str,
    start_km: int,
    end_km: int,
    step_km: int = 1,
    leaf_name: str = "inspection",
    executor_uri: str = "v://executor/system/",
) -> dict[str, Any]:
    if step_km <= 0:
        raise HTTPException(400, "step_km must be > 0")
    if end_km < start_km:
        raise HTTPException(400, "end_km must be >= start_km")
    created: list[dict[str, Any]] = []
    root = create_node(
        sb=sb,
        project_uri=project_uri,
        parent_uri=parent_uri,
        node_name=f"K{start_km}~K{end_km}",
        executor_uri=executor_uri,
        metadata={"generated": "auto_stake"},
    )
    created.append(root)
    range_root = _to_text(root.get("node_uri")).strip()
    for km in range(start_km, end_km + 1, step_km):
        km_node = create_node(
            sb=sb,
            project_uri=project_uri,
            parent_uri=range_root,
            node_name=f"K{km}",
            executor_uri=executor_uri,
            metadata={"generated": "auto_stake_point"},
        )
        created.append(km_node)
        leaf = create_node(
            sb=sb,
            project_uri=project_uri,
            parent_uri=_to_text(km_node.get("node_uri")).strip(),
            node_name=leaf_name or "inspection",
            executor_uri=executor_uri,
            metadata={"generated": "auto_stake_leaf"},
        )
        created.append(leaf)
    return {"ok": True, "created_count": len(created), "created": created}


def _collect_uris(project_uri: str, rows: list[dict[str, Any]]) -> set[str]:
    root = _normalize_uri(project_uri)
    uris: set[str] = {root}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sd = _as_dict(row.get("state_data"))
        node_uri = _to_text(sd.get("node_uri") or "").strip()
        if node_uri.startswith("v://") and node_uri.startswith(root):
            uris.add(_normalize_uri(node_uri))
        segment_uri = _to_text(row.get("segment_uri") or "").strip()
        if segment_uri.startswith("v://") and segment_uri.startswith(root):
            uris.add(_normalize_uri(segment_uri))
    expanded: set[str] = set()
    for uri in list(uris):
        expanded.add(uri)
        path = uri[len(root):].strip("/")
        if not path:
            continue
        cur = root
        for part in path.split("/"):
            cur = _normalize_uri(f"{cur.rstrip('/')}/{part}/")
            expanded.add(cur)
    return expanded


def list_node_tree(
    *,
    sb: Any,
    project_uri: str,
    root_uri: str = "",
) -> dict[str, Any]:
    proj_uri = _normalize_uri(project_uri)
    root = _normalize_uri(root_uri or proj_uri)
    if not root.startswith(proj_uri):
        raise HTTPException(409, "root_uri must be inside project_uri")
    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", proj_uri)
        .order("created_at", desc=False)
        .limit(20000)
        .execute()
        .data
        or []
    )
    all_uris = sorted([u for u in _collect_uris(proj_uri, rows) if u.startswith(root)])
    files_by_node: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_document_row(row):
            continue
        sd = _as_dict(row.get("state_data"))
        node_uri = _normalize_uri(_to_text(sd.get("node_uri") or "").strip() or _to_text(row.get("segment_uri") or "").strip() or proj_uri)
        files_by_node[node_uri] = files_by_node.get(node_uri, 0) + 1
    nodes: dict[str, dict[str, Any]] = {}
    for uri in all_uris:
        parent = _parent_uri(uri, proj_uri)
        nodes[uri] = {
            "uri": uri,
            "parent_uri": parent,
            "name": _node_name(uri) if uri != proj_uri else "project_root",
            "children": [],
            "file_count": int(files_by_node.get(uri, 0)),
        }
    for uri, node in nodes.items():
        parent = _to_text(node.get("parent_uri")).strip()
        if parent and parent in nodes and parent != uri:
            nodes[parent]["children"].append(uri)
    for node in nodes.values():
        node["children"].sort()
        node["children_count"] = len(node["children"])
    return {
        "ok": True,
        "project_uri": proj_uri,
        "root_uri": root,
        "nodes": [nodes[k] for k in sorted(nodes.keys())],
    }


def _insert_doc_tags(
    *,
    sb: Any,
    proof_id: str,
    project_uri: str,
    node_uri: str,
    tags: list[str],
    metadata: dict[str, Any],
) -> None:
    cleaned = []
    seen = set()
    for t in tags:
        token = _to_text(t).strip()
        if not token or token in seen:
            continue
        cleaned.append(token[:80])
        seen.add(token)
    if not cleaned:
        return
    rows = [
        {
            "proof_id": proof_id,
            "project_uri": project_uri,
            "node_uri": node_uri,
            "tag": tag,
            "tag_type": "document",
            "metadata": metadata or {},
        }
        for tag in cleaned
    ]
    try:
        sb.table("doc_tags").insert(rows).execute()
    except Exception:
        # migration may not be applied yet, keep proof registration non-blocking
        pass


def register_document(
    *,
    sb: Any,
    project_uri: str,
    node_uri: str,
    source_utxo_id: str,
    file_name: str,
    file_size: int,
    mime_type: str,
    storage_path: str,
    storage_url: str,
    text_excerpt: str = "",
    ai_metadata: dict[str, Any] | None = None,
    custom_metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    executor_uri: str = "v://executor/system/",
    trip_action: str = "",
    lifecycle_stage: str = "",
    trip_payload: dict[str, Any] | None = None,
    doc_spec: dict[str, Any] | None = None,
    dtorole_context: str = "",
) -> dict[str, Any]:
    proj_uri = _normalize_uri(project_uri)
    n_uri = _normalize_uri(node_uri or proj_uri)
    src_id = _to_text(source_utxo_id).strip()
    if not n_uri.startswith(proj_uri):
        raise HTTPException(409, "node_uri must be inside project_uri")
    if not src_id:
        raise HTTPException(400, "source_utxo_id is required")
    if not _to_text(file_name).strip():
        raise HTTPException(400, "file_name is required")

    proj = _project_by_uri(sb, proj_uri)
    source_row = ProofUTXOEngine(sb).get_by_id(src_id)
    if not isinstance(source_row, dict):
        raise HTTPException(404, "source_utxo_id not found")
    source_project_uri = _normalize_uri(_to_text(source_row.get("project_uri") or "").strip() or proj_uri)
    if source_project_uri != proj_uri:
        raise HTTPException(409, "source_utxo_id does not belong to project_uri")
    source_sd = _as_dict(source_row.get("state_data"))
    source_boq_item_uri = _to_text(
        source_sd.get("boq_item_uri")
        or source_sd.get("item_uri")
        or source_sd.get("boq_uri")
        or source_row.get("segment_uri")
        or ""
    ).strip()
    if source_boq_item_uri and not source_boq_item_uri.startswith("v://"):
        source_boq_item_uri = ""
    source_item_no = _to_text(source_sd.get("item_no") or "").strip()
    segment_uri = source_boq_item_uri or n_uri

    ai_meta = _as_dict(ai_metadata)
    cus_meta = _as_dict(custom_metadata)
    merged_tags = list(_as_list(tags))
    merged_tags.extend(_as_list(ai_meta.get("tags")))
    merged_tags = [_to_text(x).strip() for x in merged_tags if _to_text(x).strip()]
    fingerprint = _sha256_json(
        {
            "project_uri": proj_uri,
            "node_uri": n_uri,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
            "storage_path": storage_path,
            "text_excerpt": text_excerpt[:2000],
            "ai_metadata": ai_meta,
            "custom_metadata": cus_meta,
            "source_utxo_id": src_id,
            "source_boq_item_uri": source_boq_item_uri,
            "source_item_no": source_item_no,
            "ts": _utc_iso(),
        }
    )
    proof_id = f"GP-DOC-{fingerprint[:16].upper()}"
    state_data = {
        "artifact_type": "governance_document",
        "doc_registry": True,
        "node_uri": n_uri,
        "file_name": _to_text(file_name).strip(),
        "file_size": int(max(file_size, 0)),
        "mime_type": _to_text(mime_type).strip(),
        "storage_path": _to_text(storage_path).strip(),
        "storage_url": _to_text(storage_url).strip(),
        "text_excerpt": _to_text(text_excerpt).strip()[:2000],
        "ai_metadata": ai_meta,
        "custom_metadata": cus_meta,
        "source_utxo_id": src_id,
        "source_boq_item_uri": source_boq_item_uri,
        "source_item_no": source_item_no,
        "tags": merged_tags[:30],
        "doc_type": _to_text(ai_meta.get("doc_type") or "").strip(),
        "discipline": _to_text(ai_meta.get("discipline") or "").strip(),
        "summary": _to_text(ai_meta.get("summary") or "").strip(),
        "uploaded_at": _utc_iso(),
        "proof_fingerprint": fingerprint,
    }
    docpeg_specir_v1_1 = build_docpeg_specir_v11(
        project_uri=proj_uri,
        node_uri=n_uri,
        source_utxo_id=src_id,
        file_name=file_name,
        mime_type=mime_type,
        storage_url=storage_url,
        text_excerpt=text_excerpt,
        ai_metadata=ai_meta,
        custom_metadata={**cus_meta, "docpeg_specir_v1_1": _as_dict(doc_spec)},
        tags=merged_tags[:30],
        lifecycle_stage=lifecycle_stage,
        trigger_event=trip_action or "document.register",
        created_at=_to_text(state_data.get("uploaded_at")).strip(),
        jurisdiction=_to_text(cus_meta.get("jurisdiction")).strip(),
        proof_hash=fingerprint,
        trip_role=trip_action,
        dtorole_context=_to_text(dtorole_context).strip() or _to_text(cus_meta.get("dtorole_context") or cus_meta.get("dto_role")).strip(),
        trip_context={
            "executed_by": _to_text(executor_uri).strip() or "v://executor/system/",
            "executed_at": _to_text(state_data.get("uploaded_at")).strip(),
            "input": _as_dict(trip_payload),
            "output": {"status": "registered"},
        },
        required_trip_roles=_as_list(cus_meta.get("required_trip_roles")),
        dtorole_permissions=_as_dict(cus_meta.get("dtorole_permissions")),
        dtorole_proof=_as_dict(cus_meta.get("dtorole_proof")),
        dtorole_state=_as_dict(cus_meta.get("dtorole_state")),
    )
    state_data["docpeg_specir_v1_1"] = docpeg_specir_v1_1
    if _to_text(trip_action).strip():
        state_data["trip_action"] = _to_text(trip_action).strip()
    if _to_text(lifecycle_stage).strip():
        state_data["lifecycle_stage"] = _to_text(lifecycle_stage).strip()
    if isinstance(trip_payload, dict) and trip_payload:
        state_data["trip"] = trip_payload

    engine = ProofUTXOEngine(sb)
    create_kwargs = {
        "proof_id": proof_id,
        "owner_uri": _to_text(executor_uri).strip() or "v://executor/system/",
        "project_uri": proj_uri,
        "project_id": proj.get("id"),
        "result": "PASS",
        "state_data": state_data,
        "conditions": [],
        "parent_proof_id": src_id,
        "norm_uri": "v://norm/CoordOS/DocGovernance/1.0#document_register",
        "segment_uri": segment_uri,
        "signer_uri": _to_text(executor_uri).strip() or "v://executor/system/",
        "signer_role": "DOCPEG",
    }
    proof_type_used = "document"
    try:
        row = engine.create(proof_type=proof_type_used, **create_kwargs)
    except Exception as exc:
        if not _is_proof_type_constraint_error(exc):
            raise
        # Backward-compatible fallback for deployments where `document`
        # is not yet allowed by proof_utxo_proof_type_check.
        proof_type_used = "archive"
        row = engine.create(proof_type=proof_type_used, **create_kwargs)
    final_proof_hash = _to_text(row.get("proof_hash")).strip()
    if final_proof_hash:
        state_data["docpeg_specir_v1_1"] = _as_dict(state_data.get("docpeg_specir_v1_1"))
        _as_dict(state_data["docpeg_specir_v1_1"]).setdefault("proof", {})
        _as_dict(_as_dict(state_data["docpeg_specir_v1_1"]).get("proof"))["proof_hash"] = final_proof_hash
        _as_dict(_as_dict(state_data["docpeg_specir_v1_1"]).get("proof"))["trip_proof_hash"] = final_proof_hash
        try:
            sb.table("proof_utxo").update({"state_data": state_data}).eq("proof_id", _to_text(row.get("proof_id")).strip()).execute()
        except Exception:
            pass
    doc_view = project_docpeg_specir_v11_for_role(
        spec=_as_dict(state_data.get("docpeg_specir_v1_1")),
        dto_role=_to_text(dtorole_context).strip() or _to_text(cus_meta.get("dtorole_context") or cus_meta.get("dto_role")).strip() or "OWNER",
    )
    _insert_doc_tags(
        sb=sb,
        proof_id=_to_text(row.get("proof_id")).strip(),
        project_uri=proj_uri,
        node_uri=n_uri,
        tags=merged_tags,
        metadata={"doc_type": ai_meta.get("doc_type"), "discipline": ai_meta.get("discipline")},
    )
    return {
        "ok": True,
        "proof_id": _to_text(row.get("proof_id")).strip(),
        "proof_hash": _to_text(row.get("proof_hash")).strip(),
        "project_uri": proj_uri,
        "node_uri": n_uri,
        "source_utxo_id": src_id,
        "source_boq_item_uri": source_boq_item_uri,
        "file_name": _to_text(file_name).strip(),
        "storage_url": _to_text(storage_url).strip(),
        "proof_type": proof_type_used,
        "tags": merged_tags[:30],
        "docpeg_specir_v1_1": _as_dict(state_data.get("docpeg_specir_v1_1")),
        "docpeg_specir_v1_1_view": doc_view,
    }


def _filter_by_tags(sb: Any, proof_ids: list[str], tags: list[str]) -> set[str]:
    if not proof_ids or not tags:
        return set(proof_ids)
    cleaned = sorted({_to_text(t).strip() for t in tags if _to_text(t).strip()})
    if not cleaned:
        return set(proof_ids)
    try:
        rows = (
            sb.table("doc_tags")
            .select("proof_id,tag")
            .in_("proof_id", proof_ids[:10000])
            .in_("tag", cleaned)
            .limit(20000)
            .execute()
            .data
            or []
        )
    except Exception:
        return set(proof_ids)
    by_proof: dict[str, set[str]] = {}
    for row in rows:
        d = _as_dict(row)
        pid = _to_text(d.get("proof_id")).strip()
        tag = _to_text(d.get("tag")).strip()
        if not pid or not tag:
            continue
        by_proof.setdefault(pid, set()).add(tag)
    out = set()
    expected = set(cleaned)
    for pid, found in by_proof.items():
        if expected.issubset(found):
            out.add(pid)
    return out


def search_documents(
    *,
    sb: Any,
    project_uri: str,
    node_uri: str = "",
    include_descendants: bool = True,
    query: str = "",
    tags: list[str] | None = None,
    field_filters: dict[str, Any] | None = None,
    limit: int = 200,
    dto_role: str = "",
) -> dict[str, Any]:
    proj_uri = _normalize_uri(project_uri)
    node = _normalize_uri(node_uri or proj_uri)
    if not node.startswith(proj_uri):
        raise HTTPException(409, "node_uri must be inside project_uri")
    rows = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", proj_uri)
        .in_("proof_type", ["document", "archive"])
        .order("created_at", desc=True)
        .limit(20000)
        .execute()
        .data
        or []
    )
    q = _to_text(query).strip().lower()
    filters = _as_dict(field_filters)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_document_row(row):
            continue
        sd = _as_dict(row.get("state_data"))
        n_uri = _normalize_uri(_to_text(sd.get("node_uri") or row.get("segment_uri") or proj_uri))
        if include_descendants:
            if not n_uri.startswith(node):
                continue
        else:
            if n_uri != node:
                continue
        if q:
            blob = " ".join(
                [
                    _to_text(sd.get("file_name")).lower(),
                    _to_text(sd.get("summary")).lower(),
                    _to_text(sd.get("text_excerpt")).lower(),
                    " ".join([_to_text(x).lower() for x in _as_list(sd.get("tags"))]),
                ]
            )
            if q not in blob:
                continue
        passed_fields = True
        for key, expected in filters.items():
            if key in sd:
                actual = sd.get(key)
            else:
                actual = _as_dict(sd.get("custom_metadata")).get(key)
            if _to_text(actual).strip() != _to_text(expected).strip():
                passed_fields = False
                break
        if not passed_fields:
            continue
        filtered.append(row)

    proof_ids = [_to_text(r.get("proof_id")).strip() for r in filtered if _to_text(r.get("proof_id")).strip()]
    tag_filtered_ids = _filter_by_tags(sb, proof_ids, _as_list(tags or []))
    if tag_filtered_ids and tags:
        filtered = [r for r in filtered if _to_text(r.get("proof_id")).strip() in tag_filtered_ids]
    filtered = filtered[: max(1, min(int(limit or 200), 2000))]
    cards = []
    for row in filtered:
        sd = _as_dict(row.get("state_data"))
        doc_spec = _as_dict(sd.get("docpeg_specir_v1_1"))
        doc_view = project_docpeg_specir_v11_for_role(spec=doc_spec, dto_role=dto_role or "PUBLIC") if doc_spec else {}
        cards.append(
            {
                "proof_id": _to_text(row.get("proof_id")).strip(),
                "proof_hash": _to_text(row.get("proof_hash")).strip(),
                "created_at": _to_text(row.get("created_at")).strip(),
                "node_uri": _normalize_uri(_to_text(sd.get("node_uri") or row.get("segment_uri") or proj_uri)),
                "file_name": _to_text(sd.get("file_name")).strip(),
                "mime_type": _to_text(sd.get("mime_type")).strip(),
                "file_size": int(_to_text(sd.get("file_size") or "0") or "0"),
                "storage_url": _to_text(sd.get("storage_url")).strip(),
                "doc_type": _to_text(sd.get("doc_type")).strip(),
                "discipline": _to_text(sd.get("discipline")).strip(),
                "summary": _to_text(sd.get("summary")).strip(),
                "tags": _as_list(sd.get("tags")),
                "state_data": sd,
                "docpeg_specir_v1_1": doc_spec,
                "docpeg_specir_v1_1_view": doc_view,
            }
        )
    return {
        "ok": True,
        "project_uri": proj_uri,
        "node_uri": node,
        "dto_role": _to_text(dto_role).strip().upper() or "PUBLIC",
        "count": len(cards),
        "cards": cards,
    }
