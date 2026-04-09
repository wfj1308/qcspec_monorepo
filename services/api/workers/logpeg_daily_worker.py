from __future__ import annotations

import asyncio
from datetime import datetime
import os
from zoneinfo import ZoneInfo

from supabase import Client, create_client

from services.api.domain.logpeg.runtime import auto_generate_daily_logs, remind_unsigned_daily_logs

_SH_TZ = ZoneInfo("Asia/Shanghai")


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


class LogPegDailyWorker:
    def __init__(self) -> None:
        self.enabled = _bool_env("LOGPEG_WORKER_ENABLED", True)
        self.interval_s = max(30, _int_env("LOGPEG_WORKER_INTERVAL_S", 60))
        self.target_hour = min(max(_int_env("LOGPEG_WORKER_TARGET_HOUR", 18), 0), 23)
        self.target_minute = min(max(_int_env("LOGPEG_WORKER_TARGET_MINUTE", 0), 0), 59)
        self.remind_hour = min(max(_int_env("LOGPEG_WORKER_REMIND_HOUR", 8), 0), 23)
        self.remind_minute = min(max(_int_env("LOGPEG_WORKER_REMIND_MINUTE", 0), 0), 59)
        self._stop = asyncio.Event()
        self._last_trigger_date = ""
        self._last_remind_date = ""

    def _client(self) -> Client | None:
        url = str(os.getenv("SUPABASE_URL") or "").strip()
        key = str(os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        if not url or not key:
            return None
        return create_client(url, key)

    def generate_once(self) -> dict:
        sb = self._client()
        if sb is None:
            return {"ok": False, "reason": "supabase_not_configured"}
        today = datetime.now(_SH_TZ).date().isoformat()
        out = asyncio.run(auto_generate_daily_logs(sb=sb, date_text=today))
        return out.model_dump(mode="json")

    def remind_once(self) -> dict:
        sb = self._client()
        if sb is None:
            return {"ok": False, "reason": "supabase_not_configured"}
        out = asyncio.run(remind_unsigned_daily_logs(sb=sb))
        return out.model_dump(mode="json")

    async def run_forever(self) -> None:
        if not self.enabled:
            return
        while not self._stop.is_set():
            now = datetime.now(_SH_TZ)
            today = now.date().isoformat()
            should_generate = now.hour == self.target_hour and now.minute >= self.target_minute and self._last_trigger_date != today
            should_remind = now.hour == self.remind_hour and now.minute >= self.remind_minute and self._last_remind_date != today
            if should_generate:
                try:
                    await asyncio.to_thread(self.generate_once)
                    self._last_trigger_date = today
                except Exception:
                    pass
            if should_remind:
                try:
                    await asyncio.to_thread(self.remind_once)
                    self._last_remind_date = today
                except Exception:
                    pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_s)
            except asyncio.TimeoutError:
                continue

    async def shutdown(self) -> None:
        self._stop.set()
