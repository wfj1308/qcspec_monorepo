import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { MOBILE_ROLES } from '../types/mobile'
import type { MobileRole, RecentRecord } from '../types/mobile'

type ScanPageProps = {
  role: MobileRole
  recent: RecentRecord[]
  onRoleChange: (role: MobileRole) => void
  onResolveInput: (raw: string) => Promise<void>
  onOpenHistory: () => void
}

export default function ScanPage({
  role,
  recent,
  onRoleChange,
  onResolveInput,
  onOpenHistory,
}: ScanPageProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<number | null>(null)
  const [manualCode, setManualCode] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanHint, setScanHint] = useState('请将二维码放入取景框')
  const [working, setWorking] = useState(false)

  const sortedRecent = useMemo(() => recent.slice(0, 5), [recent])

  const stopScan = useCallback(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    setScanning(false)
  }, [])

  useEffect(() => () => stopScan(), [stopScan])

  const startScan = useCallback(async () => {
    if (scanning || working) return
    setScanHint('正在启动摄像头...')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setScanning(true)
      setScanHint('请将二维码放入取景框')

      const BarcodeDetectorCtor = (window as unknown as { BarcodeDetector?: new (o?: unknown) => { detect: (source: HTMLVideoElement) => Promise<Array<{ rawValue?: string }>> } }).BarcodeDetector
      if (!BarcodeDetectorCtor) {
        setScanHint('当前设备不支持自动识别，请手动输入桩号')
        return
      }

      const detector = new BarcodeDetectorCtor({ formats: ['qr_code'] })
      timerRef.current = window.setInterval(async () => {
        if (!videoRef.current || working) return
        try {
          const results = await detector.detect(videoRef.current)
          const rawValue = results[0]?.rawValue
          if (!rawValue) return
          setWorking(true)
          stopScan()
          await onResolveInput(rawValue)
        } catch {
          // keep scanning
        } finally {
          setWorking(false)
        }
      }, 650)
    } catch {
      setScanHint('无法打开摄像头，请检查权限')
      stopScan()
    }
  }, [onResolveInput, scanning, stopScan, working])

  const submitManual = useCallback(async () => {
    const value = manualCode.trim()
    if (!value) return
    setWorking(true)
    try {
      await onResolveInput(value)
    } finally {
      setWorking(false)
    }
  }, [manualCode, onResolveInput])

  return (
    <section className="mobile-page">
      <div className="mobile-card mobile-hero">
        <h1>QCSpec</h1>
        <p>质检现场助手</p>
      </div>

      <div className="mobile-card">
        <p className="mobile-title">我的角色</p>
        <div className="mobile-role-wrap">
          {MOBILE_ROLES.map((item) => (
            <button
              key={item}
              className={`mobile-role-chip ${item === role ? 'is-active' : ''}`}
              onClick={() => onRoleChange(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="mobile-card">
        <p className="mobile-title">操作提示</p>
        <p className="mobile-muted">扫码后会自动识别当前工序，符合角色可直接进入填写。</p>
      </div>

      <div className="mobile-card mobile-scan-box">
        <p className="mobile-title">扫描二维码</p>
        <video ref={videoRef} autoPlay muted playsInline className="mobile-video" />
        <p className="mobile-hint">{scanHint}</p>
        <div className="mobile-row">
          <button className="mobile-btn primary" disabled={working} onClick={startScan}>
            开始扫码
          </button>
          <button className="mobile-btn ghost" onClick={stopScan}>
            停止
          </button>
        </div>
      </div>

      <div className="mobile-card">
        <p className="mobile-label">或手动输入桩号</p>
        <div className="mobile-row">
          <input
            value={manualCode}
            onChange={(event) => setManualCode(event.target.value)}
            className="mobile-input"
            placeholder="例如 K12-340-phase4B"
          />
          <button className="mobile-btn primary" disabled={working} onClick={submitManual}>
            搜索
          </button>
        </div>
      </div>

      <div className="mobile-card">
        <div className="mobile-header-row">
          <p className="mobile-title">最近检查</p>
          <button className="mobile-btn ghost compact" onClick={onOpenHistory}>
            历史记录
          </button>
        </div>
        <div className="mobile-list">
          {sortedRecent.length ? (
            sortedRecent.map((item, index) => (
              <div key={`${item.code}-${item.time}-${index}`} className="mobile-list-item">
                <div>
                  <strong>{item.code}</strong> {item.step}
                  <div className="mobile-muted">{item.time}</div>
                </div>
                <span className="mobile-badge success">已完成</span>
              </div>
            ))
          ) : (
            <p className="mobile-muted">暂无记录</p>
          )}
        </div>
      </div>
    </section>
  )
}

