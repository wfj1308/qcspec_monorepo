import { useCallback } from 'react'
import { useAuthStore, useUIStore } from '../../store'
import { API_BASE, useRequest, withAuthHeaders } from './base'

export function useProjects() {
  const { request, loading } = useRequest()
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const list = useCallback(async (
    enterprise_id: string,
    params: { status?: string; type?: string } = {},
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
    body: { enterprise_id?: string; force?: boolean; writeback?: boolean } = {},
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
    },
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
    params: { status?: string; type?: string } = {},
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
      if (res.status === 401) {
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
