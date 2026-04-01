type Props = {
  showAdvancedConsensus: boolean
  onToggleAdvancedConsensus: () => void
}

export default function AdvancedConsensusTogglePanel({
  showAdvancedConsensus,
  onToggleAdvancedConsensus,
}: Props) {
  return (
    <div className="mt-3 rounded-xl border border-slate-700/70 bg-slate-950/30 p-2">
      <button
        type="button"
        onClick={onToggleAdvancedConsensus}
        className="w-full px-2 py-1.5 text-left text-sm font-semibold text-slate-200 hover:text-white"
      >
        高级共识与审计面板 {showAdvancedConsensus ? '▲' : '▼'}
      </button>
    </div>
  )
}
