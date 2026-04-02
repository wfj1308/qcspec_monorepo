import type { ComponentProps, Dispatch, SetStateAction } from 'react'

import EvidenceVault from '../EvidenceVault'
import SovereignAdvancedOpsPanels from '../SovereignAdvancedOpsPanels'
import SovereignAuditShell from '../SovereignAuditShell'
import SovereignAuditDocPreview from '../SovereignAuditDocPreview'
import SovereignConsensusAuditPanels from '../SovereignConsensusAuditPanels'
import SovereignTripFlowModals from '../SovereignTripFlowModals'

type EvidenceVaultProps = ComponentProps<typeof EvidenceVault>
type AuditShellProps = ComponentProps<typeof SovereignAuditShell>
type ConsensusAuditPanelProps = ComponentProps<typeof SovereignConsensusAuditPanels>
type AdvancedOpsPanelProps = ComponentProps<typeof SovereignAdvancedOpsPanels>
type AuditDocPreviewProps = ComponentProps<typeof SovereignAuditDocPreview>
type TripFlowModalProps = ComponentProps<typeof SovereignTripFlowModals>
type CopyTextFn = (label: string, value: string) => void | Promise<void>
type DownloadJsonFn = (filename: string, data: unknown) => void
type DescribeSpecdictItemFn = (item: unknown) => string
type FormatNumberFn = AdvancedOpsPanelProps['formatNumber']

type BuildConsensusAuditPanelPropsArgs = {
  visibility: {
    showAdvancedConsensus: boolean
    setShowAdvancedConsensus: Dispatch<SetStateAction<boolean>>
    showAcceptanceAdvanced: boolean
    setShowAcceptanceAdvanced: Dispatch<SetStateAction<boolean>>
  }
  scan: {
    finalPiecePrompt: string
    scanConfirmUri: string
    scanProofId: string
    setScanProofId: Dispatch<SetStateAction<string>>
    scanPayload: string
    setScanPayload: Dispatch<SetStateAction<string>>
    scanDid: string
    setScanDid: Dispatch<SetStateAction<string>>
    scanConfirmToken: string
    scanning: boolean
    scanRes: Record<string, unknown> | null
    doScanConfirm: () => void | Promise<void>
  }
  consensus: {
    minValueText: string
    maxValueText: string
    deviationText: string
    deviationPercentText: string
    consensusAllowedAbsText: string
    consensusAllowedPctText: string
    consensusConflict: boolean
    consensusConflictSummary: Record<string, unknown>
  }
  dispute: {
    disputeProof: string
    disputeOpen: boolean
    disputeProofId: string
    setDisputeProofId: Dispatch<SetStateAction<string>>
    disputeResolutionNote: string
    setDisputeResolutionNote: Dispatch<SetStateAction<string>>
    disputeResult: 'PASS' | 'REJECT'
    setDisputeResult: Dispatch<SetStateAction<'PASS' | 'REJECT'>>
    disputeResolving: boolean
    disputeResolveRes: Record<string, unknown> | null
    resolveDispute: () => void | Promise<void>
  }
  docFinal: {
    archiveLocked: boolean
    docFinalPassphrase: string
    setDocFinalPassphrase: Dispatch<SetStateAction<string>>
    docFinalIncludeUnsettled: boolean
    setDocFinalIncludeUnsettled: Dispatch<SetStateAction<boolean>>
    docFinalExporting: boolean
    docFinalFinalizing: boolean
    docFinalRes: Record<string, unknown> | null
    docFinalAuditUrl: string
    docFinalVerifyBaseUrl: string
    verifyUri: string
    disputeProofShort: string
    offlineQueueSize: number
    offlineSyncConflicts: number
    apiProjectUri: string
    docFinalQrSrc: string
    exportProjectDocFinal: () => void | Promise<void>
    finalizeProjectDocFinal: () => void | Promise<void>
  }
  specdict: {
    specdictProjectUris: string
    setSpecdictProjectUris: Dispatch<SetStateAction<string>>
    specdictMinSamples: string
    setSpecdictMinSamples: Dispatch<SetStateAction<string>>
    specdictNamespace: string
    setSpecdictNamespace: Dispatch<SetStateAction<string>>
    specdictCommit: boolean
    setSpecdictCommit: Dispatch<SetStateAction<boolean>>
    specdictLoading: boolean
    specdictExporting: boolean
    specdictRuleTotal: number
    specdictHighRisk: number
    specdictBestPractice: number
    specdictBundleUri: string
    specdictSuccessPatterns: unknown[]
    specdictHighRiskItems: unknown[]
    specdictBestPracticeItems: unknown[]
    specdictWeightEntries: Array<[string, unknown]>
    specdictRes: Record<string, unknown> | null
    runSpecdictEvolve: () => void | Promise<void>
    runSpecdictExport: () => void | Promise<void>
  }
  styles: {
    inputBaseCls: string
    btnBlueCls: string
    btnGreenCls: string
    btnAmberCls: string
  }
  helpers: {
    copyText: CopyTextFn
    describeSpecdictItem: DescribeSpecdictItemFn
  }
}

