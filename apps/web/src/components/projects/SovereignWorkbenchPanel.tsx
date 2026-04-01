
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { GlobalWorkerOptions } from 'pdfjs-dist/legacy/build/pdf'
import pdfWorkerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'
import { Card } from '../ui'
import { useProof } from '../../hooks/api/proof'
import { useAuthStore, useUIStore } from '../../store'
import {
  buildWorkbenchSectionsProps,
} from './sovereign/panelPropsBuilders'
import SovereignWorkbenchSections from './sovereign/SovereignWorkbenchSections'
import { useSovereignAdvancedOps } from './sovereign/useSovereignAdvancedOps'
import { useSovereignArView } from './sovereign/useSovereignArView'
import { useSovereignEvidencePanelState } from './sovereign/useSovereignEvidencePanelState'
import { useSovereignEvidenceDerivedState } from './sovereign/useSovereignEvidenceDerivedState'
import { useSovereignContextActions } from './sovereign/useSovereignContextActions'
import { useSovereignGeoSpecdictState } from './sovereign/useSovereignGeoSpecdictState'
import { useSovereignWorkbenchInputState } from './sovereign/useSovereignWorkbenchInputState'
import { useSovereignWorkbenchSummaryState } from './sovereign/useSovereignWorkbenchSummaryState'
import {
  useSovereignProofChainInputs,
  useSovereignProofChainStatus,
} from './sovereign/useSovereignProofChainState'
import {
  useSovereignActiveGenesisSummary,
  useSovereignTreeDerivedState,
} from './sovereign/useSovereignTreeDerivedState'
import { useSovereignTreeImport } from './sovereign/useSovereignTreeImport'
import { useSovereignConsensusState } from './sovereign/useSovereignConsensusState'
import { useSovereignTripFlow } from './sovereign/useSovereignTripFlow'
import { useSovereignWorkbenchActions } from './sovereign/useSovereignWorkbenchActions'
import {
  useDocPegPreviewEffects,
  useGeoFenceToastEffect,
  useWorkspaceSnapshotEffect,
} from './sovereign/useSovereignWorkbenchEffects'
import {
  useActiveNodeBroadcastEffect,
  useDisputeProofAutofillEffect,
  useLabRefreshEffect,
  useNowTickEffect,
  useSovereignVerifyAssets,
} from './sovereign/useSovereignWorkbenchSupport'
import { useSovereignWorkbenchViewState } from './sovereign/useSovereignWorkbenchViewState'
import {
  describeSpecdictItem,
} from './sovereign/analysisUtils'
import {
  downloadJson,
} from './sovereign/fileUtils'
import { NormEngineProvider } from './sovereign/NormEngine'
import type { SovereignWorkspaceSnapshot, SovereignWorkspaceView } from './sovereign/SovereignProjectContext'
import { ProjectSovereignProvider } from './sovereign/SovereignContext'
import {
  buildMeasurementPayload,
  sanitizeMeasuredInput,
  toChineseCompType,
  toChineseMetricLabel,
} from './sovereign/spuUtils'
import {
  formatNumber,
  toApiUri,
  toDisplayUri,
} from './sovereign/treeUtils'
import type { EvidenceCenterPayload } from './sovereign/types'
import { useAuditFinalizeActions } from './sovereign/useAuditFinalizeActions'
import { useEvidenceCenterLoader } from './sovereign/useEvidenceCenterLoader'
import { useEvidenceEventLogs } from './sovereign/useEvidenceEventLogs'
import { useEvidenceCenterView } from './sovereign/useEvidenceCenterView'
import { useEvidenceFiles } from './sovereign/useEvidenceFiles'
import { useOfflinePackets } from './sovereign/useOfflinePackets'
import { useScanConfirmAction } from './sovereign/useScanConfirmAction'
import { useScanEntryState } from './sovereign/useScanEntryState'
import { useSpecdictArActions } from './sovereign/useSpecdictArActions'
import { useSovereignSession } from './sovereign/useSovereignSession'
import {
  buildWorkbenchDisplayTexts,
  OFFLINE_KEY,
  WORKBENCH_FRAME_STYLE_TEXT,
  WORKBENCH_GRID_OVERLAY_STYLE,
  WORKBENCH_STYLES,
} from './sovereign/workbenchConfig'

type Props = {
  project: { id?: string; v_uri?: string; name?: string } | null
  workspaceView?: SovereignWorkspaceView
  onNavigateView?: (view: SovereignWorkspaceView) => void
  onContextChange?: (snapshot: SovereignWorkspaceSnapshot) => void
}

try {
  GlobalWorkerOptions.workerSrc = pdfWorkerUrl
} catch {
  // ignore worker setup failures in non-browser env
}

function _asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function escapePdfText(input: string): string {
  return String(input || '').replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)').replace(/\r?\n/g, ' ')
}

