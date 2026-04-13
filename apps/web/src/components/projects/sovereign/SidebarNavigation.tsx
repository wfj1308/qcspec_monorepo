import type { SovereignWorkspaceView } from './SovereignProjectContext'

type NavItem = {
  view: SovereignWorkspaceView
  label: string
  title: string
  detail: string
}

type Props = {
  items: NavItem[]
  activeView: SovereignWorkspaceView
  onNavigate: (view: SovereignWorkspaceView) => void
}

export default function SidebarNavigation({ items, activeView, onNavigate }: Props) {
  return (
    <aside className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">主权菜单</div>
      <div className="mt-3 grid gap-2">
        {items.map((item) => {
          const active = item.view === activeView
          return (
            <button
              key={item.view}
              type="button"
              onClick={() => onNavigate(item.view)}
              className={`rounded-2xl border px-3 py-3 text-left transition ${active ? 'border-slate-900 bg-slate-900 text-white shadow-[0_10px_24px_rgba(15,23,42,0.16)]' : 'border-slate-200 bg-slate-50 text-slate-900 hover:border-slate-300 hover:bg-white'}`}
            >
              <div className="text-xs font-semibold uppercase tracking-[0.16em] opacity-70">{item.title}</div>
              <div className="mt-1 text-base font-semibold">{item.label}</div>
              <div className={`mt-1 text-sm ${active ? 'text-slate-200' : 'text-slate-500'}`}>{item.detail}</div>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