type BuildAdvancedOpsPanelPropsArgs = {
  visibility: {
    showAdvancedConsensus: boolean
    showFingerprintAdvanced: boolean
    setShowFingerprintAdvanced: Dispatch<SetStateAction<boolean>>
  }
  meshpeg: {
    meshpegCloudName: string
    setMeshpegCloudName: Dispatch<SetStateAction<string>>
    meshpegBimName: string
    setMeshpegBimName: Dispatch<SetStateAction<string>>
    meshpegRunning: boolean
    meshpegRes: Record<string, unknown> | null
    runMeshpeg: () => void | Promise<void>
  }
  formula: {
    formulaExpr: string
    setFormulaExpr: Dispatch<SetStateAction<string>>
    formulaRunning: boolean
    formulaRes: Record<string, unknown> | null
    runFormulaPeg: () => void | Promise<void>
  }
  gateway: {
    gatewayRes: Record<string, unknown> | null
    runGatewaySync: () => void | Promise<void>
  }
  asset: {
    assetAppraising: boolean
    assetAppraisal: Record<string, unknown> | null
    buildAssetAppraisal: () => void | Promise<void>
  }
  ar: {
    arRadius: string
    setArRadius: Dispatch<SetStateAction<string>>
    arLimit: string
    setArLimit: Dispatch<SetStateAction<string>>
    arLoading: boolean
    activeUri: string
    latestProofId: string
    totalHashShort: string
    nearestAnchorText: string
    arItems: Array<Record<string, unknown>>
    runArOverlay: () => void | Promise<void>
    openArFullscreen: () => void
    openArFocus: (item: Record<string, unknown>) => void
  }
  geo: {
    geoFenceStatusText: string
    scanEntryStatus: AdvancedOpsPanelProps['scanEntryStatus']
    scanEntryRequired: boolean
    scanEntryToken: string
    scanChainBadge: AdvancedOpsPanelProps['scanChainBadge']
    geoAnchor: Record<string, unknown> | null
    geoDistance: number
    temporalWindow: AdvancedOpsPanelProps['temporalWindow']
    geoTemporalBlocked: boolean
    currentSubdivisionText: string
  }
  fingerprint: {
    unitLoading: boolean
    unitProofId: string
    setUnitProofId: Dispatch<SetStateAction<string>>
    unitMaxRows: string
    setUnitMaxRows: Dispatch<SetStateAction<string>>
    unitRes: Record<string, unknown> | null
    unitVerifying: boolean
    unitVerifyMsg: string
    itemPathSteps: AdvancedOpsPanelProps['itemPathSteps']
    unitPathSteps: AdvancedOpsPanelProps['unitPathSteps']
    calcUnitMerkle: () => void | Promise<void>
    useCurrentProofForUnit: () => void
    verifyUnitMerkle: () => void | Promise<void>
    exportMerkleJson: () => void
  }
  p2p: {
    p2pNodeId: string
    offlineQueueSize: number
    p2pLastSync: string
    p2pAutoSync: boolean
    setP2pAutoSync: Dispatch<SetStateAction<boolean>>
    p2pPeers: string
    setP2pPeers: Dispatch<SetStateAction<string>>
    merkleRootText: string
    exportP2PManifest: () => void
    simulateP2PSync: () => void
  }
  styles: {
    inputBaseCls: string
    btnBlueCls: string
    btnGreenCls: string
    btnAmberCls: string
  }
  helpers: {
    formatNumber: FormatNumberFn
    copyText: CopyTextFn
    downloadJson: DownloadJsonFn
  }
}

