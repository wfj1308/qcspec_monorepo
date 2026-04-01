import { useEffect, useState } from 'react'
import type { Project } from '@qcspec/types'

type ProofRow = {
  proof_id: string
  summary?: string
  object_type?: string
  action?: string
  created_at?: string
}

type ProofStats = {
  total: number
  by_type: Record<string, number>
  by_action: Record<string, number>
}

type ProofNodeRow = {
  uri?: string
  node_type?: string
  status?: string
}

type ProjectLike = Pick<Project, 'id' | 'name' | 'v_uri'> | null

interface UseProofDashboardControllerArgs {
  activeTab: string
  proj: Pick<Project, 'id' | 'name' | 'v_uri'>
  projectDetailOpen: boolean
  detailProject: ProjectLike
  showToast: (message: string) => void
  listProofs: (projectId: string) => Promise<unknown>
  verifyProof: (proofId: string) => Promise<unknown>
  proofStatsApi: (projectId: string) => Promise<unknown>
  proofNodeTreeApi: (projectUri: string) => Promise<unknown>
  boqRealtimeStatusApi: (projectUri: string) => Promise<unknown>
  boqItemSovereignHistoryApi: (payload: {
    project_uri: string
    subitem_code: string
    max_rows: number
  }) => Promise<unknown>
  boqReconciliationApi: (payload: {
    project_uri: string
    limit_items: number
  }) => Promise<unknown>
  docFinalContextApi: (boqItemUri: string) => Promise<unknown>
  generatePaymentCertificateApi: (payload: Record<string, unknown>) => Promise<unknown>
  frequencyDashboardApi: (projectUri: string, limit: number) => Promise<unknown>
  generateRailPactInstructionApi: (payload: Record<string, unknown>) => Promise<unknown>
  paymentAuditTraceApi: (paymentId: string) => Promise<unknown>
  finalizeDocFinalApi: (payload: Record<string, unknown>) => Promise<unknown>
  bindSpatialUtxoApi: (payload: {
    utxo_id: string
    project_uri: string
    bim_id?: string
    label?: string
    coordinate?: Record<string, unknown>
  }) => Promise<unknown>
  spatialDashboardApi: (projectUri: string) => Promise<unknown>
  predictiveQualityAnalysisApi: (payload: Record<string, unknown>) => Promise<unknown>
  exportFinanceProofApi: (payload: Record<string, unknown>) => Promise<unknown>
  convertRwaAssetApi: (payload: Record<string, unknown>) => Promise<unknown>
  exportOmHandoverBundleApi: (payload: Record<string, unknown>) => Promise<unknown>
  registerOmEventApi: (payload: Record<string, unknown>) => Promise<unknown>
  generateNormEvolutionReportApi: (payload: Record<string, unknown>) => Promise<unknown>
}

function downloadBlob(blob: Blob, filename: string) {
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(href)
}

