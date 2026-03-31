"""Application service that aggregates proof flows behind a DI-friendly facade."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client

from services.api.core.base import BaseService
from services.api.domain.proof.helpers import (
    download_docfinal_zip,
    export_doc_final_package,
    finalize_docfinal_delivery_package,
    get_docfinal_context,
    replay_offline_packets_payload,
)
from services.api.proof_utxo_engine import ProofUTXOEngine


class ProofApplicationService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def list_proofs(self, *, project_id: str, v_uri: str | None = None, limit: int = 50) -> Any:
        return await self.run_guarded(
            "list_proofs",
            self._list_proofs,
            project_id=project_id,
            v_uri=v_uri,
            limit=limit,
        )

    async def verify_proof(self, *, proof_id: str) -> Any:
        return await self.run_guarded(
            "verify_proof",
            self._verify_proof,
            proof_id=proof_id,
        )

    async def proof_stats(self, *, project_id: str) -> Any:
        return await self.run_guarded(
            "proof_stats",
            self._proof_stats,
            project_id=project_id,
        )

    async def get_node_tree(self, *, root_uri: str) -> Any:
        return await self.run_guarded(
            "get_node_tree",
            self._get_node_tree,
            root_uri=root_uri,
        )

    async def replay_offline_packets(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "replay_offline_packets",
            replay_offline_packets_payload,
            body=body,
            sb=self.require_supabase(),
        )

    async def get_docfinal_context(self, **kwargs: Any) -> Any:
        return await self.run_guarded(
            "get_docfinal_context",
            get_docfinal_context,
            sb=self.require_supabase(),
            **kwargs,
        )

    async def download_docfinal(self, **kwargs: Any) -> Any:
        return await self.run_guarded(
            "download_docfinal",
            download_docfinal_zip,
            sb=self.require_supabase(),
            **kwargs,
        )

    async def export_doc_final(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "export_doc_final",
            export_doc_final_package,
            body=body,
            sb=self.require_supabase(),
        )

    async def finalize_docfinal_delivery(self, *, body: Any) -> Any:
        return await self.run_guarded(
            "finalize_docfinal_delivery",
            finalize_docfinal_delivery_package,
            body=body,
            sb=self.require_supabase(),
        )

    def _engine(self) -> ProofUTXOEngine:
        return ProofUTXOEngine(self.require_supabase())

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            UUID(str(value))
            return True
        except Exception:
            return False

    @staticmethod
    def _anchor_status(anchor: str) -> str:
        value = str(anchor or "").strip()
        if not value:
            return "pending"
        if value.lower() in {"pending", "pending_anchor", "to_anchor"}:
            return "pending"
        return "anchored"

    @staticmethod
    def _utxo_to_legacy_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "proof_id": row.get("proof_id"),
            "proof_hash": row.get("proof_hash"),
            "v_uri": (row.get("state_data") or {}).get("v_uri") or row.get("project_uri"),
            "object_type": row.get("proof_type"),
            "action": "consume" if row.get("spent") else "create",
            "summary": f"{row.get('proof_type')}:{row.get('result')}",
            "created_at": row.get("created_at"),
        }

    def _list_proofs(self, *, project_id: str, v_uri: str | None, limit: int) -> dict[str, Any]:
        if not self._is_uuid(project_id):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")

        sb = self.require_supabase()
        try:
            query = (
                sb.table("proof_chain")
                .select("proof_id,proof_hash,v_uri,object_type,action,summary,created_at")
                .eq("project_id", project_id)
                .order("created_at", desc=True)
                .limit(max(1, min(limit, 200)))
            )
            if v_uri:
                query = query.eq("v_uri", v_uri)
            rows = query.execute().data or []
            return {"data": rows, "count": len(rows)}
        except APIError as exc:
            if "invalid input syntax for type uuid" in str(exc):
                raise HTTPException(400, "Invalid project_id format. UUID expected.") from exc
            try:
                project_rows = sb.table("projects").select("v_uri").eq("id", project_id).limit(1).execute().data or []
                rows: list[dict[str, Any]] = []
                if project_rows:
                    rows = [
                        self._utxo_to_legacy_row(row)
                        for row in self._engine().get_unspent(project_uri=project_rows[0]["v_uri"], limit=limit)
                    ]
                return {"data": rows, "count": len(rows)}
            except Exception as fallback_exc:
                raise HTTPException(502, "Failed to query proof chain.") from fallback_exc
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
            return {"data": [], "count": 0}

    def _verify_proof(self, *, proof_id: str) -> dict[str, Any]:
        sb = self.require_supabase()
        try:
            proof = sb.table("proof_chain").select("*").eq("proof_id", proof_id).single().execute().data
        except (APIError, httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
            proof = None

        utxo = None
        try:
            utxo = self._engine().get_by_id(proof_id)
        except Exception:
            utxo = None

        if not proof:
            if not utxo:
                return {"valid": False, "proof": None, "message": "Proof not found."}
            anchor = str(utxo.get("gitpeg_anchor") or "").strip()
            return {
                "valid": True,
                "proof_id": proof_id,
                "proof_hash": utxo.get("proof_hash"),
                "v_uri": (utxo.get("state_data") or {}).get("v_uri") or utxo.get("project_uri"),
                "project_uri": utxo.get("project_uri"),
                "segment_uri": utxo.get("segment_uri"),
                "object_type": utxo.get("proof_type"),
                "action": "consume" if utxo.get("spent") else "create",
                "summary": f"{utxo.get('proof_type')}:{utxo.get('result')}",
                "created_at": utxo.get("created_at"),
                "chain_length": int(utxo.get("depth") or 0) + 1,
                "gitpeg_anchor": anchor or None,
                "anchor_status": self._anchor_status(anchor),
                "message": "Proof verified via proof_utxo.",
            }

        expected_hash = str(proof_id).replace("GP-PROOF-", "").lower()
        hash_valid = proof.get("proof_hash") == expected_hash
        try:
            chain_rows = (
                sb.table("proof_chain")
                .select("proof_id", count="exact")
                .eq("v_uri", proof.get("v_uri"))
                .execute()
            )
            chain_count = chain_rows.count or 0
        except Exception:
            chain_count = 0

        utxo_extra: dict[str, Any] = {}
        if isinstance(utxo, dict):
            anchor = str(utxo.get("gitpeg_anchor") or "").strip()
            utxo_extra = {
                "project_uri": utxo.get("project_uri"),
                "segment_uri": utxo.get("segment_uri"),
                "proof_hash": utxo.get("proof_hash"),
                "gitpeg_anchor": anchor or None,
                "anchor_status": self._anchor_status(anchor),
            }

        return {
            "valid": hash_valid,
            "proof_id": proof_id,
            "proof_hash": proof.get("proof_hash"),
            "v_uri": proof.get("v_uri"),
            "object_type": proof.get("object_type"),
            "action": proof.get("action"),
            "summary": proof.get("summary"),
            "created_at": proof.get("created_at"),
            "chain_length": chain_count,
            "message": "Proof verified." if hash_valid else "Proof hash mismatch.",
            **utxo_extra,
        }

    def _get_node_tree(self, *, root_uri: str) -> dict[str, Any]:
        try:
            rows = (
                self.require_supabase()
                .table("v_nodes")
                .select("uri,parent_uri,node_type,peg_count,status")
                .like("uri", f"{root_uri}%")
                .order("uri")
                .execute()
                .data
                or []
            )
            return {"data": rows, "root": root_uri}
        except Exception:
            return {"data": [], "root": root_uri}

    def _proof_stats(self, *, project_id: str) -> dict[str, Any]:
        if not self._is_uuid(project_id):
            raise HTTPException(400, "Invalid project_id format. UUID expected.")

        try:
            rows = (
                self.require_supabase()
                .table("proof_chain")
                .select("object_type, action")
                .eq("project_id", project_id)
                .execute()
                .data
                or []
            )
        except Exception:
            rows = []

        by_type: dict[str, int] = {}
        by_action: dict[str, int] = {}
        for row in rows:
            object_type = row.get("object_type")
            action = row.get("action")
            if object_type:
                by_type[object_type] = by_type.get(object_type, 0) + 1
            if action:
                by_action[action] = by_action.get(action, 0) + 1

        return {"total": len(rows), "by_type": by_type, "by_action": by_action}
