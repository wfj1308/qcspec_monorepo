import { useCallback } from 'react'
import { useRequest } from './base'

export type SignPegRole = 'inspector' | 'recorder' | 'reviewer' | 'constructor' | 'supervisor'

export type SignPegStatusItem = {
  dto_role: string
  trip_role: string
  executor_uri: string
  executor_name: string
  signed_at: string
  sig_data: string
  trip_uri: string
  verified: boolean
}

export type SignPegSignPayload = {
  doc_id: string
  body_hash: string
  executor_uri: string
  dto_role: SignPegRole
  trip_role: string
  action: 'approve' | 'reject' | 'submit' | 'sign'
  actor_executor_uri?: string
  delegation_uri?: string
  project_trip_root?: string
}

export type SignPegSignResponse = {
  ok: boolean
  sig_type: string
  sig_data: string
  signed_at: string
  executor_uri: string
  executor_name: string
  dto_role: string
  trip_role: string
  doc_id: string
  body_hash: string
  trip_uri: string
  verified: boolean
  delegation_uri?: string
}

export type SignPegStatusResponse = {
  ok: boolean
  signatures: SignPegStatusItem[]
  all_signed: boolean
  next_required: string
  next_executor: string
  current_slot?: number
  next_slot?: number
  blocked_reason?: string
}

export type ExecutorSkill = {
  skill_uri: string
  skill_name?: string
  level?: number | string
  verified_by?: string
  proof_uri?: string
  cert_no: string
  issued_by: string
  valid_until: string
  scope?: string[]
}

export type ExecutorCertificate = {
  cert_id: string
  cert_type: string
  cert_no: string
  issued_by: string
  issued_date: string
  valid_until: string
  v_uri: string
  status?: 'active' | 'expired' | 'revoked'
  scan_hash?: string
}

export type ExecutorRecordResponse = {
  ok: boolean
  executor: {
    executor_uri: string
    name: string
    org_uri: string
    skills: ExecutorSkill[]
    status: string
    holder_name: string
    holder_id: string
  }
  holder_history: Array<Record<string, unknown>>
}

export type ExecutorRegisterPayload = {
  name: string
  executor_type: 'human' | 'machine' | 'tool' | 'ai' | 'org'
  org_uri: string
  capacity: { current?: number; maximum: number; unit: string }
  energy: { billing_unit: string; rate: number; currency?: string; billing_formula?: string; smu_type?: string }
  certificates?: ExecutorCertificate[]
  skills?: ExecutorSkill[]
  requires?: string[]
  tool_spec?: {
    tool_category: 'consumable' | 'reusable' | 'capability'
    consumable?: {
      sku_uri: string
      initial_qty?: number
      remaining_qty?: number
      unit?: string
      replenish_threshold?: number
    }
    reusable?: {
      purchase_price?: number
      purchase_date?: string
      expected_life?: number
      current_uses?: number
      remaining_uses?: number
      maintenance_cycle?: number
      next_maintenance_at?: number
      depreciation_per_use?: number
    }
    capability?: {
      api_endpoint?: string
      model_version?: string
      quota_total?: number
      quota_used?: number
      quota_remaining?: number
      cost_per_1k_tokens?: number
    }
  }
  org_spec?: {
    org_type?: string
    business_license?: string
    qualification_summary?: Record<string, string>
    branches?: string[]
    branch_count?: number
  }
  business_license_file?: string
  holder_name?: string
  holder_id?: string
  machine_code?: string
  tool_code?: string
  ai_version?: string
}

export type ExecutorListResponse = {
  ok: boolean
  items: Array<{
    executor_id: string
    executor_uri: string
    org_uri: string
    name: string
    executor_type: string
    status: string
    capacity: { current: number; maximum: number; unit: string }
    certificates: ExecutorCertificate[]
    certificates_valid: boolean
  }>
}

export type OrgMembersResponse = {
  ok: boolean
  org_uri: string
  org_name: string
  members: Array<{
    executor_id: string
    executor_uri: string
    name: string
    executor_type: string
    status: string
    role_keys?: string[]
    project_uris?: string[]
  }>
}

