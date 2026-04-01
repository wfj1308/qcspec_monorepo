import TripRiskGauge from './TripRiskGauge'

type GateStats = {
  qcStatus: string
  labStatus: string
  labTotal: number
  labPass: number
  labLatestPass: string
  labLatestHash: string
  dualQualified: boolean
  total: number
  pass: number
  fail: number
  pending: number
  qcCompliant: boolean
}

type Props = {
  gateStats: GateStats
  projectIsContractSpu: boolean
  activeIsLeaf: boolean
  effectiveRiskScore: number
  rejecting: boolean
  btnRedCls: string
  onRecordRejectTrip: () => void
}

export default function WorkbenchQualityPanels({
  gateStats,
  projectIsContractSpu,
  activeIsLeaf,
  effectiveRiskScore,
  rejecting,
  btnRedCls,
  onRecordRejectTrip,
}: Props) {
  return (
    <>
      <div className="mb-3 grid grid-cols-2 gap-3 max-[1180px]:grid-cols-1">
        <div className="rounded-xl border border-emerald-700/60 bg-emerald-950/25 p-3">
          <div className="mb-1 text-xs text-emerald-300">双合格门控</div>
          <div className="text-sm font-semibold text-slate-100">现场质检: {gateStats.qcStatus}</div>
          <div className="mt-1 text-sm font-semibold text-slate-100">实验佐证: {gateStats.labStatus}</div>
          {!projectIsContractSpu && gateStats.labTotal > 0 && (
            <div className="mt-1 text-xs text-slate-300">
              实验室证明: {gateStats.labPass}/{gateStats.labTotal}
              {gateStats.labLatestPass && <span className="ml-2">最新 PASS: {gateStats.labLatestPass}</span>}
              {gateStats.labLatestHash && <div className="mt-1 text-[11px] text-emerald-300">主权已锁定</div>}
            </div>
          )}
          {!projectIsContractSpu && !gateStats.labTotal && <div className="mt-1 text-xs text-amber-200">未检测到实验室 Proof Hash，请先录入 LabPeg</div>}
          <div className={`mt-2 text-xs font-bold ${gateStats.dualQualified ? 'text-emerald-300' : 'text-amber-300'}`}>双合格门控: {gateStats.dualQualified ? '通过' : '未通过'}</div>
          {!gateStats.dualQualified && activeIsLeaf && (
            <button type="button" onClick={onRecordRejectTrip} disabled={rejecting || !activeIsLeaf} className={`mt-2 w-full rounded-lg border px-3 py-2 text-xs font-bold disabled:opacity-60 ${btnRedCls}`}>
              {rejecting ? '记录中...' : '记录不合格（Reject Trip）'}
            </button>
          )}
        </div>

        <div className="rounded-xl border border-sky-700/60 bg-sky-950/20 p-3">
          <div className="mb-1 text-xs text-sky-300">规范判定概览（NormPeg）</div>
          <div className="text-sm text-slate-100">总项: {gateStats.total}</div>
          <div className="text-sm text-emerald-300">合格: {gateStats.pass}</div>
          <div className="text-sm text-red-300">不合格: {gateStats.fail}</div>
          <div className="text-sm text-amber-200">待检: {gateStats.pending}</div>
          {!gateStats.qcCompliant && <div className="mt-2 text-xs text-amber-200">TripRole 判定未完成（is_compliant=false）</div>}
          {projectIsContractSpu && <div className="mt-2 text-xs text-slate-400">合同凭证类不启用 NormPeg 评分</div>}
        </div>
      </div>

      <div className="mb-3">
        <TripRiskGauge score={effectiveRiskScore} title="Risk Score 仪表盘" />
      </div>
    </>
  )
}
