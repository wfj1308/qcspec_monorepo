"""Compatibility SignPeg engine facade."""

from __future__ import annotations

from services.api.domain.signpeg.models import Executor, SignPegRequest, SignPegResult
from services.api.domain.signpeg.runtime.signpeg import (
    build_signpeg_signature,
    sign as sign_with_store,
    verify_signature,
)


def sign(req: SignPegRequest, executor: Executor, sb) -> SignPegResult:
    """Execute SignPeg sign with persistent backend store."""
    return sign_with_store(sb=sb, req=req, executor=executor)


def verify(
    sig_data: str,
    doc_id: str,
    body_hash: str,
    executor_uri: str,
    dto_role: str,
    trip_role: str,
    signed_at,
) -> bool:
    return verify_signature(
        sig_data=sig_data,
        doc_id=doc_id,
        body_hash=body_hash,
        executor_uri=executor_uri,
        dto_role=dto_role,
        trip_role=trip_role,
        signed_at=signed_at,
    )


__all__ = ["sign", "verify", "build_signpeg_signature"]

