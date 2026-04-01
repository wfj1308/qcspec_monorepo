type Props = {
  p2pNodeId: string
  offlineQueueSize: number
  p2pLastSync: string
  p2pAutoSync: boolean
  p2pPeers: string
  merkleRootText: string
  inputBaseCls: string
  btnBlueCls: string
  btnAmberCls: string
  onP2PAutoSyncChange: (checked: boolean) => void
  onP2PPeersChange: (value: string) => void
  onExportP2PManifest: () => void
  onSimulateP2PSync: () => void
}

export default function P2PSyncPanel({
  p2pNodeId,
  offlineQueueSize,
  p2pLastSync,
  p2pAutoSync,
  p2pPeers,
  merkleRootText,
  inputBaseCls,
  btnBlueCls,
  btnAmberCls,
  onP2PAutoSyncChange,
  onP2PPeersChange,
  onExportP2PManifest,
  onSimulateP2PSync,
}: Props) {
  return (
    <div className="mt-3 rounded-xl border border-dashed border-slate-700 p-3">
      <div className="mb-1 text-xs font-extrabold">GitPeg P2P 同步</div>
      <div className="mb-2 text-[11px] text-slate-400">本地节点可离线缓存，恢复联网后再做增量同步与合并。</div>
      <div className="grid gap-2 text-[11px] text-slate-300">
        <div>本地节点: {p2pNodeId}</div>
        <div>离线队列: {offlineQueueSize} 条 | 上次同步: {p2pLastSync || '未同步'}</div>
        <label className="flex items-center gap-2 text-[11px] text-slate-400">
          <input type="checkbox" checked={p2pAutoSync} onChange={(event) => onP2PAutoSyncChange(event.target.checked)} />
          启用自动增量同步
        </label>
        <textarea
          value={p2pPeers}
          onChange={(event) => onP2PPeersChange(event.target.value)}
          rows={2}
          placeholder="Peer 节点，使用逗号或换行分隔"
          className={`${inputBaseCls} resize-y`}
        />
        <div className="grid grid-cols-2 gap-2">
          <button type="button" onClick={onExportP2PManifest} className={`px-3 py-2 text-sm font-bold ${btnBlueCls}`}>导出同步清单</button>
          <button type="button" onClick={onSimulateP2PSync} className={`px-3 py-2 text-sm font-bold ${btnAmberCls}`}>记录一次同步</button>
        </div>
        <div className="text-[11px] text-slate-400">Merkle Root: {merkleRootText}</div>
      </div>
    </div>
  )
}
