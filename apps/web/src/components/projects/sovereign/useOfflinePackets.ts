import { useCallback, useEffect, useRef, useState } from 'react'

import { downloadJson } from './fileUtils'
import {
  loadOfflinePacketsFromIndexedDb,
  mergeOfflinePacketSets,
  saveOfflinePacketsToIndexedDb,
  stampOfflinePacket,
} from './offlineSync'
import type { OfflinePacketType } from './types'

type QueueOfflinePacketOptions = {
  actorId: string
  did: string
}

type UseOfflinePacketsArgs = {
  storageKey: string
  autoReplayEnabled: boolean
  replayDefaultExecutorUri: string
  replayOfflinePackets: (payload: {
    packets: Record<string, unknown>[]
    stop_on_error: boolean
    default_executor_uri: string
    default_executor_role: string
  }) => Promise<unknown>
  onReplayResults: (results: Array<Record<string, unknown>>) => boolean
  onReplayPatched: () => void | Promise<void>
  onSyncRecorded: (iso: string) => void
  showToast: (message: string) => void
}

export function useOfflinePackets({
  storageKey,
  autoReplayEnabled,
  replayDefaultExecutorUri,
  replayOfflinePackets,
  onReplayResults,
  onReplayPatched,
  onSyncRecorded,
  showToast,
}: UseOfflinePacketsArgs) {
  const [offlinePackets, setOfflinePackets] = useState<Record<string, unknown>[]>([])
  const [offlineType, setOfflineType] = useState<OfflinePacketType>('quality.check')
  const [offlineReplay, setOfflineReplay] = useState<Record<string, unknown> | null>(null)
  const [offlineStopOnError, setOfflineStopOnError] = useState(true)
  const [offlineReplaying, setOfflineReplaying] = useState(false)
  const [offlineImporting, setOfflineImporting] = useState(false)
  const [offlineImportName, setOfflineImportName] = useState('')
  const [offlineSyncConflicts, setOfflineSyncConflicts] = useState(0)
  const [isOnline, setIsOnline] = useState(true)
  const packetsRef = useRef(offlinePackets)

  useEffect(() => {
    packetsRef.current = offlinePackets
  }, [offlinePackets])

  const persistOfflinePackets = useCallback((next: Record<string, unknown>[]) => {
    packetsRef.current = next
    setOfflinePackets(next)
    if (typeof window === 'undefined') return
    window.localStorage.setItem(storageKey, JSON.stringify(next))
    void saveOfflinePacketsToIndexedDb(next)
  }, [storageKey])

  useEffect(() => {
    if (typeof window === 'undefined') return
    let cancelled = false
    void (async () => {
      try {
        const raw = window.localStorage.getItem(storageKey)
        const localPackets = raw ? JSON.parse(raw) : []
        const indexedPackets = await loadOfflinePacketsFromIndexedDb()
        const merged = mergeOfflinePacketSets(
          Array.isArray(localPackets)
            ? localPackets.filter((item) => item && typeof item === 'object') as Record<string, unknown>[]
            : [],
          indexedPackets,
        )
        if (!cancelled) {
          setOfflinePackets(merged)
          packetsRef.current = merged
          setOfflineSyncConflicts(Math.max(0, (Array.isArray(localPackets) ? localPackets.length : 0) + indexedPackets.length - merged.length))
        }
        window.localStorage.setItem(storageKey, JSON.stringify(merged))
        void saveOfflinePacketsToIndexedDb(merged)
      } catch {
        if (!cancelled) {
          setOfflinePackets([])
          packetsRef.current = []
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [storageKey])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const update = () => setIsOnline(Boolean(navigator.onLine))
    update()
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  const queueOfflinePacket = useCallback(async (
    packet: Record<string, unknown>,
    options: QueueOfflinePacketOptions,
  ) => {
    const previousPackets = packetsRef.current
    const stamped = await stampOfflinePacket(packet, {
      actorId: options.actorId,
      did: options.did,
      previousPackets,
    })
    const next = mergeOfflinePacketSets(previousPackets, [stamped])
    persistOfflinePackets(next)
  }, [persistOfflinePackets])

  const replayOffline = useCallback(async () => {
    if (!packetsRef.current.length) {
      showToast('离线队列为空')
      return
    }
    setOfflineReplaying(true)
    try {
      const payload = await replayOfflinePackets({
        packets: packetsRef.current,
        stop_on_error: offlineStopOnError,
        default_executor_uri: replayDefaultExecutorUri,
        default_executor_role: 'TRIPROLE',
      }) as Record<string, unknown> | null
      if (!payload) {
        showToast('离线重放失败')
        return
      }
      setOfflineReplay(payload)
      const errCount = Number(payload.error_count || 0)
      const results = Array.isArray(payload.results)
        ? (payload.results as Array<Record<string, unknown>>)
        : []
      if (results.length && onReplayResults(results)) {
        void onReplayPatched()
      }
      if (errCount === 0) {
        persistOfflinePackets([])
        setOfflineSyncConflicts(0)
        onSyncRecorded(new Date().toISOString())
      }
    } finally {
      setOfflineReplaying(false)
    }
  }, [
    offlineStopOnError,
    onReplayPatched,
    onReplayResults,
    onSyncRecorded,
    persistOfflinePackets,
    replayDefaultExecutorUri,
    replayOfflinePackets,
    showToast,
  ])

  useEffect(() => {
    if (!isOnline || !autoReplayEnabled || !offlinePackets.length || offlineReplaying) return
    void replayOffline()
  }, [autoReplayEnabled, isOnline, offlinePackets.length, offlineReplaying, replayOffline])

  const removeOfflinePacket = useCallback((packetId: string) => {
    const next = packetsRef.current.filter((packet) => String(packet.offline_packet_id || '') !== packetId)
    persistOfflinePackets(next)
  }, [persistOfflinePackets])

  const clearOfflinePackets = useCallback(() => {
    persistOfflinePackets([])
  }, [persistOfflinePackets])

  const exportOfflinePackets = useCallback(() => {
    if (!packetsRef.current.length) {
      showToast('离线队列为空')
      return
    }
    downloadJson(`offline-packets-${Date.now()}.json`, packetsRef.current)
  }, [showToast])

  const importOfflinePackets = useCallback(async (file: File | null) => {
    if (!file) return
    setOfflineImporting(true)
    setOfflineImportName(file.name || '')
    try {
      const text = await file.text()
      const parsed = JSON.parse(text)
      if (!Array.isArray(parsed)) {
        showToast('离线包格式错误')
        return
      }
      const imported = parsed.filter((item) => typeof item === 'object' && item) as Record<string, unknown>[]
      const current = packetsRef.current
      const next = mergeOfflinePacketSets(current, imported)
      setOfflineSyncConflicts(Math.max(0, current.length + imported.length - next.length))
      persistOfflinePackets(next)
      showToast(`已导入 ${parsed.length} 条离线包`)
    } catch {
      showToast('离线包解析失败')
    } finally {
      setOfflineImporting(false)
    }
  }, [persistOfflinePackets, showToast])

  const simulateP2PSync = useCallback(() => {
    const current = packetsRef.current
    const merged = mergeOfflinePacketSets(current, [])
    const conflictCount = Math.max(0, current.length - merged.length)
    setOfflineSyncConflicts(conflictCount)
    persistOfflinePackets(merged)
    const syncedAt = new Date().toISOString()
    onSyncRecorded(syncedAt)
    showToast(`GitPeg P2P 已记录本地同步时间${conflictCount > 0 ? `，并折叠 ${conflictCount} 条冲突包` : ''}`)
  }, [onSyncRecorded, persistOfflinePackets, showToast])

  return {
    offlinePackets,
    offlineType,
    setOfflineType,
    offlineReplay,
    offlineStopOnError,
    setOfflineStopOnError,
    offlineReplaying,
    offlineImporting,
    offlineImportName,
    offlineSyncConflicts,
    isOnline,
    queueOfflinePacket,
    replayOffline,
    removeOfflinePacket,
    clearOfflinePackets,
    exportOfflinePackets,
    importOfflinePackets,
    simulateP2PSync,
  }
}
