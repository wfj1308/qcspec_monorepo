"""Router registry for QCSpec API."""

from __future__ import annotations

from fastapi import Depends

from services.api.dependencies import require_auth_identity

from . import auth, autoreg, boq, boqpeg, documents, erpnext, execution, finance, inspections, intelligence, photos, projects, proof, reporting, settings, smu, specification, specir, team, trip_mock, utxo, verify

AUTH_DEP = [Depends(require_auth_identity)]

ROUTER_REGISTRY = [
    {"router": auth.router, "prefix": "/v1/auth", "tags": ["auth"]},
    {"router": projects.router, "prefix": "/v1/projects", "tags": ["projects"], "dependencies": AUTH_DEP},
    {"router": projects.public_router, "prefix": "/v1/projects", "tags": ["projects-public"]},
    {"router": inspections.router, "prefix": "/v1/inspections", "tags": ["inspections"], "dependencies": AUTH_DEP},
    {"router": photos.router, "prefix": "/v1/photos", "tags": ["photos"], "dependencies": AUTH_DEP},
    {"router": documents.router, "prefix": "/v1/proof", "tags": ["documents"], "dependencies": AUTH_DEP},
    {"router": boq.router, "prefix": "/v1/proof", "tags": ["boq"], "dependencies": AUTH_DEP},
    {"router": boqpeg.router, "prefix": "/v1/proof", "tags": ["boqpeg"], "dependencies": AUTH_DEP},
    {"router": reporting.router, "prefix": "/v1/reports", "tags": ["reporting"], "dependencies": AUTH_DEP},
    {"router": reporting.router, "prefix": "/api/reports", "tags": ["reporting-api"], "dependencies": AUTH_DEP},
    {"router": trip_mock.router, "prefix": "/api/trip", "tags": ["trip-api"], "dependencies": AUTH_DEP},
    {"router": verify.router, "prefix": "/v1/verify", "tags": ["verify"], "dependencies": AUTH_DEP},
    {"router": verify.public_router, "prefix": "/api/verify", "tags": ["verify-public"]},
    {"router": verify.public_router, "prefix": "/api/v1/verify", "tags": ["verify-public-v1"]},
    {"router": proof.router, "prefix": "/v1/proof", "tags": ["proof"], "dependencies": AUTH_DEP},
    {"router": utxo.router, "prefix": "/v1/proof", "tags": ["utxo"], "dependencies": AUTH_DEP},
    {"router": smu.router, "prefix": "/v1/proof", "tags": ["smu"], "dependencies": AUTH_DEP},
    {"router": execution.router, "prefix": "/v1/proof", "tags": ["execution"], "dependencies": AUTH_DEP},
    {"router": intelligence.router, "prefix": "/v1/proof", "tags": ["intelligence"], "dependencies": AUTH_DEP},
    {"router": finance.router, "prefix": "/v1/proof", "tags": ["finance"], "dependencies": AUTH_DEP},
    {"router": specification.router, "prefix": "/v1/proof", "tags": ["specification"], "dependencies": AUTH_DEP},
    {"router": specir.router, "prefix": "/v1/specir", "tags": ["specir"], "dependencies": AUTH_DEP},
    {"router": proof.public_router, "prefix": "/v1/proof", "tags": ["proof-public"]},
    {"router": smu.public_router, "prefix": "/v1/proof", "tags": ["smu-public"]},
    {"router": boqpeg.public_router, "prefix": "/v1/proof", "tags": ["boqpeg-public"]},
    {"router": team.router, "prefix": "/v1/team", "tags": ["team"], "dependencies": AUTH_DEP},
    {"router": settings.router, "prefix": "/v1/settings", "tags": ["settings"], "dependencies": AUTH_DEP},
    {"router": erpnext.router, "prefix": "/v1/erpnext", "tags": ["erpnext"], "dependencies": AUTH_DEP},
    {"router": autoreg.router, "tags": ["autoreg"], "dependencies": AUTH_DEP},
    # Structured prefixes for kernel/product boundaries.
    # Old `/v1/proof/*` routes stay active for compatibility during migration.
    {"router": proof.router, "prefix": "/v1/docpeg/proof", "tags": ["docpeg-proof"], "dependencies": AUTH_DEP},
    {"router": utxo.router, "prefix": "/v1/docpeg", "tags": ["docpeg-utxo"], "dependencies": AUTH_DEP},
    {"router": smu.router, "prefix": "/v1/docpeg", "tags": ["docpeg-smu"], "dependencies": AUTH_DEP},
    {"router": smu.public_router, "prefix": "/v1/docpeg", "tags": ["docpeg-smu-public"]},
    {"router": boq.router, "prefix": "/v1/qcspec", "tags": ["qcspec-boq"], "dependencies": AUTH_DEP},
    {"router": boqpeg.router, "prefix": "/v1/qcspec", "tags": ["qcspec-boqpeg"], "dependencies": AUTH_DEP},
    {"router": boqpeg.public_router, "prefix": "/v1/qcspec", "tags": ["qcspec-boqpeg-public"]},
    {"router": boqpeg.router, "prefix": "/v1/boqpeg", "tags": ["boqpeg-product"], "dependencies": AUTH_DEP},
    {"router": boqpeg.public_router, "prefix": "/v1/boqpeg", "tags": ["boqpeg-product-public"]},
    {"router": boqpeg.router, "prefix": "/v1/listpeg", "tags": ["listpeg-product"], "dependencies": AUTH_DEP},
    {"router": boqpeg.public_router, "prefix": "/v1/listpeg", "tags": ["listpeg-product-public"]},
    {"router": execution.router, "prefix": "/v1/qcspec", "tags": ["qcspec-execution"], "dependencies": AUTH_DEP},
    {"router": intelligence.router, "prefix": "/v1/qcspec", "tags": ["qcspec-intelligence"], "dependencies": AUTH_DEP},
    {"router": documents.router, "prefix": "/v1/docfinal", "tags": ["docfinal-documents"], "dependencies": AUTH_DEP},
    {"router": finance.router, "prefix": "/v1/railpact", "tags": ["railpact-finance"], "dependencies": AUTH_DEP},
    {"router": specification.router, "prefix": "/v1/normref", "tags": ["normref-specification"], "dependencies": AUTH_DEP},
    {"router": specification.router, "prefix": "/api/normref", "tags": ["normref-specification-api"], "dependencies": AUTH_DEP},
    {"router": specir.router, "prefix": "/v1/normref/specir", "tags": ["normref-specir"], "dependencies": AUTH_DEP},
]

__all__ = ["ROUTER_REGISTRY"]
