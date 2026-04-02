import type { Dispatch, SetStateAction } from 'react'

import { toApiUri } from './treeUtils'
import type { TreeNode } from './types'

type RunTripApplyDeltaArgs = {
  active: TreeNode | null
  apiProjectUri: string
  deltaAmount: string
  deltaReason: string
  executorDid: string
  lat: string
  lng: string
  showToast: (message: string) => void
  applyVariationDelta: (payload: Record<string, unknown>) => Promise<unknown>
  setApplyingDelta: Dispatch<SetStateAction<boolean>>
  setNodes: Dispatch<SetStateAction<TreeNode[]>>
  setVariationRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
}

export async function runTripApplyDelta({
  active,
  apiProjectUri,
  deltaAmount,
  deltaReason,
  executorDid,
  lat,
  lng,
  showToast,
  applyVariationDelta,
  setApplyingDelta,
  setNodes,
  setVariationRes,
}: RunTripApplyDeltaArgs): Promise<void> {
  if (!active?.isLeaf || !apiProjectUri) {
    showToast('请先选择叶子细目')
    return
  }

  const delta = Number(String(deltaAmount || '').replace(/,/g, '').trim())
  if (!Number.isFinite(delta) || Math.abs(delta) < 1e-9) {
    showToast('请输入有效的变更数量')
    return
  }

  setApplyingDelta(true)
  try {
    const now = new Date().toISOString()
    const payload = await applyVariationDelta({
      boq_item_uri: toApiUri(active.uri),
      delta_amount: delta,
      reason: deltaReason,
      project_uri: apiProjectUri,
      executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
      executor_did: executorDid,
      executor_role: 'TRIPROLE',
      geo_location: { lat: Number(lat), lng: Number(lng) },
      server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
    }) as Record<string, unknown> | null

    if (!payload?.ok) {
      showToast('变更补差失败')
      return
    }

    setVariationRes(payload)
    setNodes((prev) => prev.map((node) => {
      if (node.uri !== active.uri) return node
      const next = Math.max(0, (node.contractQty || 0) + delta)
      return { ...node, contractQty: next }
    }))
    showToast('变更补差已写回链')
  } finally {
    setApplyingDelta(false)
  }
}