export function useProofDashboardController({
  activeTab,
  proj,
  projectDetailOpen,
  detailProject,
  showToast,
  listProofs,
  verifyProof,
  proofStatsApi,
  proofNodeTreeApi,
  boqRealtimeStatusApi,
  boqItemSovereignHistoryApi,
  boqReconciliationApi,
  docFinalContextApi,
  generatePaymentCertificateApi,
  frequencyDashboardApi,
  generateRailPactInstructionApi,
  paymentAuditTraceApi,
  finalizeDocFinalApi,
  bindSpatialUtxoApi,
  spatialDashboardApi,
  predictiveQualityAnalysisApi,
  exportFinanceProofApi,
  convertRwaAssetApi,
  exportOmHandoverBundleApi,
  registerOmEventApi,
  generateNormEvolutionReportApi,
}: UseProofDashboardControllerArgs) {
  const [proofRows, setProofRows] = useState<ProofRow[]>([])
  const [proofStats, setProofStats] = useState<ProofStats>({
    total: 0,
    by_type: {},
    by_action: {},
  })
  const [proofNodeRows, setProofNodeRows] = useState<ProofNodeRow[]>([])
  const [proofLoading, setProofLoading] = useState(false)
  const [proofVerifying, setProofVerifying] = useState<string | null>(null)
  const [paymentGenerating, setPaymentGenerating] = useState(false)
  const [paymentResult, setPaymentResult] = useState<any | null>(null)
  const [railpactSubmitting, setRailpactSubmitting] = useState(false)
  const [railpactResult, setRailpactResult] = useState<any | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditResult, setAuditResult] = useState<any | null>(null)
  const [frequencyLoading, setFrequencyLoading] = useState(false)
  const [frequencyResult, setFrequencyResult] = useState<any | null>(null)
  const [deliveryFinalizing, setDeliveryFinalizing] = useState(false)
  const [spatialLoading, setSpatialLoading] = useState(false)
  const [spatialDashboard, setSpatialDashboard] = useState<any | null>(null)
  const [aiRunning, setAiRunning] = useState(false)
  const [aiResult, setAiResult] = useState<any | null>(null)
  const [financeExporting, setFinanceExporting] = useState(false)
  const [rwaConverting, setRwaConverting] = useState(false)
  const [omExporting, setOmExporting] = useState(false)
  const [omEventSubmitting, setOmEventSubmitting] = useState(false)
  const [normEvolutionRunning, setNormEvolutionRunning] = useState(false)
  const [normEvolutionResult, setNormEvolutionResult] = useState<any | null>(null)
  const [lastOmRootProofId, setLastOmRootProofId] = useState('')
  const [boqRealtimeByProjectId, setBoqRealtimeByProjectId] = useState<Record<string, any>>({})
  const [boqRealtimeLoadingProjectId, setBoqRealtimeLoadingProjectId] = useState<string | null>(null)
  const [boqAuditByProjectId, setBoqAuditByProjectId] = useState<Record<string, any>>({})
  const [boqAuditLoadingProjectId, setBoqAuditLoadingProjectId] = useState<string | null>(null)
  const [boqProofPreview, setBoqProofPreview] = useState<any | null>(null)
  const [boqProofLoadingUri, setBoqProofLoadingUri] = useState<string | null>(null)
  const [boqSovereignPreview, setBoqSovereignPreview] = useState<any | null>(null)
  const [boqSovereignLoadingCode, setBoqSovereignLoadingCode] = useState<string | null>(null)

  useEffect(() => {
    if (!projectDetailOpen || !detailProject?.id || !detailProject.v_uri) return
    if (boqRealtimeByProjectId[detailProject.id]) return

    let cancelled = false
    const load = async () => {
      setBoqRealtimeLoadingProjectId(detailProject.id)
      try {
        const payload = await boqRealtimeStatusApi(detailProject.v_uri) as { ok?: boolean } | null
        if (cancelled) return
        if (payload?.ok) {
          setBoqRealtimeByProjectId((prev) => ({ ...prev, [detailProject.id as string]: payload }))
        }
      } catch {
        if (!cancelled) showToast('BOQ 实时进度加载失败')
      } finally {
        if (!cancelled) {
          setBoqRealtimeLoadingProjectId((current) => (current === detailProject.id ? null : current))
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [projectDetailOpen, detailProject?.id, detailProject?.v_uri, boqRealtimeByProjectId, boqRealtimeStatusApi, showToast])

  useEffect(() => {
    if (!projectDetailOpen || !detailProject?.id || !detailProject.v_uri) return
    if (boqAuditByProjectId[detailProject.id]) return

    let cancelled = false
    const load = async () => {
      setBoqAuditLoadingProjectId(detailProject.id)
      try {
        const payload = await boqReconciliationApi({
          project_uri: detailProject.v_uri,
          limit_items: 1000,
        }) as { ok?: boolean } | null
        if (cancelled) return
        if (payload?.ok) {
          setBoqAuditByProjectId((prev) => ({ ...prev, [detailProject.id as string]: payload }))
        }
      } catch {
        if (!cancelled) showToast('BOQ 主权审计对账加载失败')
      } finally {
        if (!cancelled) {
          setBoqAuditLoadingProjectId((current) => (current === detailProject.id ? null : current))
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [projectDetailOpen, detailProject?.id, detailProject?.v_uri, boqAuditByProjectId, boqReconciliationApi, showToast])

  useEffect(() => {
    if (!projectDetailOpen) {
      setBoqProofPreview(null)
      setBoqProofLoadingUri(null)
      setBoqSovereignPreview(null)
      setBoqSovereignLoadingCode(null)
    }
  }, [projectDetailOpen])

  useEffect(() => {
    if (activeTab !== 'proof' || !proj.id) return
    let cancelled = false
    setProofLoading(true)
    Promise.all([
      listProofs(proj.id),
      proofStatsApi(proj.id),
      proj.v_uri ? proofNodeTreeApi(proj.v_uri) : Promise.resolve(null),
    ]).then(([listRes, statsRes, treeRes]) => {
      if (cancelled) return
      const listPayload = listRes as { data?: ProofRow[] } | null
      const statsPayload = statsRes as {
        total?: number
        by_type?: Record<string, number>
        by_action?: Record<string, number>
      } | null
      const treePayload = treeRes as { data?: ProofNodeRow[] } | null

      setProofRows(listPayload?.data || [])
      setProofStats({
        total: Number(statsPayload?.total || 0),
        by_type: statsPayload?.by_type || {},
        by_action: statsPayload?.by_action || {},
      })
      setProofNodeRows(treePayload?.data || [])
    }).finally(() => {
      if (!cancelled) setProofLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [activeTab, proj.id, proj.v_uri, listProofs, proofStatsApi, proofNodeTreeApi])

  useEffect(() => {
    setPaymentResult(null)
    setRailpactResult(null)
    setAuditResult(null)
    setFrequencyResult(null)
    setSpatialDashboard(null)
    setAiResult(null)
    setNormEvolutionResult(null)
    setLastOmRootProofId('')
  }, [proj.id])

  useEffect(() => {
    if (activeTab !== 'proof' || !proj.v_uri) return
    let cancelled = false
    setFrequencyLoading(true)
    frequencyDashboardApi(proj.v_uri, 200).then((res) => {
      if (cancelled) return
      const payload = res as { ok?: boolean } | null
      if (payload?.ok) {
        setFrequencyResult(payload)
      }
    }).finally(() => {
      if (!cancelled) setFrequencyLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [activeTab, proj.v_uri, frequencyDashboardApi])

  useEffect(() => {
    if (activeTab !== 'proof' || !proj.v_uri) return
    let cancelled = false
    setSpatialLoading(true)
    spatialDashboardApi(proj.v_uri).then((res) => {
      if (cancelled) return
      const payload = res as { ok?: boolean } | null
      if (payload?.ok) {
        setSpatialDashboard(payload)
      }
    }).finally(() => {
      if (!cancelled) setSpatialLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [activeTab, proj.v_uri, spatialDashboardApi])

  const handleOpenBoqProofChain = async (boqItemUri: string) => {
    if (!boqItemUri) return
    setBoqProofLoadingUri(boqItemUri)
    try {
      const payload = await docFinalContextApi(boqItemUri) as { ok?: boolean } | null
      if (payload?.ok) {
        setBoqProofPreview(payload)
      } else {
        showToast('未获取到该细目的 Proof 链上下文')
      }
    } catch {
      showToast('未获取到该细目的 Proof 链上下文')
    } finally {
      setBoqProofLoadingUri(null)
    }
  }

  const handleOpenBoqSovereignHistory = async (subitemCode: string) => {
    if (!detailProject?.v_uri || !subitemCode) return
    setBoqSovereignLoadingCode(subitemCode)
    try {
      const payload = await boqItemSovereignHistoryApi({
        project_uri: detailProject.v_uri,
        subitem_code: subitemCode,
        max_rows: 50000,
      }) as { ok?: boolean } | null
      if (payload?.ok) {
        setBoqSovereignPreview(payload)
      } else {
        showToast('未获取到该细目的主权历史')
      }
    } catch {
      showToast('未获取到该细目的主权历史')
    } finally {
      setBoqSovereignLoadingCode(null)
    }
  }

  const handleVerifyProof = async (proofId: string) => {
    setProofVerifying(proofId)
    const res = await verifyProof(proofId) as { valid?: boolean; chain_length?: number } | null
    if (res?.valid) {
      showToast(`Proof 校验通过（链长 ${res.chain_length ?? 0}）`)
    } else {
      showToast('Proof 校验失败或不存在')
    }
    setProofVerifying(null)
  }

  const handleGeneratePaymentCertificate = async (period: string) => {
    if (!proj.v_uri) return
    setPaymentGenerating(true)
    const payload = await generatePaymentCertificateApi({
      project_uri: proj.v_uri,
      period,
      project_name: proj.name,
      create_proof: true,
      enforce_dual_pass: true,
      executor_uri: 'v://executor/system/',
    }) as { ok?: boolean } | null
    if (payload?.ok) {
      setPaymentResult(payload)
      setAuditResult(null)
      showToast(`支付证书已生成：${String((payload as any).payment_id || '-')}`)
    } else {
      showToast('支付证书生成失败')
    }
    setPaymentGenerating(false)
  }

  const handleOpenAuditTrace = async (paymentId: string) => {
    if (!paymentId) return
    setAuditLoading(true)
    const payload = await paymentAuditTraceApi(paymentId) as { ok?: boolean } | null
    if (payload?.ok) {
      setAuditResult(payload)
      showToast(`审计穿透完成：节点 ${(payload as any).nodes?.length || 0}`)
    } else {
      showToast('审计穿透失败')
    }
    setAuditLoading(false)
  }

  const handleGenerateRailPactInstruction = async (paymentId: string) => {
    if (!paymentId) return
    setRailpactSubmitting(true)
    const payload = await generateRailPactInstructionApi({
      payment_id: paymentId,
      executor_uri: 'v://executor/owner/system/',
      auto_submit: false,
    }) as { ok?: boolean; instruction_id?: string } | null
    if (payload?.ok) {
      setRailpactResult(payload)
      showToast(`RailPact 指令已生成：${String(payload.instruction_id || '-')}`)
    } else {
      showToast('RailPact 支付指令生成失败')
    }
    setRailpactSubmitting(false)
  }

  const handleOpenVerifyNode = (proofId: string) => {
    if (!proofId) return
    const base = (window.location?.origin || '').replace(/\/$/, '')
    window.open(`${base}/v/${encodeURIComponent(proofId)}?trace=true`, '_blank', 'noopener,noreferrer')
  }

  const handleFinalizeDelivery = async () => {
    if (!proj.v_uri) return
    setDeliveryFinalizing(true)
    const pack = await finalizeDocFinalApi({
      project_uri: proj.v_uri,
      project_name: proj.name,
      include_unsettled: false,
      run_anchor_rounds: 1,
    }) as {
      blob: Blob
      filename?: string
      finalGitpegAnchor?: string
      rootHash?: string
    } | null
    if (pack?.blob) {
      downloadBlob(pack.blob, pack.filename || 'MASTER-DSP.qcdsp')
      showToast(`竣工包交付完成，RootHash: ${pack.rootHash || '-'}，FinalAnchor: ${pack.finalGitpegAnchor || 'pending'}`)
    } else {
      showToast('竣工包交付失败')
    }
    setDeliveryFinalizing(false)
  }

  const refreshSpatialDashboard = async () => {
    if (!proj.v_uri) return
    setSpatialLoading(true)
    const payload = await spatialDashboardApi(proj.v_uri) as { ok?: boolean } | null
    if (payload?.ok) {
      setSpatialDashboard(payload)
    } else {
      showToast('空间孪生看板刷新失败')
    }
    setSpatialLoading(false)
  }

  const handleBindSpatial = async (payload: {
    utxo_id: string
    project_uri: string
    bim_id?: string
    label?: string
    coordinate?: Record<string, unknown>
  }) => {
    if (!payload.utxo_id) return
    const res = await bindSpatialUtxoApi(payload) as { ok?: boolean } | null
    if (res?.ok) {
      showToast('空间指纹绑定成功')
      await refreshSpatialDashboard()
    } else {
      showToast('空间指纹绑定失败')
    }
  }

  const handleRunPredictive = async (payload: {
    nearThresholdRatio: number
    minSamples: number
    applyDynamicGate: boolean
    defaultCriticalThreshold: number
  }) => {
    if (!proj.v_uri) return
    setAiRunning(true)
    const res = await predictiveQualityAnalysisApi({
      project_uri: proj.v_uri,
      near_threshold_ratio: payload.nearThresholdRatio,
      min_samples: payload.minSamples,
      apply_dynamic_gate: payload.applyDynamicGate,
      default_critical_threshold: payload.defaultCriticalThreshold,
    }) as { ok?: boolean } | null
    if (res?.ok) {
      setAiResult(res)
      showToast(`AI 治理分析完成，预警 ${Number((res as any).warning_count || 0)} 条`)
      await refreshSpatialDashboard()
    } else {
      showToast('AI 治理分析失败')
    }
    setAiRunning(false)
  }

  const handleExportFinanceProof = async (payload: {
    paymentId: string
    bankCode: string
    runAnchorRounds: number
  }) => {
    if (!payload.paymentId) return
    setFinanceExporting(true)
    const pack = await exportFinanceProofApi({
      payment_id: payload.paymentId,
      bank_code: payload.bankCode,
      run_anchor_rounds: payload.runAnchorRounds,
    }) as {
      blob: Blob
      filename?: string
      proofId?: string
      gitpegAnchor?: string
    } | null
    if (pack?.blob) {
      downloadBlob(pack.blob, pack.filename || 'FINANCE-PROOF.qcfp')
      showToast(`金融凭证导出完成，Proof: ${pack.proofId || '-'}，Anchor: ${pack.gitpegAnchor || 'pending'}`)
    } else {
      showToast('金融凭证导出失败')
    }
    setFinanceExporting(false)
  }

  const handleConvertRwaAsset = async (payload: {
    boqGroupId: string
    bankCode: string
    runAnchorRounds: number
  }) => {
    if (!proj.v_uri || !payload.boqGroupId) return
    setRwaConverting(true)
    const pack = await convertRwaAssetApi({
      project_uri: proj.v_uri,
      boq_group_id: payload.boqGroupId,
      project_name: proj.name,
      bank_code: payload.bankCode,
      run_anchor_rounds: payload.runAnchorRounds,
    }) as {
      blob: Blob
      filename?: string
      proofId?: string
      gitpegAnchor?: string
    } | null
    if (pack?.blob) {
      downloadBlob(pack.blob, pack.filename || 'RWA-ASSET.qcrwa')
      showToast(`RWA 资产转换完成，Proof: ${pack.proofId || '-'}，Anchor: ${pack.gitpegAnchor || 'pending'}`)
    } else {
      showToast('RWA 资产转换失败')
    }
    setRwaConverting(false)
  }

  const handleExportOmBundle = async (payload: {
    omOwnerUri: string
    runAnchorRounds: number
  }) => {
    if (!proj.v_uri) return
    setOmExporting(true)
    const pack = await exportOmHandoverBundleApi({
      project_uri: proj.v_uri,
      project_name: proj.name,
      om_owner_uri: payload.omOwnerUri,
      run_anchor_rounds: payload.runAnchorRounds,
    }) as {
      blob: Blob
      filename?: string
      omRootProofId?: string
      omGitpegAnchor?: string
      omRootUri?: string
    } | null
    if (pack?.blob) {
      downloadBlob(pack.blob, pack.filename || 'OM-HANDOVER.zip')
      if (pack.omRootProofId) {
        setLastOmRootProofId(pack.omRootProofId)
      }
      showToast(`运维移交包导出完成，OM Root: ${pack.omRootUri || '-'}，Anchor: ${pack.omGitpegAnchor || 'pending'}`)
    } else {
      showToast('运维移交包导出失败')
    }
    setOmExporting(false)
  }

  const handleRegisterOmEvent = async (payload: {
    omRootProofId: string
    title: string
    eventType: string
  }) => {
    if (!payload.omRootProofId || !payload.title) return
    setOmEventSubmitting(true)
    const res = await registerOmEventApi({
      om_root_proof_id: payload.omRootProofId,
      title: payload.title,
      event_type: payload.eventType,
      executor_uri: 'v://operator/om/default',
    }) as { ok?: boolean; event_proof_id?: string } | null
    if (res?.ok) {
      showToast(`运维事件挂载完成：${String(res.event_proof_id || '-')}`)
    } else {
      showToast('运维事件挂载失败')
    }
    setOmEventSubmitting(false)
  }

  const handleGenerateNormEvolution = async (payload: {
    minSamples: number
    nearThresholdRatio: number
    anonymize: boolean
  }) => {
    setNormEvolutionRunning(true)
    const res = await generateNormEvolutionReportApi({
      project_uris: proj.v_uri ? [proj.v_uri] : [],
      min_samples: payload.minSamples,
      near_threshold_ratio: payload.nearThresholdRatio,
      anonymize: payload.anonymize,
      create_proof: true,
    }) as { ok?: boolean } | null
    if (res?.ok) {
      setNormEvolutionResult(res)
      showToast(`规范演进报告生成完成，发现 ${Number((res as any).report?.finding_count || 0)} 条`)
    } else {
      showToast('规范演进报告生成失败')
    }
    setNormEvolutionRunning(false)
  }

  return {
    proofRows,
    proofStats,
    proofNodeRows,
    proofLoading,
    proofVerifying,
    paymentGenerating,
    paymentResult,
    railpactSubmitting,
    railpactResult,
    auditLoading,
    auditResult,
    frequencyLoading,
    frequencyResult,
    deliveryFinalizing,
    spatialLoading,
    spatialDashboard,
    aiRunning,
    aiResult,
    financeExporting,
    rwaConverting,
    omExporting,
    omEventSubmitting,
    normEvolutionRunning,
    normEvolutionResult,
    lastOmRootProofId,
    boqRealtime: detailProject?.id ? boqRealtimeByProjectId[detailProject.id] || null : null,
    boqRealtimeLoading: boqRealtimeLoadingProjectId === detailProject?.id,
    boqAudit: detailProject?.id ? boqAuditByProjectId[detailProject.id] || null : null,
    boqAuditLoading: boqAuditLoadingProjectId === detailProject?.id,
    boqProofPreview,
    boqProofLoadingUri,
    boqSovereignPreview,
    boqSovereignLoadingCode,
    handleOpenBoqProofChain,
    handleOpenBoqSovereignHistory,
    handleVerifyProof,
    handleGeneratePaymentCertificate,
    handleOpenAuditTrace,
    handleGenerateRailPactInstruction,
    handleOpenVerifyNode,
    handleFinalizeDelivery,
    refreshSpatialDashboard,
    handleBindSpatial,
    handleRunPredictive,
    handleExportFinanceProof,
    handleConvertRwaAsset,
    handleExportOmBundle,
    handleRegisterOmEvent,
    handleGenerateNormEvolution,
  }
}
