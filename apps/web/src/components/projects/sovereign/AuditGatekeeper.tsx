
import AuditDualGatePanel from './AuditDualGatePanel'
import AuditWarningStack from './AuditWarningStack'
import { useNormEngine } from './NormEngine'
import SettlementPreviewPanel from './SettlementPreviewPanel'
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
              <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-rose-300">审核守门</div>
              <div className="mt-2 text-sm font-semibold text-slate-100">提交通道已被物理拦截</div>
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
          <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Unspent' ? 'border-slate-500/70 bg-slate-900/60 text-slate-300' : 'border-slate-700/60 bg-slate-900/20 text-slate-500'}`}>未提交</span>
          <span className="text-slate-600">→</span>
          <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Reviewing' ? 'border-sky-500/70 bg-sky-950/30 text-sky-200' : tripStage === 'Approved' ? 'border-sky-700/50 bg-sky-950/10 text-sky-500' : 'border-slate-700/60 bg-slate-900/20 text-slate-500'}`}>审核中</span>
          <span className="text-slate-600">→</span>
          <span className={`rounded-full border px-2 py-0.5 ${tripStage === 'Approved' ? 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200' : 'border-slate-700/60 bg-slate-900/20 text-slate-500'}`}>已通过</span>
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
        {mockGenerating ? 'DocPeg 生成中...' : '确认并生成工序文档'}
      </button>
      <div className="mt-2 text-[11px] text-slate-500">
        提交后会进入工序审核链路；签认完成后自动冻结 SMU，并在右侧生成正式 DocPeg 预览与二维码。
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
            ? '缺少输入存证，无法进入工序提交流程。'
            : !isSpecBound
              ? '未绑定 NormRef / Gate，提交已被物理阻断。'
              : !gateStats.dualQualified
                ? audit.gateReason || '双门控未通过。'
                : audit.exceedBalance
                  ? '基线 UTXO 余额不足，请先发起变更补差工序。'
                  : !audit.snappegReady
                    ? 'SnapPeg 证据链未就绪，请先补齐现场证据。'
                    : audit.geoTemporalBlocked
                      ? '时空门控未通过，请修正现场定位或时间窗口。'
                      : ''

  return (
    <div className="mt-3 rounded-2xl border border-slate-700/70 bg-slate-950/30 p-3">
      <AuditDualGatePanel
        gateStats={gateStats}
        disputeOpen={audit.disputeOpen}
        archiveLocked={audit.archiveLocked}
        disputeProof={audit.disputeProof}
        disputeArbiterRole={audit.disputeArbiterRole}
        gateReason={audit.gateReason}
      />

      <div className="mb-2 flex items-center justify-between">
        <div>
          <div className="text-xs font-extrabold uppercase tracking-[0.18em] text-slate-400">审核守门</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">双门控、争议挂起与最终提交</div>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${blockedReason ? 'border-rose-500/70 bg-rose-950/30 text-rose-200' : 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200'}`}>
          {blockedReason ? '已拦截' : '可通行'}
        </span>
      </div>

      <SettlementPreviewPanel
        claimQty={claimQty}
        geoFormLocked={geoFormLocked}
        disputeOpen={audit.disputeOpen}
        archiveLocked={audit.archiveLocked}
        claimQtyProvided={claimQtyProvided}
        measuredQtyValue={measuredQtyValue}
        deltaSuggest={deltaSuggest}
        exceedBalance={audit.exceedBalance}
        baselineTotal={asset.baselineTotal}
        effectiveSpent={asset.effectiveSpent}
        effectiveClaimQtyValue={asset.effectiveClaimQtyValue}
        isContractSpu={project.isContractSpu}
        inputBaseCls={inputBaseCls}
        btnAmberCls={btnAmberCls}
        onClaimQtyChange={onClaimQtyChange}
        onSuggestDelta={onSuggestDelta}
      />

      <AuditWarningStack
        roleAllowed={identity.roleAllowed}
        disputeOpen={audit.disputeOpen}
        archiveLocked={audit.archiveLocked}
        disputeProof={audit.disputeProof}
        disputeArbiterRole={audit.disputeArbiterRole}
        labQualified={gateStats.labQualified}
        qcCompliant={gateStats.qcCompliant}
        snappegReady={audit.snappegReady}
        geoFenceActive={geoFenceActive}
        geoTemporalBlocked={geoFenceActive && (audit.geoTemporalBlocked || temporalBlocked)}
        geoDistance={geoDistance}
        geoRadiusM={geoAnchor?.radiusM}
      />

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
