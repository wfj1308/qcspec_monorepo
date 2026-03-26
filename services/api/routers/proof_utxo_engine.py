"""
Proof-UTXO engine helpers.
services/api/routers/proof_utxo_engine.py
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx
from postgrest.exceptions import APIError
from supabase import Client


PROOF_TYPES = {
    "inspection",
    "lab",
    "photo",
    "approval",
    "payment",
    "archive",
    "ordosign",
    "zero_ledger",
}

PROOF_RESULTS = {"PASS", "FAIL", "OBSERVE", "PENDING", "CANCELLED"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_tx_id() -> str:
    return f"TX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def _ordosign(target_id: str, signer_uri: str) -> str:
    payload = f"{target_id}:{signer_uri}:{_utc_now_iso()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _normalize_result(value: str) -> str:
    t = str(value or "").strip().upper()
    return t if t in PROOF_RESULTS else "PENDING"


def _normalize_type(value: str) -> str:
    t = str(value or "").strip().lower()
    return t if t in PROOF_TYPES else "inspection"


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _to_base_url(value: Any) -> str:
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return ""
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = f"https://{raw}"
    return raw


def _extract_anchor_hash(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in (
        "anchor",
        "anchor_hash",
        "proof_anchor",
        "proof_hash",
        "hash",
        "tx_hash",
        "anchorHash",
        "proofHash",
    ):
        value = payload.get(key)
        text = str(value or "").strip()
        if text:
            return text
    nested = payload.get("data")
    if isinstance(nested, dict):
        return _extract_anchor_hash(nested)
    return ""


class ProofUTXOEngine:
    def __init__(self, sb: Client):
        self.sb = sb

    def create(
        self,
        *,
        proof_id: str,
        owner_uri: str,
        project_uri: str,
        project_id: Optional[str] = None,
        proof_type: str = "inspection",
        result: str = "PENDING",
        state_data: Optional[Dict[str, Any]] = None,
        conditions: Optional[List[Dict[str, Any]]] = None,
        parent_proof_id: Optional[str] = None,
        norm_uri: Optional[str] = None,
        segment_uri: Optional[str] = None,
        signer_uri: Optional[str] = None,
        signer_role: str = "AI",
        gitpeg_anchor: Optional[str] = None,
        anchor_config: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        now_iso = str(created_at or _utc_now_iso())
        ptype = _normalize_type(proof_type)
        presult = _normalize_result(result)
        depth = 0
        if parent_proof_id:
            parent = self.get_by_id(parent_proof_id)
            depth = int(parent.get("depth") or 0) + 1 if parent else 0

        payload_for_hash = {
            "proof_id": str(proof_id),
            "owner_uri": str(owner_uri),
            "project_uri": str(project_uri),
            "project_id": project_id,
            "segment_uri": segment_uri,
            "proof_type": ptype,
            "result": presult,
            "state_data": state_data or {},
            "conditions": conditions or [],
            "parent_proof_id": parent_proof_id,
            "norm_uri": norm_uri,
        }
        proof_hash = hashlib.sha256(
            json.dumps(payload_for_hash, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        signed_by: List[Dict[str, Any]] = []
        if signer_uri:
            signed_by = [
                {
                    "executor_uri": signer_uri,
                    "role": str(signer_role or "AI").upper(),
                    "ordosign_hash": _ordosign(str(proof_id), str(signer_uri)),
                    "ts": now_iso,
                }
            ]

        row: Dict[str, Any] = {
            "proof_id": str(proof_id),
            "proof_hash": proof_hash,
            "owner_uri": str(owner_uri),
            "project_id": project_id,
            "project_uri": str(project_uri),
            "segment_uri": segment_uri,
            "proof_type": ptype,
            "result": presult,
            "state_data": state_data or {},
            "spent": False,
            "spend_tx_id": None,
            "spent_at": None,
            "conditions": conditions or [],
            "parent_proof_id": parent_proof_id,
            "depth": depth,
            "norm_uri": norm_uri,
            "gitpeg_anchor": gitpeg_anchor,
            "signed_by": signed_by,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        try:
            self.sb.table("proof_utxo").insert(row).execute()
            resolved_anchor = str(gitpeg_anchor or "").strip()
            if not resolved_anchor:
                resolved_anchor = self._try_gitpeg_anchor(
                    proof_hash=proof_hash,
                    proof_id=str(proof_id),
                    project_id=project_id,
                    project_uri=str(project_uri),
                    owner_uri=str(owner_uri),
                    proof_type=str(ptype),
                    result=str(presult),
                    state_data=state_data or {},
                    anchor_config=anchor_config,
                )
            if resolved_anchor:
                self.sb.table("proof_utxo").update({"gitpeg_anchor": resolved_anchor}).eq(
                    "proof_id", str(proof_id)
                ).execute()
                row["gitpeg_anchor"] = resolved_anchor
            return row
        except APIError as exc:
            # Allow idempotent retries from API layer.
            if "duplicate key value" not in str(exc).lower():
                raise
            existing = self.get_by_id(str(proof_id))
            if existing:
                return existing
            raise

    def consume(
        self,
        *,
        input_proof_ids: List[str],
        output_states: List[Dict[str, Any]],
        executor_uri: str,
        executor_role: str = "AI",
        trigger_action: Optional[str] = None,
        trigger_data: Optional[Dict[str, Any]] = None,
        tx_type: str = "consume",
        anchor_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not input_proof_ids:
            raise ValueError("input_proof_ids is required")
        if not output_states:
            raise ValueError("output_states is required")

        proof_map = self._load_inputs(input_proof_ids)
        for pid in input_proof_ids:
            proof = proof_map.get(pid)
            if not proof:
                raise ValueError(f"proof {pid} not found")
            if bool(proof.get("spent")):
                raise ValueError(f"proof {pid} already spent")
            ok, reason = self._check_conditions(proof, executor_uri, executor_role)
            if not ok:
                raise PermissionError(reason)

        tx_id = _gen_tx_id()
        now_iso = _utc_now_iso()
        output_proofs: List[str] = []
        first_input = proof_map[input_proof_ids[0]]
        parent_id = input_proof_ids[0]

        for output in output_states:
            created = self.create(
                proof_id=str(output.get("proof_id") or f"GP-PROOF-{uuid.uuid4().hex[:16].upper()}"),
                owner_uri=str(output.get("owner_uri") or first_input.get("owner_uri")),
                project_id=output.get("project_id") or first_input.get("project_id"),
                project_uri=str(output.get("project_uri") or first_input.get("project_uri")),
                segment_uri=output.get("segment_uri") or first_input.get("segment_uri"),
                proof_type=str(output.get("proof_type") or "inspection"),
                result=str(output.get("result") or "PENDING"),
                state_data=output.get("state_data") or {},
                conditions=output.get("conditions") or [],
                parent_proof_id=str(output.get("parent_proof_id") or parent_id),
                norm_uri=output.get("norm_uri"),
                signer_uri=executor_uri,
                signer_role=executor_role,
                gitpeg_anchor=output.get("gitpeg_anchor"),
                anchor_config=anchor_config,
                created_at=now_iso,
            )
            output_proofs.append(str(created["proof_id"]))

        tx_row = {
            "tx_id": tx_id,
            "tx_type": tx_type if tx_type in {"consume", "merge", "split", "settle", "archive"} else "consume",
            "input_proofs": input_proof_ids,
            "output_proofs": output_proofs,
            "trigger_action": trigger_action,
            "trigger_data": trigger_data or {},
            "executor_uri": executor_uri,
            "ordosign_hash": _ordosign(tx_id, executor_uri),
            "status": "success",
            "error_msg": None,
            "created_at": now_iso,
        }
        self.sb.table("proof_transaction").insert(tx_row).execute()
        for pid in input_proof_ids:
            self.sb.table("proof_utxo").update(
                {"spent": True, "spend_tx_id": tx_id, "spent_at": now_iso}
            ).eq("proof_id", pid).execute()
        return tx_row

    def get_unspent(
        self,
        *,
        project_uri: str,
        proof_type: Optional[str] = None,
        result: Optional[str] = None,
        segment_uri: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        q = self.sb.table("proof_utxo").select("*").eq("project_uri", project_uri).eq("spent", False).limit(
            max(1, min(limit, 500))
        )
        if proof_type:
            q = q.eq("proof_type", _normalize_type(proof_type))
        if result:
            q = q.eq("result", _normalize_result(result))
        if segment_uri:
            q = q.eq("segment_uri", segment_uri)
        res = q.execute()
        return res.data or []

    def get_by_id(self, proof_id: str) -> Optional[Dict[str, Any]]:
        res = self.sb.table("proof_utxo").select("*").eq("proof_id", proof_id).limit(1).execute()
        data = res.data or []
        return data[0] if data else None

    def get_chain(self, proof_id: str, max_depth: int = 128) -> List[Dict[str, Any]]:
        chain: List[Dict[str, Any]] = []
        seen: set[str] = set()
        current_id = str(proof_id)
        while current_id and len(chain) < max_depth and current_id not in seen:
            seen.add(current_id)
            current = self.get_by_id(current_id)
            if not current:
                break
            chain.append(current)
            current_id = str(current.get("parent_proof_id") or "")
        return list(reversed(chain))

    def auto_consume_inspection_pass(
        self,
        *,
        inspection_proof_id: str,
        executor_uri: str,
        executor_role: str = "AI",
        trigger_action: str = "railpact.settle",
        anchor_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        inspection = self.get_by_id(inspection_proof_id)
        if not inspection:
            return {"attempted": False, "success": False, "reason": "inspection_proof_not_found"}
        if str(inspection.get("proof_type") or "") != "inspection":
            return {"attempted": False, "success": False, "reason": "proof_type_not_inspection"}
        if str(inspection.get("result") or "") != "PASS":
            return {"attempted": False, "success": False, "reason": "inspection_not_pass"}
        if bool(inspection.get("spent")):
            return {"attempted": False, "success": False, "reason": "inspection_already_spent"}

        project_uri = str(inspection.get("project_uri") or "").strip()
        if not project_uri:
            return {"attempted": False, "success": False, "reason": "project_uri_missing"}
        segment_uri = str(inspection.get("segment_uri") or "").strip() or None

        sdata = inspection.get("state_data") if isinstance(inspection.get("state_data"), dict) else {}
        stake = str(sdata.get("stake") or sdata.get("location") or "").strip()

        labs = (
            self.sb.table("proof_utxo")
            .select("*")
            .eq("project_uri", project_uri)
            .eq("proof_type", "lab")
            .eq("result", "PASS")
            .eq("spent", False)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
        if segment_uri:
            labs = [x for x in labs if str(x.get("segment_uri") or "").strip() == segment_uri]
        if stake:
            stake_matched = []
            for lab in labs:
                ld = lab.get("state_data") if isinstance(lab.get("state_data"), dict) else {}
                l_stake = str(ld.get("stake") or ld.get("location") or "").strip()
                if l_stake == stake:
                    stake_matched.append(lab)
            if stake_matched:
                labs = stake_matched
        if not labs:
            return {"attempted": True, "success": False, "reason": "no_unspent_lab_pass"}

        lab = labs[0]
        output_state = {
            "proof_type": "payment",
            "result": "PASS",
            "owner_uri": inspection.get("owner_uri"),
            "project_id": inspection.get("project_id"),
            "project_uri": project_uri,
            "segment_uri": segment_uri,
            "conditions": [{"type": "role", "value": "SUPERVISOR"}],
            "state_data": {
                "source": "auto_settle_gate",
                "stake": stake,
                "inspection_proof_id": inspection.get("proof_id"),
                "lab_proof_id": lab.get("proof_id"),
                "inspection_state": sdata,
                "lab_state": lab.get("state_data") if isinstance(lab.get("state_data"), dict) else {},
            },
            "parent_proof_id": inspection.get("proof_id"),
        }
        tx = self.consume(
            input_proof_ids=[str(lab.get("proof_id")), str(inspection.get("proof_id"))],
            output_states=[output_state],
            executor_uri=executor_uri,
            executor_role=executor_role,
            trigger_action=trigger_action,
            trigger_data={
                "source": "inspection_pass",
                "inspection_proof_id": inspection.get("proof_id"),
                "lab_proof_id": lab.get("proof_id"),
                "stake": stake,
            },
            tx_type="settle",
            anchor_config=anchor_config,
        )
        return {
            "attempted": True,
            "success": True,
            "reason": "auto_settle_ok",
            "tx": tx,
        }

    def _load_inputs(self, proof_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        rows = (
            self.sb.table("proof_utxo")
            .select("*")
            .in_("proof_id", proof_ids)
            .limit(max(1, min(len(proof_ids), 500)))
            .execute()
            .data
            or []
        )
        return {str(row.get("proof_id")): row for row in rows}

    def _check_conditions(self, proof: Dict[str, Any], executor_uri: str, executor_role: str) -> Tuple[bool, str]:
        proof_id = str(proof.get("proof_id") or "")
        conditions = proof.get("conditions") or []
        if not conditions:
            return True, "ok"
        for cond in conditions:
            ctype = str((cond or {}).get("type") or "").strip()
            if ctype == "role":
                role_value = str((cond or {}).get("value") or "").strip().upper()
                if str(executor_role or "").strip().upper() != role_value:
                    self._log_condition(
                        proof_id=proof_id,
                        condition=cond,
                        checked_by=executor_uri,
                        passed=False,
                        detail=f"role_required:{role_value}",
                    )
                    return False, f"role_required:{role_value}"
                self._log_condition(
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=True,
                    detail="role_ok",
                )
            elif ctype == "ordosign_required":
                role_value = str((cond or {}).get("role") or "").strip().upper()
                if str(executor_role or "").strip().upper() != role_value:
                    self._log_condition(
                        proof_id=proof_id,
                        condition=cond,
                        checked_by=executor_uri,
                        passed=False,
                        detail=f"ordosign_role_required:{role_value}",
                    )
                    return False, f"ordosign_role_required:{role_value}"
                self._log_condition(
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=True,
                    detail="ordosign_role_ok",
                )
            elif ctype == "proof_required":
                query = (
                    self.sb.table("proof_utxo")
                    .select("proof_id", count="exact")
                    .eq("project_uri", proof.get("project_uri"))
                    .eq("spent", False)
                    .eq("proof_type", _normalize_type((cond or {}).get("proof_type")))
                    .eq("result", _normalize_result((cond or {}).get("result") or "PASS"))
                )
                if proof.get("segment_uri"):
                    query = query.eq("segment_uri", proof.get("segment_uri"))
                res = query.limit(1).execute()
                if int(res.count or 0) <= 0:
                    self._log_condition(
                        proof_id=proof_id,
                        condition=cond,
                        checked_by=executor_uri,
                        passed=False,
                        detail="proof_required_unsatisfied",
                    )
                    return False, "proof_required_unsatisfied"
                self._log_condition(
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=True,
                    detail="proof_required_ok",
                )
            elif ctype == "min_count":
                min_need = int((cond or {}).get("min") or 0)
                query = (
                    self.sb.table("proof_utxo")
                    .select("proof_id", count="exact")
                    .eq("project_uri", proof.get("project_uri"))
                    .eq("spent", False)
                    .eq("proof_type", _normalize_type((cond or {}).get("proof_type")))
                    .eq("result", _normalize_result((cond or {}).get("result") or "PASS"))
                )
                if proof.get("segment_uri"):
                    query = query.eq("segment_uri", proof.get("segment_uri"))
                res = query.limit(max(1, min_need)).execute()
                if int(res.count or 0) < min_need:
                    self._log_condition(
                        proof_id=proof_id,
                        condition=cond,
                        checked_by=executor_uri,
                        passed=False,
                        detail="min_count_unsatisfied",
                    )
                    return False, "min_count_unsatisfied"
                self._log_condition(
                    proof_id=proof_id,
                    condition=cond,
                    checked_by=executor_uri,
                    passed=True,
                    detail="min_count_ok",
                )
        return True, "ok"

    def _log_condition(
        self,
        *,
        proof_id: str,
        condition: Dict[str, Any],
        checked_by: str,
        passed: bool,
        detail: str,
    ) -> None:
        if not proof_id:
            return
        try:
            self.sb.table("proof_condition_log").insert(
                {
                    "proof_id": proof_id,
                    "condition": condition or {},
                    "checked_by": checked_by,
                    "passed": bool(passed),
                    "detail": detail,
                }
            ).execute()
        except Exception:
            pass

    def _try_gitpeg_anchor(
        self,
        *,
        proof_hash: str,
        proof_id: str,
        project_id: Optional[str],
        project_uri: str,
        owner_uri: str,
        proof_type: str,
        result: str,
        state_data: Dict[str, Any],
        anchor_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        cfg = self._resolve_anchor_config(anchor_config or {}, project_id=project_id)
        if not cfg.get("enabled"):
            return ""
        endpoint = str(cfg.get("endpoint") or "").strip()
        if not endpoint:
            return ""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "QCSpec-ProofUTXO/1.0",
        }
        token = str(cfg.get("auth_token") or "").strip()
        if token:
            if token.lower().startswith("bearer "):
                headers["Authorization"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
        body = {
            "proof_hash": proof_hash,
            "proof_id": proof_id,
            "project_uri": project_uri,
            "owner_uri": owner_uri,
            "proof_type": proof_type,
            "result": result,
            "state_data": state_data or {},
        }
        try:
            timeout_s = float(cfg.get("timeout_s") or 6.0)
        except Exception:
            timeout_s = 6.0
        try:
            with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
                res = client.post(endpoint, headers=headers, json=body)
                if res.status_code >= 400:
                    return ""
                payload = {}
                try:
                    payload = res.json()
                except Exception:
                    payload = {}
                return _extract_anchor_hash(payload)
        except Exception:
            return ""

    def _resolve_anchor_config(self, anchor_config: Dict[str, Any], *, project_id: Optional[str] = None) -> Dict[str, Any]:
        db_custom: Dict[str, Any] = {}
        if project_id:
            db_custom = self._load_project_custom_fields(str(project_id))
        base_url = _to_base_url(
            anchor_config.get("base_url")
            or db_custom.get("gitpeg_registrar_base_url")
            or anchor_config.get("gitpeg_registrar_base_url")
            or os.getenv("GITPEG_REGISTRAR_BASE_URL")
            or "https://gitpeg.cn"
        )
        path = str(
            anchor_config.get("anchor_path")
            or db_custom.get("gitpeg_proof_anchor_path")
            or anchor_config.get("gitpeg_proof_anchor_path")
            or os.getenv("GITPEG_PROOF_ANCHOR_PATH")
            or ""
        ).strip()
        endpoint = str(anchor_config.get("anchor_endpoint") or db_custom.get("gitpeg_proof_anchor_endpoint") or "").strip()
        if not endpoint and base_url and path:
            endpoint = f"{base_url}{path if path.startswith('/') else '/' + path}"
        enabled = _to_bool(
            anchor_config.get("enabled")
            or anchor_config.get("gitpeg_anchor_enabled")
            or anchor_config.get("proof_utxo_gitpeg_anchor_enabled")
            or db_custom.get("proof_utxo_gitpeg_anchor_enabled")
            or os.getenv("PROOF_UTXO_GITPEG_ANCHOR_ENABLED")
        )
        auth_token = str(
            anchor_config.get("auth_token")
            or db_custom.get("gitpeg_anchor_token")
            or db_custom.get("gitpeg_token")
            or db_custom.get("gitpeg_client_secret")
            or anchor_config.get("gitpeg_token")
            or anchor_config.get("gitpeg_client_secret")
            or os.getenv("GITPEG_PROOF_ANCHOR_TOKEN")
            or ""
        ).strip()
        timeout_s = (
            anchor_config.get("timeout_s")
            or db_custom.get("gitpeg_proof_anchor_timeout_s")
            or os.getenv("GITPEG_PROOF_ANCHOR_TIMEOUT_S")
            or 6
        )
        return {
            "enabled": enabled,
            "endpoint": endpoint,
            "auth_token": auth_token,
            "timeout_s": timeout_s,
        }

    def _load_project_custom_fields(self, project_id: str) -> Dict[str, Any]:
        try:
            proj = (
                self.sb.table("projects")
                .select("enterprise_id")
                .eq("id", project_id)
                .limit(1)
                .execute()
            )
            rows = proj.data or []
            if not rows:
                return {}
            enterprise_id = str(rows[0].get("enterprise_id") or "").strip()
            if not enterprise_id:
                return {}
            cfg = (
                self.sb.table("enterprise_configs")
                .select("custom_fields")
                .eq("enterprise_id", enterprise_id)
                .limit(1)
                .execute()
            )
            cfg_rows = cfg.data or []
            if not cfg_rows:
                return {}
            custom = cfg_rows[0].get("custom_fields") or {}
            return custom if isinstance(custom, dict) else {}
        except Exception:
            return {}
