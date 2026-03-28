import type { Dispatch, SetStateAction } from 'react'
import type { SettingsState } from './appShellShared'
import type { RegisterErpBindingState, RegisterFormState } from '../components/register/types'

interface ErpProjectBasicsResult {
  project_basics?: {
    project_code?: string
    project_name?: string
    owner_unit?: string
    contractor?: string
    supervisor?: string
    contract_no?: string
    start_date?: string
    end_date?: string
    description?: string
  }
}

interface PullErpProjectBindingFlowArgs {
  settings: SettingsState
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  regForm: RegisterFormState
  setRegForm: Dispatch<SetStateAction<RegisterFormState>>
  setErpBindingLoading: (value: boolean) => void
  setErpBinding: (value: RegisterErpBindingState) => void
  getErpProjectBasicsApi: (payload: Record<string, unknown>) => Promise<unknown>
  showToast: (message: string) => void
}

const normalizeDateOnly = (value?: string): string => {
  const text = String(value || '').trim()
  if (!text) return ''
  const match = text.match(/^(\d{4}-\d{2}-\d{2})/)
  return match ? match[1] : ''
}

export async function pullErpProjectBindingFlow({
  settings,
  canUseEnterpriseApi,
  enterpriseId,
  regForm,
  setRegForm,
  setErpBindingLoading,
  setErpBinding,
  getErpProjectBasicsApi,
  showToast,
}: PullErpProjectBindingFlowArgs): Promise<void> {
  if (!settings.erpnextSync) {
    showToast('ERP 同步未启用，无需拉取 ERP 项目')
    return
  }
  if (!canUseEnterpriseApi || !enterpriseId) {
    showToast('当前环境未连接企业后端，无法从 ERP 拉取项目')
    return
  }

  const lookupCode = String(regForm.erp_project_code || '').trim()
  const lookupName = String(regForm.erp_project_name || '').trim()
  if (!lookupCode) {
    showToast('请先填写 ERP 项目编码（如 PROJ-0001）')
    return
  }

  setErpBindingLoading(true)
  const res = (await getErpProjectBasicsApi({
    enterprise_id: enterpriseId,
    project_code: lookupCode,
    ...(lookupName ? { project_name: lookupName } : {}),
  })) as ErpProjectBasicsResult | null
  setErpBindingLoading(false)

  const basics = res?.project_basics
  if (!basics) {
    setErpBinding({ success: false, code: lookupCode, name: '', reason: 'fetch_failed' })
    return
  }

  const boundCode = String(basics.project_code || lookupCode).trim()
  const boundName = String(basics.project_name || '').trim()
  if (!boundCode || !boundName) {
    setErpBinding({
      success: false,
      code: boundCode || lookupCode,
      name: boundName,
      reason: 'missing_basics',
    })
    showToast('ERP 返回缺少项目编码或项目名称，无法绑定')
    return
  }

  setRegForm((prev) => ({
    ...prev,
    erp_project_code: boundCode,
    erp_project_name: boundName,
    owner_unit: String(basics.owner_unit || prev.owner_unit || '').trim(),
    contractor: String(basics.contractor || prev.contractor || '').trim(),
    supervisor: String(basics.supervisor || prev.supervisor || '').trim(),
    contract_no: String(basics.contract_no || prev.contract_no || '').trim(),
    start_date: normalizeDateOnly(basics.start_date) || prev.start_date,
    end_date: normalizeDateOnly(basics.end_date) || prev.end_date,
    description: String(basics.description || prev.description || '').trim(),
  }))

  setErpBinding({
    success: true,
    code: boundCode,
    name: boundName,
    reason: '',
  })
  showToast(`ERP 绑定成功：${boundCode} / ${boundName}`)
}

