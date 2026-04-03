import { useCallback } from 'react'
import { API_BASE, normalizeApiPayload, type ApiRequestFn } from '../base'

export function useProofSmu(request: ApiRequestFn) {
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
    require_sm2?: boolean
    sm2_signatures?: Array<Record<string, unknown>>
    consensus_values?: Array<Record<string, unknown>>
    allowed_deviation?: number
    allowed_deviation_percent?: number
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

  const tripGenerateDoc = useCallback(async (body: {
    project_uri: string
    boq_item_uri?: string
    smu_id?: string
    subitem_code?: string
    item_name?: string
    unit?: string
    executor_did?: string
    geo_location?: Record<string, unknown>
    anchor_location?: Record<string, unknown>
    norm_rows?: Array<Record<string, unknown>>
    measurements?: Record<string, unknown>
    evidence_hashes?: string[]
    report_template?: string
    verify_base_url?: string
  }) => {
    return request('/api/trip/generate-doc', {
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

  const smuRetryErpnext = useCallback(async (limit = 20) => {
    return request(`/v1/proof/smu/erpnext/retry?limit=${encodeURIComponent(String(limit))}`, {
      method: 'POST',
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

  return {
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJob,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    smuNodeContext,
    smuExecute,
    smuSign,
    tripGenerateDoc,
    smuValidateLogic,
    smuFreeze,
    smuRetryErpnext,
    boqRealtimeStatus,
    projectReadinessCheck,
  }
}
