import { useCallback } from 'react'
import { useAuthStore } from '../../../store'
import { API_BASE, type ApiRequestFn, withAuthHeaders } from '../base'

export function useProofGovernance(request: ApiRequestFn) {
  const boqItemSovereignHistory = useCallback(async (query: {
    project_uri: string
    subitem_code: string
    max_rows?: number
  }) => {
    const p = new URLSearchParams({
      project_uri: query.project_uri,
      subitem_code: query.subitem_code,
      ...(typeof query.max_rows === 'number' ? { max_rows: String(query.max_rows) } : {}),
    }).toString()
    return request(`/v1/proof/boq/item-sovereign-history?${p}`)
  }, [request])

  const evidenceCenterEvidence = useCallback(async (query: {
    project_uri?: string
    subitem_code?: string
    boq_item_uri?: string
    smu_id?: string
  }) => {
    const p = new URLSearchParams()
    if (query.project_uri) p.set('project_uri', query.project_uri)
    if (query.subitem_code) p.set('subitem_code', query.subitem_code)
    if (query.boq_item_uri) p.set('boq_item_uri', query.boq_item_uri)
    if (query.smu_id) p.set('smu_id', query.smu_id)
    return request(`/v1/proof/boq/evidence-center/evidence?${p.toString()}`)
  }, [request])

  const triproleAssetOrigin = useCallback(async (query: {
    utxo_id?: string
    boq_item_uri?: string
    project_uri?: string
  }) => {
    const p = new URLSearchParams()
    if (query.utxo_id) p.set('utxo_id', query.utxo_id)
    if (query.boq_item_uri) p.set('boq_item_uri', query.boq_item_uri)
    if (query.project_uri) p.set('project_uri', query.project_uri)
    return request(`/v1/proof/triprole/asset-origin?${p.toString()}`)
  }, [request])

  const identityReputation = useCallback(async (query: {
    project_uri: string
    participant_did: string
    window_days?: number
  }) => {
    const p = new URLSearchParams({
      project_uri: query.project_uri,
      participant_did: query.participant_did,
      ...(typeof query.window_days === 'number' ? { window_days: String(query.window_days) } : {}),
    }).toString()
    return request(`/v1/proof/identity/reputation?${p}`)
  }, [request])

  const boqReconciliation = useCallback(async (query: {
    project_uri: string
    subitem_code?: string
    max_rows?: number
    limit_items?: number
  }) => {
    const p = new URLSearchParams({
      project_uri: query.project_uri,
      ...(query.subitem_code ? { subitem_code: query.subitem_code } : {}),
      ...(typeof query.max_rows === 'number' ? { max_rows: String(query.max_rows) } : {}),
      ...(typeof query.limit_items === 'number' ? { limit_items: String(query.limit_items) } : {}),
    }).toString()
    return request(`/v1/proof/boq/reconciliation?${p}`, { timeoutMs: 120000 })
  }, [request])

  const docFinalContext = useCallback(async (boq_item_uri: string) => {
    return request(`/v1/proof/docfinal/context?boq_item_uri=${encodeURIComponent(boq_item_uri)}`)
  }, [request])

  const getGateEditorPayload = useCallback(async (project_uri: string, subitem_code: string) => {
    const qs = new URLSearchParams({ project_uri }).toString()
    return request(`/v1/proof/gate-editor/${encodeURIComponent(subitem_code)}?${qs}`)
  }, [request])

  const importGateRulesFromNorm = useCallback(async (body: {
    spec_uri: string
    context?: string
  }) => {
    return request('/v1/proof/gate-editor/import-norm', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const generateGateRulesViaAi = useCallback(async (body: {
    prompt: string
    subitem_code?: string
  }) => {
    return request('/v1/proof/gate-editor/generate-via-ai', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const saveGateRuleVersion = useCallback(async (body: {
    project_uri: string
    subitem_code: string
    gate_id_base?: string
    rules: Array<Record<string, unknown>>
    execution_strategy?: string
    fail_action?: string
    apply_to_similar?: boolean
    executor_uri?: string
    metadata?: Record<string, unknown>
  }) => {
    return request('/v1/proof/gate-editor/save', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const rollbackGateRuleVersion = useCallback(async (body: {
    project_uri: string
    subitem_code: string
    target_proof_id?: string
    target_version?: string
    apply_to_similar?: boolean
    executor_uri?: string
  }) => {
    return request('/v1/proof/gate-editor/rollback', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const getSpecDict = useCallback(async (spec_dict_key: string) => {
    return request(`/v1/proof/spec-dict/${encodeURIComponent(spec_dict_key)}`)
  }, [request])

  const saveSpecDict = useCallback(async (body: {
    spec_dict_key: string
    title?: string
    version?: string
    authority?: string
    spec_uri?: string
    items: Record<string, unknown>
    metadata?: Record<string, unknown>
    is_active?: boolean
  }) => {
    return request('/v1/proof/spec-dict/save', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }, [request])

  const resolveSpecDictThreshold = useCallback(async (gate_id: string, context = '') => {
    const qs = new URLSearchParams({ gate_id, context }).toString()
    return request(`/v1/proof/spec-dict-resolve-threshold?${qs}`)
  }, [request])

  const exportDocFinal = useCallback(async (body: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/docfinal/export`, {
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
      rootHash: res.headers.get('X-DocFinal-Root-Hash') || '',
      proofId: res.headers.get('X-DocFinal-Proof-Id') || '',
      gitpegAnchor: res.headers.get('X-DocFinal-GitPeg-Anchor') || '',
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'MASTER-DSP.qcdsp',
    }
  }, [])

  const finalizeDocFinal = useCallback(async (body: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
    run_anchor_rounds?: number
  }) => {
    const res = await fetch(`${API_BASE}/v1/proof/docfinal/finalize`, {
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
      rootHash: res.headers.get('X-DocFinal-Root-Hash') || '',
      proofId: res.headers.get('X-DocFinal-Proof-Id') || '',
      gitpegAnchor: res.headers.get('X-DocFinal-GitPeg-Anchor') || '',
      finalGitpegAnchor: res.headers.get('X-DocFinal-Final-GitPeg-Anchor') || '',
      anchorRuns: Number(res.headers.get('X-DocFinal-Anchor-Runs') || 0),
      filename: (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] || 'MASTER-DSP.qcdsp',
    }
  }, [])

  return {
    boqItemSovereignHistory,
    evidenceCenterEvidence,
    triproleAssetOrigin,
    identityReputation,
    boqReconciliation,
    docFinalContext,
    getGateEditorPayload,
    importGateRulesFromNorm,
    generateGateRulesViaAi,
    saveGateRuleVersion,
    rollbackGateRuleVersion,
    getSpecDict,
    saveSpecDict,
    resolveSpecDictThreshold,
    exportDocFinal,
    finalizeDocFinal,
  }
}
