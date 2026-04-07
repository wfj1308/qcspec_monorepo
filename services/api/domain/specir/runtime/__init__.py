"""SpecIR runtime helpers."""

from services.api.domain.specir.runtime.catalog import (
    BUILTIN_QCSPEC_SPECIR_CATALOG,
    list_builtin_qcspec_specir_catalog,
    seed_builtin_qcspec_specir_catalog,
)
from services.api.domain.specir.runtime.refs import (
    resolve_spu_ref_pack,
)
from services.api.domain.specir.runtime.repair import (
    collect_ref_uris_from_state_data,
    infer_specir_kind,
    register_missing_specir_refs_from_rows,
)
from services.api.domain.specir.runtime.spu_schema import (
    SPUUltimateSchema,
    build_spu_ultimate_content,
    is_spu_ultimate_content,
    normalize_spu_content,
    validate_spu_content,
)
from services.api.domain.specir.runtime.spu_library import (
    BUILTIN_QCSPEC_FULL_SPU_LIBRARY,
    list_builtin_qcspec_full_spu_library,
    seed_builtin_qcspec_full_spu_library,
)
from services.api.domain.specir.runtime.query import (
    list_specir_spu_library,
)
from services.api.domain.specir.runtime.layering import (
    ProjectBOQItem,
    StandardSPU,
    build_project_boq_item_ref,
    resolve_standard_spu_snapshot,
)
from services.api.domain.specir.runtime.registry import (
    build_specir_ref_uri,
    ensure_specir_object,
    get_specir_object,
    specir_is_ready,
    upsert_specir_object,
)

__all__ = [
    "BUILTIN_QCSPEC_SPECIR_CATALOG",
    "build_specir_ref_uri",
    "ensure_specir_object",
    "get_specir_object",
    "list_builtin_qcspec_specir_catalog",
    "seed_builtin_qcspec_specir_catalog",
    "collect_ref_uris_from_state_data",
    "infer_specir_kind",
    "register_missing_specir_refs_from_rows",
    "resolve_spu_ref_pack",
    "ProjectBOQItem",
    "StandardSPU",
    "SPUUltimateSchema",
    "build_project_boq_item_ref",
    "build_spu_ultimate_content",
    "BUILTIN_QCSPEC_FULL_SPU_LIBRARY",
    "list_builtin_qcspec_full_spu_library",
    "seed_builtin_qcspec_full_spu_library",
    "list_specir_spu_library",
    "is_spu_ultimate_content",
    "normalize_spu_content",
    "validate_spu_content",
    "resolve_standard_spu_snapshot",
    "specir_is_ready",
    "upsert_specir_object",
]
