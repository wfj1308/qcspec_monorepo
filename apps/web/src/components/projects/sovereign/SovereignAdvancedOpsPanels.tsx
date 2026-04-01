import ArPanel from './ArPanel'
import AssetAppraisalPanel from './AssetAppraisalPanel'
import ExecutionPegPanels from './ExecutionPegPanels'
import FingerprintPanel from './FingerprintPanel'
import GeoFencePanel from './GeoFencePanel'
import P2PSyncPanel from './P2PSyncPanel'

type ScanChainBadge = {
  cls: string
  label: string
}

type TemporalWindow = {
  start: number
  end: number
}

type MerkleStep = {
  depth: number
  position: string
  sibling_hash: string
  combined_hash: string
}

type Props = {
  show: boolean
  meshpegCloudName: string
  meshpegBimName: string
  meshpegRunning: boolean
  meshpegRes: Record<string, unknown> | null
  formulaExpr: string
  formulaRunning: boolean
  formulaRes: Record<string, unknown> | null
  gatewayRes: Record<string, unknown> | null
  assetAppraising: boolean
  assetAppraisal: Record<string, unknown> | null
  arRadius: string
  arLimit: string
  arLoading: boolean
  activeUri: string
  latestProofId: string
  totalHashShort: string
  nearestAnchorText: string
  arItems: Array<Record<string, unknown>>
  geoFenceStatusText: string
  scanEntryStatus: 'idle' | 'ok' | 'blocked'
  scanEntryRequired: boolean
  scanEntryToken: string
  scanChainBadge: ScanChainBadge
  geoAnchor: Record<string, unknown> | null
  geoDistance: number
  temporalWindow: TemporalWindow | null
  geoTemporalBlocked: boolean
  currentSubdivisionText: string
  showFingerprintAdvanced: boolean
  unitLoading: boolean
  unitProofId: string
  unitMaxRows: string
  unitRes: Record<string, unknown> | null
  unitVerifying: boolean
  unitVerifyMsg: string
  itemPathSteps: MerkleStep[]
  unitPathSteps: MerkleStep[]
  p2pNodeId: string
  offlineQueueSize: number
  p2pLastSync: string
  p2pAutoSync: boolean
  p2pPeers: string
  merkleRootText: string
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  btnAmberCls: string
  formatNumber: (value: unknown) => string
  onMeshpegCloudNameChange: (value: string) => void
  onMeshpegBimNameChange: (value: string) => void
  onRunMeshpeg: () => void
  onFormulaExprChange: (value: string) => void
  onRunFormulaPeg: () => void
  onRunGatewaySync: () => void
  onCopyGatewayJson: () => void
  onDownloadGatewayJson: () => void
  onBuildAssetAppraisal: () => void
  onCopyAssetAppraisalJson: () => void
  onDownloadAssetAppraisalJson: () => void
  onArRadiusChange: (value: string) => void
  onArLimitChange: (value: string) => void
  onRunArOverlay: () => void
  onOpenArFullscreen: () => void
  onFocusArItem: (item: Record<string, unknown>) => void
  onToggleFingerprintAdvanced: () => void
  onUnitProofIdChange: (value: string) => void
  onUnitMaxRowsChange: (value: string) => void
  onCalcUnitMerkle: () => void
  onUseCurrentProofForUnit: () => void
  onVerifyUnitMerkle: () => void
  onExportMerkleJson: () => void
  onP2PAutoSyncChange: (checked: boolean) => void
  onP2PPeersChange: (value: string) => void
  onExportP2PManifest: () => void
  onSimulateP2PSync: () => void
}

