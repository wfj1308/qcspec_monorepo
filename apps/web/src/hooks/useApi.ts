/**
 * QCSpec · API Hooks
 * apps/web/src/hooks/useApi.ts
 */

import { useState, useCallback } from 'react'
import { useUIStore } from '../store'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ── 通用请求 ──
export function useRequest<T = unknown>() {
  const [data,    setData]    = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)
  const { showToast } = useUIStore()

  const request = useCallback(async (
    path:    string,
    options: RequestInit = {}
  ): Promise<T | null> => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const json = await res.json()
      setData(json)
      return json
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败'
      setError(msg)
      showToast(`⚠️ ${msg}`)
      return null
    } finally {
      setLoading(false)
    }
  }, [showToast])

  return { data, loading, error, request }
}

// ── 项目 Hooks ──
export function useProjects() {
  const { request, loading } = useRequest()
  const { showToast } = useUIStore()

  const list = useCallback(async (enterprise_id: string) => {
    return request(`/v1/projects/?enterprise_id=${enterprise_id}`)
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

  const listActivity = useCallback(async (enterprise_id: string, limit = 20) => {
    return request(`/v1/projects/activity?enterprise_id=${enterprise_id}&limit=${limit}`)
  }, [request])

  const exportCsv = useCallback(async (enterprise_id: string) => {
    try {
      const res = await fetch(`${API_BASE}/v1/projects/export?enterprise_id=${enterprise_id}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      return blob
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '导出失败'
      showToast(`⚠️ ${msg}`)
      return null
    }
  }, [showToast])

  return { list, create, update, stats, remove, listActivity, exportCsv, loading }
}

// ── 质检 Hooks ──
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

  return { list, submit, remove, loading }
}

// ── 照片 Hooks ──
export function usePhotos() {
  const [uploading, setUploading] = useState(false)
  const { showToast } = useUIStore()

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
      })
      if (!res.ok) throw new Error(`上传失败 HTTP ${res.status}`)
      const data = await res.json()
      showToast(`✅ 照片已上传·Proof: ${data.proof_id}`)
      return data
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '上传失败'
      showToast(`⚠️ ${msg}`)
      return null
    } finally {
      setUploading(false)
    }
  }, [showToast])

  const list = useCallback(async (
    project_id: string,
    inspection_id?: string
  ) => {
    const qs = new URLSearchParams({ project_id,
      ...(inspection_id ? { inspection_id } : {})
    }).toString()
    const res = await fetch(`${API_BASE}/v1/photos/?${qs}`)
    return res.ok ? res.json() : null
  }, [])

  return { upload, list, uploading }
}

// ── 报告 Hooks ──
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

  return { generate, list, loading }
}

// ── Proof Hooks ──
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

  return { listProofs, verify, stats, loading }
}

// 鈹€鈹€ Team Hooks 鈹€鈹€
export function useTeam() {
  const { request, loading } = useRequest()

  const listMembers = useCallback(async (enterprise_id: string) => {
    return request(`/v1/team/members?enterprise_id=${enterprise_id}`)
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

// 鈹€鈹€ Settings Hooks 鈹€鈹€
export function useSettings() {
  const { request, loading } = useRequest()
  const { showToast } = useUIStore()

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

  const uploadTemplate = useCallback(async (enterprise_id: string, file: File) => {
    try {
      const form = new FormData()
      form.append('enterprise_id', enterprise_id)
      form.append('file', file)
      const res = await fetch(`${API_BASE}/v1/settings/template/upload`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      return await res.json()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '模板上传失败'
      showToast(`⚠️ ${msg}`)
      return null
    }
  }, [showToast])

  return { getSettings, saveSettings, uploadTemplate, loading }
}
