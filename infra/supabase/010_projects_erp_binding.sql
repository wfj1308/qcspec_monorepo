-- Bind QCSpec project to ERP project identity.
-- Goal: keep ERP linkage stable by `erp_project_code` instead of project name text.

alter table if exists projects
  add column if not exists erp_project_code text,
  add column if not exists erp_project_name text;

update projects
set
  erp_project_code = coalesce(nullif(erp_project_code, ''), nullif(contract_no, ''), id::text),
  erp_project_name = coalesce(nullif(erp_project_name, ''), nullif(name, ''))
where
  erp_project_code is null
  or erp_project_code = ''
  or erp_project_name is null
  or erp_project_name = '';

create index if not exists idx_projects_enterprise_erp_project_code
  on projects(enterprise_id, erp_project_code);