export type OrgMemberCreatePayload = {
  name: string
  executor_type?: 'human' | 'machine' | 'tool' | 'ai'
  role_keys?: string[]
  project_uris?: string[]
  capacity?: { current?: number; maximum?: number; unit?: string }
  energy?: { billing_unit?: string; rate?: number; currency?: string; billing_formula?: string; smu_type?: string }
  certificates?: ExecutorCertificate[]
  skills?: ExecutorSkill[]
  requires?: string[]
  tool_spec?: ExecutorRegisterPayload['tool_spec']
  status?: 'active' | 'inactive' | 'suspended' | 'available' | 'busy' | 'offline' | 'in_use' | 'maintenance' | 'depleted' | 'retired'
  holder_name?: string
  holder_id?: string
  machine_code?: string
  tool_code?: string
  ai_version?: string
}

export type OrgMemberUpdatePayload = {
  role_keys?: string[]
  project_uris?: string[]
  status?: 'active' | 'inactive' | 'suspended' | 'available' | 'busy' | 'offline' | 'in_use' | 'maintenance' | 'depleted' | 'retired'
}

export type OrgMemberMutationResponse = {
  ok: boolean
  org_uri: string
  member_executor_uri: string
  role_keys?: string[]
  project_uris?: string[]
  status?: string
  reason?: string
  disable_proof?: string
}

export type OrgBranchesResponse = {
  ok: boolean
  org_uri: string
  org_name: string
  branch_count: number
  branches: string[]
}

export type ExecutorUsePayload = {
  trip_id?: string
  trip_uri?: string
  trip_role?: string
  shifts?: number
  duration_hours?: number
  tokens_used?: number
  consumed_qty?: number
  note?: string
}

export type ToolType = 'consumable' | 'reusable' | 'capability'
export type ToolOwnerType = 'executor' | 'pool' | 'org'

export type ToolCertificate = {
  cert_type: string
  cert_no: string
  valid_until: string
  issued_by?: string
  status?: 'active' | 'expired' | 'revoked'
  scan_hash?: string
}

export type ToolEnergy = {
  energy_type: string
  unit: string
  rate: number
  cost_per_unit: number
  smu_type?: string
}

export type ConsumableSpec = {
  sku_uri: string
  initial_qty: number
  remaining_qty?: number
  unit: string
  replenish_threshold: number
  unit_price?: number
}

export type ReusableSpec = {
  purchase_price: number
  purchase_date?: string
  expected_life: number
  current_uses?: number
  remaining_uses?: number
  maintenance_cycle: number
  next_maintenance_at?: number
  last_maintenance?: string
  depreciation_per_use?: number
}

export type CapabilitySpec = {
  api_endpoint: string
  model_version: string
  quota_total: number
  quota_used?: number
  quota_remaining?: number
  rate_limit?: string
  cost_per_1k_tokens?: number
}

export type ToolRegisterPayload = {
  tool_name: string
  tool_code: string
  tool_type: ToolType
  owner_type: ToolOwnerType
  owner_uri: string
  project_uri?: string
  certificates?: ToolCertificate[]
  tool_energy?: ToolEnergy
  consumable_spec?: ConsumableSpec
  reusable_spec?: ReusableSpec
  capability_spec?: CapabilitySpec
}

export type ToolUsePayload = {
  trip_id?: string
  trip_uri?: string
  trip_role?: string
  shifts?: number
  duration_hours?: number
  tokens_used?: number
  consumed_qty?: number
  note?: string
}

export type ToolListResponse = {
  ok: boolean
  items: Array<{
    tool_id: string
    tool_uri: string
    tool_name: string
    tool_type: ToolType
    status: string
    owner_uri: string
    project_uri: string
    certificates_valid: boolean
    remaining_life?: number | null
    remaining_qty?: number | null
    quota_remaining?: number | null
  }>
}

