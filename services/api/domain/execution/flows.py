"""Canonical execution-domain flow entry points."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from services.api.domain.execution.integrations import (
    compute_did_reputation,
    calc_inspection_frequency,
    close_remediation_trip,
    get_frequency_dashboard,
    open_remediation_trip,
    record_lab_test,
    remediation_reinspect,
)

__all__ = [
    "execute_triprole_action",
    "aggregate_provenance_chain",
    "get_full_lineage",
    "trace_asset_origin",
    "get_boq_realtime_status",
    "build_docfinal_package_for_boq",
    "export_doc_final",
    "compute_did_reputation",
    "transfer_asset",
    "apply_variation",
    "replay_offline_packets",
    "scan_to_confirm_signature",
    "ingest_sensor_data",
    "record_lab_test",
    "calc_inspection_frequency",
    "get_frequency_dashboard",
    "open_remediation_trip",
    "remediation_reinspect",
    "close_remediation_trip",
]


def _triprole_engine_module() -> Any:
    return import_module("services.api.triprole_engine")


def execute_triprole_action(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().execute_triprole_action(*args, **kwargs)


def aggregate_provenance_chain(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().aggregate_provenance_chain(*args, **kwargs)


def get_full_lineage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().get_full_lineage(*args, **kwargs)


def trace_asset_origin(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().trace_asset_origin(*args, **kwargs)


def transfer_asset(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().transfer_asset(*args, **kwargs)


def apply_variation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().apply_variation(*args, **kwargs)


def replay_offline_packets(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().replay_offline_packets(*args, **kwargs)


def scan_to_confirm_signature(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().scan_to_confirm_signature(*args, **kwargs)


def ingest_sensor_data(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().ingest_sensor_data(*args, **kwargs)


def get_boq_realtime_status(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().get_boq_realtime_status(*args, **kwargs)


def build_docfinal_package_for_boq(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().build_docfinal_package_for_boq(*args, **kwargs)


def export_doc_final(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _triprole_engine_module().export_doc_final(*args, **kwargs)
