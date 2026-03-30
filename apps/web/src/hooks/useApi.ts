/**
 * QCSpec API Hooks
 * apps/web/src/hooks/useApi.ts
 */

import { useState, useCallback } from 'react'
import { useAuthStore, useUIStore } from '../store'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 30000)
const inflightGetRequests = new Map<string, Promise<unknown>>()

const utf8Decoder = typeof TextDecoder !== 'undefined' ? new TextDecoder('utf-8', { fatal: true }) : null

function looksLikeMojibake(input: string): boolean {
  if (!input || /[\u4e00-\u9fff]/.test(input)) return false
  let latinExtended = 0
  for (const ch of input) {
    const code = ch.charCodeAt(0)
    if (code >= 0x00c0 && code <= 0x00ff) latinExtended += 1
  }
  return latinExtended >= 2
}

function decodeLatin1Utf8(input: string): string {
  if (!utf8Decoder || !looksLikeMojibake(input)) return input
  const bytes = new Uint8Array(Array.from(input, (ch) => ch.charCodeAt(0) & 0xff))
  try {
    const decoded = utf8Decoder.decode(bytes)
    return /[\u4e00-\u9fff]/.test(decoded) ? decoded : input
  } catch {
    return input
  }
}

function normalizeApiPayload<T>(value: T): T {
  if (typeof value === 'string') {
    return decodeLatin1Utf8(value) as T
  }
  if (Array.isArray(value)) {
    return value.map((item) => normalizeApiPayload(item)) as T
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    const repaired: Record<string, unknown> = {}
    for (const [key, val] of entries) {
      repaired[key] = normalizeApiPayload(val)
    }
    return repaired as T
  }
  return value
}

