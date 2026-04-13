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

export function useProofGovernance(_request: ApiRequestFn) {

  const boqItemSovereignHistory = useCallback(async (query: {
    project_uri: string
    subitem_code: string
    max_rows?: number
  }) => {
    return {
      ok: true,
      project_uri: query.project_uri,
      subitem_code: String(query.subitem_code || '').trim(),
      rows: [],
      source: 'docpeg-api-pack',
    }
  }, [])

  const evidenceCenterEvidence = useCallback(async (_query: {
    project_uri?: string
    subitem_code?: string
    boq_item_uri?: string
    smu_id?: string
  }) => {
    return unsupported('evidenceCenterEvidence')
  }, [])

  const boqReconciliation = useCallback(async (query: {
    project_uri: string
    subitem_code?: string
    max_rows?: number
    limit_items?: number
  }) => {
    return {
      ok: true,
      project_uri: query.project_uri,
      subitem_code: String(query.subitem_code || '').trim() || undefined,
      items: [],
      total: 0,
      source: 'docpeg-api-pack',
    }
  }, [])

  const docFinalContext = useCallback(async (_boq_item_uri: string) => {
    return unsupported('docFinalContext')
  }, [])

  const exportDocFinal = useCallback(async (_body: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
  }) => {
    return unsupported('exportDocFinal')
  }, [])

  const finalizeDocFinal = useCallback(async (_body: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
    run_anchor_rounds?: number
  }) => {
    return unsupported('finalizeDocFinal')
  }, [])

  return {
    boqItemSovereignHistory,
    evidenceCenterEvidence,
    boqReconciliation,
    docFinalContext,
    exportDocFinal,
    finalizeDocFinal,
  }
}
