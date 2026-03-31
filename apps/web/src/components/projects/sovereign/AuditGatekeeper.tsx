import React from 'react'
import { useNormEngine } from './NormEngine'
import { useProjectSovereign } from './SovereignContext'

type SubmissionZoneProps = {
  btnBlueCls: string
  btnGreenCls: string
  btnRedCls: string
  executing: boolean
  mockGenerating: boolean
  isSpecBound: boolean
  tripStage: 'Unspent' | 'Reviewing' | 'Approved'
  onSubmitTrip: () => void | Promise<void>
  onSubmitTripMock: () => void | Promise<void>
  forceDisabled?: boolean
}

type GuardProps = {
  blocked: boolean
  reason: string
}

function withAuditGatekeeper<P extends { forceDisabled?: boolean }>(Component: React.ComponentType<P>) {
  return function GuardedComponent(props: P & GuardProps) {
    const { blocked, reason, ...rest } = props
    const componentProps = rest as unknown as P
    return (
      <div className="relative">
        <div className={blocked ? 'pointer-events-none opacity-35 blur-[1px]' : ''}>
          <Component
            {...componentProps}
            forceDisabled={blocked || Boolean((rest as { forceDisabled?: boolean }).forceDisabled)}
          />
        </div>
        {blocked && (
          <div className="absolute inset-0 grid place-items-center rounded-2xl border border-rose-500/60 bg-slate-950/78 p-4 text-center">
            <div>
              <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-rose-300">Audit Gatekeeper</div>
              <div className="mt-2 text-sm font-semibold text-slate-100">提交区域已物理拦截</div>
              <div className="mt-1 text-xs leading-5 text-slate-300">{reason}</div>
            </div>
          </div>
        )}
      </div>
    )
  }
}

