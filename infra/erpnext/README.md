# ERPNext integration snippets

This folder contains deployable snippets that were missing from the repo but required by the handoff flow.

## 1) Project on_submit auto-registration

File: `project_on_submit_autoreg.py`

- Type: ERPNext/Frappe `Server Script`
- DocType: `Project`
- Event: `After Submit` (or `on_submit`)
- Purpose: call backend `POST /v1/autoreg/project` and write back GitPeg URIs.

## 2) Required custom fields on ERPNext Project

- `gitpeg_project_uri` (Data)
- `gitpeg_site_uri` (Data)
- `gitpeg_status` (Data/Select)
- `gitpeg_register_result_json` (Long Text)

## 3) Required site config keys

In `site_config.json` (or equivalent environment override):

- `qcspec_autoreg_url`  
  example: `http://127.0.0.1:8000/v1/autoreg/project`
- `qcspec_autoreg_token` (optional)  
  if backend requires an owner token, send `Authorization: Bearer <token>`.
