from __future__ import annotations

import io
import zipfile

import pytest
from fastapi import HTTPException

from services.api.domain.execution.triprole_docfinal_export import export_doc_final_archive


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_export_doc_final_archive_requires_settled_items_when_not_including_unsettled() -> None:
    with pytest.raises(HTTPException) as exc:
        export_doc_final_archive(
            status={"items": [{"boq_item_uri": "v://boq/1-1", "settlement_count": 0}]},
            sb=object(),
            project_uri="v://project/demo",
            include_unsettled=False,
            build_docfinal_package_for_boq_fn=lambda **_: {},
            get_full_lineage_fn=lambda *_: {},
            item_no_from_boq_uri_fn=lambda _uri: "1-1",
            smu_id_from_item_no_fn=lambda _item_no: "SMU1",
            utc_iso_fn=lambda: "2026-01-01T00:00:00Z",
            encrypt_aes256_fn=lambda _blob, _key: {"algorithm": "AES-256", "cipher_hash": "h1"},
            create_birth_row_fn=lambda *_: {"proof_id": "p1", "proof_hash": "h1", "gitpeg_anchor": "a1"},
        )
    assert exc.value.status_code == 404


def test_export_doc_final_archive_returns_master_payload_and_item_errors() -> None:
    def _build_docfinal_package_for_boq(**kwargs: object) -> dict[str, object]:
        boq_item_uri = str(kwargs.get("boq_item_uri") or "")
        if boq_item_uri.endswith("/2-1"):
            raise RuntimeError("render failed")
        return {
            "zip_bytes": _zip_bytes({"doc.txt": b"ok"}),
            "asset_transfer": {"ok": True},
        }

    payload = export_doc_final_archive(
        status={
            "summary": {"boq_item_count": 2},
            "items": [
                {
                    "boq_item_uri": "v://boq/1-1",
                    "item_no": "1-1",
                    "latest_settlement_proof_id": "s1",
                    "settlement_count": 1,
                },
                {
                    "boq_item_uri": "v://boq/2-1",
                    "item_no": "2-1",
                    "latest_settlement_proof_id": "s2",
                    "settlement_count": 0,
                },
            ],
        },
        sb=object(),
        project_uri="v://project/demo",
        project_name="Demo Project",
        include_unsettled=True,
        build_docfinal_package_for_boq_fn=_build_docfinal_package_for_boq,
        get_full_lineage_fn=lambda *_: {"total_proof_hash": "th"},
        item_no_from_boq_uri_fn=lambda uri: str(uri).rstrip("/").split("/")[-1],
        smu_id_from_item_no_fn=lambda item_no: f"SMU-{str(item_no).split('-')[0]}",
        utc_iso_fn=lambda: "2026-01-01T00:00:00Z",
        encrypt_aes256_fn=lambda blob, _key: {"algorithm": "AES-256", "cipher_hash": str(len(blob))},
        create_birth_row_fn=lambda proof_id, *_: {
            "proof_id": proof_id,
            "proof_hash": "proof-hash",
            "gitpeg_anchor": "anchor",
        },
    )

    assert payload["ok"] is True
    assert payload["project_uri"] == "v://project/demo"
    assert payload["status_summary"] == {"boq_item_count": 2}
    assert len(payload["items_exported"]) == 1
    assert payload["items_exported"][0]["boq_item_uri"] == "v://boq/1-1"
    assert len(payload["errors"]) == 1
    assert payload["errors"][0]["boq_item_uri"] == "v://boq/2-1"
    assert payload["birth_certificate"]["proof_hash"] == "proof-hash"
    assert payload["encrypted_bytes"]
    assert payload["filename"].endswith(".qcdsp")
