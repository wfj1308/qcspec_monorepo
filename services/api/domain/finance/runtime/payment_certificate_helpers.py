"""Pure helper functions for BOQ payment certificate computation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any

from fastapi import HTTPException

from services.api.domain.boq.runtime.audit_common import (
    as_dict,
    as_list,
    to_float as common_to_float,
    to_text,
)

REQUIRED_CONSENSUS_ROLES = ("contractor", "supervisor", "owner")


def to_float(value: Any) -> float | None:
    return common_to_float(value, regex_fallback=True)


def safe_period_token(period: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9_\-]+", "-", to_text(period).strip()).strip("-")
    return token[:60] or "all"


def parse_iso_dt(value: Any) -> datetime | None:
    text = to_text(value).strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        dt = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_period(period: str) -> tuple[datetime | None, datetime | None, str]:
    text = to_text(period).strip()
    if not text:
        return None, None, "all"

    monthly = re.fullmatch(r"(\d{4})-(\d{2})", text)
    if monthly:
        year = int(monthly.group(1))
        month = int(monthly.group(2))
        if month < 1 or month > 12:
            raise HTTPException(400, "period month must be 01-12")
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)
        return start, end, text

    daily = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if daily:
        year = int(daily.group(1))
        month = int(daily.group(2))
        day = int(daily.group(3))
        start = datetime(year, month, day, tzinfo=timezone.utc)
        return start, start + timedelta(days=1), text

    ranged = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\s*(?:~|to|,)\s*(\d{4}-\d{2}-\d{2})", text, flags=re.IGNORECASE)
    if ranged:
        start = datetime.fromisoformat(ranged.group(1)).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(ranged.group(2)).replace(tzinfo=timezone.utc) + timedelta(days=1)
        if end <= start:
            raise HTTPException(400, "period range must be ascending")
        return start, end, text

    raise HTTPException(400, "period must be YYYY-MM or YYYY-MM-DD or YYYY-MM-DD~YYYY-MM-DD")


def in_period(value: Any, start: datetime | None, end: datetime | None) -> bool:
    if start is None or end is None:
        return True
    dt = parse_iso_dt(value)
    if dt is None:
        return False
    return start <= dt < end


def stage(row: dict[str, Any]) -> str:
    sd = as_dict(row.get("state_data"))
    stage_value = to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    if stage_value:
        return stage_value
    if to_text(row.get("proof_type")).strip().lower() == "zero_ledger":
        return "INITIAL"
    return ""


def is_leaf_boq_row(row: dict[str, Any]) -> bool:
    sd = as_dict(row.get("state_data"))
    if "is_leaf" in sd:
        return bool(sd.get("is_leaf"))
    tree = as_dict(sd.get("hierarchy_tree"))
    if "is_leaf" in tree:
        return bool(tree.get("is_leaf"))
    children = as_list(tree.get("children")) or as_list(tree.get("children_codes"))
    return not bool(children)


def extract_settled_quantity(row: dict[str, Any], *, fallback_design: float | None = None) -> float:
    sd = as_dict(row.get("state_data"))
    settlement = as_dict(sd.get("settlement"))
    measurement = as_dict(sd.get("measurement"))

    for path in (
        settlement.get("settled_quantity"),
        settlement.get("quantity"),
        settlement.get("confirmed_quantity"),
        sd.get("settled_quantity"),
        measurement.get("quantity"),
        measurement.get("used_quantity"),
        sd.get("quantity"),
    ):
        q = to_float(path)
        if q is not None:
            return max(0.0, float(q))

    values = as_list(measurement.get("values"))
    nums = [x for x in (to_float(v) for v in values) if x is not None]
    if nums:
        return max(0.0, float(sum(nums) / len(nums)))

    if fallback_design is not None:
        return max(0.0, float(fallback_design))
    return 0.0


def effective_design_quantity(genesis_row: dict[str, Any], bucket: list[dict[str, Any]]) -> float:
    gsd = as_dict(genesis_row.get("state_data"))
    base_design = to_float(gsd.get("design_quantity"))
    if base_design is None:
        base_design = to_float(as_dict(gsd.get("ledger")).get("initial_balance"))
    if base_design is None:
        base_design = 0.0

    latest_merged_total: float | None = None
    latest_delta_total: float | None = None
    for row in sorted(bucket, key=lambda r: to_text(r.get("created_at") or "")):
        sd = as_dict(row.get("state_data"))
        ledger = as_dict(sd.get("ledger"))
        merged_total = to_float(ledger.get("merged_total"))
        if merged_total is not None:
            latest_merged_total = float(merged_total)
        delta_total = to_float(ledger.get("delta_total"))
        if delta_total is not None:
            latest_delta_total = float(delta_total)

    if latest_merged_total is not None:
        return max(0.0, latest_merged_total)
    if latest_delta_total is not None:
        return max(0.0, float(base_design + latest_delta_total))
    return max(0.0, float(base_design))


def has_tripartite_consensus(row: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    sd = as_dict(row.get("state_data"))
    consensus = as_dict(sd.get("consensus"))
    signatures = as_list(consensus.get("signatures"))

    by_role: dict[str, dict[str, Any]] = {}
    for sig in signatures:
        if not isinstance(sig, dict):
            continue
        role = to_text(sig.get("role") or "").strip().lower()
        if role:
            by_role[role] = sig

    missing = [role for role in REQUIRED_CONSENSUS_ROLES if role not in by_role]
    invalid: list[str] = []
    for role in REQUIRED_CONSENSUS_ROLES:
        sig = by_role.get(role)
        if not sig:
            continue
        did = to_text(sig.get("did") or "").strip()
        sig_hash = to_text(sig.get("signature_hash") or "").strip().lower()
        if not did.startswith("did:"):
            invalid.append(f"{role}:did_invalid")
        if not re.fullmatch(r"[a-f0-9]{64}", sig_hash):
            invalid.append(f"{role}:signature_hash_invalid")

    ok = (not missing) and (not invalid)
    return ok, {
        "ok": ok,
        "missing_roles": missing,
        "invalid": invalid,
        "consensus_complete": bool(consensus.get("consensus_complete")),
        "signature_count": len(signatures),
    }


def has_any_fail(chain_rows: list[dict[str, Any]]) -> bool:
    for row in chain_rows:
        result = to_text((row or {}).get("result") or "").strip().upper()
        if result == "FAIL":
            return True
    return False


def chapter_from_item_no(item_no: str) -> str:
    text = to_text(item_no).strip()
    if not text:
        return "misc"
    return text.split("-")[0] if "-" in text else text.split(".")[0]