type BuildEvidenceVaultPropsArgs = {
  evidenceCenter: {
    evidenceCenterLoading: boolean
    evidenceCenterError: string
    evidenceQuery: string
    setEvidenceQuery: Dispatch<SetStateAction<string>>
    evidenceScope: EvidenceVaultProps['evidenceScope']
    setEvidenceScope: Dispatch<SetStateAction<EvidenceVaultProps['evidenceScope']>>
    evidenceSmuId: string
    setEvidenceSmuId: Dispatch<SetStateAction<string>>
    evidenceFilter: EvidenceVaultProps['evidenceFilter']
    setEvidenceFilter: Dispatch<SetStateAction<EvidenceVaultProps['evidenceFilter']>>
    smuOptions: string[]
    filteredEvidenceItems: Array<Record<string, unknown>>
    filteredDocs: Array<Record<string, unknown>>
    evidenceCompletenessScore: number
    settlementRiskScore: number
    evidenceGraphNodes: EvidenceVaultProps['evidenceGraphNodes']
    ledgerSnapshot: Record<string, unknown>
    meshpegItems: Array<Record<string, unknown>>
    formulaItems: Array<Record<string, unknown>>
    gatewayItems: Array<Record<string, unknown>>
    assetOrigin: Record<string, unknown>
    assetOriginStatement: string
    didReputationScore: number
    didReputationGrade: string
    didSamplingMultiplier: number
    didHighRiskList: unknown[]
    sealingPatternId: string
    sealingScanHint: string
    sealingMicrotext: string[]
    sealingRows: string[]
    scanEntryActiveOnly: Array<Record<string, unknown>>
    evidenceItemsPaged: Array<Record<string, unknown>>
    evidencePageSafe: number
    setEvidencePage: Dispatch<SetStateAction<number>>
    totalEvidencePages: number
    latestEvidenceNode: Record<string, unknown> | null
    utxoStatusText: string
    evidenceZipDownloading: boolean
    erpReceiptDoc: Record<string, unknown> | null
    docpegRisk: Record<string, unknown>
    docpegRiskScore: number
    loadEvidenceCenter: () => void | Promise<void>
    downloadEvidenceCenterPackage: () => void | Promise<void>
    exportEvidenceCenter: () => void
    exportEvidenceCenterCsv: () => void
    openEvidenceFocus: (value: string) => void
    openDocumentFocus: (value: string) => void
  }
  dispute: {
    consensusConflict: Record<string, unknown> | boolean
    consensusAllowedAbsText: string
    consensusAllowedPctText: string
    disputeConflict: Record<string, unknown>
    disputeDeviation: number
    disputeDeviationPct: number
    disputeAllowedAbs: number | null
    disputeAllowedPct: number | null
    disputeValues: unknown[]
    disputeProof: string
    disputeOpen: boolean
    disputeProofShort: string
    setShowAdvancedConsensus: Dispatch<SetStateAction<boolean>>
    setDisputeProofId: Dispatch<SetStateAction<string>>
  }
  erp: {
    erpRetrying: boolean
    erpRetryMsg: string
    retryErpnextPush: () => void | Promise<void>
  }
  styles: {
    btnBlueCls: string
  }
  helpers: {
    copyText: CopyTextFn
  }
}

type BuildAuditDocPreviewPropsArgs = {
  conflict: {
    consensusConflict: boolean
    disputeOpen: boolean
    disputeProof: string
    consensusDeviationText: string
    consensusDeviationPercentText: string
    consensusAllowedAbsText: string
    consensusAllowedPctText: string
  }
  document: {
    finalProofReady: boolean
    qrSrc: string
    verifyUri: string
    finalProofId: string
    previewPdfB64: string
    pdfB64: string
    previewIsDraft: boolean
    tripStage: AuditDocPreviewProps['tripStage']
    evidenceCount: number
    totalHash: string
    activeCode: string
    activePath: string
    activeUri: string
    gatePass: number
    gateTotal: number
    reportedPctText: string
    activeSignMarker: AuditDocPreviewProps['activeSignMarker']
    pdfPage: number
    templateSourceText: string
    pdfRenderLoading: boolean
    pdfRenderError: string
    draftReady: boolean
    templateDisplay: string
    docModalOpen: boolean
    sampleId: string
  }
  identity: {
    signFocus: AuditDocPreviewProps['signFocus']
    signStep: number
    executorDid: string
    supervisorDid: string
    ownerDid: string
    setSupervisorDid: Dispatch<SetStateAction<string>>
    setOwnerDid: Dispatch<SetStateAction<string>>
  }
  refs: {
    contractorAnchorRef: AuditDocPreviewProps['contractorAnchorRef']
    supervisorAnchorRef: AuditDocPreviewProps['supervisorAnchorRef']
    ownerAnchorRef: AuditDocPreviewProps['ownerAnchorRef']
    previewScrollRef: AuditDocPreviewProps['previewScrollRef']
    pdfCanvasRef: AuditDocPreviewProps['pdfCanvasRef']
  }
  styles: {
    inputBaseCls: string
  }
  helpers: {
    scrollToSign: AuditDocPreviewProps['onScrollToSign']
    copyText: CopyTextFn
    setDocModalOpen: Dispatch<SetStateAction<boolean>>
  }
}

