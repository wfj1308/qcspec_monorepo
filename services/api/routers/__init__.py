"""Router registry for QCSpec API."""

from __future__ import annotations

from fastapi import Depends

from services.api.dependencies import require_auth_identity

from . import auth, autoreg, boq, documents, erpnext, execution, inspections, intelligence, photos, projects, proof, reports, settlement, settings, smu, specification, team, trip_mock, utxo, verify

AUTH_DEP = [Depends(require_auth_identity)]

ROUTER_REGISTRY = [
    {"router": auth.router, "prefix": "/v1/auth", "tags": ["auth"]},
    {"router": projects.router, "prefix": "/v1/projects", "tags": ["projects"], "dependencies": AUTH_DEP},
    {"router": projects.public_router, "prefix": "/v1/projects", "tags": ["projects-public"]},
    {"router": inspections.router, "prefix": "/v1/inspections", "tags": ["inspections"], "dependencies": AUTH_DEP},
    {"router": photos.router, "prefix": "/v1/photos", "tags": ["photos"], "dependencies": AUTH_DEP},
    {"router": documents.router, "prefix": "/v1/proof", "tags": ["documents"], "dependencies": AUTH_DEP},
    {"router": boq.router, "prefix": "/v1/proof", "tags": ["boq"], "dependencies": AUTH_DEP},
    {"router": reports.router, "prefix": "/v1/reports", "tags": ["reports"], "dependencies": AUTH_DEP},
    {"router": reports.router, "prefix": "/api/reports", "tags": ["reports-api"], "dependencies": AUTH_DEP},
    {"router": trip_mock.router, "prefix": "/api/trip", "tags": ["trip-api"], "dependencies": AUTH_DEP},
    {"router": verify.router, "prefix": "/v1/verify", "tags": ["verify"], "dependencies": AUTH_DEP},
    {"router": verify.public_router, "prefix": "/api/verify", "tags": ["verify-public"]},
    {"router": verify.public_router, "prefix": "/api/v1/verify", "tags": ["verify-public-v1"]},
    {"router": proof.router, "prefix": "/v1/proof", "tags": ["proof"], "dependencies": AUTH_DEP},
    {"router": utxo.router, "prefix": "/v1/proof", "tags": ["utxo"], "dependencies": AUTH_DEP},
    {"router": smu.router, "prefix": "/v1/proof", "tags": ["smu"], "dependencies": AUTH_DEP},
    {"router": execution.router, "prefix": "/v1/proof", "tags": ["execution"], "dependencies": AUTH_DEP},
    {"router": intelligence.router, "prefix": "/v1/proof", "tags": ["intelligence"], "dependencies": AUTH_DEP},
    {"router": settlement.router, "prefix": "/v1/proof", "tags": ["settlement"], "dependencies": AUTH_DEP},
    {"router": specification.router, "prefix": "/v1/proof", "tags": ["specification"], "dependencies": AUTH_DEP},
    {"router": proof.public_router, "prefix": "/v1/proof", "tags": ["proof-public"]},
    {"router": smu.public_router, "prefix": "/v1/proof", "tags": ["smu-public"]},
    {"router": team.router, "prefix": "/v1/team", "tags": ["team"], "dependencies": AUTH_DEP},
    {"router": settings.router, "prefix": "/v1/settings", "tags": ["settings"], "dependencies": AUTH_DEP},
    {"router": erpnext.router, "prefix": "/v1/erpnext", "tags": ["erpnext"], "dependencies": AUTH_DEP},
    {"router": autoreg.router, "tags": ["autoreg"], "dependencies": AUTH_DEP},
]

__all__ = ["ROUTER_REGISTRY"]
