import { useCallback } from 'react'
import { useAuthStore } from '../../../store'
import { API_BASE, type ApiRequestFn, withAuthHeaders } from '../base'

export function useProofExecution(request: ApiRequestFn) {
  const generatePaymentCertificate = useCallback(async (body: {
    project_uri: string
    period: string
    project_name?: string
    verify_base_url?: string
    create_proof?: boolean
    executor_uri?: string
    enforce_dual_pass?: boolean
  }) => {
    return request('/v1/proof/payment/certificate/generate', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const paymentAuditTrace = useCallback(async (payment_id: string) => {
    return request(`/v1/proof/payment/audit-trace/${encodeURIComponent(payment_id)}`)
  }, [request])

  const recordLabTest = useCallback(async (body: {
    project_uri: string
    boq_item_uri: string
    sample_id: string
    jtg_form_code?: string
    instrument_sn?: string
    tested_at?: string
    witness_record?: Record<string, unknown>
    sample_tracking?: Record<string, unknown>
    metrics?: Array<Record<string, unknown>>
    result?: string
    executor_uri?: string
    metadata?: Record<string, unknown>
  }) => {
    return request('/v1/proof/lab/record', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const calcInspectionFrequency = useCallback(async (body: {
    boq_item_uri: string
    project_uri?: string
  }) => {
    return request('/v1/proof/frequency/calc', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const frequencyDashboard = useCallback(async (project_uri: string, limit_items = 200) => {
    const qs = new URLSearchParams({
      project_uri,
      limit_items: String(limit_items),
    }).toString()
    return request(`/v1/proof/frequency/dashboard?${qs}`)
  }, [request])

  const openRemediation = useCallback(async (body: {
    fail_proof_id: string
    notice?: string
    due_date?: string
    assignees?: string[]
    executor_uri?: string
  }) => {
    return request('/v1/proof/remediation/open', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const remediationReinspect = useCallback(async (body: {
    remediation_proof_id: string
    result: string
    payload?: Record<string, unknown>
    executor_uri?: string
  }) => {
    return request('/v1/proof/remediation/reinspect', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const closeRemediation = useCallback(async (body: {
    remediation_proof_id: string
    reinspection_proof_id: string
    close_note?: string
    executor_uri?: string
  }) => {
    return request('/v1/proof/remediation/close', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const generateRailPactInstruction = useCallback(async (body: {
    payment_id: string
    executor_uri?: string
    auto_submit?: boolean
  }) => {
    return request('/v1/proof/payment/railpact/instruction', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const bindSpatialUtxo = useCallback(async (body: {
    utxo_id: string
    project_uri?: string
    bim_id?: string
    label?: string
    coordinate?: Record<string, unknown>
    metadata?: Record<string, unknown>
  }) => {
    return request('/v1/proof/spatial/bind', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const spatialDashboard = useCallback(async (project_uri: string, limit = 5000) => {
    return request(`/v1/proof/spatial/dashboard?project_uri=${encodeURIComponent(project_uri)}&limit=${encodeURIComponent(String(limit))}`)
  }, [request])

  const predictiveQualityAnalysis = useCallback(async (body: {
    project_uri: string
    near_threshold_ratio?: number
    min_samples?: number
    apply_dynamic_gate?: boolean
    default_critical_threshold?: number
  }) => {
    return request('/v1/proof/ai/predictive-quality', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const exportFinanceProof = useCallback(async (body: {
    payment_id: string
    bank_code?: string
    passphrase?: string
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/finance/proof/export`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      paymentId: res.headers.get('X-Finance-Payment-Id') || '',
      proofId: res.headers.get('X-Finance-Proof-Id') || '',
      payloadHash: res.headers.get('X-Finance-Payload-Hash') || '',
      gitpegAnchor: res.headers.get('X-Finance-GitPeg-Anchor') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'FINANCE-PROOF.qcfp',
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
    return request('/v1/proof/triprole/execute', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

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
    return request('/v1/proof/triprole/apply-variation', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const replayOfflinePackets = useCallback(async (body: {
    packets: Array<Record<string, unknown>>
    stop_on_error?: boolean
    default_executor_uri?: string
    default_executor_role?: string
  }) => {
    return request('/v1/proof/triprole/offline/replay', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

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
    return request('/v1/proof/triprole/scan-confirm', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const ingestSensorData = useCallback(async (body: {
    device_id: string
    raw_payload: unknown
    boq_item_uri: string
    project_uri?: string
    executor_uri?: string
    executor_did?: string
    executor_role?: string
    metadata?: Record<string, unknown>
    credentials_vc?: Array<Record<string, unknown>>
    geo_location?: Record<string, unknown>
    server_timestamp_proof?: Record<string, unknown>
  }) => {
    return request('/v1/proof/triprole/hardware/ingest', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const unitMerkleRoot = useCallback(async (query: {
    project_uri: string
    unit_code?: string
    proof_id?: string
    max_rows?: number
  }) => {
    const p = new URLSearchParams()
    p.set('project_uri', query.project_uri)
    if (query.unit_code) p.set('unit_code', query.unit_code)
    if (query.proof_id) p.set('proof_id', query.proof_id)
    if (typeof query.max_rows === 'number') p.set('max_rows', String(query.max_rows))
    return request(`/v1/proof/unit/merkle-root?${p.toString()}`)
  }, [request])

  const convertRwaAsset = useCallback(async (body: {
    project_uri: string
    boq_group_id: string
    project_name?: string
    bank_code?: string
    passphrase?: string
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/rwa/convert`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      projectUri: res.headers.get('X-RWA-Project-Uri') || '',
      groupId: res.headers.get('X-RWA-Group-Id') || '',
      proofId: res.headers.get('X-RWA-Proof-Id') || '',
      certificateHash: res.headers.get('X-RWA-Certificate-Hash') || '',
      gitpegAnchor: res.headers.get('X-RWA-GitPeg-Anchor') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'RWA-ASSET.qcrwa',
    }
  }, [])

  const exportOmHandoverBundle = useCallback(async (body: {
    project_uri: string
    project_name?: string
    om_owner_uri?: string
    passphrase?: string
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/om/handover/export`, {
      method: 'POST',
      headers: withAuthHeaders(useAuthStore.getState().token, {
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return {
      blob,
      omRootUri: res.headers.get('X-OM-Root-Uri') || '',
      omRootProofId: res.headers.get('X-OM-Root-Proof-Id') || '',
      omGitpegAnchor: res.headers.get('X-OM-GitPeg-Anchor') || '',
      payloadHash: res.headers.get('X-OM-Payload-Hash') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'OM-HANDOVER.zip',
    }
  }, [])

  const registerOmEvent = useCallback(async (body: {
    om_root_proof_id: string
    title: string
    event_type?: string
    payload?: Record<string, unknown>
    executor_uri?: string
  }) => {
    return request('/v1/proof/om/event/register', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const generateNormEvolutionReport = useCallback(async (body: {
    project_uris?: string[]
    min_samples?: number
    near_threshold_ratio?: number
    anonymize?: boolean
    create_proof?: boolean
  }) => {
    return request('/v1/proof/norm/evolution/report', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const specdictEvolve = useCallback(async (body: {
    project_uris?: string[]
    min_samples?: number
  }) => {
    return request('/v1/proof/specdict/evolve', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const specdictExport = useCallback(async (body: {
    project_uris?: string[]
    min_samples?: number
    namespace_uri?: string
    commit?: boolean
  }) => {
    return request('/v1/proof/specdict/export', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const arOverlay = useCallback(async (query: {
    project_uri: string
    lat: number
    lng: number
    radius_m?: number
    limit?: number
  }) => {
    const p = new URLSearchParams({
      project_uri: query.project_uri,
      lat: String(query.lat),
      lng: String(query.lng),
      ...(typeof query.radius_m === 'number' ? { radius_m: String(query.radius_m) } : {}),
      ...(typeof query.limit === 'number' ? { limit: String(query.limit) } : {}),
    }).toString()
    return request(`/v1/proof/ar/overlay?${p}`)
  }, [request])

  return {
    generatePaymentCertificate,
    paymentAuditTrace,
    recordLabTest,
    calcInspectionFrequency,
    frequencyDashboard,
    openRemediation,
    remediationReinspect,
    closeRemediation,
    generateRailPactInstruction,
    bindSpatialUtxo,
    spatialDashboard,
    predictiveQualityAnalysis,
    exportFinanceProof,
    triproleExecute,
    applyVariationDelta,
    replayOfflinePackets,
    scanConfirmSignature,
    ingestSensorData,
    unitMerkleRoot,
    convertRwaAsset,
    exportOmHandoverBundle,
    registerOmEvent,
    generateNormEvolutionReport,
    specdictEvolve,
    specdictExport,
    arOverlay,
  }
}