type BuildTripFlowModalPropsArgs = {
  sign: {
    signOpen: boolean
    tripStage: TripFlowModalProps['tripStage']
    signStep: number
    signing: boolean
    executorDid: string
    supervisorDid: string
    ownerDid: string
    doSign: () => void | Promise<void>
    setSignOpen: Dispatch<SetStateAction<boolean>>
  }
  consensus: {
    consensusContractorValue: string
    setConsensusContractorValue: Dispatch<SetStateAction<string>>
    consensusSupervisorValue: string
    setConsensusSupervisorValue: Dispatch<SetStateAction<string>>
    consensusOwnerValue: string
    setConsensusOwnerValue: Dispatch<SetStateAction<string>>
    consensusAllowedDeviation: string
    setConsensusAllowedDeviation: Dispatch<SetStateAction<string>>
    consensusAllowedDeviationPct: string
    setConsensusAllowedDeviationPct: Dispatch<SetStateAction<string>>
    consensusBaseValueText: string
    consensusConflict: boolean
    consensusMinValueText: string
    consensusMaxValueText: string
    consensusDeviationText: string
    consensusDeviationPercentText: string
    consensusAllowedAbsText: string
    consensusAllowedPctText: string
  }
  lock: {
    scanLockStage: TripFlowModalProps['scanLockStage']
    scanLockProofId: string
    closeScanLock: TripFlowModalProps['onCloseScanLock']
  }
  delta: {
    deltaModalOpen: boolean
    exceedTotalText: string
    setShowAdvancedExecution: Dispatch<SetStateAction<boolean>>
    setDeltaModalOpen: Dispatch<SetStateAction<boolean>>
  }
  styles: {
    inputBaseCls: string
    btnAmberCls: string
  }
}

type BuildAuditShellPropsArgs = {
  shell: Pick<AuditShellProps, 'isAuditView' | 'panelCls' | 'draftReady'>
  auditDocPreview: BuildAuditDocPreviewPropsArgs
  consensusAudit: BuildConsensusAuditPanelPropsArgs
  advancedOps: BuildAdvancedOpsPanelPropsArgs
}

function toFiniteNumberArray(values: unknown): number[] {
  if (!Array.isArray(values)) return []
  return values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))
}

