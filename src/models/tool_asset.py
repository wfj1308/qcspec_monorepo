"""Compatibility exports for tool-asset models."""

from services.api.domain.boqpeg.models import (
    ToolAsset,
    ToolAssetRegisterRequest,
    ToolAssetStatusResult,
)

__all__ = [
    "ToolAsset",
    "ToolAssetRegisterRequest",
    "ToolAssetStatusResult",
]
