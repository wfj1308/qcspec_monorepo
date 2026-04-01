import AdvancedConsensusTogglePanel from './AdvancedConsensusTogglePanel'
import ConsensusDisputePanel from './ConsensusDisputePanel'
import DocFinalPanel from './DocFinalPanel'
import FinalPiecePanel from './FinalPiecePanel'
import ScanConfirmPanel from './ScanConfirmPanel'
import SpecdictPanel from './SpecdictPanel'

type Props = {
  showAdvancedConsensus: boolean
  showAcceptanceAdvanced: boolean
  finalPiecePrompt: string
  scanConfirmUri: string
  scanProofId: string
  scanPayload: string
  scanDid: string
  scanConfirmToken: string
  scanning: boolean
  scanRes: Record<string, unknown> | null
  minValueText: string
  maxValueText: string
  deviationText: string
  deviationPercentText: string
  consensusAllowedAbsText: string
  consensusAllowedPctText: string
  consensusConflict: boolean
  disputeProof: string
  disputeOpen: boolean
  disputeProofId: string
  disputeResolutionNote: string
  disputeResult: 'PASS' | 'REJECT'
  disputeResolving: boolean
  disputeResolveRes: Record<string, unknown> | null
  archiveLocked: boolean
  docFinalPassphrase: string
  docFinalIncludeUnsettled: boolean
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
  specdictProjectUris: string
  specdictMinSamples: string
  specdictNamespace: string
  specdictCommit: boolean
  specdictLoading: boolean
  specdictExporting: boolean
  specdictRuleTotal: number
  specdictHighRisk: number
  specdictBestPractice: number
  specdictBundleUri: string
  successPatterns: string[]
  highRiskItems: string[]
  bestPracticeItems: string[]
  weightEntriesText: string[]
  hasSpecdictRes: boolean
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  btnAmberCls: string
  onToggleAdvancedConsensus: () => void
  onCopyFinalPiece: () => void
  onScanPayloadChange: (value: string) => void
  onScanDidChange: (value: string) => void
  onScanProofIdChange: (value: string) => void
  onFillScanToken: () => void
  onScanConfirm: () => void
  onToggleAcceptanceAdvanced: () => void
  onCopyConflictSummary: () => void
  onJumpToDispute: () => void
  onDisputeProofIdChange: (value: string) => void
  onDisputeResolutionNoteChange: (value: string) => void
  onDisputeResultChange: (value: 'PASS' | 'REJECT') => void
  onResolveDispute: () => void
  onDocFinalPassphraseChange: (value: string) => void
  onDocFinalIncludeUnsettledChange: (value: boolean) => void
  onExportProjectDocFinal: () => void
  onFinalizeProjectDocFinal: () => void
  onProjectUrisChange: (value: string) => void
  onMinSamplesChange: (value: string) => void
  onNamespaceChange: (value: string) => void
  onCommitChange: (value: boolean) => void
  onRunSpecdictEvolve: () => void
  onRunSpecdictExport: () => void
  onOneClickWriteGlobal: () => void
}

