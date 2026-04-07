"""Compatibility shim for legacy SMU BOQ upload parser path."""

from services.api.domain.boqpeg.integrations import parse_boq_upload

__all__ = ["parse_boq_upload"]

