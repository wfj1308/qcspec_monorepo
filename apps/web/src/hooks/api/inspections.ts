import { useCallback } from 'react'
import type { InspectResult, Inspection } from '@qcspec/types'
import { useQCSpecDocPegApi } from './qcspecDocpeg'

type Dict = Record<string, unknown>

type TripItem = {
  trip_id?: string
  trip_uri?: string
  action?: string
  status?: string
  target_uri?: string
  component_uri?: string
  proof_id?: string
  created_at?: string
  updated_at?: string
  result?: string
  payload?: Dict
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

function toNumber(value: unknown): number | undefined {
  const n = Number(value)
  return Number.isFinite(n) ? n : undefined
}

function normalizeInspectResult(value: unknown): InspectResult {
  const text = toText(value).toLowerCase()
  if (text === 'pass' || text === 'warn' || text === 'fail') return text
  if (/fail|reject|error|blocked/.test(text)) return 'fail'
  if (/warn|pending|review/.test(text)) return 'warn'
  return 'pass'
}

function parseLocation(item: TripItem): string {
  const fromPayload = toText(item.payload?.inspection_location || item.payload?.location || item.payload?.pile_id)
  if (fromPayload) return fromPayload

  const fromTarget = toText(item.target_uri || item.component_uri)
  if (!fromTarget) return '-'
  const parts = fromTarget.split('/').filter(Boolean)
  return parts[parts.length - 1] || '-'
}

function parseType(action: string): { type: string; typeName: string } {
  const text = toText(action)
  if (!text) return { type: 'unknown', typeName: '未标注工序' }

  const tail = text.split('.').filter(Boolean).slice(-1)[0] || text
  const normalized = tail.replace(/[^a-zA-Z0-9_\-]/g, '_') || 'unknown'
  return {
    type: normalized.toLowerCase(),
    typeName: text,
  }
}

function mapTripToInspection(item: TripItem): Inspection | null {
  const id = toText(item.trip_id)
  if (!id) return null

  const action = toText(item.action)
  const parsedType = parseType(action)
  const result = normalizeInspectResult(item.result || item.status)
  const proofId = toText(item.proof_id)
  const measuredValue =
    toNumber(item.payload?.inspection_value) ??
    toNumber(item.payload?.value) ??
    toNumber(item.payload?.measurement) ??
    0

  return {
    id,
    project_id: toText(item.payload?.project_id || ''),
    v_uri: toText(item.trip_uri) || `v://cn.docpeg/trip/${id}`,
    location: parseLocation(item),
    type: parsedType.type,
    type_name: parsedType.typeName,
    value: measuredValue,
    standard: toNumber(item.payload?.standard),
    unit: toText(item.payload?.unit) || '-',
    result,
    design: toNumber(item.payload?.design),
    limit: toText(item.payload?.limit) || undefined,
    values: asArray<number>(item.payload?.values),
    person: toText(item.payload?.person || item.payload?.inspector || item.payload?.executor_name) || undefined,
    remark: toText(item.payload?.remark || item.payload?.result_note) || undefined,
    proof_id: proofId || undefined,
    proof_hash: toText(item.payload?.proof_hash) || undefined,
    proof_status: proofId ? 'confirmed' : 'pending',
    seal_status: proofId ? 'sealed' : 'unsigned',
    inspected_at: toText(item.created_at || item.updated_at) || new Date().toISOString(),
  }
}

function extractTripItems(payload: unknown): TripItem[] {
  const row = asDict(payload)
  return asArray<TripItem>(row.items || row.data || row.list || asDict(row.result).items)
}

export function useInspections() {
  const {
    listTripRoleTrips,
    executeExecpeg,
    getExecpegStatus,
    getExecpegCallbacks,
    loading,
  } = useQCSpecDocPegApi()

  const list = useCallback(async (
    project_id: string,
    params: Record<string, string> = {},
  ) => {
    const projectId = toText(project_id)
    if (!projectId) return { ok: true, data: [], total: 0 }

    const limit = Number(params.limit || 200)
    const offset = Number(params.offset || 0)

    const tripsRes = await listTripRoleTrips(projectId, {
      limit: Number.isFinite(limit) ? Math.max(1, Math.min(limit, 500)) : 200,
      offset: Number.isFinite(offset) ? Math.max(0, offset) : 0,
    })

    const items = extractTripItems(tripsRes)
      .map((item) => mapTripToInspection(item))
      .filter((item): item is Inspection => Boolean(item))
      .map((item) => ({ ...item, project_id: item.project_id || projectId }))

    const total = Number(asDict(tripsRes).total)
    return {
      ok: true,
      data: items,
      total: Number.isFinite(total) ? total : items.length,
    }
  }, [listTripRoleTrips])

  const submit = useCallback(async (body: Record<string, unknown>) => {
    const projectId = toText(body.project_id)
    if (!projectId) return null

    const inspectionId = `INS-DOCPEG-${Date.now()}`
    const result = normalizeInspectResult(body.result)
    const tripRoleId = toText(body.exec_trip_role_id || body.trip_role_id || body.tripRoleId)

    if (!tripRoleId) {
      return {
        ok: true,
        inspection_id: inspectionId,
        result,
        proof_id: toText(body.proof_id),
        unsupported: true,
        source: 'docpeg-api-pack-placeholder',
      }
    }

    const projectRef = toText(body.project_ref || body.projectRef) || `v://cn.project/${projectId}`
    const componentRef = toText(body.component_ref || body.componentRef || body.component_uri) || `v://cn.project/${projectId}/component/default`
    const callbackUrl = toText(body.callback_url || body.callbackUrl)
    const payload = {
      tripRoleId,
      projectRef,
      componentRef,
      context: {
        autoData: {},
        manualInput: {
          source: 'qcspec_web_inspection_submit',
          inspection_id: inspectionId,
          type: toText(body.type),
          location: toText(body.location),
          result,
        },
      },
      ...(callbackUrl ? { callbackUrl } : {}),
    }

    const execRes = await executeExecpeg(payload, {
      idempotencyKey: `${projectId}-${inspectionId}`,
    })

    const execId = toText(asDict(execRes).execId || asDict(execRes).exec_id)
    const statusRes = execId ? await getExecpegStatus(execId) : null
    const callbackRes = execId ? await getExecpegCallbacks(execId, { limit: 1, offset: 0 }) : null
    const callbackTotal = Number(asDict(callbackRes).total)

    const proofId = toText(
      asDict(execRes).proof_id ||
      asDict(asDict(execRes).proof).proofId ||
      asDict(asDict(statusRes).exec).proofId ||
      asDict(asDict(statusRes).execution).proofId ||
      asDict(asDict(asDict(statusRes).execution).proof).proofId,
    )
    const execStatus = toText(
      asDict(execRes).status ||
      asDict(asDict(statusRes).exec).status ||
      asDict(asDict(statusRes).execution).status,
    )

    return {
      ok: true,
      inspection_id: inspectionId,
      result,
      proof_id: proofId,
      exec_id: execId || undefined,
      exec_status: execStatus || undefined,
      callback_total: Number.isFinite(callbackTotal) ? callbackTotal : undefined,
      source: 'docpeg-execpeg',
    }
  }, [executeExecpeg, getExecpegCallbacks, getExecpegStatus])

  const remove = useCallback(async (_id: string) => {
    return {
      ok: false,
      unsupported: true,
      message: '同事 API 文档未提供质检记录删除接口',
    }
  }, [])

  const stats = useCallback(async (project_id: string) => {
    const res = await list(project_id, { limit: '500', offset: '0' })
    const rows = res.data || []
    const total = rows.length
    const pass = rows.filter((row) => row.result === 'pass').length
    const warn = rows.filter((row) => row.result === 'warn').length
    const fail = rows.filter((row) => row.result === 'fail').length
    const pass_rate = total > 0 ? Math.round((pass / total) * 1000) / 10 : 0
    return { total, pass, warn, fail, pass_rate }
  }, [list])

  return { list, submit, remove, stats, loading }
}
