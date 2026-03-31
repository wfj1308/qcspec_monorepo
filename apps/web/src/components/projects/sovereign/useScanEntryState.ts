import { useCallback, useEffect, useState } from 'react'

import { sha256Hex } from './fileUtils'

type ScanEntryStatus = 'idle' | 'ok' | 'blocked'

type UseScanEntryStateParams = {
  activeUri: string
  geoTemporalBlocked: boolean
  lat: string
  lng: string
  showToast: (message: string) => void
  enqueueScanEntryPacket: (status: 'ok' | 'blocked', tokenHash: string, nowIso: string, tokenPresent: boolean) => string | void
  appendScanEntryLog: (entry: Record<string, unknown>) => void
  loadEvidenceCenter: () => void | Promise<void>
}

type UseScanEntryStateResult = {
  scanEntryAt: string
  scanEntryStatus: ScanEntryStatus
  scanEntryToken: string
  scanEntryTokenHash: string
  scanEntryRequired: boolean
  setScanEntryToken: (value: string) => void
  setScanEntryRequired: (value: boolean) => void
  handleScanEntry: () => void
}

export function useScanEntryState({
  activeUri,
  geoTemporalBlocked,
  lat,
  lng,
  showToast,
  enqueueScanEntryPacket,
  appendScanEntryLog,
  loadEvidenceCenter,
}: UseScanEntryStateParams): UseScanEntryStateResult {
  const [scanEntryAt, setScanEntryAt] = useState('')
  const [scanEntryStatus, setScanEntryStatus] = useState<ScanEntryStatus>('idle')
  const [scanEntryToken, setScanEntryToken] = useState('')
  const [scanEntryTokenHash, setScanEntryTokenHash] = useState('')
  const [scanEntryRequired, setScanEntryRequired] = useState(true)

  useEffect(() => {
    setScanEntryAt('')
    setScanEntryStatus('idle')
    setScanEntryToken('')
    setScanEntryTokenHash('')
  }, [activeUri])

  const handleScanEntry = useCallback(() => {
    if (!activeUri) {
      showToast('请先选择细目')
      return
    }
    if (scanEntryRequired && !scanEntryToken.trim()) {
      showToast('扫码令牌为空，请先扫码')
      return
    }
    const status: 'ok' | 'blocked' = geoTemporalBlocked ? 'blocked' : 'ok'
    const nowIso = new Date().toISOString()
    setScanEntryStatus(status)
    setScanEntryAt(nowIso)
    const token = scanEntryToken.trim()
    const tokenPresent = Boolean(token)
    const commitRecord = (tokenHash: string) => {
      const packetId = enqueueScanEntryPacket(status, tokenHash, nowIso, tokenPresent)
      appendScanEntryLog({
        item_uri: activeUri,
        token: tokenPresent ? 'submitted' : 'missing',
        token_hash: tokenHash || null,
        status,
        reason: status === 'blocked' ? 'geo_temporal_block' : '',
        lat,
        lng,
        created_at: nowIso,
        chain_status: 'queued',
        offline_packet_id: packetId || '',
      })
      void loadEvidenceCenter()
    }
    if (token) {
      void sha256Hex(`scan-entry:${token}|${activeUri}`).then((hash) => {
        setScanEntryTokenHash(hash)
        commitRecord(hash)
      })
    } else {
      setScanEntryTokenHash('')
      commitRecord('')
    }
    showToast(status === 'blocked' ? '空间坐标越界（Geo-Leap Error），扫码进入被拦截' : '扫码进入成功，已通过时空围栏')
  }, [activeUri, appendScanEntryLog, enqueueScanEntryPacket, geoTemporalBlocked, lat, lng, loadEvidenceCenter, scanEntryRequired, scanEntryToken, showToast])

  return {
    scanEntryAt,
    scanEntryStatus,
    scanEntryToken,
    scanEntryTokenHash,
    scanEntryRequired,
    setScanEntryToken,
    setScanEntryRequired,
    handleScanEntry,
  }
}
