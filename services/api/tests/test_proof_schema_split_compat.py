from __future__ import annotations

from services.api.domain.proof.schema_models import TripRoleExecuteBody as SplitTripRoleExecuteBody
from services.api.domain.proof.schema_models import UTXOCreateBody as SplitUTXOCreateBody
from services.api.domain.proof.schemas import TripRoleExecuteBody
from services.api.domain.proof.schemas import UTXOCreateBody


def test_schemas_module_reexports_split_models() -> None:
    assert UTXOCreateBody is SplitUTXOCreateBody
    assert TripRoleExecuteBody is SplitTripRoleExecuteBody

