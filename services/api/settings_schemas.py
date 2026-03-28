"""
Request models for settings router.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    enterpriseName: Optional[str] = None
    enterpriseVUri: Optional[str] = None
    enterpriseCreditCode: Optional[str] = None
    emailNotify: Optional[bool] = None
    wechatNotify: Optional[bool] = None
    autoGenerateReport: Optional[bool] = None
    strictProof: Optional[bool] = None
    reportTemplate: Optional[str] = None
    reportHeader: Optional[str] = None
    webhookUrl: Optional[str] = None
    gitpegToken: Optional[str] = None
    gitpegEnabled: Optional[bool] = None
    gitpegRegistrarBaseUrl: Optional[str] = None
    gitpegPartnerCode: Optional[str] = None
    gitpegIndustryCode: Optional[str] = None
    gitpegClientId: Optional[str] = None
    gitpegClientSecret: Optional[str] = None
    gitpegRegistrationMode: Optional[str] = None
    gitpegReturnUrl: Optional[str] = None
    gitpegWebhookUrl: Optional[str] = None
    gitpegWebhookSecret: Optional[str] = None
    gitpegModuleCandidates: Optional[list[str]] = None
    erpnextSync: Optional[bool] = None
    erpnextUrl: Optional[str] = None
    erpnextSiteName: Optional[str] = None
    erpnextApiKey: Optional[str] = None
    erpnextApiSecret: Optional[str] = None
    erpnextUsername: Optional[str] = None
    erpnextPassword: Optional[str] = None
    erpnextProjectDoctype: Optional[str] = None
    erpnextProjectLookupField: Optional[str] = None
    erpnextProjectLookupValue: Optional[str] = None
    erpnextGitpegProjectUriField: Optional[str] = None
    erpnextGitpegSiteUriField: Optional[str] = None
    erpnextGitpegStatusField: Optional[str] = None
    erpnextGitpegResultJsonField: Optional[str] = None
    erpnextGitpegRegistrationIdField: Optional[str] = None
    erpnextGitpegNodeUriField: Optional[str] = None
    erpnextGitpegShellUriField: Optional[str] = None
    erpnextGitpegProofHashField: Optional[str] = None
    erpnextGitpegIndustryProfileIdField: Optional[str] = None
    wechatMiniapp: Optional[bool] = None
    droneImport: Optional[bool] = None
    permissionMatrix: Optional[list[dict]] = None


class ErpNextTestRequest(BaseModel):
    url: str
    siteName: Optional[str] = None
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    timeoutMs: Optional[int] = 8000


class GitPegRegistrarTestRequest(BaseModel):
    baseUrl: str
    partnerCode: str
    industryCode: str
    clientId: Optional[str] = None
    clientSecret: Optional[str] = None
    registrationMode: Optional[str] = "DOMAIN"
    returnUrl: Optional[str] = None
    webhookUrl: Optional[str] = None
    moduleCandidates: Optional[list[str]] = None
    timeoutMs: Optional[int] = 10000
