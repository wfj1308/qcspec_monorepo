"""Genesis-phase helper functions for SMU flow orchestration."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.boq.runtime.utxo import initialize_boq_utxos
from services.api.domain.smu.runtime.smu_primitives import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)


def resolve_genesis_roots(
    *,
    project_uri: str,
    boq_root_uri: str,
    norm_context_root_uri: str,
) -> tuple[str, str]:
    p_uri = _to_text(project_uri).strip()
    root_uri = _to_text(boq_root_uri).strip() or f"{p_uri.rstrip('/')}/boq/400"
    norm_root = _to_text(norm_context_root_uri).strip() or f"{p_uri.rstrip('/')}/normContext"
    return root_uri, norm_root


def initialize_genesis_chain(
    *,
    sb: Any,
    project_uri: str,
    project_id: str,
    boq_items: list[dict[str, Any]],
    root_uri: str,
    norm_root: str,
    owner_uri: str,
    upload_file_name: str,
    commit: bool,
) -> dict[str, Any]:
    return initialize_boq_utxos(
        sb=sb,
        project_uri=project_uri,
        project_id=_to_text(project_id).strip() or None,
        boq_items=boq_items,
        boq_root_uri=root_uri,
        norm_context_root_uri=norm_root,
        owner_uri=_to_text(owner_uri).strip() or f"{project_uri.rstrip('/')}/role/system/",
        source_file=upload_file_name,
        commit=bool(commit),
    )


def enrich_genesis_preview_rows(
    *,
    result: dict[str, Any],
    upload_file_name: str,
    owner_uri: str,
    build_genesis_enrichment_patch: Callable[..., dict[str, Any]],
) -> None:
    for row in _as_list(result.get("preview")):
        sd = _as_dict(row.get("state_data"))
        code = _to_text(sd.get("item_no") or "").strip()
        name = _to_text(sd.get("item_name") or "").strip()
        patch = build_genesis_enrichment_patch(
            code=code,
            name=name,
            sd=sd,
            upload_file_name=upload_file_name,
            owner_uri=owner_uri,
        )
        sd.update(patch)
        row["state_data"] = sd


def persist_genesis_created_enrichment(
    *,
    sb: Any,
    result: dict[str, Any],
    upload_file_name: str,
    owner_uri: str,
    build_genesis_enrichment_patch: Callable[..., dict[str, Any]],
    patch_state_data: Callable[[Any, str, dict[str, Any]], dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    persist_failed_streak = 0
    for created in _as_list(result.get("created")):
        pid = _to_text(created.get("proof_id") or "").strip()
        sd = _as_dict(created.get("state_data"))
        code = _to_text(sd.get("item_no") or "").strip()
        name = _to_text(sd.get("item_name") or "").strip()
        patch = build_genesis_enrichment_patch(
            code=code,
            name=name,
            sd=sd,
            upload_file_name=upload_file_name,
            owner_uri=owner_uri,
        )
        merged_state = dict(sd)
        merged_state.update(patch)
        created["state_data"] = merged_state
        if not pid:
            continue
        if persist_failed_streak >= 3:
            warnings.append(
                {
                    "proof_id": pid,
                    "item_no": code,
                    "error": "persistence skipped after repeated connection failures",
                }
            )
            continue
        try:
            patch_state_data(sb, pid, patch)
            persist_failed_streak = 0
        except Exception as exc:
            persist_failed_streak += 1
            warnings.append(
                {
                    "proof_id": pid,
                    "item_no": code,
                    "error": f"{exc.__class__.__name__}: {exc}",
                }
            )
    return warnings


__all__ = [
    "enrich_genesis_preview_rows",
    "initialize_genesis_chain",
    "persist_genesis_created_enrichment",
    "resolve_genesis_roots",
]