export default function SovereignConsensusAuditPanels({
  showAdvancedConsensus,
  showAcceptanceAdvanced,
  finalPiecePrompt,
  scanConfirmUri,
  scanProofId,
  scanPayload,
  scanDid,
  scanConfirmToken,
  scanning,
  scanRes,
  minValueText,
  maxValueText,
  deviationText,
  deviationPercentText,
  consensusAllowedAbsText,
  consensusAllowedPctText,
  consensusConflict,
  disputeProof,
  disputeOpen,
  disputeProofId,
  disputeResolutionNote,
  disputeResult,
  disputeResolving,
  disputeResolveRes,
  archiveLocked,
  docFinalPassphrase,
  docFinalIncludeUnsettled,
  docFinalExporting,
  docFinalFinalizing,
  docFinalRes,
  docFinalAuditUrl,
  docFinalVerifyBaseUrl,
  verifyUri,
  disputeProofShort,
  offlineQueueSize,
  offlineSyncConflicts,
  apiProjectUri,
  docFinalQrSrc,
  specdictProjectUris,
  specdictMinSamples,
  specdictNamespace,
  specdictCommit,
  specdictLoading,
  specdictExporting,
  specdictRuleTotal,
  specdictHighRisk,
  specdictBestPractice,
  specdictBundleUri,
  successPatterns,
  highRiskItems,
  bestPracticeItems,
  weightEntriesText,
  hasSpecdictRes,
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  btnAmberCls,
  onToggleAdvancedConsensus,
  onCopyFinalPiece,
  onScanPayloadChange,
  onScanDidChange,
  onScanProofIdChange,
  onFillScanToken,
  onScanConfirm,
  onToggleAcceptanceAdvanced,
  onCopyConflictSummary,
  onJumpToDispute,
  onDisputeProofIdChange,
  onDisputeResolutionNoteChange,
  onDisputeResultChange,
  onResolveDispute,
  onDocFinalPassphraseChange,
  onDocFinalIncludeUnsettledChange,
  onExportProjectDocFinal,
  onFinalizeProjectDocFinal,
  onProjectUrisChange,
  onMinSamplesChange,
  onNamespaceChange,
  onCommitChange,
  onRunSpecdictEvolve,
  onRunSpecdictExport,
  onOneClickWriteGlobal,
}: Props) {
  return (
    <>
      <AdvancedConsensusTogglePanel
        showAdvancedConsensus={showAdvancedConsensus}
        onToggleAdvancedConsensus={onToggleAdvancedConsensus}
      />
      {showAdvancedConsensus && (
        <>
          <FinalPiecePanel
            finalPiecePrompt={finalPiecePrompt}
            onCopyFinalPiece={onCopyFinalPiece}
          />
          <ScanConfirmPanel
            scanConfirmUri={scanConfirmUri}
            scanProofId={scanProofId}
            scanPayload={scanPayload}
            scanDid={scanDid}
            scanConfirmToken={scanConfirmToken}
            scanning={scanning}
            showAcceptanceAdvanced={showAcceptanceAdvanced}
            scanRes={scanRes}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            btnGreenCls={btnGreenCls}
            onScanPayloadChange={onScanPayloadChange}
            onScanDidChange={onScanDidChange}
            onScanProofIdChange={onScanProofIdChange}
            onFillScanToken={onFillScanToken}
            onScanConfirm={onScanConfirm}
            onToggleAdvanced={onToggleAcceptanceAdvanced}
          />
          <ConsensusDisputePanel
            minValueText={minValueText}
            maxValueText={maxValueText}
            deviationText={deviationText}
            deviationPercentText={deviationPercentText}
            consensusAllowedAbsText={consensusAllowedAbsText}
            consensusAllowedPctText={consensusAllowedPctText}
            consensusConflict={consensusConflict}
            disputeProof={disputeProof}
            disputeOpen={disputeOpen}
            disputeProofId={disputeProofId}
            disputeResolutionNote={disputeResolutionNote}
            disputeResult={disputeResult}
            disputeResolving={disputeResolving}
            disputeResolveRes={disputeResolveRes}
            inputBaseCls={inputBaseCls}
            btnAmberCls={btnAmberCls}
            onCopyConflictSummary={onCopyConflictSummary}
            onJumpToDispute={onJumpToDispute}
            onDisputeProofIdChange={onDisputeProofIdChange}
            onDisputeResolutionNoteChange={onDisputeResolutionNoteChange}
            onDisputeResultChange={onDisputeResultChange}
            onResolveDispute={onResolveDispute}
          />
          <DocFinalPanel
            archiveLocked={archiveLocked}
            docFinalPassphrase={docFinalPassphrase}
            docFinalIncludeUnsettled={docFinalIncludeUnsettled}
            docFinalExporting={docFinalExporting}
            docFinalFinalizing={docFinalFinalizing}
            docFinalRes={docFinalRes}
            docFinalAuditUrl={docFinalAuditUrl}
            docFinalVerifyBaseUrl={docFinalVerifyBaseUrl}
            verifyUri={verifyUri}
            disputeOpen={disputeOpen}
            disputeProofShort={disputeProofShort}
            offlineQueueSize={offlineQueueSize}
            offlineSyncConflicts={offlineSyncConflicts}
            apiProjectUri={apiProjectUri}
            docFinalQrSrc={docFinalQrSrc}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            btnGreenCls={btnGreenCls}
            onDocFinalPassphraseChange={onDocFinalPassphraseChange}
            onDocFinalIncludeUnsettledChange={onDocFinalIncludeUnsettledChange}
            onExportProjectDocFinal={onExportProjectDocFinal}
            onFinalizeProjectDocFinal={onFinalizeProjectDocFinal}
          />
          <SpecdictPanel
            specdictProjectUris={specdictProjectUris}
            specdictMinSamples={specdictMinSamples}
            specdictNamespace={specdictNamespace}
            specdictCommit={specdictCommit}
            specdictLoading={specdictLoading}
            specdictExporting={specdictExporting}
            specdictRuleTotal={specdictRuleTotal}
            specdictHighRisk={specdictHighRisk}
            specdictBestPractice={specdictBestPractice}
            specdictBundleUri={specdictBundleUri}
            successPatterns={successPatterns}
            highRiskItems={highRiskItems}
            bestPracticeItems={bestPracticeItems}
            weightEntriesText={weightEntriesText}
            hasSpecdictRes={hasSpecdictRes}
            inputBaseCls={inputBaseCls}
            btnBlueCls={btnBlueCls}
            btnGreenCls={btnGreenCls}
            onProjectUrisChange={onProjectUrisChange}
            onMinSamplesChange={onMinSamplesChange}
            onNamespaceChange={onNamespaceChange}
            onCommitChange={onCommitChange}
            onRunSpecdictEvolve={onRunSpecdictEvolve}
            onRunSpecdictExport={onRunSpecdictExport}
            onOneClickWriteGlobal={onOneClickWriteGlobal}
          />
        </>
      )}
    </>
  )
}
