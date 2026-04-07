from __future__ import annotations

from services.api.core import NormRefResolverService as LegacyNormRefResolverService
from services.api.core import ProofUTXOService as LegacyProofUTXOService
from services.api.core.docpeg import NormRefResolverService
from services.api.core.docpeg import ProofUTXOService
from services.api.core.docpeg.normref import NormRefResolverService as NormRefFromSubpackage
from services.api.core.docpeg.utxo import ProofUTXOService as UtxoFromSubpackage


def test_docpeg_normref_shim_points_to_legacy_core_service() -> None:
    assert NormRefResolverService is LegacyNormRefResolverService
    assert NormRefFromSubpackage is LegacyNormRefResolverService


def test_docpeg_utxo_shim_points_to_legacy_core_service() -> None:
    assert ProofUTXOService is LegacyProofUTXOService
    assert UtxoFromSubpackage is LegacyProofUTXOService

