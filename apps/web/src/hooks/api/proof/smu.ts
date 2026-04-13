import { useCallback } from 'react'
import { type ApiRequestFn } from '../base'

type SmuGenesisImportParams = {
  file: File
  project_uri: string
  project_id?: string
  boq_root_uri?: string
  norm_context_root_uri?: string
  owner_uri?: string
  commit?: boolean
}

type SmuGenesisPreviewParams = Omit<SmuGenesisImportParams, 'commit'>

const DOCPEG_UNSUPPORTED_PREFIX = 'DocPeg API pack does not expose this capability yet'

function unsupported(feature: string) {
  return {
    ok: false,
    unsupported: true,
    feature,
    message: `${DOCPEG_UNSUPPORTED_PREFIX}: ${feature}`,
  }
}

export function useProofSmu(_request: ApiRequestFn) {

  const smuImportGenesis = useCallback(async (_params: SmuGenesisImportParams) => {
    return unsupported('smuImportGenesis')
  }, [])

  const smuImportGenesisAsync = useCallback(async (_params: SmuGenesisImportParams) => {
    return unsupported('smuImportGenesisAsync')
  }, [])

  const smuImportGenesisPreview = useCallback(async (_params: SmuGenesisPreviewParams) => {
    return unsupported('smuImportGenesisPreview')
  }, [])

  const smuImportGenesisJobPublic = useCallback(async (_job_id: string) => {
    return unsupported('smuImportGenesisJobPublic')
  }, [])

  const smuImportGenesisJobActivePublic = useCallback(async (_project_uri: string) => {
    return unsupported('smuImportGenesisJobActivePublic')
  }, [])

  const smuNodeContext = useCallback(async (_query: {
    project_uri: string
    boq_item_uri: string
    component_type?: string
    measured_value?: number
  }) => {
    return unsupported('smuNodeContext')
  }, [])

  const smuExecute = useCallback(async (_body: {
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
    return unsupported('smuExecute')
  }, [])

  const smuSign = useCallback(async (_body: {
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
    return unsupported('smuSign')
  }, [])

  const tripGenerateDoc = useCallback(async (_body: {
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
    return unsupported('tripGenerateDoc')
  }, [])

  const smuFreeze = useCallback(async (_body: {
    project_uri: string
    smu_id: string
    executor_uri?: string
    min_risk_score?: number
  }) => {
    return unsupported('smuFreeze')
  }, [])

  const smuRetryErpnext = useCallback(async (_limit = 20) => {
    return unsupported('smuRetryErpnext')
  }, [])

  const boqRealtimeStatus = useCallback(async (project_uri: string) => {
    return {
      ok: true,
      project_uri,
      items: [],
      total: 0,
      source: 'docpeg-api-pack',
    }
  }, [])

  const projectReadinessCheck = useCallback(async (project_uri: string) => {
    return {
      ok: true,
      overall_status: 'missing',
      readiness_percent: 0,
      layers: [
        {
          key: 'boq_items',
          name: 'BOQ Items',
          status: 'missing',
          metrics: {
            item_count: 0,
          },
        },
      ],
      source: 'docpeg-api-pack',
    }
  }, [])

  return {
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    smuNodeContext,
    smuExecute,
    smuSign,
    tripGenerateDoc,
    smuFreeze,
    smuRetryErpnext,
    boqRealtimeStatus,
    projectReadinessCheck,
  }
}
