from __future__ import annotations

from services.api.domain.execution.triprole_component_docpeg import (
    build_component_docpeg_bundle,
    build_component_docpeg_context,
    render_component_docpeg_docx,
)


def _verification_payload() -> dict[str, object]:
    return {
        "project_uri": "v://cn.yanan/east-ring-expressway",
        "component_id": "MAIN-BEAM-L3",
        "component_uri": "v://cn.yanan/east-ring-expressway/component/MAIN-BEAM-L3",
        "kind": "precast_beam",
        "status": "QUALIFIED",
        "version": 2,
        "proof_hash": "COMP-1234567890ABCDEF",
        "within_tolerance": True,
        "total_delta": 0.0,
        "materials": [
            {
                "material_role": "steel",
                "boq_item_id": "403-1-2",
                "planned": 1885,
                "actual": 1885,
                "deviation_ratio": 0.0,
                "within_tolerance": True,
            },
            {
                "material_role": "concrete",
                "boq_item_id": "404-2-1",
                "planned": 23.6,
                "actual": 23.6,
                "deviation_ratio": 0.0,
                "within_tolerance": True,
            },
        ],
    }


def test_build_component_docpeg_context_contains_verify_uri() -> None:
    context = build_component_docpeg_context(
        verification=_verification_payload(),
        verify_base_url="https://verify.qcspec.com",
    )
    assert context["component_id"] == "MAIN-BEAM-L3"
    assert context["proof_hash"] == "COMP-1234567890ABCDEF"
    assert context["verify_uri"] == "https://verify.qcspec.com/component-proof/COMP-1234567890ABCDEF"
    assert len(context["materials"]) == 2


def test_render_component_docpeg_docx_fallback_generates_docx() -> None:
    context = build_component_docpeg_context(verification=_verification_payload())
    docx_bytes, template_used = render_component_docpeg_docx(
        context=context,
        template_path=None,
    )
    assert template_used == "fallback_programmatic"
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0


def test_build_component_docpeg_bundle_without_base64() -> None:
    bundle = build_component_docpeg_bundle(
        verification=_verification_payload(),
        include_docx_base64=False,
    )
    assert bundle["ok"] is True
    assert bundle["document_type"] == "component_report"
    assert bundle["proof_embedded"] is True
    assert bundle["qr_embedded"] is True
    assert bundle["docx_size"] > 0
    assert "docx_base64" not in bundle
