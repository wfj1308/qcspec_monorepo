from __future__ import annotations

from services.api.domain.execution.docfinal.triprole_docfinal_master_export import (
    export_doc_final,
)


def test_export_doc_final_delegates_archive_and_birth_creation() -> None:
    captured: dict[str, object] = {}

    class _Engine:
        def __init__(self, sb: object) -> None:
            captured["engine_sb"] = sb

        def create(self, **kwargs: object) -> dict[str, object]:
            captured["create_kwargs"] = kwargs
            return {"proof_id": kwargs.get("proof_id"), "ok": True}

    def _status_fn(**kwargs: object) -> dict[str, object]:
        captured["status_kwargs"] = kwargs
        return {"items": [{"boq_item_uri": "v://project/demo/boq/1-1"}]}

    def _archive_fn(**kwargs: object) -> dict[str, object]:
        captured["archive_kwargs"] = kwargs
        create_birth_row_fn = kwargs["create_birth_row_fn"]
        captured["birth_result"] = create_birth_row_fn(
            "proof://master/1",
            "v://owner/demo/",
            "v://project/demo/",
            {"root_hash": "h1"},
            "v://project/demo/segment/archive/",
        )
        return {"ok": True, "filename": "MASTER-DSP.qcdsp"}

    out = export_doc_final(
        sb="SB",
        project_uri="v://project/demo/",
        project_name="Demo",
        passphrase="secret",
        verify_base_url="https://verify.example.com",
        include_unsettled=True,
        get_boq_realtime_status_fn=_status_fn,
        proof_utxo_engine_cls=_Engine,
        export_doc_final_archive_fn=_archive_fn,
        build_docfinal_package_for_boq_fn=lambda **_: {},
        get_full_lineage_fn=lambda *_args, **_kwargs: {},
        item_no_from_boq_uri_fn=lambda _uri: "1-1",
        smu_id_from_item_no_fn=lambda _item: "SMU-001",
        utc_iso_fn=lambda: "2026-01-01T00:00:00Z",
        encrypt_aes256_fn=lambda data, _passphrase: data,
    )

    assert out == {"ok": True, "filename": "MASTER-DSP.qcdsp"}
    assert captured["status_kwargs"] == {
        "sb": "SB",
        "project_uri": "v://project/demo/",
        "limit": 10000,
    }
    assert captured["engine_sb"] == "SB"

    create_kwargs = captured["create_kwargs"]
    assert isinstance(create_kwargs, dict)
    assert create_kwargs["proof_type"] == "archive"
    assert create_kwargs["norm_uri"] == "v://norm/CoordOS/DocFinal/1.0#master_dsp"
    assert create_kwargs["signer_role"] == "SYSTEM"

    archive_kwargs = captured["archive_kwargs"]
    assert isinstance(archive_kwargs, dict)
    assert archive_kwargs["project_uri"] == "v://project/demo/"
    assert archive_kwargs["project_name"] == "Demo"
    assert archive_kwargs["include_unsettled"] is True
