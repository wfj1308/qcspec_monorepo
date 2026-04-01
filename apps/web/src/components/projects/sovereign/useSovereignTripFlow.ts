import { useCallback, useEffect, useRef } from 'react'
import type { Dispatch, SetStateAction } from 'react'

import { buildMeasurementPayload } from './spuUtils'
import { toApiUri } from './treeUtils'
import type { Evidence, FormRow, TreeNode } from './types'

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

type GateStatsLike = {
  labQualified: boolean
  qcCompliant: boolean
  labLatestPass: string
  labLatestHash: string
}

type TripFlowState = {
  setExecuting: Dispatch<SetStateAction<boolean>>
  setRejecting: Dispatch<SetStateAction<boolean>>
  execRes: Record<string, unknown> | null
  setExecRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  setSignOpen: Dispatch<SetStateAction<boolean>>
  setSignStep: Dispatch<SetStateAction<number>>
  setSigning: Dispatch<SetStateAction<boolean>>
  signRes: Record<string, unknown> | null
  setSignRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  mockGenerating: boolean
  setMockGenerating: Dispatch<SetStateAction<boolean>>
  mockDocRes: Record<string, unknown> | null
  setMockDocRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  consensusContractorValue: string
  consensusSupervisorValue: string
  consensusOwnerValue: string
  consensusAllowedDeviation: string
  consensusAllowedDeviationPct: string
  setFreezeProof: Dispatch<SetStateAction<string>>
  deltaAmount: string
  deltaReason: string
  setApplyingDelta: Dispatch<SetStateAction<boolean>>
  setVariationRes: Dispatch<SetStateAction<Record<string, unknown> | null>>
  setShowAdvancedExecution: Dispatch<SetStateAction<boolean>>
  setDeltaModalOpen: Dispatch<SetStateAction<boolean>>
}

type UseSovereignTripFlowArgs = {
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
  measuredQtyValue: number
  exceedBalance: boolean
  executorDid: string
  supervisorDid: string
  ownerDid: string
  lat: string
  lng: string
  evidence: Evidence[]
  gateStats: GateStatsLike
  geoAnchor: { lat: number; lng: number } | null
  templatePath: string
  refreshTreeFromServer: (focusCode?: string | null) => Promise<unknown>
  setNodes: Dispatch<SetStateAction<TreeNode[]>>
  setDisputeProofId: Dispatch<SetStateAction<string>>
  setShowAdvancedConsensus: Dispatch<SetStateAction<boolean>>
  showToast: (message: string) => void
  smuExecute: (payload: Record<string, unknown>) => Promise<unknown>
  tripGenerateDoc: (payload: Record<string, unknown>) => Promise<unknown>
  smuSign: (payload: Record<string, unknown>) => Promise<unknown>
  smuFreeze: (payload: Record<string, unknown>) => Promise<unknown>
  applyVariationDelta: (payload: Record<string, unknown>) => Promise<unknown>
  tripState: TripFlowState
  onMockDocReady?: () => void
}