export function buildConsensusAuditPanelProps({
  visibility,
  scan,
  consensus,
  dispute,
  docFinal,
  specdict,
  styles,
  helpers,
}: BuildConsensusAuditPanelPropsArgs): ConsensusAuditPanelProps {
  return {
    showAdvancedConsensus: visibility.showAdvancedConsensus,
    showAcceptanceAdvanced: visibility.showAcceptanceAdvanced,
    finalPiecePrompt: scan.finalPiecePrompt,
    scanConfirmUri: scan.scanConfirmUri,
    scanProofId: scan.scanProofId,
    scanPayload: scan.scanPayload,
    scanDid: scan.scanDid,
    scanConfirmToken: scan.scanConfirmToken,
    scanning: scan.scanning,
    scanRes: scan.scanRes,
    minValueText: consensus.minValueText,
    maxValueText: consensus.maxValueText,
    deviationText: consensus.deviationText,
    deviationPercentText: consensus.deviationPercentText,
    consensusAllowedAbsText: consensus.consensusAllowedAbsText,
    consensusAllowedPctText: consensus.consensusAllowedPctText,
    consensusConflict: consensus.consensusConflict,
    disputeProof: dispute.disputeProof,
    disputeOpen: dispute.disputeOpen,
    disputeProofId: dispute.disputeProofId,
    disputeResolutionNote: dispute.disputeResolutionNote,
    disputeResult: dispute.disputeResult,
    disputeResolving: dispute.disputeResolving,
    disputeResolveRes: dispute.disputeResolveRes,
    archiveLocked: docFinal.archiveLocked,
    docFinalPassphrase: docFinal.docFinalPassphrase,
    docFinalIncludeUnsettled: docFinal.docFinalIncludeUnsettled,
    docFinalExporting: docFinal.docFinalExporting,
    docFinalFinalizing: docFinal.docFinalFinalizing,
    docFinalRes: docFinal.docFinalRes,
    docFinalAuditUrl: docFinal.docFinalAuditUrl,
    docFinalVerifyBaseUrl: docFinal.docFinalVerifyBaseUrl,
    verifyUri: docFinal.verifyUri,
    disputeProofShort: docFinal.disputeProofShort,
    offlineQueueSize: docFinal.offlineQueueSize,
    offlineSyncConflicts: docFinal.offlineSyncConflicts,
    apiProjectUri: docFinal.apiProjectUri,
    docFinalQrSrc: docFinal.docFinalQrSrc,
    specdictProjectUris: specdict.specdictProjectUris,
    specdictMinSamples: specdict.specdictMinSamples,
    specdictNamespace: specdict.specdictNamespace,
    specdictCommit: specdict.specdictCommit,
    specdictLoading: specdict.specdictLoading,
    specdictExporting: specdict.specdictExporting,
    specdictRuleTotal: specdict.specdictRuleTotal,
    specdictHighRisk: specdict.specdictHighRisk,
    specdictBestPractice: specdict.specdictBestPractice,
    specdictBundleUri: specdict.specdictBundleUri,
    successPatterns: specdict.specdictSuccessPatterns.slice(0, 3).map((item) => helpers.describeSpecdictItem(item)),
    highRiskItems: specdict.specdictHighRiskItems.slice(0, 3).map((item) => helpers.describeSpecdictItem(item)),
    bestPracticeItems: specdict.specdictBestPracticeItems.slice(0, 3).map((item) => helpers.describeSpecdictItem(item)),
    weightEntriesText: specdict.specdictWeightEntries.map(([key, value]) => `${key}:${String(value)}`),
    hasSpecdictRes: Boolean(specdict.specdictRes),
    inputBaseCls: styles.inputBaseCls,
    btnBlueCls: styles.btnBlueCls,
    btnGreenCls: styles.btnGreenCls,
    btnAmberCls: styles.btnAmberCls,
    onToggleAdvancedConsensus: () => visibility.setShowAdvancedConsensus((value) => !value),
    onCopyFinalPiece: () => void helpers.copyText('Final Piece Prompt', scan.finalPiecePrompt),
    onScanPayloadChange: scan.setScanPayload,
    onScanDidChange: scan.setScanDid,
    onScanProofIdChange: scan.setScanProofId,
    onFillScanToken: () => scan.setScanPayload(scan.scanConfirmToken),
    onScanConfirm: () => void scan.doScanConfirm(),
    onToggleAcceptanceAdvanced: () => visibility.setShowAcceptanceAdvanced((value) => !value),
    onCopyConflictSummary: () => void helpers.copyText('共识冲突摘要', JSON.stringify(consensus.consensusConflictSummary, null, 2)),
    onJumpToDispute: () => {
      visibility.setShowAdvancedConsensus(true)
      if (dispute.disputeProof) dispute.setDisputeProofId(dispute.disputeProof)
    },
    onDisputeProofIdChange: dispute.setDisputeProofId,
    onDisputeResolutionNoteChange: dispute.setDisputeResolutionNote,
    onDisputeResultChange: dispute.setDisputeResult,
    onResolveDispute: () => void dispute.resolveDispute(),
    onDocFinalPassphraseChange: docFinal.setDocFinalPassphrase,
    onDocFinalIncludeUnsettledChange: docFinal.setDocFinalIncludeUnsettled,
    onExportProjectDocFinal: () => void docFinal.exportProjectDocFinal(),
    onFinalizeProjectDocFinal: () => void docFinal.finalizeProjectDocFinal(),
    onProjectUrisChange: specdict.setSpecdictProjectUris,
    onMinSamplesChange: specdict.setSpecdictMinSamples,
    onNamespaceChange: specdict.setSpecdictNamespace,
    onCommitChange: specdict.setSpecdictCommit,
    onRunSpecdictEvolve: () => void specdict.runSpecdictEvolve(),
    onRunSpecdictExport: () => void specdict.runSpecdictExport(),
    onOneClickWriteGlobal: () => {
      specdict.setSpecdictCommit(true)
      void specdict.runSpecdictExport()
    },
  }
}

