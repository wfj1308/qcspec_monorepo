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

  const listProjects = useCallback(async (limit = 100) => {
    return request(`/v1/autoreg/projects?limit=${limit}`)
  }, [request])

  return { registerProject, registerProjectAlias, listProjects, loading }
}
