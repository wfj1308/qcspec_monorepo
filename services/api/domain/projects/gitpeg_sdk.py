"""Lightweight GitPeg SDK helpers for in-domain sovereign node registration."""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _slug_segment(value: Any) -> str:
    text = _to_text(value).strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "node"


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _project_code_from_uri(project_uri: str) -> str:
    tail = _to_text(project_uri).strip().rstrip("/").split("/")[-1]
    return _slug_segment(tail)


def _namespace_from_project_uri(project_uri: str) -> str:
    text = _to_text(project_uri).strip().rstrip("/")
    if not text.startswith("v://"):
        return "v://"
    parts = text.split("/")
    if len(parts) <= 3:
        return text + "/"
    return "/".join(parts[:-1]) + "/"


def _display_name_for_entity(*, identifier: str, metadata: dict[str, Any]) -> str:
    for key in ("name", "description", "title", "label"):
        text = _to_text((metadata or {}).get(key)).strip()
        if text:
            return text
    return identifier


def _upsert_node_meta(
    *,
    sb: Any,
    uri: str,
    parent_uri: str,
    entity_type: str,
    identifier: str,
    canonical_uri: str,
    scope: str,
    metadata: dict[str, Any],
    source_system: str,
    project_code: str,
) -> None:
    now = _utc_iso()
    payload = {
        "uri": uri,
        "parent_uri": parent_uri,
        "entity_type": entity_type,
        "identifier": identifier,
        "canonical_uri": canonical_uri,
        "scope": scope,
        "metadata": dict(metadata or {}),
        "source_system": source_system,
        "project_code": project_code,
        "updated_at": now,
        "created_at": now,
    }
    try:
        sb.table("coord_gitpeg_node_registry").upsert(payload, on_conflict="uri").execute()
    except Exception:
        return


def _upsert_uri_link(
    *,
    sb: Any,
    alias_uri: str,
    canonical_uri: str,
    link_type: str,
    metadata: dict[str, Any],
) -> None:
    now = _utc_iso()
    payload = {
        "alias_uri": alias_uri,
        "canonical_uri": canonical_uri,
        "link_type": link_type,
        "metadata": dict(metadata or {}),
        "updated_at": now,
        "created_at": now,
    }
    try:
        sb.table("coord_gitpeg_uri_links").upsert(payload, on_conflict="alias_uri,canonical_uri,link_type").execute()
    except Exception:
        return


def register_entity(
    *,
    sb: Any,
    entity_type: str,
    parent_uri: str,
    identifier: str,
    metadata: dict[str, Any] | None = None,
    source_system: str = "qcspec-boqpeg",
    commit: bool = False,
) -> dict[str, Any]:
    normalized_parent = _to_text(parent_uri).strip().rstrip("/")
    normalized_entity_type = _to_text(entity_type).strip().strip("/")
    normalized_identifier = _to_text(identifier).strip()
    if not normalized_parent.startswith("v://"):
        raise ValueError("parent_uri must start with v://")
    if not normalized_entity_type:
        raise ValueError("entity_type is required")
    if not normalized_identifier:
        raise ValueError("identifier is required")

    uri = f"{normalized_parent}/{normalized_entity_type}/{normalized_identifier}"
    namespace_uri = _namespace_from_project_uri(normalized_parent)
    project_code = _project_code_from_uri(normalized_parent)
    display_name = _display_name_for_entity(identifier=normalized_identifier, metadata=metadata or {})

    preview = {
        "ok": True,
        "uri": uri,
        "entity_type": normalized_entity_type,
        "parent_uri": normalized_parent,
        "identifier": normalized_identifier,
        "namespace_uri": namespace_uri,
        "project_code": project_code,
        "display_name": display_name,
        "metadata": dict(metadata or {}),
        "committed": False,
    }
    if not commit or sb is None:
        return preview

    now = _utc_iso()
    sb.table("coord_gitpeg_nodes").upsert(
        {
            "uri": uri,
            "uri_type": normalized_entity_type,
            "project_code": project_code,
            "display_name": display_name,
            "namespace_uri": namespace_uri,
            "source_system": source_system,
            "updated_at": now,
        },
        on_conflict="uri",
    ).execute()
    preview["committed"] = True
    return preview


