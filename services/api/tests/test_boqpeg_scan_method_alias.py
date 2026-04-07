from __future__ import annotations

from services.api.domain.boqpeg import import_boq_upload_chain, scan_boq_and_create_utxos


def _sample_csv_bytes() -> bytes:
    csv_text = (
        "item_no,name,unit,division,subdivision,hierarchy,design_quantity,unit_price,approved_quantity\n"
        "403-1-2,Rebar processing and install,t,Bridge,Rebar,Bridge/Rebar,10,100,9.8\n"
    )
    return csv_text.encode("utf-8")


def test_scan_boq_and_create_utxos_alias_behaves_like_import_chain() -> None:
    kwargs = {
        "sb": None,
        "project_uri": "v://project/demo",
        "project_id": None,
        "upload_file_name": "boq.csv",
        "upload_content": _sample_csv_bytes(),
        "boq_root_uri": "v://project/demo/boq/400",
        "norm_context_root_uri": "v://project/demo/normContext",
        "owner_uri": "v://project/demo/role/system/",
        "bridge_mappings": {"403-1-2": "YK0+500-main"},
        "dto_role": "OWNER",
        "commit": False,
    }
    direct = scan_boq_and_create_utxos(**kwargs)
    compat = import_boq_upload_chain(**kwargs)

    assert direct["ok"] is True
    assert compat["ok"] is True
    assert int(direct.get("boqpeg", {}).get("item_count") or 0) == int(compat.get("boqpeg", {}).get("item_count") or 0)
    assert int(direct.get("boqpeg", {}).get("smu_units") or 0) >= 1
    assert str((direct.get("view") or {}).get("view_role") or "") == "OWNER"

