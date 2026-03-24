"""
ERPNext/Frappe Server Script: Project on_submit -> QCSpec autoreg backend.

How to use:
1) ERPNext -> Server Script -> New
2) Script Type: DocType Event
3) Reference DocType: Project
4) Event: After Submit
5) Paste this script
6) Set site config:
   - qcspec_autoreg_url
   - qcspec_autoreg_token (optional)
"""

import json

import frappe
import requests


def _v_namespace():
    root = frappe.conf.get("qcspec_v_namespace") or "v://cn.zhongbei/"
    root = str(root).strip()
    if not root.endswith("/"):
        root += "/"
    return root


def _project_code(doc):
    return (
        str(getattr(doc, "project_code", "") or "").strip()
        or str(getattr(doc, "name", "") or "").strip()
    )


def _site_code(doc):
    # Prefer explicit code-like fields if present.
    for field in ("site_code", "custom_site_code", "project_code"):
        value = str(getattr(doc, field, "") or "").strip()
        if value:
            return value
    return _project_code(doc)


def run_autoreg(doc):
    endpoint = str(frappe.conf.get("qcspec_autoreg_url") or "").strip()
    if not endpoint:
        frappe.log_error("missing qcspec_autoreg_url in site config", "QCSpec AutoReg")
        return

    payload = {
        "project_code": _project_code(doc),
        "project_name": str(getattr(doc, "project_name", "") or doc.name).strip(),
        "site_code": _site_code(doc),
        "site_name": str(getattr(doc, "project_name", "") or doc.name).strip(),
        "namespace_uri": _v_namespace(),
        "source_system": "erpnext",
    }

    headers = {"Content-Type": "application/json"}
    token = str(frappe.conf.get("qcspec_autoreg_token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=10)
        resp.raise_for_status()
        body = resp.json()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "QCSpec AutoReg")
        raise

    # Writeback fields; ensure these custom fields exist on Project.
    doc.db_set("gitpeg_project_uri", body.get("gitpeg_project_uri"), update_modified=False)
    doc.db_set("gitpeg_site_uri", body.get("gitpeg_site_uri"), update_modified=False)
    doc.db_set("gitpeg_status", body.get("gitpeg_status") or "active", update_modified=False)
    doc.db_set(
        "gitpeg_register_result_json",
        json.dumps(body, ensure_ascii=False),
        update_modified=False,
    )


# For ERPNext Server Script (DocType Event), `doc` is provided in globals.
if "doc" in globals():
    run_autoreg(doc)


# For custom app hooks.py use:
#   doc_events = {"Project": {"on_submit": "your_app.path.to.module.on_submit"}}
def on_submit(doc, method=None):
    run_autoreg(doc)
