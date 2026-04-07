"""BOQPeg async import job wrappers (reusing existing SMU job engine)."""

from __future__ import annotations

from typing import Any


def start_boqpeg_import_job(
    *,
    upload_file_name: str,
    upload_content: bytes,
    project_uri: str,
    project_id: str = "",
    boq_root_uri: str = "",
    norm_context_root_uri: str = "",
    owner_uri: str = "",
    bridge_mappings: dict[str, Any] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    from services.api.domain.smu.runtime.smu_import_job_service import start_smu_import_job

    return start_smu_import_job(
        upload_file_name=upload_file_name,
        upload_content=upload_content,
        project_uri=project_uri,
        project_id=project_id,
        boq_root_uri=boq_root_uri,
        norm_context_root_uri=norm_context_root_uri,
        owner_uri=owner_uri,
        bridge_mappings=bridge_mappings,
        commit=commit,
    )


def get_boqpeg_import_job(job_id: str) -> dict[str, Any]:
    from services.api.domain.smu.runtime.smu_import_job_service import get_smu_import_job

    return get_smu_import_job(job_id)


def get_active_boqpeg_import_job(*, project_uri: str) -> dict[str, Any]:
    from services.api.domain.smu.runtime.smu_import_job_service import get_active_smu_import_job

    return get_active_smu_import_job(project_uri=project_uri)


__all__ = [
    "get_active_boqpeg_import_job",
    "get_boqpeg_import_job",
    "start_boqpeg_import_job",
]
