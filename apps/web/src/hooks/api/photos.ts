import { useCallback, useState } from 'react'
import { useAuthStore, useUIStore } from '../../store'
import { API_BASE, withAuthHeaders } from './base'

export function usePhotos() {
  const [uploading, setUploading] = useState(false)
  const { showToast } = useUIStore()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)

  const upload = useCallback(async (params: {
    file: File
    project_id: string
    enterprise_id: string
    location?: string
    inspection_id?: string
    gps_lat?: number
    gps_lng?: number
  }) => {
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', params.file)
      form.append('project_id', params.project_id)
      form.append('enterprise_id', params.enterprise_id)
      if (params.location) form.append('location', params.location)
      if (params.inspection_id) form.append('inspection_id', params.inspection_id)
      if (params.gps_lat != null) form.append('gps_lat', String(params.gps_lat))
      if (params.gps_lng != null) form.append('gps_lng', String(params.gps_lng))

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
    inspection_id?: string,
  ) => {
    const qs = new URLSearchParams({
      project_id,
      ...(inspection_id ? { inspection_id } : {}),
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
