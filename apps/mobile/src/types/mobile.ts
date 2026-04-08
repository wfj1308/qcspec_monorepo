export const MOBILE_ROLES = ['检查', '记录', '复核', '施工单位', '监理'] as const
export type MobileRole = (typeof MOBILE_ROLES)[number]

export const MOBILE_ROUTES = ['scan', 'workorder', 'form', 'sign', 'done', 'history'] as const
export type MobileRoute = (typeof MOBILE_ROUTES)[number]

export type StepStatus = 'done' | 'current' | 'todo'

export type GateOperator = 'gte' | 'lte' | 'range' | 'eq'

export type ThresholdValue = number | string | [number, number]

export type FieldThreshold = {
  operator: GateOperator
  value: ThresholdValue
}

export type MobileWorkStep = {
  key: string
  name: string
  status: StepStatus
  requiredRole: MobileRole
  formName?: string
  normrefUri?: string
  doneAt?: string
  doneBy?: string
  proofId?: string
}

export type MobileWorkorder = {
  code: string
  name: string
  vUri: string
  steps: MobileWorkStep[]
}

export type MobileBaseField = {
  key: string
  label: string
  type?: 'text' | 'date'
  readonly?: boolean
  defaultValue?: string
}

export type MobileFormField = {
  key: string
  label: string
  hint?: string
  unit?: string
  required: boolean
  threshold: FieldThreshold
}

export type MobileFormSpec = {
  subtitle: string
  normrefUri?: string
  baseFields: MobileBaseField[]
  fields: MobileFormField[]
}

export type FieldValidation = {
  ok: boolean
  message: string
  detail?: string
  tip?: string
}

export type PhotoEvidence = {
  preview: string
  base64: string
  hash: string
  gps: { lat: number | null; lng: number | null }
  timestamp: string
}

export type SignatureMethod = 'handwrite' | 'signpeg' | 'ca'
export type ChainSyncState = 'chained' | 'pending' | 'fallback'

export type HistoryRecord = {
  code: string
  step: string
  result: '合格' | '不合格'
  role: MobileRole
  time: string
  proofId: string
  nextStep: string
  chainSyncState?: ChainSyncState
  chainSyncMessage?: string
  chainSyncAction?: string
  chainSyncError?: string
}

export type RecentRecord = {
  code: string
  step: string
  time: string
}

export type PendingSubmission = {
  id: string
  payload: Record<string, unknown>
  retry: number
}

export type PendingAnchor = {
  id: string
  payload: Record<string, unknown>
  retry: number
}
