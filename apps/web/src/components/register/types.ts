export interface RegisterFormState {
  name: string
  type: string
  owner_unit: string
  erp_project_code: string
  erp_project_name: string
  contractor: string
  supervisor: string
  contract_no: string
  start_date: string
  end_date: string
  description: string
  seg_start: string
  seg_end: string
}

export interface RegisterErpBindingState {
  success: boolean
  code: string
  name: string
  reason: string
}
