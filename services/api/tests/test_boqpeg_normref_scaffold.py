from __future__ import annotations

from pathlib import Path

from services.api.domain.boqpeg.runtime.normref_scaffold import (
    bootstrap_normref_logic_scaffold,
    table_to_protocol_block,
)


def test_bootstrap_normref_logic_scaffold_writes_seed_files(tmp_path: Path) -> None:
    out = bootstrap_normref_logic_scaffold(
        sb=None,
        commit=False,
        write_files=True,
        output_root=tmp_path,
    )

    assert out["ok"] is True
    assert out["levels"]["l0"] == "v://normref.com/core@v1"
    assert out["levels"]["l1"] == "v://normref.com/construction/highway@v1"
    assert out["levels"]["l2"] == "v://normref.com/qc/raft-foundation@v1"
    assert "v://normref.com/qc/template/general-quality-inspection@v1" in out["protocol_catalog"]
    assert "v://normref.com/qc/concrete-compressive-test@v1" in out["protocol_catalog"]
    assert "v://normref.com/qc/pile-foundation@v1" in out["protocol_catalog"]
    assert out["raft_spu"]["uri"] == "v://normref.com/spu/raft-foundation@v1"
    assert out["raft_protocol"]["uri"] == "v://normref.com/qc/raft-foundation@v1"
    assert out["prompt_spu"]["uri"] == "v://normref.com/prompt/tab-to-peg-engine@v1"

    core_md = Path(out["files"]["core"]["md_path"])
    highway_md = Path(out["files"]["highway"]["md_path"])
    schema_md = Path(out["files"]["schema"]["md_path"])
    general_template_md = Path(out["files"]["general_template"]["md_path"])
    protocol_md = Path(out["files"]["rebar_protocol"]["md_path"])
    concrete_protocol_md = Path(out["files"]["concrete_protocol"]["md_path"])
    pile_protocol_md = Path(out["files"]["pile_protocol"]["md_path"])
    raft_spu_md = Path(out["files"]["raft_spu"]["md_path"])
    raft_protocol_md = Path(out["files"]["raft_protocol"]["md_path"])
    prompt_md = Path(out["files"]["prompt_spu"]["md_path"])
    assert core_md.exists()
    assert highway_md.exists()
    assert schema_md.exists()
    assert general_template_md.exists()
    assert protocol_md.exists()
    assert concrete_protocol_md.exists()
    assert pile_protocol_md.exists()
    assert raft_spu_md.exists()
    assert raft_protocol_md.exists()
    assert prompt_md.exists()
    assert core_md.name == "core@v1.md"
    assert highway_md.name == "highway@v1.md"
    assert schema_md.name == "qc-v1.md"
    assert "general-quality-inspection@v1" in general_template_md.as_posix()
    assert "v://normref.com/qc/rebar-processing@v1" in protocol_md.read_text(encoding="utf-8")
    assert "v://normref.com/qc/concrete-compressive-test@v1" in concrete_protocol_md.read_text(encoding="utf-8")
    assert "v://normref.com/qc/pile-foundation@v1" in pile_protocol_md.read_text(encoding="utf-8")
    assert "v://normref.com/spu/raft-foundation@v1" in raft_spu_md.read_text(encoding="utf-8")
    assert "v://normref.com/qc/raft-foundation@v1" in raft_protocol_md.read_text(encoding="utf-8")


def test_table_to_protocol_block_parses_gates_and_thresholds(tmp_path: Path) -> None:
    csv_bytes = (
        "检查项,允许偏差,规范,严重级别\n"
        "直径偏差,<=2%,GB50204-2015 5.3.2,mandatory\n"
        "坍落度,180~220mm,GB50204-2015 7.4.3,warning\n"
    ).encode("utf-8")

    out = table_to_protocol_block(
        sb=None,
        upload_file_name="qc.csv",
        upload_content=csv_bytes,
        protocol_uri="v://normref.com/qc/rebar-processing@v1",
        norm_code="GB50204-2015",
        boq_item_id="403-1-2",
        description="钢筋加工及安装",
        topology_component_count=52,
        forms_per_component=2,
        generated_qc_table_count=3,
        signed_pass_table_count=0,
        owner_uri="v://normref.com/executor/system/",
        commit=False,
        write_files=True,
        output_root=tmp_path,
    )

    assert out["ok"] is True
    assert out["summary"]["gate_count"] == 2
    assert out["summary"]["source_row_count"] == 2
    assert out["summary"]["expected_qc_table_count"] == 104
    assert out["summary"]["pending_qc_table_count"] == 101

    protocol = out["protocol"]
    assert protocol["uri"] == "v://normref.com/qc/rebar-processing@v1"
    assert protocol["schema_uri"] == "v://normref.com/schema/qc-v1"
    assert protocol["layers"]["header"]["v_uri"] == "v://normref.com/qc/rebar-processing@v1"
    assert str(protocol["layers"]["header"]["doc_id"]).startswith("NINST-")
    assert "project_ref" in protocol["layers"]["header"]
    assert set(protocol["layers"].keys()) == {"header", "gate", "body", "proof", "state"}
    assert "timestamps" in protocol["layers"]["proof"]
    assert "valid_until" in protocol["layers"]["state"]

    first_gate = protocol["gates"][0]
    second_gate = protocol["gates"][1]
    assert first_gate["threshold"]["operator"] == "lte"
    assert second_gate["threshold"]["operator"] == "range"
    assert second_gate["severity"] == "warning"
    assert len(protocol["logic_inputs"]) >= 2
    assert protocol["state_matrix"]["expected_qc_table_count"] == 104
    assert protocol["state_matrix"]["total_qc_tables"] == 104
    assert protocol["state_matrix"]["pending"] == 101
    assert protocol["layers"]["state"]["state_matrix"]["total_qc_tables"] == 104

    md_path = Path(out["files"]["md_path"])
    json_path = Path(out["files"]["json_path"])
    assert md_path.exists()
    assert json_path.exists()
