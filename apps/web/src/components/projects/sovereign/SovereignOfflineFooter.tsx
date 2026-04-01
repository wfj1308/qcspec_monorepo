import React from 'react'

import type { OfflinePacketType } from './types'

type Props = {
  isOnline: boolean
  offlineCount: number
  offlineSyncConflicts: number
  offlineType: OfflinePacketType
  inputXsCls: string
  btnBlueCls: string
  offlineImporting: boolean
  offlineImportName: string
  offlineReplay: Record<string, unknown> | null
  offlinePacketsCount: number
  offlineImportRef: React.RefObject<HTMLInputElement | null>
  onOfflineTypeChange: (value: OfflinePacketType) => void
  onSealOfflinePacket: () => void
  onTriggerImport: () => void
  onExportOfflinePackets: () => void
  onClearOfflinePackets: () => void
  onImportOfflinePackets: (file: File | null) => void | Promise<void>
}

export default function SovereignOfflineFooter({
  isOnline,
  offlineCount,
  offlineSyncConflicts,
  offlineType,
  inputXsCls,
  btnBlueCls,
  offlineImporting,
  offlineImportName,
  offlineReplay,
  offlinePacketsCount,
  offlineImportRef,
  onOfflineTypeChange,
  onSealOfflinePacket,
  onTriggerImport,
  onExportOfflinePackets,
  onClearOfflinePackets,
  onImportOfflinePackets,
}: Props) {
  if (isOnline) return null

  return (
    <div className="fixed bottom-4 left-4 right-4 z-[1100] border border-amber-600/70 bg-amber-950/40 text-amber-100 rounded-xl px-4 py-3 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs font-semibold">
          离线主权模式 · 待同步 {offlineCount}
          {offlineSyncConflicts > 0 ? ` · 向量钟折叠 ${offlineSyncConflicts}` : ''}
        </div>
        <div className="flex items-center gap-2">
          <select value={offlineType} onChange={(event) => onOfflineTypeChange(event.target.value as OfflinePacketType)} className={inputXsCls}>
            <option value="quality.check">离线质检封存</option>
            <option value="variation.apply">离线变更补差</option>
          </select>
          <button type="button" onClick={onSealOfflinePacket} className={`px-3 py-2 text-xs font-bold ${btnBlueCls}`}>封存当前动作</button>
          <button type="button" disabled={offlineImporting} onClick={onTriggerImport} className={`px-3 py-2 text-xs font-bold ${btnBlueCls}`}>{offlineImporting ? '导入中...' : '导入离线包'}</button>
          <button type="button" onClick={onExportOfflinePackets} disabled={!offlinePacketsCount} className={`px-3 py-2 text-xs disabled:opacity-60 ${btnBlueCls}`}>导出</button>
          <button type="button" onClick={onClearOfflinePackets} disabled={!offlinePacketsCount} className="rounded-lg border border-slate-600 px-3 py-2 text-xs bg-slate-900 text-slate-200 disabled:opacity-60">清空</button>
        </div>
      </div>
      <input ref={offlineImportRef} type="file" accept="application/json,.json" onChange={(event) => void onImportOfflinePackets(event.target.files?.[0] || null)} className="hidden" />
      {offlineImportName && <div className="mt-2 text-[11px] text-amber-200">已选文件: {offlineImportName}</div>}
      {!!offlineReplay && (
        <div className="mt-2 text-[11px] text-amber-200">
          重放完成: {String(offlineReplay.replayed_count || 0)} 条 · 错误 {String(offlineReplay.error_count || 0)} 条
        </div>
      )}
    </div>
  )
}
