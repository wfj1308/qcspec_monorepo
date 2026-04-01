import { useCallback } from 'react'
import { type ApiRequestFn } from '../base'

export function useProofDocs(request: ApiRequestFn) {
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

  return {
    docAutoClassify,
    docTree,
    docCreateNode,
    docAutoGenerateNodes,
    docSearch,
    docRegister,
  }
}
