import {
  type buildOfflineFooterProps,
  type buildWorkbenchOverlayProps,
} from './workbench/overlayPropsBuilders'
import { type buildWorkbenchSectionsProps } from './workbench/sectionPropsBuilders'

type WorkbenchOverlayBuilderArgs = Parameters<typeof buildWorkbenchOverlayProps>[0]
type OfflineFooterBuilderArgs = Parameters<typeof buildOfflineFooterProps>[0]
type WorkbenchSecondaryBuilderArgs = Parameters<typeof buildWorkbenchSectionsProps>[0]['secondary']
type AuditShellBuilderArgs = WorkbenchSecondaryBuilderArgs['auditShell']
type EvidenceVaultBuilderArgs = WorkbenchSecondaryBuilderArgs['evidenceVault']
type TripFlowModalBuilderArgs = WorkbenchSecondaryBuilderArgs['tripFlowModal']
type EvidenceModalBuilderArgs = WorkbenchSecondaryBuilderArgs['evidenceModal']

type BuildSecondaryOverlayArgs = {
  arFocus: WorkbenchOverlayBuilderArgs['ar']['focus']
  arFullscreen: WorkbenchOverlayBuilderArgs['ar']['fullscreen']
  lat: WorkbenchOverlayBuilderArgs['ar']['lat']
  lng: WorkbenchOverlayBuilderArgs['ar']['lng']
  arRadius: WorkbenchOverlayBuilderArgs['ar']['radius']
  arFilteredItems: WorkbenchOverlayBuilderArgs['ar']['filteredItems']
  arItemsSortedCount: WorkbenchOverlayBuilderArgs['ar']['totalItemsCount']
  arLoading: WorkbenchOverlayBuilderArgs['ar']['loading']
  arFilterMax: WorkbenchOverlayBuilderArgs['ar']['filterMax']
  overlayArStyles: Pick<
    WorkbenchOverlayBuilderArgs['ar'],
    'inputBaseCls' | 'btnBlueCls' | 'btnAmberCls'
  >
  onArCopyText: WorkbenchOverlayBuilderArgs['ar']['onCopyText']
  onArFilterMaxChange: WorkbenchOverlayBuilderArgs['ar']['onFilterMaxChange']
  onArRefresh: WorkbenchOverlayBuilderArgs['ar']['onRefresh']
  onArCloseFocus: WorkbenchOverlayBuilderArgs['ar']['onCloseFocus']
  onArJumpToItem: WorkbenchOverlayBuilderArgs['ar']['onJumpToItem']
  onArCloseFullscreen: WorkbenchOverlayBuilderArgs['ar']['onCloseFullscreen']
  onArSelectFullscreenItem: WorkbenchOverlayBuilderArgs['ar']['onSelectFullscreenItem']
  fingerprintOpen: WorkbenchOverlayBuilderArgs['fingerprint']['open']
  evidenceSource: WorkbenchOverlayBuilderArgs['fingerprint']['evidenceSource']
  onFingerprintClose: WorkbenchOverlayBuilderArgs['fingerprint']['onClose']
  traceOpen: WorkbenchOverlayBuilderArgs['trace']['open']
  traceNodes: WorkbenchOverlayBuilderArgs['trace']['nodes']
  onTraceClose: WorkbenchOverlayBuilderArgs['trace']['onClose']
  executorDid: WorkbenchOverlayBuilderArgs['floatingDid']['executorDid']
  supervisorDid: WorkbenchOverlayBuilderArgs['floatingDid']['supervisorDid']
  ownerDid: WorkbenchOverlayBuilderArgs['floatingDid']['ownerDid']
  riskScore: WorkbenchOverlayBuilderArgs['floatingDid']['riskScore']
  totalHash: WorkbenchOverlayBuilderArgs['floatingDid']['totalHash']
}

type BuildSecondaryOfflineFooterArgs = Pick<
  OfflineFooterBuilderArgs,
  | 'isOnline'
  | 'offlineCount'
  | 'offlineSyncConflicts'
  | 'offlineType'
  | 'inputXsCls'
  | 'btnBlueCls'
  | 'offlineImporting'
  | 'offlineImportName'
  | 'offlineReplay'
  | 'offlineImportRef'
  | 'onOfflineTypeChange'
  | 'onSealOfflinePacket'
  | 'onTriggerImport'
  | 'onExportOfflinePackets'
  | 'onClearOfflinePackets'
  | 'onImportOfflinePackets'
>

type BuildSecondaryEvidenceVaultArgs = {
  evidenceCenter: EvidenceVaultBuilderArgs['evidenceCenter']
  dispute: Omit<EvidenceVaultBuilderArgs['dispute'], 'disputeAllowedAbs' | 'disputeAllowedPct'> & {
    disputeAllowedAbsRaw: unknown
    disputeAllowedPctRaw: unknown
  }
  erp: EvidenceVaultBuilderArgs['erp']
  styles: EvidenceVaultBuilderArgs['styles']
  helpers: EvidenceVaultBuilderArgs['helpers']
}

type BuildSecondaryTripFlowModalArgs = TripFlowModalBuilderArgs
type BuildSecondaryEvidenceModalArgs = EvidenceModalBuilderArgs

