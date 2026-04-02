"""
Background job service for SMU BOQ genesis import.

This prevents heavy import parsing from blocking unrelated APIs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
import time
import traceback
import uuid
from typing import Any

from fastapi import HTTPException

from services.api.supabase_provider import get_supabase_client

_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_MAX_BYTES = 60 * 1024 * 1024
_MAX_JOB_RETENTION = 120


def _import_genesis_trip(*, sb: Any, **kwargs: Any) -> dict[str, Any]:
    from services.api.domain.smu.flows import import_genesis_trip

    return import_genesis_trip(sb=sb, **kwargs)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    inner = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    return {
        "ok": bool(payload.get("ok")),
        "phase": payload.get("phase"),
        "project_uri": payload.get("project_uri"),
        "total_items": payload.get("total_items", inner.get("total_items")),
        "total_nodes": payload.get("total_nodes", inner.get("total_nodes")),
        "leaf_nodes": payload.get("leaf_nodes", inner.get("leaf_nodes")),
        "group_nodes": payload.get("group_nodes", inner.get("group_nodes")),
        "success_count": payload.get("success_count", inner.get("success_count")),
        "hierarchy_root_hash": payload.get("hierarchy_root_hash", inner.get("hierarchy_root_hash")),
        "errors": list(payload.get("errors") or inner.get("errors") or [])[:5],
    }


def _trim_jobs() -> None:
    with _LOCK:
        if len(_JOBS) <= _MAX_JOB_RETENTION:
            return
        # Keep newest jobs only.
        ordered = sorted(
            _JOBS.items(),
            key=lambda kv: str((kv[1] or {}).get("created_at") or ""),
            reverse=True,
        )
        keep = dict(ordered[:_MAX_JOB_RETENTION])
        _JOBS.clear()
        _JOBS.update(keep)


def start_smu_import_job(
    *,
    upload_file_name: str,
    upload_content: bytes,
    project_uri: str,
    project_id: str = "",
    boq_root_uri: str = "",
    norm_context_root_uri: str = "",
    owner_uri: str = "",
    commit: bool = True,
) -> dict[str, Any]:
    content = upload_content or b""
    if not content:
        raise HTTPException(400, "empty upload file")
    if len(content) > _MAX_BYTES:
        raise HTTPException(400, "upload file too large, max 60MB")

    normalized_project_uri = str(project_uri or "").strip()
    with _LOCK:
        active = None
        for row in _JOBS.values():
            if str((row or {}).get("project_uri") or "").strip() != normalized_project_uri:
                continue
            if str((row or {}).get("state") or "") in {"queued", "running"}:
                active = dict(row)
                break
        if active:
            return {
                "ok": True,
                "reused": True,
                "job_id": str(active.get("job_id") or ""),
                "state": str(active.get("state") or "running"),
                "progress": int(active.get("progress") or 0),
                "message": "已有导入任务在执行，已自动复用",
            }

    job_id = f"smu-import-{uuid.uuid4().hex[:16]}"
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "state": "queued",
            "stage": "queued",
            "progress": 0,
            "message": "任务已排队，等待执行",
            "created_at": _utc_iso(),
            "started_at": None,
            "finished_at": None,
            "project_uri": str(project_uri or ""),
            "file_name": str(upload_file_name or ""),
            "result": None,
            "error": None,
        }

    def _runner() -> None:
        def _update_status(*, stage: str, progress: int | None = None, message: str | None = None, state: str | None = None) -> None:
            with _LOCK:
                job = _JOBS.get(job_id)
                if not job:
                    return
                if state:
                    job["state"] = state
                if stage:
                    job["stage"] = stage
                if progress is not None:
                    current = int(job.get("progress") or 0)
                    target = max(0, min(100, int(progress)))
                    job["progress"] = max(current, target)
                if message:
                    job["message"] = str(message)

        heartbeat_stop = threading.Event()

        def _heartbeat() -> None:
            while not heartbeat_stop.is_set():
                time.sleep(2)
                with _LOCK:
                    job = _JOBS.get(job_id)
                    if not job or str(job.get("state")) != "running":
                        return
                    current = int(job.get("progress") or 0)
                    if current < 90:
                        job["progress"] = min(90, current + 2)

        with _LOCK:
            job = _JOBS.get(job_id)
            if not job:
                return
            job["started_at"] = _utc_iso()
        _update_status(state="running", stage="parsing", progress=10, message="开始解析 BOQ 文件")
        try:
            sb = get_supabase_client()
            _update_status(stage="building_tree", progress=30, message="生成主权资产树并写链（大文件约 1-3 分钟）")
            hb = threading.Thread(target=_heartbeat, name=f"smu-import-heartbeat-{job_id}", daemon=True)
            hb.start()

            payload = _import_genesis_trip(
                sb=sb,
                project_uri=project_uri,
                project_id=project_id,
                upload_file_name=upload_file_name,
                upload_content=content,
                boq_root_uri=boq_root_uri,
                norm_context_root_uri=norm_context_root_uri,
                owner_uri=owner_uri,
                commit=bool(commit),
                progress_hook=lambda stage, progress, message: _update_status(
                    stage=str(stage or "running"),
                    progress=int(progress or 0),
                    message=str(message or ""),
                ),
            )

            with _LOCK:
                job = _JOBS.get(job_id)
                if job:
                    job.update(
                        {
                            "state": "success",
                            "stage": "completed",
                            "progress": 100,
                            "message": "导入完成",
                            "finished_at": _utc_iso(),
                            "result": _compact_result(payload),
                            "error": None,
                        }
                    )
        except Exception as exc:
            with _LOCK:
                job = _JOBS.get(job_id)
                if job:
                    job.update(
                        {
                            "state": "failed",
                            "stage": "failed",
                            "progress": 100,
                            "message": "导入失败",
                            "finished_at": _utc_iso(),
                            "error": {
                                "type": exc.__class__.__name__,
                                "detail": str(exc),
                                "traceback": traceback.format_exc(limit=6),
                            },
                        }
                    )
        finally:
            heartbeat_stop.set()
            _trim_jobs()

    t = threading.Thread(target=_runner, name=f"smu-import-{job_id}", daemon=True)
    t.start()
    return {"ok": True, "job_id": job_id, "state": "queued", "progress": 0, "message": "任务已创建"}


def get_smu_import_job(job_id: str) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise HTTPException(400, "job_id is required")
    with _LOCK:
        row = _JOBS.get(jid)
        if not row:
            raise HTTPException(404, "import job not found")
        return dict(row)


def get_active_smu_import_job(*, project_uri: str) -> dict[str, Any]:
    p_uri = str(project_uri or "").strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    with _LOCK:
        active_rows = [
            dict(row)
            for row in _JOBS.values()
            if str((row or {}).get("project_uri") or "").strip() == p_uri
            and str((row or {}).get("state") or "") in {"queued", "running"}
        ]
    if not active_rows:
        return {"ok": True, "active": False}
    active_rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    top = active_rows[0]
    return {
        "ok": True,
        "active": True,
        "job_id": str(top.get("job_id") or ""),
        "state": str(top.get("state") or ""),
        "stage": str(top.get("stage") or ""),
        "progress": int(top.get("progress") or 0),
        "message": str(top.get("message") or ""),
        "created_at": top.get("created_at"),
        "started_at": top.get("started_at"),
        "file_name": str(top.get("file_name") or ""),
    }
