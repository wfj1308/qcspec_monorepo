import { useCallback } from 'react'
import { useAuthStore } from '../../../store'
import { API_BASE, type ApiRequestFn, withAuthHeaders } from '../base'

export function useProofCore(request: ApiRequestFn) {
  const listProofs = useCallback(async (project_id: string) => {
    return request(`/v1/proof/?project_id=${project_id}`)
  }, [request])

  const verify = useCallback(async (proof_id: string) => {
    return request(`/v1/proof/verify/${proof_id}`)
  }, [request])

  const publicVerifyDetail = useCallback(async (proof_id: string, lineage_depth = 'item') => {
    const id = encodeURIComponent(String(proof_id || '').trim())
    if (!id) return null
    const qs = new URLSearchParams({ lineage_depth }).toString()
    return request(`/api/v1/verify/${id}?${qs}`, { skipAuthRedirect: true })
  }, [request])

  const downloadEvidenceCenterZip = useCallback(async (query: {
    project_uri: string
    subitem_code: string
    proof_id?: string
    verify_base_url?: string
  }) => {
    const qs = new URLSearchParams({
      project_uri: query.project_uri,
      subitem_code: query.subitem_code,
      ...(query.proof_id ? { proof_id: query.proof_id } : {}),
      ...(query.verify_base_url ? { verify_base_url: query.verify_base_url } : {}),
    }).toString()
    const res = await fetch(`${API_BASE}/v1/proof/boq/evidence-center/download?${qs}`, {
      method: 'GET',
      headers: withAuthHeaders(useAuthStore.getState().token),
    })
    if (!res.ok) return null
    const blob = await res.blob()
    const filename =
      (res.headers.get('Content-Disposition') || '').match(/filename=\"?([^\";]+)\"?/)?.[1] ||
      'EvidenceCenter.zip'
    return { blob, filename }
  }, [])

  const stats = useCallback(async (project_id: string) => {
    return request(`/v1/proof/stats/${project_id}`)
  }, [request])

  const nodeTree = useCallback(async (root_uri: string) => {
    return request(`/v1/proof/node-tree?root_uri=${encodeURIComponent(root_uri)}`, { timeoutMs: 120000 })
  }, [request])

  return {
    listProofs,
    verify,
    publicVerifyDetail,
    downloadEvidenceCenterZip,
    stats,
    nodeTree,
  }
}
