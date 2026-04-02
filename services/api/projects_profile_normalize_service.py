"""Compatibility shim for legacy project profile normalization imports.

Prefer importing from ``services.api.domain.projects.profile_normalize`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.profile_normalize import (
    VALID_DTO_ROLES,
    VALID_INSPECTION_TYPES,
    VALID_PERM_TEMPLATES,
    VALID_SEG_TYPES,
    VALID_ZERO_SIGN_STATUS,
    normalize_contract_segs,
    normalize_inspection_types,
    normalize_km_interval,
    normalize_perm_template,
    normalize_seg_type,
    normalize_structures,
    normalize_zero_equipment,
    normalize_zero_materials,
    normalize_zero_personnel,
    normalize_zero_sign_status,
    normalize_zero_subcontracts,
)

_normalize_seg_type = normalize_seg_type
_normalize_perm_template = normalize_perm_template
_normalize_km_interval = normalize_km_interval
_normalize_inspection_types = normalize_inspection_types
_normalize_contract_segs = normalize_contract_segs
_normalize_structures = normalize_structures
_normalize_zero_sign_status = normalize_zero_sign_status
_normalize_zero_personnel = normalize_zero_personnel
_normalize_zero_equipment = normalize_zero_equipment
_normalize_zero_subcontracts = normalize_zero_subcontracts
_normalize_zero_materials = normalize_zero_materials

__all__ = [
    "VALID_SEG_TYPES",
    "VALID_PERM_TEMPLATES",
    "VALID_INSPECTION_TYPES",
    "VALID_DTO_ROLES",
    "VALID_ZERO_SIGN_STATUS",
    "normalize_seg_type",
    "normalize_perm_template",
    "normalize_km_interval",
    "normalize_inspection_types",
    "normalize_contract_segs",
    "normalize_structures",
    "normalize_zero_sign_status",
    "normalize_zero_personnel",
    "normalize_zero_equipment",
    "normalize_zero_subcontracts",
    "normalize_zero_materials",
    "_normalize_seg_type",
    "_normalize_perm_template",
    "_normalize_km_interval",
    "_normalize_inspection_types",
    "_normalize_contract_segs",
    "_normalize_structures",
    "_normalize_zero_sign_status",
    "_normalize_zero_personnel",
    "_normalize_zero_equipment",
    "_normalize_zero_subcontracts",
    "_normalize_zero_materials",
]
