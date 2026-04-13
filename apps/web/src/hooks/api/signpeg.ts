import { useCallback, useRef } from 'react'
import { useUIStore } from '../../store'

export type SignPegRole = 'inspector' | 'recorder' | 'reviewer' | 'constructor' | 'supervisor'

export type SignPegStatusItem = {
  dto_role: string
  trip_role: string
  executor_uri: string
  executor_name: string
  signed_at: string
  sig_data: string
  trip_uri: string
  verified: boolean
}

export type SignPegSignPayload = {
  doc_id: string
  body_hash: string
  executor_uri: string
  dto_role: SignPegRole
  trip_role: string
  action: 'approve' | 'reject' | 'submit' | 'sign'
  actor_executor_uri?: string
  delegation_uri?: string
  project_trip_root?: string
}

export type SignPegSignResponse = {
  ok: boolean
  sig_type: string
  sig_data: string
  signed_at: string
  executor_uri: string
  executor_name: string
  dto_role: string
  trip_role: string
  doc_id: string
  body_hash: string
  trip_uri: string
  verified: boolean
  delegation_uri?: string
}

export type SignPegStatusResponse = {
  ok: boolean
  signatures: SignPegStatusItem[]
  all_signed: boolean
  next_required: string
  next_executor: string
  current_slot?: number
  next_slot?: number
  blocked_reason?: string
}

export type ExecutorSkill = {
  skill_uri: string
  skill_name?: string
  level?: number | string
  verified_by?: string
  proof_uri?: string
  cert_no: string
  issued_by: string
  valid_until: string
  scope?: string[]
}

export type ExecutorRecordResponse = {
  ok: boolean
  executor: {
    executor_uri: string
    name: string
    org_uri: string
    skills: ExecutorSkill[]
    status: string
    holder_name: string
    holder_id: string
  }
  holder_history: Array<Record<string, unknown>>
}

export type ExplainIssue = {
  field: string
  expected: string
  actual: string
  deviation: string
  norm_ref: string
  severity: 'blocking' | 'warning' | 'info'
  explanation: string
}

export type GateExplainResponse = {
  ok: boolean
  result: {
    passed: boolean
    summary: string
    issues: ExplainIssue[]
    next_steps: string[]
    norm_refs: string[]
    language: 'zh' | 'en'
  }
}

export type ProcessExplainResponse = {
  ok: boolean
  result: {
    step: string
    status: 'locked' | 'active' | 'completed'
    summary: string
    blocking_reasons: Array<{ type: string; description: string; action: string }>
    estimated_unblock: string
    language: 'zh' | 'en'
  }
}

export type FieldValidationResponse = {
  ok: boolean
  result: {
    field: string
    value: unknown
    status: 'ok' | 'warning' | 'blocking'
    message: string
    norm_ref: string
    expected: string
    actual: string
    deviation: string
    language: 'zh' | 'en'
  }
}

export function useSignPegApi() {
  const showToast = useUIStore((s) => s.showToast)
  const warnedRef = useRef(false)

  const notifyUnsupported = useCallback(() => {
    if (warnedRef.current) return
    warnedRef.current = true
    showToast('[Info] SignPeg API is not integrated yet')
  }, [showToast])

  const unsupported = useCallback(async <T = unknown>() => {
    notifyUnsupported()
    return null as T | null
  }, [notifyUnsupported])

  const sign = useCallback(async (_payload: SignPegSignPayload) => {
    return unsupported<SignPegSignResponse>()
  }, [unsupported])

  const status = useCallback(async (_docId: string) => {
    return unsupported<SignPegStatusResponse>()
  }, [unsupported])

  const getExecutor = useCallback(async (_executorUri: string) => {
    return unsupported<ExecutorRecordResponse>()
  }, [unsupported])

  const explainGate = useCallback(async (_payload: {
    form_code: string
    gate_result: Record<string, unknown>
    norm_context?: Record<string, unknown>
    language?: 'zh' | 'en'
  }) => {
    return unsupported<GateExplainResponse>()
  }, [unsupported])

  const explainProcess = useCallback(async (_payload: {
    project_uri: string
    component_uri: string
    step_id: string
    current_status: 'locked' | 'active' | 'completed'
    chain_snapshot?: Record<string, unknown>
    language?: 'zh' | 'en'
  }) => {
    return unsupported<ProcessExplainResponse>()
  }, [unsupported])

  const validateFieldRealtime = useCallback(async (_payload: {
    form_code: string
    field_key: string
    value: unknown
    context?: Record<string, unknown>
    language?: 'zh' | 'en'
  }) => {
    return unsupported<FieldValidationResponse>()
  }, [unsupported])

  return {
    sign,
    status,
    getExecutor,
    explainGate,
    explainProcess,
    validateFieldRealtime,
  }
}