function SubmissionZone({
  btnBlueCls,
  btnGreenCls,
  btnRedCls,
  executing,
  mockGenerating,
  isSpecBound,
  tripStage,
  onSubmitTrip,
  onSubmitTripMock,
  forceDisabled,
}: SubmissionZoneProps) {
  return (
    <>
      <div className="mt-3 rounded-lg border border-slate-700/70 bg-slate-950/40 px-3 py-2 text-xs">
        <div className="mb-1 text-slate-400">审批状态</div>
        <div className="flex items-center gap-2">
          <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Unspent' ? 'border-slate-500/70 bg-slate-900/60 text-slate-300' : 'border-slate-700/60 bg-slate-900/20 text-slate-500'}`}>Unspent</span>
          <span className="text-slate-600">→</span>
          <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Reviewing' ? 'border-sky-500/70 bg-sky-950/30 text-sky-200' : tripStage === 'Approved' ? 'border-sky-700/50 bg-sky-950/10 text-sky-500' : 'border-slate-700/60 bg-slate-900/20 text-slate-500'}`}>Reviewing</span>
          <span className="text-slate-600">→</span>
          <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Approved' ? 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200' : 'border-slate-700/60 bg-slate-900/20 text-slate-500'}`}>Approved</span>
        </div>
      </div>
      <button
        type="button"
        onClick={() => void onSubmitTrip()}
        disabled={executing || forceDisabled}
        className={`mt-3 w-full px-3 py-2 font-bold disabled:opacity-60 ${forceDisabled ? btnRedCls : btnGreenCls}`}
      >
        {executing ? '提交中...' : '确认提交'}
      </button>
      <button
        type="button"
        onClick={() => void onSubmitTripMock()}
        disabled={mockGenerating || forceDisabled || !isSpecBound}
        className={`mt-2 w-full px-3 py-2 font-bold disabled:opacity-60 ${btnBlueCls}`}
      >
        {mockGenerating ? 'DocPeg 生成中...' : '确认并生成 Document.create_trip'}
      </button>
      <div className="mt-2 text-[11px] text-slate-500">
        提交后会进入 TripRole 审核链路；签认完成后自动冻结 SMU，并在右侧生成正式 DocPeg 预览与二维码。
      </div>
    </>
  )
}

const GuardedSubmissionZone = withAuditGatekeeper(SubmissionZone)

type Props = {
  inputBaseCls: string
  btnBlueCls: string
  btnGreenCls: string
  btnRedCls: string
  btnAmberCls: string
  claimQty: string
  geoFormLocked: boolean
  claimQtyProvided: boolean
  measuredQtyValue: number
  deltaSuggest: number
  isSpecBound: boolean
  temporalBlocked: boolean
  geoFenceActive: boolean
  geoDistance: number
  geoAnchor: Record<string, unknown> | null
  tripStage: 'Unspent' | 'Reviewing' | 'Approved'
  onClaimQtyChange: (value: string) => void
  onSuggestDelta: () => void
  onSubmitTrip: () => void | Promise<void>
  onSubmitTripMock: () => void | Promise<void>
  executing: boolean
  mockGenerating: boolean
}

export default function AuditGatekeeper({
  inputBaseCls,
  btnBlueCls,
  btnGreenCls,
  btnRedCls,
  btnAmberCls,
  claimQty,
  geoFormLocked,
  claimQtyProvided,
  measuredQtyValue,
  deltaSuggest,
  isSpecBound,
  temporalBlocked,
  geoFenceActive,
  geoDistance,
  geoAnchor,
  tripStage,
  onClaimQtyChange,
  onSuggestDelta,
  onSubmitTrip,
  onSubmitTripMock,
  executing,
  mockGenerating,
}: Props) {
  const { gateStats } = useNormEngine()
  const { project, identity, asset, audit } = useProjectSovereign()

  const blockedReason = !identity.roleAllowed
    ? '身份不匹配：当前 DID 无权提交该资产，请切换到授权 DTORole。'
    : audit.archiveLocked
      ? 'Archive_Trip 已封存：该 v:// 资产已转为只读，禁止继续 consume。'
      : audit.disputeOpen
        ? `DISPUTE 挂起中：${audit.disputeProof || '争议 UTXO'} 等待 ${audit.disputeArbiterRole || '业主/第三方检测'} 仲裁。`
        : !project.active?.isLeaf
          ? '仅叶子节点允许提交。'
          : !asset.inputProofId
            ? '缺少输入 Proof，无法进入 TripRole 提交流程。'
            : !isSpecBound
              ? '未绑定 NormRef / Gate，提交已被物理阻断。'
              : !gateStats.dualQualified
                ? audit.gateReason || '双门控未通过。'
                : audit.exceedBalance
                  ? 'Genesis UTXO 余额不足，请先发起变更补差 Trip。'
                  : !audit.snappegReady
                    ? 'SnapPeg 证据链未就绪，请先补齐现场证据。'
                    : audit.geoTemporalBlocked
                      ? '时空门控未通过，请修正现场定位或时间窗口。'
                      : ''

  return (
    <div className="mt-3 rounded-2xl border border-slate-700/70 bg-slate-950/30 p-3">
      <div className="mb-3 rounded-xl border border-slate-700/70 bg-slate-950/40 p-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Dual-Gate Indicator</div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {[
            { label: '现场质检', ok: gateStats.qcCompliant, detail: gateStats.qcStatus },
            { label: '实验室 LabPeg', ok: gateStats.labQualified, detail: gateStats.labStatus },
          ].map((item) => (
            <div key={item.label} className={`rounded-xl border px-3 py-3 ${item.ok ? 'border-emerald-500/60 bg-emerald-950/20' : 'border-amber-500/60 bg-amber-950/20'}`}>
              <div className="flex items-center gap-2">
                <span className={`inline-flex h-3 w-3 rounded-full ${item.ok ? 'bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,.55)]' : 'bg-amber-400 shadow-[0_0_14px_rgba(251,191,36,.45)]'}`} />
                <span className="text-sm font-semibold text-slate-100">{item.label}</span>
              </div>
              <div className={`mt-2 text-xs ${item.ok ? 'text-emerald-200' : 'text-amber-200'}`}>{item.detail}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-slate-400">Audit Gatekeeper</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">双门控、争议挂起与最终提交</div>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${blockedReason ? 'border-rose-500/70 bg-rose-950/30 text-rose-200' : 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200'}`}>
          {blockedReason ? '已拦截' : '可通行'}
        </span>
      </div>

      <div className={`mb-3 rounded-xl border px-3 py-2 ${gateStats.dualQualified && !audit.disputeOpen && !audit.archiveLocked ? 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200' : 'border-rose-500/70 bg-rose-950/30 text-rose-200'}`}>
        <div className="text-xs font-extrabold">终极审判</div>
        <div className="text-sm font-bold">
          {audit.archiveLocked
            ? '封存 · Archive_Trip 已锁死'
            : audit.disputeOpen
              ? `拦截 · ${audit.disputeArbiterRole || '业主/第三方检测'} 仲裁中`
              : gateStats.dualQualified
                ? '通过 · 证据链完整'
                : `拦截 · ${audit.gateReason || '证据链不完整'}`}
        </div>
      </div>

      <div className="rounded-xl border border-slate-700/70 bg-slate-950/30 p-3">
        <div className="mb-2 text-xs font-semibold text-slate-300">结算预警条</div>
        <div className={`mb-2 rounded-lg px-2.5 py-1 text-[11px] font-semibold ${audit.exceedBalance ? 'border border-rose-500/70 bg-rose-950/30 text-rose-200' : 'border border-emerald-500/60 bg-emerald-950/20 text-emerald-200'}`}>
          {audit.exceedBalance ? '余额不足 · 需先执行变更补差 Trip' : '守恒通过 · 可继续提交'}
        </div>
        <div className="mb-2 grid grid-cols-3 gap-2 text-xs text-slate-300">
          <div>设计总量: {asset.baselineTotal.toLocaleString()}</div>
          <div>已结算累计量: {asset.effectiveSpent.toLocaleString()}</div>
          <div>剩余额度: {asset.availableTotal.toLocaleString()}</div>
        </div>
        <div className="grid grid-cols-[1fr_auto] items-center gap-2">
          <input
            value={claimQty}
            disabled={geoFormLocked || audit.disputeOpen || audit.archiveLocked}
            onChange={(e) => onClaimQtyChange(e.target.value)}
            placeholder="本次申报量（空则取实测值）"
            className={`${inputBaseCls} ${geoFormLocked || audit.disputeOpen || audit.archiveLocked ? 'cursor-not-allowed opacity-60' : ''}`}
          />
          <span className={`text-xs ${audit.exceedBalance ? 'text-rose-300' : 'text-emerald-300'}`}>
            {audit.exceedBalance ? 'Genesis UTXO Deviation Warning' : '余额充足'}
          </span>
        </div>
        {!project.isContractSpu && !claimQtyProvided && measuredQtyValue > 0 && (
          <div className="mt-1 text-[11px] text-slate-500">未填申报量，已取实测值 {measuredQtyValue.toLocaleString()}</div>
        )}
        <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full border border-slate-700/70 bg-slate-900">
          <div
            className={`h-2.5 ${audit.exceedBalance ? 'bg-rose-500' : 'bg-emerald-500'}`}
            style={{ width: `${Math.max(0, Math.min(100, asset.baselineTotal > 0 ? ((asset.effectiveSpent + asset.effectiveClaimQtyValue) * 100) / asset.baselineTotal : 0))}%` }}
          />
        </div>
        <div className="mt-1 text-[11px] text-slate-400">公式：申报量 + 已结算累计量 ≤ Genesis Approved 总量</div>
        <div className="mt-1 text-[11px] text-slate-500">当前申报量 + 已结算累计量 = {(asset.effectiveSpent + asset.effectiveClaimQtyValue).toLocaleString()}</div>
        {audit.exceedBalance && deltaSuggest > 0 && (
          <div className="mt-2 flex items-center gap-2 text-[11px] text-rose-300">
            <span>建议补差量 {deltaSuggest.toFixed(3)}</span>
            <button type="button" onClick={onSuggestDelta} className={`rounded border border-amber-600/60 px-2 py-0.5 text-amber-200 ${btnAmberCls}`}>
              一键填入
            </button>
          </div>
        )}
      </div>

      {!identity.roleAllowed && (
        <div className="mt-3 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-300">
          身份不匹配：当前 DID 无权提交该资产，请切换到授权 DTORole。
        </div>
      )}
      {audit.disputeOpen && (
        <div className="mt-3 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-200">
          争议挂起中：{audit.disputeProof || 'Dispute UTXO'} 已锁定该 v:// 地址，等待 {audit.disputeArbiterRole || '业主/第三方检测'} 签入最终判定。
        </div>
      )}
      {audit.archiveLocked && (
        <div className="mt-3 rounded-lg border border-sky-700/70 bg-sky-950/30 px-2 py-1.5 text-xs text-sky-200">
          主权封存：DocFinal 已导出并触发 Archive_Trip，当前资产已进入只读状态。
        </div>
      )}
      {identity.roleAllowed && !gateStats.labQualified && (
        <div className="mt-3 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200">
          证据链不完整：缺少实验合格 Proof。
        </div>
      )}
      {identity.roleAllowed && gateStats.labQualified && !gateStats.qcCompliant && (
        <div className="mt-3 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200">
          证据链不完整：TripRole 现场判定未通过。
        </div>
      )}
      {identity.roleAllowed && !audit.snappegReady && (
        <div className="mt-3 rounded-lg border border-amber-700/70 bg-amber-950/30 px-2 py-1.5 text-xs text-amber-200">
          SnapPeg 证据链未就绪：请补齐带 GPS / 时间戳的现场照片。
        </div>
      )}
      {geoFenceActive && audit.geoTemporalBlocked && (
        <div className="mt-3 rounded-lg border border-rose-700/70 bg-rose-950/30 px-2 py-1.5 text-xs text-rose-200">
          空间越界：当前位置距锚点中心 {geoDistance ? `${Math.round(geoDistance)}m` : '未知'}，允许半径 {String(geoAnchor?.radiusM ?? '-')}m。{temporalBlocked ? ' 时间窗口不匹配。' : ''}
        </div>
      )}

      <GuardedSubmissionZone
        blocked={Boolean(blockedReason)}
        reason={blockedReason}
        btnBlueCls={btnBlueCls}
        btnGreenCls={btnGreenCls}
        btnRedCls={btnRedCls}
        executing={executing}
        mockGenerating={mockGenerating}
        isSpecBound={isSpecBound}
        tripStage={tripStage}
        onSubmitTrip={onSubmitTrip}
        onSubmitTripMock={onSubmitTripMock}
      />
    </div>
  )
}
