"""DocFinal per-item export helpers for master archive assembly."""

from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Any, Callable


def export_docfinal_item_to_master(
    *,
    item: dict[str, Any],
    sb: Any,
    project_uri: str,
    project_name: str,
    verify_base_url: str,
    master_zip: Any,
    item_no_from_boq_uri: Callable[[str], str],
    smu_id_from_item_no: Callable[[str], str],
    build_docfinal_package_for_boq: Callable[..., dict[str, Any]],
    get_full_lineage: Callable[[str, Any], dict[str, Any]],
) -> dict[str, Any]:
    boq_item_uri = str(item.get("boq_item_uri") or "").strip()
    if not boq_item_uri:
        return {
            "skipped": True,
            "exported_item": None,
            "file_fingerprints": [],
            "lineage_snapshot": None,
            "item_error": None,
        }

    item_no = str(item.get("item_no") or item_no_from_boq_uri(boq_item_uri) or "unknown").strip()
    smu_id = smu_id_from_item_no(item_no)
    base_dir = f"smu_archive/{smu_id}/{item_no or 'unknown'}"

    try:
        package = build_docfinal_package_for_boq(
            boq_item_uri=boq_item_uri,
            sb=sb,
            project_meta={
                "project_name": project_name,
                "project_uri": project_uri,
            },
            verify_base_url=verify_base_url,
            apply_asset_transfer=True,
        )
        package_zip = package.get("zip_bytes") or b""
        if not package_zip:
            raise RuntimeError("empty docfinal package")

        file_fingerprints: list[dict[str, Any]] = []
        item_file_count = 0
        with zipfile.ZipFile(io.BytesIO(package_zip), mode="r") as item_zip:
            for name in item_zip.namelist():
                blob = item_zip.read(name)
                target_name = f"{base_dir}/{name}"
                master_zip.writestr(target_name, blob)
                item_file_count += 1
                file_fingerprints.append(
                    {
                        "path": target_name,
                        "sha256": hashlib.sha256(blob).hexdigest(),
                        "size": len(blob),
                    }
                )

        exported_item = {
            "boq_item_uri": boq_item_uri,
            "item_no": item_no,
            "smu_id": smu_id,
            "base_dir": base_dir,
            "latest_settlement_proof_id": str(item.get("latest_settlement_proof_id") or ""),
            "file_count": item_file_count,
            "asset_transfer": package.get("asset_transfer"),
        }

        lineage_snapshot: dict[str, Any] | None = None
        lineage_proof_id = str(item.get("latest_settlement_proof_id") or "").strip()
        if lineage_proof_id:
            try:
                lineage = get_full_lineage(lineage_proof_id, sb)
                lineage_snapshot = {
                    "boq_item_uri": boq_item_uri,
                    "item_no": item_no,
                    "proof_id": lineage_proof_id,
                    "total_proof_hash": str(lineage.get("total_proof_hash") or "").strip(),
                    "norm_refs": lineage.get("norm_refs") or [],
                    "evidence_hashes": lineage.get("evidence_hashes") or [],
                    "qc_conclusions": lineage.get("qc_conclusions") or [],
                    "consensus_signatures": lineage.get("consensus_signatures") or [],
                }
            except Exception:
                lineage_snapshot = {
                    "boq_item_uri": boq_item_uri,
                    "item_no": item_no,
                    "proof_id": lineage_proof_id,
                    "error": "lineage_snapshot_failed",
                }

        return {
            "skipped": False,
            "exported_item": exported_item,
            "file_fingerprints": file_fingerprints,
            "lineage_snapshot": lineage_snapshot,
            "item_error": None,
        }
    except Exception as exc:
        return {
            "skipped": False,
            "exported_item": None,
            "file_fingerprints": [],
            "lineage_snapshot": None,
            "item_error": {
                "boq_item_uri": boq_item_uri,
                "item_no": item_no,
                "error": f"{exc.__class__.__name__}: {exc}",
            },
        }


__all__ = ["export_docfinal_item_to_master"]
