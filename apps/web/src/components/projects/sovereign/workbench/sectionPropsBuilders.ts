import type { ComponentProps } from 'react'

import GenesisTree from '../GenesisTree'
import SovereignGenesisOverview from '../SovereignGenesisOverview'
import SovereignWorkbench from '../SovereignWorkbench'
import SovereignWorkbenchHero from '../SovereignWorkbenchHero'
import SovereignWorkbenchSections from '../SovereignWorkbenchSections'
import { buildAuditShellProps, buildEvidenceVaultProps, buildTripFlowModalProps } from './auditPanelPropsBuilders'
import { buildEvidenceModalProps, buildOfflineFooterProps, buildWorkbenchOverlayProps } from './overlayPropsBuilders'

type GenesisTreeProps = ComponentProps<typeof GenesisTree>
type GenesisOverviewProps = ComponentProps<typeof SovereignGenesisOverview>
type TripWorkbenchProps = ComponentProps<typeof SovereignWorkbench>
type WorkbenchHeroProps = ComponentProps<typeof SovereignWorkbenchHero>
type WorkbenchSectionsProps = ComponentProps<typeof SovereignWorkbenchSections>

type BuildWorkbenchHeroPropsArgs = Pick<
  WorkbenchHeroProps,
  | 'activePath'
  | 'displayProjectUri'
  | 'progressPct'
  | 'isOnline'
  | 'offlineCount'
  | 'nodeCount'
  | 'activeCode'
  | 'totalHash'
  | 'isTripView'
  | 'finalProofReady'
  | 'btnBlueCls'
  | 'onNavigateAudit'
>

type BuildGenesisOverviewPropsArgs = Pick<
  GenesisOverviewProps,
  | 'isGenesisView'
  | 'readinessOverall'
  | 'readinessLoading'
  | 'readinessPercent'
  | 'readinessLayers'
  | 'readinessAction'
  | 'showRolePlaybook'
  | 'btnBlueCls'
  | 'btnGreenCls'
  | 'btnAmberCls'
  | 'panelCls'
  | 'apiProjectUri'
  | 'specBinding'
  | 'gateBinding'
  | 'normRefs'
  | 'isSpecBound'
  | 'lifecycle'
  | 'activeCode'
  | 'availableTotal'
  | 'activePath'
  | 'displayProjectUri'
  | 'onRunReadinessCheck'
  | 'onToggleRolePlaybook'
  | 'onNavigateTrip'
  | 'onNavigateAudit'
>

type BuildGenesisTreePropsArgs = {
  styles: Pick<GenesisTreeProps, 'panelCls' | 'inputBaseCls' | 'btnBlueCls'>
  files: Pick<GenesisTreeProps, 'boqFileRef' | 'fileName'>
  importState: Pick<
    GenesisTreeProps,
    | 'importing'
    | 'importJobId'
    | 'importStatusText'
    | 'importProgress'
    | 'importError'
  >
  tree: Pick<
    GenesisTreeProps,
    | 'showLeftSummary'
    | 'treeQuery'
    | 'treeSearch'
    | 'nodes'
    | 'roots'
    | 'byCode'
    | 'aggMap'
    | 'expandedCodes'
    | 'nodePathMap'
  >
  actions: {
    onSelectFile: GenesisTreeProps['onSelectFile']
    onImportGenesis: () => void | Promise<void>
    onLoadBuiltinLedger400: () => void | Promise<void>
    onToggleSummary: () => void
    onTreeQueryChange: GenesisTreeProps['onTreeQueryChange']
    onToggleExpanded: GenesisTreeProps['onToggleExpanded']
    onSelectNode: GenesisTreeProps['onSelectNode']
  }
}

