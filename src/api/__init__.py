"""Compatibility API package."""

from .executor import router as executor_router  # noqa: F401
from .signpeg import router as signpeg_router  # noqa: F401
from .tool import router as tool_router  # noqa: F401

__all__ = ["signpeg_router", "executor_router", "tool_router"]
