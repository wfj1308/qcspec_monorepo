"""Executor scheduler and delegation runtime."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from services.api.domain.signpeg.models import Delegation, DelegationRequest, Executor


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NoAvailableExecutorError(RuntimeError):
    """No executor can serve the requested task."""


def _executor_from_row(row: dict[str, Any]) -> Executor:
    derived_id = _to_text(row.get("executor_id")).strip() or _to_text(row.get("id")).strip()
    if not derived_id:
        digest = hashlib.sha256((_to_text(row.get("executor_uri")).strip() or "unknown").encode("utf-8")).hexdigest()
        derived_id = f"EXEC-{digest[:8].upper()}"
    payload = {
        "executor_id": derived_id,
        "executor_uri": _to_text(row.get("executor_uri")).strip(),
        "executor_type": _to_text(row.get("executor_type")).strip() or "human",
        "name": _to_text(row.get("name")).strip(),
        "org_uri": _to_text(row.get("org_uri")).strip(),
        "capacity": _as_dict(row.get("capacity")),
        "certificates": _as_list(row.get("certificates")),
        "energy": _as_dict(row.get("energy")),
        "skills": _as_list(row.get("skills")),
        "status": _to_text(row.get("status")).strip() or "available",
        "registration_proof": _to_text(row.get("registration_proof")).strip(),
        "proof_history": _as_list(row.get("proof_history")),
        "registered_at": row.get("registered_at") or _utc_now().isoformat(),
        "last_active": row.get("last_active") or _utc_now().isoformat(),
        "trip_count": int(row.get("trip_count") or 0),
        "proof_count": int(row.get("proof_count") or 0),
        "holder_name": _to_text(row.get("holder_name")).strip(),
        "holder_id": _to_text(row.get("holder_id")).strip(),
        "holder_since": row.get("holder_since") or _utc_now().isoformat(),
    }
    return Executor.model_validate(payload)


def _list_executor_rows(sb: Any) -> list[dict[str, Any]]:
    rows = (
        sb.table("san_executors")
        .select("*")
        .limit(2000)
        .execute()
        .data
        or []
    )
    return [row for row in rows if isinstance(row, dict)]


def _insert_delegation(sb: Any, delegation: Delegation) -> None:
    sb.table("san_delegations").insert(
        {
            "delegation_uri": delegation.delegation_uri,
            "from_executor_uri": delegation.from_executor_uri,
            "to_executor_uri": delegation.to_executor_uri,
            "scope": delegation.scope,
            "valid_from": delegation.valid_from.isoformat(),
            "valid_until": delegation.valid_until.isoformat(),
            "proof_doc": delegation.proof_doc,
            "status": delegation.status,
            "created_at": delegation.created_at.isoformat(),
        }
    ).execute()


class ExecutorScheduler:
    def __init__(self, *, sb: Any) -> None:
        self.sb = sb

    async def filter_by_skill(self, required_skill: str, *, dto_role: str = "") -> list[Executor]:
        rows = _list_executor_rows(self.sb)
        token = _to_text(required_skill).strip().lower()
        out: list[Executor] = []
        for row in rows:
            executor = _executor_from_row(row)
            if not executor.status_available():
                continue
            if token:
                if not any(
                    token in " ".join(
                        [
                            skill.skill_uri.lower(),
                            skill.level_text.lower(),
                            " ".join([str(x).lower() for x in skill.scope]),
                        ]
                    )
                    for skill in executor.skills
                    if skill.is_valid_on(_utc_now().date())
                ):
                    continue
            elif dto_role and not executor.has_skill_for(dto_role):
                continue
            if not executor.cert_valid():
                continue
            out.append(executor)
        return out

    async def assign(self, dto_role: str, required_skill: str, doc_id: str) -> Executor:
        candidates = await self.filter_by_skill(required_skill, dto_role=dto_role)
        candidates = [item for item in candidates if item.capacity.current_load < item.capacity.max_concurrent]
        candidates = [item for item in candidates if item.energy.consumed < item.energy.credit_limit]
        if not candidates:
            raise NoAvailableExecutorError(f"没有可用执行体: {dto_role} ({doc_id})")
        return min(candidates, key=lambda item: int(item.capacity.current_load))

    async def delegate(self, body: DelegationRequest) -> Delegation:
        if body.valid_until <= body.valid_from:
            raise HTTPException(status_code=400, detail="valid_until must be greater than valid_from")
        now = _utc_now()
        delegation_id = f"DLG-{uuid4().hex[:10].upper()}"
        date_token = now.strftime("%Y/%m%d")
        delegation_uri = f"v://cn.大锦/DJGS/delegation/{date_token}/{delegation_id}"
        delegation = Delegation(
            delegation_uri=delegation_uri,
            from_executor_uri=body.from_executor_uri,
            to_executor_uri=body.to_executor_uri,
            scope=[_to_text(x).strip().lower() for x in body.scope if _to_text(x).strip()],
            valid_from=body.valid_from,
            valid_until=body.valid_until,
            proof_doc=body.proof_doc,
            status="active",
            created_at=now,
        )
        try:
            _insert_delegation(self.sb, delegation)
        except Exception:
            # Fallback for environments where migration is not yet applied.
            digest = hashlib.sha256(
                json.dumps(delegation.model_dump(mode="json"), ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            delegation = delegation.model_copy(update={"delegation_uri": f"{delegation_uri}-{digest[:8]}"})
        return delegation
