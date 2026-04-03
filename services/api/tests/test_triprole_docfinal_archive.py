from __future__ import annotations

import io
import json
import zipfile

from services.api.domain.execution.docfinal.triprole_docfinal_archive import (
    build_archive_index_payload,
    build_archive_volumes,
    write_archive_manifest_files,
)


def test_build_archive_volumes_assigns_pages_and_groups() -> None:
    volumes = build_archive_volumes(
        exported_items=[
            {"item_no": "2-2-1", "boq_item_uri": "v://boq/2-2-1", "file_count": 1},
            {"item_no": "1-1-2", "boq_item_uri": "v://boq/1-1-2", "file_count": 2, "smu_id": "SMU1"},
            {"item_no": "1-1-1", "boq_item_uri": "v://boq/1-1-1", "file_count": 1, "smu_id": "SMU1"},
        ],
        smu_id_from_item_no=lambda item_no: f"SMU{item_no.split('-')[0]}" if item_no else "SMU0",
    )

    assert len(volumes) == 2
    assert volumes[0]["smu_id"] == "SMU1"
    assert volumes[0]["volume_no"] == 1
    assert volumes[1]["smu_id"] == "SMU2"
    assert volumes[1]["volume_no"] == 2

    entries = volumes[0]["entries"]
    assert entries[0]["item_no"] == "1-1-1"
    assert entries[0]["start_page"] == 1
    assert entries[0]["end_page"] == 2
    assert entries[1]["item_no"] == "1-1-2"
    assert entries[1]["start_page"] == 3
    assert entries[1]["end_page"] == 6


def test_write_archive_manifest_files_writes_index_catalog_and_volume_docs() -> None:
    archive_volumes = [
        {
            "volume_no": 1,
            "title": "JTG Archive Volume 1 (SMU SMU1)",
            "smu_id": "SMU1",
            "chapter": "SMU1",
            "archive_scope": "smu",
            "estimated_pages": 3,
            "entries": [{"item_no": "1-1-1", "start_page": 1, "end_page": 3}],
        }
    ]
    index_payload = build_archive_index_payload(
        generated_at="2026-04-02T00:00:00Z",
        project_uri="v://project/demo",
        project_name="Demo",
        exported_items=[],
        archive_volumes=archive_volumes,
        lineage_snapshots=[],
        item_errors=[],
        file_fingerprints=[],
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        write_archive_manifest_files(
            master_zip=zf,
            index_payload=index_payload,
            archive_volumes=archive_volumes,
            project_uri="v://project/demo",
            project_name="Demo",
        )

    with zipfile.ZipFile(io.BytesIO(buf.getvalue()), mode="r") as zf:
        names = set(zf.namelist())
        assert "index.json" in names
        assert "jtg_archive/catalog.json" in names
        assert "jtg_archive/volume_01_cover.txt" in names
        assert "jtg_archive/volume_01_toc.txt" in names

        index_payload_read = json.loads(zf.read("index.json").decode("utf-8"))
        assert index_payload_read["project_uri"] == "v://project/demo"
        assert index_payload_read["project_name"] == "Demo"

        toc = zf.read("jtg_archive/volume_01_toc.txt").decode("utf-8")
        assert "SMU ID: SMU1" in toc
        assert "- 1-1-1: p.1-3" in toc