type BuildTripWorkbenchPropsArgs = {
  styles: Pick<
    TripWorkbenchProps,
    'panelCls' | 'inputBaseCls' | 'btnBlueCls' | 'btnAmberCls' | 'btnGreenCls' | 'btnRedCls'
  >
  display: Pick<
    TripWorkbenchProps,
    | 'hashing'
    | 'templateDisplay'
    | 'isSpecBound'
    | 'specBinding'
    | 'gateBinding'
    | 'displayMeta'
    | 'componentTypeOptions'
  >
  context: Pick<
    TripWorkbenchProps,
    | 'compType'
    | 'loadingCtx'
    | 'contextError'
    | 'sampleId'
    | 'effectiveSchema'
    | 'form'
    | 'normRefs'
  >
  scan: Pick<
    TripWorkbenchProps,
    | 'geoFormLocked'
    | 'scanEntryStatus'
    | 'scanEntryAt'
    | 'scanEntryToken'
    | 'scanEntryRequired'
    | 'scanEntryTokenHash'
    | 'scanChainBadge'
    | 'scanEntryLatest'
  >
  evidence: Pick<
    TripWorkbenchProps,
    | 'evidence'
    | 'evidenceName'
    | 'evidenceAccept'
    | 'evidenceLabel'
    | 'evidenceHint'
    | 'evidenceFileRef'
  >
  delta: Pick<
    TripWorkbenchProps,
    | 'showAdvancedExecution'
    | 'deltaAmount'
    | 'deltaReason'
    | 'applyingDelta'
    | 'variationRes'
    | 'claimQty'
    | 'claimQtyProvided'
    | 'measuredQtyValue'
    | 'deltaSuggest'
  >
  geo: Pick<
    TripWorkbenchProps,
    | 'geoValid'
    | 'geoFenceWarning'
    | 'temporalBlocked'
    | 'geoFenceActive'
    | 'geoDistance'
    | 'geoAnchor'
    | 'lat'
    | 'lng'
  >
  execution: Pick<
    TripWorkbenchProps,
    | 'tripStage'
    | 'effectiveRiskScore'
    | 'executing'
    | 'mockGenerating'
    | 'rejecting'
  >
  actions: {
    onTraceOpen: TripWorkbenchProps['onTraceOpen']
    onScanEntry: () => void | Promise<void>
    onScanEntryTokenChange: TripWorkbenchProps['onScanEntryTokenChange']
    onScanEntryRequiredChange: TripWorkbenchProps['onScanEntryRequiredChange']
    onSampleIdChange: TripWorkbenchProps['onSampleIdChange']
    onCompTypeChange: TripWorkbenchProps['onCompTypeChange']
    onExecutorDidChange: TripWorkbenchProps['onExecutorDidChange']
    onLoadContext: () => void | Promise<void>
    onFormChange: TripWorkbenchProps['onFormChange']
    onEvidence: TripWorkbenchProps['onEvidence']
    onFingerprintOpen: TripWorkbenchProps['onFingerprintOpen']
    onEvidencePreview: TripWorkbenchProps['onEvidencePreview']
    onDeltaAmountChange: TripWorkbenchProps['onDeltaAmountChange']
    onDeltaReasonChange: TripWorkbenchProps['onDeltaReasonChange']
    onApplyDelta: () => void | Promise<void>
    onSuggestDelta: TripWorkbenchProps['onSuggestDelta']
    onClaimQtyChange: TripWorkbenchProps['onClaimQtyChange']
    onSubmitTrip: () => void | Promise<void>
    onSubmitTripMock: () => void | Promise<void>
    onRecordRejectTrip: () => void | Promise<void>
    onLatChange: TripWorkbenchProps['onLatChange']
    onLngChange: TripWorkbenchProps['onLngChange']
  }
  helpers: Pick<
    TripWorkbenchProps,
    'sanitizeMeasuredInput' | 'metricLabel' | 'toChineseCompType'
  >
}

type BuildWorkbenchPrimarySectionPropsArgs = {
  hero: BuildWorkbenchHeroPropsArgs
  genesisOverview: BuildGenesisOverviewPropsArgs
  genesisTree: BuildGenesisTreePropsArgs
  tripWorkbench: BuildTripWorkbenchPropsArgs
}

type BuildWorkbenchSecondarySectionPropsArgs = {
  auditShell: Parameters<typeof buildAuditShellProps>[0]
  evidenceVault: Parameters<typeof buildEvidenceVaultProps>[0]
  tripFlowModal: Parameters<typeof buildTripFlowModalProps>[0]
  evidenceModal: Parameters<typeof buildEvidenceModalProps>[0]
  workbenchOverlay: Parameters<typeof buildWorkbenchOverlayProps>[0]
  offlineFooter: Parameters<typeof buildOfflineFooterProps>[0]
}

type BuildWorkbenchSectionsPropsArgs = {
  shell: WorkbenchSectionsProps['shell']
  primary: BuildWorkbenchPrimarySectionPropsArgs
  secondary: BuildWorkbenchSecondarySectionPropsArgs
}

