import type { ComponentProps } from 'react'

import { toneForDistance } from './analysisUtils'
import DidFloatingCard from './DidFloatingCard'
import EvidenceLineageGraph from './EvidenceLineageGraph'

type TraceNodes = ComponentProps<typeof EvidenceLineageGraph>['nodes']

type Props = {
  ar: {
    focus: Record<string, unknown> | null
    fullscreen: boolean
    lat: string
    lng: string
    radius: string
    filteredItems: Array<Record<string, unknown>>
    totalItemsCount: number
    loading: boolean
    filterMax: string
    inputBaseCls: string
    btnBlueCls: string
    btnAmberCls: string
    onCopyText: (label: string, value: string) => void
    onFilterMaxChange: (value: string) => void
    onRefresh: () => void
    onCloseFocus: () => void
    onJumpToItem: (item: Record<string, unknown>) => void
    onCloseFullscreen: () => void
    onSelectFullscreenItem: (item: Record<string, unknown>) => void
  }
  fingerprint: {
    open: boolean
    evidence: Array<{ name: string; ntp: string }>
    onClose: () => void
  }
  trace: {
    open: boolean
    nodes: TraceNodes
    onClose: () => void
  }
  floatingDid: ComponentProps<typeof DidFloatingCard>
}

export default function SovereignWorkbenchOverlays({
  ar,
  fingerprint,
  trace,
  floatingDid,
}: Props) {
  return (
    <>
      {ar.focus && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">AR 现场验真视窗</div>
            <div className="text-xs text-slate-400 break-all grid gap-1">
              <div>细目: {String(ar.focus.item_no || ar.focus.item_name || ar.focus.boq_item_uri || '-')}</div>
              <div>存证ID: {String(ar.focus.proof_id || '-')}</div>
              <div>存证哈希: {String(ar.focus.proof_hash || '-')}</div>
              <div>Trip: {String(ar.focus.trip_action || ar.focus.proof_type || '-')}</div>
              <div>阶段: {String(ar.focus.lifecycle_stage || '-')}</div>
              <div>结果: {String(ar.focus.result || '-')}</div>
              <div>距离: {String(ar.focus.distance_m || '-')}m</div>
              <div>时间: {String(ar.focus.created_at || '-')}</div>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
              <span>GPS: {ar.lat}, {ar.lng}</span>
              <button
                type="button"
                onClick={() => ar.onCopyText('AR 存证哈希', String(ar.focus?.proof_hash || ''))}
                className="px-2 py-1 rounded border border-slate-700 text-[10px] text-slate-200 hover:bg-slate-800"
              >
                复制 Hash
              </button>
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <button type="button" onClick={() => ar.focus && ar.onJumpToItem(ar.focus)} className={`px-3 py-2 text-sm font-bold ${ar.btnBlueCls}`}>定位到细目</button>
              <button type="button" onClick={ar.onCloseFocus} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}

      {ar.fullscreen && (
        <div className="fixed inset-0 z-[1300] bg-slate-950/95 text-slate-100">
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-b from-slate-900/60 via-slate-950/40 to-slate-950/80" />
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute left-1/2 top-1/2 w-14 h-14 -translate-x-1/2 -translate-y-1/2 border border-emerald-400/60 rounded-full" />
              <div className="absolute left-1/2 top-1/2 w-2 h-2 -translate-x-1/2 -translate-y-1/2 bg-emerald-400 rounded-full shadow-[0_0_16px_rgba(16,185,129,0.8)]" />
              <div className="absolute left-1/2 top-1/2 w-[1px] h-20 -translate-x-1/2 -translate-y-[calc(50%+40px)] bg-emerald-400/70" />
              <div className="absolute left-1/2 top-1/2 w-[1px] h-20 -translate-x-1/2 translate-y-[calc(50%+40px)] bg-emerald-400/70" />
              <div className="absolute left-1/2 top-1/2 h-[1px] w-20 -translate-y-1/2 -translate-x-[calc(50%+40px)] bg-emerald-400/70" />
              <div className="absolute left-1/2 top-1/2 h-[1px] w-20 -translate-y-1/2 translate-x-[calc(50%+40px)] bg-emerald-400/70" />
            </div>
          </div>
          <div className="relative z-10 h-full w-full flex flex-col">
            <div className="px-4 py-3 flex items-center justify-between border-b border-slate-800/60 bg-slate-950/70">
              <div>
                <div className="text-sm font-extrabold">AR 现场验真全屏</div>
                <div className="text-[11px] text-slate-400">
                  GPS: {ar.lat}, {ar.lng} · 半径 {ar.radius}m · 锚点 {ar.filteredItems.length}/{ar.totalItemsCount}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={ar.onRefresh}
                  disabled={ar.loading}
                  className={`px-3 py-2 text-xs font-bold ${ar.btnAmberCls}`}
                >
                  {ar.loading ? '刷新中...' : '刷新锚点'}
                </button>
                <button
                  type="button"
                  onClick={ar.onCloseFullscreen}
                  className="px-3 py-2 text-xs border border-slate-700 rounded-lg bg-slate-900 text-slate-200"
                >
                  退出
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-4 py-4">
              <div className="mb-3 grid gap-2">
                <div className="text-[11px] text-slate-400">距离过滤（米）</div>
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <input value={ar.filterMax} onChange={(e) => ar.onFilterMaxChange(e.target.value)} placeholder="例如 120" className={ar.inputBaseCls} />
                  <div className="grid grid-cols-3 gap-1">
                    {[20, 50, 100].map((meter) => (
                      <button
                        type="button"
                        key={`ar-filter-${meter}`}
                        onClick={() => ar.onFilterMaxChange(String(meter))}
                        className="px-2 py-2 text-[11px] border border-slate-700 rounded bg-slate-900 text-slate-200 hover:bg-slate-800"
                      >
                        {meter}m
                      </button>
                    ))}
                  </div>
                </div>
                <div className="text-[11px] text-slate-500">提示：留空或 0 表示不筛选</div>
              </div>
              {ar.totalItemsCount === 0 && (
                <div className="text-sm text-slate-400 text-center mt-10">暂无锚点，请先获取 AR 叠加。</div>
              )}
              {ar.totalItemsCount > 0 && ar.filteredItems.length === 0 && (
                <div className="text-sm text-slate-400 text-center mt-4">当前距离过滤未命中锚点，请放宽范围。</div>
              )}
              <div className="grid gap-3">
                {ar.filteredItems.map((item, idx) => {
                  const distance = Number(item.distance_m ?? 0)
                  const tone = toneForDistance(distance)
                  return (
                    <button
                      type="button"
                      key={`ar-full-${idx}`}
                      onClick={() => ar.onSelectFullscreenItem(item)}
                      className="w-full text-left border border-slate-800 rounded-xl p-3 bg-slate-950/70 hover:bg-slate-900/70"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-semibold text-slate-100 truncate">
                          {String(item.item_no || item.item_name || item.boq_item_uri || 'UTXO')}
                        </div>
                        <div className={`text-[10px] px-2 py-0.5 rounded-full border ${tone}`}>{String(item.distance_m || '-')}m</div>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-400 truncate">Proof: {String(item.proof_id || '-')}</div>
                      <div className="text-[11px] text-slate-500 truncate">Trip: {String(item.trip_action || item.proof_type || '-')}</div>
                      <div className="text-[11px] text-slate-500 truncate">时间: {String(item.created_at || '-')}</div>
                    </button>
                  )
                })}
              </div>
            </div>
            <div className="px-4 py-3 border-t border-slate-800/60 text-[11px] text-slate-400 bg-slate-950/70">
              提示：点击锚点可进入验真详情并定位到对应细目。
            </div>
          </div>
        </div>
      )}

      <DidFloatingCard {...floatingDid} />

      {fingerprint.open && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[520px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">主权指纹</div>
            <div className="text-xs text-slate-400 mb-3">指纹数量: {fingerprint.evidence.length}</div>
            <div className="grid gap-2 max-h-[360px] overflow-y-auto">
              {fingerprint.evidence.length === 0 && <div className="text-xs text-slate-500">暂无指纹记录</div>}
              {fingerprint.evidence.map((item, idx) => (
                <div key={`${item.name}-${idx}`} className="border border-slate-800 rounded-lg p-2 text-xs">
                  <div className="text-emerald-300 font-semibold">指纹记录 #{String(idx + 1).padStart(2, '0')} · 主权已锁定</div>
                  <div className="text-slate-400 mt-1">文件: {item.name}</div>
                  <div className="text-slate-500">授时戳: {item.ntp}</div>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-3">
              <button type="button" onClick={fingerprint.onClose} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}

      {trace.open && (
        <div className="fixed inset-0 bg-slate-950/70 z-[1200] grid place-items-center">
          <div className="w-[560px] max-w-[92vw] rounded-xl border border-slate-700 bg-slate-950 text-slate-100 p-4">
            <div className="text-sm font-extrabold mb-2">样品溯源图谱</div>
            <EvidenceLineageGraph nodes={trace.nodes} />
            <div className="flex justify-end mt-3">
              <button type="button" onClick={trace.onClose} className="border border-slate-700 rounded-lg px-3 py-2 bg-slate-900 text-slate-200">关闭</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

