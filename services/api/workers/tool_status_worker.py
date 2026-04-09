"""Tool status checker worker for ToolPeg."""

from __future__ import annotations

from typing import Any

from services.api.domain.signpeg.runtime.toolpeg import check_tool_status
from services.api.infrastructure.database import get_supabase_client


class ToolStatusWorker:
    """Daily tool-status checker (recommended cron: 08:00 local)."""

    def __init__(self, *, sb: Any | None = None) -> None:
        self.sb = sb or get_supabase_client()

    async def run_once(self) -> dict[str, Any]:
        return check_tool_status(self.sb)


async def check_tool_status_job() -> dict[str, Any]:
    worker = ToolStatusWorker()
    return await worker.run_once()


__all__ = ["ToolStatusWorker", "check_tool_status_job"]

