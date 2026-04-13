import { useCallback } from 'react'
import type { Report } from '@qcspec/types'
import { useUIStore } from '../../store'
import { useQCSpecDocPegApi } from './qcspecDocpeg'

type Dict = Record<string, unknown>

type TripItem = {
  trip_id?: string
  proof_id?: string
  status?: string
  result?: string
  created_at?: string
  updated_at?: string
  action?: string
  target_uri?: string
}

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Dict)
    : {}
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

function toText(value: unknown): string {
  return String(value || '').trim()
}

function toDateKey(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '00000000'
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}${m}${d}`
}

function normalizeResult(value: unknown): 'pass' | 'warn' | 'fail' {
  const text = toText(value).toLowerCase()
  if (text === 'pass' || text === 'warn' || text === 'fail') return text
  if (/fail|reject|error|blocked/.test(text)) return 'fail'
  if (/warn|pending|review/.test(text)) return 'warn'
  return 'pass'
}

function extractTrips(payload: unknown): TripItem[] {
  const row = asDict(payload)
  return asArray<TripItem>(row.items || row.data || row.list || asDict(row.result).items)
}

function mapTripsToReports(projectId: string, trips: TripItem[]): Report[] {
  const grouped = new Map<string, TripItem[]>()
  for (const trip of trips) {
    const day = toDateKey(toText(trip.created_at || trip.updated_at))
    if (!grouped.has(day)) grouped.set(day, [])
    grouped.get(day)?.push(trip)
  }

  return [...grouped.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([day, rows]) => {
      const total = rows.length
      const pass = rows.filter((row) => normalizeResult(row.result || row.status) === 'pass').length
      const warn = rows.filter((row) => normalizeResult(row.result || row.status) === 'warn').length
      const fail = rows.filter((row) => normalizeResult(row.result || row.status) === 'fail').length
      const passRate = total > 0 ? Math.round((pass / total) * 1000) / 10 : 0
      const latest = rows[0]
      const reportId = `REPORT-AUTO-${projectId}-${day}`
      const proofId = toText(latest?.proof_id)
      const location = toText(latest?.target_uri).split('/').filter(Boolean).slice(-1)[0] || undefined
      return {
        id: reportId,
        project_id: projectId,
        v_uri: `v://cn.docpeg/project/${projectId}/report/${reportId}`,
        report_no: `AUTO-${projectId.slice(0, 8).toUpperCase()}-${day}`,
        location,
        total_count: total,
        pass_count: pass,
        warn_count: warn,
        fail_count: fail,
        pass_rate: passRate,
        conclusion: fail === 0 ? '自动汇总：当前无不合格项' : '自动汇总：存在不合格项待处理',
        fail_items: fail === 0 ? '无' : `共 ${fail} 项异常`,
        suggestions: fail === 0 ? '保持当前工序质量控制。' : '建议优先复核异常工序并补充证据链。',
        file_url: undefined,
        proof_id: proofId || undefined,
        seal_status: proofId ? 'sealed' : 'unsigned',
        generated_at: toText(latest?.created_at || latest?.updated_at) || new Date().toISOString(),
      } satisfies Report
    })
}

export function useReports() {
  const { showToast } = useUIStore()
  const { listTripRoleTrips, loading } = useQCSpecDocPegApi()

  const generate = useCallback(async (_params: {
    project_id: string
    enterprise_id: string
    location?: string
    date_from?: string
    date_to?: string
  }) => {
    showToast('同事 API 暂未提供报告生成接口，当前页面仅展示自动汇总数据')
    return null
  }, [showToast])

  const exportDocpeg = useCallback(async (_params: {
    project_id: string
    enterprise_id: string
    type?: 'inspection' | 'lab' | 'monthly_summary' | 'final_archive'
    format?: 'docx' | 'pdf'
    location?: string
    date_from?: string
    date_to?: string
  }) => {
    showToast('同事 API 暂未提供报告导出接口')
    return null
  }, [showToast])

  const list = useCallback(async (project_id: string) => {
    const projectId = toText(project_id)
    if (!projectId) return { ok: true, data: [] as Report[] }

    const tripsRes = await listTripRoleTrips(projectId, {
      limit: 500,
      offset: 0,
    })

    const trips = extractTrips(tripsRes)
    const data = mapTripsToReports(projectId, trips)
    return { ok: true, data }
  }, [listTripRoleTrips])

  const getById = useCallback(async (_report_id: string) => {
    return null
  }, [])

  return { generate, exportDocpeg, list, getById, loading }
}
