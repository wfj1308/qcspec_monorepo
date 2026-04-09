from __future__ import annotations

from services.api.domain.boqpeg.runtime.process_chain import create_process_chain, pile_component_uri
from services.api.domain.specir import compile_specir_process_chain


def _table(step: dict[str, object]) -> str:
    tables = step.get("required_tables")
    if not isinstance(tables, list) or not tables:
        return ""
    return str(tables[0] or "").strip()


def test_compile_drilled_pile_from_specir_matches_expected_sequence() -> None:
    out = compile_specir_process_chain(
        sb=None,
        spec_uri="v://normref.com/std/JTG-F80-1-2017",
        component_type="drilled_pile",
        chapter="第7章 桩基础工程",
    )

    assert out["ok"] is True
    assert out["source"] == "builtin"
    steps = out["steps"]
    assert isinstance(steps, list)
    assert len(steps) == 6

    expected_pairs = [
        ("pile-prepare-01", "桥施2表"),
        ("pile-hole-02", "桥施7表"),
        ("pile-rebar-03", "桥施11表"),
        ("pile-pour-04", "桥施9表"),
        ("pile-acceptance-05", "桥施13表"),
        ("pile-subitem-06", "桥施64表"),
    ]

    for idx, (step_id, table_name) in enumerate(expected_pairs):
        step = steps[idx]
        assert step["step_id"] == step_id
        assert _table(step) == table_name
        if idx == 0:
            assert step["pre_conditions"] == []
        else:
            assert step["pre_conditions"] == [expected_pairs[idx - 1][1]]


def test_process_chain_default_steps_are_compiled_from_specir() -> None:
    component_uri = pile_component_uri("v://cn.zhongbei/YADGS", "YK0+500-main", "P3")

    chain = create_process_chain(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        component_uri=component_uri,
        chain_kind="drilled_pile",
        commit=False,
    )["chain"]
    compiled = compile_specir_process_chain(
        sb=None,
        spec_uri="v://normref.com/std/JTG-F80-1-2017",
        component_type="drilled_pile",
        component_uri=component_uri,
    )

    chain_steps = chain.get("steps")
    compiled_steps = compiled.get("steps")
    assert isinstance(chain_steps, list)
    assert isinstance(compiled_steps, list)

    chain_pairs = [(str(step.get("step_id") or ""), _table(step)) for step in chain_steps if isinstance(step, dict)]
    compiled_pairs = [
        (str(step.get("step_id") or ""), _table(step))
        for step in compiled_steps
        if isinstance(step, dict)
    ]
    assert chain_pairs == compiled_pairs


def test_compile_additional_component_types_have_expected_step_counts() -> None:
    expected_counts = {
        "prestressed_beam": 8,
        "subgrade": 5,
        "tunnel_lining": 7,
        "pavement": 6,
    }

    for component_type, expected in expected_counts.items():
        out = compile_specir_process_chain(
            sb=None,
            spec_uri="v://normref.com/std/JTG-F80-1-2017",
            component_type=component_type,
        )
        steps = out["steps"]
        assert isinstance(steps, list)
        assert len(steps) == expected
        assert steps[0]["pre_conditions"] == []
        for idx in range(1, len(steps)):
            assert steps[idx]["pre_conditions"] == [_table(steps[idx - 1])]