export function buildAdvancedOpsPanelProps({
  visibility,
  meshpeg,
  formula,
  gateway,
  asset,
  ar,
  geo,
  fingerprint,
  p2p,
  styles,
  helpers,
}: BuildAdvancedOpsPanelPropsArgs): AdvancedOpsPanelProps {
  return {
    show: visibility.showAdvancedConsensus,
    meshpegCloudName: meshpeg.meshpegCloudName,
    meshpegBimName: meshpeg.meshpegBimName,
    meshpegRunning: meshpeg.meshpegRunning,
    meshpegRes: meshpeg.meshpegRes,
    formulaExpr: formula.formulaExpr,
    formulaRunning: formula.formulaRunning,
    formulaRes: formula.formulaRes,
    gatewayRes: gateway.gatewayRes,
    assetAppraising: asset.assetAppraising,
    assetAppraisal: asset.assetAppraisal,
    arRadius: ar.arRadius,
    arLimit: ar.arLimit,
    arLoading: ar.arLoading,
    activeUri: ar.activeUri,
    latestProofId: ar.latestProofId,
    totalHashShort: ar.totalHashShort,
    nearestAnchorText: ar.nearestAnchorText,
    arItems: ar.arItems,
    geoFenceStatusText: geo.geoFenceStatusText,
    scanEntryStatus: geo.scanEntryStatus,
    scanEntryRequired: geo.scanEntryRequired,
    scanEntryToken: geo.scanEntryToken,
    scanChainBadge: geo.scanChainBadge,
    geoAnchor: geo.geoAnchor,
    geoDistance: geo.geoDistance,
    temporalWindow: geo.temporalWindow,
    geoTemporalBlocked: geo.geoTemporalBlocked,
    currentSubdivisionText: geo.currentSubdivisionText,
    showFingerprintAdvanced: visibility.showFingerprintAdvanced,
    unitLoading: fingerprint.unitLoading,
    unitProofId: fingerprint.unitProofId,
    unitMaxRows: fingerprint.unitMaxRows,
    unitRes: fingerprint.unitRes,
    unitVerifying: fingerprint.unitVerifying,
    unitVerifyMsg: fingerprint.unitVerifyMsg,
    itemPathSteps: fingerprint.itemPathSteps,
    unitPathSteps: fingerprint.unitPathSteps,
    p2pNodeId: p2p.p2pNodeId,
    offlineQueueSize: p2p.offlineQueueSize,
    p2pLastSync: p2p.p2pLastSync,
    p2pAutoSync: p2p.p2pAutoSync,
    p2pPeers: p2p.p2pPeers,
    merkleRootText: p2p.merkleRootText,
    inputBaseCls: styles.inputBaseCls,
    btnBlueCls: styles.btnBlueCls,
    btnGreenCls: styles.btnGreenCls,
    btnAmberCls: styles.btnAmberCls,
    formatNumber: helpers.formatNumber,
    onMeshpegCloudNameChange: meshpeg.setMeshpegCloudName,
    onMeshpegBimNameChange: meshpeg.setMeshpegBimName,
    onRunMeshpeg: () => void meshpeg.runMeshpeg(),
    onFormulaExprChange: formula.setFormulaExpr,
    onRunFormulaPeg: () => void formula.runFormulaPeg(),
    onRunGatewaySync: () => void gateway.runGatewaySync(),
    onCopyGatewayJson: () => void helpers.copyText('监管同步摘要', JSON.stringify(gateway.gatewayRes, null, 2)),
    onDownloadGatewayJson: () => helpers.downloadJson(`gateway-${Date.now()}.json`, gateway.gatewayRes),
    onBuildAssetAppraisal: () => void asset.buildAssetAppraisal(),
    onCopyAssetAppraisalJson: () => void helpers.copyText('资产评估 JSON', JSON.stringify(asset.assetAppraisal, null, 2)),
    onDownloadAssetAppraisalJson: () => helpers.downloadJson(`asset-appraisal-${Date.now()}.json`, asset.assetAppraisal),
    onArRadiusChange: ar.setArRadius,
    onArLimitChange: ar.setArLimit,
    onRunArOverlay: () => void ar.runArOverlay(),
    onOpenArFullscreen: ar.openArFullscreen,
    onFocusArItem: ar.openArFocus,
    onToggleFingerprintAdvanced: () => visibility.setShowFingerprintAdvanced((value) => !value),
    onUnitProofIdChange: fingerprint.setUnitProofId,
    onUnitMaxRowsChange: fingerprint.setUnitMaxRows,
    onCalcUnitMerkle: () => void fingerprint.calcUnitMerkle(),
    onUseCurrentProofForUnit: fingerprint.useCurrentProofForUnit,
    onVerifyUnitMerkle: () => void fingerprint.verifyUnitMerkle(),
    onExportMerkleJson: fingerprint.exportMerkleJson,
    onP2PAutoSyncChange: (checked) => p2p.setP2pAutoSync(checked),
    onP2PPeersChange: p2p.setP2pPeers,
    onExportP2PManifest: p2p.exportP2PManifest,
    onSimulateP2PSync: p2p.simulateP2PSync,
  }
}

