import { useCallback, useMemo, useState } from 'react'
import { useAuthStore, useUIStore } from '../../store'
import { assertDocpegApiPath, normalizeApiPayload, type ApiRequestOptions } from './base'

const DOCPEG_API_BASE = String(import.meta.env.VITE_DOCPEG_API_URL || 'https://api.docpeg.cn').replace(/\/+$/, '')
const DOCPEG_API_KEY = String(import.meta.env.VITE_DOCPEG_API_KEY || '').trim()
const DOCPEG_BEARER_TOKEN = String(import.meta.env.VITE_DOCPEG_BEARER_TOKEN || '').trim()
const DOCPEG_USE_APP_AUTH = String(import.meta.env.VITE_DOCPEG_USE_APP_AUTH || '').trim() === 'true'
const DOCPEG_ACTOR_ROLE = String(import.meta.env.VITE_DOCPEG_ACTOR_ROLE || 'designer').trim()
const DOCPEG_ACTOR_NAME = String(import.meta.env.VITE_DOCPEG_ACTOR_NAME || 'designer-user').trim()
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000)

type QueryLike = Record<string, unknown>

export type DocpegActorHeaders = {
  actor_role?: string
  actor_name?: string
}

export type ProcessChainCommonQuery = {
  chain_id?: string
  component_uri?: string
  pile_id?: string
  inspection_location?: string
  source_mode?: string
}

export type DocpegTripPayload = {
  request_id?: string
  project_id?: string
  chain_id?: string
  component_uri?: string
  pile_id?: string
  inspection_location?: string
  action?: string
  payload?: Record<string, unknown>
  [key: string]: unknown
}

export type DocpegExecpegPayload = {
  tripRoleId?: string
  projectRef?: string
  componentRef?: string
  context?: Record<string, unknown>
  callbackUrl?: string
  [key: string]: unknown
}

export type DocpegEntityPayload = {
  name?: string
  code?: string
  type?: string
  parent_uri?: string
  uri?: string
  [key: string]: unknown
}

export type SignPegSignPayload = {
  doc_id: string
  body_hash: string
  executor_uri: string
  dto_role: string
  trip_role: string
  signed_at?: string
  [key: string]: unknown
}

export type SignPegVerifyPayload = {
  doc_id: string
  body_hash: string
  executor_uri: string
  dto_role: string
  trip_role: string
  signed_at: string
  sig_data: string
  [key: string]: unknown
}

type HttpError = Error & { status?: number }

type CreateProjectPayload = {
  project_id: string
  name: string
  description?: string
  [key: string]: unknown
}

function buildQuery(params?: QueryLike): string {
  if (!params) return ''
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined) return
    const text = String(value).trim()
    if (!text) return
    search.set(key, text)
  })
  const out = search.toString()
  return out ? `?${out}` : ''
}

function trimSlash(input: string): string {
  return String(input || '').replace(/\/+$/, '')
}

function encodePathSegment(input: string): string {
  return encodeURIComponent(String(input || '').trim())
}

