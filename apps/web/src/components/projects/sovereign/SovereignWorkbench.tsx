import { Suspense, lazy, useMemo  } from 'react'

import AuditGatekeeper from './AuditGatekeeper'
import { useNormEngine } from './NormEngine'
import { useProjectSovereign } from './SovereignContext'
import type { Evidence, FormRow } from './types'
import WorkbenchEvidencePanel from './WorkbenchEvidencePanel'
import WorkbenchNodeContextPanel from './WorkbenchNodeContextPanel'
import WorkbenchQualityPanels from './WorkbenchQualityPanels'

const BridgeWorkbench = lazy(() => import('./workbench/BridgeWorkbench'))
const LandscapeWorkbench = lazy(() => import('./workbench/LandscapeWorkbench'))
const PhysicalWorkbench = lazy(() => import('./workbench/PhysicalWorkbench'))
const ContractFeeWorkbench = lazy(() => import('./workbench/ContractFeeWorkbench'))

type Props = {
  panelCls: string
  inputBaseCls: string
  btnBlueCls: string
  btnAmberCls: string
  btnGreenCls: string
  btnRedCls: string
  hashing: boolean
  templateDisplay: string
  isSpecBound: boolean
  specBinding: string
  gateBinding: string
  displayMeta: { unitProject: string; subdivisionProject: string }
  compType: string
  componentTypeOptions: Array<{ value: string; label: string }>
  loadingCtx: boolean
  geoFormLocked: boolean
  scanEntryStatus: 'idle' | 'ok' | 'blocked'
  scanEntryAt: string
  scanEntryToken: string
  scanEntryRequired: boolean
  scanEntryTokenHash: string
  scanChainBadge: { cls: string; label: string }
  scanEntryLatest: Record<string, unknown> | null
  normRefs: string[]
  contextError: string
  sampleId: string
  effectiveSchema: FormRow[]
  form: Record<string, string>
  evidence: Evidence[]
  evidenceName: string
  evidenceAccept: string
  evidenceLabel: string
  evidenceHint: string
  geoValid: boolean
  geoFenceWarning: string
  showAdvancedExecution: boolean
  deltaAmount: string
  deltaReason: string
  applyingDelta: boolean
  variationRes: Record<string, unknown> | null
  claimQty: string
  claimQtyProvided: boolean
  measuredQtyValue: number
  deltaSuggest: number
  temporalBlocked: boolean
  geoFenceActive: boolean
  geoDistance: number
  geoAnchor: Record<string, unknown> | null
  tripStage: 'Unspent' | 'Reviewing' | 'Approved'
  effectiveRiskScore: number
  executing: boolean
  mockGenerating: boolean
  rejecting: boolean
  evidenceFileRef: React.RefObject<HTMLInputElement | null>
  lat: string
  lng: string
  onTraceOpen: () => void
  onScanEntry: () => void
  onScanEntryTokenChange: (value: string) => void
  onScanEntryRequiredChange: (checked: boolean) => void
  onSampleIdChange: (value: string) => void
  onCompTypeChange: (value: string) => void
  onExecutorDidChange: (value: string) => void
  onLoadContext: () => void | Promise<void>
  onFormChange: (next: Record<string, string>) => void
  onEvidence: (files: FileList | null) => void | Promise<void>
  onFingerprintOpen: () => void
  onEvidencePreview: (item: Evidence) => void
  onDeltaAmountChange: (value: string) => void
  onDeltaReasonChange: (value: string) => void
  onApplyDelta: () => void | Promise<void>
  onSuggestDelta: () => void
  onClaimQtyChange: (value: string) => void
  onSubmitTrip: () => void | Promise<void>
  onSubmitTripMock: () => void | Promise<void>
  onRecordRejectTrip: () => void | Promise<void>
  onLatChange: (value: string) => void
  onLngChange: (value: string) => void
  sanitizeMeasuredInput: (raw: string) => string
  metricLabel: (label: string, fieldKey: string) => string
  toChineseCompType: (value: string) => string
}