function buildDraftPdfBase64(lines: string[]): string {
  const safeLines = lines.filter(Boolean).map((line) => escapePdfText(line))
  const content = safeLines
    .map((line, idx) => {
      const y = 720 - idx * 16
      return `BT /F1 12 Tf 72 ${y} Td (${line}) Tj ET`
    })
    .join('\n')
  const encoder = new TextEncoder()
  const header = '%PDF-1.4\n'
  const obj1 = '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
  const obj2 = '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
  const obj3 = '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n'
  const contentBytes = encoder.encode(content)
  const obj4 = `4 0 obj\n<< /Length ${contentBytes.length} >>\nstream\n${content}\nendstream\nendobj\n`
  const obj5 = '5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'
  const objects = [obj1, obj2, obj3, obj4, obj5]
  const offsets: number[] = [0]
  let cursor = encoder.encode(header).length
  for (const obj of objects) {
    offsets.push(cursor)
    cursor += encoder.encode(obj).length
  }
  let xref = `xref\n0 ${objects.length + 1}\n`
  xref += '0000000000 65535 f \n'
  for (let i = 1; i < offsets.length; i += 1) {
    xref += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`
  }
  const trailer = `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${cursor}\n%%EOF`
  const pdf = header + objects.join('') + xref + trailer
  const bytes = encoder.encode(pdf)
  let binary = ''
  bytes.forEach((b) => { binary += String.fromCharCode(b) })
  return btoa(binary)
}

export default function SovereignWorkbenchPanel({
  project,
  workspaceView = 'trip',
  onNavigateView,
  onContextChange,
}: Props) {
  const projectUri = String(project?.v_uri || '')
  const apiProjectUri = toApiUri(projectUri)
  const displayProjectUri = projectUri || toDisplayUri(apiProjectUri)
  const projectId = String(project?.id || '')
  const { showToast } = useUIStore()
  const dtoRole = useAuthStore((s) => String(s.user?.dto_role || 'PUBLIC').toUpperCase())
  const forcedBoqProjectUri = displayProjectUri ? displayProjectUri.replace(/\/$/, '') : 'v://cn.zhongbei/highway'
  const forcedBoqRootBase = `${forcedBoqProjectUri}/boq`
  const apiBoqRootBase = apiProjectUri ? `${apiProjectUri.replace(/\/$/, '')}/boq` : toApiUri(forcedBoqRootBase)
  const {
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    smuNodeContext,
    smuExecute,
    smuSign,
    tripGenerateDoc,
    smuFreeze,
    smuRetryErpnext,
    boqRealtimeStatus,
    evidenceCenterEvidence,
    publicVerifyDetail,
    downloadEvidenceCenterZip,
    triproleExecute,
    applyVariationDelta,
    scanConfirmSignature,
    replayOfflinePackets,
    exportDocFinal,
    finalizeDocFinal,
    unitMerkleRoot,
    projectReadinessCheck,
    specdictEvolve,
    specdictExport,
    arOverlay,
  } = useProof()

  const boqFileRef = useRef<HTMLInputElement | null>(null)
  const evidenceFileRef = useRef<HTMLInputElement | null>(null)
  const offlineImportRef = useRef<HTMLInputElement | null>(null)
  const previewScrollRef = useRef<HTMLDivElement | null>(null)
  const pdfCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const contractorAnchorRef = useRef<HTMLDivElement | null>(null)
  const supervisorAnchorRef = useRef<HTMLDivElement | null>(null)
  const ownerAnchorRef = useRef<HTMLDivElement | null>(null)
  const autoRejectRef = useRef('')
  const [ctx, setCtx] = useState<Record<string, unknown> | null>(null)
  const [loadingCtx, setLoadingCtx] = useState(false)
  const [contextError, setContextError] = useState('')
  const [form, setForm] = useState<Record<string, string>>({})
  const [compType, setCompType] = useState('generic')
  const [sampleId, setSampleId] = useState('')
  const [claimQty, setClaimQty] = useState('')

  const [executorDid, setExecutorDid] = useState('did:qcspec:contractor:demo')
  const [supervisorDid, setSupervisorDid] = useState('did:qcspec:supervisor:demo')
  const [ownerDid, setOwnerDid] = useState('did:qcspec:owner:demo')
  const [lat, setLat] = useState('30.657')
  const [lng, setLng] = useState('104.065')

  const {
    evidence,
    evidenceName,
    evidenceOpen,
    evidenceFocus,
    hashing,
    resetEvidence,
    onEvidence,
    openEvidencePreview,
    closeEvidencePreview,
  } = useEvidenceFiles()
  const [evidenceCenter, setEvidenceCenter] = useState<EvidenceCenterPayload | null>(null)
  const [evidenceCenterLoading, setEvidenceCenterLoading] = useState(false)
  const [evidenceCenterError, setEvidenceCenterError] = useState('')
  const [erpRetrying, setErpRetrying] = useState(false)
  const [erpRetryMsg, setErpRetryMsg] = useState('')
  const [fingerprintOpen, setFingerprintOpen] = useState(false)
  const [draftStamp, setDraftStamp] = useState('')
  const [disputeProofId, setDisputeProofId] = useState('')
  const [disputeResolutionNote, setDisputeResolutionNote] = useState('')
  const [disputeResult, setDisputeResult] = useState<'PASS' | 'REJECT'>('PASS')
  const [copiedMsg, setCopiedMsg] = useState('')
  const [traceOpen, setTraceOpen] = useState(false)
  const [docModalOpen, setDocModalOpen] = useState(false)
  const [pdfRenderError, setPdfRenderError] = useState('')
  const [pdfRenderLoading, setPdfRenderLoading] = useState(false)
  const [showAdvancedConsensus, setShowAdvancedConsensus] = useState(false)
  const [showAcceptanceAdvanced, setShowAcceptanceAdvanced] = useState(false)
  const [specdictProjectUris, setSpecdictProjectUris] = useState(apiProjectUri || displayProjectUri || '')
  const [specdictMinSamples, setSpecdictMinSamples] = useState('5')
  const [specdictNamespace, setSpecdictNamespace] = useState('v://global/templates')
  const [specdictCommit, setSpecdictCommit] = useState(false)
  const [arRadius, setArRadius] = useState('80')
  const [arLimit, setArLimit] = useState('50')
  const [p2pNodeId] = useState(() => `node-${Math.random().toString(16).slice(2, 8)}`)
  const [p2pPeers, setP2pPeers] = useState('')
  const [p2pAutoSync, setP2pAutoSync] = useState(true)
  const [p2pLastSync, setP2pLastSync] = useState('')
  const [docFinalPassphrase, setDocFinalPassphrase] = useState('')
  const [docFinalIncludeUnsettled, setDocFinalIncludeUnsettled] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [execRes, setExecRes] = useState<Record<string, unknown> | null>(null)
  const [signOpen, setSignOpen] = useState(false)
  const [signStep, setSignStep] = useState(0)
  const [signing, setSigning] = useState(false)
  const [signRes, setSignRes] = useState<Record<string, unknown> | null>(null)
  const [mockGenerating, setMockGenerating] = useState(false)
  const [mockDocRes, setMockDocRes] = useState<Record<string, unknown> | null>(null)
  const [consensusContractorValue, setConsensusContractorValue] = useState('')
  const [consensusSupervisorValue, setConsensusSupervisorValue] = useState('')
  const [consensusOwnerValue, setConsensusOwnerValue] = useState('')
  const [consensusAllowedDeviation, setConsensusAllowedDeviation] = useState('')
  const [consensusAllowedDeviationPct, setConsensusAllowedDeviationPct] = useState('')
  const [, setFreezeProof] = useState('')
  const [signFocus, setSignFocus] = useState<'contractor' | 'supervisor' | 'owner' | ''>('')
  const [deltaAmount, setDeltaAmount] = useState('')
  const [deltaReason, setDeltaReason] = useState('变更指令')
  const [applyingDelta, setApplyingDelta] = useState(false)
  const [variationRes, setVariationRes] = useState<Record<string, unknown> | null>(null)
  const [showAdvancedExecution, setShowAdvancedExecution] = useState(false)
  const [deltaModalOpen, setDeltaModalOpen] = useState(false)
  const [nowTick, setNowTick] = useState(Date.now())
  const {
    scanEntryLog,
    meshpegLog,
    formulaLog,
    gatewayLog,
    setScanEntryLog,
    setMeshpegLog,
    setFormulaLog,
    setGatewayLog,
    appendScanEntryLog,
    appendMeshpegLog,
    appendFormulaLog,
    appendGatewayLog,
    reconcileReplayResults,
  } = useEvidenceEventLogs()
  const {
    specdictLoading,
    specdictExporting,
    specdictRes,
    runSpecdictEvolve,
    runSpecdictExport,
    arLoading,
    arRes,
    runArOverlay,
  } = useSpecdictArActions({
    apiProjectUri,
    specdictProjectUris,
    specdictMinSamples,
    specdictNamespace,
    specdictCommit,
    lat,
    lng,
    arRadius,
    arLimit,
    specdictEvolve,
    specdictExport,
    arOverlay,
    showToast,
  })

  useNowTickEffect({
    setNowTick,
  })
  const {
    resetSelectionWorkspace,
    activateTreeNode,
    loadContext,
    retryErpnextPush,
  } = useSovereignContextActions({
    apiProjectUri,
    compType,
    sampleId,
    erpRetrying,
    resetEvidence,
    showToast,
    smuNodeContext,
    smuRetryErpnext,
    setCtx,
    setContextError,
    setForm,
    setCompType,
    setSampleId,
    setClaimQty,
    setLoadingCtx,
    setErpRetrying,
    setErpRetryMsg,
  })

  const {
    fileName,
    importing,
    importJobId,
    importProgress,
    importStatusText,
    importError,
    readinessLoading,
    readinessPercent,
    readinessOverall,
    readinessLayers,
    showRolePlaybook,
    setShowRolePlaybook,
    showLeftSummary,
    setShowLeftSummary,
    nodes,
    setNodes,
    expandedCodes,
    activeUri,
    treeQuery,
    setTreeQuery,
    byUri,
    byCode,
    roots,
    treeSearch,
    runReadinessCheck,
    refreshTreeFromServer,
    onSelectFile,
    loadBuiltinLedger400,
    importGenesis,
    selectNode,
    toggleExpanded,
  } = useSovereignTreeImport({
    apiProjectUri,
    displayProjectUri,
    forcedBoqRootBase,
    apiBoqRootBase,
    projectId,
    showToast,
    projectReadinessCheck,
    boqRealtimeStatus,
    smuImportGenesis,
    smuImportGenesisAsync,
    smuImportGenesisPreview,
    smuImportGenesisJobPublic,
    smuImportGenesisJobActivePublic,
    resetSelectionWorkspace,
    onActivateNode: activateTreeNode,
  })

  const {
    active,
    smuOptions,
    aggMap,
    summary,
  } = useSovereignTreeDerivedState({
    activeUri,
    byUri,
    nodes,
    byCode,
  })
  const sovereignSession = useSovereignSession({
    projectUri,
    apiProjectUri,
    displayProjectUri,
    projectId,
    nodes,
    byCode,
    active,
    ctx,
    execRes,
    signRes,
    dtoRole,
  })
  const {
    nodePathMap,
    activePath,
    boundSpu,
    isContractSpu,
    spuKind,
    spuBadge,
    stepLabel,
    roleAllowed,
    normResolution,
    lifecycle,
  } = sovereignSession
  useActiveNodeBroadcastEffect({
    activeCode: String(active?.code || ''),
    activeName: String(active?.name || ''),
    activeStatus: String(active?.status || ''),
    activeSpu: String(active?.spu || ''),
    activeUri: String(active?.uri || ''),
    activePath,
    displayProjectUri,
  })
  const {
    effectiveSchema,
    gateStats,
    offlineActorId,
  } = useSovereignWorkbenchInputState({
    ctx,
    active,
    boundSpu,
    isContractSpu,
    form,
    executorDid,
    p2pNodeId,
  })

  const {
    inputProofId,
    verifyUri,
    pdfB64,
    totalHash,
    scanConfirmUri,
    scanConfirmToken,
  } = useSovereignProofChainInputs({
    ctx,
    execRes,
    signRes,
    mockDocRes,
    evidenceCenter,
  })
  const {
    scanPayload,
    setScanPayload,
    scanDid,
    setScanDid,
    scanProofId,
    setScanProofId,
    scanRes,
    scanning,
    scanLockStage,
    scanLockProofId,
    doScanConfirm,
    closeScanLock,
  } = useScanConfirmAction({
    apiProjectUri,
    inputProofId,
    scanConfirmToken,
    lat,
    lng,
    scanConfirmSignature,
    showToast,
  })
  const {
    finalProofId,
    tripStage,
    finalProofReady,
  } = useSovereignProofChainStatus({
    signRes,
    execRes,
    scanRes,
    scanLockProofId,
    verifyUri,
  })
  const isGenesisView = workspaceView === 'genesis'
  const isTripView = workspaceView === 'trip'
  const isAuditView = workspaceView === 'audit'
  const {
    evidenceTimeline,
    evidenceDocs,
    evidenceItems,
    scanEntryItems,
    meshpegItems,
    formulaItems,
    gatewayItems,
    ledgerSnapshot,
    consensusDispute,
    latestEvidenceNode,
    utxoStatusText,
    docpegRisk,
    docpegRiskScore,
    effectiveRiskScore,
    evidenceCompletenessScore,
    settlementRiskScore,
    assetOrigin,
    assetOriginStatement,
    didReputation,
    didReputationScore,
    didReputationGrade,
    didSamplingMultiplier,
    didHighRiskList,
    sealingTrip,
    sealingPatternId,
    sealingScanHint,
    sealingRows,
    sealingMicrotext,
    disputeOpen,
    disputeProof,
    disputeProofShort,
    disputeConflict,
    disputeDeviation,
    disputeDeviationPct,
    disputeAllowedAbs,
    disputeAllowedPct,
    disputeValues,
  } = useSovereignEvidenceDerivedState({
    evidenceCenter,
    signRes,
    mockDocRes,
    activeStatus: String(active?.status || ''),
  })
  const {
    showAllScanEntries,
    setShowAllScanEntries,
    scanEntryLatest,
    scanChainBadge,
    scanEntryActiveOnly,
  } = useSovereignEvidencePanelState({
    activeUri: String(active?.uri || ''),
    scanEntryItems,
  })
  const {
    evidenceQuery,
    setEvidenceQuery,
    evidenceFilter,
    setEvidenceFilter,
    evidenceScope,
    setEvidenceScope,
    evidenceSmuId,
    setEvidenceSmuId,
    setEvidencePage,
    evidenceCenterFocus,
    evidenceCenterDocFocus,
    openEvidenceFocus,
    closeEvidenceFocus,
    openDocumentFocus,
    closeDocumentFocus,
    evidenceZipDownloading,
    filteredEvidenceItems,
    filteredDocs,
    erpReceiptDoc,
    evidencePageSafe,
    totalEvidencePages,
    evidenceItemsPaged,
    exportEvidenceCenter,
    exportEvidenceCenterCsv,
    downloadEvidenceCenterPackage,
  } = useEvidenceCenterView({
    activeCode: String(active?.code || ''),
    apiProjectUri,
    smuOptions,
    evidenceCenter,
    evidenceDocs,
    evidenceItems,
    evidenceTimeline,
    meshpegItems,
    formulaItems,
    gatewayItems,
    ledgerSnapshot,
    docpegRisk,
    didReputation,
    assetOrigin,
    assetOriginStatement,
    sealingTrip,
    totalHash,
    showToast,
    downloadEvidenceCenterZip,
  })
  useDisputeProofAutofillEffect({
    openProofId: String(consensusDispute.open_proof_id || ''),
    disputeProofId,
    setDisputeProofId,
  })
  const activeGenesisSummary = useSovereignActiveGenesisSummary({
    active,
    byCode,
    filteredDocs,
    gateStats,
    summary,
  })
  const {
    evidenceGraphNodes,
    templateDisplay,
    templatePath,
    templateSourceText,
    draftReady,
    previewPdfB64,
    previewIsDraft,
    pdfPage,
    activeSignMarker,
  } = useSovereignWorkbenchViewState({
    active,
    ctx,
    signRes,
    inputProofId,
    verifyUri,
    totalHash,
    filteredDocs,
    evidenceTimeline,
    gateStats: {
      qcCompliant: gateStats.qcCompliant,
      labLatestPass: gateStats.labLatestPass,
      labQualified: gateStats.labQualified,
    },
    signStep,
    draftStamp,
    executorDid,
    supervisorDid,
    ownerDid,
    pdfB64,
    signFocus,
    buildDraftPdfBase64,
  })
  const specBinding = normResolution.specBinding
  const gateBinding = normResolution.gateBinding
  const normRefs = normResolution.normRefs
  const {
    geoAnchor,
    geoDistance,
    temporalWindow,
    geoFenceActive,
    temporalBlocked,
    geoTemporalBlocked,
    specdictRuleTotal,
    specdictHighRisk,
    specdictBestPractice,
    specdictHighRiskItems,
    specdictBestPracticeItems,
    specdictSuccessPatterns,
    specdictWeightEntries,
    specdictBundleUri,
    gateReason,
    displayMeta,
    geoValid,
    geoFenceWarning,
    snappegReady,
    geoFenceStatusText,
    geoFormLocked,
    evidenceLabel,
    evidenceAccept,
    evidenceHint,
    finalPiecePrompt,
    arItems,
    isSpecBound,
  } = useSovereignGeoSpecdictState({
    active,
    ctx,
    lat,
    lng,
    nowTick,
    specdictRes,
    specdictNamespace,
    arRes,
    gateStats,
    form,
    execRes,
    isContractSpu,
    evidence,
    specBinding,
    gateBinding,
  })
  const {
    baselineTotal,
    availableTotal,
    effectiveSpent,
    claimQtyProvided,
    measuredQtyValue,
    effectiveClaimQtyValue,
    consensusBaseValueText,
    consensusConflict,
    consensusMinValueText,
    consensusMaxValueText,
    consensusDeviationText,
    consensusDeviationPercentText,
    consensusAllowedAbsText,
    consensusAllowedPctText,
    consensusConflictSummary,
    exceedBalance,
    deltaSuggest,
    exceedTotalText,
  } = useSovereignConsensusState({
    summary,
    claimQty,
    form,
    effectiveSchema,
    isContractSpu,
    consensus: {
      contractorValue: consensusContractorValue,
      supervisorValue: consensusSupervisorValue,
      ownerValue: consensusOwnerValue,
      allowedDeviation: consensusAllowedDeviation,
      allowedDeviationPct: consensusAllowedDeviationPct,
    },
    identity: {
      executorDid,
      supervisorDid,
      ownerDid,
    },
    context: {
      apiProjectUri,
      activeUri: String(active?.uri || ''),
    },
    helpers: {
      formatNumber,
    },
  })
  const {
    submitTrip,
    submitTripMock,
    recordRejectTrip,
    doSign,
    applyDelta,
  } = useSovereignTripFlow({
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
    tripState: {
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
    },
    onMockDocReady: () => setDocModalOpen(true),
  })

  useLabRefreshEffect({
    labQualified: gateStats.labQualified,
    activeIsLeaf: Boolean(active?.isLeaf),
    activeUri,
    apiProjectUri,
    isContractSpu,
    sampleId,
    loadingCtx,
    compType,
    loadContext,
  })

  const { loadEvidenceCenter } = useEvidenceCenterLoader({
    apiProjectUri,
    activeCode: String(active?.code || ''),
    activeIsLeaf: Boolean(active?.isLeaf),
    activeUri: String(active?.uri || ''),
    evidenceScope,
    evidenceSmuId,
    finalProofId,
    inputProofId,
    evidenceCenterEvidence,
    publicVerifyDetail,
    showToast,
    setEvidenceCenter,
    setEvidenceCenterLoading,
    setEvidenceCenterError,
    scanEntryLog,
    meshpegLog,
    formulaLog,
    gatewayLog,
    setScanEntryLog,
    setMeshpegLog,
    setFormulaLog,
    setGatewayLog,
  })
  const {
    offlinePackets,
    offlineType,
    setOfflineType,
    offlineReplay,
    offlineImporting,
    offlineImportName,
    offlineSyncConflicts,
    isOnline,
    queueOfflinePacket,
    clearOfflinePackets,
    exportOfflinePackets,
    importOfflinePackets,
    simulateP2PSync,
  } = useOfflinePackets({
    storageKey: OFFLINE_KEY,
    autoReplayEnabled: p2pAutoSync,
    replayDefaultExecutorUri: apiProjectUri ? `${apiProjectUri.replace(/\/$/, '')}/role/contractor/mobile/` : '',
    replayOfflinePackets,
    onReplayResults: reconcileReplayResults,
    onReplayPatched: loadEvidenceCenter,
    onSyncRecorded: (iso) => setP2pLastSync(iso),
    showToast,
  })
  const offlineCount = offlinePackets.length
  const {
    disputeResolving,
    disputeResolveRes,
    resolveDispute,
    docFinalExporting,
    docFinalFinalizing,
    docFinalRes,
    archiveLocked,
    exportProjectDocFinal,
    finalizeProjectDocFinal,
    assetAppraising,
    assetAppraisal,
    buildAssetAppraisal,
  } = useAuditFinalizeActions({
    apiProjectUri,
    projectName: String(project?.name || ''),
    ownerDid,
    lat,
    lng,
    disputeProofId,
    disputeResolutionNote,
    disputeResult,
    docFinalPassphrase,
    docFinalIncludeUnsettled,
    activeUri: String(active?.uri || ''),
    finalProofReady,
    consensusConflict,
    disputeOpen,
    docpegRiskScore,
    totalHash,
    evidenceCount: evidenceItems.length,
    documentCount: evidenceDocs.length,
    finalProofId,
    inputProofId,
    triproleExecute,
    exportDocFinal,
    finalizeDocFinal,
    loadEvidenceCenter,
    showToast,
  })
  useWorkspaceSnapshotEffect({
    onContextChange,
    activePath,
    displayProjectUri,
    lifecycle,
    activeCode: String(active?.code || ''),
    activeStatus: String(active?.status || ''),
    totalHash: String(totalHash || ''),
    verifyUri: String(verifyUri || ''),
    finalProofReady,
    isOnline,
    offlineQueueSize: offlinePackets.length,
    disputeOpen: Boolean(_asDict(evidenceCenter?.consensusDispute || {}).open),
    disputeProof: String(_asDict(evidenceCenter?.consensusDispute || {}).open_proof_id || _asDict(evidenceCenter?.consensusDispute || {}).latest_proof_id || ''),
    archiveLocked,
  })

  useGeoFenceToastEffect({
    geoFenceActive,
    activeUri: String(active?.uri || ''),
    geoTemporalBlocked,
    geoDistance,
    temporalBlocked,
    geoRadiusM: geoAnchor?.radiusM,
    showToast,
  })

  const {
    arFocus,
    arFullscreen,
    arFilterMax,
    arItemsSorted,
    arFilteredItems,
    arPrimary,
    setArFilterMax,
    openArFocus,
    closeArFocus,
    openArFullscreen,
    closeArFullscreen,
    selectArFullscreenItem,
    jumpToArItem,
  } = useSovereignArView({
    arItems,
    byCode,
    byUri,
    selectNode,
    showToast,
  })

  useDocPegPreviewEffects({
    signRes,
    setScanProofId,
    pdfB64,
    setDocModalOpen,
    draftReady,
    draftStamp,
    setDraftStamp,
    activeUri: String(active?.uri || ''),
    previewPdfB64,
    pdfPage,
    pdfCanvasRef,
    setPdfRenderError,
    setPdfRenderLoading,
    activeSignMarker,
    previewScrollRef,
  })

  const {
    qrSrc,
    docFinalVerifyBaseUrl,
    docFinalAuditUrl,
    docFinalQrSrc,
  } = useSovereignVerifyAssets({
    mockDocRes,
    verifyUri,
    projectId,
  })
  const {
    scrollToSign,
    copyText,
    sealOfflinePacket,
    enqueueScanEntryPacket,
    enqueueTriprolePacket,
  } = useSovereignWorkbenchActions({
    sign: {
      setSignFocus,
      contractorAnchorRef,
      supervisorAnchorRef,
      ownerAnchorRef,
    },
    clipboard: {
      setCopiedMsg,
      showToast,
    },
    offline: {
      activeUri: String(active?.uri || ''),
      apiProjectUri,
      compType,
      deltaAmount,
      deltaReason,
      evidence,
      executorDid,
      form,
      inputProofId,
      lat,
      lng,
      offlineActorId,
      offlineType,
      queueOfflinePacket,
      sampleId,
    },
    scanEntry: {
      activeUri: String(active?.uri || ''),
      apiProjectUri,
      inputProofId,
      executorDid,
      lat,
      lng,
      offlineActorId,
      queueOfflinePacket,
      geoDistance,
      geoRadiusM: geoAnchor?.radiusM,
      temporalWindow,
    },
    triprole: {
      activeUri: String(active?.uri || ''),
      apiProjectUri,
      inputProofId,
      executorDid,
      lat,
      lng,
      offlineActorId,
      queueOfflinePacket,
    },
  })

  const {
    scanEntryAt,
    scanEntryStatus,
    scanEntryToken,
    scanEntryTokenHash,
    scanEntryRequired,
    setScanEntryToken,
    setScanEntryRequired,
    handleScanEntry,
  } = useScanEntryState({
    activeUri: String(active?.uri || ''),
    geoTemporalBlocked,
    lat,
    lng,
    showToast,
    enqueueScanEntryPacket,
    appendScanEntryLog,
    loadEvidenceCenter,
  })

  const {
    showFingerprintAdvanced,
    setShowFingerprintAdvanced,
    unitProofId,
    setUnitProofId,
    unitMaxRows,
    setUnitMaxRows,
    unitRes,
    unitLoading,
    unitVerifying,
    unitVerifyMsg,
    itemPathSteps,
    unitPathSteps,
    meshpegCloudName,
    setMeshpegCloudName,
    meshpegBimName,
    setMeshpegBimName,
    meshpegRunning,
    meshpegRes,
    formulaExpr,
    setFormulaExpr,
    formulaRunning,
    formulaRes,
    gatewayRes,
    calcUnitMerkle,
    useCurrentProofForUnit,
    exportMerkleJson,
    runMeshpeg,
    runFormulaPeg,
    runGatewaySync,
    verifyUnitMerkle,
  } = useSovereignAdvancedOps({
    apiProjectUri,
    activeCode: String(active?.code || ''),
    activeUri: String(active?.uri || ''),
    inputProofId,
    finalProofId,
    totalHash,
    docpegRiskScore,
    scanEntryLatestProofId: String(scanEntryLatest?.proof_id || ''),
    geoDistance,
    effectiveClaimQtyValue,
    measuredQtyValue,
    ledgerSnapshot,
    unitMerkleRoot,
    enqueueTriprolePacket,
    appendMeshpegLog,
    appendFormulaLog,
    appendGatewayLog,
    showToast,
  })

  const exportP2PManifest = useCallback(() => {
    const projectRoot = String((unitRes || {}).project_root_hash || (unitRes || {}).global_project_fingerprint || '')
    const payload = {
      node_id: p2pNodeId,
      project_uri: apiProjectUri,
      project_root_hash: projectRoot,
      total_proof_hash: totalHash,
      offline_packets: offlinePackets,
      offline_queue_size: offlinePackets.length,
      offline_conflicts: offlineSyncConflicts,
      peers: p2pPeers.split(/[\n,]+/).map((x) => x.trim()).filter(Boolean),
      generated_at: new Date().toISOString(),
    }
    downloadJson(`gitpeg-sync-${Date.now()}.json`, payload)
  }, [apiProjectUri, offlinePackets, offlineSyncConflicts, p2pNodeId, p2pPeers, totalHash, unitRes])
  const {
    inputBaseCls,
    inputXsCls,
    btnBlueCls,
    btnGreenCls,
    btnAmberCls,
    btnRedCls,
    panelCls,
  } = WORKBENCH_STYLES
  const {
    latestProofIdText,
    totalHashShort,
    nearestAnchorText,
    currentSubdivisionText,
    merkleRootText,
  } = buildWorkbenchDisplayTexts({
    latestEvidenceNode,
    inputProofId,
    totalHash,
    arPrimary,
    active,
    unitRes,
  })
  const {
    traceOverlayNodes,
    readinessAction,
    componentTypeOptions,
    sovereignValue,
  } = useSovereignWorkbenchSummaryState({
    project: {
      projectUri,
      apiProjectUri,
      displayProjectUri,
      projectId,
      active,
      activeUri,
      activePath,
      boundSpu,
      isContractSpu,
      spuKind,
      spuBadge,
      stepLabel,
      lifecycle,
      nodePathMap,
    },
    identity: {
      dtoRole,
      roleAllowed,
      executorDid,
      supervisorDid,
      ownerDid,
    },
    asset: {
      summary,
      activeGenesisSummary,
      baselineTotal,
      availableTotal,
      effectiveSpent,
      effectiveClaimQtyValue,
      inputProofId,
      finalProofId,
      totalHash,
      verifyUri,
      evidenceCenter,
      sampleId,
    },
    audit: {
      gateStats,
      gateReason,
      exceedBalance,
      snappegReady,
      geoTemporalBlocked,
      normResolution,
      disputeOpen,
      disputeProof,
      archiveLocked,
    },
    ui: {
      compType,
    },
  })
  const workbenchSectionsProps = buildWorkbenchSectionsProps({
    shell: {
      isGenesisView,
      isTripView,
      isAuditView,
      frameStyleText: WORKBENCH_FRAME_STYLE_TEXT,
      gridOverlayStyle: WORKBENCH_GRID_OVERLAY_STYLE,
    },
    primary: {
      hero: {
      activePath,
      displayProjectUri,
      progressPct: summary.pct,
      isOnline,
      offlineCount,
      nodeCount: nodes.length,
      activeCode: active?.code || '',
      totalHash,
      isTripView,
      finalProofReady,
      btnBlueCls,
      onNavigateAudit: onNavigateView ? () => onNavigateView('audit') : undefined,
    },
      genesisOverview: {
      isGenesisView,
      readinessOverall,
      readinessLoading,
      readinessPercent,
      readinessLayers,
      readinessAction,
      showRolePlaybook,
      btnBlueCls,
      btnGreenCls,
      btnAmberCls,
      panelCls,
      apiProjectUri,
      specBinding,
      gateBinding,
      normRefs,
      isSpecBound,
      lifecycle,
      activeCode: active?.code || '',
      availableTotal,
      activePath,
      displayProjectUri,
      onRunReadinessCheck: () => void runReadinessCheck(false),
      onToggleRolePlaybook: () => setShowRolePlaybook((value) => !value),
      onNavigateTrip: onNavigateView ? () => onNavigateView('trip') : undefined,
      onNavigateAudit: onNavigateView ? () => onNavigateView('audit') : undefined,
    },
      genesisTree: {
      styles: {
        panelCls,
        inputBaseCls,
        btnBlueCls,
      },
      files: {
        boqFileRef,
        fileName,
      },
      importState: {
        importing,
        importJobId,
        importStatusText,
        importProgress,
        importError,
      },
      tree: {
        showLeftSummary,
        treeQuery,
        treeSearch,
        nodes,
        roots,
        byCode,
        aggMap,
        expandedCodes,
        nodePathMap,
      },
      actions: {
        onSelectFile,
        onImportGenesis: () => importGenesis(),
        onLoadBuiltinLedger400: () => loadBuiltinLedger400(),
        onToggleSummary: () => setShowLeftSummary((v) => !v),
        onTreeQueryChange: setTreeQuery,
        onToggleExpanded: toggleExpanded,
        onSelectNode: (code) => selectNode(code),
      },
    },
      tripWorkbench: {
      styles: {
        panelCls,
        inputBaseCls,
        btnBlueCls,
        btnAmberCls,
        btnGreenCls,
        btnRedCls,
      },
      display: {
        hashing,
        templateDisplay,
        isSpecBound,
        specBinding,
        gateBinding,
        displayMeta,
        componentTypeOptions,
      },
      context: {
        compType,
        loadingCtx,
        contextError,
        sampleId,
        effectiveSchema,
        form,
        normRefs,
      },
      scan: {
        geoFormLocked,
        scanEntryStatus,
        scanEntryAt,
        scanEntryToken,
        scanEntryRequired,
        scanEntryTokenHash,
        scanChainBadge,
        scanEntryLatest,
      },
      evidence: {
        evidence,
        evidenceName,
        evidenceAccept,
        evidenceLabel,
        evidenceHint,
        evidenceFileRef,
      },
      delta: {
        showAdvancedExecution,
        deltaAmount,
        deltaReason,
        applyingDelta,
        variationRes,
        claimQty,
        claimQtyProvided,
        measuredQtyValue,
        deltaSuggest,
      },
      geo: {
        geoValid,
        geoFenceWarning,
        temporalBlocked,
        geoFenceActive,
        geoDistance,
        geoAnchor,
        lat,
        lng,
      },
      execution: {
        tripStage,
        effectiveRiskScore,
        executing,
        mockGenerating,
        rejecting,
      },
      actions: {
        onTraceOpen: () => setTraceOpen(true),
        onScanEntry: () => handleScanEntry(),
        onScanEntryTokenChange: setScanEntryToken,
        onScanEntryRequiredChange: setScanEntryRequired,
        onSampleIdChange: setSampleId,
        onCompTypeChange: setCompType,
        onExecutorDidChange: setExecutorDid,
        onLoadContext: () => active?.uri && loadContext(active.uri, compType),
        onFormChange: setForm,
        onEvidence: (files) => onEvidence(files),
        onFingerprintOpen: () => setFingerprintOpen(true),
        onEvidencePreview: openEvidencePreview,
        onDeltaAmountChange: setDeltaAmount,
        onDeltaReasonChange: setDeltaReason,
        onApplyDelta: () => applyDelta(),
        onSuggestDelta: () => {
          setDeltaAmount(deltaSuggest.toFixed(3))
          setDeltaReason('超量补差')
          setShowAdvancedExecution(true)
        },
        onClaimQtyChange: setClaimQty,
        onSubmitTrip: () => submitTrip(),
        onSubmitTripMock: () => submitTripMock(),
        onRecordRejectTrip: () => recordRejectTrip(),
        onLatChange: setLat,
        onLngChange: setLng,
      },
      helpers: {
        sanitizeMeasuredInput,
        metricLabel: toChineseMetricLabel,
        toChineseCompType,
      },
    },
    },
    secondary: {
      auditShell: {
        shell: {
          isAuditView,
          panelCls,
          draftReady,
        },
        consensusAudit: {
          visibility: {
            showAdvancedConsensus,
            setShowAdvancedConsensus,
            showAcceptanceAdvanced,
            setShowAcceptanceAdvanced,
          },
          scan: {
            finalPiecePrompt,
            scanConfirmUri,
            scanProofId,
            setScanProofId,
            scanPayload,
            setScanPayload,
            scanDid,
            setScanDid,
            scanConfirmToken,
            scanning,
            scanRes,
            doScanConfirm,
          },
          consensus: {
            minValueText: consensusMinValueText,
            maxValueText: consensusMaxValueText,
            deviationText: consensusDeviationText,
            deviationPercentText: consensusDeviationPercentText,
            consensusAllowedAbsText,
            consensusAllowedPctText,
            consensusConflict,
            consensusConflictSummary,
          },
          dispute: {
            disputeProof,
            disputeOpen,
            disputeProofId,
            setDisputeProofId,
            disputeResolutionNote,
            setDisputeResolutionNote,
            disputeResult,
            setDisputeResult,
            disputeResolving,
            disputeResolveRes,
            resolveDispute,
          },
          docFinal: {
            archiveLocked,
            docFinalPassphrase,
            setDocFinalPassphrase,
            docFinalIncludeUnsettled,
            setDocFinalIncludeUnsettled,
            docFinalExporting,
            docFinalFinalizing,
            docFinalRes,
            docFinalAuditUrl,
            docFinalVerifyBaseUrl,
            verifyUri,
            disputeProofShort,
            offlineQueueSize: offlinePackets.length,
            offlineSyncConflicts,
            apiProjectUri,
            docFinalQrSrc,
            exportProjectDocFinal,
            finalizeProjectDocFinal,
          },
          specdict: {
            specdictProjectUris,
            setSpecdictProjectUris,
            specdictMinSamples,
            setSpecdictMinSamples,
            specdictNamespace,
            setSpecdictNamespace,
            specdictCommit,
            setSpecdictCommit,
            specdictLoading,
            specdictExporting,
            specdictRuleTotal,
            specdictHighRisk,
            specdictBestPractice,
            specdictBundleUri,
            specdictSuccessPatterns,
            specdictHighRiskItems,
            specdictBestPracticeItems,
            specdictWeightEntries,
            specdictRes,
            runSpecdictEvolve,
            runSpecdictExport,
          },
          styles: {
            inputBaseCls,
            btnBlueCls,
            btnGreenCls,
            btnAmberCls,
          },
          helpers: {
            copyText,
            describeSpecdictItem,
          },
        },
        advancedOps: {
          visibility: {
            showAdvancedConsensus,
            showFingerprintAdvanced,
            setShowFingerprintAdvanced,
          },
          meshpeg: {
            meshpegCloudName,
            setMeshpegCloudName,
            meshpegBimName,
            setMeshpegBimName,
            meshpegRunning,
            meshpegRes,
            runMeshpeg,
          },
          formula: {
            formulaExpr,
            setFormulaExpr,
            formulaRunning,
            formulaRes,
            runFormulaPeg,
          },
          gateway: {
            gatewayRes,
            runGatewaySync,
          },
          asset: {
            assetAppraising,
            assetAppraisal,
            buildAssetAppraisal,
          },
          ar: {
            arRadius,
            setArRadius,
            arLimit,
            setArLimit,
            arLoading,
            activeUri: String(active?.uri || ''),
            latestProofId: latestProofIdText,
            totalHashShort,
            nearestAnchorText,
            arItems,
            runArOverlay,
            openArFullscreen,
            openArFocus,
          },
          geo: {
            geoFenceStatusText,
            scanEntryStatus,
            scanEntryRequired,
            scanEntryToken,
            scanChainBadge,
            geoAnchor,
            geoDistance,
            temporalWindow,
            geoTemporalBlocked,
            currentSubdivisionText,
          },
          fingerprint: {
            unitLoading,
            unitProofId,
            setUnitProofId,
            unitMaxRows,
            setUnitMaxRows,
            unitRes,
            unitVerifying,
            unitVerifyMsg,
            itemPathSteps,
            unitPathSteps,
            calcUnitMerkle,
            useCurrentProofForUnit,
            verifyUnitMerkle,
            exportMerkleJson,
          },
          p2p: {
            p2pNodeId,
            offlineQueueSize: offlinePackets.length,
            p2pLastSync,
            p2pAutoSync,
            setP2pAutoSync,
            p2pPeers,
            setP2pPeers,
            merkleRootText,
            exportP2PManifest,
            simulateP2PSync,
          },
          styles: {
            inputBaseCls,
            btnBlueCls,
            btnGreenCls,
            btnAmberCls,
          },
          helpers: {
            formatNumber,
            copyText,
            downloadJson,
          },
        },
        auditDocPreview: {
          conflict: {
            consensusConflict,
            disputeOpen,
            disputeProof,
            consensusDeviationText,
            consensusDeviationPercentText,
            consensusAllowedAbsText,
            consensusAllowedPctText,
          },
          document: {
            finalProofReady,
            qrSrc,
            verifyUri,
            finalProofId,
            previewPdfB64,
            pdfB64,
            previewIsDraft,
            tripStage,
            evidenceCount: evidence.length,
            totalHash,
            activeCode: String(active?.code || ''),
            activePath,
            activeUri: String(active?.uri || ''),
            gatePass: gateStats.pass,
            gateTotal: gateStats.total || 0,
            reportedPctText: activeGenesisSummary.reportedPct.toFixed(2),
            activeSignMarker,
            pdfPage,
            templateSourceText,
            pdfRenderLoading,
            pdfRenderError,
            draftReady,
            templateDisplay,
            docModalOpen,
            sampleId,
          },
          identity: {
            signFocus,
            signStep,
            executorDid,
            supervisorDid,
            ownerDid,
            setSupervisorDid,
            setOwnerDid,
          },
          refs: {
            contractorAnchorRef,
            supervisorAnchorRef,
            ownerAnchorRef,
            previewScrollRef,
            pdfCanvasRef,
          },
          styles: {
            inputBaseCls,
          },
          helpers: {
            scrollToSign,
            copyText,
            setDocModalOpen,
          },
        },
      },
      evidenceVault: {
        evidenceCenter: {
          evidenceCenterLoading,
          evidenceCenterError,
          evidenceQuery,
          setEvidenceQuery,
          evidenceScope,
          setEvidenceScope,
          evidenceSmuId,
          setEvidenceSmuId,
          evidenceFilter,
          setEvidenceFilter,
          smuOptions,
          filteredEvidenceItems,
          filteredDocs,
          evidenceCompletenessScore,
          settlementRiskScore,
          evidenceGraphNodes,
          ledgerSnapshot,
          meshpegItems,
          formulaItems,
          gatewayItems,
          assetOrigin,
          assetOriginStatement,
          didReputationScore,
          didReputationGrade,
          didSamplingMultiplier,
          didHighRiskList,
          sealingPatternId,
          sealingScanHint,
          sealingMicrotext,
          sealingRows,
          scanEntryActiveOnly,
          evidenceItemsPaged,
          evidencePageSafe,
          setEvidencePage,
          totalEvidencePages,
          latestEvidenceNode,
          utxoStatusText,
          evidenceZipDownloading,
          erpReceiptDoc,
          docpegRisk,
          docpegRiskScore,
          loadEvidenceCenter,
          downloadEvidenceCenterPackage,
          exportEvidenceCenter,
          exportEvidenceCenterCsv,
          openEvidenceFocus,
          openDocumentFocus,
        },
        dispute: {
          consensusConflict,
          consensusAllowedAbsText,
          consensusAllowedPctText,
          disputeConflict,
          disputeDeviation,
          disputeDeviationPct,
          disputeAllowedAbs: typeof disputeAllowedAbs === 'number' ? disputeAllowedAbs : null,
          disputeAllowedPct: typeof disputeAllowedPct === 'number' ? disputeAllowedPct : null,
          disputeValues,
          disputeProof,
          disputeOpen,
          disputeProofShort,
          setShowAdvancedConsensus,
          setDisputeProofId,
        },
        erp: {
          erpRetrying,
          erpRetryMsg,
          retryErpnextPush,
        },
        styles: {
          btnBlueCls,
        },
        helpers: {
          copyText,
        },
      },
      tripFlowModal: {
        sign: {
          signOpen,
          tripStage,
          signStep,
          signing,
          executorDid,
          supervisorDid,
          ownerDid,
          doSign,
          setSignOpen,
        },
        consensus: {
          consensusContractorValue,
          setConsensusContractorValue,
          consensusSupervisorValue,
          setConsensusSupervisorValue,
          consensusOwnerValue,
          setConsensusOwnerValue,
          consensusAllowedDeviation,
          setConsensusAllowedDeviation,
          consensusAllowedDeviationPct,
          setConsensusAllowedDeviationPct,
          consensusBaseValueText,
          consensusConflict,
          consensusMinValueText,
          consensusMaxValueText,
          consensusDeviationText,
          consensusDeviationPercentText,
          consensusAllowedAbsText,
          consensusAllowedPctText,
        },
        lock: {
          scanLockStage,
          scanLockProofId,
          closeScanLock,
        },
        delta: {
          deltaModalOpen,
          exceedTotalText,
          setShowAdvancedExecution,
          setDeltaModalOpen,
        },
        styles: {
          inputBaseCls,
          btnAmberCls,
        },
      },
      evidenceModal: {
        evidencePreview: {
          evidenceOpen,
          evidenceFocus,
          geoTemporalBlocked,
          activeCode: String(active?.code || ''),
          activeUri: String(active?.uri || ''),
          lat,
          lng,
          executorDid,
          sampleId,
          onCloseEvidencePreview: closeEvidencePreview,
        },
        evidenceCenter: {
          evidenceCenterFocus,
          evidenceCenterDocFocus,
          onCloseEvidenceFocus: closeEvidenceFocus,
          onCloseDocumentFocus: closeDocumentFocus,
        },
      },
      workbenchOverlay: {
        ar: {
          focus: arFocus,
          fullscreen: arFullscreen,
          lat,
          lng,
          radius: arRadius,
          filteredItems: arFilteredItems,
          totalItemsCount: arItemsSorted.length,
          loading: arLoading,
          filterMax: arFilterMax,
          inputBaseCls,
          btnBlueCls,
          btnAmberCls,
          onCopyText: (label, value) => void copyText(label, value),
          onFilterMaxChange: setArFilterMax,
          onRefresh: () => void runArOverlay(),
          onCloseFocus: closeArFocus,
          onJumpToItem: jumpToArItem,
          onCloseFullscreen: closeArFullscreen,
          onSelectFullscreenItem: selectArFullscreenItem,
        },
        fingerprint: {
          open: fingerprintOpen,
          evidenceSource: evidence,
          onClose: () => setFingerprintOpen(false),
        },
        trace: {
          open: traceOpen,
          nodes: traceOverlayNodes,
          onClose: () => setTraceOpen(false),
        },
        floatingDid: {
          executorDid,
          supervisorDid,
          ownerDid,
          riskScore: effectiveRiskScore,
          totalHash: String(totalHash || ''),
        },
      },
      offlineFooter: {
        isOnline,
        offlineCount,
        offlineSyncConflicts,
        offlineType,
        inputXsCls,
        btnBlueCls,
        offlineImporting,
        offlineImportName,
        offlineReplay,
        offlinePacketsCount: offlinePackets.length,
        offlineImportRef,
        onOfflineTypeChange: setOfflineType,
        onSealOfflinePacket: sealOfflinePacket,
        onTriggerImport: () => offlineImportRef.current?.click(),
        onExportOfflinePackets: exportOfflinePackets,
        onClearOfflinePackets: clearOfflinePackets,
        onImportOfflinePackets: importOfflinePackets,
      },
    },
  })

  return (
    <ProjectSovereignProvider value={sovereignValue}>
      <NormEngineProvider schema={effectiveSchema} form={form} ctx={ctx} isContractSpu={isContractSpu}>
        <Card title="主权 BOQ 工作台" icon="🔗" style={{ marginBottom: 10 }} className="overflow-hidden sovereign-workbench">
          <SovereignWorkbenchSections {...workbenchSectionsProps} />
        </Card>
      </NormEngineProvider>
    </ProjectSovereignProvider>
  )
}