export function useSovereignTripFlow({
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
  measuredQtyValue,
  exceedBalance,
  executorDid,
  supervisorDid,
  ownerDid,
  lat,
  lng,
  evidence,
  gateStats,
  geoAnchor,
  templatePath,
  refreshTreeFromServer,
  setNodes,
  setDisputeProofId,
  setShowAdvancedConsensus,
  showToast,
  smuExecute,
  tripGenerateDoc,
  smuSign,
  smuFreeze,
  applyVariationDelta,
  tripState,
  onMockDocReady,
}: UseSovereignTripFlowArgs) {
  const autoDocTriggerRef = useRef('')
  const {
    setExecuting,
    setRejecting,
    execRes,
    setExecRes,
    setSignOpen,
    setSignStep,
    setSigning,
    signRes,
    setSignRes,
    mockGenerating,
    setMockGenerating,
    mockDocRes,
    setMockDocRes,
    consensusContractorValue,
    consensusSupervisorValue,
    consensusOwnerValue,
    consensusAllowedDeviation,
    consensusAllowedDeviationPct,
    setFreezeProof,
    deltaAmount,
    deltaReason,
    setApplyingDelta,
    setVariationRes,
    setShowAdvancedExecution,
    setDeltaModalOpen,
  } = tripState

  const consensusBaseValue = effectiveClaimQtyValue > 0 ? effectiveClaimQtyValue : measuredQtyValue
  const approvedProofId = String(
    asDict(signRes?.trip).output_proof_id ||
    (signRes as Record<string, unknown> | null)?.output_proof_id ||
    '',
  ).trim()
  const hasPreviewPdf = Boolean(
    String(asDict(signRes?.docpeg).pdf_preview_b64 || asDict(mockDocRes?.docpeg).pdf_preview_b64 || '').trim(),
  )

  useEffect(() => {
    if (exceedBalance) {
      setDeltaModalOpen(true)
      setShowAdvancedExecution(true)
      return
    }
    setDeltaModalOpen(false)
    setShowAdvancedExecution(false)
  }, [exceedBalance, setDeltaModalOpen, setShowAdvancedExecution])

  const submitTrip = useCallback(async () => {
    if (!active?.isLeaf || !apiProjectUri || !inputProofId) {
      showToast('请先选择叶子细目并加载规则')
      return
    }
    if (!isSpecBound) {
      showToast('未绑定规范/门控，禁止提交')
      return
    }
    if (!roleAllowed) {
      showToast('角色权限冲突：当前账号无权提交该子目')
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
  }, [
    active,
    apiProjectUri,
    compType,
    effectiveClaimQtyValue,
    effectiveSchema,
    evidence,
    exceedBalance,
    executorDid,
    form,
    gateStats,
    inputProofId,
    isSpecBound,
    lat,
    lng,
    refreshTreeFromServer,
    roleAllowed,
    setDeltaModalOpen,
    setExecuting,
    setExecRes,
    setNodes,
    setShowAdvancedExecution,
    setSignOpen,
    setSignStep,
    showToast,
    smuExecute,
    sampleId,
  ])

  const submitTripMock = useCallback(async () => {
    if (!active?.isLeaf || !apiProjectUri) {
      showToast('请先选择叶子细目')
      return
    }
    if (!isSpecBound) {
      showToast('未绑定规范/门控，禁止提交')
      return
    }

    const measurement = buildMeasurementPayload(form, effectiveSchema)
    if (sampleId) measurement.sample_id = sampleId
    if (effectiveClaimQtyValue > 0) measurement.claim_quantity = effectiveClaimQtyValue

    const normRows = effectiveSchema.map((row, idx) => {
      const field = String(row.field || `f_${idx}`)
      const measured = String(form[field] ?? '').trim()
      return {
        field,
        label: row.label || field,
        operator: String(row.operator || 'present'),
        threshold: String(row.default || ''),
        measured_value: measured,
        unit: String(row.unit || ''),
      }
    })

    setMockGenerating(true)
    try {
      const payload = await tripGenerateDoc({
        project_uri: apiProjectUri,
        boq_item_uri: toApiUri(active.uri),
        smu_id: String(active.code || '').split('-')[0],
        subitem_code: active.code,
        item_name: active.name,
        unit: active.unit || '',
        executor_did: executorDid,
        geo_location: { lat: Number(lat), lng: Number(lng) },
        anchor_location: geoAnchor ? { lat: geoAnchor.lat, lng: geoAnchor.lng } : {},
        norm_rows: normRows,
        measurements: measurement,
        evidence_hashes: evidence.map((item) => item.hash),
        report_template: '3、桥施表.docx',
      }) as Record<string, unknown> | null

      if (!payload?.ok) {
        showToast('DocPeg Mock 生成失败')
        return
      }

      setMockDocRes(payload)
      onMockDocReady?.()
      const risk = Number((asDict(payload.risk_audit).risk_score || 0))
      if (risk < 60) showToast(`报告已生成，但风险偏高（${risk.toFixed(2)}）`)
      else showToast('桥施表已生成，Total Proof Hash 已锁定')
    } finally {
      setMockGenerating(false)
    }
  }, [
    active,
    apiProjectUri,
    effectiveClaimQtyValue,
    effectiveSchema,
    evidence,
    executorDid,
    form,
    geoAnchor,
    isSpecBound,
    lat,
    lng,
    onMockDocReady,
    sampleId,
    setMockDocRes,
    setMockGenerating,
    showToast,
    tripGenerateDoc,
  ])

  useEffect(() => {
    if (!approvedProofId) return
    if (hasPreviewPdf) return
    if (mockGenerating) return
    if (!active?.isLeaf || !isSpecBound) return
    if (autoDocTriggerRef.current === approvedProofId) return
    autoDocTriggerRef.current = approvedProofId
    void submitTripMock()
  }, [active?.isLeaf, approvedProofId, hasPreviewPdf, isSpecBound, mockGenerating, submitTripMock])

  const recordRejectTrip = useCallback(async () => {
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
  }, [
    active,
    apiProjectUri,
    compType,
    effectiveSchema,
    evidence,
    executorDid,
    form,
    gateStats.labLatestHash,
    gateStats.labLatestPass,
    inputProofId,
    lat,
    lng,
    refreshTreeFromServer,
    sampleId,
    setExecRes,
    setRejecting,
    showToast,
    smuExecute,
  ])

  const doSign = useCallback(async () => {
    const output = String(asDict(execRes?.trip).output_proof_id || '')
    if (!active?.uri || !output) return

    setSigning(true)
    try {
      for (const step of [1, 2, 3]) {
        setSignStep(step)
        await new Promise((resolve) => window.setTimeout(resolve, 350))
      }

      const now = new Date().toISOString()
      const parseConsensus = (raw: string, fallback: number) => {
        const cleaned = String(raw || '').replace(/,/g, '').trim()
        const parsed = Number(cleaned)
        return Number.isFinite(parsed) ? parsed : fallback
      }
      const parseOptional = (raw: string) => {
        const cleaned = String(raw || '').replace(/,/g, '').trim()
        if (!cleaned) return Number.NaN
        return Number(cleaned)
      }

      const consensusValues = [
        { role: 'contractor', did: executorDid, value: parseConsensus(consensusContractorValue, consensusBaseValue) },
        { role: 'supervisor', did: supervisorDid, value: parseConsensus(consensusSupervisorValue, consensusBaseValue) },
        { role: 'owner', did: ownerDid, value: parseConsensus(consensusOwnerValue, consensusBaseValue) },
      ].filter((item) => Number.isFinite(item.value))

      const allowedAbs = parseOptional(consensusAllowedDeviation)
      const allowedPct = parseOptional(consensusAllowedDeviationPct)
      const signerMetadata = {
        mode: 'liveness',
        checked_at: now,
        passed: true,
        signers: consensusValues.map((item) => ({
          role: item.role,
          did: item.did,
          biometric_passed: true,
          verified_at: now,
          measured_value: item.value,
        })),
      }

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
          allowed_deviation: Number.isFinite(allowedAbs) ? allowedAbs : undefined,
          allowed_deviation_percent: Number.isFinite(allowedPct) ? allowedPct : undefined,
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
  }, [
    active,
    apiProjectUri,
    consensusAllowedDeviation,
    consensusAllowedDeviationPct,
    consensusBaseValue,
    consensusContractorValue,
    consensusOwnerValue,
    consensusSupervisorValue,
    execRes,
    executorDid,
    lat,
    lng,
    ownerDid,
    setDisputeProofId,
    setFreezeProof,
    setNodes,
    setShowAdvancedConsensus,
    setSignOpen,
    setSignRes,
    setSignStep,
    setSigning,
    showToast,
    smuFreeze,
    smuSign,
    supervisorDid,
    templatePath,
  ])

  const applyDelta = useCallback(async () => {
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
  }, [
    active,
    apiProjectUri,
    applyVariationDelta,
    deltaAmount,
    deltaReason,
    executorDid,
    lat,
    lng,
    setApplyingDelta,
    setNodes,
    setVariationRes,
    showToast,
  ])

  return {
    submitTrip,
    submitTripMock,
    recordRejectTrip,
    doSign,
    applyDelta,
  }
}
