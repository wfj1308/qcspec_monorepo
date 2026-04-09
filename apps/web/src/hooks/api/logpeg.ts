import { useCallback } from 'react'
import { useAuthStore } from '../../store'
import { API_BASE, useRequest, withAuthHeaders } from './base'

export type MaterialConsumed = {
  name: string
  code: string
  qty: number
  unit: string
  unit_price: number
  total_cost: number
  iqc_batch: string
}

export type LogPegActivity = {
  time: string
  component_uri: string
  pile_id: string
  location: string
  process_step: string
  form_code: string
  trip_id: string
  primary_executor: string
  executor_org: string
  supervisor: string
  equipment_used: string[]
  gate_result: string
  proof_id: string
  materials_consumed: MaterialConsumed[]
  cost_labor: number
  cost_equipment: number
  cost_material: number
  cost_total: number
  remarks: string
}

export type MaterialSummary = {
  name: string
  code: string
  total_qty: number
  unit: string
  total_cost: number
}

export type EquipmentSummary = {
  name: string
  executor_uri: string
  shifts: number
  hours: number
  cost: number
}

export type PersonnelSummary = {
  name: string
  role: string
  executor_uri: string
  hours: number
  cost: number
}

export type ProgressSummary = {
  completed_steps: number
  generated_proofs: number
  components_completed: number
  components_in_progress: number
  pending_steps: number
}

export type QualitySummary = {
  total_inspections: number
  passed: number
  failed: number
  pass_rate: number
}

export type CostSummary = {
  daily_labor: number
  daily_equipment: number
  daily_material: number
  daily_total: number
  cumulative_total: number
}

export type LogPegAnomaly = {
  type: string
  severity: 'high' | 'medium' | 'low'
  component_uri: string
  description: string
  action_required: string
}

export type LogPegDailyLog = {
  log_date: string
  project_uri: string
  project_name: string
  contract_section: string
  weather: string
  temperature_range: string
  wind_level: string
  activities: LogPegActivity[]
  material_summary: MaterialSummary[]
  equipment_summary: EquipmentSummary[]
  personnel_summary: PersonnelSummary[]
  progress_summary: ProgressSummary
  quality_summary: QualitySummary
  cost_summary: CostSummary
  anomalies: LogPegAnomaly[]
  process_snapshot: Record<string, Record<string, unknown>>
  signed_by: string
  signed_at?: string | null
  sign_proof?: string
  v_uri: string
  data_hash: string
  language: 'zh' | 'en'
  locked: boolean
}

export type AggregateSummary = {
  total_completed_steps: number
  total_generated_proofs: number
  total_pending_steps: number
  total_failed: number
  total_material_cost: number
  total_labor_cost: number
  total_equipment_cost: number
  total_cost: number
  total_components_completed: number
  total_components_in_progress: number
  average_pass_rate: number
}

export type LogPegDailyResponse = {
  ok: boolean
  log: LogPegDailyLog
  v_uri?: string
  data_hash?: string
  sign_proof?: string
}

export type LogPegWeeklyResponse = {
  ok: boolean
  project_uri: string
  week_start: string
  week_end: string
  daily_logs: LogPegDailyLog[]
  weekly_summary: AggregateSummary
  language: 'zh' | 'en'
}

export type LogPegMonthlyResponse = {
  ok: boolean
  project_uri: string
  month: string
  daily_logs: LogPegDailyLog[]
  monthly_summary: AggregateSummary
  language: 'zh' | 'en'
}

export function useLogPegApi() {
  const { request, loading, error } = useRequest()

  const daily = useCallback(async (params: {
    project_id: string
    date: string
    weather?: string
    temperature_range?: string
    wind_level?: string
    language?: 'zh' | 'en'
  }) => {
    const qs = new URLSearchParams({
      date: params.date,
      ...(params.weather ? { weather: params.weather } : {}),
      ...(params.temperature_range ? { temperature_range: params.temperature_range } : {}),
      ...(params.wind_level ? { wind_level: params.wind_level } : {}),
      ...(params.language ? { language: params.language } : {}),
    }).toString()
    return request(`/api/v1/logpeg/${encodeURIComponent(params.project_id)}/daily?${qs}`, {
      skipAuthRedirect: true,
      timeoutMs: 90000,
    }) as Promise<LogPegDailyResponse | null>
  }, [request])

  const weekly = useCallback(async (params: {
    project_id: string
    week_start: string
    language?: 'zh' | 'en'
  }) => {
    const qs = new URLSearchParams({
      week_start: params.week_start,
      ...(params.language ? { language: params.language } : {}),
    }).toString()
    return request(`/api/v1/logpeg/${encodeURIComponent(params.project_id)}/weekly?${qs}`, {
      skipAuthRedirect: true,
      timeoutMs: 120000,
    }) as Promise<LogPegWeeklyResponse | null>
  }, [request])

  const monthly = useCallback(async (params: {
    project_id: string
    month: string
    language?: 'zh' | 'en'
  }) => {
    const qs = new URLSearchParams({
      month: params.month,
      ...(params.language ? { language: params.language } : {}),
    }).toString()
    return request(`/api/v1/logpeg/${encodeURIComponent(params.project_id)}/monthly?${qs}`, {
      skipAuthRedirect: true,
      timeoutMs: 120000,
    }) as Promise<LogPegMonthlyResponse | null>
  }, [request])

  const sign = useCallback(async (params: {
    project_id: string
    date: string
    executor_uri?: string
    signed_by?: string
    weather?: string
    temperature_range?: string
    wind_level?: string
    language?: 'zh' | 'en'
  }) => {
    return request(`/api/v1/logpeg/${encodeURIComponent(params.project_id)}/daily/sign`, {
      method: 'POST',
      skipAuthRedirect: true,
      body: JSON.stringify({
        date: params.date,
        executor_uri: params.executor_uri || '',
        signed_by: params.signed_by || '',
        weather: params.weather || '',
        temperature_range: params.temperature_range || '',
        wind_level: params.wind_level || '',
        language: params.language || 'zh',
      }),
      timeoutMs: 90000,
    }) as Promise<LogPegDailyResponse | null>
  }, [request])

  const exportDaily = useCallback(async (params: {
    project_id: string
    date: string
    format: 'pdf' | 'word' | 'json'
    language?: 'zh' | 'en'
  }) => {
    const token = useAuthStore.getState().token
    const qs = new URLSearchParams({
      date: params.date,
      format: params.format,
      language: params.language || 'zh',
    }).toString()
    const res = await fetch(`${API_BASE}/api/v1/logpeg/${encodeURIComponent(params.project_id)}/daily/export?${qs}`, {
      method: 'GET',
      headers: withAuthHeaders(token),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    const filename =
      (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] ||
      `logpeg-${params.date}.${params.format === 'word' ? 'docx' : params.format}`
    return { blob, filename }
  }, [])

  return {
    loading,
    error,
    daily,
    weekly,
    monthly,
    sign,
    exportDaily,
  }
}
