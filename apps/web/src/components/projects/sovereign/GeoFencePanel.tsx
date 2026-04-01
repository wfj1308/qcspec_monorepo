type ScanChainBadge = {
  cls: string
  label: string
}

type TemporalWindow = {
  start: number
  end: number
}

type Props = {
  geoFenceStatusText: string
  scanEntryStatus: 'idle' | 'ok' | 'blocked'
  scanEntryRequired: boolean
  scanEntryToken: string
  scanChainBadge: ScanChainBadge
  geoAnchor: Record<string, unknown> | null
  geoDistance: number
  temporalWindow: TemporalWindow | null
  geoTemporalBlocked: boolean
}

function renderTimeWindow(temporalWindow: TemporalWindow | null) {
  if (!temporalWindow) return '未限制'
  const start = `${Math.floor(temporalWindow.start / 60).toString().padStart(2, '0')}:${String(temporalWindow.start % 60).padStart(2, '0')}`
  const end = `${Math.floor(temporalWindow.end / 60).toString().padStart(2, '0')}:${String(temporalWindow.end % 60).padStart(2, '0')}`
  return `${start} - ${end}`
}

export default function GeoFencePanel({
  geoFenceStatusText,
  scanEntryStatus,
  scanEntryRequired,
  scanEntryToken,
  scanChainBadge,
  geoAnchor,
  geoDistance,
  temporalWindow,
  geoTemporalBlocked,
}: Props) {
  return (
    <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
      <div className="mb-1 text-xs font-extrabold">动态时空围栏</div>
      <div className="mb-2 text-[11px] text-slate-400">扫码进入节点时实时校验，越界或超时会直接锁定录入动作。</div>
      <div className="grid gap-2 text-[11px] text-slate-300">
        <div>围栏状态: {geoFenceStatusText}</div>
        <div>扫码状态: {scanEntryStatus === 'ok' ? '已通过' : scanEntryStatus === 'blocked' ? '已拦截' : '未扫码'}</div>
        <div>扫码令牌: {scanEntryRequired ? (scanEntryToken ? '已提供' : '缺失') : '可选'}</div>
        <div className="flex items-center gap-2">
          <span>链状态</span>
          <span className={`rounded-full border px-2 py-0.5 ${scanChainBadge.cls}`}>{scanChainBadge.label}</span>
        </div>
        <div>锚点中心: {geoAnchor ? `${String(geoAnchor.lat ?? '-')}, ${String(geoAnchor.lng ?? '-')}` : '未配置'}</div>
        <div>允许半径: {geoAnchor ? `${String(geoAnchor.radiusM ?? '-')}m` : '-'}</div>
        <div>当前距离: {Number.isFinite(geoDistance) ? `${Math.round(geoDistance)}m` : '-'}</div>
        <div>时间窗口: {renderTimeWindow(temporalWindow)}</div>
        <div className={geoTemporalBlocked ? 'text-rose-300' : 'text-emerald-300'}>
          {geoTemporalBlocked ? 'Geo-Leap Error：已锁定录入按钮' : '定位与时间均合规'}
        </div>
      </div>
    </div>
  )
}