export function buildEvidenceVaultProps({
  evidenceCenter,
  dispute,
  erp,
  styles,
  helpers,
}: BuildEvidenceVaultPropsArgs): EvidenceVaultProps {
  return {
    btnBlueCls: styles.btnBlueCls,
    evidenceCenterLoading: evidenceCenter.evidenceCenterLoading,
    evidenceCenterError: evidenceCenter.evidenceCenterError,
    evidenceQuery: evidenceCenter.evidenceQuery,
    evidenceScope: evidenceCenter.evidenceScope,
    evidenceSmuId: evidenceCenter.evidenceSmuId,
    evidenceFilter: evidenceCenter.evidenceFilter,
    smuOptions: evidenceCenter.smuOptions,
    filteredEvidenceItems: evidenceCenter.filteredEvidenceItems,
    filteredDocs: evidenceCenter.filteredDocs,
    evidenceCompletenessScore: evidenceCenter.evidenceCompletenessScore,
    settlementRiskScore: evidenceCenter.settlementRiskScore,
    evidenceGraphNodes: evidenceCenter.evidenceGraphNodes,
    ledgerSnapshot: evidenceCenter.ledgerSnapshot,
    meshpegItems: evidenceCenter.meshpegItems,
    formulaItems: evidenceCenter.formulaItems,
    gatewayItems: evidenceCenter.gatewayItems,
    assetOrigin: evidenceCenter.assetOrigin,
    assetOriginStatement: evidenceCenter.assetOriginStatement,
    didReputationScore: evidenceCenter.didReputationScore,
    didReputationGrade: evidenceCenter.didReputationGrade,
    didSamplingMultiplier: evidenceCenter.didSamplingMultiplier,
    didHighRiskList: evidenceCenter.didHighRiskList.map((item) => String(item)),
    sealingPatternId: evidenceCenter.sealingPatternId,
    sealingScanHint: evidenceCenter.sealingScanHint,
    sealingMicrotext: evidenceCenter.sealingMicrotext,
    sealingRows: evidenceCenter.sealingRows,
    scanEntryActiveOnly: evidenceCenter.scanEntryActiveOnly,
    evidenceItemsPaged: evidenceCenter.evidenceItemsPaged,
    evidencePageSafe: evidenceCenter.evidencePageSafe,
    totalEvidencePages: evidenceCenter.totalEvidencePages,
    latestEvidenceNode: evidenceCenter.latestEvidenceNode,
    utxoStatusText: evidenceCenter.utxoStatusText,
    consensusConflict: dispute.consensusConflict,
    consensusAllowedAbsText: dispute.consensusAllowedAbsText,
    consensusAllowedPctText: dispute.consensusAllowedPctText,
    disputeConflict: dispute.disputeConflict,
    disputeDeviation: dispute.disputeDeviation,
    disputeDeviationPct: dispute.disputeDeviationPct,
    disputeAllowedAbs: dispute.disputeAllowedAbs,
    disputeAllowedPct: dispute.disputeAllowedPct,
    disputeValues: toFiniteNumberArray(dispute.disputeValues),
    disputeProof: dispute.disputeProof,
    disputeOpen: dispute.disputeOpen,
    disputeProofShort: dispute.disputeProofShort,
    erpRetrying: erp.erpRetrying,
    erpRetryMsg: erp.erpRetryMsg,
    evidenceZipDownloading: evidenceCenter.evidenceZipDownloading,
    erpReceiptDoc: evidenceCenter.erpReceiptDoc,
    docpegRisk: evidenceCenter.docpegRisk,
    docpegRiskScore: evidenceCenter.docpegRiskScore,
    onEvidenceQueryChange: evidenceCenter.setEvidenceQuery,
    onEvidenceScopeChange: evidenceCenter.setEvidenceScope,
    onEvidenceSmuIdChange: evidenceCenter.setEvidenceSmuId,
    onEvidenceFilterChange: evidenceCenter.setEvidenceFilter,
    onEvidencePageChange: evidenceCenter.setEvidencePage,
    onEvidenceFocus: evidenceCenter.openEvidenceFocus,
    onDocumentFocus: evidenceCenter.openDocumentFocus,
    onCopyText: (label, value) => void helpers.copyText(label, value),
    onRetryErpnextPush: () => void erp.retryErpnextPush(),
    onExportEvidenceCenter: evidenceCenter.exportEvidenceCenter,
    onExportEvidenceCenterCsv: evidenceCenter.exportEvidenceCenterCsv,
    onDownloadEvidenceCenterPackage: () => void evidenceCenter.downloadEvidenceCenterPackage(),
    onLoadEvidenceCenter: () => void evidenceCenter.loadEvidenceCenter(),
    onOpenDispute: (proofId) => {
      dispute.setShowAdvancedConsensus(true)
      dispute.setDisputeProofId(proofId)
    },
  }
}

