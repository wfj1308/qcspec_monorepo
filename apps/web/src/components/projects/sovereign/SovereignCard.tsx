
type SovereignCardTone = 'certified' | 'pending' | 'conflict'

type Props = {
  title: string
  subtitle?: string
  tone?: SovereignCardTone
  eyebrow?: string
  onClick?: () => void
  children?: React.ReactNode
}

const toneMap: Record<SovereignCardTone, string> = {
  certified: 'border-emerald-500/60 bg-emerald-950/18 text-emerald-100',
  pending: 'border-amber-500/60 bg-amber-950/18 text-amber-100',
  conflict: 'border-rose-500/60 bg-rose-950/18 text-rose-100',
}

export default function SovereignCard({
  title,
  subtitle,
  tone = 'pending',
  eyebrow,
  onClick,
  children,
}: Props) {
  const content = (
    <div className={`rounded-2xl border p-3 transition hover:-translate-y-[1px] ${toneMap[tone]}`}>
      {eyebrow && <div className="text-[10px] uppercase tracking-[0.16em] text-slate-400">{eyebrow}</div>}
      <div className="mt-1 text-sm font-semibold">{title}</div>
      {subtitle && <div className="mt-1 line-clamp-2 text-[11px] text-slate-300">{subtitle}</div>}
      {children && <div className="mt-3">{children}</div>}
    </div>
  )

  if (!onClick) return content

  return (
    <button type="button" onClick={onClick} className="w-full text-left">
      {content}
    </button>
  )
}
