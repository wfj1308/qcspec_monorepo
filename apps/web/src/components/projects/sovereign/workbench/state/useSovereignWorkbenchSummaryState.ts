import { useMemo } from 'react'

import { buildProjectSovereignValue } from '../../contextBuilders'
import type { ProjectSovereignContextValue } from '../../SovereignContext'
import type {
  ActiveGenesisSummary,
  EvidenceCenterPayload,
  EvidenceGraphNode,
  GateStats,
  NormResolutionState,
  SpuBadge,
  SpuKind,
  SummaryMetrics,
  TreeNode,
} from '../../types'

const READINESS_ACTION: Record<string, string> = {
  live_boq: '导入 400 章台账并完成 Genesis 锚定',
  specdict_qcgate: '将闸门规则绑定到 SpecDict 并发布版本',
  docpeg_documents: '完成签认并挂接 DocPeg 文档',
  field_execution_qcspec: '至少提交一次现场质检执行存证',
  labpeg_dual_gate: '补齐 LabPeg 证据并清理缺检项',
  finance_erp_railpact: '生成支付凭证并下发 RailPact 指令',
  audit_reconciliation: '执行主权对账并确认非法尝试为零',
}

type Args = {
  project: {
    projectUri: string
    apiProjectUri: string
    displayProjectUri: string
    projectId: string
    active: TreeNode | null
    activeUri: string
    activePath: string
    boundSpu: string
    isContractSpu: boolean
    spuKind: SpuKind
    spuBadge: SpuBadge
    stepLabel: string
    lifecycle: ProjectSovereignContextValue['project']['lifecycle']
    nodePathMap: Map<string, string>
  }
  identity: {
    dtoRole: string
    roleAllowed: boolean
    executorDid: string
    supervisorDid: string
    ownerDid: string
  }
  asset: {
    summary: SummaryMetrics
    activeGenesisSummary: ActiveGenesisSummary
    baselineTotal: number
    availableTotal: number
    effectiveSpent: number
    effectiveClaimQtyValue: number
    inputProofId: string
    finalProofId: string
    totalHash: string
    verifyUri: string
    evidenceCenter: EvidenceCenterPayload | null
    sampleId: string
  }
  audit: {
    gateStats: GateStats
    gateReason: string
    exceedBalance: boolean
    snappegReady: boolean
    geoTemporalBlocked: boolean
    normResolution: NormResolutionState
    disputeOpen: boolean
    disputeProof: string
    archiveLocked: boolean
  }
  ui: {
    compType: string
  }
}

export function useSovereignWorkbenchSummaryState({
  project,
  identity,
  asset,
  audit,
  ui,
}: Args) {
  const traceOverlayNodes = useMemo<EvidenceGraphNode[]>(() => ([
    { id: 'ledger', label: '0# 账本基线', subtitle: project.active?.uri || '-', tone: 'neutral' },
    { id: 'qcspec', label: 'QCSpec 存证', subtitle: asset.sampleId || '-', tone: audit.gateStats.qcCompliant ? 'ok' : 'warn' },
    { id: 'lab', label: 'LabPeg 存证', subtitle: audit.gateStats.labLatestPass || '待生成', tone: audit.gateStats.labQualified ? 'ok' : 'warn' },
    { id: 'docpeg', label: 'DocPeg 报告', subtitle: asset.verifyUri || '-', tone: asset.verifyUri ? 'ok' : 'neutral' },
    { id: 'hash', label: '最终总存证哈希', subtitle: asset.totalHash || '-', tone: asset.totalHash ? 'ok' : 'neutral' },
  ]), [
    asset.sampleId,
    asset.totalHash,
    asset.verifyUri,
    audit.gateStats.labLatestPass,
    audit.gateStats.labQualified,
    audit.gateStats.qcCompliant,
    project.active?.uri,
  ])

  const componentTypeOptions = useMemo<Array<{ value: string; label: string }>>(() => {
    const base = [
      { value: 'main_beam', label: '主梁' },
      { value: 'pier', label: '桥墩' },
      { value: 'guardrail', label: '护栏' },
      { value: 'slab', label: '板体' },
    ]
    if (!base.some((item) => item.value === ui.compType) && ui.compType) {
      base.unshift({
        value: ui.compType,
        label: ui.compType === 'generic' ? '未映射构件' : `其他（${ui.compType}）`,
      })
    }
    return base
  }, [ui.compType])

  const sovereignValue = useMemo(() => buildProjectSovereignValue({
    project: {
      projectUri: project.projectUri,
      apiProjectUri: project.apiProjectUri,
      displayProjectUri: project.displayProjectUri,
      projectId: project.projectId,
      active: project.active,
      activeUri: project.activeUri,
      activePath: project.activePath,
      boundSpu: project.boundSpu,
      isContractSpu: project.isContractSpu,
      spuKind: project.spuKind,
      spuBadge: project.spuBadge,
      stepLabel: project.stepLabel,
      lifecycle: project.lifecycle,
      nodePathMap: project.nodePathMap,
    },
    identity: {
      dtoRole: identity.dtoRole,
      roleAllowed: identity.roleAllowed,
      executorDid: identity.executorDid,
      supervisorDid: identity.supervisorDid,
      ownerDid: identity.ownerDid,
    },
    asset: {
      summary: asset.summary,
      activeGenesisSummary: asset.activeGenesisSummary,
      baselineTotal: asset.baselineTotal,
      availableTotal: asset.availableTotal,
      effectiveSpent: asset.effectiveSpent,
      effectiveClaimQtyValue: asset.effectiveClaimQtyValue,
      inputProofId: asset.inputProofId,
      finalProofId: asset.finalProofId,
      totalHash: asset.totalHash,
      verifyUri: asset.verifyUri,
      evidenceCenter: asset.evidenceCenter,
    },
    audit: {
      gateStats: audit.gateStats,
      gateReason: audit.gateReason,
      exceedBalance: audit.exceedBalance,
      snappegReady: audit.snappegReady,
      geoTemporalBlocked: audit.geoTemporalBlocked,
      normResolution: audit.normResolution,
      disputeOpen: audit.disputeOpen,
      disputeProof: audit.disputeProof,
      disputeArbiterRole: 'OWNER / THIRD_PARTY',
      archiveLocked: audit.archiveLocked,
    },
  }), [
    asset.activeGenesisSummary,
    asset.availableTotal,
    asset.baselineTotal,
    asset.effectiveClaimQtyValue,
    asset.effectiveSpent,
    asset.evidenceCenter,
    asset.finalProofId,
    asset.inputProofId,
    asset.summary,
    asset.totalHash,
    asset.verifyUri,
    audit.archiveLocked,
    audit.disputeOpen,
    audit.disputeProof,
    audit.exceedBalance,
    audit.gateReason,
    audit.gateStats,
    audit.geoTemporalBlocked,
    audit.normResolution,
    audit.snappegReady,
    identity.dtoRole,
    identity.executorDid,
    identity.ownerDid,
    identity.roleAllowed,
    identity.supervisorDid,
    project.active,
    project.activePath,
    project.activeUri,
    project.apiProjectUri,
    project.boundSpu,
    project.displayProjectUri,
    project.isContractSpu,
    project.lifecycle,
    project.nodePathMap,
    project.projectId,
    project.projectUri,
    project.spuBadge,
    project.spuKind,
    project.stepLabel,
  ])

  return {
    traceOverlayNodes,
    readinessAction: READINESS_ACTION,
    componentTypeOptions,
    sovereignValue,
  }
}