type BuildSecondaryStylePacksArgs = {
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  btnAmberCls: string
}

type BuildSecondaryStylePacksResult = {
  auditActionStyles: Pick<
    AuditShellBuilderArgs['consensusAudit']['styles'],
    'inputBaseCls' | 'btnBlueCls' | 'btnGreenCls' | 'btnAmberCls'
  >
  overlayArStyles: BuildSecondaryOverlayArgs['overlayArStyles']
}

function toNullableFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export function buildSovereignWorkbenchSecondaryAuditShell(
  args: AuditShellBuilderArgs,
): AuditShellBuilderArgs {
  return args
}

export function buildSovereignWorkbenchSecondaryStylePacks({
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  btnAmberCls,
}: BuildSecondaryStylePacksArgs): BuildSecondaryStylePacksResult {
  return {
    auditActionStyles: {
      inputBaseCls,
      btnBlueCls,
      btnGreenCls,
      btnAmberCls,
    },
    overlayArStyles: {
      inputBaseCls,
      btnBlueCls,
      btnAmberCls,
    },
  }
}

export function buildSovereignWorkbenchSecondaryOverlay({
  arFocus,
  arFullscreen,
  lat,
  lng,
  arRadius,
  arFilteredItems,
  arItemsSortedCount,
  arLoading,
  arFilterMax,
  overlayArStyles,
  onArCopyText,
  onArFilterMaxChange,
  onArRefresh,
  onArCloseFocus,
  onArJumpToItem,
  onArCloseFullscreen,
  onArSelectFullscreenItem,
  fingerprintOpen,
  evidenceSource,
  onFingerprintClose,
  traceOpen,
  traceNodes,
  onTraceClose,
  executorDid,
  supervisorDid,
  ownerDid,
  riskScore,
  totalHash,
}: BuildSecondaryOverlayArgs): WorkbenchOverlayBuilderArgs {
  return {
    ar: {
      focus: arFocus,
      fullscreen: arFullscreen,
      lat,
      lng,
      radius: arRadius,
      filteredItems: arFilteredItems,
      totalItemsCount: arItemsSortedCount,
      loading: arLoading,
      filterMax: arFilterMax,
      ...overlayArStyles,
      onCopyText: onArCopyText,
      onFilterMaxChange: onArFilterMaxChange,
      onRefresh: onArRefresh,
      onCloseFocus: onArCloseFocus,
      onJumpToItem: onArJumpToItem,
      onCloseFullscreen: onArCloseFullscreen,
      onSelectFullscreenItem: onArSelectFullscreenItem,
    },
    fingerprint: {
      open: fingerprintOpen,
      evidenceSource,
      onClose: onFingerprintClose,
    },
    trace: {
      open: traceOpen,
      nodes: traceNodes,
      onClose: onTraceClose,
    },
    floatingDid: {
      executorDid,
      supervisorDid,
      ownerDid,
      riskScore,
      totalHash,
    },
  }
}

export function buildSovereignWorkbenchSecondaryOfflineFooter({
  isOnline,
  offlineCount,
  offlineSyncConflicts,
  offlineType,
  inputXsCls,
  btnBlueCls,
  offlineImporting,
  offlineImportName,
  offlineReplay,
  offlineImportRef,
  onOfflineTypeChange,
  onSealOfflinePacket,
  onTriggerImport,
  onExportOfflinePackets,
  onClearOfflinePackets,
  onImportOfflinePackets,
}: BuildSecondaryOfflineFooterArgs): OfflineFooterBuilderArgs {
  return {
    isOnline,
    offlineCount,
    offlineSyncConflicts,
    offlineType,
    inputXsCls,
    btnBlueCls,
    offlineImporting,
    offlineImportName,
    offlineReplay,
    offlinePacketsCount: offlineCount,
    offlineImportRef,
    onOfflineTypeChange,
    onSealOfflinePacket,
    onTriggerImport,
    onExportOfflinePackets,
    onClearOfflinePackets,
    onImportOfflinePackets,
  }
}

export function buildSovereignWorkbenchSecondaryEvidenceVault({
  evidenceCenter,
  dispute,
  erp,
  styles,
  helpers,
}: BuildSecondaryEvidenceVaultArgs): EvidenceVaultBuilderArgs {
  const {
    disputeAllowedAbsRaw,
    disputeAllowedPctRaw,
    ...restDispute
  } = dispute
  return {
    evidenceCenter,
    dispute: {
      ...restDispute,
      disputeAllowedAbs: toNullableFiniteNumber(disputeAllowedAbsRaw),
      disputeAllowedPct: toNullableFiniteNumber(disputeAllowedPctRaw),
    },
    erp,
    styles,
    helpers,
  }
}

export function buildSovereignWorkbenchSecondaryTripFlowModal(
  args: BuildSecondaryTripFlowModalArgs,
): TripFlowModalBuilderArgs {
  return args
}

export function buildSovereignWorkbenchSecondaryEvidenceModal(
  args: BuildSecondaryEvidenceModalArgs,
): EvidenceModalBuilderArgs {
  return args
}

export function buildSovereignWorkbenchSecondary(
  args: WorkbenchSecondaryBuilderArgs,
): WorkbenchSecondaryBuilderArgs {
  return args
}