export function useQCSpecDocPegApi() {
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const projectPathIdCache = useMemo(() => new Map<string, string>(), [])

  const baseUrl = useMemo(() => trimSlash(DOCPEG_API_BASE), [])

  const requestRaw = useCallback(async <T = unknown>(
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<T> => {
    const { timeoutMs: timeoutOverrideMs, ...fetchOptions } = options
    const controller = new AbortController()
    const timeoutMs = Number(timeoutOverrideMs || DEFAULT_TIMEOUT_MS)
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

    try {
      const headers = new Headers(fetchOptions.headers)
      if (!headers.has('Authorization')) {
        if (DOCPEG_BEARER_TOKEN) {
          headers.set('Authorization', `Bearer ${DOCPEG_BEARER_TOKEN}`)
        } else if (DOCPEG_USE_APP_AUTH && token) {
          headers.set('Authorization', `Bearer ${token}`)
        }
      }
      if (DOCPEG_API_KEY && !headers.has('x-api-key')) {
        headers.set('x-api-key', DOCPEG_API_KEY)
      }

      const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData
      if (!headers.has('Content-Type') && !isFormData) {
        headers.set('Content-Type', 'application/json')
      }

      assertDocpegApiPath(path)
      const response = await fetch(`${baseUrl}${path}`, {
        ...fetchOptions,
        headers,
        signal: controller.signal,
      })

      const data = await response.json().catch(() => ({} as Record<string, unknown>))
      if (!response.ok) {
        const err = new Error(String((data as Record<string, unknown>).detail || `HTTP ${response.status}`)) as HttpError
        err.status = response.status
        throw err
      }
      return normalizeApiPayload(data as T)
    } finally {
      window.clearTimeout(timeoutId)
    }
  }, [baseUrl, token])

  const call = useCallback(async <T = unknown>(
    runner: () => Promise<T>,
    options?: { silent?: boolean; fallback?: T | null },
  ): Promise<T | null> => {
    setLoading(true)
    setError(null)
    try {
      return await runner()
    } catch (e: unknown) {
      const msg = e instanceof DOMException && e.name === 'AbortError'
        ? 'Request timed out. Please retry.'
        : (e instanceof Error ? e.message : 'Request failed')
      if (!options?.silent) {
        setError(msg)
        showToast(`[Error] ${msg}`)
      }
      return options?.fallback ?? null
    } finally {
      setLoading(false)
    }
  }, [showToast])

  const buildWriteHeaders = useCallback((base?: HeadersInit, actor?: DocpegActorHeaders): Headers => {
    const headers = new Headers(base)
    const role = String(actor?.actor_role || DOCPEG_ACTOR_ROLE || '').trim()
    const name = String(actor?.actor_name || DOCPEG_ACTOR_NAME || '').trim()
    if (role && !headers.has('x-actor-role')) headers.set('x-actor-role', role)
    if (name && !headers.has('x-actor-name')) headers.set('x-actor-name', name)
    return headers
  }, [])

  const listProjects = useCallback(async (query?: QueryLike) => {
    return call(() => requestRaw(`/projects${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const createProject = useCallback(async (
    payload: CreateProjectPayload,
    options?: { idempotencyKey?: string; actor?: DocpegActorHeaders },
  ) => {
    const headers = buildWriteHeaders(undefined, options?.actor)
    const idempotencyKey = String(options?.idempotencyKey || '').trim()
    if (idempotencyKey) headers.set('x-idempotency-key', idempotencyKey)
    return call(() => requestRaw('/projects', {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      headers,
      skipAuthRedirect: true,
    }))
  }, [buildWriteHeaders, call, requestRaw])

  const getProject = useCallback(async (projectId: string) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const resolveProjectPathId = useCallback(async (projectId: string) => {
    const raw = String(projectId || '').trim()
    if (!raw) return ''
    const key = raw.toUpperCase()
    const cached = projectPathIdCache.get(key)
    if (cached) return cached

    const payload = await call(() => requestRaw<{
      items?: Array<Record<string, unknown>>
      data?: { items?: Array<Record<string, unknown>> }
    }>(`/projects${buildQuery({ q: raw, limit: 20, offset: 0 })}`, { skipAuthRedirect: true }), {
      silent: true,
      fallback: null,
    })

    const rows = payload?.items || payload?.data?.items || []
    const hit = rows.find((item) => {
      const row = item?.project && typeof item.project === 'object'
        ? { ...item, ...(item.project as Record<string, unknown>) }
        : item
      const candidates = [row.id, row.project_id, row.code]
      return candidates.some((value) => String(value || '').trim().toUpperCase() === key)
    })
    const resolved = String(hit?.id || hit?.project_id || raw).trim() || raw
    projectPathIdCache.set(key, resolved)
    return resolved
  }, [call, projectPathIdCache, requestRaw])

  const getProcessChainStatus = useCallback(async (
    projectId: string,
    query: ProcessChainCommonQuery = {},
  ) => {
    const chainId = encodePathSegment(String(query.chain_id || ''))
    if (!chainId) return null
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/${chainId}/status${buildQuery({
      ...(query.component_uri ? { component_uri: query.component_uri } : {}),
      ...(query.pile_id ? { pile_id: query.pile_id } : {}),
      ...(query.inspection_location ? { inspection_location: query.inspection_location } : {}),
      ...(query.source_mode ? { source_mode: query.source_mode } : {}),
    })}`, { skipAuthRedirect: true }), { silent: true, fallback: null })
  }, [call, requestRaw, resolveProjectPathId])

  const getProcessChainSummary = useCallback(async (
    projectId: string,
    chainId: string,
    query: ProcessChainCommonQuery = {},
  ) => {
    return getProcessChainStatus(projectId, { ...query, chain_id: chainId })
  }, [getProcessChainStatus])

  const getProcessChainItemList = useCallback(async (
    projectId: string,
    chainId: string,
    query: ProcessChainCommonQuery = {},
  ) => {
    const cid = encodePathSegment(chainId)
    if (!cid) return null
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/${cid}/list${buildQuery({
      source_mode: query.source_mode || 'hybrid',
      ...(query.component_uri ? { component_uri: query.component_uri } : {}),
      ...(query.pile_id ? { pile_id: query.pile_id } : {}),
    })}`, { skipAuthRedirect: true }), { silent: true, fallback: { ok: true, items: [] } })
  }, [call, requestRaw, resolveProjectPathId])

  const getProcessChainList = useCallback(async (
    projectId: string,
    query: ProcessChainCommonQuery = {},
  ) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains${buildQuery({
      source_mode: query.source_mode || 'hybrid',
    })}`, { skipAuthRedirect: true }), { silent: true, fallback: { ok: true, items: [] } })
  }, [call, requestRaw, resolveProjectPathId])

  const getProcessChainRecommend = useCallback(async (
    projectId: string,
    query: ProcessChainCommonQuery = {},
  ) => {
    const status = await getProcessChainStatus(projectId, query)
    const row = (status && typeof status === 'object') ? (status as Record<string, unknown>) : {}
    const nextAction = String(
      row.next_action || row.recommend_action || row.action || row.current_step || row.current_step_name || '',
    ).trim()
    if (!nextAction) return { ok: true, next_action: '-', source: 'derived-from-status' }
    return { ok: true, next_action: nextAction, source: 'derived-from-status', status: row }
  }, [getProcessChainStatus])

  const getProcessChainDependencies = useCallback(async (
    projectId: string,
    query: ProcessChainCommonQuery = {},
  ) => {
    const status = await getProcessChainStatus(projectId, query)
    const steps = Array.isArray((status as Record<string, unknown> | null)?.steps)
      ? ((status as Record<string, unknown>).steps as unknown[])
      : []
    return { ok: true, items: steps, source: 'derived-from-status' }
  }, [getProcessChainStatus])

  const previewTrip = useCallback(async (payload: DocpegTripPayload) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/triprole/preview', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const submitTrip = useCallback(async (payload: DocpegTripPayload) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/triprole/submit', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const getBindings = useCallback(async (query?: QueryLike) => {
    return call(() => requestRaw(`/api/v1/dtorole/role-bindings${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: { ok: true, items: [] } })
  }, [call, requestRaw])

  const saveBinding = useCallback(async (payload: QueryLike) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/dtorole/role-bindings', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const getBindingByEntity = useCallback(async (projectId: string, entityUri: string) => {
    const pid = await resolveProjectPathId(projectId)
    return getBindings({
      project_id: pid,
      entity_uri: entityUri,
    })
  }, [getBindings, resolveProjectPathId])

  const listNormrefForms = useCallback(async (projectId: string) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    return call(() => requestRaw(`/api/v1/normref/projects/${pid}/forms`, { skipAuthRedirect: true }), {
      silent: true,
      fallback: { ok: true, items: [] },
    })
  }, [call, requestRaw, resolveProjectPathId])

  const getNormrefForm = useCallback(async (projectId: string, formCode: string) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return call(() => requestRaw(`/api/v1/normref/projects/${pid}/forms/${code}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [call, requestRaw, resolveProjectPathId])

  const interpretPreview = useCallback(async (
    projectId: string,
    formCode: string,
    payload: QueryLike,
  ) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/api/v1/normref/projects/${pid}/forms/${code}/interpret-preview`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const saveDraftInstance = useCallback(async (
    projectId: string,
    formCode: string,
    payload: QueryLike,
  ) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/api/v1/normref/projects/${pid}/forms/${code}/draft-instances`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const getLatestDraftInstance = useCallback(async (
    projectId: string,
    formCode: string,
    query?: QueryLike,
  ) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return call(() => requestRaw(`/api/v1/normref/projects/${pid}/forms/${code}/draft-instances/latest${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [call, requestRaw, resolveProjectPathId])

  const submitDraftInstance = useCallback(async (
    projectId: string,
    formCode: string,
    instanceId: string,
    payload: QueryLike = {},
  ) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const code = encodePathSegment(formCode)
    const iid = encodePathSegment(instanceId)
    if (!pid || !code || !iid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/api/v1/normref/projects/${pid}/forms/${code}/draft-instances/${iid}/submit`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const getLatestSubmitted = useCallback(async (
    projectId: string,
    formCode: string,
    query?: QueryLike,
  ) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return call(() => requestRaw(`/api/v1/normref/projects/${pid}/forms/${code}/latest-submitted${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [call, requestRaw, resolveProjectPathId])

  const listTripRoleTrips = useCallback(async (projectId: string, query: QueryLike = {}) => {
    const pid = await resolveProjectPathId(projectId)
    return call(() => requestRaw(`/api/v1/triprole/trips${buildQuery({
      ...query,
      project_id: pid,
    })}`, { skipAuthRedirect: true }), { silent: true, fallback: { ok: true, items: [], total: 0 } })
  }, [call, requestRaw, resolveProjectPathId])

  const previewTripRole = useCallback(async (payload: QueryLike) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/triprole/preview', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const submitTripRole = useCallback(async (payload: QueryLike) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/triprole/submit', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const executeExecpeg = useCallback(async (
    payload: DocpegExecpegPayload,
    options?: { idempotencyKey?: string; actor?: DocpegActorHeaders },
  ) => {
    const headers = buildWriteHeaders(undefined, options?.actor)
    const idempotencyKey = String(options?.idempotencyKey || '').trim()
    if (idempotencyKey) headers.set('x-idempotency-key', idempotencyKey)
    return call(() => requestRaw('/api/v1/execpeg/execute', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const getExecpegStatus = useCallback(async (execId: string) => {
    const eid = encodePathSegment(execId)
    if (!eid) return null
    return call(() => requestRaw(`/api/v1/execpeg/status/${eid}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [call, requestRaw])

  const getExecpegCallbacks = useCallback(async (execId: string, query: QueryLike = {}) => {
    const eid = encodePathSegment(execId)
    if (!eid) return null
    return call(() => requestRaw(`/api/v1/execpeg/status/${eid}/callbacks${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: { ok: true, items: [], total: 0 } })
  }, [call, requestRaw])

  const patchExecpegManualInput = useCallback(async (payload: QueryLike) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/execpeg/manual-input', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const registerExecpegTemplate = useCallback(async (payload: QueryLike) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/execpeg/register', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const listExecpegHighwaySpus = useCallback(async (query: QueryLike = {}) => {
    return call(() => requestRaw(`/api/v1/execpeg/highway-spus${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: { ok: true, items: [], total: 0 } })
  }, [call, requestRaw])

  const getExecpegHighwaySpu = useCallback(async (spuRef: string) => {
    const encoded = encodePathSegment(spuRef)
    if (!encoded) return null
    return call(() => requestRaw(`/api/v1/execpeg/highway-spus/${encoded}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [call, requestRaw])

  const checkDtoPermission = useCallback(async (query: QueryLike) => {
    return call(() => requestRaw(`/api/v1/dtorole/permission-check${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: { ok: false, allowed: false } })
  }, [call, requestRaw])

  const getBoqItems = useCallback(async (projectId: string, query: QueryLike = {}) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    return call(() => requestRaw(`/api/v1/boqitem/projects/${pid}/items${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: { ok: true, items: [] } })
  }, [call, requestRaw, resolveProjectPathId])

  const getBoqNodes = useCallback(async (projectId: string, query: QueryLike = {}) => {
    return getBoqItems(projectId, query)
  }, [getBoqItems])

  const getBoqUtxos = useCallback(async (_projectId: string, _query: QueryLike = {}) => {
    return { ok: true, items: [] }
  }, [])

  const consumeBoqItem = useCallback(async (projectId: string, payload: QueryLike) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/api/v1/boqitem/projects/${pid}/consume`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const settleBoqItem = useCallback(async (projectId: string, payload: QueryLike) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/api/v1/boqitem/projects/${pid}/settle`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const getLayerpegChainStatus = useCallback(async (projectId: string) => {
    const pid = await resolveProjectPathId(projectId)
    return call(() => requestRaw(`/api/v1/layerpeg/chain-status${buildQuery({ project_id: pid })}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: { ok: true, mode: 'unknown', reason: '' } })
  }, [call, requestRaw, resolveProjectPathId])

  const createLayerpegAnchor = useCallback(async (payload: QueryLike) => {
    const headers = buildWriteHeaders()
    return call(() => requestRaw('/api/v1/layerpeg/anchor', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const getLayerpegAnchor = useCallback(async (projectId: string, entityUri: string) => {
    const pid = await resolveProjectPathId(projectId)
    return call(() => requestRaw(`/api/v1/layerpeg/anchor${buildQuery({
      project_id: pid,
      entity_uri: entityUri,
    })}`, { skipAuthRedirect: true }), { silent: true, fallback: { ok: true, items: [] } })
  }, [call, requestRaw, resolveProjectPathId])

  const getHealth = useCallback(async () => {
    return call(() => requestRaw('/health', { skipAuthRedirect: true }), { silent: true, fallback: null })
  }, [call, requestRaw])

  const getOpenApi = useCallback(async () => {
    return call(() => requestRaw('/openapi.json', { skipAuthRedirect: true }), { silent: true, fallback: null })
  }, [call, requestRaw])

  const getDocpegSummary = useCallback(async () => {
    const health = await getHealth()
    return { ok: !!health, health }
  }, [getHealth])

  const sign = useCallback(async (..._args: unknown[]) => null, [])

  const verify = useCallback(async (proofId: string) => {
    const pid = encodePathSegment(proofId)
    if (!pid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/api/v1/proof/${pid}/verify`, {
      method: 'POST',
      headers,
      body: '{}',
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const getProof = useCallback(async (proofId: string) => {
    const pid = encodePathSegment(proofId)
    if (!pid) return null
    return call(() => requestRaw(`/api/v1/proof/${pid}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [call, requestRaw])

  const addProofAttachment = useCallback(async (proofId: string, payload: QueryLike) => {
    const pid = encodePathSegment(proofId)
    if (!pid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/api/v1/proof/${pid}/attachments`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw])

  const listProjectEntities = useCallback(async (projectId: string, query: QueryLike = {}) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/entities${buildQuery(query)}`, {
      skipAuthRedirect: true,
    }), { silent: true, fallback: { ok: true, items: [], total: 0 } })
  }, [call, requestRaw, resolveProjectPathId])

  const createProjectEntity = useCallback(async (projectId: string, payload: DocpegEntityPayload) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/projects/${pid}/entities`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const patchProjectEntity = useCallback(async (projectId: string, entityId: string, payload: DocpegEntityPayload) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const eid = encodePathSegment(entityId)
    if (!pid || !eid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/projects/${pid}/entities/${eid}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const createProjectDocument = useCallback(async (projectId: string, payload: QueryLike) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    if (!pid) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/projects/${pid}/documents`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const createProjectDocumentVersion = useCallback(async (
    projectId: string,
    documentId: string,
    payload: QueryLike,
  ) => {
    const pid = encodePathSegment(await resolveProjectPathId(projectId))
    const did = encodePathSegment(documentId)
    if (!pid || !did) return null
    const headers = buildWriteHeaders()
    return call(() => requestRaw(`/projects/${pid}/documents/${did}/versions`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }), { silent: true, fallback: null })
  }, [buildWriteHeaders, call, requestRaw, resolveProjectPathId])

  const getSignStatus = useCallback(async (_docId: string) => {
    return {
      ok: true,
      next_required: '-',
      blocked_reason: '-',
      source: 'docpeg-api-pack-placeholder',
    }
  }, [])

  return {
    loading,
    error,
    baseUrl,
    listProjects,
    createProject,
    getProject,
    getProcessChainStatus,
    getProcessChainSummary,
    getProcessChainItemList,
    getProcessChainList,
    getProcessChainRecommend,
    getProcessChainDependencies,
    previewTrip,
    submitTrip,
    getBindings,
    saveBinding,
    getBindingByEntity,
    listNormrefForms,
    getNormrefForm,
    interpretPreview,
    saveDraftInstance,
    getLatestDraftInstance,
    submitDraftInstance,
    getLatestSubmitted,
    listTripRoleTrips,
    previewTripRole,
    submitTripRole,
    executeExecpeg,
    getExecpegStatus,
    getExecpegCallbacks,
    patchExecpegManualInput,
    registerExecpegTemplate,
    listExecpegHighwaySpus,
    getExecpegHighwaySpu,
    checkDtoPermission,
    getBoqItems,
    getBoqNodes,
    getBoqUtxos,
    consumeBoqItem,
    settleBoqItem,
    getLayerpegChainStatus,
    createLayerpegAnchor,
    getLayerpegAnchor,
    getHealth,
    getOpenApi,
    getDocpegSummary,
    sign,
    getProof,
    verify,
    addProofAttachment,
    listProjectEntities,
    createProjectEntity,
    patchProjectEntity,
    createProjectDocument,
    createProjectDocumentVersion,
    getSignStatus,
  }
}
