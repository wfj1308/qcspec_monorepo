"""SMU-domain integration entry points."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _smu_flow_module() -> Any:
    return import_module("services.api.smu_flow_service")


def _smu_import_job_module() -> Any:
    return import_module("services.api.smu_import_job_service")


def import_genesis_trip(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().import_genesis_trip(*args, **kwargs)


def preview_genesis_tree(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().preview_genesis_tree(*args, **kwargs)


def list_spu_template_library(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().list_spu_template_library(*args, **kwargs)


def get_governance_context(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().get_governance_context(*args, **kwargs)


def execute_smu_trip(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().execute_smu_trip(*args, **kwargs)


def sign_smu_approval(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().sign_smu_approval(*args, **kwargs)


def validate_logic(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().validate_logic(*args, **kwargs)


def freeze_smu(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().freeze_smu(*args, **kwargs)


def retry_erpnext_push_queue_smu(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_flow_module().retry_erpnext_push_queue(*args, **kwargs)


def start_smu_import_job(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_import_job_module().start_smu_import_job(*args, **kwargs)


def get_smu_import_job(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_import_job_module().get_smu_import_job(*args, **kwargs)


def get_active_smu_import_job(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _smu_import_job_module().get_active_smu_import_job(*args, **kwargs)

__all__ = [
    "import_genesis_trip",
    "preview_genesis_tree",
    "start_smu_import_job",
    "get_smu_import_job",
    "get_active_smu_import_job",
    "list_spu_template_library",
    "get_governance_context",
    "execute_smu_trip",
    "sign_smu_approval",
    "validate_logic",
    "freeze_smu",
    "retry_erpnext_push_queue_smu",
]
