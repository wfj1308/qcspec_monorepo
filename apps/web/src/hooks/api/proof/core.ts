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

export function useProofCore(_request: ApiRequestFn) {
  const listProofs = useCallback(async (project_id: string) => {
    return unsupported('listProofs', { project_id })
  }, [])

  const verify = useCallback(async (proof_id: string) => {
    const id = String(proof_id || '').trim()
    if (!id) return null
    return {
      valid: false,
      chain_length: 0,
      unsupported: true,
      message: `${DOCPEG_UNSUPPORTED_PREFIX}: verify`,
    }
  }, [])

  const publicVerifyDetail = useCallback(async (proof_id: string, lineage_depth = 'item') => {
    const id = String(proof_id || '').trim()
    if (!id) return null
    return {
      ok: false,
      unsupported: true,
      proof_id: id,
      lineage_depth,
      source: 'docpeg-api-pack',
    }
  }, [])

  const downloadEvidenceCenterZip = useCallback(async (_query: {
    project_uri: string
    subitem_code: string
    proof_id?: string
    verify_base_url?: string
  }) => {
    return {
      blob: undefined,
      filename: undefined,
      ...unsupported('downloadEvidenceCenterZip'),
    }
  }, [])

  const stats = useCallback(async (_project_id: string) => {
    return unsupported('stats')
  }, [])

  const nodeTree = useCallback(async (_root_uri: string) => {
    return unsupported('nodeTree')
  }, [])

  return {
    listProofs,
    verify,
    publicVerifyDetail,
    downloadEvidenceCenterZip,
    stats,
    nodeTree,
  }
}
