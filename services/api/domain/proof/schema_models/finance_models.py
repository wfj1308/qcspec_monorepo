"""Finance/DocFinal request models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DocFinalExportBody(BaseModel):
    project_uri: str
    project_name: Optional[str] = None
    passphrase: str = Field(default="", description="Optional encryption passphrase (AES-256).")
    verify_base_url: str = "https://verify.qcspec.com"
    include_unsettled: bool = False


class DocFinalFinalizeBody(BaseModel):
    project_uri: str
    project_name: Optional[str] = None
    passphrase: str = Field(default="", description="Optional encryption passphrase (AES-256).")
    verify_base_url: str = "https://verify.qcspec.com"
    include_unsettled: bool = False
    run_anchor_rounds: int = Field(default=1, ge=0, le=5, description="How many anchor rounds to run after export.")


class PaymentCertificateBody(BaseModel):
    project_uri: str
    period: str = Field(..., description="YYYY-MM or YYYY-MM-DD or YYYY-MM-DD~YYYY-MM-DD")
    project_name: Optional[str] = None
    verify_base_url: str = "https://verify.qcspec.com"
    create_proof: bool = True
    executor_uri: str = "v://executor/system/"
    enforce_dual_pass: bool = True


class RailPactInstructionBody(BaseModel):
    payment_id: str
    executor_uri: str = "v://executor/owner/system/"
    auto_submit: bool = False

