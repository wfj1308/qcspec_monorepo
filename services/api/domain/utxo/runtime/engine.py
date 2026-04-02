"""
Proof-UTXO engine helpers.
services/api/routers/proof_utxo_engine.py
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from supabase import Client
from services.api.domain.utxo.common import (
    gen_tx_id as _gen_tx_id,
    normalize_result as _normalize_result,
    normalize_type as _normalize_type,
    ordosign as _ordosign,
    utc_now_iso as _utc_now_iso,
)
from services.api.domain.utxo.runtime.anchor import (
    load_project_custom_fields_from_db as _load_project_custom_fields_service,
    resolve_anchor_config as _resolve_anchor_config_service,
    try_gitpeg_anchor as _try_gitpeg_anchor_service,
)
from services.api.domain.utxo.runtime.query import (
    get_by_id_row as _get_by_id_row_service,
    get_chain_rows as _get_chain_rows_service,
    get_unspent_rows as _get_unspent_rows_service,
)
from services.api.domain.utxo.runtime.condition import (
    check_conditions as _check_conditions_service,
    load_inputs as _load_inputs_service,
)
from services.api.domain.utxo.runtime.transaction import (
    auto_consume_inspection_pass_flow as _auto_consume_inspection_pass_flow,
    consume_proofs as _consume_proofs_service,
    create_proof_row as _create_proof_row_service,
)


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
        return _create_proof_row_service(
            sb=self.sb,
            proof_id=proof_id,
            owner_uri=owner_uri,
            project_uri=project_uri,
            project_id=project_id,
            proof_type=proof_type,
            result=result,
            state_data=state_data,
            conditions=conditions,
            parent_proof_id=parent_proof_id,
            norm_uri=norm_uri,
            segment_uri=segment_uri,
            signer_uri=signer_uri,
            signer_role=signer_role,
            gitpeg_anchor=gitpeg_anchor,
            anchor_config=anchor_config,
            created_at=created_at,
            normalize_type=_normalize_type,
            normalize_result=_normalize_result,
            utc_now_iso=_utc_now_iso,
            ordosign=_ordosign,
            get_by_id=self.get_by_id,
            try_gitpeg_anchor=self._try_gitpeg_anchor,
        )

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
        return _consume_proofs_service(
            sb=self.sb,
            input_proof_ids=input_proof_ids,
            output_states=output_states,
            executor_uri=executor_uri,
            executor_role=executor_role,
            trigger_action=trigger_action,
            trigger_data=trigger_data,
            tx_type=tx_type,
            anchor_config=anchor_config,
            load_inputs=self._load_inputs,
            check_conditions=self._check_conditions,
            create_callback=self.create,
            gen_tx_id=_gen_tx_id,
            utc_now_iso=_utc_now_iso,
            ordosign=_ordosign,
        )

    def get_unspent(
        self,
        *,
        project_uri: str,
        proof_type: Optional[str] = None,
        result: Optional[str] = None,
        segment_uri: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        return _get_unspent_rows_service(
            sb=self.sb,
            project_uri=project_uri,
            proof_type=proof_type,
            result=result,
            segment_uri=segment_uri,
            limit=limit,
            normalize_type=_normalize_type,
            normalize_result=_normalize_result,
        )

    def get_by_id(self, proof_id: str) -> Optional[Dict[str, Any]]:
        return _get_by_id_row_service(sb=self.sb, proof_id=proof_id)

    def get_chain(self, proof_id: str, max_depth: int = 128) -> List[Dict[str, Any]]:
        return _get_chain_rows_service(
            proof_id=proof_id,
            max_depth=max_depth,
            get_by_id=self.get_by_id,
        )

    def auto_consume_inspection_pass(
        self,
        *,
        inspection_proof_id: str,
        executor_uri: str,
        executor_role: str = "AI",
        trigger_action: str = "railpact.settle",
        anchor_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return _auto_consume_inspection_pass_flow(
            sb=self.sb,
            inspection_proof_id=inspection_proof_id,
            executor_uri=executor_uri,
            executor_role=executor_role,
            trigger_action=trigger_action,
            anchor_config=anchor_config,
            get_by_id=self.get_by_id,
            consume_callback=self.consume,
        )

    def _load_inputs(self, proof_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        return _load_inputs_service(self.sb, proof_ids)

    def _check_conditions(self, proof: Dict[str, Any], executor_uri: str, executor_role: str) -> Tuple[bool, str]:
        return _check_conditions_service(
            sb=self.sb,
            proof=proof,
            executor_uri=executor_uri,
            executor_role=executor_role,
            normalize_type=_normalize_type,
            normalize_result=_normalize_result,
        )

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
        return _try_gitpeg_anchor_service(
            proof_hash=proof_hash,
            proof_id=proof_id,
            project_id=project_id,
            project_uri=project_uri,
            owner_uri=owner_uri,
            proof_type=proof_type,
            result=result,
            state_data=state_data,
            anchor_config=anchor_config,
            load_project_custom_fields=lambda pid: _load_project_custom_fields_service(self.sb, pid),
        )

    def _resolve_anchor_config(self, anchor_config: Dict[str, Any], *, project_id: Optional[str] = None) -> Dict[str, Any]:
        return _resolve_anchor_config_service(
            anchor_config,
            project_id=project_id,
            load_project_custom_fields=lambda pid: _load_project_custom_fields_service(self.sb, pid),
        )
