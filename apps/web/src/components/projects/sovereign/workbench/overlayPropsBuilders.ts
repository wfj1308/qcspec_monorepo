import type { ComponentProps } from 'react'

import SovereignEvidenceModals from '../SovereignEvidenceModals'
import SovereignOfflineFooter from '../SovereignOfflineFooter'
import SovereignWorkbenchOverlays from '../SovereignWorkbenchOverlays'

type EvidenceModalProps = ComponentProps<typeof SovereignEvidenceModals>
type OfflineFooterProps = ComponentProps<typeof SovereignOfflineFooter>
type WorkbenchOverlayProps = ComponentProps<typeof SovereignWorkbenchOverlays>

type BuildWorkbenchOverlayPropsArgs = {
  ar: WorkbenchOverlayProps['ar']
  fingerprint: Omit<WorkbenchOverlayProps['fingerprint'], 'evidence'> & {
    evidenceSource: Array<{ name: string; ntp?: unknown }>
  }
  trace: WorkbenchOverlayProps['trace']
  floatingDid: WorkbenchOverlayProps['floatingDid']
}

type BuildEvidenceModalPropsArgs = {
  evidencePreview: Pick<
    EvidenceModalProps,
    | 'evidenceOpen'
    | 'evidenceFocus'
    | 'geoTemporalBlocked'
    | 'activeCode'
    | 'activeUri'
    | 'lat'
    | 'lng'
    | 'executorDid'
    | 'sampleId'
    | 'onCloseEvidencePreview'
  >
  evidenceCenter: Pick<
    EvidenceModalProps,
    | 'evidenceCenterFocus'
    | 'evidenceCenterDocFocus'
    | 'onCloseEvidenceFocus'
    | 'onCloseDocumentFocus'
  >
}

type BuildOfflineFooterPropsArgs = Pick<
  OfflineFooterProps,
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
> & {
  offlinePacketsCount: number
  onOfflineTypeChange: OfflineFooterProps['onOfflineTypeChange']
  onSealOfflinePacket: () => void | Promise<void>
  onTriggerImport: () => void
  onExportOfflinePackets: () => void
  onClearOfflinePackets: () => void
  onImportOfflinePackets: (file: File | null) => void | Promise<void>
}

export function buildWorkbenchOverlayProps({
  ar,
  fingerprint,
  trace,
  floatingDid,
}: BuildWorkbenchOverlayPropsArgs): WorkbenchOverlayProps {
  const { evidenceSource, ...fingerprintRest } = fingerprint

  return {
    ar,
    fingerprint: {
      ...fingerprintRest,
      evidence: evidenceSource.map((item) => ({
        name: item.name,
        ntp: String(item.ntp || '-'),
      })),
    },
    trace,
    floatingDid,
  }
}

export function buildEvidenceModalProps({
  evidencePreview,
  evidenceCenter,
}: BuildEvidenceModalPropsArgs): EvidenceModalProps {
  return {
    ...evidencePreview,
    ...evidenceCenter,
  }
}

export function buildOfflineFooterProps({
  isOnline,
  offlineCount,
  offlineSyncConflicts,
  offlineType,
  inputXsCls,
  btnBlueCls,
  offlineImporting,
  offlineImportName,
  offlineReplay,
  offlinePacketsCount,
  offlineImportRef,
  onOfflineTypeChange,
  onSealOfflinePacket,
  onTriggerImport,
  onExportOfflinePackets,
  onClearOfflinePackets,
  onImportOfflinePackets,
}: BuildOfflineFooterPropsArgs): OfflineFooterProps {
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
    offlinePacketsCount,
    offlineImportRef,
    onOfflineTypeChange,
    onSealOfflinePacket: () => void onSealOfflinePacket(),
    onTriggerImport,
    onExportOfflinePackets,
    onClearOfflinePackets,
    onImportOfflinePackets: (file) => void onImportOfflinePackets(file),
  }
}
