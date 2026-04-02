"""DocFinal master archive volume and manifest helpers."""

from __future__ import annotations

import json
from typing import Any, Callable


def build_archive_volumes(
    *,
    exported_items: list[dict[str, Any]],
    smu_id_from_item_no: Callable[[str], str],
) -> list[dict[str, Any]]:
    archive_volumes: list[dict[str, Any]] = []
    page_cursor = 1
    by_smu: dict[str, list[dict[str, Any]]] = {}
    for item in exported_items:
        smu_id = str(item.get("smu_id") or "").strip() or smu_id_from_item_no(
            str(item.get("item_no") or "").strip()
        )
        by_smu.setdefault(smu_id, []).append(item)

    volume_no = 1
    for smu_id in sorted(by_smu.keys()):
        smu_items = sorted(
            by_smu.get(smu_id) or [],
            key=lambda row: str((row or {}).get("item_no") or "").strip(),
        )
        est_pages = 0
        entries: list[dict[str, Any]] = []
        for item in smu_items:
            item_pages = max(1, int(item.get("file_count") or 1) * 2)
            start_page = page_cursor
            end_page = page_cursor + item_pages - 1
            page_cursor = end_page + 1
            est_pages += item_pages
            entries.append(
                {
                    "item_no": str(item.get("item_no") or "").strip(),
                    "boq_item_uri": str(item.get("boq_item_uri") or "").strip(),
                    "smu_id": smu_id,
                    "start_page": start_page,
                    "end_page": end_page,
                }
            )
        archive_volumes.append(
            {
                "volume_no": volume_no,
                "title": f"JTG Archive Volume {volume_no} (SMU {smu_id})",
                "smu_id": smu_id,
                "chapter": smu_id,
                "archive_scope": "smu",
                "estimated_pages": est_pages,
                "entries": entries,
            }
        )
        volume_no += 1

    return archive_volumes


def build_archive_index_payload(
    *,
    generated_at: str,
    project_uri: str,
    project_name: str,
    exported_items: list[dict[str, Any]],
    archive_volumes: list[dict[str, Any]],
    lineage_snapshots: list[dict[str, Any]],
    item_errors: list[dict[str, Any]],
    file_fingerprints: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generated_at": str(generated_at or ""),
        "project_uri": str(project_uri or ""),
        "project_name": str(project_name or ""),
        "items": exported_items,
        "archive_volumes": archive_volumes,
        "lineage_snapshots": lineage_snapshots,
        "errors": item_errors,
        "fingerprints": file_fingerprints,
    }


def write_archive_manifest_files(
    *,
    master_zip: Any,
    index_payload: dict[str, Any],
    archive_volumes: list[dict[str, Any]],
    project_uri: str,
    project_name: str,
) -> None:
    index_json = json.dumps(index_payload, ensure_ascii=False, indent=2, sort_keys=True, default=str).encode("utf-8")
    master_zip.writestr("index.json", index_json)
    master_zip.writestr(
        "jtg_archive/catalog.json",
        json.dumps(archive_volumes, ensure_ascii=False, indent=2, sort_keys=True, default=str),
    )
    for vol in archive_volumes:
        cover = (
            f"JTG Archive Cover\n"
            f"Project: {str(project_name or '')}\n"
            f"Project URI: {str(project_uri or '')}\n"
            f"Volume No: {vol.get('volume_no')}\n"
            f"Title: {str(vol.get('title') or '')}\n"
            f"Estimated Pages: {int(vol.get('estimated_pages') or 0)}\n"
        )
        master_zip.writestr(
            f"jtg_archive/volume_{int(vol.get('volume_no') or 0):02d}_cover.txt",
            cover,
        )
        toc_lines = [
            "SMU Archive Catalog",
            f"SMU ID: {str(vol.get('smu_id') or '').strip()}",
            f"Volume No: {int(vol.get('volume_no') or 0)}",
            f"Estimated Pages: {int(vol.get('estimated_pages') or 0)}",
            "",
            "Entries:",
        ]
        for entry in (vol.get("entries") or []):
            row = entry if isinstance(entry, dict) else {}
            toc_lines.append(
                f"- {str(row.get('item_no') or '').strip()}: "
                f"p.{int(row.get('start_page') or 0)}-"
                f"{int(row.get('end_page') or 0)}"
            )
        master_zip.writestr(
            f"jtg_archive/volume_{int(vol.get('volume_no') or 0):02d}_toc.txt",
            "\n".join(toc_lines),
        )


__all__ = [
    "build_archive_volumes",
    "build_archive_index_payload",
    "write_archive_manifest_files",
]
