/**
 * QCSpec API Hooks
 * apps/web/src/hooks/useApi.ts
 */

import { useState, useCallback } from 'react'
import { useAuthStore, useUIStore } from '../store'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
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
    const { timeoutMs: timeoutOverrideMs, ...fetchOptions } = options
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
          if (shouldHandleAsSessionExpired) {
            logout()
            throw new Error('Login expired. Please sign in again.')
          }
          if (shouldHandleAuthMeServerError) {
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
    })
  }, [request])

  const me = useCallback(async (options: ApiRequestOptions = {}) => {
    return request('/v1/auth/me', options)
  }, [request])

  const getEnterprise = useCallback(async (enterprise_id: string, options: ApiRequestOptions = {}) => {
    return request(`/v1/auth/enterprise/${enterprise_id}`, options)
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

  return { list, create, update, stats, getById, remove, syncAutoreg, listActivity, exportCsv, loading }
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

  const list = useCallback(async (project_id: string) => {
    return request(`/v1/reports/?project_id=${project_id}`)
  }, [request])

  const getById = useCallback(async (report_id: string) => {
    return request(`/v1/reports/${report_id}`)
  }, [request])

  return { generate, list, getById, loading }
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

  return { listProofs, verify, stats, nodeTree, loading }
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
    erpnextSync?: boolean
    erpnextUrl?: string
    erpnextSiteName?: string
    erpnextApiKey?: string
    erpnextApiSecret?: string
    erpnextProjectDoctype?: string
    erpnextProjectLookupField?: string
    erpnextProjectLookupValue?: string
    erpnextGitpegProjectUriField?: string
    erpnextGitpegSiteUriField?: string
    erpnextGitpegStatusField?: string
    erpnextGitpegResultJsonField?: string
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

  return { getSettings, saveSettings, testErpnext, uploadTemplate, loading }
}
