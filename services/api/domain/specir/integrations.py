"""Integration boundary for SpecIR domain helpers."""

from __future__ import annotations

from typing import Any

from services.api.core.docpeg.normref.ports import NormRefResolverPort
from services.api.domain.specir.runtime import (
    BUILTIN_QCSPEC_FULL_SPU_LIBRARY,
    BUILTIN_QCSPEC_SPECIR_CATALOG,
    SPUUltimateSchema,
    ProjectBOQItem,
    StandardSPU,
    build_specir_ref_uri,
    build_project_boq_item_ref,
    build_spu_ultimate_content,
    ensure_specir_object,
    get_specir_object,
    is_spu_ultimate_content,
    list_builtin_qcspec_specir_catalog,
    list_builtin_qcspec_full_spu_library,
    list_specir_spu_library,
    normalize_spu_content,
    seed_builtin_qcspec_full_spu_library,
    seed_builtin_qcspec_specir_catalog,
    specir_is_ready,
    SpecIRCompiler,
    compile_specir_process_chain,
    resolve_spu_ref_pack,
    resolve_standard_spu_snapshot,
    collect_ref_uris_from_state_data,
    infer_specir_kind,
    register_missing_specir_refs_from_rows,
    upsert_specir_object,
    validate_spu_content,
)


def list_builtin_specir_catalog(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return list_builtin_qcspec_specir_catalog()


def seed_builtin_specir_catalog(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return seed_builtin_qcspec_specir_catalog(*args, **kwargs)


def list_builtin_full_spu_library(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return list_builtin_qcspec_full_spu_library()


def seed_builtin_full_spu_library(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return seed_builtin_qcspec_full_spu_library(*args, **kwargs)


def seed_specir_baseline(
    *,
    sb: Any,
    overwrite: bool = False,
    include_full_spu: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = seed_builtin_qcspec_specir_catalog(sb=sb, overwrite=overwrite, metadata=metadata)
    details = {"base_catalog": base}
    saved_total = int(base.get("saved_count") or 0)
    error_total = int(base.get("error_count") or 0)
    if include_full_spu:
        full = seed_builtin_qcspec_full_spu_library(sb=sb, overwrite=overwrite, metadata=metadata)
        details["full_spu_library"] = full
        saved_total += int(full.get("saved_count") or 0)
        error_total += int(full.get("error_count") or 0)
    return {
        "ok": error_total == 0,
        "saved_count": saved_total,
        "error_count": error_total,
        "details": details,
    }


def list_spu_library(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return list_specir_spu_library(*args, **kwargs)


class SpecirNormRefResolverAdapter(NormRefResolverPort):
    """Domain adapter for NormRef kernel resolver port."""

    def resolve_threshold(self, *, sb: Any, gate_id: str, context: Any = "") -> dict[str, Any]:
        from services.api.domain.boq.runtime.specdict_gate import resolve_dynamic_threshold

        return resolve_dynamic_threshold(sb=sb, gate_id=gate_id, context=context)

    def get_spec_dict(self, *, sb: Any, spec_dict_key: str) -> dict[str, Any]:
        from services.api.domain.boq.runtime.specdict_gate import get_spec_dict

        return get_spec_dict(sb=sb, spec_dict_key=spec_dict_key)


__all__ = [
    "BUILTIN_QCSPEC_FULL_SPU_LIBRARY",
    "BUILTIN_QCSPEC_SPECIR_CATALOG",
    "SPUUltimateSchema",
    "ProjectBOQItem",
    "StandardSPU",
    "build_specir_ref_uri",
    "build_project_boq_item_ref",
    "build_spu_ultimate_content",
    "ensure_specir_object",
    "get_specir_object",
    "is_spu_ultimate_content",
    "list_builtin_specir_catalog",
    "list_builtin_full_spu_library",
    "list_spu_library",
    "normalize_spu_content",
    "seed_builtin_full_spu_library",
    "seed_builtin_specir_catalog",
    "seed_specir_baseline",
    "SpecirNormRefResolverAdapter",
    "SpecIRCompiler",
    "compile_specir_process_chain",
    "resolve_spu_ref_pack",
    "resolve_standard_spu_snapshot",
    "collect_ref_uris_from_state_data",
    "infer_specir_kind",
    "register_missing_specir_refs_from_rows",
    "specir_is_ready",
    "upsert_specir_object",
    "validate_spu_content",
]