export function buildGenesisTreeProps({
  styles,
  files,
  importState,
  tree,
  actions,
}: BuildGenesisTreePropsArgs): GenesisTreeProps {
  return {
    panelCls: styles.panelCls,
    inputBaseCls: styles.inputBaseCls,
    btnBlueCls: styles.btnBlueCls,
    boqFileRef: files.boqFileRef,
    fileName: files.fileName,
    importing: importState.importing,
    importJobId: importState.importJobId,
    importStatusText: importState.importStatusText,
    importProgress: importState.importProgress,
    importError: importState.importError,
    showLeftSummary: tree.showLeftSummary,
    treeQuery: tree.treeQuery,
    treeSearch: tree.treeSearch,
    nodes: tree.nodes,
    roots: tree.roots,
    byCode: tree.byCode,
    aggMap: tree.aggMap,
    expandedCodes: tree.expandedCodes,
    nodePathMap: tree.nodePathMap,
    onSelectFile: actions.onSelectFile,
    onImportGenesis: () => void actions.onImportGenesis(),
    onLoadBuiltinLedger400: () => void actions.onLoadBuiltinLedger400(),
    onToggleSummary: actions.onToggleSummary,
    onTreeQueryChange: actions.onTreeQueryChange,
    onToggleExpanded: actions.onToggleExpanded,
    onSelectNode: (code) => void actions.onSelectNode(code),
  }
}

export function buildWorkbenchHeroProps({
  activePath,
  displayProjectUri,
  progressPct,
  isOnline,
  offlineCount,
  nodeCount,
  activeCode,
  totalHash,
  isTripView,
  finalProofReady,
  btnBlueCls,
  onNavigateAudit,
}: BuildWorkbenchHeroPropsArgs): WorkbenchHeroProps {
  return {
    activePath,
    displayProjectUri,
    progressPct,
    isOnline,
    offlineCount,
    nodeCount,
    activeCode,
    totalHash,
    isTripView,
    finalProofReady,
    btnBlueCls,
    onNavigateAudit,
  }
}

export function buildGenesisOverviewProps({
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
  activeCode,
  availableTotal,
  activePath,
  displayProjectUri,
  onRunReadinessCheck,
  onToggleRolePlaybook,
  onNavigateTrip,
  onNavigateAudit,
}: BuildGenesisOverviewPropsArgs): GenesisOverviewProps {
  return {
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
    activeCode,
    availableTotal,
    activePath,
    displayProjectUri,
    onRunReadinessCheck,
    onToggleRolePlaybook,
    onNavigateTrip,
    onNavigateAudit,
  }
}