export default function SovereignWorkbench({
  panelCls,
  inputBaseCls,
  btnBlueCls,
  btnAmberCls,
  btnGreenCls,
  btnRedCls,
  hashing,
  templateDisplay,
  isSpecBound,
  specBinding,
  gateBinding,
  displayMeta,
  compType,
  componentTypeOptions,
  loadingCtx,
  geoFormLocked,
  scanEntryStatus,
  scanEntryAt,
  scanEntryToken,
  scanEntryRequired,
  scanEntryTokenHash,
  scanChainBadge,
  scanEntryLatest,
  normRefs,
  contextError,
  sampleId,
  effectiveSchema,
  form,
  evidence,
  evidenceName,
  evidenceAccept,
  evidenceLabel,
  evidenceHint,
  geoValid,
  geoFenceWarning,
  showAdvancedExecution,
  deltaAmount,
  deltaReason,
  applyingDelta,
  variationRes,
  claimQty,
  claimQtyProvided,
  measuredQtyValue,
  deltaSuggest,
  temporalBlocked,
  geoFenceActive,
  geoDistance,
  geoAnchor,
  tripStage,
  effectiveRiskScore,
  executing,
  mockGenerating,
  rejecting,
  evidenceFileRef,
  lat,
  lng,
  onTraceOpen,
  onScanEntry,
  onScanEntryTokenChange,
  onScanEntryRequiredChange,
  onSampleIdChange,
  onCompTypeChange,
  onExecutorDidChange,
  onLoadContext,
  onFormChange,
  onEvidence,
  onFingerprintOpen,
  onEvidencePreview,
  onDeltaAmountChange,
  onDeltaReasonChange,
  onApplyDelta,
  onSuggestDelta,
  onClaimQtyChange,
  onSubmitTrip,
  onSubmitTripMock,
  onRecordRejectTrip,
  onLatChange,
  onLngChange,
  sanitizeMeasuredInput,
  metricLabel,
  toChineseCompType,
}: Props) {
  const { project, identity } = useProjectSovereign()
  const { gateStats, gateReason, evalNorm, ruleText } = useNormEngine()

  const DynamicWorkbench = useMemo(() => {
    if (project.spuKind === 'bridge') return BridgeWorkbench
    if (project.spuKind === 'landscape') return LandscapeWorkbench
    if (project.spuKind === 'contract') return ContractFeeWorkbench
    return PhysicalWorkbench
  }, [project.spuKind])

  const headerToneCls = project.spuKind === 'bridge'
    ? 'border-emerald-600/60 bg-emerald-950/30 text-emerald-100'
    : project.spuKind === 'landscape'
      ? 'border-lime-600/60 bg-lime-950/25 text-lime-100'
      : project.spuKind === 'contract'
        ? 'border-amber-600/60 bg-amber-950/25 text-amber-100'
        : 'border-slate-600/50 bg-slate-950/20 text-slate-100'

  const progressToneCls = project.spuBadge.cls.includes('emerald')
    ? 'from-emerald-500/70 via-emerald-500/40 to-slate-800/30'
    : project.spuBadge.cls.includes('lime')
      ? 'from-lime-500/70 via-lime-500/40 to-slate-800/30'
      : project.spuBadge.cls.includes('amber')
        ? 'from-amber-500/70 via-amber-500/40 to-slate-800/30'
        : 'from-slate-500/40 via-slate-500/20 to-slate-800/30'

  return (
    <div className={`${panelCls} wb-panel`}>
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-sm font-extrabold">{project.stepLabel}</div>
          <span className="rounded-full border border-slate-700 bg-slate-800/90 px-2 py-0.5 text-[10px] text-slate-400">执行层</span>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] ${project.spuBadge.cls}`}>{project.spuBadge.label}</span>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] ${hashing ? 'border-amber-500/60 text-amber-300' : 'border-emerald-500/60 text-emerald-300'}`}>
            {project.isContractSpu ? '附件数量' : 'SnapPeg 数量'} {hashing ? '计算中...' : evidence.length}
          </span>
        </div>
        <button type="button" onClick={onTraceOpen} className={`px-3 py-1.5 text-xs ${btnBlueCls}`}>溯源图谱</button>
      </div>

      <div className={`mb-3 h-1 rounded-full bg-gradient-to-r ${progressToneCls}`} />

      <div className={`mb-3 rounded-xl border px-3 py-2 ${headerToneCls}`}>
        {project.spuKind === 'bridge' && (
          <div className="grid gap-1">
            <div className="text-xs font-extrabold">桥梁质检卡</div>
            <div className="text-xs text-emerald-200">结构实测 | 保护层控制 | 施工锁线</div>
          </div>
        )}
        {project.spuKind === 'landscape' && (
          <div className="grid gap-1">
            <div className="text-xs font-extrabold">绿化验收卡</div>
            <div className="text-xs text-lime-200">成活率 | 覆盖率 | 高度偏差</div>
          </div>
        )}
        {project.spuKind === 'contract' && (
          <div className="grid gap-1">
            <div className="text-xs font-extrabold">合同凭证卡</div>
            <div className="text-xs text-amber-200">附件核验 | 金额锁定 | 证据链归档</div>
          </div>
        )}
        {project.spuKind === 'physical' && (
          <div className="grid gap-1">
            <div className="text-xs font-extrabold">实体工程卡</div>
            <div className="text-xs text-slate-300">实测值 | 设计值 | 允许偏差</div>
          </div>
        )}
      </div>

      <WorkbenchNodeContextPanel
        activePathText={project.activePath || String(project.active?.uri || '')}
        templateDisplay={templateDisplay}
        isSpecBound={isSpecBound}
        isContractSpu={project.isContractSpu}
        specBinding={specBinding}
        gateBinding={gateBinding}
        displayMeta={displayMeta}
        compType={compType}
        componentTypeOptions={componentTypeOptions}
        loadingCtx={loadingCtx}
        geoFormLocked={geoFormLocked}
        scanEntryStatus={scanEntryStatus}
        scanEntryAt={scanEntryAt}
        scanEntryToken={scanEntryToken}
        scanEntryRequired={scanEntryRequired}
        scanEntryTokenHash={scanEntryTokenHash}
        scanChainBadge={scanChainBadge}
        scanEntryLatest={scanEntryLatest}
        normRefs={normRefs}
        contextError={contextError}
        sampleId={sampleId}
        executorDid={identity.executorDid}
        inputBaseCls={inputBaseCls}
        btnBlueCls={btnBlueCls}
        toChineseCompType={toChineseCompType}
        onScanEntry={onScanEntry}
        onScanEntryTokenChange={onScanEntryTokenChange}
        onScanEntryRequiredChange={onScanEntryRequiredChange}
        onSampleIdChange={onSampleIdChange}
        onCompTypeChange={onCompTypeChange}
        onExecutorDidChange={onExecutorDidChange}
        onLoadContext={() => void onLoadContext()}
        canScan={Boolean(project.active?.isLeaf)}
        canLoadContext={Boolean(project.active?.isLeaf) && !loadingCtx && !geoFormLocked}
      />

      <Suspense fallback={<div className="mb-3 rounded-xl border border-slate-700/70 bg-slate-950/30 px-3 py-4 text-sm text-slate-400">执行战区加载中...</div>}>
        <DynamicWorkbench
          isContractSpu={project.isContractSpu}
          schema={effectiveSchema}
          form={form}
          geoFormLocked={geoFormLocked}
          onFormChange={onFormChange}
          evalNorm={evalNorm}
          sanitizeMeasuredInput={sanitizeMeasuredInput}
          metricLabel={metricLabel}
          ruleText={ruleText}
        />
      </Suspense>

      <WorkbenchQualityPanels
        gateStats={gateStats}
        projectIsContractSpu={project.isContractSpu}
        activeIsLeaf={Boolean(project.active?.isLeaf)}
        effectiveRiskScore={effectiveRiskScore}
        rejecting={rejecting}
        btnRedCls={btnRedCls}
        onRecordRejectTrip={() => void onRecordRejectTrip()}
      />

      <WorkbenchEvidencePanel
        lat={lat}
        lng={lng}
        geoFormLocked={geoFormLocked}
        evidenceFileRef={evidenceFileRef}
        evidenceLabel={evidenceLabel}
        evidenceName={evidenceName}
        evidenceAccept={evidenceAccept}
        evidenceHint={evidenceHint}
        geoValid={geoValid}
        geoFenceWarning={geoFenceWarning}
        geoFenceActive={geoFenceActive}
        geoDistance={geoDistance}
        activeIsLeaf={Boolean(project.active?.isLeaf)}
        sampleId={sampleId}
        executorDid={identity.executorDid}
        activeUri={String(project.active?.uri || '')}
        hashing={hashing}
        evidence={evidence}
        showAdvancedExecution={showAdvancedExecution}
        deltaAmount={deltaAmount}
        deltaReason={deltaReason}
        applyingDelta={applyingDelta}
        variationRes={variationRes}
        inputBaseCls={inputBaseCls}
        btnAmberCls={btnAmberCls}
        onLatChange={onLatChange}
        onLngChange={onLngChange}
        onEvidence={onEvidence}
        onFingerprintOpen={onFingerprintOpen}
        onEvidencePreview={onEvidencePreview}
        onDeltaAmountChange={onDeltaAmountChange}
        onDeltaReasonChange={onDeltaReasonChange}
        onApplyDelta={() => void onApplyDelta()}
      />

      <AuditGatekeeper
        inputBaseCls={inputBaseCls}
        btnBlueCls={btnBlueCls}
        btnGreenCls={btnGreenCls}
        btnRedCls={btnRedCls}
        btnAmberCls={btnAmberCls}
        claimQty={claimQty}
        geoFormLocked={geoFormLocked}
        claimQtyProvided={claimQtyProvided}
        measuredQtyValue={measuredQtyValue}
        deltaSuggest={deltaSuggest}
        isSpecBound={isSpecBound}
        temporalBlocked={temporalBlocked}
        geoFenceActive={geoFenceActive}
        geoDistance={geoDistance}
        geoAnchor={geoAnchor}
        tripStage={tripStage}
        onClaimQtyChange={onClaimQtyChange}
        onSuggestDelta={onSuggestDelta}
        onSubmitTrip={onSubmitTrip}
        onSubmitTripMock={onSubmitTripMock}
        executing={executing}
        mockGenerating={mockGenerating}
      />

      <div className="mt-2 text-[11px] text-slate-500">Gatekeeper 状态: {gateStats.dualQualified ? '双门控通过' : gateReason || '等待补齐证据链'}</div>
    </div>
  )
}
