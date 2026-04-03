from __future__ import annotations

import io
import zipfile

from services.api.domain.execution.docfinal.triprole_docfinal_items import export_docfinal_item_to_master


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_export_docfinal_item_to_master_success_and_lineage() -> None:
    item_zip = _zip_bytes({"a.txt": b"hello"})
    master_buf = io.BytesIO()
    with zipfile.ZipFile(master_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as master_zip:
        result = export_docfinal_item_to_master(
            item={
                "boq_item_uri": "v://boq/1-1-1",
                "item_no": "1-1-1",
                "latest_settlement_proof_id": "p1",
            },
            sb=object(),
            project_uri="v://project/demo",
            project_name="Demo",
            verify_base_url="https://verify.qcspec.com",
            master_zip=master_zip,
            item_no_from_boq_uri=lambda uri: "from-uri",
            smu_id_from_item_no=lambda item_no: "SMU1",
            build_docfinal_package_for_boq=lambda **_: {"zip_bytes": item_zip, "asset_transfer": {"ok": True}},
            get_full_lineage=lambda proof_id, sb: {
                "total_proof_hash": "h1",
                "norm_refs": ["n1"],
                "evidence_hashes": ["e1"],
                "qc_conclusions": ["q1"],
                "consensus_signatures": ["s1"],
            },
        )

    assert result["skipped"] is False
    assert result["item_error"] is None
    exported = result["exported_item"]
    assert exported["item_no"] == "1-1-1"
    assert exported["smu_id"] == "SMU1"
    assert exported["file_count"] == 1
    assert exported["asset_transfer"] == {"ok": True}

    fingerprints = result["file_fingerprints"]
    assert len(fingerprints) == 1
    assert fingerprints[0]["path"].startswith("smu_archive/SMU1/1-1-1/")

    lineage = result["lineage_snapshot"]
    assert lineage["proof_id"] == "p1"
    assert lineage["total_proof_hash"] == "h1"

    with zipfile.ZipFile(io.BytesIO(master_buf.getvalue()), mode="r") as zf:
        names = zf.namelist()
        assert any(name.endswith("/a.txt") for name in names)


def test_export_docfinal_item_to_master_skips_missing_uri() -> None:
    result = export_docfinal_item_to_master(
        item={},
        sb=object(),
        project_uri="v://project/demo",
        project_name="Demo",
        verify_base_url="https://verify.qcspec.com",
        master_zip=None,
        item_no_from_boq_uri=lambda uri: "from-uri",
        smu_id_from_item_no=lambda item_no: "SMU1",
        build_docfinal_package_for_boq=lambda **_: {},
        get_full_lineage=lambda *_: {},
    )
    assert result["skipped"] is True
    assert result["item_error"] is None


def test_export_docfinal_item_to_master_returns_item_error_on_failure() -> None:
    master_buf = io.BytesIO()
    with zipfile.ZipFile(master_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as master_zip:
        result = export_docfinal_item_to_master(
            item={"boq_item_uri": "v://boq/1-1-1", "item_no": "1-1-1"},
            sb=object(),
            project_uri="v://project/demo",
            project_name="Demo",
            verify_base_url="https://verify.qcspec.com",
            master_zip=master_zip,
            item_no_from_boq_uri=lambda uri: "from-uri",
            smu_id_from_item_no=lambda item_no: "SMU1",
            build_docfinal_package_for_boq=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
            get_full_lineage=lambda *_: {},
        )

    assert result["skipped"] is False
    assert result["exported_item"] is None
    assert result["lineage_snapshot"] is None
    assert result["item_error"]["boq_item_uri"] == "v://boq/1-1-1"
    assert "RuntimeError" in result["item_error"]["error"]
