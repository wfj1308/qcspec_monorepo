"""Executor certificate expiry checks for ExecutorPeg."""

from __future__ import annotations

from typing import Any

from services.api.domain.signpeg.runtime.signpeg import check_executor_certificate_expiry
from services.api.infrastructure.database import get_supabase_client


class ExecutorCertificateWorker:
    """Daily certificate checker (intended cron time: 08:00 local)."""

    def __init__(self, *, sb: Any | None = None) -> None:
        self.sb = sb or get_supabase_client()

    async def run_once(self) -> dict[str, Any]:
        return check_executor_certificate_expiry(self.sb)


async def check_certificate_expiry_job() -> dict[str, Any]:
    worker = ExecutorCertificateWorker()
    return await worker.run_once()


__all__ = ["ExecutorCertificateWorker", "check_certificate_expiry_job"]

