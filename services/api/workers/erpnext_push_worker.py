from __future__ import annotations

import asyncio
import os
from typing import Any

from supabase import Client, create_client

from services.api.smu_flow_service import retry_erpnext_push_queue


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _bool_env(name: str, default: bool) -> bool:
    raw = str(os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name) or "").strip() or default)
    except Exception:
        return default


class ERPNextPushWorker:
    def __init__(self) -> None:
        self.enabled = _bool_env("ERPNEXT_PUSH_WORKER_ENABLED", True)
        self.interval_s = max(15, _int_env("ERPNEXT_PUSH_INTERVAL_S", 120))
        self.batch_size = max(1, _int_env("ERPNEXT_PUSH_BATCH_SIZE", 50))
        self._stop = asyncio.Event()

    def _client(self) -> Client | None:
        url = str(os.getenv("SUPABASE_URL") or "").strip()
        key = str(os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        if not url or not key:
            return None
        return create_client(url, key)

    def push_once(self) -> dict[str, Any]:
        sb = self._client()
        if sb is None:
            return {"ok": False, "reason": "supabase_not_configured"}
        return retry_erpnext_push_queue(sb=sb, limit=self.batch_size)

    async def run_forever(self) -> None:
        if not self.enabled:
            return
        while not self._stop.is_set():
            try:
                await asyncio.to_thread(self.push_once)
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_s)
            except asyncio.TimeoutError:
                continue

    async def shutdown(self) -> None:
        self._stop.set()
