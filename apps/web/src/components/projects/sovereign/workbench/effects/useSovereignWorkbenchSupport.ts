import type { Dispatch, SetStateAction } from 'react'
import { useEffect, useMemo, useRef } from 'react'

import { createQrSvg } from '../../../../../utils/qrcode'

type UseLabRefreshEffectArgs = {
  labQualified: boolean
  activeIsLeaf: boolean
  activeUri: string
  apiProjectUri: string
  isContractSpu: boolean
  sampleId: string
  loadingCtx: boolean
  compType: string
  loadContext: (activeUri: string, compType: string) => void | Promise<void>
}

type UseSovereignVerifyAssetsArgs = {
  mockDocRes: Record<string, unknown> | null
  verifyUri: string
  projectId: string
}

type UseActiveNodeBroadcastEffectArgs = {
  activeCode: string
  activeName: string
  activeStatus: string
  activeSpu: string
  activeUri: string
  activePath: string
  displayProjectUri: string
}

type UseDisputeProofAutofillEffectArgs = {
  openProofId: string
  disputeProofId: string
  setDisputeProofId: Dispatch<SetStateAction<string>>
}

type UseNowTickEffectArgs = {
  setNowTick: Dispatch<SetStateAction<number>>
}

export function useLabRefreshEffect({
  labQualified,
  activeIsLeaf,
  activeUri,
  apiProjectUri,
  isContractSpu,
  sampleId,
  loadingCtx,
  compType,
  loadContext,
}: UseLabRefreshEffectArgs) {
  const labRefreshTimerRef = useRef<number | null>(null)
  const labRefreshAttemptsRef = useRef(0)

  useEffect(() => {
    if (labQualified) {
      labRefreshAttemptsRef.current = 0
      if (labRefreshTimerRef.current) {
        window.clearTimeout(labRefreshTimerRef.current)
        labRefreshTimerRef.current = null
      }
      return
    }
    if (!activeIsLeaf || !activeUri || !apiProjectUri) return
    if (isContractSpu) return
    if (!sampleId) return
    if (loadingCtx) return
    if (labRefreshAttemptsRef.current >= 3) return
    if (labRefreshTimerRef.current) return
    labRefreshTimerRef.current = window.setTimeout(() => {
      labRefreshTimerRef.current = null
      labRefreshAttemptsRef.current += 1
      void loadContext(activeUri, compType)
    }, 3000)
    return () => {
      if (labRefreshTimerRef.current) {
        window.clearTimeout(labRefreshTimerRef.current)
        labRefreshTimerRef.current = null
      }
    }
  }, [activeIsLeaf, activeUri, apiProjectUri, compType, isContractSpu, labQualified, loadContext, loadingCtx, sampleId])
}

export function useActiveNodeBroadcastEffect({
  activeCode,
  activeName,
  activeStatus,
  activeSpu,
  activeUri,
  activePath,
  displayProjectUri,
}: UseActiveNodeBroadcastEffectArgs) {
  useEffect(() => {
    if (typeof window === 'undefined') return
    const detail = {
      code: activeCode,
      name: activeName,
      status: activeStatus,
      spu: activeSpu,
      path: activePath || displayProjectUri || '',
      uri: activeUri || displayProjectUri || '',
    }
    try {
      window.sessionStorage.setItem('coordos.activeNode', JSON.stringify(detail))
      window.dispatchEvent(new CustomEvent('coordos:active-node-change', { detail }))
    } catch {
      // ignore storage/event failures in preview env
    }
  }, [activeCode, activeName, activePath, activeSpu, activeStatus, activeUri, displayProjectUri])
}

export function useDisputeProofAutofillEffect({
  openProofId,
  disputeProofId,
  setDisputeProofId,
}: UseDisputeProofAutofillEffectArgs) {
  useEffect(() => {
    if (openProofId && !disputeProofId) {
      setDisputeProofId(openProofId)
    }
  }, [disputeProofId, openProofId, setDisputeProofId])
}

export function useNowTickEffect({
  setNowTick,
}: UseNowTickEffectArgs) {
  useEffect(() => {
    const timer = window.setInterval(() => setNowTick(Date.now()), 30000)
    return () => window.clearInterval(timer)
  }, [setNowTick])
}

export function useSovereignVerifyAssets({
  mockDocRes,
  verifyUri,
  projectId,
}: UseSovereignVerifyAssetsArgs) {
  const origin = useMemo(() => {
    if (typeof window === 'undefined') return ''
    return window.location.origin
  }, [])

  const qrSrc = useMemo(() => {
    const backendQrSrc = String(((mockDocRes?.docpeg || {}) as Record<string, unknown>).qr_png_base64 || '')
    return backendQrSrc || createQrSvg(verifyUri || 'qcspec-docpeg-empty', 140, 'medium')
  }, [mockDocRes, verifyUri])

  const docFinalVerifyBaseUrl = useMemo(() => {
    if (!origin) return ''
    return `${origin}/verify`
  }, [origin])

  const docFinalAuditUrl = useMemo(() => {
    if (!origin || !projectId) return verifyUri || ''
    return `${origin}/project/${encodeURIComponent(projectId)}/auditor/workbench?view=audit`
  }, [origin, projectId, verifyUri])

  const docFinalQrSrc = useMemo(
    () => createQrSvg(docFinalAuditUrl || verifyUri || 'qcspec-docfinal-empty', 120, 'medium'),
    [docFinalAuditUrl, verifyUri],
  )

  return {
    qrSrc,
    docFinalVerifyBaseUrl,
    docFinalAuditUrl,
    docFinalQrSrc,
  }
}
