"""
DOCX engine mock fixtures.
services/api/docx_engine_mock_data.py
"""

from __future__ import annotations

from typing import Any

def build_rebar_live_mock_case() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Mock data compatible with ProofUTXOEngine rows.
    """
    project_meta = {
        "name": "\u6210\u5ce8\u9ad8\u901f",
        "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
        "contract_no": "CEGS-TJ01",
        "stake_range": "K22+500~K22+800",
        "check_date": "2026-03-26",
        "inspector": "\u738b\u8d28\u68c0",
        "tech_leader": "\u674e\u5de5",
        "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
        "construction_unit": "\u56db\u5ddd\u6210\u5ce8\u9ad8\u901f\u603b\u627f\u5305\u90e8",
        "template_name": "01_inspection_report.docx",
        "norm_ref": "JTG F80/1-2017",
    }
    proofs = [
        {
            "proof_id": "GP-PROOF-A1B2C3D4E5F60708",
            "proof_hash": "8fdce5686af2d6516c3e2fdf3f31d801cfd09e61a01f93838ec74ec31da43f4b",
            "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
            "segment_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/segment/K22+500/",
            "proof_type": "inspection",
            "result": "PASS",
            "gitpeg_anchor": "GitPeg#72d88d93",
            "signed_by": [
                {
                    "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
                    "role": "AI",
                    "ordosign_hash": "d0e8da4d4435630ee35f35ef",
                    "ts": "2026-03-26T10:10:00Z",
                }
            ],
            "created_at": "2026-03-26T10:10:00Z",
            "state_data": {
                "inspection_id": "24db30d4-b573-4ff8-b5ec-59f6e5f4df22",
                "v_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/inspection/24db30d4/",
                "location": "K22+500",
                "type": "rebar_spacing",
                "type_name": "\u53d7\u529b\u94a2\u7b4b\u95f4\u8ddd\uff08\u540c\u6392\uff09",
                "design": 300,
                "limit": "\u00b110",
                "values": [304, 299, 303, 301, 297, 296, 297, 300, 302, 297, 304, 299],
                "remark": "\u73b0\u573a\u62bd\u68c012\u70b9",
                "norm_ref": "JTG F80/1-2017",
            },
        },
        {
            "proof_id": "GP-PROOF-B1C2D3E4F5060708",
            "proof_hash": "21f51f453f248e73f3a6f11f91a79f7f17cd5c66f2269a205ca45d84f8f1732f",
            "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
            "segment_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/segment/K22+500/",
            "proof_type": "inspection",
            "result": "PASS",
            "gitpeg_anchor": "GitPeg#72d88d93",
            "signed_by": [
                {
                    "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
                    "role": "AI",
                    "ordosign_hash": "c3f8c4b76d90da7d5b08725d",
                    "ts": "2026-03-26T10:12:00Z",
                }
            ],
            "created_at": "2026-03-26T10:12:00Z",
            "state_data": {
                "inspection_id": "8f26d77c-6721-4ff3-a2ef-90d53ca2ecf0",
                "v_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/inspection/8f26d77c/",
                "location": "K22+500",
                "type": "rebar_spacing",
                "type_name": "\u53d7\u529b\u94a2\u7b4b\u95f4\u8ddd\uff08\u4e24\u6392\u4ee5\u4e0a\u6392\u8ddd\uff09",
                "design": 300,
                "limit": "\u00b110",
                "values": [304, 299, 303, 301, 297, 296, 297, 300, 302, 297],
                "remark": "\u73b0\u573a\u62bd\u68c010\u70b9",
                "norm_ref": "JTG F80/1-2017",
            },
        },
        {
            "proof_id": "GP-PROOF-C1D2E3F405060708",
            "proof_hash": "9b005bc4ef9d0f35a3945a502f6b29e6c867651fcd965dff1f4f9ea14303497e",
            "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
            "segment_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/segment/K22+500/",
            "proof_type": "inspection",
            "result": "PASS",
            "gitpeg_anchor": "GitPeg#72d88d93",
            "signed_by": [
                {
                    "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
                    "role": "AI",
                    "ordosign_hash": "2a20f39d3847c2921b5826fc",
                    "ts": "2026-03-26T10:14:00Z",
                }
            ],
            "created_at": "2026-03-26T10:14:00Z",
            "state_data": {
                "inspection_id": "b6ce12a3-e2a5-4797-a5d8-1017bbd33434",
                "v_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/inspection/b6ce12a3/",
                "location": "K22+500",
                "type": "cover_thickness",
                "type_name": "\u4fdd\u62a4\u5c42\u539a\u5ea6",
                "design": 30,
                "limit": "\u00b15",
                "values": [33, 29, 30, 31, 26, 33],
                "remark": "\u73b0\u573a\u62bd\u68c06\u70b9",
                "norm_ref": "JTG F80/1-2017",
            },
        },
    ]
    return proofs, project_meta

