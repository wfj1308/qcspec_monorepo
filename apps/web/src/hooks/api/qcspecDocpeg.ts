import { useCallback, useMemo, useState } from 'react'
import { useUIStore, useAuthStore } from '../../store'
import { normalizeApiPayload, type ApiRequestOptions, API_BASE } from './base'

const DOCPEG_API_BASE = String(import.meta.env.VITE_DOCPEG_API_URL || API_BASE || '').replace(/\/+$/, '')
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

export type DocpegSourceMode = 'component' | 'pile' | 'inspection_location' | string

export type ProcessChainCommonQuery = {
  chain_id?: string
  component_uri?: string
  pile_id?: string
  inspection_location?: string
  source_mode?: DocpegSourceMode
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

function buildNormrefV1Base(projectId: string): string {
  return `/api/v1/normref/projects/${projectId}`
}

function buildNormrefLegacyBase(projectId: string): string {
  return `/projects/${projectId}/normref`
}

export function useQCSpecDocPegApi() {
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  const call = useCallback(async <T = unknown>(runner: () => Promise<T>): Promise<T | null> => {
    setLoading(true)
    setError(null)
    try {
      return await runner()
    } catch (e: unknown) {
      const msg = e instanceof DOMException && e.name === 'AbortError'
        ? 'Request timed out. Please retry.'
        : (e instanceof Error ? e.message : 'Request failed')
      setError(msg)
      showToast(`[Error] ${msg}`)
      return null
    } finally {
      setLoading(false)
    }
  }, [showToast])

  const runWithCompat = useCallback(async <T = unknown>(
    primary: () => Promise<T>,
    compat?: () => Promise<T>,
  ): Promise<T | null> => {
    return call(async () => {
      try {
        return await primary()
      } catch (e: unknown) {
        const status = (e as HttpError)?.status
        if (status === 404 && compat) {
          return compat()
        }
        throw e
      }
    })
  }, [call])

  const buildWriteHeaders = useCallback((base?: HeadersInit, actor?: DocpegActorHeaders): Headers => {
    const headers = new Headers(base)
    const role = String(actor?.actor_role || DOCPEG_ACTOR_ROLE || '').trim()
    const name = String(actor?.actor_name || DOCPEG_ACTOR_NAME || '').trim()
    if (role && !headers.has('x-actor-role')) headers.set('x-actor-role', role)
    if (name && !headers.has('x-actor-name')) headers.set('x-actor-name', name)
    return headers
  }, [])

  const postTripWithCompat = useCallback(async (primaryPath: string, compatPath: string, payload: DocpegTripPayload) => {
    return runWithCompat(
      () => requestRaw(primaryPath, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(),
        skipAuthRedirect: true,
      }),
      () => requestRaw(compatPath, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(),
        skipAuthRedirect: true,
      }),
    )
  }, [buildWriteHeaders, requestRaw, runWithCompat])

  const listProjects = useCallback(async (query?: QueryLike) => {
    return call(() => requestRaw(`/projects${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getProject = useCallback(async (projectId: string) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getProcessChainStatus = useCallback(async (projectId: string, query: ProcessChainCommonQuery) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/status${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getProcessChainSummary = useCallback(async (projectId: string, chainId: string, query?: Omit<ProcessChainCommonQuery, 'chain_id'>) => {
    const pid = encodePathSegment(projectId)
    const cid = encodePathSegment(chainId)
    if (!pid || !cid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/${cid}/summary${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getProcessChainItemList = useCallback(async (projectId: string, chainId: string, query?: Omit<ProcessChainCommonQuery, 'chain_id'>) => {
    const pid = encodePathSegment(projectId)
    const cid = encodePathSegment(chainId)
    if (!pid || !cid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/${cid}/list${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getProcessChainList = useCallback(async (projectId: string, query?: QueryLike) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/list${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getProcessChainRecommend = useCallback(async (projectId: string, query?: ProcessChainCommonQuery) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/recommend${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getProcessChainDependencies = useCallback(async (projectId: string, query?: Pick<ProcessChainCommonQuery, 'chain_id'> & QueryLike) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/dependencies${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const previewTrip = useCallback(async (payload: DocpegTripPayload) => {
    return postTripWithCompat('/api/v1/trips/preview', '/trips/preview', payload)
  }, [postTripWithCompat])

  const submitTrip = useCallback(async (payload: DocpegTripPayload) => {
    return postTripWithCompat('/api/v1/trips/submit', '/trips/submit', payload)
  }, [postTripWithCompat])

  const getBindings = useCallback(async (projectId: string, query?: QueryLike) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/bindings${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const saveBinding = useCallback(async (
    projectId: string,
    payload: { entity_uri: string; chain_id: string; [key: string]: unknown },
    actor?: DocpegActorHeaders,
  ) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/bindings`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      headers: buildWriteHeaders(undefined, actor),
      skipAuthRedirect: true,
    }))
  }, [buildWriteHeaders, call, requestRaw])

  const getBindingByEntity = useCallback(async (projectId: string, entityUri: string) => {
    const pid = encodePathSegment(projectId)
    const uri = String(entityUri || '').trim()
    if (!pid || !uri) return null
    return call(() => requestRaw(`/projects/${pid}/process-chains/bindings/by-entity${buildQuery({ entity_uri: uri })}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const listNormrefForms = useCallback(async (projectId: string) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return runWithCompat(
      () => requestRaw(`${buildNormrefV1Base(pid)}/forms`, { skipAuthRedirect: true }),
      () => requestRaw(`${buildNormrefLegacyBase(pid)}/forms`, { skipAuthRedirect: true }),
    )
  }, [requestRaw, runWithCompat])

  const getNormrefForm = useCallback(async (projectId: string, formCode: string) => {
    const pid = encodePathSegment(projectId)
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return runWithCompat(
      () => requestRaw(`${buildNormrefV1Base(pid)}/forms/${code}`, { skipAuthRedirect: true }),
      () => requestRaw(`${buildNormrefLegacyBase(pid)}/forms/${code}`, { skipAuthRedirect: true }),
    )
  }, [requestRaw, runWithCompat])

  const interpretPreview = useCallback(async (
    projectId: string,
    formCode: string,
    payload: Record<string, unknown>,
    actor?: DocpegActorHeaders,
  ) => {
    const pid = encodePathSegment(projectId)
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return runWithCompat(
      () => requestRaw(`${buildNormrefV1Base(pid)}/forms/${code}/interpret-preview`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(undefined, actor),
        skipAuthRedirect: true,
      }),
      () => requestRaw(`${buildNormrefLegacyBase(pid)}/forms/${code}/interpret-preview`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(undefined, actor),
        skipAuthRedirect: true,
      }),
    )
  }, [buildWriteHeaders, requestRaw, runWithCompat])

  const saveDraftInstance = useCallback(async (
    projectId: string,
    formCode: string,
    payload: Record<string, unknown>,
    actor?: DocpegActorHeaders,
  ) => {
    const pid = encodePathSegment(projectId)
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return runWithCompat(
      () => requestRaw(`${buildNormrefV1Base(pid)}/forms/${code}/draft-instances`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(undefined, actor),
        skipAuthRedirect: true,
      }),
      () => requestRaw(`${buildNormrefLegacyBase(pid)}/forms/${code}/draft-instances`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(undefined, actor),
        skipAuthRedirect: true,
      }),
    )
  }, [buildWriteHeaders, requestRaw, runWithCompat])

  const getLatestDraftInstance = useCallback(async (projectId: string, formCode: string) => {
    const pid = encodePathSegment(projectId)
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return runWithCompat(
      () => requestRaw(`${buildNormrefV1Base(pid)}/forms/${code}/draft-instances/latest`, { skipAuthRedirect: true }),
      () => requestRaw(`${buildNormrefLegacyBase(pid)}/forms/${code}/draft-instances/latest`, { skipAuthRedirect: true }),
    )
  }, [requestRaw, runWithCompat])

  const submitDraftInstance = useCallback(async (
    projectId: string,
    formCode: string,
    instanceId: string,
    payload: Record<string, unknown> = {},
    actor?: DocpegActorHeaders,
  ) => {
    const pid = encodePathSegment(projectId)
    const code = encodePathSegment(formCode)
    const iid = encodePathSegment(instanceId)
    if (!pid || !code || !iid) return null
    return runWithCompat(
      () => requestRaw(`${buildNormrefV1Base(pid)}/forms/${code}/draft-instances/${iid}/submit`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(undefined, actor),
        skipAuthRedirect: true,
      }),
      () => requestRaw(`${buildNormrefLegacyBase(pid)}/forms/${code}/draft-instances/${iid}/submit`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
        headers: buildWriteHeaders(undefined, actor),
        skipAuthRedirect: true,
      }),
    )
  }, [buildWriteHeaders, requestRaw, runWithCompat])

  const getLatestSubmitted = useCallback(async (projectId: string, formCode: string) => {
    const pid = encodePathSegment(projectId)
    const code = encodePathSegment(formCode)
    if (!pid || !code) return null
    return runWithCompat(
      () => requestRaw(`${buildNormrefV1Base(pid)}/forms/${code}/latest-submitted`, { skipAuthRedirect: true }),
      () => requestRaw(`${buildNormrefLegacyBase(pid)}/forms/${code}/latest-submitted`, { skipAuthRedirect: true }),
    )
  }, [requestRaw, runWithCompat])

  const listTripRoleTrips = useCallback(async (projectId: string, query?: QueryLike) => {
    const pid = String(projectId || '').trim()
    if (!pid) return null
    const mergedQuery = { project_id: pid, ...(query || {}) }
    return call(() => requestRaw(`/api/v1/triprole/trips${buildQuery(mergedQuery)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const previewTripRole = useCallback(async (payload: Record<string, unknown>, actor?: DocpegActorHeaders) => {
    return call(() => requestRaw('/api/v1/triprole/preview', {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      headers: buildWriteHeaders(undefined, actor),
      skipAuthRedirect: true,
    }))
  }, [buildWriteHeaders, call, requestRaw])

  const submitTripRole = useCallback(async (payload: Record<string, unknown>, actor?: DocpegActorHeaders) => {
    return call(() => requestRaw('/api/v1/triprole/submit', {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      headers: buildWriteHeaders(undefined, actor),
      skipAuthRedirect: true,
    }))
  }, [buildWriteHeaders, call, requestRaw])

  const checkDtoPermission = useCallback(async (query: QueryLike) => {
    const merged = { ...query }
    if (!merged.actor_role && DOCPEG_ACTOR_ROLE) merged.actor_role = DOCPEG_ACTOR_ROLE
    if (!merged.actor_name && DOCPEG_ACTOR_NAME) merged.actor_name = DOCPEG_ACTOR_NAME
    return call(() => requestRaw(`/api/v1/dtorole/permission-check${buildQuery(merged)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getBoqItems = useCallback(async (projectId: string, query?: QueryLike) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/api/v1/boqitem/projects/${pid}/items${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getBoqNodes = useCallback(async (projectId: string, query?: QueryLike) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/api/v1/boqitem/projects/${pid}/nodes${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getBoqUtxos = useCallback(async (projectId: string, query?: QueryLike) => {
    const pid = encodePathSegment(projectId)
    if (!pid) return null
    return call(() => requestRaw(`/api/v1/boqitem/projects/${pid}/utxos${buildQuery(query)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getLayerpegChainStatus = useCallback(async (projectId: string, query?: QueryLike) => {
    const pid = String(projectId || '').trim()
    if (!pid) return null
    const mergedQuery = { project_id: pid, ...(query || {}) }
    return call(() => requestRaw(`/api/v1/layerpeg/chain-status${buildQuery(mergedQuery)}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const createLayerpegAnchor = useCallback(async (
    payload: { project_id: string; entity_uri: string; hash: string; [key: string]: unknown },
    actor?: DocpegActorHeaders,
  ) => {
    return call(() => requestRaw('/api/v1/layerpeg/anchor', {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      headers: buildWriteHeaders(undefined, actor),
      skipAuthRedirect: true,
    }))
  }, [buildWriteHeaders, call, requestRaw])

  const getLayerpegAnchor = useCallback(async (projectId: string, entityUri: string) => {
    const pid = String(projectId || '').trim()
    const uri = String(entityUri || '').trim()
    if (!pid || !uri) return null
    return call(() => requestRaw(`/api/v1/layerpeg/anchor${buildQuery({ project_id: pid, entity_uri: uri })}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getHealth = useCallback(async () => {
    return call(() => requestRaw('/health', { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getOpenApi = useCallback(async () => {
    return call(() => requestRaw('/openapi.json', { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const getDocpegSummary = useCallback(async () => {
    return call(() => requestRaw('/api/v1/docpeg/summary', { skipAuthRedirect: true }))
  }, [call, requestRaw])

  const sign = useCallback(async (payload: SignPegSignPayload, actor?: DocpegActorHeaders) => {
    return call(() => requestRaw('/api/v1/signpeg/sign', {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      headers: buildWriteHeaders(undefined, actor),
      skipAuthRedirect: true,
    }))
  }, [buildWriteHeaders, call, requestRaw])

  const verify = useCallback(async (payload: SignPegVerifyPayload, actor?: DocpegActorHeaders) => {
    return call(() => requestRaw('/api/v1/signpeg/verify', {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      headers: buildWriteHeaders(undefined, actor),
      skipAuthRedirect: true,
    }))
  }, [buildWriteHeaders, call, requestRaw])

  const getSignStatus = useCallback(async (docId: string) => {
    const id = encodePathSegment(docId)
    if (!id) return null
    return call(() => requestRaw(`/api/v1/signpeg/status/${id}`, { skipAuthRedirect: true }))
  }, [call, requestRaw])

  return {
    loading,
    error,
    baseUrl,
    listProjects,
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
    checkDtoPermission,
    getBoqItems,
    getBoqNodes,
    getBoqUtxos,
    getLayerpegChainStatus,
    createLayerpegAnchor,
    getLayerpegAnchor,
    getHealth,
    getOpenApi,
    getDocpegSummary,
    sign,
    verify,
    getSignStatus,
  }
}
