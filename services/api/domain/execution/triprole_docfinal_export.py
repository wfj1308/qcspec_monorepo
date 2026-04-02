"""DocFinal master archive export orchestration helpers."""

from __future__ import annotations

import io
import zipfile
from typing import Any, Callable

from fastapi import HTTPException

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
    utc_iso as _utc_iso,
)
from services.api.domain.execution.triprole_docfinal_archive import (
    build_archive_index_payload as _build_archive_index_payload,
    build_archive_volumes as _build_archive_volumes,
    write_archive_manifest_files as _write_archive_manifest_files,
)
from services.api.domain.execution.triprole_docfinal_finalize import (
    finalize_master_docfinal as _finalize_master_docfinal,
)
from services.api.domain.execution.triprole_docfinal_items import (
    export_docfinal_item_to_master as _export_docfinal_item_to_master,
)


def export_doc_final_archive(
    *,
    status: dict[str, Any],
    sb: Any,
    project_uri: str,
    project_name: str | None = None,
    passphrase: str = "",
    verify_base_url: str = "https://verify.qcspec.com",
    include_unsettled: bool = False,
    build_docfinal_package_for_boq_fn: Callable[..., dict[str, Any]],
    get_full_lineage_fn: Callable[[str, Any], dict[str, Any]],
    item_no_from_boq_uri_fn: Callable[[str], str],
    smu_id_from_item_no_fn: Callable[[str], str],
    utc_iso_fn: Callable[[], str],
    encrypt_aes256_fn: Callable[[bytes, str], bytes],
    create_birth_row_fn: Callable[[str, str, str, dict[str, Any], str], Any],
) -> dict[str, Any]:
    items = _as_list(status.get("items"))
    if include_unsettled:
        target_items = items
    else:
        target_items = [item for item in items if int(item.get("settlement_count") or 0) > 0]

    if not target_items:
        raise HTTPException(404, "no settled boq items found for project")

    master_buf = io.BytesIO()
    file_fingerprints: list[dict[str, Any]] = []
    item_errors: list[dict[str, Any]] = []
    exported_items: list[dict[str, Any]] = []
    lineage_snapshots: list[dict[str, Any]] = []

    with zipfile.ZipFile(master_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as master_zip:
        for item in target_items:
            item_result = _export_docfinal_item_to_master(
                item=_as_dict(item),
                sb=sb,
                project_uri=_to_text(project_uri),
                project_name=_to_text(project_name or ""),
                verify_base_url=verify_base_url,
                master_zip=master_zip,
                item_no_from_boq_uri=item_no_from_boq_uri_fn,
                smu_id_from_item_no=smu_id_from_item_no_fn,
                build_docfinal_package_for_boq=build_docfinal_package_for_boq_fn,
                get_full_lineage=get_full_lineage_fn,
            )
            if bool(item_result.get("skipped")):
                continue

            file_fingerprints.extend(_as_list(item_result.get("file_fingerprints")))

            exported_item = _as_dict(item_result.get("exported_item"))
            if exported_item:
                exported_items.append(exported_item)

            lineage_snapshot = _as_dict(item_result.get("lineage_snapshot"))
            if lineage_snapshot:
                lineage_snapshots.append(lineage_snapshot)

            item_error = _as_dict(item_result.get("item_error"))
            if item_error:
                item_errors.append(item_error)

        archive_volumes = _build_archive_volumes(
            exported_items=exported_items,
            smu_id_from_item_no=smu_id_from_item_no_fn,
        )

        index_payload = _build_archive_index_payload(
            generated_at=_utc_iso(),
            project_uri=_to_text(project_uri),
            project_name=_to_text(project_name or ""),
            exported_items=exported_items,
            archive_volumes=archive_volumes,
            lineage_snapshots=lineage_snapshots,
            item_errors=item_errors,
            file_fingerprints=file_fingerprints,
        )
        _write_archive_manifest_files(
            master_zip=master_zip,
            index_payload=index_payload,
            archive_volumes=archive_volumes,
            project_uri=_to_text(project_uri),
            project_name=_to_text(project_name or ""),
        )

    master_bytes = master_buf.getvalue()
    final_payload = _finalize_master_docfinal(
        master_bytes=master_bytes,
        project_uri=_to_text(project_uri),
        project_name=_to_text(project_name or ""),
        exported_items=exported_items,
        item_errors=item_errors,
        passphrase=passphrase,
        utc_iso=utc_iso_fn,
        encrypt_aes256=encrypt_aes256_fn,
        create_birth_row=create_birth_row_fn,
    )
    root_hash = _to_text(final_payload.get("root_hash") or "").strip()

    return {
        "ok": True,
        "project_uri": _to_text(project_uri),
        "root_hash": root_hash,
        "birth_certificate": _as_dict(final_payload.get("birth_certificate")),
        "items_exported": exported_items,
        "errors": item_errors,
        "encrypted_bytes": final_payload.get("encrypted_bytes") or b"",
        "filename": _to_text(final_payload.get("filename") or f"MASTER-DSP-{root_hash[:16]}.qcdsp"),
        "status_summary": status.get("summary") or {},
    }


__all__ = ["export_doc_final_archive"]
