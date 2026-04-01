import { useCallback } from 'react'
import { useRequest } from './base'

export function useInspections() {
  const { request, loading } = useRequest()

  const list = useCallback(async (
    project_id: string,
    params: Record<string, string> = {},
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
