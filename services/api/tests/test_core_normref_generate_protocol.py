from __future__ import annotations

from services.api.core.norm.service import NormRefResolverService


class _FakePort:
    def resolve_threshold(self, *, sb, gate_id, context=""):  # pragma: no cover - not used in this file
        return {}

    def get_spec_dict(self, *, sb, spec_dict_key):  # pragma: no cover - not used in this file
        return {}


def test_generate_protocol_from_table_content_csv_text() -> None:
    table = (
        "检查项,允许偏差,规范,严重级别\n"
        "直径偏差,<=2%,GB50204-2015 5.3.2,mandatory\n"
        "钢筋间距,10,GB50204-2015 5.3.2,warning\n"
    )
    out = NormRefResolverService.generate_protocol(
        table_content=table,
        protocol_uri="v://normref.com/qc/rebar-processing@v1",
        norm_code="GB50204-2015 5.3.2",
        boq_item_id="403-1-2",
        description="钢筋加工及安装",
    )

    assert out["uri"] == "v://normref.com/qc/rebar-processing@v1"
    assert out["schema_uri"] == "v://normref.com/schema/qc-v1"
    assert out["metadata"]["boq_item_id"] == "403-1-2"
    assert str(out["metadata"]["doc_id"]).startswith("NINST-")
    assert len(out["gates"]) == 2
    assert out["gates"][0]["threshold"]["operator"] == "lte"
    assert isinstance(out.get("logic_inputs"), list) and len(out["logic_inputs"]) >= 2
    assert out.get("state_matrix", {}).get("total_qc_tables") == 2
    assert out.get("state_matrix", {}).get("expected_qc_table_count") == 2
    assert out.get("state_matrix", {}).get("pending_qc_table_count") == 2
    layers = out.get("layers") or {}
    assert set(layers.keys()) == {"header", "gate", "body", "proof", "state"}
    assert layers["header"]["doc_type"] == "v://normref.com/doc-type/quality-inspection@v1"
    assert layers["header"]["v_uri"] == out["uri"]
    assert layers["state"]["state_matrix"]["total_qc_tables"] == len(out["gates"])
    assert layers["state"]["state_matrix"]["expected_qc_table_count"] == len(out["gates"])
    assert "valid_until" in layers["state"]


def test_generate_protocol_camel_case_alias() -> None:
    table = "检查项,允许偏差\n保护层,<=5\n"
    out = NormRefResolverService.generateProtocol(table)
    assert out["uri"].startswith("v://normref.com/qc/")
    assert out["gates"][0]["label"] == "保护层"


def test_generate_protocol_defaults_to_raft_uri_when_table_mentions_raft() -> None:
    table = "检查项,允许偏差\n筏基础厚度,<=10mm\n"
    out = NormRefResolverService.generate_protocol(table_content=table)
    assert out["uri"] == "v://normref.com/qc/raft-foundation@v1"


def test_verify_against_protocol_pass_and_fail() -> None:
    protocol = {
        "uri": "v://normref.com/qc/rebar-processing@v1",
        "gates": [
            {
                "check_id": "spacing",
                "label": "钢筋间距偏差",
                "severity": "mandatory",
                "threshold": {"operator": "lte", "value": 10, "unit": "mm"},
            },
            {
                "check_id": "diameter",
                "label": "直径偏差",
                "severity": "mandatory",
                "threshold": {"operator": "lte", "value": 0.02, "unit": "%"},
            },
        ],
    }

    pass_out = NormRefResolverService.verify_against_protocol(
        protocol=protocol,
        actual_data={"spacing": 8, "diameter": 19.8},
        design_data={"spacing": 10, "diameter": 20.0},
    )
    assert pass_out["ok"] is True
    assert pass_out["result"] == "PASS"
    assert pass_out["failed_gates"] == []
    assert pass_out["proof_hash"]

    fail_out = NormRefResolverService.verify_against_protocol(
        protocol=protocol,
        actual_data={"spacing": 22, "diameter": 19.0},
        design_data={"spacing": 10, "diameter": 20.0},
    )
    assert fail_out["ok"] is True
    assert fail_out["result"] == "FAIL"
    assert "spacing" in fail_out["failed_gates"]


def test_resolve_protocol_from_docs_json_for_concrete_and_pile() -> None:
    service = NormRefResolverService(sb=None, port=_FakePort())

    concrete = service.resolve_protocol(uri="v://normref.com/qc/concrete-compressive-test@v1")
    assert concrete["ok"] is True
    assert concrete["source"] == "docs_json"
    assert concrete["protocol"]["uri"] == "v://normref.com/qc/concrete-compressive-test@v1"
    assert len(concrete["protocol"]["gates"]) >= 2

    pile = service.resolve_protocol(uri="v://normref.com/qc/pile-foundation@v1")
    assert pile["ok"] is True
    assert pile["source"] == "docs_json"
    assert pile["protocol"]["uri"] == "v://normref.com/qc/pile-foundation@v1"
    assert len(pile["protocol"]["gates"]) >= 2