export function buildTripWorkbenchProps({
  styles,
  display,
  context,
  scan,
  evidence,
  delta,
  geo,
  execution,
  actions,
  helpers,
}: BuildTripWorkbenchPropsArgs): TripWorkbenchProps {
  return {
    panelCls: styles.panelCls,
    inputBaseCls: styles.inputBaseCls,
    btnBlueCls: styles.btnBlueCls,
    btnAmberCls: styles.btnAmberCls,
    btnGreenCls: styles.btnGreenCls,
    btnRedCls: styles.btnRedCls,
    hashing: display.hashing,
    templateDisplay: display.templateDisplay,
    isSpecBound: display.isSpecBound,
    specBinding: display.specBinding,
    gateBinding: display.gateBinding,
    displayMeta: display.displayMeta,
    compType: context.compType,
    componentTypeOptions: display.componentTypeOptions,
    loadingCtx: context.loadingCtx,
    geoFormLocked: scan.geoFormLocked,
    scanEntryStatus: scan.scanEntryStatus,
    scanEntryAt: scan.scanEntryAt,
    scanEntryToken: scan.scanEntryToken,
    scanEntryRequired: scan.scanEntryRequired,
    scanEntryTokenHash: scan.scanEntryTokenHash,
    scanChainBadge: scan.scanChainBadge,
    scanEntryLatest: scan.scanEntryLatest,
    normRefs: context.normRefs,
    contextError: context.contextError,
    sampleId: context.sampleId,
    effectiveSchema: context.effectiveSchema,
    form: context.form,
    evidence: evidence.evidence,
    evidenceName: evidence.evidenceName,
    evidenceAccept: evidence.evidenceAccept,
    evidenceLabel: evidence.evidenceLabel,
    evidenceHint: evidence.evidenceHint,
    geoValid: geo.geoValid,
    geoFenceWarning: geo.geoFenceWarning,
    showAdvancedExecution: delta.showAdvancedExecution,
    deltaAmount: delta.deltaAmount,
    deltaReason: delta.deltaReason,
    applyingDelta: delta.applyingDelta,
    variationRes: delta.variationRes,
    claimQty: delta.claimQty,
    claimQtyProvided: delta.claimQtyProvided,
    measuredQtyValue: delta.measuredQtyValue,
    deltaSuggest: delta.deltaSuggest,
    temporalBlocked: geo.temporalBlocked,
    geoFenceActive: geo.geoFenceActive,
    geoDistance: geo.geoDistance,
    geoAnchor: geo.geoAnchor,
    tripStage: execution.tripStage,
    effectiveRiskScore: execution.effectiveRiskScore,
    executing: execution.executing,
    mockGenerating: execution.mockGenerating,
    rejecting: execution.rejecting,
    evidenceFileRef: evidence.evidenceFileRef,
    lat: geo.lat,
    lng: geo.lng,
    onTraceOpen: actions.onTraceOpen,
    onScanEntry: () => void actions.onScanEntry(),
    onScanEntryTokenChange: actions.onScanEntryTokenChange,
    onScanEntryRequiredChange: actions.onScanEntryRequiredChange,
    onSampleIdChange: actions.onSampleIdChange,
    onCompTypeChange: actions.onCompTypeChange,
    onExecutorDidChange: actions.onExecutorDidChange,
    onLoadContext: () => void actions.onLoadContext(),
    onFormChange: actions.onFormChange,
    onEvidence: (files) => void actions.onEvidence(files),
    onFingerprintOpen: actions.onFingerprintOpen,
    onEvidencePreview: actions.onEvidencePreview,
    onDeltaAmountChange: actions.onDeltaAmountChange,
    onDeltaReasonChange: actions.onDeltaReasonChange,
    onApplyDelta: () => void actions.onApplyDelta(),
    onSuggestDelta: actions.onSuggestDelta,
    onClaimQtyChange: actions.onClaimQtyChange,
    onSubmitTrip: () => void actions.onSubmitTrip(),
    onSubmitTripMock: () => void actions.onSubmitTripMock(),
    onRecordRejectTrip: () => void actions.onRecordRejectTrip(),
    onLatChange: actions.onLatChange,
    onLngChange: actions.onLngChange,
    sanitizeMeasuredInput: helpers.sanitizeMeasuredInput,
    metricLabel: helpers.metricLabel,
    toChineseCompType: helpers.toChineseCompType,
  }
}

export function buildWorkbenchPrimarySectionProps({
  hero,
  genesisOverview,
  genesisTree,
  tripWorkbench,
}: BuildWorkbenchPrimarySectionPropsArgs) {
  return {
    workbenchHeroProps: buildWorkbenchHeroProps(hero),
    genesisOverviewProps: buildGenesisOverviewProps(genesisOverview),
    genesisTreeProps: buildGenesisTreeProps(genesisTree),
    tripWorkbenchProps: buildTripWorkbenchProps(tripWorkbench),
  }
}

export function buildWorkbenchSecondarySectionProps({
  auditShell,
  evidenceVault,
  tripFlowModal,
  evidenceModal,
  workbenchOverlay,
  offlineFooter,
}: BuildWorkbenchSecondarySectionPropsArgs) {
  return {
    auditShellProps: buildAuditShellProps(auditShell),
    evidenceVaultProps: buildEvidenceVaultProps(evidenceVault),
    tripFlowModalProps: buildTripFlowModalProps(tripFlowModal),
    evidenceModalProps: buildEvidenceModalProps(evidenceModal),
    workbenchOverlayProps: buildWorkbenchOverlayProps(workbenchOverlay),
    offlineFooterProps: buildOfflineFooterProps(offlineFooter),
  }
}

export function buildWorkbenchSectionsProps({
  shell,
  primary,
  secondary,
}: BuildWorkbenchSectionsPropsArgs): WorkbenchSectionsProps {
  return {
    shell,
    primary: buildWorkbenchPrimarySectionProps(primary),
    secondary: buildWorkbenchSecondarySectionProps(secondary),
  }
}

