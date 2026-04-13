import { useCallback } from 'react'
import { type ApiRequestFn } from '../base'

const DOCPEG_UNSUPPORTED_PREFIX = 'DocPeg API pack does not expose this capability yet'

function unsupported(feature: string, extra: Record<string, unknown> = {}) {
  return {
    ok: false,
    unsupported: true,
    feature,
    message: `${DOCPEG_UNSUPPORTED_PREFIX}: ${feature}`,
    ...extra,
  }
}

export function useProofExecution(_request: ApiRequestFn) {
  const submitTripRole = useCallback(async (payload: Record<string, unknown>) => {
    return {
      ok: false,
      unsupported: true,
      feature: 'submitTripRole',
      message: `${DOCPEG_UNSUPPORTED_PREFIX}: submitTripRole`,
      payload,
    }
  }, [])

  const triproleExecute = useCallback(async (body: {
    action: string
    input_proof_id: string
    executor_uri?: string
    executor_did?: string
    executor_role?: string
    result?: string
    segment_uri?: string
    boq_item_uri?: string
    signatures?: Array<Record<string, unknown>>
    consensus_signatures?: Array<Record<string, unknown>>
    signer_metadata?: Record<string, unknown>
    payload?: Record<string, unknown>
    credentials_vc?: Array<Record<string, unknown>>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
    offline_packet_id?: string
  }) => {
    return submitTripRole(body)
  }, [submitTripRole])

  const applyVariationDelta = useCallback(async (body: {
    boq_item_uri: string
    delta_amount: number
    reason?: string
    project_uri?: string
    executor_uri?: string
    executor_did?: string
    executor_role?: string
    metadata?: Record<string, unknown>
    credentials_vc?: Array<Record<string, unknown>>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
  }) => {
    return submitTripRole({
      action: 'apply_variation',
      payload: body,
    })
  }, [submitTripRole])

  const replayOfflinePackets = useCallback(async (body: {
    packets: Array<Record<string, unknown>>
    stop_on_error?: boolean
    default_executor_uri?: string
    default_executor_role?: string
  }) => {
    return submitTripRole({
      action: 'offline_replay',
      payload: body,
    })
  }, [submitTripRole])

  const scanConfirmSignature = useCallback(async (body: {
    input_proof_id: string
    scan_payload: string
    scanner_did: string
    scanner_role?: string
    executor_uri?: string
    executor_role?: string
    signature_hash?: string
    signer_metadata?: Record<string, unknown>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
  }) => {
    return submitTripRole({
      action: 'scan_confirm',
      payload: body,
    })
  }, [submitTripRole])

  const unitMerkleRoot = useCallback(async (_query: {
    project_uri: string
    unit_code?: string
    proof_id?: string
    max_rows?: number
  }) => {
    return unsupported('unitMerkleRoot')
  }, [])

  const specdictEvolve = useCallback(async (_body: {
    project_uris?: string[]
    min_samples?: number
  }) => {
    return unsupported('specdictEvolve')
  }, [])

  const specdictExport = useCallback(async (_body: {
    project_uris?: string[]
    min_samples?: number
    namespace_uri?: string
    commit?: boolean
  }) => {
    return unsupported('specdictExport')
  }, [])

  const arOverlay = useCallback(async (_query: {
    project_uri: string
    lat: number
    lng: number
    radius_m?: number
    limit?: number
  }) => {
    return unsupported('arOverlay')
  }, [])

  return {
    triproleExecute,
    applyVariationDelta,
    replayOfflinePackets,
    scanConfirmSignature,
    unitMerkleRoot,
    specdictEvolve,
    specdictExport,
    arOverlay,
  }
}
