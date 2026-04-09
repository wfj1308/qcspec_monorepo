"""Compatibility exports for equipment-trip models."""

from services.api.domain.boqpeg.models import (
    EquipmentHistoryResult,
    EquipmentTrip,
    EquipmentTripRequest,
    EquipmentTripSubmitResult,
)

__all__ = [
    "EquipmentTrip",
    "EquipmentTripRequest",
    "EquipmentTripSubmitResult",
    "EquipmentHistoryResult",
]
