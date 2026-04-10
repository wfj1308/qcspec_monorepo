import { useCallback } from 'react'
import { useRequest } from './base'

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

  const listProjects = useCallback(async (
    limit = 100,
    filters?: { enterpriseId?: string; namespaceUri?: string }
  ) => {
    const params = new URLSearchParams()
    params.set('limit', String(limit))
    const enterpriseId = String(filters?.enterpriseId || '').trim()
    if (enterpriseId) params.set('enterprise_id', enterpriseId)
    const namespaceUri = String(filters?.namespaceUri || '').trim()
    if (namespaceUri) params.set('namespace_uri', namespaceUri)
    return request(`/v1/autoreg/projects?${params.toString()}`)
  }, [request])

  return { registerProject, registerProjectAlias, listProjects, loading }
}
