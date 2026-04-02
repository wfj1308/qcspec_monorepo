import type { Dispatch, SetStateAction } from 'react'

import { buildMeasurementPayload } from './spuUtils'
import type { Evidence, FormRow, TreeNode } from './types'

type GateStatsLike = {
  labQualified: boolean
  qcCompliant: boolean
  labLatestPass: string
  labLatestHash: string
}

type RunTripSubmitArgs = {
  active: TreeNode | null
  apiProjectUri: string
  inputProofId: string
  isSpecBound: boolean
  roleAllowed: boolean
  compType: string
  form: Record<string, string>
  effectiveSchema: FormRow[]
  sampleId: string
  effectiveClaimQtyValue: number
  exceedBalance: boolean
  executorDid: string
  lat: string
  lng: string
  evidence: Evidence[]
  gateStats: GateStatsLike
  showToast: (message: string) => void
  setDeltaModalOpen: Dispatch<SetStateAction<boolean>>
  setShowAdvancedExecution: Dispatch<SetStateAction<boolean>>
  setExecuting: Dispatch<SetStateAction<boolean>>
  setExecRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  setNodes: Dispatch<SetStateAction<TreeNode[]>>
  setSignOpen: Dispatch<SetStateAction<boolean>>
  setSignStep: Dispatch<SetStateAction<number>>
  refreshTreeFromServer: (focusCode?: string | null) => Promise<unknown>
  smuExecute: (payload: Record<string, unknown>) => Promise<unknown>
}

export async function runTripSubmit({
  active,
  apiProjectUri,
  inputProofId,
  isSpecBound,
  roleAllowed,
  compType,
  form,
  effectiveSchema,
  sampleId,
  effectiveClaimQtyValue,
  exceedBalance,
  executorDid,
  lat,
  lng,
  evidence,
  gateStats,
  showToast,
  setDeltaModalOpen,
  setShowAdvancedExecution,
  setExecuting,
  setExecRes,
  setNodes,
  setSignOpen,
  setSignStep,
  refreshTreeFromServer,
  smuExecute,
}: RunTripSubmitArgs): Promise<void> {
  if (!active?.isLeaf || !apiProjectUri || !inputProofId) {
    showToast('请先选择叶子细目并加载规则')
    return
  }
  if (!isSpecBound) {
    showToast('未绑定规范门控，禁止提交')
    return
  }
  if (!roleAllowed) {
    showToast('角色权限冲突：当前账号无权提交该细目')
    return
  }
  if (!gateStats.labQualified) {
    showToast('证据链不完整：缺少实验合格 Proof')
    return
  }
  if (!gateStats.qcCompliant) {
    showToast('TripRole 现场判定未通过，已拦截提交')
    return
  }
  if (exceedBalance) {
    showToast('申报量超出批复量，已自动跳转变更补差流程')
    setDeltaModalOpen(true)
    setShowAdvancedExecution(true)
    return
  }

  const measurement = buildMeasurementPayload(form, effectiveSchema)
  if (sampleId) {
    measurement.sample_id = sampleId
    measurement.utxo_identifier = sampleId
  }
  if (effectiveClaimQtyValue > 0) measurement.claim_quantity = effectiveClaimQtyValue
  if (gateStats.labLatestPass) measurement.lab_proof_id = gateStats.labLatestPass
  if (gateStats.labLatestHash) measurement.lab_proof_hash = gateStats.labLatestHash

  setExecuting(true)
  try {
    const now = new Date().toISOString()
    let payload: Record<string, unknown> | null = null
    try {
      payload = await smuExecute({
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
      }) as Record<string, unknown> | null
    } catch (err) {
      const msg = String((err as Error)?.message || err || '')
      if (msg.includes('lab PASS')) {
        showToast('证据链不完整：缺少实验合格 Proof')
      } else if (msg.includes('deviation_warning')) {
        showToast('申报量超出批复量，已自动跳转变更补差流程')
        setDeltaModalOpen(true)
        setShowAdvancedExecution(true)
      } else {
        showToast('提交失败')
      }
      return
    }

    if (!payload?.ok) {
      showToast('提交失败')
      return
    }

    setExecRes(payload)
    setNodes((prev) => prev.map((node) => (node.uri === active.uri ? { ...node, status: 'Spending' } : node)))
    setSignOpen(true)
    setSignStep(0)
    void refreshTreeFromServer(active.code)
  } finally {
    setExecuting(false)
  }
}
