import type { MutableRefObject } from 'react'

type BuildWorkbenchSectionHandlersArgs = {
  runReadinessCheck: (silent?: boolean) => void | Promise<void>
  setShowRolePlaybook: (updater: (value: boolean) => boolean) => void
  importGenesis: () => void | Promise<void>
  loadBuiltinLedger400: () => void | Promise<void>
  setShowLeftSummary: (updater: (value: boolean) => boolean) => void
  selectNode: (code: string) => void | Promise<void>
  setTraceOpen: (value: boolean) => void
  handleScanEntry: () => void | Promise<void>
  activeUri: string
  loadContext: (uri: string, componentType: string) => void | Promise<void>
  compType: string
  onEvidence: (files: FileList | null) => void
  setFingerprintOpen: (value: boolean) => void
  applyDelta: () => void | Promise<void>
  setDeltaAmount: (value: string) => void
  deltaSuggest: number
  setDeltaReason: (value: string) => void
  setShowAdvancedExecution: (value: boolean) => void
  submitTrip: () => void | Promise<void>
  submitTripMock: () => void | Promise<void>
  recordRejectTrip: () => void | Promise<void>
  copyText: (label: string, value: string) => void | Promise<void>
  runArOverlay: () => void | Promise<void>
  offlineImportRef: MutableRefObject<HTMLInputElement | null>
}

const SUGGEST_DELTA_REASON = '超量补差'

export function buildSovereignWorkbenchSectionHandlers({
  runReadinessCheck,
  setShowRolePlaybook,
  importGenesis,
  loadBuiltinLedger400,
  setShowLeftSummary,
  selectNode,
  setTraceOpen,
  handleScanEntry,
  activeUri,
  loadContext,
  compType,
  onEvidence,
  setFingerprintOpen,
  applyDelta,
  setDeltaAmount,
  deltaSuggest,
  setDeltaReason,
  setShowAdvancedExecution,
  submitTrip,
  submitTripMock,
  recordRejectTrip,
  copyText,
  runArOverlay,
  offlineImportRef,
}: BuildWorkbenchSectionHandlersArgs) {
  const handleRunReadinessCheck = () => void runReadinessCheck(false)
  const handleToggleRolePlaybook = () => setShowRolePlaybook((value) => !value)
  const handleImportGenesis = () => void importGenesis()
  const handleLoadBuiltinLedger400 = () => void loadBuiltinLedger400()
  const handleToggleTreeSummary = () => setShowLeftSummary((value) => !value)
  const handleSelectNode = (code: string) => void selectNode(code)
  const handleOpenTrace = () => setTraceOpen(true)
  const triggerScanEntry = () => void handleScanEntry()
  const handleLoadContext = () => {
    if (!activeUri) return
    void loadContext(activeUri, compType)
  }
  const handleEvidenceUpload = (files: FileList | null) => onEvidence(files)
  const handleOpenFingerprint = () => setFingerprintOpen(true)
  const handleApplyDelta = () => void applyDelta()
  const handleSuggestDelta = () => {
    const safeDeltaSuggest = Number.isFinite(deltaSuggest) ? deltaSuggest : 0
    setDeltaAmount(safeDeltaSuggest.toFixed(3))
    setDeltaReason(SUGGEST_DELTA_REASON)
    setShowAdvancedExecution(true)
  }
  const handleSubmitTrip = () => void submitTrip()
  const handleSubmitTripMock = () => void submitTripMock()
  const handleRecordRejectTrip = () => void recordRejectTrip()
  const handleArCopyText = (label: string, value: string) => void copyText(label, value)
  const handleArRefresh = () => void runArOverlay()
  const handleCloseFingerprint = () => setFingerprintOpen(false)
  const handleCloseTrace = () => setTraceOpen(false)
  const handleTriggerOfflineImport = () => offlineImportRef.current?.click()

  return {
    handleRunReadinessCheck,
    handleToggleRolePlaybook,
    handleImportGenesis,
    handleLoadBuiltinLedger400,
    handleToggleTreeSummary,
    handleSelectNode,
    handleOpenTrace,
    triggerScanEntry,
    handleLoadContext,
    handleEvidenceUpload,
    handleOpenFingerprint,
    handleApplyDelta,
    handleSuggestDelta,
    handleSubmitTrip,
    handleSubmitTripMock,
    handleRecordRejectTrip,
    handleArCopyText,
    handleArRefresh,
    handleCloseFingerprint,
    handleCloseTrace,
    handleTriggerOfflineImport,
  }
}