export function buildAuditDocPreviewProps({
  conflict,
  document,
  identity,
  refs,
  styles,
  helpers,
}: BuildAuditDocPreviewPropsArgs): AuditDocPreviewProps {
  return {
    consensusConflict: conflict.consensusConflict,
    disputeOpen: conflict.disputeOpen,
    disputeProof: conflict.disputeProof,
    consensusDeviationText: conflict.consensusDeviationText,
    consensusDeviationPercentText: conflict.consensusDeviationPercentText,
    consensusAllowedAbsText: conflict.consensusAllowedAbsText,
    consensusAllowedPctText: conflict.consensusAllowedPctText,
    finalProofReady: document.finalProofReady,
    qrSrc: document.qrSrc,
    verifyUri: document.verifyUri,
    finalProofId: document.finalProofId,
    signFocus: identity.signFocus,
    signStep: identity.signStep,
    executorDid: identity.executorDid,
    supervisorDid: identity.supervisorDid,
    ownerDid: identity.ownerDid,
    inputBaseCls: styles.inputBaseCls,
    previewPdfB64: document.previewPdfB64,
    pdfB64: document.pdfB64,
    previewIsDraft: document.previewIsDraft,
    tripStage: document.tripStage,
    evidenceCount: document.evidenceCount,
    totalHash: document.totalHash,
    activeCode: document.activeCode,
    activePath: document.activePath,
    activeUri: document.activeUri,
    gatePass: document.gatePass,
    gateTotal: document.gateTotal,
    reportedPctText: document.reportedPctText,
    activeSignMarker: document.activeSignMarker,
    pdfPage: document.pdfPage,
    templateSourceText: document.templateSourceText,
    contractorAnchorRef: refs.contractorAnchorRef,
    supervisorAnchorRef: refs.supervisorAnchorRef,
    ownerAnchorRef: refs.ownerAnchorRef,
    previewScrollRef: refs.previewScrollRef,
    pdfCanvasRef: refs.pdfCanvasRef,
    pdfRenderLoading: document.pdfRenderLoading,
    pdfRenderError: document.pdfRenderError,
    draftReady: document.draftReady,
    templateDisplay: document.templateDisplay,
    docModalOpen: document.docModalOpen,
    sampleId: document.sampleId,
    onScrollToSign: helpers.scrollToSign,
    onSupervisorDidChange: identity.setSupervisorDid,
    onOwnerDidChange: identity.setOwnerDid,
    onCopyText: (label, value) => void helpers.copyText(label, value),
    onOpenDocModal: () => helpers.setDocModalOpen(true),
    onCloseDocModal: () => helpers.setDocModalOpen(false),
  }
}

export function buildTripFlowModalProps({
  sign,
  consensus,
  lock,
  delta,
  styles,
}: BuildTripFlowModalPropsArgs): TripFlowModalProps {
  return {
    signOpen: sign.signOpen,
    tripStage: sign.tripStage,
    signStep: sign.signStep,
    signing: sign.signing,
    executorDid: sign.executorDid,
    supervisorDid: sign.supervisorDid,
    ownerDid: sign.ownerDid,
    consensusContractorValue: consensus.consensusContractorValue,
    consensusSupervisorValue: consensus.consensusSupervisorValue,
    consensusOwnerValue: consensus.consensusOwnerValue,
    consensusAllowedDeviation: consensus.consensusAllowedDeviation,
    consensusAllowedDeviationPct: consensus.consensusAllowedDeviationPct,
    consensusBaseValueText: consensus.consensusBaseValueText,
    consensusConflict: consensus.consensusConflict,
    consensusMinValueText: consensus.consensusMinValueText,
    consensusMaxValueText: consensus.consensusMaxValueText,
    consensusDeviationText: consensus.consensusDeviationText,
    consensusDeviationPercentText: consensus.consensusDeviationPercentText,
    consensusAllowedAbsText: consensus.consensusAllowedAbsText,
    consensusAllowedPctText: consensus.consensusAllowedPctText,
    inputBaseCls: styles.inputBaseCls,
    btnAmberCls: styles.btnAmberCls,
    scanLockStage: lock.scanLockStage,
    scanLockProofId: lock.scanLockProofId,
    deltaModalOpen: delta.deltaModalOpen,
    exceedTotalText: delta.exceedTotalText,
    onCloseSignModal: () => sign.setSignOpen(false),
    onDoSign: () => void sign.doSign(),
    onConsensusContractorValueChange: consensus.setConsensusContractorValue,
    onConsensusSupervisorValueChange: consensus.setConsensusSupervisorValue,
    onConsensusOwnerValueChange: consensus.setConsensusOwnerValue,
    onConsensusAllowedDeviationChange: consensus.setConsensusAllowedDeviation,
    onConsensusAllowedDeviationPctChange: consensus.setConsensusAllowedDeviationPct,
    onCloseScanLock: lock.closeScanLock,
    onOpenAdvancedExecution: () => {
      delta.setShowAdvancedExecution(true)
      delta.setDeltaModalOpen(false)
    },
  }
}

export function buildAuditShellProps({
  shell,
  auditDocPreview,
  consensusAudit,
  advancedOps,
}: BuildAuditShellPropsArgs): AuditShellProps {
  return {
    ...shell,
    auditDocPreviewProps: buildAuditDocPreviewProps(auditDocPreview),
    consensusAuditPanelProps: buildConsensusAuditPanelProps(consensusAudit),
    advancedOpsPanelProps: buildAdvancedOpsPanelProps(advancedOps),
  }
}
