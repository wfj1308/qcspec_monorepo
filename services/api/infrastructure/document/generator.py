"""Unified document generation façade."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from services.api.archive_service import create_dsp_package
from services.api.docx_engine import DocxEngine


class DocumentGenerator:
    def __init__(self) -> None:
        self.engine = DocxEngine()

    def render_report(self, *, report_type: str, proofs: list[dict[str, Any]], project_meta: dict[str, Any]) -> bytes:
        return self.engine.render_universal_report(report_type=report_type, proofs=proofs, project_meta=project_meta)

    def render_docpeg(self, **kwargs: Any) -> bytes:
        return self.engine.render_docpeg_report(**kwargs)

    def create_archive_package(self, **kwargs: Any) -> bytes:
        return create_dsp_package(**kwargs)


@lru_cache(maxsize=1)
def get_document_generator_singleton() -> DocumentGenerator:
    return DocumentGenerator()
