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
  live_boq: 'Import the 400-chapter ledger and finish Genesis anchoring',
  specdict_qcgate: 'Bind gates to SpecDict and publish a version',
  docpeg_documents: 'Complete signing and attach DocPeg documents',
  field_execution_qcspec: 'Submit at least one field QC execution proof',
  labpeg_dual_gate: 'Record LabPeg evidence and clear missing inspections',
  finance_erp_railpact: 'Generate payment certificate and RailPact instruction',
  audit_reconciliation: 'Run sovereign reconciliation and confirm zero illegal attempts',
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
    { id: 'ledger', label: '0# Ledger Genesis', subtitle: project.active?.uri || '-', tone: 'neutral' },
    { id: 'qcspec', label: 'QCSpec proof', subtitle: asset.sampleId || '-', tone: audit.gateStats.qcCompliant ? 'ok' : 'warn' },
    { id: 'lab', label: 'LabPeg proof', subtitle: audit.gateStats.labLatestPass || 'pending', tone: audit.gateStats.labQualified ? 'ok' : 'warn' },
    { id: 'docpeg', label: 'DocPeg report', subtitle: asset.verifyUri || '-', tone: asset.verifyUri ? 'ok' : 'neutral' },
    { id: 'hash', label: 'Final total_proof_hash', subtitle: asset.totalHash || '-', tone: asset.totalHash ? 'ok' : 'neutral' },
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
      { value: 'main_beam', label: 'Main Beam' },
      { value: 'pier', label: 'Pier' },
      { value: 'guardrail', label: 'Guardrail' },
      { value: 'slab', label: 'Slab' },
    ]
    if (!base.some((item) => item.value === ui.compType) && ui.compType) {
      base.unshift({
        value: ui.compType,
        label: ui.compType === 'generic' ? 'Unmapped component' : `Other (${ui.compType})`,
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
