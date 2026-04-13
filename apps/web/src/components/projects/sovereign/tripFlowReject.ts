import type { Dispatch, SetStateAction } from 'react'

import { buildMeasurementPayload } from './spuUtils'
import type { Evidence, FormRow, TreeNode } from './types'

type GateStatsLike = {
  labLatestPass: string
  labLatestHash: string
}

type RunTripRejectArgs = {
  active: TreeNode | null
  apiProjectUri: string
  inputProofId: string
  compType: string
  form: Record<string, string>
  effectiveSchema: FormRow[]
  sampleId: string
  executorDid: string
  lat: string
  lng: string
  evidence: Evidence[]
  gateStats: GateStatsLike
  refreshTreeFromServer: (focusCode?: string | null) => Promise<unknown>
  showToast: (message: string) => void
  smuExecute: (payload: Record<string, unknown>) => Promise<unknown>
  setRejecting: Dispatch<SetStateAction<boolean>>
  setExecRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
}

export async function runTripReject({
  active,
  apiProjectUri,
  inputProofId,
  compType,
  form,
  effectiveSchema,
  sampleId,
  executorDid,
  lat,
  lng,
  evidence,
  gateStats,
  refreshTreeFromServer,
  showToast,
  smuExecute,
  setRejecting,
  setExecRes,
}: RunTripRejectArgs): Promise<void> {
  if (!active?.isLeaf || !apiProjectUri || !inputProofId) {
    showToast('请先选择叶子细目并加载规则')
    return
  }

  setRejecting(true)
  try {
    const now = new Date().toISOString()
    const measurement = buildMeasurementPayload(form, effectiveSchema)
    if (sampleId) {
      measurement.sample_id = sampleId
      measurement.utxo_identifier = sampleId
    }
    if (gateStats.labLatestPass) measurement.lab_proof_id = gateStats.labLatestPass
    if (gateStats.labLatestHash) measurement.lab_proof_hash = gateStats.labLatestHash

    const payload = await smuExecute({
      project_uri: apiProjectUri,
      input_proof_id: inputProofId,
      executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/`,
      executor_did: executorDid,
      executor_role: 'TRIPROLE',
      component_type: compType,
      measurement,
      geo_location: { lat: Number(lat), lng: Number(lng) },
      server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
      evidence_hashes: evidence.map((item) => item.hash),
      force_reject: true,
    }) as Record<string, unknown> | null

    if (!payload?.ok) {
      showToast('记录拒绝失败')
      return
    }

    setExecRes(payload)
    showToast('已记录不合格 Proof')
    void refreshTreeFromServer(active.code)
  } finally {
    setRejecting(false)
  }
}

