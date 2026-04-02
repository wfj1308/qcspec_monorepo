from __future__ import annotations

from services.api import proof_utxo_engine
from services.api import triprole_engine
from services.api.domain.execution.runtime import triprole_engine as runtime_triprole_engine
from services.api.domain.utxo.integrations import ProofUTXOEngine


def test_proof_utxo_engine_shim_exports_domain_integration() -> None:
    assert proof_utxo_engine.ProofUTXOEngine is ProofUTXOEngine


def test_triprole_engine_shim_constants_match_runtime() -> None:
    assert triprole_engine.VALID_TRIPROLE_ACTIONS == runtime_triprole_engine.VALID_TRIPROLE_ACTIONS
    assert triprole_engine.CONSENSUS_REQUIRED_ROLES == runtime_triprole_engine.CONSENSUS_REQUIRED_ROLES
