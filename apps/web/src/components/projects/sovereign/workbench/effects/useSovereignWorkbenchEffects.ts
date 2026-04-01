import type { MutableRefObject } from 'react'
import { useEffect, useRef } from 'react'
import { getDocument } from 'pdfjs-dist/legacy/build/pdf'

import { buildWorkspaceSnapshot } from '../../contextBuilders'

type SignMarker = {
  page?: number
  x: number
  y: number
} | null

type UseWorkspaceSnapshotEffectArgs = {
  onContextChange?: ((snapshot: ReturnType<typeof buildWorkspaceSnapshot>) => void) | undefined
  activePath: string
  displayProjectUri: string
  lifecycle: string
  activeCode: string
  activeStatus: string
  totalHash: string
  verifyUri: string
  finalProofReady: boolean
  isOnline: boolean
  offlineQueueSize: number
  disputeOpen: boolean
  disputeProof: string
  archiveLocked: boolean
}

type UseGeoFenceToastEffectArgs = {
  geoFenceActive: boolean
  activeUri: string
  geoTemporalBlocked: boolean
  geoDistance: number | null
  temporalBlocked: boolean
  geoRadiusM: number | null | undefined
  showToast: (message: string) => void
}

type UseDocPegPreviewEffectsArgs = {
  signRes: Record<string, unknown> | null
  setScanProofId: (value: string) => void
  pdfB64: string
  setDocModalOpen: (value: boolean) => void
  draftReady: boolean
  draftStamp: string
  setDraftStamp: (value: string) => void
  activeUri: string
  previewPdfB64: string
  pdfPage: number
  pdfCanvasRef: MutableRefObject<HTMLCanvasElement | null>
  setPdfRenderError: (value: string) => void
  setPdfRenderLoading: (value: boolean) => void
  activeSignMarker: SignMarker
  previewScrollRef: MutableRefObject<HTMLDivElement | null>
}

export function useWorkspaceSnapshotEffect({
  onContextChange,
  activePath,
  displayProjectUri,
  lifecycle,
  activeCode,
  activeStatus,
  totalHash,
  verifyUri,
  finalProofReady,
  isOnline,
  offlineQueueSize,
  disputeOpen,
  disputeProof,
  archiveLocked,
}: UseWorkspaceSnapshotEffectArgs) {
  useEffect(() => {
    onContextChange?.(buildWorkspaceSnapshot({
      activePath: activePath || displayProjectUri || '',
      lifecycle,
      activeCode,
      activeStatus,
      totalHash,
      verifyUri,
      finalProofReady,
      isOnline,
      offlineQueueSize,
      disputeOpen,
      disputeProof,
      archiveLocked,
    }))
  }, [
    activeCode,
    activePath,
    activeStatus,
    archiveLocked,
    displayProjectUri,
    disputeOpen,
    disputeProof,
    finalProofReady,
    isOnline,
    lifecycle,
    offlineQueueSize,
    onContextChange,
    totalHash,
    verifyUri,
  ])
}

export function useGeoFenceToastEffect({
  geoFenceActive,
  activeUri,
  geoTemporalBlocked,
  geoDistance,
  temporalBlocked,
  geoRadiusM,
  showToast,
}: UseGeoFenceToastEffectArgs) {
  const geoFenceToastRef = useRef('')

  useEffect(() => {
    if (!geoFenceActive || !activeUri) {
      geoFenceToastRef.current = ''
      return
    }
    if (!geoTemporalBlocked) return
    const key = `${activeUri}|${Math.round(geoDistance || 0)}|${temporalBlocked ? 'time' : 'geo'}`
    if (geoFenceToastRef.current === key) return
    geoFenceToastRef.current = key
    const distanceText = geoDistance != null ? `${Math.round(geoDistance)}m` : 'unknown'
    const radiusText = geoRadiusM != null ? `${geoRadiusM}m` : '-'
    showToast(`Geo-temporal block active: distance ${distanceText} / radius ${radiusText}`)
  }, [activeUri, geoDistance, geoFenceActive, geoRadiusM, geoTemporalBlocked, showToast, temporalBlocked])
}

