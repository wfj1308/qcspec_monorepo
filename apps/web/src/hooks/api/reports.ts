import { useCallback } from 'react'
import { useRequest } from './base'

export function useReports() {
  const { request, loading } = useRequest()

  const generate = useCallback(async (params: {
    project_id: string
    enterprise_id: string
    location?: string
    date_from?: string
    date_to?: string
  }) => {
    return request('/v1/reports/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }, [request])

  const exportDocpeg = useCallback(async (params: {
    project_id: string
    enterprise_id: string
    type?: 'inspection' | 'lab' | 'monthly_summary' | 'final_archive'
    format?: 'docx' | 'pdf'
    location?: string
    date_from?: string
    date_to?: string
  }) => {
    return request('/v1/reports/export', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }, [request])

  const list = useCallback(async (project_id: string) => {
    return request(`/v1/reports/?project_id=${project_id}`, { timeoutMs: 90000 })
  }, [request])

  const getById = useCallback(async (report_id: string) => {
    return request(`/v1/reports/${report_id}`, { timeoutMs: 60000 })
  }, [request])

  return { generate, exportDocpeg, list, getById, loading }
}
