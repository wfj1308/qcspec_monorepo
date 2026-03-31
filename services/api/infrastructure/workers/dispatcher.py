"""Task dispatch helpers for heavy API jobs."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import BackgroundTasks


class TaskDispatcher:
    def dispatch(self, tasks: BackgroundTasks | None, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if tasks is not None:
            tasks.add_task(fn, *args, **kwargs)
            return {"scheduled": True}
        fn(*args, **kwargs)
        return {"scheduled": False}
