"""Shared service primitives for the API application layer."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from fastapi import HTTPException


class BaseService:
    """Base class that centralizes shared dependency access and error wrapping."""

    def __init__(self, *, sb: Any | None = None) -> None:
        self.sb = sb

    def require_supabase(self) -> Any:
        if self.sb is None:
            raise RuntimeError("Supabase client has not been injected")
        return self.sb

    async def run_guarded(self, operation: str, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        try:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - defensive service boundary
            raise HTTPException(status_code=500, detail=f"{operation} failed: {exc}") from exc
