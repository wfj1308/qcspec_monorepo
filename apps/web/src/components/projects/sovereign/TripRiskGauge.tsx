import { useMemo  } from 'react'

type Props = {
  score: number
  title?: string
}

export default function TripRiskGauge({ score, title = '风险审计' }: Props) {
  const clamped = Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0
  const tone = clamped >= 80 ? 'text-emerald-300 border-emerald-500/60' : clamped >= 60 ? 'text-amber-300 border-amber-500/60' : 'text-rose-300 border-rose-500/60'
  const ring = useMemo(
    () => ({
      background: `conic-gradient(${clamped >= 80 ? '#10B981' : clamped >= 60 ? '#F59E0B' : '#F43F5E'} ${clamped * 3.6}deg, rgba(51,65,85,0.35) 0deg)`,
    }),
    [clamped],
  )

  return (
    <div className={`rounded-xl border ${tone} bg-slate-950/30 p-3`}>
      <div className="text-xs text-slate-400 mb-2">{title}</div>
      <div className="flex items-center gap-3">
        <div className="relative h-16 w-16 rounded-full p-1" style={ring}>
          <div className="h-full w-full rounded-full bg-slate-950 grid place-items-center">
            <span className="text-[11px] font-bold text-slate-100">{clamped.toFixed(0)}</span>
          </div>
        </div>
        <div className="text-xs leading-5">
          <div className="text-slate-200">风险分: {clamped.toFixed(2)}</div>
          <div className={clamped >= 80 ? 'text-emerald-300' : clamped >= 60 ? 'text-amber-300' : 'text-rose-300'}>
            等级: {clamped >= 80 ? '低风险' : clamped >= 60 ? '中风险' : '高风险'}
          </div>
        </div>
      </div>
    </div>
  )
}
