import { useCallback } from 'react'

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

const logpegStore = new Map<string, LogPegDailyLog>()

function emptyAggregate(): AggregateSummary {
  return {
    total_completed_steps: 0,
    total_generated_proofs: 0,
    total_pending_steps: 0,
    total_failed: 0,
    total_material_cost: 0,
    total_labor_cost: 0,
    total_equipment_cost: 0,
    total_cost: 0,
    total_components_completed: 0,
    total_components_in_progress: 0,
    average_pass_rate: 0,
  }
}

function buildEmptyDailyLog(params: {
  project_id: string
  date: string
  weather?: string
  temperature_range?: string
  wind_level?: string
  language?: 'zh' | 'en'
}): LogPegDailyLog {
  return {
    log_date: params.date,
    project_uri: `v://project/${params.project_id}`,
    project_name: params.project_id,
    contract_section: '',
    weather: params.weather || '',
    temperature_range: params.temperature_range || '',
    wind_level: params.wind_level || '',
    activities: [],
    material_summary: [],
    equipment_summary: [],
    personnel_summary: [],
    progress_summary: {
      completed_steps: 0,
      generated_proofs: 0,
      components_completed: 0,
      components_in_progress: 0,
      pending_steps: 0,
    },
    quality_summary: {
      total_inspections: 0,
      passed: 0,
      failed: 0,
      pass_rate: 0,
    },
    cost_summary: {
      daily_labor: 0,
      daily_equipment: 0,
      daily_material: 0,
      daily_total: 0,
      cumulative_total: 0,
    },
    anomalies: [],
    process_snapshot: {},
    signed_by: '',
    signed_at: null,
    sign_proof: '',
    v_uri: `v://project/${params.project_id}/logpeg/${params.date}/`,
    data_hash: '',
    language: params.language || 'zh',
    locked: false,
  }
}

export function useLogPegApi() {
  const daily = useCallback(async (params: {
    project_id: string
    date: string
    weather?: string
    temperature_range?: string
    wind_level?: string
    language?: 'zh' | 'en'
  }) => {
    const key = `${params.project_id}:${params.date}`
    const log = logpegStore.get(key) || buildEmptyDailyLog(params)
    logpegStore.set(key, log)
    return { ok: true, log } as LogPegDailyResponse
  }, [])

  const weekly = useCallback(async (params: {
    project_id: string
    week_start: string
    language?: 'zh' | 'en'
  }) => {
    return {
      ok: true,
      project_uri: `v://project/${params.project_id}`,
      week_start: params.week_start,
      week_end: params.week_start,
      daily_logs: [],
      weekly_summary: emptyAggregate(),
      language: params.language || 'zh',
    } as LogPegWeeklyResponse
  }, [])

  const monthly = useCallback(async (params: {
    project_id: string
    month: string
    language?: 'zh' | 'en'
  }) => {
    return {
      ok: true,
      project_uri: `v://project/${params.project_id}`,
      month: params.month,
      daily_logs: [],
      monthly_summary: emptyAggregate(),
      language: params.language || 'zh',
    } as LogPegMonthlyResponse
  }, [])

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
    const key = `${params.project_id}:${params.date}`
    const base = logpegStore.get(key) || buildEmptyDailyLog({
      project_id: params.project_id,
      date: params.date,
      weather: params.weather,
      temperature_range: params.temperature_range,
      wind_level: params.wind_level,
      language: params.language,
    })
    const next: LogPegDailyLog = {
      ...base,
      weather: params.weather || base.weather,
      temperature_range: params.temperature_range || base.temperature_range,
      wind_level: params.wind_level || base.wind_level,
      signed_by: params.signed_by || '',
      signed_at: new Date().toISOString(),
      sign_proof: '',
      locked: true,
    }
    logpegStore.set(key, next)
    return { ok: true, log: next } as LogPegDailyResponse
  }, [])

  const exportDaily = useCallback(async (params: {
    project_id: string
    date: string
    format: 'pdf' | 'word' | 'json'
    language?: 'zh' | 'en'
  }) => {
    const key = `${params.project_id}:${params.date}`
    const log = logpegStore.get(key) || buildEmptyDailyLog({
      project_id: params.project_id,
      date: params.date,
      language: params.language,
    })
    const text = JSON.stringify(log, null, 2)
    const ext = params.format === 'word' ? 'docx' : params.format
    const mime = params.format === 'pdf'
      ? 'application/pdf'
      : params.format === 'word'
        ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        : 'application/json'
    return {
      blob: new Blob([text], { type: mime }),
      filename: `logpeg-${params.date}.${ext}`,
    }
  }, [])

  return {
    loading: false,
    error: null,
    daily,
    weekly,
    monthly,
    sign,
    exportDaily,
  }
}
