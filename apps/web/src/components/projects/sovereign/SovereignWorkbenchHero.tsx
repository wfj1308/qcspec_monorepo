
type Props = {
  activePath: string
  displayProjectUri: string
  progressPct: number
  isOnline: boolean
  offlineCount: number
  nodeCount: number
  activeCode: string
  totalHash: string
  isTripView: boolean
  finalProofReady: boolean
  btnBlueCls: string
  onNavigateAudit?: (() => void) | undefined
}

export default function SovereignWorkbenchHero({
  activePath,
  displayProjectUri,
  progressPct,
  isOnline,
  offlineCount,
  nodeCount,
  activeCode,
  totalHash,
  isTripView,
  finalProofReady,
  btnBlueCls,
  onNavigateAudit,
}: Props) {
  return (
    <>
      <div className="mb-4 rounded-xl border border-slate-700/80 bg-slate-950/55 px-4 py-3 text-slate-200 shadow-[0_18px_36px_rgba(2,6,23,.24)]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-sky-300/80">主权执行控制台</div>
            <div className="mt-1 text-base font-bold text-slate-50">400 章主权资产树 + TripRole 执行闭环</div>
            <div className="mt-1 text-xs text-slate-400 break-all">当前主权路径: {activePath || '-'}</div>
            <div className="mt-2 rounded-lg border border-slate-700 bg-slate-950 text-slate-100 px-3 py-1.5 text-[11px] font-mono flex items-center gap-2">
              <span className="text-sky-300">v://</span>
              <span className="truncate">{activePath || displayProjectUri || '-'}</span>
            </div>
            <div className="mt-2">
              <div className="flex items-center justify-between text-[10px] text-slate-500">
                <span>钱袋子树红线刻度</span>
                <span>0 · 50 · 100</span>
              </div>
              <div className="relative mt-1 h-2 w-full rounded-full border border-slate-700 bg-slate-900 overflow-hidden">
                <div className="h-2 bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-500" style={{ width: `${Math.max(0, Math.min(100, progressPct))}%` }} />
                <div className="absolute right-0 top-0 h-full w-[2px] bg-rose-600" />
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[11px]">
            <div
              className={`rounded-full border px-2 py-0.5 flex items-center gap-1 ${isOnline ? 'border-slate-600 bg-slate-900/70 text-slate-300' : 'border-amber-500/60 bg-amber-950/30 text-amber-200'}`}
              title="同步云 · 离线队列"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M7 18h10a4 4 0 0 0 0-8 5.5 5.5 0 0 0-10.7 1.8A3.8 3.8 0 0 0 7 18Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              同步云 {offlineCount}
            </div>
            <span className="rounded-full border border-slate-600 bg-slate-900/70 px-2 py-0.5 text-slate-300">节点 {nodeCount}</span>
            <span className="rounded-full border border-sky-500/60 bg-sky-950/30 px-2 py-0.5 text-sky-200">当前 {activeCode || '-'}</span>
          </div>
        </div>
      </div>

      {!!totalHash && (
        <div className="mb-3 border border-emerald-600/80 bg-emerald-950 text-emerald-100 rounded-xl p-2">
          <div className="text-xs font-extrabold">总证明哈希: 主权已锁定</div>
          <div className="mt-1 text-xs">SMU 已冻结，证据链不可篡改</div>
          <div className="mt-1 text-[11px] font-mono break-all">总存证哈希: {totalHash}</div>
        </div>
      )}

      {isTripView && finalProofReady && onNavigateAudit && (
        <div className="mb-4 rounded-xl border border-sky-500/70 bg-sky-950/30 p-3 text-sky-100">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-xs font-extrabold">Proof 已生成</div>
              <div className="mt-1 text-[11px] text-sky-200">执行数据已落链，可一键跳转到证据与审计视图检查因果链。</div>
            </div>
            <button type="button" onClick={onNavigateAudit} className={`px-3 py-2 text-sm ${btnBlueCls}`}>
              打开证据与审计
            </button>
          </div>
        </div>
      )}
    </>
  )
}

