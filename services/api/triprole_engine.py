"""Compatibility layer for TripRole runtime execution helpers.

Canonical implementation lives in
``services.api.domain.execution.runtime.triprole_engine``.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Any

VALID_TRIPROLE_ACTIONS = {
    "quality.check",
    "measure.record",
    "variation.record",
    "settlement.confirm",
    "dispute.resolve",
    "scan.entry",
    "meshpeg.verify",
    "formula.price",
    "gateway.sync",
}
CONSENSUS_REQUIRED_ROLES = ("contractor", "supervisor", "owner")


@lru_cache(maxsize=1)
def _runtime_module() -> Any:
    return import_module("services.api.domain.execution.runtime.triprole_engine")


def _build_docfinal_package_for_boq_runtime(**kwargs: Any) -> dict[str, Any]:
    return _runtime_module()._build_docfinal_package_for_boq_runtime(**kwargs)


def aggregate_provenance_chain(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().aggregate_provenance_chain(*args, **kwargs)


def aggregate_chain(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().aggregate_chain(*args, **kwargs)


def get_full_lineage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().get_full_lineage(*args, **kwargs)


def trace_asset_origin(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().trace_asset_origin(*args, **kwargs)


def transfer_asset(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().transfer_asset(*args, **kwargs)


def ingest_sensor_data(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().ingest_sensor_data(*args, **kwargs)


def apply_variation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().apply_variation(*args, **kwargs)


def execute_triprole_action(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().execute_triprole_action(*args, **kwargs)


def replay_offline_packets(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().replay_offline_packets(*args, **kwargs)


def scan_to_confirm_signature(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().scan_to_confirm_signature(*args, **kwargs)


def get_boq_realtime_status(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().get_boq_realtime_status(*args, **kwargs)


def export_doc_final(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_module().export_doc_final(*args, **kwargs)


def build_docfinal_package_for_boq(
    *,
    boq_item_uri: str,
    sb: Any,
    project_meta: dict[str, Any] | None = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: str | Path | None = None,
    apply_asset_transfer: bool = False,
    transfer_amount: float | None = None,
    transfer_executor_uri: str = "v://executor/system/",
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
) -> dict[str, Any]:
    return _build_docfinal_package_for_boq_runtime(
        boq_item_uri=boq_item_uri,
        sb=sb,
        project_meta=project_meta,
        verify_base_url=verify_base_url,
        template_path=template_path,
        apply_asset_transfer=apply_asset_transfer,
        transfer_amount=transfer_amount,
        transfer_executor_uri=transfer_executor_uri,
        aggregate_anchor_code=aggregate_anchor_code,
        aggregate_direction=aggregate_direction,
        aggregate_level=aggregate_level,
        module_file=__file__,
        get_boq_realtime_status_fn=get_boq_realtime_status,
        get_full_lineage_fn=get_full_lineage,
        trace_asset_origin_fn=trace_asset_origin,
        transfer_asset_fn=transfer_asset,
    )


__all__ = [
    "VALID_TRIPROLE_ACTIONS",
    "CONSENSUS_REQUIRED_ROLES",
    "aggregate_provenance_chain",
    "aggregate_chain",
    "get_full_lineage",
    "trace_asset_origin",
    "transfer_asset",
    "ingest_sensor_data",
    "apply_variation",
    "execute_triprole_action",
    "replay_offline_packets",
    "scan_to_confirm_signature",
    "build_docfinal_package_for_boq",
    "get_boq_realtime_status",
    "export_doc_final",
]
