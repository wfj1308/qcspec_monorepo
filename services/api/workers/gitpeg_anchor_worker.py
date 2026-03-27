from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import json
import os
from typing import Any

from supabase import Client, create_client


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


def _merkle_root(items: list[str]) -> str:
    if not items:
        return ""
    layer = [hashlib.sha256(x.encode("utf-8")).hexdigest() for x in items]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        nxt: list[str] = []
        for i in range(0, len(layer), 2):
            nxt.append(hashlib.sha256(f"{layer[i]}{layer[i+1]}".encode("utf-8")).hexdigest())
        layer = nxt
    return layer[0]


class GitPegAnchorWorker:
    def __init__(self) -> None:
        self.enabled = _bool_env("MOCK_GITPEG_WORKER_ENABLED", True)
        self.interval_s = max(5, _int_env("MOCK_GITPEG_ANCHOR_INTERVAL_S", 30))
        self.batch_size = max(10, _int_env("MOCK_GITPEG_ANCHOR_BATCH_SIZE", 200))
        self.base_height = _int_env("MOCK_GITPEG_BASE_HEIGHT", 8847000)
        self._stop = asyncio.Event()
        self._height = self.base_height

    def _client(self) -> Client | None:
        url = str(os.getenv("SUPABASE_URL") or "").strip()
        key = str(os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        if not url or not key:
            return None
        return create_client(url, key)

    def _load_candidates(self, sb: Client) -> list[dict[str, Any]]:
        rows = (
            sb.table("proof_utxo")
            .select("proof_id,proof_hash,gitpeg_anchor,created_at")
            .order("created_at", desc=False)
            .limit(self.batch_size)
            .execute()
            .data
            or []
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            anchor = _to_text((row or {}).get("gitpeg_anchor")).strip()
            if not anchor or "height=" not in anchor.lower():
                out.append(row)
        return out

    def anchor_once(self) -> dict[str, Any]:
        sb = self._client()
        if sb is None:
            return {"ok": False, "reason": "supabase_not_configured"}

        candidates = self._load_candidates(sb)
        if not candidates:
            return {"ok": True, "anchored": 0, "height": self._height}

        hashes = [_to_text(x.get("proof_hash")) for x in candidates if _to_text(x.get("proof_hash"))]
        merkle_root = _merkle_root(hashes)
        self._height += 1
        block_height = self._height
        batch_id = hashlib.sha256(
            json.dumps(
                {"h": block_height, "m": merkle_root, "count": len(candidates)},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:8]
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        anchored = 0
        for row in candidates:
            proof_id = _to_text(row.get("proof_id")).strip()
            if not proof_id:
                continue
            proof_hash = _to_text(row.get("proof_hash")).strip()
            anchor_ref = (
                f"GitPeg#{batch_id}-{proof_id[-6:]};"
                f"height={block_height};"
                f"merkle={merkle_root[:16]};"
                f"proof={proof_hash[:16]};"
                f"ts={ts}"
            )
            try:
                sb.table("proof_utxo").update({"gitpeg_anchor": anchor_ref}).eq("proof_id", proof_id).execute()
                anchored += 1
            except Exception:
                continue
        return {
            "ok": True,
            "anchored": anchored,
            "height": block_height,
            "merkle_root": merkle_root,
            "batch_id": batch_id,
        }

    async def run_forever(self) -> None:
        if not self.enabled:
            return
        while not self._stop.is_set():
            try:
                await asyncio.to_thread(self.anchor_once)
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_s)
            except asyncio.TimeoutError:
                continue

    async def shutdown(self) -> None:
        self._stop.set()

