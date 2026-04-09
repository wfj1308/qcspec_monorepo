from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.api.domain.signpeg.runtime.gate_explainer import explain_gate_result, make_demo_failed_gate_result
from services.api.domain.signpeg.runtime.process_explainer import explain_process_status
from services.api.domain.signpeg.runtime.realtime_validator import validate_field_realtime


@pytest.fixture(autouse=True)
def _disable_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_gate_explainer_hole_diameter_blocking() -> None:
    gate_result = make_demo_failed_gate_result(hole_diameter=1.38, design_diameter=1.5)
    out = asyncio.run(
        explain_gate_result(
            form_code="桥施7表",
            gate_result=gate_result,
            norm_context={"protocol_uri": "v://normref.com/doc-type/bridge/pile-hole-check@v1"},
            language="zh",
        )
    )
    assert out.passed is False
    assert out.issues
    assert out.issues[0].severity == "blocking"
    assert "JTG F80/1-2017" in out.issues[0].norm_ref
    assert out.next_steps


def test_process_explainer_locked_with_two_reasons() -> None:
    chain: dict[str, Any] = {
        "steps": [
            {"step_id": "pile-pour-04", "name": "水下混凝土灌注（桥施9表）"},
        ],
        "state_matrix": {
            "blocked_details": [
                {
                    "step_id": "pile-pour-04",
                    "missing_pre_conditions": ["桥施11表"],
                    "missing_materials": ["concrete-c50"],
                    "missing_inspection_batches": [],
                }
            ]
        },
    }
    out = explain_process_status(
        chain=chain,
        component_uri="v://cn.demo/project/pile/001",
        step_id="pile-pour-04",
        current_status="locked",
        language="zh",
    )
    assert out.status == "locked"
    assert len(out.blocking_reasons) == 2
    assert any(item.type == "previous_step_incomplete" for item in out.blocking_reasons)
    assert any(item.type == "material_iqc_missing" for item in out.blocking_reasons)


def test_gate_explainer_all_pass() -> None:
    gate_result = {
        "result": "PASS",
        "checks": [{"check_id": "hole_diameter", "label": "孔径检查", "pass": True, "severity": "mandatory"}],
    }
    out = asyncio.run(
        explain_gate_result(
            form_code="桥施7表",
            gate_result=gate_result,
            norm_context={},
            language="zh",
        )
    )
    assert out.passed is True
    assert "通过" in out.summary


def test_gate_explainer_multilang_en() -> None:
    gate_result = make_demo_failed_gate_result(hole_diameter=1.38, design_diameter=1.5)
    out = asyncio.run(
        explain_gate_result(
            form_code="Bridge Form 7",
            gate_result=gate_result,
            norm_context={"protocol_uri": "v://normref.com/doc-type/bridge/pile-hole-check@v1"},
            language="en",
        )
    )
    assert out.language == "en"
    assert out.passed is False
    assert "failed" in out.summary.lower()


def test_realtime_validator_hole_diameter_warning_blocking() -> None:
    out = asyncio.run(
        validate_field_realtime(
            form_code="桥施7表",
            field_key="hole_diameter",
            value=1.38,
            context={
                "design_diameter": 1.5,
                "tolerance_pct": 5,
                "unit": "m",
                "norm_ref": "JTG F80/1-2017 第7.1条",
            },
            language="zh",
        )
    )
    assert out.status == "blocking"
    assert "JTG F80/1-2017" in out.norm_ref
    assert out.expected
    assert out.message