export type ToolStatusResponse = {
  ok: boolean
  tool_id: string
  tool_uri: string
  status: string
  certificates_valid: boolean
  remaining_life?: number | null
  remaining_qty?: number | null
  quota_remaining?: number | null
  expiring_soon: ToolCertificate[]
}

export type ExplainIssue = {
  field: string
  expected: string
  actual: string
  deviation: string
  norm_ref: string
  severity: 'blocking' | 'warning' | 'info'
  explanation: string
}

export type GateExplainResponse = {
  ok: boolean
  result: {
    passed: boolean
    summary: string
    issues: ExplainIssue[]
    next_steps: string[]
    norm_refs: string[]
    language: 'zh' | 'en'
  }
}

export type ProcessExplainResponse = {
  ok: boolean
  result: {
    step: string
    status: 'locked' | 'active' | 'completed'
    summary: string
    blocking_reasons: Array<{ type: string; description: string; action: string }>
    estimated_unblock: string
    language: 'zh' | 'en'
  }
}

export type FieldValidationResponse = {
  ok: boolean
  result: {
    field: string
    value: unknown
    status: 'ok' | 'warning' | 'blocking'
    message: string
    norm_ref: string
    expected: string
    actual: string
    deviation: string
    language: 'zh' | 'en'
  }
}

