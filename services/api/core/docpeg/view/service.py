"""Role-aware DTO view layer for DocPeg Core API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


class Role(str, Enum):
    PUBLIC = "PUBLIC"
    MARKET = "MARKET"
    AI = "AI"
    SUPERVISOR = "SUPERVISOR"
    OWNER = "OWNER"
    REGULATOR = "REGULATOR"


_ROLE_ALIASES: dict[str, Role] = {
    "PUBLIC": Role.PUBLIC,
    "MARKET": Role.MARKET,
    "AI": Role.AI,
    "SUPERVISOR": Role.SUPERVISOR,
    "OWNER": Role.OWNER,
    "REGULATOR": Role.REGULATOR,
    "ADMIN": Role.OWNER,
    "SUPER_ADMIN": Role.OWNER,
    "SUPERADMIN": Role.OWNER,
    "MANAGER": Role.OWNER,
    "QA_MANAGER": Role.OWNER,
    "QCSPEC_ADMIN": Role.OWNER,
    "CONTRACTOR": Role.AI,
}


@dataclass(slots=True)
class BaseDTO:
    usi: str = ""
    role: str = Role.PUBLIC.value
    generated_at: str = field(default_factory=_utc_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutorDTO(BaseDTO):
    executor_uri: str = ""
    executor_name: str = ""
    executor_role: str = ""


@dataclass(slots=True)
class TripDTO(BaseDTO):
    trip_id: str = ""
    trip_uri: str = ""
    status: str = ""
    result: str = ""


@dataclass(slots=True)
class NormTemplateDTO(BaseDTO):
    norm_uri: str = ""
    title: str = ""
    version: str = ""
    status: str = ""


@dataclass(slots=True)
class WalletDTO(BaseDTO):
    wallet_uri: str = ""
    owner_uri: str = ""
    balance: float = 0.0
    currency: str = "CNY"


@dataclass(slots=True)
class BOQItemPublicDTO(BaseDTO):
    boq_item_id: str = ""
    description: str = ""
    unit: str = ""
    boq_quantity: float = 0.0
    bridge_name: str = ""
    genesis_hash: str = ""


@dataclass(slots=True)
class BOQItemSupervisorDTO(BaseDTO):
    boq_item_id: str = ""
    description: str = ""
    unit: str = ""
    boq_quantity: float = 0.0
    bridge_name: str = ""
    attached_spus: list[str] = field(default_factory=list)
    norm_refs: list[str] = field(default_factory=list)
    qc_gate_count: int = 0
    genesis_hash: str = ""


@dataclass(slots=True)
class BOQItemOwnerDTO(BaseDTO):
    boq_item_id: str = ""
    description: str = ""
    unit: str = ""
    boq_quantity: float = 0.0
    unit_price: float = 0.0
    total_amount: float = 0.0
    bridge_name: str = ""
    attached_spus: list[str] = field(default_factory=list)
    norm_refs: list[str] = field(default_factory=list)
    settlement_rules: list[str] = field(default_factory=list)
    genesis_hash: str = ""


@dataclass(slots=True)
class SPUBOQMappingPublicDTO(BaseDTO):
    mapping_id: str = ""
    boq_item_id: str = ""
    spu_uri: str = ""
    capability_type: str = ""
    norm_ref: str = ""


@dataclass(slots=True)
class SPUBOQMappingSupervisorDTO(BaseDTO):
    mapping_id: str = ""
    boq_item_id: str = ""
    boq_v_uri: str = ""
    bridge_uri: str = ""
    spu_uri: str = ""
    capability_type: str = ""
    norm_ref: str = ""
    weight: float = 1.0
    proof_hash: str = ""


@dataclass(slots=True)
class SPUBOQMappingOwnerDTO(BaseDTO):
    mapping_id: str = ""
    boq_item_id: str = ""
    boq_v_uri: str = ""
    bridge_uri: str = ""
    spu_uri: str = ""
    capability_type: str = ""
    norm_ref: str = ""
    weight: float = 1.0
    proof_id: str = ""
    proof_hash: str = ""
    source_file: str = ""


@dataclass(slots=True)
class SMUPublicDTO(BaseDTO):
    smu_id: str = ""
    name: str = ""
    component_type: str = ""
    bridge_uri: str = ""
    composition_count: int = 0
    sealed_at: str = ""


@dataclass(slots=True)
class SMUSupervisorDTO(BaseDTO):
    smu_id: str = ""
    name: str = ""
    component_type: str = ""
    bridge_uri: str = ""
    spu_composition: list[dict[str, Any]] = field(default_factory=list)
    settlement_proof_hash: str = ""
    sealed_at: str = ""


@dataclass(slots=True)
class SMUOwnerDTO(BaseDTO):
    smu_id: str = ""
    name: str = ""
    component_type: str = ""
    bridge_uri: str = ""
    spu_composition: list[dict[str, Any]] = field(default_factory=list)
    total_settlement_value: float = 0.0
    settlement_proof_hash: str = ""
    sealed_at: str = ""


class DTORole:
    @staticmethod
    def normalize(value: str | Role | None) -> Role:
        if isinstance(value, Role):
            return value
        token = _to_text(value).strip().upper()
        return _ROLE_ALIASES.get(token, Role.PUBLIC)

    @staticmethod
    def executor(executor: dict[str, Any], role: str | Role | None) -> BaseDTO:
        r = DTORole.normalize(role)
        return ExecutorDTO(
            usi=_to_text(executor.get("executor_uri") or executor.get("usi")).strip(),
            role=r.value,
            executor_uri=_to_text(executor.get("executor_uri")).strip(),
            executor_name=_to_text(executor.get("executor_name") or executor.get("name")).strip(),
            executor_role=_to_text(executor.get("executor_role") or executor.get("role")).strip(),
        )

    @staticmethod
    def trip(trip: dict[str, Any], role: str | Role | None) -> BaseDTO:
        r = DTORole.normalize(role)
        return TripDTO(
            usi=_to_text(trip.get("trip_uri") or trip.get("usi")).strip(),
            role=r.value,
            trip_id=_to_text(trip.get("trip_id")).strip(),
            trip_uri=_to_text(trip.get("trip_uri")).strip(),
            status=_to_text(trip.get("status")).strip(),
            result=_to_text(trip.get("result")).strip(),
        )

    @staticmethod
    def norm_template(norm: dict[str, Any], role: str | Role | None) -> BaseDTO:
        r = DTORole.normalize(role)
        return NormTemplateDTO(
            usi=_to_text(norm.get("norm_uri") or norm.get("usi")).strip(),
            role=r.value,
            norm_uri=_to_text(norm.get("norm_uri")).strip(),
            title=_to_text(norm.get("title")).strip(),
            version=_to_text(norm.get("version")).strip(),
            status=_to_text(norm.get("status")).strip(),
        )

    @staticmethod
    def wallet(wallet: dict[str, Any], role: str | Role | None) -> BaseDTO:
        r = DTORole.normalize(role)
        return WalletDTO(
            usi=_to_text(wallet.get("wallet_uri") or wallet.get("usi")).strip(),
            role=r.value,
            wallet_uri=_to_text(wallet.get("wallet_uri")).strip(),
            owner_uri=_to_text(wallet.get("owner_uri")).strip(),
            balance=_to_float(wallet.get("balance"), 0.0),
            currency=_to_text(wallet.get("currency") or "CNY").strip() or "CNY",
        )

    @staticmethod
    def boq_item(boq: dict[str, Any], role: str | Role | None) -> BaseDTO:
        r = DTORole.normalize(role)
        usi = _to_text(boq.get("v_uri") or boq.get("boq_v_uri") or boq.get("usi")).strip()
        attached_spus = [
            _to_text(item).strip()
            for item in _as_list(boq.get("attached_spus"))
            if _to_text(item).strip()
        ]
        norm_refs = [
            _to_text(item).strip()
            for item in _as_list(boq.get("norm_refs"))
            if _to_text(item).strip()
        ]
        settlement_rules = [
            _to_text(item).strip()
            for item in _as_list(boq.get("settlement_rules"))
            if _to_text(item).strip()
        ]

        if r in {Role.PUBLIC, Role.MARKET}:
            return BOQItemPublicDTO(
                usi=usi,
                role=r.value,
                boq_item_id=_to_text(boq.get("boq_item_id")).strip(),
                description=_to_text(boq.get("description")).strip(),
                unit=_to_text(boq.get("unit")).strip(),
                boq_quantity=_to_float(boq.get("boq_quantity"), 0.0),
                bridge_name=_to_text(boq.get("bridge_name")).strip(),
                genesis_hash=_to_text(boq.get("genesis_hash")).strip(),
            )

        if r in {Role.AI, Role.SUPERVISOR, Role.REGULATOR}:
            return BOQItemSupervisorDTO(
                usi=usi,
                role=r.value,
                boq_item_id=_to_text(boq.get("boq_item_id")).strip(),
                description=_to_text(boq.get("description")).strip(),
                unit=_to_text(boq.get("unit")).strip(),
                boq_quantity=_to_float(boq.get("boq_quantity"), 0.0),
                bridge_name=_to_text(boq.get("bridge_name")).strip(),
                attached_spus=attached_spus,
                norm_refs=norm_refs,
                qc_gate_count=len(attached_spus),
                genesis_hash=_to_text(boq.get("genesis_hash")).strip(),
            )

        if r == Role.OWNER:
            return BOQItemOwnerDTO(
                usi=usi,
                role=r.value,
                boq_item_id=_to_text(boq.get("boq_item_id")).strip(),
                description=_to_text(boq.get("description")).strip(),
                unit=_to_text(boq.get("unit")).strip(),
                boq_quantity=_to_float(boq.get("boq_quantity"), 0.0),
                unit_price=_to_float(boq.get("unit_price"), 0.0),
                total_amount=_to_float(boq.get("total_amount"), 0.0),
                bridge_name=_to_text(boq.get("bridge_name")).strip(),
                attached_spus=attached_spus,
                norm_refs=norm_refs,
                settlement_rules=settlement_rules,
                genesis_hash=_to_text(boq.get("genesis_hash")).strip(),
            )

        return BaseDTO(usi=usi, role=r.value)

    @staticmethod
    def spu_boq_mapping(mapping: dict[str, Any], role: str | Role | None) -> BaseDTO:
        r = DTORole.normalize(role)
        usi = _to_text(mapping.get("boq_v_uri") or mapping.get("usi")).strip()
        if r in {Role.PUBLIC, Role.MARKET}:
            return SPUBOQMappingPublicDTO(
                usi=usi,
                role=r.value,
                mapping_id=_to_text(mapping.get("mapping_id")).strip(),
                boq_item_id=_to_text(mapping.get("boq_item_id")).strip(),
                spu_uri=_to_text(mapping.get("spu_uri")).strip(),
                capability_type=_to_text(mapping.get("capability_type")).strip(),
                norm_ref=_to_text(mapping.get("norm_ref")).strip(),
            )
        if r in {Role.AI, Role.SUPERVISOR, Role.REGULATOR}:
            return SPUBOQMappingSupervisorDTO(
                usi=usi,
                role=r.value,
                mapping_id=_to_text(mapping.get("mapping_id")).strip(),
                boq_item_id=_to_text(mapping.get("boq_item_id")).strip(),
                boq_v_uri=_to_text(mapping.get("boq_v_uri")).strip(),
                bridge_uri=_to_text(mapping.get("bridge_uri")).strip(),
                spu_uri=_to_text(mapping.get("spu_uri")).strip(),
                capability_type=_to_text(mapping.get("capability_type")).strip(),
                norm_ref=_to_text(mapping.get("norm_ref")).strip(),
                weight=_to_float(mapping.get("weight"), 1.0),
                proof_hash=_to_text(mapping.get("proof_hash")).strip(),
            )
        if r == Role.OWNER:
            return SPUBOQMappingOwnerDTO(
                usi=usi,
                role=r.value,
                mapping_id=_to_text(mapping.get("mapping_id")).strip(),
                boq_item_id=_to_text(mapping.get("boq_item_id")).strip(),
                boq_v_uri=_to_text(mapping.get("boq_v_uri")).strip(),
                bridge_uri=_to_text(mapping.get("bridge_uri")).strip(),
                spu_uri=_to_text(mapping.get("spu_uri")).strip(),
                capability_type=_to_text(mapping.get("capability_type")).strip(),
                norm_ref=_to_text(mapping.get("norm_ref")).strip(),
                weight=_to_float(mapping.get("weight"), 1.0),
                proof_id=_to_text(mapping.get("proof_id")).strip(),
                proof_hash=_to_text(mapping.get("proof_hash")).strip(),
                source_file=_to_text(mapping.get("source_file")).strip(),
            )
        return BaseDTO(usi=usi, role=r.value)

    @staticmethod
    def smu(smu: dict[str, Any], role: str | Role | None) -> BaseDTO:
        r = DTORole.normalize(role)
        usi = _to_text(smu.get("smu_uri") or smu.get("bridge_uri") or smu.get("usi")).strip()
        composition = [item for item in _as_list(smu.get("spu_composition")) if isinstance(item, dict)]
        if r in {Role.PUBLIC, Role.MARKET}:
            return SMUPublicDTO(
                usi=usi,
                role=r.value,
                smu_id=_to_text(smu.get("smu_id")).strip(),
                name=_to_text(smu.get("name")).strip(),
                component_type=_to_text(smu.get("component_type")).strip(),
                bridge_uri=_to_text(smu.get("bridge_uri")).strip(),
                composition_count=len(composition),
                sealed_at=_to_text(smu.get("sealed_at")).strip(),
            )
        if r in {Role.AI, Role.SUPERVISOR, Role.REGULATOR}:
            return SMUSupervisorDTO(
                usi=usi,
                role=r.value,
                smu_id=_to_text(smu.get("smu_id")).strip(),
                name=_to_text(smu.get("name")).strip(),
                component_type=_to_text(smu.get("component_type")).strip(),
                bridge_uri=_to_text(smu.get("bridge_uri")).strip(),
                spu_composition=composition,
                settlement_proof_hash=_to_text(smu.get("settlement_proof_hash")).strip(),
                sealed_at=_to_text(smu.get("sealed_at")).strip(),
            )
        if r == Role.OWNER:
            return SMUOwnerDTO(
                usi=usi,
                role=r.value,
                smu_id=_to_text(smu.get("smu_id")).strip(),
                name=_to_text(smu.get("name")).strip(),
                component_type=_to_text(smu.get("component_type")).strip(),
                bridge_uri=_to_text(smu.get("bridge_uri")).strip(),
                spu_composition=composition,
                total_settlement_value=_to_float(smu.get("total_settlement_value"), 0.0),
                settlement_proof_hash=_to_text(smu.get("settlement_proof_hash")).strip(),
                sealed_at=_to_text(smu.get("sealed_at")).strip(),
            )
        return BaseDTO(usi=usi, role=r.value)

    @staticmethod
    def boq_scan_bundle(
        *,
        scan_results: list[dict[str, Any]],
        mapping_rows: list[dict[str, Any]],
        smu_rows: list[dict[str, Any]] | None = None,
        role: str | Role | None,
    ) -> dict[str, Any]:
        effective_role = DTORole.normalize(role)
        boq_views: list[dict[str, Any]] = []
        mapping_views: list[dict[str, Any]] = []
        smu_views: list[dict[str, Any]] = []
        for item in scan_results:
            if not isinstance(item, dict):
                continue
            boq = item.get("boq_item") if isinstance(item.get("boq_item"), dict) else {}
            utxo = item.get("initial_utxo") if isinstance(item.get("initial_utxo"), dict) else {}
            merged = {
                **boq,
                "attached_spus": _as_list(utxo.get("attached_spus")),
            }
            dto = DTORole.boq_item(merged, effective_role)
            boq_views.append(dto.to_dict())
        for row in mapping_rows:
            if not isinstance(row, dict):
                continue
            dto = DTORole.spu_boq_mapping(row, effective_role)
            mapping_views.append(dto.to_dict())
        for row in _as_list(smu_rows):
            if not isinstance(row, dict):
                continue
            dto = DTORole.smu(row, effective_role)
            smu_views.append(dto.to_dict())
        return {
            "view_role": effective_role.value,
            "boq_items": boq_views,
            "spu_boq_mappings": mapping_views,
            "smu_units": smu_views,
            "generated_at": _utc_iso(),
        }


__all__ = [
    "BaseDTO",
    "BOQItemOwnerDTO",
    "BOQItemPublicDTO",
    "BOQItemSupervisorDTO",
    "DTORole",
    "ExecutorDTO",
    "NormTemplateDTO",
    "Role",
    "SPUBOQMappingOwnerDTO",
    "SPUBOQMappingPublicDTO",
    "SPUBOQMappingSupervisorDTO",
    "SMUOwnerDTO",
    "SMUPublicDTO",
    "SMUSupervisorDTO",
    "TripDTO",
    "WalletDTO",
]
