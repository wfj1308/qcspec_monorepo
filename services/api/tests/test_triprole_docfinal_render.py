from __future__ import annotations

from pathlib import Path

from services.api.domain.execution.triprole_docfinal_render import render_docfinal_artifacts


def test_render_docfinal_artifacts_with_evidence_and_custom_template(tmp_path: Path) -> None:
    template = tmp_path / "tpl.docx"
    template.write_bytes(b"tpl")
    context: dict[str, object] = {}

    result = render_docfinal_artifacts(
        module_file=tmp_path / "module.py",
        template_path=template,
        normalized_uri="v://boq/1-1-1",
        context=context,
        chain=[{"proof_id": "p1"}],
        sb=object(),
        render_docx=lambda **kwargs: (
            b"docx" if Path(kwargs["template_path"]).name == "tpl.docx" else b"bad"
        ),
        render_pdf=lambda **kwargs: b"pdf" if kwargs["docx_bytes"] == b"docx" else b"bad",
        get_evidence=lambda **_: {"evidence": [{"id": 1}, {"id": 2}]},
        build_zip=lambda **kwargs: (
            b"zip"
            if kwargs["report_pdf_bytes"] == b"pdf"
            and kwargs["docx_bytes"] == b"docx"
            and isinstance(kwargs["evidence_items"], list)
            else b"bad"
        ),
    )

    assert result["docx_bytes"] == b"docx"
    assert result["pdf_bytes"] == b"pdf"
    assert result["zip_bytes"] == b"zip"
    assert result["filename_base"] == "v_boq_1-1-1"
    assert context["evidence_count"] == 2
    assert context["evidence_source"] == "boq_chain"


def test_render_docfinal_artifacts_ignores_evidence_errors(tmp_path: Path) -> None:
    result = render_docfinal_artifacts(
        module_file=tmp_path / "module.py",
        template_path=None,
        normalized_uri="",
        context={},
        chain=[],
        sb=object(),
        render_docx=lambda **_: b"docx",
        render_pdf=lambda **_: b"pdf",
        get_evidence=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
        build_zip=lambda **kwargs: b"zip" if kwargs["evidence_items"] is None else b"bad",
    )

    assert result["zip_bytes"] == b"zip"
    assert result["filename_base"] == "docfinal"
