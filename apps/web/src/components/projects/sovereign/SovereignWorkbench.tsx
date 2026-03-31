import React, { Suspense, lazy, useMemo } from 'react'
import AuditGatekeeper from './AuditGatekeeper'
import { useNormEngine } from './NormEngine'
import { useProjectSovereign } from './SovereignContext'
import TripRiskGauge from './TripRiskGauge'
import type { Evidence, FormRow } from './types'

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
      <div className={`mb-3 h-1 rounded-full bg-gradient-to-r ${project.spuBadge.cls.includes('emerald') ? 'from-emerald-500/70 via-emerald-500/40 to-slate-800/30' : project.spuBadge.cls.includes('lime') ? 'from-lime-500/70 via-lime-500/40 to-slate-800/30' : project.spuBadge.cls.includes('amber') ? 'from-amber-500/70 via-amber-500/40 to-slate-800/30' : 'from-slate-500/40 via-slate-500/20 to-slate-800/30'}`} />
      <div className={`mb-3 rounded-xl border px-3 py-2 ${project.spuKind === 'bridge' ? 'border-emerald-600/60 bg-emerald-950/30 text-emerald-100' : project.spuKind === 'landscape' ? 'border-lime-600/60 bg-lime-950/25 text-lime-100' : project.spuKind === 'contract' ? 'border-amber-600/60 bg-amber-950/25 text-amber-100' : 'border-slate-600/50 bg-slate-950/20 text-slate-100'}`}>
        {project.spuKind === 'bridge' && <div className="grid gap-1"><div className="text-xs font-extrabold">桥梁质检台</div><div className="text-xs text-emerald-200">结构实测 · 保护层控制 · 施工锁线</div></div>}
        {project.spuKind === 'landscape' && <div className="grid gap-1"><div className="text-xs font-extrabold">绿化验收台</div><div className="text-xs text-lime-200">成活率 · 覆盖率 · 高度偏差</div></div>}
        {project.spuKind === 'contract' && <div className="grid gap-1"><div className="text-xs font-extrabold">合同凭证台</div><div className="text-xs text-amber-200">附件核验 · 金额锁定 · 证据链归档</div></div>}
        {project.spuKind === 'physical' && <div className="grid gap-1"><div className="text-xs font-extrabold">实体工程台</div><div className="text-xs text-slate-300">实测值 · 设计值 · 允许偏差</div></div>}
      </div>
      <div className="mb-3 rounded-xl border border-slate-700/70 p-3 text-sm">
        <div className="mb-1 text-xs text-sky-300">当前节点</div>
        <div className="break-all">{project.activePath || project.active?.uri || '-'}</div>
        <div className="mt-2 text-xs text-slate-400">模板绑定: {templateDisplay}</div>
        <div className={`text-xs ${isSpecBound ? 'text-emerald-300' : 'text-amber-300'}`}>规范绑定: {specBinding || (project.isContractSpu ? '合同凭证类' : '未绑定')} {gateBinding ? `· 门控 ${gateBinding}` : ''}</div>
        <div className="text-xs text-slate-500">自动预填: {displayMeta.unitProject} / {displayMeta.subdivisionProject}</div>
        <div className="text-xs text-slate-500">构件类型: {toChineseCompType(compType)}</div>
        <div className="mt-2 grid grid-cols-[1fr_auto] items-center gap-2">
          <button type="button" onClick={onScanEntry} disabled={!project.active?.isLeaf} className={`px-3 py-2 text-xs font-bold ${btnBlueCls} disabled:opacity-60`}>扫码进入节点</button>
          <div className="text-[11px] text-slate-400">扫码状态: {scanEntryStatus === 'ok' ? '已通过' : scanEntryStatus === 'blocked' ? '被拦截' : '未扫码'}{scanEntryAt ? ` · ${scanEntryAt.slice(11, 19)}` : ''}</div>
        </div>
        <div className="mt-2 grid gap-2">
          <div className="grid grid-cols-[1fr_auto] items-center gap-2">
            <input value={scanEntryToken} onChange={(e) => onScanEntryTokenChange(e.target.value)} placeholder="扫码令牌（scan_entry_token）" className={inputBaseCls} />
            <label className="flex items-center gap-2 text-[11px] text-slate-400"><input type="checkbox" checked={scanEntryRequired} onChange={(e) => onScanEntryRequiredChange(e.target.checked)} />令牌必填</label>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span>链状态</span>
            <span className={`rounded-full border px-2 py-0.5 ${scanChainBadge.cls}`}>{scanChainBadge.label}</span>
            {scanEntryLatest?.proof_id && <span className="truncate text-slate-500">Proof: {String(scanEntryLatest.proof_id || '-')}</span>}
          </div>
          {scanEntryTokenHash && <div className="break-all text-[11px] text-slate-500">令牌哈希: {scanEntryTokenHash}</div>}
        </div>
        {!!normRefs.length && <div className="text-xs text-slate-400">规范索引: {normRefs.join(' / ')}</div>}
        {!!contextError && <div className="mt-2 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-300">{contextError}</div>}
        {!isSpecBound && <div className="mt-2 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-300">未绑定规范/门控，已锁定提交</div>}
      </div>
      <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
        <input value={sampleId} disabled={geoFormLocked} onChange={(e) => onSampleIdChange(e.target.value)} placeholder="UTXO_Identifier（样品编号）" className={`${inputBaseCls} ${geoFormLocked ? 'cursor-not-allowed opacity-60' : ''}`} />
        <div className="rounded-lg border border-dashed border-slate-700 px-3 py-2 text-sm leading-5 text-slate-400">UTXO_Identifier 将自动映射到链上样品字段</div>
      </div>
      <div className="mb-3 grid grid-cols-[1fr_1fr_auto] gap-3 max-[1180px]:grid-cols-1">
        <select value={compType} disabled={geoFormLocked} onChange={(e) => onCompTypeChange(e.target.value)} className={`${inputBaseCls} ${geoFormLocked ? 'cursor-not-allowed opacity-60' : ''}`}>
          {componentTypeOptions.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
        <input value={identity.executorDid} disabled={geoFormLocked} onChange={(e) => onExecutorDidChange(e.target.value)} placeholder="执行人 DID" className={`${inputBaseCls} ${geoFormLocked ? 'cursor-not-allowed opacity-60' : ''}`} />
        <button type="button" disabled={!project.active?.isLeaf || loadingCtx || geoFormLocked} onClick={() => void onLoadContext()} className={`px-3 py-2 text-sm disabled:opacity-60 ${btnBlueCls}`}>{loadingCtx ? '加载中...' : '加载门控'}</button>
      </div>
      <Suspense fallback={<div className="mb-3 rounded-xl border border-slate-700/70 bg-slate-950/30 px-3 py-4 text-sm text-slate-400">执行战区按 Material Tag 装载中...</div>}>
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
      <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
        <div className="rounded-xl border border-emerald-700/60 bg-emerald-950/25 p-3">
          <div className="mb-1 text-xs text-emerald-300">双合格门控</div>
          <div className="text-sm font-semibold text-slate-100">现场质检: {gateStats.qcStatus}</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">实验佐证: {gateStats.labStatus}</div>
          {!project.isContractSpu && gateStats.labTotal > 0 && <div className="mt-1 text-xs text-slate-300">实验室证明: {gateStats.labPass}/{gateStats.labTotal}{gateStats.labLatestPass && <span className="ml-2">最新 PASS: {gateStats.labLatestPass}</span>}{gateStats.labLatestHash && <div className="mt-1 text-[11px] text-emerald-300">主权已锁定</div>}</div>}
          {!project.isContractSpu && !gateStats.labTotal && <div className="mt-1 text-xs text-amber-200">未检测到实验室 Proof Hash，请先录入 LabPeg</div>}
          <div className={`mt-2 text-xs font-bold ${gateStats.dualQualified ? 'text-emerald-300' : 'text-amber-300'}`}>双合格门控: {gateStats.dualQualified ? '通过' : '未通过'}</div>
          {!gateStats.dualQualified && project.active?.isLeaf && <button type="button" onClick={() => void onRecordRejectTrip()} disabled={rejecting || !project.active?.isLeaf} className="mt-2 w-full rounded-lg border border-rose-500/70 bg-rose-950/40 px-3 py-2 text-xs font-bold text-rose-200 hover:bg-rose-900/40 disabled:opacity-60">{rejecting ? '记录中...' : '记录不合格（Reject Trip）'}</button>}
        </div>
        <div className="rounded-xl border border-sky-700/60 bg-sky-950/20 p-3">
          <div className="mb-1 text-xs text-sky-300">规范判定概览（NormPeg）</div>
          <div className="text-sm text-slate-100">总项: {gateStats.total}</div>
          <div className="text-sm text-emerald-300">合格: {gateStats.pass}</div>
          <div className="text-sm text-red-300">不合格: {gateStats.fail}</div>
          <div className="text-sm text-amber-200">待检: {gateStats.pending}</div>
          {!gateStats.qcCompliant && <div className="mt-2 text-xs text-amber-200">TripRole 判定未完成（is_compliant=false）</div>}
          {project.isContractSpu && <div className="mt-2 text-xs text-slate-400">合同凭证类不启用 NormPeg 评分</div>}
        </div>
      </div>
      <div className="mb-3"><TripRiskGauge score={effectiveRiskScore} title="Risk Score 仪表盘" /></div>
      <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
        <input value={lat} disabled={geoFormLocked} onChange={(e) => onLatChange(e.target.value)} placeholder="GPS 纬度" className={`${inputBaseCls} ${geoFormLocked ? 'cursor-not-allowed opacity-60' : ''}`} />
        <input value={lng} disabled={geoFormLocked} onChange={(e) => onLngChange(e.target.value)} placeholder="GPS 经度" className={`${inputBaseCls} ${geoFormLocked ? 'cursor-not-allowed opacity-60' : ''}`} />
      </div>
      <div className="grid grid-cols-[auto_1fr] items-center gap-2">
        <button type="button" disabled={geoFormLocked} onClick={() => evidenceFileRef.current?.click()} className={`rounded-lg border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm leading-5 text-slate-200 ${geoFormLocked ? 'cursor-not-allowed opacity-60' : ''}`}>{evidenceLabel}</button>
        <div className={`truncate text-sm leading-5 ${evidenceName ? 'text-slate-200' : 'text-slate-500'}`}>{evidenceName || `未选择任何文件（${evidenceHint}）`}</div>
        <input ref={evidenceFileRef} type="file" multiple disabled={geoFormLocked} accept={evidenceAccept} onChange={(e) => void onEvidence(e.target.files)} className="hidden" />
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
        <span className="flex items-center gap-2">主权指纹<button type="button" onClick={onFingerprintOpen} className="rounded border border-slate-600 bg-slate-900/70 px-2 py-0.5 text-[11px] text-slate-200">查看</button></span>
        <span className={`rounded-full border px-2 py-0.5 ${hashing ? 'border-amber-500/60 text-amber-300' : 'border-emerald-500/60 text-emerald-300'}`}>{hashing ? '计算中...' : `数量 ${evidence.length}`}</span>
      </div>
      <div className={`mt-1 text-xs ${geoValid ? 'text-emerald-300' : 'text-amber-300'}`}>位置校验: {geoValid ? '坐标已采集' : '疑似虚假影像（坐标缺失）'}</div>
      {!!geoFenceWarning && <div className="mt-1 text-xs text-rose-300">位置警告: {geoFenceWarning}</div>}
      <div className="mt-3 mb-3 grid max-h-[190px] grid-cols-2 gap-2 overflow-y-auto">
        {evidence.map((item) => (
          <button type="button" key={item.hash} onClick={() => onEvidencePreview(item)} className={`relative overflow-hidden rounded-lg border bg-transparent p-0 ${geoFenceActive && geoDistance > 0 ? 'border-rose-500/80' : 'border-slate-700'}`}>
            <img src={item.url} alt={item.name} className="block h-[108px] w-full object-cover" />
            <div className="absolute inset-0 flex flex-col justify-end gap-0.5 bg-gradient-to-t from-slate-950/80 to-slate-950/20 p-2 text-[11px] leading-4 text-slate-200">
              <div className={`inline-flex w-fit rounded-full border px-1.5 py-0 text-[10px] ${geoFenceActive && geoDistance > 0 ? 'border-rose-400/70 bg-rose-950/40 text-rose-200' : 'border-emerald-400/70 bg-emerald-950/40 text-emerald-200'}`}>{geoFenceActive && geoDistance > 0 ? 'SnapPeg 拦截' : 'SnapPeg Sealed'}</div>
              <div>v:// 路径: {project.active?.uri || '-'}</div>
              <div>GPS 坐标: {lat}, {lng}</div>
              <div>NTP 时间戳: {item.ntp}</div>
              <div>DID 签名者: {identity.executorDid}</div>
              <div>样品编号: {sampleId || '-'}</div>
            </div>
          </button>
        ))}
      </div>
      {showAdvancedExecution && (
        <div className="mb-3 rounded-xl border border-dashed border-rose-600/60 bg-rose-950/20 p-3">
          <div className="mb-1 text-xs font-extrabold">变更补差 (Delta UTXO)</div>
          <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
            <input value={deltaAmount} onChange={(e) => onDeltaAmountChange(e.target.value)} placeholder="变更数量 (+/-)" className={inputBaseCls} />
            <input value={deltaReason} onChange={(e) => onDeltaReasonChange(e.target.value)} placeholder="变更原因" className={inputBaseCls} />
          </div>
          <button type="button" onClick={() => void onApplyDelta()} disabled={applyingDelta || !project.active?.isLeaf} className={`w-full px-3 py-2 text-sm font-bold disabled:opacity-60 ${btnAmberCls}`}>{applyingDelta ? '提交中...' : '提交变更补差'}</button>
          {!!variationRes && <div className="mt-1 text-[11px] text-amber-200">变更 Proof: {String(variationRes.output_proof_id || '')}</div>}
        </div>
      )}
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
