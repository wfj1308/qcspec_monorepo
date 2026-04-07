"""Bridge-level schedule engines with Trip sync and full-line aggregation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import re
from typing import Any

from fastapi import HTTPException

from services.api.domain.utxo.integrations import ProofUTXOEngine


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    text = _to_text(value).strip().replace(",", "")
    if not text:
        return float(default)
    try:
        return float(text)
    except Exception:
        return float(default)


def _clamp_progress(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _round(value: float, ndigits: int = 6) -> float:
    return round(float(value), ndigits)


def _normalize_bridge_slug(name: str) -> str:
    text = _to_text(name).strip().lower()
    text = text.replace("\\", "-").replace("/", "-")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff_-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "bridge"


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _bridge_uri(project_uri: str, bridge_slug: str) -> str:
    return f"{_to_text(project_uri).strip().rstrip('/')}/bridge/{bridge_slug}"


def _schedule_uri(bridge_uri: str) -> str:
    return f"{bridge_uri.rstrip('/')}/schedule/main"


@dataclass(slots=True)
class Milestone:
    milestone_id: str
    name: str
    planned_start: str
    planned_end: str
    status: str = "pending"


@dataclass(slots=True)
class ScheduleTask:
    task_id: str
    task_name: str
    planned_start: str
    planned_end: str
    duration_days: float
    logic_type: str = "FS"
    predecessors: list[str] = field(default_factory=list)
    component_uri: str = ""
    boq_item_uri: str = ""
    bound_trip_ids: list[str] = field(default_factory=list)
    progress: float = 0.0
    status: str = "pending"


@dataclass(slots=True)
class BridgeSchedule:
    schedule_id: str
    bridge_uri: str
    bridge_name: str
    bridge_slug: str
    project_uri: str
    baseline_start: str
    baseline_end: str
    milestones: list[Milestone] = field(default_factory=list)
    tasks: list[ScheduleTask] = field(default_factory=list)
    current_progress: float = 0.0
    version: int = 1
    updated_at: str = ""


def _derive_task_status(progress: float) -> str:
    p = _clamp_progress(progress)
    if p >= 100.0:
        return "done"
    if p > 0:
        return "in_progress"
    return "pending"


def _schedule_progress(tasks: list[ScheduleTask]) -> float:
    if not tasks:
        return 0.0
    total_weight = 0.0
    weighted = 0.0
    for task in tasks:
        weight = max(float(task.duration_days or 0.0), 1.0)
        total_weight += weight
        weighted += weight * _clamp_progress(task.progress)
    if total_weight <= 1e-9:
        return 0.0
    return _round(weighted / total_weight, 4)


def _create_proof(
    *,
    sb: Any,
    commit: bool,
    proof_id: str,
    owner_uri: str,
    project_uri: str,
    proof_type: str,
    result: str,
    segment_uri: str,
    norm_uri: str,
    state_data: dict[str, Any],
) -> dict[str, Any]:
    preview = {
        "proof_id": proof_id,
        "proof_type": proof_type,
        "result": result,
        "segment_uri": segment_uri,
        "state_data": state_data,
        "committed": False,
    }
    if not commit or sb is None:
        return preview
    row = ProofUTXOEngine(sb).create(
        proof_id=proof_id,
        owner_uri=owner_uri,
        project_uri=project_uri,
        proof_type=proof_type,
        result=result,
        state_data=state_data,
        norm_uri=norm_uri,
        segment_uri=segment_uri,
        signer_uri=owner_uri,
        signer_role="SYSTEM",
    )
    return {
        **preview,
        "committed": True,
        "row": row,
    }


def _fetch_schedule_rows(*, sb: Any, project_uri: str) -> list[dict[str, Any]]:
    if sb is None:
        return []
    try:
        rows = (
            sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", _to_text(project_uri).strip())
            .eq("proof_type", "node")
            .order("created_at", desc=False)
            .limit(20000)
            .execute()
            .data
            or []
        )
        return [row for row in rows if isinstance(row, dict)]
    except Exception as exc:
        raise HTTPException(502, f"failed to query bridge schedules: {exc}") from exc


def _latest_bridge_schedules(*, sb: Any, project_uri: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _fetch_schedule_rows(sb=sb, project_uri=project_uri):
        sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
        if _to_text(sd.get("entity_type")).strip() != "bridge_schedule":
            continue
        slug = _to_text(sd.get("bridge_slug")).strip()
        if not slug:
            continue
        latest[slug] = sd
    return latest


def _normalize_milestones(raw: Any, *, bridge_uri: str) -> list[Milestone]:
    milestones: list[Milestone] = []
    if not isinstance(raw, list):
        return milestones
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        name = _to_text(item.get("name")).strip()
        if not name:
            continue
        milestone_id = _to_text(item.get("milestone_id")).strip() or f"MS-{_sha16(f'{bridge_uri}:{name}:{idx}').upper()[:10]}"
        milestones.append(
            Milestone(
                milestone_id=milestone_id,
                name=name,
                planned_start=_to_text(item.get("planned_start")).strip(),
                planned_end=_to_text(item.get("planned_end")).strip(),
                status=_to_text(item.get("status")).strip() or "pending",
            )
        )
    return milestones


def _normalize_tasks(raw: Any, *, bridge_uri: str) -> list[ScheduleTask]:
    tasks: list[ScheduleTask] = []
    if not isinstance(raw, list):
        return tasks
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        name = _to_text(item.get("task_name") or item.get("name")).strip()
        if not name:
            continue
        task_id = _to_text(item.get("task_id")).strip() or f"TSK-{_sha16(f'{bridge_uri}:{name}:{idx}').upper()[:10]}"
        duration = _to_float(item.get("duration_days"), 1.0)
        if duration <= 0:
            duration = 1.0
        progress = _clamp_progress(_to_float(item.get("progress"), 0.0))
        task = ScheduleTask(
            task_id=task_id,
            task_name=name,
            planned_start=_to_text(item.get("planned_start")).strip(),
            planned_end=_to_text(item.get("planned_end")).strip(),
            duration_days=duration,
            logic_type=_to_text(item.get("logic_type")).strip().upper() or "FS",
            predecessors=[str(x).strip() for x in (item.get("predecessors") or []) if str(x).strip()],
            component_uri=_to_text(item.get("component_uri")).strip(),
            boq_item_uri=_to_text(item.get("boq_item_uri")).strip(),
            bound_trip_ids=[str(x).strip() for x in (item.get("bound_trip_ids") or []) if str(x).strip()],
            progress=progress,
            status=_derive_task_status(progress),
        )
        tasks.append(task)
    return tasks


def _schedule_state(schedule: BridgeSchedule, *, action: str) -> dict[str, Any]:
    payload = asdict(schedule)
    payload.update(
        {
            "entity_type": "bridge_schedule",
            "action": action,
        }
    )
    return payload


def create_bridge_schedule(
    *,
    sb: Any,
    project_uri: str,
    bridge_name: str,
    body: dict[str, Any],
    owner_uri: str = "",
    commit: bool = False,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    b_name = _to_text(bridge_name).strip()
    if not b_name:
        raise HTTPException(400, "bridge_name is required")
    slug = _normalize_bridge_slug(b_name)
    bridge_uri = _bridge_uri(p_uri, slug)
    schedule_uri = _schedule_uri(bridge_uri)
    baseline_start = _to_text(body.get("baseline_start")).strip()
    baseline_end = _to_text(body.get("baseline_end")).strip()
    if not baseline_start or not baseline_end:
        raise HTTPException(400, "baseline_start and baseline_end are required")
    milestones = _normalize_milestones(body.get("milestones"), bridge_uri=bridge_uri)
    tasks = _normalize_tasks(body.get("tasks"), bridge_uri=bridge_uri)
    current_progress = _schedule_progress(tasks)
    now = datetime.now(UTC).isoformat()
    existing = _latest_bridge_schedules(sb=sb, project_uri=p_uri).get(slug)
    version = int(existing.get("version") or 0) + 1 if existing else 1
    schedule = BridgeSchedule(
        schedule_id=f"SCH-{_sha16(f'{schedule_uri}:{now}').upper()}",
        bridge_uri=bridge_uri,
        bridge_name=b_name,
        bridge_slug=slug,
        project_uri=p_uri,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        milestones=milestones,
        tasks=tasks,
        current_progress=current_progress,
        version=version,
        updated_at=now,
    )
    normalized_owner = _to_text(owner_uri).strip() or f"{p_uri.rstrip('/')}/role/system/"
    entity_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-BRIDGE-SCHEDULE-{_sha16(f'{schedule.schedule_id}:entity').upper()}",
        owner_uri=normalized_owner,
        project_uri=p_uri,
        proof_type="node",
        result="PASS",
        segment_uri=schedule_uri,
        norm_uri="v://norm/NormPeg/BridgeSchedule/1.0",
        state_data=_schedule_state(schedule, action="compiled"),
    )
    compiled_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-BRIDGE-SCHEDULE-COMPILED-{_sha16(f'{schedule.schedule_id}:{now}').upper()}",
        owner_uri=normalized_owner,
        project_uri=p_uri,
        proof_type="inspection",
        result="PASS",
        segment_uri=f"{schedule_uri}/proofs",
        norm_uri="v://norm/NormPeg/BridgeSchedulePlan/1.0",
        state_data={
            "proof_kind": "bridge_schedule_compiled",
            "bridge_uri": bridge_uri,
            "schedule_id": schedule.schedule_id,
            "task_count": len(tasks),
            "milestone_count": len(milestones),
            "current_progress": current_progress,
            "timestamp": now,
        },
    )
    return {
        "ok": True,
        "bridge_uri": bridge_uri,
        "schedule_uri": schedule_uri,
        "schedule": _schedule_state(schedule, action="compiled"),
        "proofs": {
            "entity_proof": entity_proof,
            "compiled_proof": compiled_proof,
        },
    }


def get_bridge_schedule(*, sb: Any, project_uri: str, bridge_name: str) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    b_name = _to_text(bridge_name).strip()
    if not b_name:
        raise HTTPException(400, "bridge_name is required")
    slug = _normalize_bridge_slug(b_name)
    all_schedules = _latest_bridge_schedules(sb=sb, project_uri=p_uri)
    latest = all_schedules.get(slug)
    if not latest:
        normalized_name = b_name.lower()
        for sched in all_schedules.values():
            if _to_text(sched.get("bridge_name")).strip().lower() == normalized_name:
                latest = sched
                break
    if not latest:
        raise HTTPException(404, "bridge schedule not found")
    schedule_uri = _schedule_uri(_to_text(latest.get("bridge_uri")).strip())
    return {
        "ok": True,
        "bridge_uri": _to_text(latest.get("bridge_uri")).strip(),
        "schedule_uri": schedule_uri,
        "schedule": latest,
    }


def sync_bridge_schedule_progress(
    *,
    sb: Any,
    project_uri: str,
    bridge_name: str,
    body: dict[str, Any],
    owner_uri: str = "",
    commit: bool = False,
) -> dict[str, Any]:
    found = get_bridge_schedule(sb=sb, project_uri=project_uri, bridge_name=bridge_name)
    schedule = found.get("schedule") if isinstance(found.get("schedule"), dict) else {}
    tasks_raw = schedule.get("tasks") if isinstance(schedule.get("tasks"), list) else []
    tasks = _normalize_tasks(tasks_raw, bridge_uri=_to_text(schedule.get("bridge_uri")).strip())
    completed_trip_ids = {str(x).strip() for x in (body.get("completed_trip_ids") or []) if str(x).strip()}
    task_progress_updates = body.get("task_progress_updates") if isinstance(body.get("task_progress_updates"), dict) else {}
    planned_progress_by_task = body.get("planned_progress_by_task") if isinstance(body.get("planned_progress_by_task"), dict) else {}
    deviation_threshold = max(_to_float(body.get("gate_deviation_threshold"), 15.0), 0.0)

    changed_tasks = 0
    deviation_tasks: list[dict[str, Any]] = []
    for task in tasks:
        before = _clamp_progress(task.progress)
        if task.task_id in task_progress_updates:
            task.progress = _clamp_progress(_to_float(task_progress_updates.get(task.task_id), before))
        elif completed_trip_ids and any(trip_id in completed_trip_ids for trip_id in task.bound_trip_ids):
            task.progress = 100.0
        task.status = _derive_task_status(task.progress)
        if abs(task.progress - before) > 1e-9:
            changed_tasks += 1
        planned = _to_float(planned_progress_by_task.get(task.task_id), before)
        delta = abs(task.progress - planned)
        if delta > deviation_threshold:
            deviation_tasks.append(
                {
                    "task_id": task.task_id,
                    "task_name": task.task_name,
                    "planned_progress": _round(planned, 4),
                    "actual_progress": _round(task.progress, 4),
                    "delta": _round(delta, 4),
                }
            )

    current_progress = _schedule_progress(tasks)
    now = datetime.now(UTC).isoformat()
    version = int(schedule.get("version") or 1) + 1
    bridge_uri = _to_text(schedule.get("bridge_uri")).strip()
    schedule_uri = _schedule_uri(bridge_uri)
    normalized_owner = _to_text(owner_uri).strip() or f"{_to_text(project_uri).strip().rstrip('/')}/role/system/"

    updated_schedule = {
        **schedule,
        "tasks": [asdict(task) for task in tasks],
        "current_progress": current_progress,
        "version": version,
        "updated_at": now,
        "entity_type": "bridge_schedule",
        "action": "trip_sync",
    }

    entity_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-BRIDGE-SCHEDULE-{_sha16(f'{schedule_uri}:{version}').upper()}",
        owner_uri=normalized_owner,
        project_uri=_to_text(project_uri).strip(),
        proof_type="node",
        result="PASS",
        segment_uri=schedule_uri,
        norm_uri="v://norm/NormPeg/BridgeSchedule/1.0",
        state_data=updated_schedule,
    )
    sync_proof = _create_proof(
        sb=sb,
        commit=bool(commit),
        proof_id=f"GP-BRIDGE-SCHEDULE-SYNC-{_sha16(f'{schedule_uri}:{now}').upper()}",
        owner_uri=normalized_owner,
        project_uri=_to_text(project_uri).strip(),
        proof_type="inspection",
        result="PASS" if not deviation_tasks else "OBSERVE",
        segment_uri=f"{schedule_uri}/trips",
        norm_uri="v://norm/NormPeg/BridgeScheduleTripSync/1.0",
        state_data={
            "proof_kind": "bridge_schedule_trip_sync",
            "bridge_uri": bridge_uri,
            "completed_trip_ids": sorted(completed_trip_ids),
            "changed_tasks": changed_tasks,
            "current_progress": current_progress,
            "deviation_tasks": deviation_tasks,
            "timestamp": now,
        },
    )
    gate_review_proof = None
    if deviation_tasks:
        gate_review_proof = _create_proof(
            sb=sb,
            commit=bool(commit),
            proof_id=f"GP-BRIDGE-SCHEDULE-GATE-{_sha16(f'{schedule_uri}:gate:{now}').upper()}",
            owner_uri=normalized_owner,
            project_uri=_to_text(project_uri).strip(),
            proof_type="inspection",
            result="FAIL",
            segment_uri=f"{schedule_uri}/gates",
            norm_uri="v://norm/NormPeg/BridgeScheduleGate/1.0",
            state_data={
                "proof_kind": "bridge_schedule_gate_review",
                "bridge_uri": bridge_uri,
                "deviation_threshold": deviation_threshold,
                "deviation_tasks": deviation_tasks,
                "action": "auto_gate_review_triggered",
                "timestamp": now,
            },
        )

    return {
        "ok": True,
        "bridge_uri": bridge_uri,
        "schedule_uri": schedule_uri,
        "schedule": updated_schedule,
        "proofs": {
            "entity_proof": entity_proof,
            "sync_proof": sync_proof,
            "gate_review_proof": gate_review_proof,
        },
    }


def get_project_full_line_schedule_summary(*, sb: Any, project_uri: str) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    schedules = _latest_bridge_schedules(sb=sb, project_uri=p_uri)
    bridge_rows: list[dict[str, Any]] = []
    total_tasks = 0
    total_progress_weighted = 0.0
    for slug, sched in sorted(schedules.items()):
        tasks = sched.get("tasks") if isinstance(sched.get("tasks"), list) else []
        task_count = len(tasks)
        done_tasks = sum(1 for task in tasks if isinstance(task, dict) and _to_text(task.get("status")).strip() == "done")
        progress = _to_float(sched.get("current_progress"), 0.0)
        total_tasks += task_count
        total_progress_weighted += progress * max(task_count, 1)
        bridge_rows.append(
            {
                "bridge_slug": slug,
                "bridge_name": _to_text(sched.get("bridge_name")).strip(),
                "bridge_uri": _to_text(sched.get("bridge_uri")).strip(),
                "schedule_uri": _schedule_uri(_to_text(sched.get("bridge_uri")).strip()),
                "baseline_start": _to_text(sched.get("baseline_start")).strip(),
                "baseline_end": _to_text(sched.get("baseline_end")).strip(),
                "task_count": task_count,
                "done_task_count": done_tasks,
                "current_progress": _round(progress, 4),
                "version": int(sched.get("version") or 1),
            }
        )
    if bridge_rows:
        project_progress = total_progress_weighted / sum(max(row["task_count"], 1) for row in bridge_rows)
    else:
        project_progress = 0.0
    return {
        "ok": True,
        "project_uri": p_uri,
        "full_line_schedule_uri": f"{p_uri.rstrip('/')}/full-line/schedule",
        "bridge_count": len(bridge_rows),
        "total_task_count": total_tasks,
        "project_progress": _round(project_progress, 4),
        "bridges": bridge_rows,
    }


__all__ = [
    "BridgeSchedule",
    "Milestone",
    "ScheduleTask",
    "create_bridge_schedule",
    "get_bridge_schedule",
    "get_project_full_line_schedule_summary",
    "sync_bridge_schedule_progress",
]

