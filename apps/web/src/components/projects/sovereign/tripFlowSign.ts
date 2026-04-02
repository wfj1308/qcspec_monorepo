import type { Dispatch, SetStateAction } from 'react'

import { buildConsensusValues, buildSignerMetadata, parseOptionalNumber } from './tripFlowConsensus'
import { toApiUri } from './treeUtils'
import type { TreeNode } from './types'
import { asDict } from './tripFlowUtils'

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

type RunTripSignArgs = {
  active: TreeNode | null
  execRes: Record<string, unknown> | null
  apiProjectUri: string
  templatePath: string
  executorDid: string
  supervisorDid: string
  ownerDid: string
  lat: string
  lng: string
  consensusBaseValue: number
  consensusContractorValue: string
  consensusSupervisorValue: string
  consensusOwnerValue: string
  consensusAllowedDeviation: string
  consensusAllowedDeviationPct: string
  showToast: (message: string) => void
  smuSign: (payload: Record<string, unknown>) => Promise<unknown>
  smuFreeze: (payload: Record<string, unknown>) => Promise<unknown>
  setSigning: Dispatch<SetStateAction<boolean>>
  setSignStep: Dispatch<SetStateAction<number>>
  setDisputeProofId: Dispatch<SetStateAction<string>>
  setShowAdvancedConsensus: Dispatch<SetStateAction<boolean>>
  setSignRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  setNodes: Dispatch<SetStateAction<TreeNode[]>>
  setFreezeProof: Dispatch<SetStateAction<string>>
  setSignOpen: Dispatch<SetStateAction<boolean>>
}

export async function runTripSign({
  active,
  execRes,
  apiProjectUri,
  templatePath,
  executorDid,
  supervisorDid,
  ownerDid,
  lat,
  lng,
  consensusBaseValue,
  consensusContractorValue,
  consensusSupervisorValue,
  consensusOwnerValue,
  consensusAllowedDeviation,
  consensusAllowedDeviationPct,
  showToast,
  smuSign,
  smuFreeze,
  setSigning,
  setSignStep,
  setDisputeProofId,
  setShowAdvancedConsensus,
  setSignRes,
  setNodes,
  setFreezeProof,
  setSignOpen,
}: RunTripSignArgs): Promise<void> {
  const output = String(asDict(execRes?.trip).output_proof_id || '')
  if (!active?.uri || !output) return

  setSigning(true)
  try {
    for (const step of [1, 2, 3]) {
      setSignStep(step)
      await sleep(350)
    }

    const now = new Date().toISOString()
    const consensusValues = buildConsensusValues({
      executorDid,
      supervisorDid,
      ownerDid,
      consensusContractorValue,
      consensusSupervisorValue,
      consensusOwnerValue,
      fallbackValue: consensusBaseValue,
    })
    const allowedAbs = parseOptionalNumber(consensusAllowedDeviation)
    const allowedPct = parseOptionalNumber(consensusAllowedDeviationPct)
    const signerMetadata = buildSignerMetadata(consensusValues, now)

    let payload: Record<string, unknown> | null = null
    try {
      payload = await smuSign({
        input_proof_id: output,
        boq_item_uri: toApiUri(active.uri),
        supervisor_executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/supervisor/mobile/`,
        supervisor_did: supervisorDid,
        contractor_did: executorDid,
        owner_did: ownerDid,
        signer_metadata: signerMetadata,
        consensus_values: consensusValues,
        allowed_deviation: allowedAbs,
        allowed_deviation_percent: allowedPct,
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
        auto_docpeg: true,
        template_path: String(templatePath || ''),
      }) as Record<string, unknown> | null
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求异常'
      const disputeMatch = String(msg || '').match(/dispute_proof_id=([A-Za-z0-9-]+)/)
      const openMatch = String(msg || '').match(/consensus_dispute_open:\s*([A-Za-z0-9-]+)/)
      const disputeId = disputeMatch?.[1] || openMatch?.[1] || ''
      if (disputeId) {
        setDisputeProofId(disputeId)
        setShowAdvancedConsensus(true)
        showToast(`共识冲突已触发：${disputeId}`)
        return
      }
      showToast(`签认失败：${msg}`)
      return
    }

    if (!payload?.ok) {
      showToast('签认失败')
      return
    }

    setSignRes(payload)
    setNodes((prev) => prev.map((node) => (node.uri === active.uri ? { ...node, status: 'Settled' } : node)))
    const smuId = active.code.split('-')[0]
    if (smuId) {
      const freeze = await smuFreeze({
        project_uri: apiProjectUri,
        smu_id: smuId,
        executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/owner/system/`,
        min_risk_score: 60,
      }) as Record<string, unknown> | null
      if (freeze?.ok) setFreezeProof(String(freeze.freeze_proof_id || ''))
    }
    setSignOpen(false)
  } finally {
    setSigning(false)
  }
}
