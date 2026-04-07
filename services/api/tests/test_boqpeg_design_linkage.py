from __future__ import annotations

from services.api.domain.boqpeg.runtime.design_linkage import (
    match_boq_with_design_manifest,
    parse_design_manifest_from_upload,
    run_bidirectional_closure,
)
from services.api.domain.boqpeg.runtime import design_linkage


def _sample_boq_csv_bytes() -> bytes:
    csv_text = (
        "item_no,name,unit,division,subdivision,hierarchy,design_quantity,unit_price,approved_quantity\n"
        "403-1-2,Spillway concrete C30,m3,Dam,Spillway,YK0+500,120,500,100\n"
    )
    return csv_text.encode("utf-8")


def test_parse_design_manifest_from_pdf_text_fallback() -> None:
    content = "Pile P-1 C30 YK0+500 length 12 quantity 10".encode("utf-8")
    out = parse_design_manifest_from_upload(
        upload_file_name="drawing.pdf",
        upload_content=content,
        project_uri="v://project/demo",
    )
    assert out["ok"] is True
    manifest = out["manifest"]
    assert manifest["manifest_uri"].startswith("v://project/demo/design/manifest/")
    assert int(manifest["stats"]["component_count"]) >= 1


def test_match_boq_with_design_manifest_reports_consistent_rows() -> None:
    manifest = {
        "manifest": {
            "manifest_uri": "v://project/demo/design/manifest/m1",
            "components": [
                {
                    "component_uri": "v://project/demo/design/component/c-1",
                    "component_id": "403-1-2-c1",
                    "component_type": "pile",
                    "description": "Spillway concrete C30",
                    "material_spec": "C30",
                    "location_mark": "YK0+500",
                    "geometry": {"quantity": 100},
                }
            ],
        }
    }
    out = match_boq_with_design_manifest(
        sb=None,
        upload_file_name="boq.csv",
        upload_content=_sample_boq_csv_bytes(),
        project_uri="v://project/demo",
        owner_uri="v://project/demo/role/system/",
        design_manifest=manifest,
        commit=False,
    )
    assert out["ok"] is True
    assert out["summary"]["matched_rows"] == 1
    assert out["summary"]["deviation_rows"] == 0
    assert out["matches"][0]["status"] == "consistent"


def test_run_bidirectional_closure_generates_sync_actions() -> None:
    out = run_bidirectional_closure(
        sb=None,
        body={
            "project_uri": "v://project/demo",
            "node_uri": "v://tz.nest-dam/bill28/spillway/concrete/",
            "change_source": "boq",
            "matched_boq_codes": ["403-1-2"],
            "delta_ratio": 0.09,
        },
        commit=False,
    )
    assert out["ok"] is True
    assert out["change_source"] == "boq"
    assert out["forward_actions"][0]["action"] == "propose_design_manifest_update"
    assert out["proof"]["state_data"]["proof_kind"] == "Design-BOQ Bidirectional Sync Proof"


def test_match_boq_with_design_manifest_reads_threshold_from_normpeg(monkeypatch) -> None:
    manifest = {
        "manifest": {
            "manifest_uri": "v://project/demo/design/manifest/m1",
            "components": [
                {
                    "component_uri": "v://project/demo/design/component/c-1",
                    "component_id": "403-1-2-c1",
                    "component_type": "pile",
                    "description": "Spillway concrete C30",
                    "material_spec": "C30",
                    "location_mark": "YK0+500",
                    "geometry": {"quantity": 91},
                }
            ],
        }
    }
    monkeypatch.setattr(
        design_linkage,
        "resolve_norm_rule",
        lambda _uri, _ctx: {"warning_ratio": 0.05, "review_ratio": 0.1},
    )
    out = match_boq_with_design_manifest(
        sb=None,
        upload_file_name="boq.csv",
        upload_content=_sample_boq_csv_bytes(),
        project_uri="v://project/demo",
        owner_uri="v://project/demo/role/system/",
        design_manifest=manifest,
        threshold_spec_uri="v://norm/spec/deviation-threshold@v1",
        commit=False,
    )
    assert out["ok"] is True
    assert out["thresholds"]["warning_ratio"] == 0.05
    assert out["thresholds"]["review_ratio"] == 0.1