export default function SovereignAdvancedOpsPanels({
  show,
  meshpegCloudName,
  meshpegBimName,
  meshpegRunning,
  meshpegRes,
  formulaExpr,
  formulaRunning,
  formulaRes,
  gatewayRes,
  assetAppraising,
  assetAppraisal,
  arRadius,
  arLimit,
  arLoading,
  activeUri,
  latestProofId,
  totalHashShort,
  nearestAnchorText,
  arItems,
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
  showFingerprintAdvanced,
  unitLoading,
  unitProofId,
  unitMaxRows,
  unitRes,
  unitVerifying,
  unitVerifyMsg,
  itemPathSteps,
  unitPathSteps,
  p2pNodeId,
  offlineQueueSize,
  p2pLastSync,
  p2pAutoSync,
  p2pPeers,
  merkleRootText,
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  btnAmberCls,
  formatNumber,
  onMeshpegCloudNameChange,
  onMeshpegBimNameChange,
  onRunMeshpeg,
  onFormulaExprChange,
  onRunFormulaPeg,
  onRunGatewaySync,
  onCopyGatewayJson,
  onDownloadGatewayJson,
  onBuildAssetAppraisal,
  onCopyAssetAppraisalJson,
  onDownloadAssetAppraisalJson,
  onArRadiusChange,
  onArLimitChange,
  onRunArOverlay,
  onOpenArFullscreen,
  onFocusArItem,
  onToggleFingerprintAdvanced,
  onUnitProofIdChange,
  onUnitMaxRowsChange,
  onCalcUnitMerkle,
  onUseCurrentProofForUnit,
  onVerifyUnitMerkle,
  onExportMerkleJson,
  onP2PAutoSyncChange,
  onP2PPeersChange,
  onExportP2PManifest,
  onSimulateP2PSync,
}: Props) {
  if (!show) return null

  return (
    <>
      <ExecutionPegPanels
        meshpegCloudName={meshpegCloudName}
        meshpegBimName={meshpegBimName}
        meshpegRunning={meshpegRunning}
        meshpegRes={meshpegRes}
        formulaExpr={formulaExpr}
        formulaRunning={formulaRunning}
        formulaRes={formulaRes}
        gatewayRes={gatewayRes}
        inputBaseCls={inputBaseCls}
        btnBlueCls={btnBlueCls}
        btnGreenCls={btnGreenCls}
        btnAmberCls={btnAmberCls}
        formatNumber={formatNumber}
        onMeshpegCloudNameChange={onMeshpegCloudNameChange}
        onMeshpegBimNameChange={onMeshpegBimNameChange}
        onRunMeshpeg={onRunMeshpeg}
        onFormulaExprChange={onFormulaExprChange}
        onRunFormulaPeg={onRunFormulaPeg}
        onRunGatewaySync={onRunGatewaySync}
        onCopyGatewayJson={onCopyGatewayJson}
        onDownloadGatewayJson={onDownloadGatewayJson}
      />

      <AssetAppraisalPanel
        assetAppraising={assetAppraising}
        assetAppraisal={assetAppraisal}
        btnGreenCls={btnGreenCls}
        onBuildAssetAppraisal={onBuildAssetAppraisal}
        onCopyAssetAppraisalJson={onCopyAssetAppraisalJson}
        onDownloadAssetAppraisalJson={onDownloadAssetAppraisalJson}
      />

      <ArPanel
        arRadius={arRadius}
        arLimit={arLimit}
        arLoading={arLoading}
        activeUri={activeUri}
        latestProofId={latestProofId}
        totalHashShort={totalHashShort}
        nearestAnchorText={nearestAnchorText}
        arItems={arItems}
        inputBaseCls={inputBaseCls}
        btnAmberCls={btnAmberCls}
        onArRadiusChange={onArRadiusChange}
        onArLimitChange={onArLimitChange}
        onRunArOverlay={onRunArOverlay}
        onOpenFullscreen={onOpenArFullscreen}
        onFocusItem={onFocusArItem}
      />

      <GeoFencePanel
        geoFenceStatusText={geoFenceStatusText}
        scanEntryStatus={scanEntryStatus}
        scanEntryRequired={scanEntryRequired}
        scanEntryToken={scanEntryToken}
        scanChainBadge={scanChainBadge}
        geoAnchor={geoAnchor}
        geoDistance={geoDistance}
        temporalWindow={temporalWindow}
        geoTemporalBlocked={geoTemporalBlocked}
      />

      <FingerprintPanel
        currentSubdivisionText={currentSubdivisionText}
        showFingerprintAdvanced={showFingerprintAdvanced}
        unitLoading={unitLoading}
        unitProofId={unitProofId}
        unitMaxRows={unitMaxRows}
        unitRes={unitRes}
        unitVerifying={unitVerifying}
        unitVerifyMsg={unitVerifyMsg}
        itemPathSteps={itemPathSteps}
        unitPathSteps={unitPathSteps}
        inputBaseCls={inputBaseCls}
        btnBlueCls={btnBlueCls}
        btnAmberCls={btnAmberCls}
        onToggleFingerprintAdvanced={onToggleFingerprintAdvanced}
        onUnitProofIdChange={onUnitProofIdChange}
        onUnitMaxRowsChange={onUnitMaxRowsChange}
        onCalcUnitMerkle={onCalcUnitMerkle}
        onUseCurrentProofForUnit={onUseCurrentProofForUnit}
        onVerifyUnitMerkle={onVerifyUnitMerkle}
        onExportMerkleJson={onExportMerkleJson}
      />

      <P2PSyncPanel
        p2pNodeId={p2pNodeId}
        offlineQueueSize={offlineQueueSize}
        p2pLastSync={p2pLastSync}
        p2pAutoSync={p2pAutoSync}
        p2pPeers={p2pPeers}
        merkleRootText={merkleRootText}
        inputBaseCls={inputBaseCls}
        btnBlueCls={btnBlueCls}
        btnAmberCls={btnAmberCls}
        onP2PAutoSyncChange={onP2PAutoSyncChange}
        onP2PPeersChange={onP2PPeersChange}
        onExportP2PManifest={onExportP2PManifest}
        onSimulateP2PSync={onSimulateP2PSync}
      />
    </>
  )
}