def register_uri(
    *,
    sb: Any,
    uri: str,
    uri_type: str = "node",
    metadata: dict[str, Any] | None = None,
    source_system: str = "qcspec-boqpeg",
    commit: bool = False,
) -> dict[str, Any]:
    normalized_uri = _to_text(uri).strip().rstrip("/")
    normalized_type = _to_text(uri_type).strip() or "node"
    if not normalized_uri.startswith("v://"):
        raise ValueError("uri must start with v://")

    namespace_uri = _namespace_from_project_uri(normalized_uri)
    project_code = _project_code_from_uri(normalized_uri)
    display_name = _display_name_for_entity(identifier=normalized_uri.split("/")[-1], metadata=metadata or {})
    preview = {
        "ok": True,
        "uri": normalized_uri,
        "uri_type": normalized_type,
        "namespace_uri": namespace_uri,
        "project_code": project_code,
        "display_name": display_name,
        "metadata": dict(metadata or {}),
        "committed": False,
    }
    if not commit or sb is None:
        return preview

    now = _utc_iso()
    sb.table("coord_gitpeg_nodes").upsert(
        {
            "uri": normalized_uri,
            "uri_type": normalized_type,
            "project_code": project_code,
            "display_name": display_name,
            "namespace_uri": namespace_uri,
            "source_system": source_system,
            "updated_at": now,
        },
        on_conflict="uri",
    ).execute()
    preview["committed"] = True
    return preview


def register_boq_item(
    *,
    sb: Any,
    project_uri: str,
    identifier: str,
    metadata: dict[str, Any] | None = None,
    bridge_uri: str = "",
    source_system: str = "qcspec-boqpeg",
    commit: bool = False,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip().rstrip("/")
    boq_id = _to_text(identifier).strip()
    if not p_uri.startswith("v://"):
        raise ValueError("project_uri must start with v://")
    if not boq_id:
        raise ValueError("identifier is required")

    base_meta = dict(metadata or {})
    base_meta["boq_item_id"] = boq_id
    canonical = register_entity(
        sb=sb,
        entity_type="boq",
        parent_uri=p_uri,
        identifier=boq_id,
        metadata=base_meta,
        source_system=source_system,
        commit=bool(commit),
    )
    canonical_uri = _to_text(canonical.get("uri")).strip()

    full_line_alias = register_entity(
        sb=sb,
        entity_type="full-line/boq",
        parent_uri=p_uri,
        identifier=boq_id,
        metadata={**base_meta, "scope": "full_line"},
        source_system=source_system,
        commit=bool(commit),
    )

    bridge = _to_text(bridge_uri).strip().rstrip("/")
    bridge_alias_uri = ""
    bridge_alias: dict[str, Any] = {}
    if bridge.startswith("v://"):
        bridge_name = bridge.split("/")[-1]
        bridge_alias = register_entity(
            sb=sb,
            entity_type="boq",
            parent_uri=bridge,
            identifier=boq_id,
            metadata={**base_meta, "scope": "bridge", "bridge_uri": bridge, "bridge_name": bridge_name},
            source_system=source_system,
            commit=bool(commit),
        )
        bridge_alias_uri = _to_text(bridge_alias.get("uri")).strip()

    if commit and sb is not None:
        project_code = _project_code_from_uri(p_uri)
        _upsert_node_meta(
            sb=sb,
            uri=canonical_uri,
            parent_uri=p_uri,
            entity_type="boq_item",
            identifier=boq_id,
            canonical_uri=canonical_uri,
            scope="canonical",
            metadata=base_meta,
            source_system=source_system,
            project_code=project_code,
        )
        _upsert_node_meta(
            sb=sb,
            uri=_to_text(full_line_alias.get("uri")).strip(),
            parent_uri=p_uri,
            entity_type="boq_item_alias",
            identifier=boq_id,
            canonical_uri=canonical_uri,
            scope="full_line",
            metadata={**base_meta, "scope": "full_line"},
            source_system=source_system,
            project_code=project_code,
        )
        _upsert_uri_link(
            sb=sb,
            alias_uri=_to_text(full_line_alias.get("uri")).strip(),
            canonical_uri=canonical_uri,
            link_type="alias_of",
            metadata={"scope": "full_line", "boq_item_id": boq_id},
        )
        if bridge_alias_uri:
            _upsert_node_meta(
                sb=sb,
                uri=bridge_alias_uri,
                parent_uri=bridge,
                entity_type="boq_item_alias",
                identifier=boq_id,
                canonical_uri=canonical_uri,
                scope="bridge",
                metadata={**base_meta, "scope": "bridge", "bridge_uri": bridge},
                source_system=source_system,
                project_code=project_code,
            )
            _upsert_uri_link(
                sb=sb,
                alias_uri=bridge_alias_uri,
                canonical_uri=canonical_uri,
                link_type="alias_of",
                metadata={"scope": "bridge", "bridge_uri": bridge, "boq_item_id": boq_id},
            )

    return {
        "ok": True,
        "boq_item_id": boq_id,
        "project_uri": p_uri,
        "canonical_uri": canonical_uri,
        "full_line_uri": _to_text(full_line_alias.get("uri")).strip(),
        "bridge_uri": bridge,
        "bridge_scoped_uri": bridge_alias_uri,
        "metadata": base_meta,
        "registration": {
            "canonical": canonical,
            "full_line": full_line_alias,
            "bridge": bridge_alias,
        },
        "committed": bool(commit and sb is not None),
    }


__all__ = ["register_entity", "register_uri", "register_boq_item"]