export function useSignPegApi() {
  const { request, loading, error } = useRequest()

  const sign = useCallback(async (payload: SignPegSignPayload) => {
    return request('/api/v1/signpeg/sign', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    }) as Promise<SignPegSignResponse | null>
  }, [request])

  const verify = useCallback(async (payload: {
    sig_data: string
    doc_id: string
    body_hash: string
    executor_uri: string
    dto_role: string
    trip_role: string
    signed_at: string
  }) => {
    return request('/api/v1/signpeg/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    })
  }, [request])

  const status = useCallback(async (docId: string) => {
    const id = encodeURIComponent(String(docId || '').trim())
    if (!id) return null
    return request(`/api/v1/signpeg/status/${id}`, {
      skipAuthRedirect: true,
    }) as Promise<SignPegStatusResponse | null>
  }, [request])

  const getExecutor = useCallback(async (executorUri: string) => {
    const uri = encodeURIComponent(String(executorUri || '').trim())
    if (!uri) return null
    return request(`/api/v1/executor/${uri}`, {
      skipAuthRedirect: true,
    }) as Promise<ExecutorRecordResponse | null>
  }, [request])

  const registerExecutor = useCallback(async (payload: ExecutorRegisterPayload) => {
    return request('/api/v1/executors/register', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    })
  }, [request])

  const listExecutors = useCallback(async (orgUri = '') => {
    const query = orgUri ? `?org_uri=${encodeURIComponent(orgUri)}` : ''
    return request(`/api/v1/executors/list${query}`, {
      skipAuthRedirect: true,
    }) as Promise<ExecutorListResponse | null>
  }, [request])

  const searchExecutors = useCallback(async (query: {
    skill_uri?: string
    org_uri?: string
    type?: string
    available?: boolean
  }) => {
    const params = new URLSearchParams()
    if (query.skill_uri) params.set('skill_uri', query.skill_uri)
    if (query.org_uri) params.set('org_uri', query.org_uri)
    if (query.type) params.set('type', query.type)
    if (typeof query.available === 'boolean') params.set('available', String(query.available))
    const suffix = params.toString()
    return request(`/api/v1/executors/search${suffix ? `?${suffix}` : ''}`, {
      skipAuthRedirect: true,
    }) as Promise<ExecutorListResponse | null>
  }, [request])

  const getOrgMembers = useCallback(async (orgUri: string) => {
    const encoded = encodeURIComponent(String(orgUri || '').trim())
    if (!encoded) return null
    return request(`/api/v1/executors/orgs/${encoded}/members`, {
      skipAuthRedirect: true,
    }) as Promise<OrgMembersResponse | null>
  }, [request])

  const getOrgBranches = useCallback(async (orgUri: string) => {
    const encoded = encodeURIComponent(String(orgUri || '').trim())
    if (!encoded) return null
    return request(`/api/v1/executors/orgs/${encoded}/branches`, {
      skipAuthRedirect: true,
    }) as Promise<OrgBranchesResponse | null>
  }, [request])

  const addOrgMember = useCallback(async (orgUri: string, memberExecutorUri: string) => {
    const encoded = encodeURIComponent(String(orgUri || '').trim())
    if (!encoded) return null
    return request(`/api/v1/executors/orgs/${encoded}/members/add`, {
      method: 'POST',
      body: JSON.stringify({ member_executor_uri: memberExecutorUri }),
      skipAuthRedirect: true,
    })
  }, [request])

  const createOrgMember = useCallback(async (orgUri: string, payload: OrgMemberCreatePayload) => {
    const encoded = encodeURIComponent(String(orgUri || '').trim())
    if (!encoded) return null
    return request(`/api/v1/executors/orgs/${encoded}/members/create`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }) as Promise<OrgMemberMutationResponse | null>
  }, [request])

  const updateOrgMember = useCallback(async (orgUri: string, memberExecutorUri: string, payload: OrgMemberUpdatePayload) => {
    const encodedOrg = encodeURIComponent(String(orgUri || '').trim())
    const encodedMember = encodeURIComponent(String(memberExecutorUri || '').trim())
    if (!encodedOrg || !encodedMember) return null
    return request(`/api/v1/executors/orgs/${encodedOrg}/members/${encodedMember}`, {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    }) as Promise<OrgMemberMutationResponse | null>
  }, [request])

  const disableOrgMember = useCallback(async (orgUri: string, memberExecutorUri: string, reason = 'disabled_by_org_admin') => {
    const encodedOrg = encodeURIComponent(String(orgUri || '').trim())
    const encodedMember = encodeURIComponent(String(memberExecutorUri || '').trim())
    if (!encodedOrg || !encodedMember) return null
    return request(`/api/v1/executors/orgs/${encodedOrg}/members/${encodedMember}/disable`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
      skipAuthRedirect: true,
    }) as Promise<OrgMemberMutationResponse | null>
  }, [request])

  const addOrgProject = useCallback(async (orgUri: string, projectUri: string) => {
    const encoded = encodeURIComponent(String(orgUri || '').trim())
    if (!encoded) return null
    return request(`/api/v1/executors/orgs/${encoded}/projects/add`, {
      method: 'POST',
      body: JSON.stringify({ project_uri: projectUri }),
      skipAuthRedirect: true,
    })
  }, [request])

  const addExecutorRequires = useCallback(async (executorId: string, toolExecutorUris: string[]) => {
    const id = encodeURIComponent(String(executorId || '').trim())
    if (!id) return null
    return request(`/api/v1/executors/${id}/requires/add`, {
      method: 'POST',
      body: JSON.stringify({ tool_executor_uris: toolExecutorUris || [] }),
      skipAuthRedirect: true,
    })
  }, [request])

  const useExecutor = useCallback(async (executorId: string, payload: ExecutorUsePayload) => {
    const id = encodeURIComponent(String(executorId || '').trim())
    if (!id) return null
    return request(`/api/v1/executors/${id}/use`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    })
  }, [request])

  const maintainExecutor = useCallback(async (executorId: string, payload: { note?: string; performed_at?: string }) => {
    const id = encodeURIComponent(String(executorId || '').trim())
    if (!id) return null
    return request(`/api/v1/executors/${id}/maintain`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    })
  }, [request])

  const registerTool = useCallback(async (payload: ToolRegisterPayload) => {
    return request('/api/v1/tools/register', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    })
  }, [request])

  const listTools = useCallback(async (query?: {
    project_uri?: string
    owner_uri?: string
    tool_type?: string
    status?: string
  }) => {
    const params = new URLSearchParams()
    if (query?.project_uri) params.set('project_uri', query.project_uri)
    if (query?.owner_uri) params.set('owner_uri', query.owner_uri)
    if (query?.tool_type) params.set('tool_type', query.tool_type)
    if (query?.status) params.set('status', query.status)
    const suffix = params.toString()
    return request(`/api/v1/tools/list${suffix ? `?${suffix}` : ''}`, {
      skipAuthRedirect: true,
    }) as Promise<ToolListResponse | null>
  }, [request])

  const getTool = useCallback(async (toolId: string) => {
    const id = encodeURIComponent(String(toolId || '').trim())
    if (!id) return null
    return request(`/api/v1/tools/${id}`, {
      skipAuthRedirect: true,
    })
  }, [request])

  const getToolStatus = useCallback(async (toolId: string) => {
    const id = encodeURIComponent(String(toolId || '').trim())
    if (!id) return null
    return request(`/api/v1/tools/${id}/status`, {
      skipAuthRedirect: true,
    }) as Promise<ToolStatusResponse | null>
  }, [request])

  const useTool = useCallback(async (toolId: string, payload: ToolUsePayload) => {
    const id = encodeURIComponent(String(toolId || '').trim())
    if (!id) return null
    return request(`/api/v1/tools/${id}/use`, {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuthRedirect: true,
    })
  }, [request])

  const maintainTool = useCallback(async (toolId: string, payload: { note?: string; performed_at?: string }) => {
    const id = encodeURIComponent(String(toolId || '').trim())
    if (!id) return null
    return request(`/api/v1/tools/${id}/maintain`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    })
  }, [request])

  const retireTool = useCallback(async (toolId: string, payload: { reason?: string }) => {
    const id = encodeURIComponent(String(toolId || '').trim())
    if (!id) return null
    return request(`/api/v1/tools/${id}/retire`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
      skipAuthRedirect: true,
    })
  }, [request])

  const explainGate = useCallback(async (payload: {
    form_code: string
    gate_result: Record<string, unknown>
    norm_context?: Record<string, unknown>
    language?: 'zh' | 'en'
  }) => {
    return request('/api/v1/explain/gate', {
      method: 'POST',
      body: JSON.stringify({
        form_code: payload.form_code,
        gate_result: payload.gate_result || {},
        norm_context: payload.norm_context || {},
        language: payload.language || 'zh',
      }),
      skipAuthRedirect: true,
    }) as Promise<GateExplainResponse | null>
  }, [request])

  const explainProcess = useCallback(async (payload: {
    project_uri: string
    component_uri: string
    step_id: string
    current_status: 'locked' | 'active' | 'completed'
    chain_snapshot?: Record<string, unknown>
    language?: 'zh' | 'en'
  }) => {
    return request('/api/v1/explain/process', {
      method: 'POST',
      body: JSON.stringify({
        ...payload,
        language: payload.language || 'zh',
      }),
      skipAuthRedirect: true,
    }) as Promise<ProcessExplainResponse | null>
  }, [request])

  const validateFieldRealtime = useCallback(async (payload: {
    form_code: string
    field_key: string
    value: unknown
    context?: Record<string, unknown>
    language?: 'zh' | 'en'
  }) => {
    return request('/api/v1/explain/field-validate', {
      method: 'POST',
      body: JSON.stringify({
        ...payload,
        context: payload.context || {},
        language: payload.language || 'zh',
      }),
      skipAuthRedirect: true,
    }) as Promise<FieldValidationResponse | null>
  }, [request])

  return {
    loading,
    error,
    sign,
    verify,
    status,
    getExecutor,
    registerExecutor,
    listExecutors,
    searchExecutors,
    getOrgMembers,
    getOrgBranches,
    addOrgMember,
    createOrgMember,
    updateOrgMember,
    disableOrgMember,
    addOrgProject,
    addExecutorRequires,
    useExecutor,
    maintainExecutor,
    registerTool,
    listTools,
    getTool,
    getToolStatus,
    useTool,
    maintainTool,
    retireTool,
    explainGate,
    explainProcess,
    validateFieldRealtime,
  }
}