export function useDocPegPreviewEffects({
  signRes,
  setScanProofId,
  pdfB64,
  setDocModalOpen,
  draftReady,
  draftStamp,
  setDraftStamp,
  activeUri,
  previewPdfB64,
  pdfPage,
  pdfCanvasRef,
  setPdfRenderError,
  setPdfRenderLoading,
  activeSignMarker,
  previewScrollRef,
}: UseDocPegPreviewEffectsArgs) {
  const pdfRenderRef = useRef<{ doc: unknown; task: { cancel: () => void } | null } | null>(null)

  useEffect(() => {
    const next = String(((signRes?.trip || {}) as Record<string, unknown>).output_proof_id || '')
    if (next) setScanProofId(next)
  }, [setScanProofId, signRes])

  useEffect(() => {
    if (pdfB64) setDocModalOpen(true)
  }, [pdfB64, setDocModalOpen])

  useEffect(() => {
    if (!draftReady) {
      if (draftStamp) setDraftStamp('')
      return
    }
    setDraftStamp(new Date().toISOString())
  }, [activeUri, draftReady, draftStamp, setDraftStamp])

  useEffect(() => {
    if (!previewPdfB64 || !pdfCanvasRef.current) {
      setPdfRenderError('')
      return
    }
    let cancelled = false
    let activeTask: { cancel: () => void; promise?: Promise<void> } | null = null
    let activeDoc: { destroy?: () => void; numPages?: number; getPage?: (n: number) => Promise<unknown> } | null = null
    setPdfRenderLoading(true)
    setPdfRenderError('')
    const bytes = Uint8Array.from(atob(previewPdfB64), (char) => char.charCodeAt(0))
    const loadingTask: any = getDocument({ data: bytes })
    loadingTask.promise.then((doc) => {
      if (cancelled) {
        doc.destroy?.()
        return
      }
      activeDoc = doc
      const total = Number(doc.numPages || 1)
      const pageNum = Math.min(Math.max(1, pdfPage), total)
      return doc.getPage?.(pageNum).then((page: unknown) => {
        if (cancelled || !pdfCanvasRef.current || !page) return
        const pdfPageInstance = page as {
          getViewport: (opts: { scale: number }) => { width: number; height: number }
          render: (opts: {
            canvasContext: CanvasRenderingContext2D
            viewport: { width: number; height: number }
          }) => { promise: Promise<void>; cancel: () => void }
        }
        const viewport = pdfPageInstance.getViewport({ scale: 1.2 })
        const canvas = pdfCanvasRef.current
        const context = canvas.getContext('2d')
        if (!context) return
        canvas.width = viewport.width
        canvas.height = viewport.height
        activeTask = pdfPageInstance.render({ canvasContext: context, viewport })
        pdfRenderRef.current = { doc, task: activeTask }
        return activeTask.promise
      })
    }).then(() => {
      if (cancelled) return
      setPdfRenderLoading(false)
    }).catch(() => {
      if (cancelled) return
      setPdfRenderError('PDF preview failed')
      setPdfRenderLoading(false)
    })
    return () => {
      cancelled = true
      if (activeTask) activeTask.cancel()
      if (pdfRenderRef.current?.task) pdfRenderRef.current.task.cancel()
      activeDoc?.destroy?.()
      loadingTask.destroy()
    }
  }, [pdfCanvasRef, pdfPage, previewPdfB64, setPdfRenderError, setPdfRenderLoading])

  useEffect(() => {
    if (!activeSignMarker || !previewScrollRef.current || !pdfCanvasRef.current) return
    const canvas = pdfCanvasRef.current
    const container = previewScrollRef.current
    const canvasHeight = canvas.getBoundingClientRect().height || canvas.offsetHeight
    if (!canvasHeight) return
    const targetTop = activeSignMarker.y * canvasHeight
    const nextTop = Math.max(0, targetTop - container.clientHeight / 2)
    container.scrollTo({ top: nextTop, behavior: 'smooth' })
  }, [activeSignMarker, pdfCanvasRef, previewPdfB64, previewScrollRef])
}