function withAuthHeaders(token: string | null, base?: HeadersInit) {
  const headers = new Headers(base)
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

type ApiRequestOptions = RequestInit & {
  timeoutMs?: number
  skipAuthRedirect?: boolean
}

// Request Hook
export function useRequest<T = unknown>() {
  const [data,    setData]    = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const request = useCallback(async (
    path:    string,
    options: ApiRequestOptions = {}
  ): Promise<T | null> => {
    const { timeoutMs: timeoutOverrideMs, skipAuthRedirect, ...fetchOptions } = options
    const method = String(fetchOptions.method || 'GET').toUpperCase()
    const dedupeKey = `${method}:${path}:${token || ''}`
    const canDedupe = method === 'GET' && !fetchOptions.signal
    if (canDedupe) {
      const inFlight = inflightGetRequests.get(dedupeKey) as Promise<T | null> | undefined
      if (inFlight) return inFlight
    }

    const run = (async (): Promise<T | null> => {
      setLoading(true)
      setError(null)
      const controller = new AbortController()
      const timeoutMs = Number(timeoutOverrideMs || DEFAULT_TIMEOUT_MS)
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

      if (fetchOptions.signal) {
        if (fetchOptions.signal.aborted) controller.abort()
        else fetchOptions.signal.addEventListener('abort', () => controller.abort(), { once: true })
      }

      try {
        const headers = withAuthHeaders(token, fetchOptions.headers)
        const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData
        if (!headers.has('Content-Type') && !isFormData) {
          headers.set('Content-Type', 'application/json')
        }
        const res = await fetch(`${API_BASE}${path}`, {
          headers,
          ...fetchOptions,
          signal: controller.signal,
        })
        if (!res.ok) {
          const isAuthMeRequest = path.startsWith('/v1/auth/me')
          const shouldHandleAsSessionExpired =
            (res.status === 401 || res.status === 403) &&
            !!token &&
            !path.startsWith('/v1/auth/login') &&
            !path.startsWith('/v1/auth/register-enterprise')
          const shouldHandleAuthMeServerError =
            res.status >= 500 &&
            !!token &&
            isAuthMeRequest
          if (shouldHandleAsSessionExpired && !skipAuthRedirect) {
            logout()
            throw new Error('Login expired. Please sign in again.')
          }
          if (shouldHandleAuthMeServerError && !skipAuthRedirect) {
            logout()
            throw new Error('Session invalid. Please sign in again.')
          }
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${res.status}`)
        }
        const json = await res.json()
        const normalized = normalizeApiPayload(json)
        setData(normalized)
        return normalized
      } catch (e: unknown) {
        // Component unmount / effect cleanup aborts should be silent.
        if (fetchOptions.signal?.aborted) {
          return null
        }
        const msg = e instanceof DOMException && e.name === 'AbortError'
          ? 'Request timed out. Please retry.'
          : (e instanceof Error ? e.message : 'Request failed')
        setError(msg)
        showToast(`[Error] ${msg}`)
        return null
      } finally {
        window.clearTimeout(timeoutId)
        setLoading(false)
      }
    })()

    if (canDedupe) {
      inflightGetRequests.set(dedupeKey, run as Promise<unknown>)
      run.finally(() => {
        inflightGetRequests.delete(dedupeKey)
      })
    }

    return run
  }, [showToast, token, logout])

  return { data, loading, error, request }
}

// Auth Hooks
export function useAuthApi() {
  const { request, loading } = useRequest()

  const login = useCallback(async (body: { email: string; password: string }) => {
    return request('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
      timeoutMs: 8000,
    })
  }, [request])

  const me = useCallback(async (options: ApiRequestOptions = {}) => {
    return request('/v1/auth/me', options)
  }, [request])

  const getEnterprise = useCallback(async (enterprise_id: string, options: ApiRequestOptions = {}) => {
    return request(`/v1/auth/enterprise/${enterprise_id}`, { timeoutMs: 8000, ...options })
  }, [request])

  const logout = useCallback(async () => {
    return request('/v1/auth/logout', {
      method: 'POST',
    })
  }, [request])

  const registerEnterprise = useCallback(async (body: {
    name: string
    adminPhone: string
    password: string
    creditCode?: string
    adminEmail?: string
    adminName?: string
  }) => {
    return request('/v1/auth/register-enterprise', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  return { login, me, getEnterprise, logout, registerEnterprise, loading }
}

// Projects Hooks
export function useProjects() {
  const { request, loading } = useRequest()
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const list = useCallback(async (
    enterprise_id: string,
    params: { status?: string; type?: string } = {}
  ) => {
    const qs = new URLSearchParams({
      enterprise_id,
      ...(params.status ? { status: params.status } : {}),
      ...(params.type ? { type: params.type } : {}),
    }).toString()
    return request(`/v1/projects/?${qs}`)
  }, [request])

  const create = useCallback(async (body: Record<string, unknown>) => {
    return request('/v1/projects/', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const stats = useCallback(async (project_id: string) => {
    return request(`/v1/inspections/stats/${project_id}`)
  }, [request])

  const getById = useCallback(async (project_id: string) => {
    return request(`/v1/projects/${project_id}`)
  }, [request])

  const update = useCallback(async (project_id: string, body: Record<string, unknown>) => {
    return request(`/v1/projects/${project_id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }, [request])

  const remove = useCallback(async (project_id: string, enterprise_id?: string) => {
    const qs = enterprise_id ? `?enterprise_id=${enterprise_id}` : ''
    return request(`/v1/projects/${project_id}${qs}`, { method: 'DELETE' })
  }, [request])

  const syncAutoreg = useCallback(async (
    project_id: string,
    body: { enterprise_id?: string; force?: boolean; writeback?: boolean } = {}
  ) => {
    return request(`/v1/projects/${project_id}/autoreg-sync`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const completeGitpeg = useCallback(async (
    project_id: string,
    body: {
      code: string
      registration_id?: string
      session_id?: string
      enterprise_id?: string
    }
  ) => {
    return request(`/v1/projects/${project_id}/gitpeg/complete`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const listActivity = useCallback(async (enterprise_id: string, limit = 20) => {
    return request(`/v1/projects/activity?enterprise_id=${enterprise_id}&limit=${limit}`)
  }, [request])

  const exportCsv = useCallback(async (
    enterprise_id: string,
    params: { status?: string; type?: string } = {}
  ) => {
    try {
      const qs = new URLSearchParams({
        enterprise_id,
        ...(params.status ? { status: params.status } : {}),
        ...(params.type ? { type: params.type } : {}),
      }).toString()
      const res = await fetch(`${API_BASE}/v1/projects/export?${qs}`, {
        headers: withAuthHeaders(token),
      })
      if (res.status === 401 || res.status === 403) {
        logout()
        throw new Error('Login expired. Please sign in again.')
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      return blob
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Export failed'
      showToast(`[Error] ${msg}`)
      return null
    }
  }, [showToast, token, logout])

  return { list, create, update, stats, getById, remove, syncAutoreg, completeGitpeg, listActivity, exportCsv, loading }
}

// Inspections Hooks
export function useInspections() {
  const { request, loading } = useRequest()

  const list = useCallback(async (
    project_id: string,
    params: Record<string, string> = {}
  ) => {
    const qs = new URLSearchParams({ project_id, ...params }).toString()
    return request(`/v1/inspections/?${qs}`)
  }, [request])

  const submit = useCallback(async (body: Record<string, unknown>) => {
    return request('/v1/inspections/', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const remove = useCallback(async (id: string) => {
    return request(`/v1/inspections/${id}`, { method: 'DELETE' })
  }, [request])

  const stats = useCallback(async (project_id: string) => {
    return request(`/v1/inspections/stats/${project_id}`)
  }, [request])

  return { list, submit, remove, stats, loading }
}

// Photos Hooks
export function usePhotos() {
  const [uploading, setUploading] = useState(false)
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const upload = useCallback(async (params: {
    file:          File
    project_id:    string
    enterprise_id: string
    location?:     string
    inspection_id?: string
    gps_lat?:      number
    gps_lng?:      number
  }) => {
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file',          params.file)
      form.append('project_id',    params.project_id)
      form.append('enterprise_id', params.enterprise_id)
      if (params.location)      form.append('location',      params.location)
      if (params.inspection_id) form.append('inspection_id', params.inspection_id)
      if (params.gps_lat != null) form.append('gps_lat',     String(params.gps_lat))
      if (params.gps_lng != null) form.append('gps_lng',     String(params.gps_lng))

      const res = await fetch(`${API_BASE}/v1/photos/upload`, {
        method: 'POST',
        body: form,
        headers: withAuthHeaders(token),
      })
      if (res.status === 401 || res.status === 403) {
        logout()
        throw new Error('Login expired. Please sign in again.')
      }
      if (!res.ok) throw new Error(`Upload failed HTTP ${res.status}`)
      const data = await res.json()
      showToast(`Uploaded photo. Proof: ${data.proof_id}`)
      return data
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Upload failed'
      showToast(`[Error] ${msg}`)
      return null
    } finally {
      setUploading(false)
    }
  }, [showToast, token, logout])

  const list = useCallback(async (
    project_id: string,
    inspection_id?: string
  ) => {
    const qs = new URLSearchParams({ project_id,
      ...(inspection_id ? { inspection_id } : {})
    }).toString()
    const res = await fetch(`${API_BASE}/v1/photos/?${qs}`, {
      headers: withAuthHeaders(token),
    })
    if (res.status === 401 || res.status === 403) {
      logout()
      return null
    }
    return res.ok ? res.json() : null
  }, [token, logout])

  const remove = useCallback(async (photo_id: string) => {
    const res = await fetch(`${API_BASE}/v1/photos/${photo_id}`, {
      method: 'DELETE',
      headers: withAuthHeaders(token),
    })
    if (res.status === 401 || res.status === 403) {
      logout()
      return null
    }
    if (!res.ok) return null
    return res.json()
  }, [token, logout])

  return { upload, list, remove, uploading }
}

// Reports Hooks
export function useReports() {
  const { request, loading } = useRequest()

  const generate = useCallback(async (params: {
    project_id:    string
    enterprise_id: string
    location?:     string
    date_from?:    string
    date_to?:      string
  }) => {
    return request('/v1/reports/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }, [request])

  const exportDocpeg = useCallback(async (params: {
    project_id:    string
    enterprise_id: string
    type?:         'inspection' | 'lab' | 'monthly_summary' | 'final_archive'
    format?:       'docx' | 'pdf'
    location?:     string
    date_from?:    string
    date_to?:      string
  }) => {
    return request('/v1/reports/export', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }, [request])

  const list = useCallback(async (project_id: string) => {
    return request(`/v1/reports/?project_id=${project_id}`)
  }, [request])

  const getById = useCallback(async (report_id: string) => {
    return request(`/v1/reports/${report_id}`)
  }, [request])

  return { generate, exportDocpeg, list, getById, loading }
}

// Proof Hooks
export function useProof() {
  const { request, loading } = useRequest()

  const listProofs = useCallback(async (project_id: string) => {
    return request(`/v1/proof/?project_id=${project_id}`)
  }, [request])

  const verify = useCallback(async (proof_id: string) => {
    return request(`/v1/proof/verify/${proof_id}`)
  }, [request])

  const stats = useCallback(async (project_id: string) => {
    return request(`/v1/proof/stats/${project_id}`)
  }, [request])

  const nodeTree = useCallback(async (root_uri: string) => {
    return request(`/v1/proof/node-tree?root_uri=${encodeURIComponent(root_uri)}`)
  }, [request])

  const docAutoClassify = useCallback(async (body: {
    file_name: string
    text_excerpt?: string
    mime_type?: string
  }) => {
    return request('/v1/proof/docs/auto-classify', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const docTree = useCallback(async (project_uri: string, root_uri = '') => {
    const qs = new URLSearchParams({
      project_uri,
      ...(root_uri ? { root_uri } : {}),
    }).toString()
    return request(`/v1/proof/docs/tree?${qs}`)
  }, [request])

  const docCreateNode = useCallback(async (body: {
    project_uri: string
    parent_uri?: string
    node_name: string
    executor_uri?: string
    metadata?: Record<string, unknown>
  }) => {
    return request('/v1/proof/docs/node/create', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const docAutoGenerateNodes = useCallback(async (body: {
    project_uri: string
    parent_uri?: string
    start_km: number
    end_km: number
    step_km?: number
    leaf_name?: string
    executor_uri?: string
  }) => {
    return request('/v1/proof/docs/node/auto-generate', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const docSearch = useCallback(async (body: {
    project_uri: string
    node_uri?: string
    include_descendants?: boolean
    query?: string
    tags?: string[]
    field_filters?: Record<string, unknown>
    limit?: number
  }) => {
    return request('/v1/proof/docs/search', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const docRegister = useCallback(async (params: {
    file: File
    project_uri: string
    source_utxo_id: string
    node_uri?: string
    executor_uri?: string
    text_excerpt?: string
    tags?: string[]
    custom_metadata?: Record<string, unknown>
    ai_metadata?: Record<string, unknown>
    auto_classify?: boolean
  }) => {
    const form = new FormData()
    form.append('file', params.file)
    form.append('project_uri', params.project_uri)
    form.append('source_utxo_id', params.source_utxo_id)
    if (params.node_uri) form.append('node_uri', params.node_uri)
    if (params.executor_uri) form.append('executor_uri', params.executor_uri)
    if (params.text_excerpt) form.append('text_excerpt', params.text_excerpt)
    if (params.tags?.length) form.append('tags', JSON.stringify(params.tags))
    if (params.custom_metadata) form.append('custom_metadata', JSON.stringify(params.custom_metadata))
    if (params.ai_metadata) form.append('ai_metadata', JSON.stringify(params.ai_metadata))
    form.append('auto_classify', String(params.auto_classify !== false))

    return request('/v1/proof/docs/register', {
      method: 'POST',
      body: form,
      timeoutMs: 90000,
    })
  }, [request])

  const smuImportGenesis = useCallback(async (params: {
    file: File
    project_uri: string
    project_id?: string
    boq_root_uri?: string
    norm_context_root_uri?: string
    owner_uri?: string
    commit?: boolean
  }) => {
    const form = new FormData()
    form.append('file', params.file)
    form.append('project_uri', params.project_uri)
    if (params.project_id) form.append('project_id', params.project_id)
    if (params.boq_root_uri) form.append('boq_root_uri', params.boq_root_uri)
    if (params.norm_context_root_uri) form.append('norm_context_root_uri', params.norm_context_root_uri)
    if (params.owner_uri) form.append('owner_uri', params.owner_uri)
    form.append('commit', String(params.commit !== false))

    return request('/v1/proof/smu/genesis/import', {
      method: 'POST',
      body: form,
      // Sync fallback is for legacy environments; large BOQ imports can exceed 45s.
      timeoutMs: 10 * 60 * 1000,
    })
  }, [request])

  const smuImportGenesisAsync = useCallback(async (params: {
    file: File
    project_uri: string
    project_id?: string
    boq_root_uri?: string
    norm_context_root_uri?: string
    owner_uri?: string
    commit?: boolean
  }) => {
    const form = new FormData()
    form.append('file', params.file)
    form.append('project_uri', params.project_uri)
    if (params.project_id) form.append('project_id', params.project_id)
    if (params.boq_root_uri) form.append('boq_root_uri', params.boq_root_uri)
    if (params.norm_context_root_uri) form.append('norm_context_root_uri', params.norm_context_root_uri)
    if (params.owner_uri) form.append('owner_uri', params.owner_uri)
    form.append('commit', String(params.commit !== false))

    return request('/v1/proof/smu/genesis/import-async', {
      method: 'POST',
      body: form,
      timeoutMs: 12000,
    })
  }, [request])

  const smuImportGenesisPreview = useCallback(async (params: {
    file: File
    project_uri: string
    project_id?: string
    boq_root_uri?: string
    norm_context_root_uri?: string
    owner_uri?: string
  }) => {
    const form = new FormData()
    form.append('file', params.file)
    form.append('project_uri', params.project_uri)
    if (params.project_id) form.append('project_id', params.project_id)
    if (params.boq_root_uri) form.append('boq_root_uri', params.boq_root_uri)
    if (params.norm_context_root_uri) form.append('norm_context_root_uri', params.norm_context_root_uri)
    if (params.owner_uri) form.append('owner_uri', params.owner_uri)

    return request('/v1/proof/smu/genesis/preview', {
      method: 'POST',
      body: form,
      timeoutMs: 12000,
      skipAuthRedirect: true,
    })
  }, [request])

  const smuImportGenesisJob = useCallback(async (job_id: string) => {
    return request(`/v1/proof/smu/genesis/import-job/${encodeURIComponent(job_id)}`, {
      timeoutMs: 12000,
    })
  }, [request])

  const smuImportGenesisJobPublic = useCallback(async (job_id: string) => {
    const id = encodeURIComponent(String(job_id || '').trim())
    if (!id) return null
    try {
      const res = await fetch(`${API_BASE}/v1/proof/smu/genesis/import-job-public/${id}`, {
        method: 'GET',
      })
      if (!res.ok) return null
      const json = await res.json()
      return normalizeApiPayload(json)
    } catch {
      return null
    }
  }, [])

  const smuImportGenesisJobActivePublic = useCallback(async (project_uri: string) => {
    const uri = String(project_uri || '').trim()
    if (!uri) return null
    try {
      const qs = new URLSearchParams({ project_uri: uri }).toString()
      const res = await fetch(`${API_BASE}/v1/proof/smu/genesis/import-job-active-public?${qs}`, {
        method: 'GET',
      })
      if (!res.ok) return null
      const json = await res.json()
      return normalizeApiPayload(json)
    } catch {
      return null
    }
  }, [])

  const smuNodeContext = useCallback(async (query: {
    project_uri: string
    boq_item_uri: string
    component_type?: string
    measured_value?: number
  }) => {
    const qs = new URLSearchParams({
      project_uri: query.project_uri,
      boq_item_uri: query.boq_item_uri,
      component_type: query.component_type || 'generic',
      ...(typeof query.measured_value === 'number' ? { measured_value: String(query.measured_value) } : {}),
    }).toString()
    return request(`/v1/proof/smu/node/context?${qs}`, { skipAuthRedirect: true })
  }, [request])

  const smuExecute = useCallback(async (body: {
    project_uri: string
    input_proof_id: string
    executor_uri?: string
    executor_did?: string
    executor_role?: string
    component_type?: string
    measurement?: Record<string, unknown>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
    evidence_hashes?: string[]
    credentials_vc?: Array<Record<string, unknown>>
    force_reject?: boolean
  }) => {
    return request('/v1/proof/smu/execute', {
      method: 'POST',
      body: JSON.stringify(body),
      skipAuthRedirect: true,
    })
  }, [request])

  const smuSign = useCallback(async (body: {
    input_proof_id: string
    boq_item_uri: string
    supervisor_executor_uri?: string
    supervisor_did: string
    contractor_did: string
    owner_did: string
    signer_metadata?: Record<string, unknown>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
    auto_docpeg?: boolean
    verify_base_url?: string
    template_path?: string
  }) => {
    return request('/v1/proof/smu/sign', {
      method: 'POST',
      body: JSON.stringify(body),
      skipAuthRedirect: true,
    })
  }, [request])

  const smuValidateLogic = useCallback(async (body: {
    project_uri: string
    smu_id: string
  }) => {
    return request('/v1/proof/smu/validate-logic', {
      method: 'POST',
      body: JSON.stringify(body),
      skipAuthRedirect: true,
    })
  }, [request])

  const smuFreeze = useCallback(async (body: {
    project_uri: string
    smu_id: string
    executor_uri?: string
    min_risk_score?: number
  }) => {
    return request('/v1/proof/smu/freeze', {
      method: 'POST',
      body: JSON.stringify(body),
      skipAuthRedirect: true,
    })
  }, [request])

  const boqRealtimeStatus = useCallback(async (project_uri: string) => {
    return request(`/v1/proof/boq/realtime-status?project_uri=${encodeURIComponent(project_uri)}`, {
      skipAuthRedirect: true,
    })
  }, [request])

  const projectReadinessCheck = useCallback(async (project_uri: string) => {
    return request(`/v1/proof/project-readiness-check?project_uri=${encodeURIComponent(project_uri)}`, {
      skipAuthRedirect: true,
    })
  }, [request])

  const boqItemSovereignHistory = useCallback(async (query: {
    project_uri: string
    subitem_code: string
    max_rows?: number
  }) => {
    const p = new URLSearchParams({
      project_uri: query.project_uri,
      subitem_code: query.subitem_code,
      ...(typeof query.max_rows === 'number' ? { max_rows: String(query.max_rows) } : {}),
    }).toString()
    return request(`/v1/proof/boq/item-sovereign-history?${p}`)
  }, [request])

  const boqReconciliation = useCallback(async (query: {
    project_uri: string
    subitem_code?: string
    max_rows?: number
    limit_items?: number
  }) => {
    const p = new URLSearchParams({
      project_uri: query.project_uri,
      ...(query.subitem_code ? { subitem_code: query.subitem_code } : {}),
      ...(typeof query.max_rows === 'number' ? { max_rows: String(query.max_rows) } : {}),
      ...(typeof query.limit_items === 'number' ? { limit_items: String(query.limit_items) } : {}),
    }).toString()
    return request(`/v1/proof/boq/reconciliation?${p}`)
  }, [request])

  const docFinalContext = useCallback(async (boq_item_uri: string) => {
    return request(`/v1/proof/docfinal/context?boq_item_uri=${encodeURIComponent(boq_item_uri)}`)
  }, [request])

  const getGateEditorPayload = useCallback(async (project_uri: string, subitem_code: string) => {
    const qs = new URLSearchParams({
      project_uri,
    }).toString()
    return request(`/v1/proof/gate-editor/${encodeURIComponent(subitem_code)}?${qs}`)
  }, [request])

  const importGateRulesFromNorm = useCallback(async (body: {
    spec_uri: string
    context?: string
  }) => {
    return request('/v1/proof/gate-editor/import-norm', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const generateGateRulesViaAi = useCallback(async (body: {
    prompt: string
    subitem_code?: string
  }) => {
    return request('/v1/proof/gate-editor/generate-via-ai', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const saveGateRuleVersion = useCallback(async (body: {
    project_uri: string
    subitem_code: string
    gate_id_base?: string
    rules: Array<Record<string, unknown>>
    execution_strategy?: string
    fail_action?: string
    apply_to_similar?: boolean
    executor_uri?: string
    metadata?: Record<string, unknown>
  }) => {
    return request('/v1/proof/gate-editor/save', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const rollbackGateRuleVersion = useCallback(async (body: {
    project_uri: string
    subitem_code: string
    target_proof_id?: string
    target_version?: string
    apply_to_similar?: boolean
    executor_uri?: string
  }) => {
    return request('/v1/proof/gate-editor/rollback', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const getSpecDict = useCallback(async (spec_dict_key: string) => {
    return request(`/v1/proof/spec-dict/${encodeURIComponent(spec_dict_key)}`)
  }, [request])

  const saveSpecDict = useCallback(async (body: {
    spec_dict_key: string
    title?: string
    version?: string
    authority?: string
    spec_uri?: string
    items: Record<string, unknown>
    metadata?: Record<string, unknown>
    is_active?: boolean
  }) => {
    return request('/v1/proof/spec-dict/save', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const resolveSpecDictThreshold = useCallback(async (gate_id: string, context = '') => {
    const qs = new URLSearchParams({ gate_id, context }).toString()
    return request(`/v1/proof/spec-dict-resolve-threshold?${qs}`)
  }, [request])

  const exportDocFinal = useCallback(async (body: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/docfinal/export`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      rootHash: res.headers.get('X-DocFinal-Root-Hash') || '',
      proofId: res.headers.get('X-DocFinal-Proof-Id') || '',
      gitpegAnchor: res.headers.get('X-DocFinal-GitPeg-Anchor') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'MASTER-DSP.qcdsp',
    }
  }, [])

  const finalizeDocFinal = useCallback(async (body: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/docfinal/finalize`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      rootHash: res.headers.get('X-DocFinal-Root-Hash') || '',
      proofId: res.headers.get('X-DocFinal-Proof-Id') || '',
      gitpegAnchor: res.headers.get('X-DocFinal-GitPeg-Anchor') || '',
      finalGitpegAnchor: res.headers.get('X-DocFinal-Final-GitPeg-Anchor') || '',
      anchorRuns: Number(res.headers.get('X-DocFinal-Anchor-Runs') || 0),
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'MASTER-DSP.qcdsp',
    }
  }, [])

  const generatePaymentCertificate = useCallback(async (body: {
    project_uri: string
    period: string
    project_name?: string
    verify_base_url?: string
    create_proof?: boolean
    executor_uri?: string
    enforce_dual_pass?: boolean
  }) => {
    return request('/v1/proof/payment/certificate/generate', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const paymentAuditTrace = useCallback(async (payment_id: string) => {
    return request(`/v1/proof/payment/audit-trace/${encodeURIComponent(payment_id)}`)
  }, [request])

  const recordLabTest = useCallback(async (body: {
    project_uri: string
    boq_item_uri: string
    sample_id: string
    jtg_form_code?: string
    instrument_sn?: string
    tested_at?: string
    witness_record?: Record<string, unknown>
    sample_tracking?: Record<string, unknown>
    metrics?: Array<Record<string, unknown>>
    result?: string
    executor_uri?: string
    metadata?: Record<string, unknown>
  }) => {
    return request('/v1/proof/lab/record', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const calcInspectionFrequency = useCallback(async (body: {
    boq_item_uri: string
    project_uri?: string
  }) => {
    return request('/v1/proof/frequency/calc', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const frequencyDashboard = useCallback(async (project_uri: string, limit_items = 200) => {
    const qs = new URLSearchParams({
      project_uri,
      limit_items: String(limit_items),
    }).toString()
    return request(`/v1/proof/frequency/dashboard?${qs}`)
  }, [request])

  const openRemediation = useCallback(async (body: {
    fail_proof_id: string
    notice?: string
    due_date?: string
    assignees?: string[]
    executor_uri?: string
  }) => {
    return request('/v1/proof/remediation/open', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const remediationReinspect = useCallback(async (body: {
    remediation_proof_id: string
    result: string
    payload?: Record<string, unknown>
    executor_uri?: string
  }) => {
    return request('/v1/proof/remediation/reinspect', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const closeRemediation = useCallback(async (body: {
    remediation_proof_id: string
    reinspection_proof_id: string
    close_note?: string
    executor_uri?: string
  }) => {
    return request('/v1/proof/remediation/close', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const generateRailPactInstruction = useCallback(async (body: {
    payment_id: string
    executor_uri?: string
    auto_submit?: boolean
  }) => {
    return request('/v1/proof/payment/railpact/instruction', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const bindSpatialUtxo = useCallback(async (body: {
    utxo_id: string
    project_uri?: string
    bim_id?: string
    label?: string
    coordinate?: Record<string, unknown>
    metadata?: Record<string, unknown>
  }) => {
    return request('/v1/proof/spatial/bind', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const spatialDashboard = useCallback(async (project_uri: string, limit = 5000) => {
    return request(`/v1/proof/spatial/dashboard?project_uri=${encodeURIComponent(project_uri)}&limit=${encodeURIComponent(String(limit))}`)
  }, [request])

  const predictiveQualityAnalysis = useCallback(async (body: {
    project_uri: string
    near_threshold_ratio?: number
    min_samples?: number
    apply_dynamic_gate?: boolean
    default_critical_threshold?: number
  }) => {
    return request('/v1/proof/ai/predictive-quality', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const exportFinanceProof = useCallback(async (body: {
    payment_id: string
    bank_code?: string
    passphrase?: string
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/finance/proof/export`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      paymentId: res.headers.get('X-Finance-Payment-Id') || '',
      proofId: res.headers.get('X-Finance-Proof-Id') || '',
      payloadHash: res.headers.get('X-Finance-Payload-Hash') || '',
      gitpegAnchor: res.headers.get('X-Finance-GitPeg-Anchor') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'FINANCE-PROOF.qcfp',
    }
  }, [])

  const applyVariationDelta = useCallback(async (body: {
    boq_item_uri: string
    delta_amount: number
    reason?: string
    project_uri?: string
    executor_uri?: string
    executor_did?: string
    executor_role?: string
    metadata?: Record<string, unknown>
    credentials_vc?: Array<Record<string, unknown>>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
  }) => {
    return request('/v1/proof/triprole/apply-variation', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const replayOfflinePackets = useCallback(async (body: {
    packets: Array<Record<string, unknown>>
    stop_on_error?: boolean
    default_executor_uri?: string
    default_executor_role?: string
  }) => {
    return request('/v1/proof/triprole/offline/replay', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const scanConfirmSignature = useCallback(async (body: {
    input_proof_id: string
    scan_payload: string
    scanner_did: string
    scanner_role?: string
    executor_uri?: string
    executor_role?: string
    signature_hash?: string
    signer_metadata?: Record<string, unknown>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
  }) => {
    return request('/v1/proof/triprole/scan-confirm', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const ingestSensorData = useCallback(async (body: {
    device_id: string
    raw_payload: unknown
    boq_item_uri: string
    project_uri?: string
    executor_uri?: string
    executor_did?: string
    executor_role?: string
    metadata?: Record<string, unknown>
    credentials_vc?: Array<Record<string, unknown>>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
  }) => {
    return request('/v1/proof/triprole/hardware/ingest', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const unitMerkleRoot = useCallback(async (query: {
    project_uri: string
    unit_code?: string
    proof_id?: string
    max_rows?: number
  }) => {
    const p = new URLSearchParams()
    p.set('project_uri', query.project_uri)
    if (query.unit_code) p.set('unit_code', query.unit_code)
    if (query.proof_id) p.set('proof_id', query.proof_id)
    if (typeof query.max_rows === 'number') p.set('max_rows', String(query.max_rows))
    return request(`/v1/proof/unit/merkle-root?${p.toString()}`)
  }, [request])

  const convertRwaAsset = useCallback(async (body: {
    project_uri: string
    boq_group_id: string
    project_name?: string
    bank_code?: string
    passphrase?: string
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/rwa/convert`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      projectUri: res.headers.get('X-RWA-Project-Uri') || '',
      groupId: res.headers.get('X-RWA-Group-Id') || '',
      proofId: res.headers.get('X-RWA-Proof-Id') || '',
      certificateHash: res.headers.get('X-RWA-Certificate-Hash') || '',
      gitpegAnchor: res.headers.get('X-RWA-GitPeg-Anchor') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'RWA-ASSET.qcrwa',
    }
  }, [])

  const exportOmHandoverBundle = useCallback(async (body: {
    project_uri: string
    project_name?: string
    om_owner_uri?: string
    passphrase?: string
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/om/handover/export`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      omRootUri: res.headers.get('X-OM-Root-Uri') || '',
      omRootProofId: res.headers.get('X-OM-Root-Proof-Id') || '',
      omGitpegAnchor: res.headers.get('X-OM-GitPeg-Anchor') || '',
      payloadHash: res.headers.get('X-OM-Payload-Hash') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'OM-HANDOVER.zip',
    }
  }, [])

  const registerOmEvent = useCallback(async (body: {
    om_root_proof_id: string
    title: string
    event_type?: string
    payload?: Record<string, unknown>
    executor_uri?: string
  }) => {
    return request('/v1/proof/om/event/register', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const generateNormEvolutionReport = useCallback(async (body: {
    project_uris?: string[]
    min_samples?: number
    near_threshold_ratio?: number
    anonymize?: boolean
    create_proof?: boolean
  }) => {
    return request('/v1/proof/norm/evolution/report', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  return {
    listProofs,
    verify,
    stats,
    nodeTree,
    docAutoClassify,
    docTree,
    docCreateNode,
    docAutoGenerateNodes,
    docSearch,
    docRegister,
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJob,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    smuNodeContext,
    smuExecute,
    smuSign,
    smuValidateLogic,
    smuFreeze,
    boqRealtimeStatus,
    projectReadinessCheck,
    boqItemSovereignHistory,
    boqReconciliation,
    docFinalContext,
    getGateEditorPayload,
    importGateRulesFromNorm,
    generateGateRulesViaAi,
    saveGateRuleVersion,
    rollbackGateRuleVersion,
    getSpecDict,
    saveSpecDict,
    resolveSpecDictThreshold,
    exportDocFinal,
    finalizeDocFinal,
    generatePaymentCertificate,
    paymentAuditTrace,
    recordLabTest,
    calcInspectionFrequency,
    frequencyDashboard,
    openRemediation,
    remediationReinspect,
    closeRemediation,
    generateRailPactInstruction,
    bindSpatialUtxo,
    spatialDashboard,
    predictiveQualityAnalysis,
    exportFinanceProof,
    applyVariationDelta,
    replayOfflinePackets,
    scanConfirmSignature,
    ingestSensorData,
    unitMerkleRoot,
    convertRwaAsset,
    exportOmHandoverBundle,
    registerOmEvent,
    generateNormEvolutionReport,
    loading,
  }
}

// Team Hooks
export function useTeam() {
  const { request, loading } = useRequest()

  const listMembers = useCallback(async (
    enterprise_id: string,
    include_inactive = false
  ) => {
    const qs = new URLSearchParams({
      enterprise_id,
      include_inactive: String(include_inactive),
    }).toString()
    return request(`/v1/team/members?${qs}`)
  }, [request])

  const inviteMember = useCallback(async (body: {
    enterprise_id: string
    name: string
    email: string
    dto_role: string
    title?: string
    project_ids?: string[]
  }) => {
    return request('/v1/team/members', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const updateMember = useCallback(async (user_id: string, body: {
    name?: string
    email?: string
    dto_role?: string
    title?: string
    project_ids?: string[]
    is_active?: boolean
  }) => {
    return request(`/v1/team/members/${user_id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }, [request])

  const removeMember = useCallback(async (user_id: string) => {
    return request(`/v1/team/members/${user_id}`, { method: 'DELETE' })
  }, [request])

  return { listMembers, inviteMember, updateMember, removeMember, loading }
}

// AutoRegister Hooks
export function useAutoreg() {
  const { request, loading } = useRequest()

  const registerProject = useCallback(async (body: {
    project_code?: string
    project_name: string
    site_code?: string
    site_name?: string
    namespace_uri?: string
    source_system?: string
    executor_code?: string
    executor_name?: string
    endpoint?: string
    norm_refs?: string[]
  }) => {
    return request('/v1/autoreg/project', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const registerProjectAlias = useCallback(async (body: {
    project_code?: string
    project_name: string
    site_code?: string
    site_name?: string
    namespace_uri?: string
    source_system?: string
    executor_code?: string
    executor_name?: string
    endpoint?: string
    norm_refs?: string[]
  }) => {
    return request('/v1/gitpeg/autoreg/project', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const listProjects = useCallback(async (limit = 100) => {
    return request(`/v1/autoreg/projects?limit=${limit}`)
  }, [request])

  return { registerProject, registerProjectAlias, listProjects, loading }
}

// ERPNext Hooks
export function useErpnext() {
  const { request, loading } = useRequest()

  const gateCheck = useCallback(async (params: {
    enterprise_id: string
    project_id?: string
    project_code?: string
    stake: string
    subitem: string
    result: 'pass' | 'warn' | 'fail'
  }) => {
    const qs = new URLSearchParams({
      enterprise_id: params.enterprise_id,
      ...(params.project_id ? { project_id: params.project_id } : {}),
      ...(params.project_code ? { project_code: params.project_code } : {}),
      stake: params.stake,
      subitem: params.subitem,
      result: params.result,
    }).toString()
    return request(`/v1/erpnext/gate-check?${qs}`)
  }, [request])

  const getMeteringRequests = useCallback(async (params: {
    enterprise_id: string
    project_code?: string
    stake?: string
    subitem?: string
    status?: string
  }) => {
    const qs = new URLSearchParams({
      enterprise_id: params.enterprise_id,
      ...(params.project_code ? { project_code: params.project_code } : {}),
      ...(params.stake ? { stake: params.stake } : {}),
      ...(params.subitem ? { subitem: params.subitem } : {}),
      ...(params.status ? { status: params.status } : {}),
    }).toString()
    return request(`/v1/erpnext/metering-requests?${qs}`)
  }, [request])

  const getProjectBasics = useCallback(async (params: {
    enterprise_id: string
    project_code?: string
    project_name?: string
  }) => {
    const qs = new URLSearchParams({
      enterprise_id: params.enterprise_id,
      ...(params.project_code ? { project_code: params.project_code } : {}),
      ...(params.project_name ? { project_name: params.project_name } : {}),
    }).toString()
    return request(`/v1/erpnext/project-basics?${qs}`)
  }, [request])

  return { gateCheck, getMeteringRequests, getProjectBasics, loading }
}

// Settings Hooks
export function useSettings() {
  const { request, loading } = useRequest()
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const getSettings = useCallback(async (enterprise_id: string) => {
    return request(`/v1/settings/?enterprise_id=${enterprise_id}`)
  }, [request])

  const saveSettings = useCallback(async (enterprise_id: string, body: {
    enterpriseName?: string
    enterpriseVUri?: string
    enterpriseCreditCode?: string
    emailNotify?: boolean
    wechatNotify?: boolean
    autoGenerateReport?: boolean
    strictProof?: boolean
    reportTemplate?: string
    reportHeader?: string
    webhookUrl?: string
    gitpegToken?: string
    gitpegEnabled?: boolean
    gitpegRegistrarBaseUrl?: string
    gitpegPartnerCode?: string
    gitpegIndustryCode?: string
    gitpegClientId?: string
    gitpegClientSecret?: string
    gitpegRegistrationMode?: string
    gitpegReturnUrl?: string
    gitpegWebhookUrl?: string
    gitpegWebhookSecret?: string
    gitpegModuleCandidates?: string[]
    erpnextSync?: boolean
    erpnextUrl?: string
    erpnextSiteName?: string
    erpnextApiKey?: string
    erpnextApiSecret?: string
    erpnextUsername?: string
    erpnextPassword?: string
    erpnextProjectDoctype?: string
    erpnextProjectLookupField?: string
    erpnextProjectLookupValue?: string
    erpnextGitpegProjectUriField?: string
    erpnextGitpegSiteUriField?: string
    erpnextGitpegStatusField?: string
    erpnextGitpegResultJsonField?: string
    erpnextGitpegRegistrationIdField?: string
    erpnextGitpegNodeUriField?: string
    erpnextGitpegShellUriField?: string
    erpnextGitpegProofHashField?: string
    erpnextGitpegIndustryProfileIdField?: string
    wechatMiniapp?: boolean
    droneImport?: boolean
    permissionMatrix?: Array<{
      role: string
      view: boolean
      input: boolean
      approve: boolean
      manage: boolean
      settle: boolean
      regulator: boolean
    }>
  }) => {
    return request(`/v1/settings/?enterprise_id=${enterprise_id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }, [request])

  const testErpnext = useCallback(async (body: {
    url: string
    siteName?: string
    apiKey?: string
    apiSecret?: string
    username?: string
    password?: string
    timeoutMs?: number
  }) => {
    return request('/v1/settings/erpnext/test', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const testGitpegRegistrar = useCallback(async (body: {
    baseUrl: string
    partnerCode: string
    industryCode: string
    clientId?: string
    clientSecret?: string
    registrationMode?: string
    returnUrl?: string
    webhookUrl?: string
    moduleCandidates?: string[]
    timeoutMs?: number
  }) => {
    return request('/v1/settings/gitpeg/test', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const uploadTemplate = useCallback(async (enterprise_id: string, file: File) => {
    try {
      const form = new FormData()
      form.append('enterprise_id', enterprise_id)
      form.append('file', file)
      const res = await fetch(`${API_BASE}/v1/settings/template/upload`, {
        method: 'POST',
        body: form,
        headers: withAuthHeaders(token),
      })
      if (res.status === 401 || res.status === 403) {
        logout()
        throw new Error('Login expired. Please sign in again.')
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      return await res.json()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Template upload failed'
      showToast(`[Error] ${msg}`)
      return null
    }
  }, [showToast, token, logout])

  return { getSettings, saveSettings, testErpnext, testGitpegRegistrar, uploadTemplate, loading }
}
