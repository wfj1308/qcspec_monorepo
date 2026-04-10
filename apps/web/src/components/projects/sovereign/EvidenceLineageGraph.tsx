
export type LineageNode = {
  id: string
  label: string
  subtitle?: string
  tone?: 'neutral' | 'ok' | 'warn'
}

type Props = {
  nodes: LineageNode[]
  onNodeClick?: (id: string) => void
}

function toneClass(tone: LineageNode['tone']) {
  if (tone === 'ok') return 'border-emerald-500/60 bg-emerald-950/20 text-emerald-100'
  if (tone === 'warn') return 'border-amber-500/60 bg-amber-950/20 text-amber-100'
  return 'border-slate-700 bg-slate-900/70 text-slate-100'
}

export default function EvidenceLineageGraph({ nodes, onNodeClick }: Props) {
  return (
    <div className="grid gap-2">
      {nodes.map((node, idx) => (
        <div key={node.id}>
          <button
            type="button"
            onClick={() => onNodeClick?.(node.id)}
            className={`w-full text-left rounded-lg border px-3 py-2 ${toneClass(node.tone)} ${onNodeClick ? 'hover:brightness-110' : ''}`}
          >
            <div className="text-xs font-semibold">{node.label}</div>
            {node.subtitle && <div className="text-[11px] mt-1 opacity-90 break-all">{node.subtitle}</div>}
          </button>
          {idx < nodes.length - 1 && (
            <div className="flex justify-center py-1 text-slate-500 text-xs">↓</div>
          )}
        </div>
      ))}
    </div>
  )
}
