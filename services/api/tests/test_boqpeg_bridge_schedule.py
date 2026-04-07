from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import HTTPException

from services.api.domain.boqpeg.runtime.bridge_schedule import (
    create_bridge_schedule,
    get_bridge_schedule,
    get_project_full_line_schedule_summary,
    sync_bridge_schedule_progress,
)


@dataclass
class _ExecResult:
    data: list[dict[str, Any]]


class _FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def select(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def eq(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> "_FakeQuery":
        return self

    def execute(self) -> _ExecResult:
        return _ExecResult(data=self.rows)


class _FakeSupabase:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self.rows)


def test_create_bridge_schedule_preview() -> None:
    out = create_bridge_schedule(
        sb=None,
        project_uri="v://cn.zhongbei/YADGS",
        bridge_name="YK0+500 主桥",
        body={
            "baseline_start": "2026-04-01",
            "baseline_end": "2026-08-30",
            "milestones": [{"name": "桩基完成", "planned_start": "2026-04-01", "planned_end": "2026-05-10"}],
            "tasks": [
                {
                    "task_name": "桩基施工",
                    "planned_start": "2026-04-01",
                    "planned_end": "2026-05-10",
                    "duration_days": 40,
                    "bound_trip_ids": ["TRIP-PILE-001"],
                }
            ],
        },
        commit=False,
    )
    assert out["ok"] is True
    assert out["schedule_uri"].endswith("/schedule/main")
    assert out["schedule"]["current_progress"] == 0.0
    assert len(out["schedule"]["tasks"]) == 1


def test_get_and_sync_bridge_schedule() -> None:
    rows = [
        {
            "state_data": {
                "entity_type": "bridge_schedule",
                "bridge_slug": "yk0-500-main",
                "bridge_name": "YK0+500 主桥",
                "bridge_uri": "v://cn.zhongbei/YADGS/bridge/yk0-500-main",
                "baseline_start": "2026-04-01",
                "baseline_end": "2026-08-30",
                "tasks": [
                    {
                        "task_id": "TSK-1",
                        "task_name": "pile foundation",
                        "planned_start": "2026-04-01",
                        "planned_end": "2026-05-01",
                        "duration_days": 30,
                        "bound_trip_ids": ["TRIP-001"],
                        "progress": 20,
                        "status": "in_progress",
                    }
                ],
                "current_progress": 20,
                "version": 1,
            }
        }
    ]
    sb = _FakeSupabase(rows)
    fetched = get_bridge_schedule(sb=sb, project_uri="v://cn.zhongbei/YADGS", bridge_name="YK0+500 主桥")
    assert fetched["ok"] is True
    assert fetched["schedule"]["current_progress"] == 20

    synced = sync_bridge_schedule_progress(
        sb=sb,
        project_uri="v://cn.zhongbei/YADGS",
        bridge_name="YK0+500 主桥",
        body={
            "completed_trip_ids": ["TRIP-001"],
            "task_progress_updates": {},
            "planned_progress_by_task": {"TSK-1": 50},
            "gate_deviation_threshold": 10,
        },
        commit=False,
    )
    assert synced["ok"] is True
    assert synced["schedule"]["current_progress"] == 100.0
    assert synced["proofs"]["sync_proof"]["state_data"]["proof_kind"] == "bridge_schedule_trip_sync"
    assert synced["proofs"]["gate_review_proof"]["state_data"]["proof_kind"] == "bridge_schedule_gate_review"


def test_full_line_schedule_summary_and_not_found() -> None:
    rows = [
        {
            "state_data": {
                "entity_type": "bridge_schedule",
                "bridge_slug": "yk0-500-main",
                "bridge_name": "YK0+500 主桥",
                "bridge_uri": "v://cn.zhongbei/YADGS/bridge/yk0-500-main",
                "baseline_start": "2026-04-01",
                "baseline_end": "2026-08-30",
                "tasks": [
                    {"task_id": "1", "status": "done"},
                    {"task_id": "2", "status": "in_progress"},
                ],
                "current_progress": 50,
                "version": 2,
            }
        },
        {
            "state_data": {
                "entity_type": "bridge_schedule",
                "bridge_slug": "yk1-200-side",
                "bridge_name": "YK1+200 引桥",
                "bridge_uri": "v://cn.zhongbei/YADGS/bridge/yk1-200-side",
                "baseline_start": "2026-04-15",
                "baseline_end": "2026-09-10",
                "tasks": [
                    {"task_id": "1", "status": "done"},
                    {"task_id": "2", "status": "done"},
                ],
                "current_progress": 100,
                "version": 1,
            }
        },
    ]
    sb = _FakeSupabase(rows)
    out = get_project_full_line_schedule_summary(sb=sb, project_uri="v://cn.zhongbei/YADGS")
    assert out["ok"] is True
    assert out["bridge_count"] == 2
    assert out["total_task_count"] == 4
    assert out["project_progress"] > 70

    with pytest.raises(HTTPException) as exc:
        get_bridge_schedule(sb=sb, project_uri="v://cn.zhongbei/YADGS", bridge_name="不存在")
    assert exc.value.status_code == 404
