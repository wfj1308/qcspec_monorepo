import { useCallback, useEffect, useRef, useState } from 'react'

type UseScanConfirmActionArgs = {
  apiProjectUri: string
  inputProofId: string
  scanConfirmToken: string
  lat: string
  lng: string
  scanConfirmSignature: (payload: Record<string, unknown>) => Promise<unknown>
  showToast: (message: string) => void
}

export function useScanConfirmAction({
  apiProjectUri,
  inputProofId,
  scanConfirmToken,
  lat,
  lng,
  scanConfirmSignature,
  showToast,
}: UseScanConfirmActionArgs) {
  const [scanPayload, setScanPayload] = useState('')
  const [scanDid, setScanDid] = useState('')
  const [scanProofId, setScanProofId] = useState('')
  const [scanRes, setScanRes] = useState<Record<string, unknown> | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanLockStage, setScanLockStage] = useState<'idle' | 'locking' | 'done'>('idle')
  const [scanLockProofId, setScanLockProofId] = useState('')
  const scanLockTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!scanProofId && inputProofId) setScanProofId(String(inputProofId))
  }, [inputProofId, scanProofId])

  useEffect(() => {
    if (!scanPayload && scanConfirmToken) setScanPayload(String(scanConfirmToken))
  }, [scanConfirmToken, scanPayload])

  useEffect(() => {
    return () => {
      if (scanLockTimerRef.current) window.clearTimeout(scanLockTimerRef.current)
    }
  }, [])

  const doScanConfirm = useCallback(async () => {
    const proofId = String(scanProofId || inputProofId || '')
    if (!proofId) {
      showToast('请输入构件 Proof ID')
      return
    }
    if (!scanPayload) {
      showToast('请提供验收令牌')
      return
    }
    if (!scanDid) {
      showToast('请输入验收人 DID')
      return
    }
    setScanning(true)
    try {
      const now = new Date().toISOString()
      const payload = await scanConfirmSignature({
        input_proof_id: proofId,
        scan_payload: scanPayload,
        scanner_did: scanDid,
        scanner_role: 'SUPERVISOR',
        executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/supervisor/mobile/`,
        executor_role: 'SUPERVISOR',
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('现场联合验收失败')
        return
      }
      setScanRes(payload)
      showToast('现场联合验收成功')
      const finalProof = String(payload.output_proof_id || payload.final_proof_id || payload.proof_id || '')
      setScanLockProofId(finalProof)
      setScanLockStage('locking')
      if (scanLockTimerRef.current) window.clearTimeout(scanLockTimerRef.current)
      scanLockTimerRef.current = window.setTimeout(() => {
        setScanLockStage('done')
      }, 1400)
    } finally {
      setScanning(false)
    }
  }, [apiProjectUri, inputProofId, lat, lng, scanConfirmSignature, scanDid, scanPayload, scanProofId, showToast])

  const closeScanLock = useCallback(() => {
    setScanLockStage('idle')
  }, [])

  return {
    scanPayload,
    setScanPayload,
    scanDid,
    setScanDid,
    scanProofId,
    setScanProofId,
    scanRes,
    scanning,
    scanLockStage,
    scanLockProofId,
    doScanConfirm,
    closeScanLock,
  }
}
