type Props = {
  arRadius: string
  arLimit: string
  arLoading: boolean
  activeUri: string
  latestProofId: string
  totalHashShort: string
  nearestAnchorText: string
  arItems: Array<Record<string, unknown>>
  inputBaseCls: string
  btnAmberCls: string
  onArRadiusChange: (value: string) => void
  onArLimitChange: (value: string) => void
  onRunArOverlay: () => void
  onOpenFullscreen: () => void
  onFocusItem: (item: Record<string, unknown>) => void
}

export default function ArPanel({
  arRadius,
  arLimit,
  arLoading,
  activeUri,
  latestProofId,
  totalHashShort,
  nearestAnchorText,
  arItems,
  inputBaseCls,
  btnAmberCls,
  onArRadiusChange,
  onArLimitChange,
  onRunArOverlay,
  onOpenFullscreen,
  onFocusItem,
}: Props) {
  return (
    <div className="border border-dashed border-slate-700 rounded-xl p-3 mt-3">
      <div className="text-xs font-extrabold mb-1">AR 主权叠加</div>
      <div className="text-[11px] text-slate-400 mb-2">基于当前 GPS 获取附近锚点，现场验真视窗可直接叠加 Proof 与 NormPeg 判定。</div>
      <div className="grid gap-2">
        <div className="grid grid-cols-2 gap-2">
          <input
            value={arRadius}
            onChange={(event) => onArRadiusChange(event.target.value)}
            placeholder="半径（米）"
            className={inputBaseCls}
          />
          <input
            value={arLimit}
            onChange={(event) => onArLimitChange(event.target.value)}
            placeholder="最大锚点数"
            className={inputBaseCls}
          />
        </div>
        <button
          type="button"
          onClick={onRunArOverlay}
          disabled={arLoading}
          className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}
        >
          {arLoading ? '加载中...' : '获取 AR 叠加'}
        </button>
        <button
          type="button"
          onClick={onOpenFullscreen}
          className="px-3 py-2 text-sm font-bold border border-slate-700 rounded-lg bg-slate-900 text-slate-200 hover:bg-slate-800"
        >
          进入 AR 全屏
        </button>
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-300">
          <div>当前构件: {activeUri || '-'}</div>
          <div>最新 Proof: {latestProofId || '-'}</div>
          <div>总 存证哈希: {totalHashShort || '-'}</div>
          {nearestAnchorText && <div>最近锚点: {nearestAnchorText}</div>}
        </div>
        {arItems.length > 0 && (
          <div className="text-[11px] text-slate-400 grid gap-1">
            <div>命中锚点: {arItems.length}</div>
            {arItems.slice(0, 3).map((item, index) => (
              <div key={`ar-item-${index}`} className="truncate">
                {String(item.item_no || item.boq_item_uri || 'UTXO')} · {String(item.distance_m || '-')}m
              </div>
            ))}
          </div>
        )}
        {arItems.length > 0 && (
          <div className="grid gap-2 text-[11px]">
            {arItems.slice(0, 5).map((item, index) => (
              <button
                type="button"
                key={`ar-detail-${index}`}
                onClick={() => onFocusItem(item)}
                className="border border-slate-800 rounded-lg p-2 text-left bg-slate-900/40 hover:bg-slate-900/60"
              >
                <div className="text-slate-200 font-semibold truncate">
                  {String(item.item_no || item.item_name || item.boq_item_uri || 'UTXO')}
                </div>
                <div className="text-slate-500 truncate">Proof: {String(item.proof_id || '-')}</div>
                <div className="text-slate-500 truncate">哈希: {String(item.proof_hash || '-')}</div>
                <div className="text-slate-500 truncate">Trip: {String(item.trip_action || item.proof_type || '-')}</div>
                <div className="text-slate-500 truncate">距离: {String(item.distance_m || '-')}m · {String(item.created_at || '-')}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

