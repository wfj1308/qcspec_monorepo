"""
Compatibility shim for legacy proof UTXO common imports.

Prefer importing from ``services.api.domain.utxo.common`` directly.
"""

from __future__ import annotations

from services.api.domain.utxo import common as _utxo_common


def _ordered_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


PROOF_TYPES = _utxo_common.PROOF_TYPES
PROOF_RESULTS = _utxo_common.PROOF_RESULTS
utc_now_iso = _utxo_common.utc_now_iso
gen_tx_id = _utxo_common.gen_tx_id
ordosign = _utxo_common.ordosign
normalize_result = _utxo_common.normalize_result
normalize_type = _utxo_common.normalize_type

_gen_tx_id = gen_tx_id
_normalize_result = normalize_result
_normalize_type = normalize_type
_ordosign = ordosign
_utc_now_iso = utc_now_iso

__all__ = _ordered_unique(
    [
        *_utxo_common.__all__,
        "_utc_now_iso",
        "_gen_tx_id",
        "_ordosign",
        "_normalize_result",
        "_normalize_type",
    ]
)
