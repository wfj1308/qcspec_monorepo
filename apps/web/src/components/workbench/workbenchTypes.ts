export type EntityType = 'unit' | 'division' | 'subitem' | string

export interface WorkbenchEntity {
  id: string
  entity_uri: string
  entity_code: string
  entity_name: string
  entity_type: EntityType
  parent_uri?: string | null
  location_chain?: string | null
  chain_id?: string | null
  status?: string | null
}

export interface WorkbenchEntitiesResponse {
  ok: true
  items: WorkbenchEntity[]
  total: number
}

export interface ProcessChainItem {
  chain_id: string
  chain_name: string
  in_progress?: number
  completed?: number
  abnormal?: number
}

export interface ProcessChainsResponse {
  ok: true
  items: ProcessChainItem[]
}

export interface ProcessStepInstance {
  instance_id: string
  status: string
  updated_at?: string
}

export interface ProcessStep {
  step_id: string
  step_name: string
  form_code: string
  latest_instance?: ProcessStepInstance
}

export interface ChainStatusResponse {
  ok: true
  chain_id: string
  component_uri: string
  chain_state: string
  current_step?: string
  complete?: boolean
  steps: ProcessStep[]
}

export interface NormrefFormResponse {
  ok: true
  form: {
    form_code: string
    family?: string
    title?: string
    template?: Record<string, unknown>
    protocol_stub?: Record<string, unknown>
  }
}

export interface InterpretPreviewResponse {
  ok: true
  preview: {
    raw?: Record<string, unknown>
    normalized?: Record<string, unknown>
    derived?: Record<string, unknown>
    gate_check?: Record<string, unknown>
    proof_preview?: Record<string, unknown>
    [key: string]: unknown
  }
}

export interface DraftInstanceResponse {
  ok: true
  instance_id: string
  status: string
  updated_at?: string
}

export interface SubmitDraftResponse {
  ok: true
  instance_id: string
  status: string
  trip_id?: string
  proof_id?: string
}

export interface TripSubmitResponse {
  ok: true
  trip_id: string
  status: string
  proof_id?: string
  next_step?: string
}

export interface TripRecord {
  trip_id: string
  project_id?: string
  component_uri?: string
  trip_role?: string
  status?: string
  proof_id?: string
  created_at?: string
}

export interface TripHistoryResponse {
  ok: true
  items: TripRecord[]
  total: number
}

export interface ProofDetailsResponse {
  ok: true
  proof: {
    proof_id: string
    hash?: string
    signatures?: unknown[]
    snapshots?: unknown[]
    attachments?: unknown[]
    result?: string
    created_at?: string
    [key: string]: unknown
  }
}
