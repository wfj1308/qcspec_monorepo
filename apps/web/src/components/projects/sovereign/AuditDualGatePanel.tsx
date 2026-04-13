type GateStats = {
  qcCompliant: boolean
  qcStatus: string
  labQualified?: boolean
  labStatus: string
  dualQualified: boolean
}

type Props = {
  gateStats: GateStats
  disputeOpen: boolean
  archiveLocked: boolean
  disputeProof: string
  disputeArbiterRole: string
  gateReason: string
}

export default function AuditDualGatePanel({
  gateStats,
  disputeOpen,
  archiveLocked,
  disputeProof,
  disputeArbiterRole,
  gateReason,
}: Props) {
  return (
    <>
      <div className="mb-3 rounded-xl border border-slate-700/70 bg-slate-950/40 p-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">双门控指示器</div>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {[
            { label: '现场质检', ok: gateStats.qcCompliant, detail: gateStats.qcStatus },
            { label: '实验室（LabPeg）', ok: Boolean(gateStats.labQualified), detail: gateStats.labStatus },
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

      <div className={`mb-3 rounded-xl border px-3 py-2 ${gateStats.dualQualified && !disputeOpen && !archiveLocked ? 'border-emerald-500/70 bg-emerald-950/30 text-emerald-200' : 'border-rose-500/70 bg-rose-950/30 text-rose-200'}`}>
        <div className="text-xs font-extrabold">最终判定</div>
        <div className="text-sm font-bold">
          {archiveLocked
            ? '封存 | 归档工序已锁止'
            : disputeOpen
              ? `拦截 | ${disputeArbiterRole || '业主/第三方检测'} 仲裁中`
              : gateStats.dualQualified
                ? '通过 | 证据链完整'
                : `拦截 | ${gateReason || '证据链不完整'}`}
        </div>
        {disputeOpen && disputeProof && <div className="mt-1 text-[11px] opacity-80">争议存证: {disputeProof}</div>}
      </div>
    </>
  )
}
