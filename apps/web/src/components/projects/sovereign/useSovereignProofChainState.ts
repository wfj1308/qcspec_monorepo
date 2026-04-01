import { useMemo } from 'react'

import type { EvidenceCenterPayload } from './types'

type UseProofChainInputsArgs = {
  ctx: Record<string, unknown> | null
  execRes: Record<string, unknown> | null
  signRes: Record<string, unknown> | null
  mockDocRes: Record<string, unknown> | null
  evidenceCenter: EvidenceCenterPayload | null
}

type UseProofChainStatusArgs = {
  signRes: Record<string, unknown> | null
  execRes: Record<string, unknown> | null
  scanRes: Record<string, unknown> | null
  scanLockProofId: string
  verifyUri: string
}

export function useSovereignProofChainInputs({
  ctx,
  execRes,
  signRes,
  mockDocRes,
  evidenceCenter,
}: UseProofChainInputsArgs) {
  const inputProofId = useMemo(() => {
    const trip = (ctx?.trip || {}) as Record<string, unknown>
    const node = (ctx?.node || {}) as Record<string, unknown>
    const result = (execRes?.trip || {}) as Record<string, unknown>
    return String(result.output_proof_id || trip.input_proof_id || node.proof_id || '')
  }, [ctx, execRes])

  const verifyUri = useMemo(() => {
    const fromSign = String(((signRes?.docpeg || {}) as Record<string, unknown>).verify_uri || '')
    if (fromSign) return fromSign
    return String(((mockDocRes?.docpeg || {}) as Record<string, unknown>).verify_uri || '')
  }, [mockDocRes, signRes])

  const pdfB64 = useMemo(() => {
    const fromSign = String(((signRes?.docpeg || {}) as Record<string, unknown>).pdf_preview_b64 || '')
    if (fromSign) return fromSign
    return String(((mockDocRes?.docpeg || {}) as Record<string, unknown>).pdf_preview_b64 || '')
  }, [mockDocRes, signRes])

  const totalHash = useMemo(() => {
    const fromSign = String(((signRes?.trip || {}) as Record<string, unknown>).total_proof_hash || '')
    if (fromSign) return fromSign
    const fromMock = String((mockDocRes?.total_proof_hash || '')).trim()
    if (fromMock) return fromMock
    return String((evidenceCenter?.totalProofHash || '')).trim()
  }, [evidenceCenter?.totalProofHash, mockDocRes, signRes])

  const scanConfirmUri = useMemo(
    () => String(((signRes?.docpeg || {}) as Record<string, unknown>).scan_confirm_uri || ''),
    [signRes],
  )

  const scanConfirmToken = useMemo(
    () => String(((signRes?.docpeg || {}) as Record<string, unknown>).scan_confirm_token || ''),
    [signRes],
  )

  return {
    inputProofId,
    verifyUri,
    pdfB64,
    totalHash,
    scanConfirmUri,
    scanConfirmToken,
  }
}

export function useSovereignProofChainStatus({
  signRes,
  execRes,
  scanRes,
  scanLockProofId,
  verifyUri,
}: UseProofChainStatusArgs) {
  const finalProofId = useMemo(() => {
    const fromScan = String(scanLockProofId || '')
    if (fromScan) return fromScan
    const scanOut = String(((scanRes || {}) as Record<string, unknown>).output_proof_id || '')
    if (scanOut) return scanOut
    return String(
      ((signRes || {}) as Record<string, unknown>).output_proof_id ||
      ((signRes?.trip || {}) as Record<string, unknown>).output_proof_id ||
      '',
    )
  }, [scanLockProofId, scanRes, signRes])

  const approvedProofId = useMemo(() => {
    return String(
      ((signRes?.trip || {}) as Record<string, unknown>).output_proof_id ||
      (signRes as Record<string, unknown> | null)?.output_proof_id ||
      '',
    ).trim()
  }, [signRes])

  const tripStage = useMemo<'Unspent' | 'Reviewing' | 'Approved'>(() => {
    if (approvedProofId) return 'Approved'
    const reviewingProof = String(((execRes?.trip || {}) as Record<string, unknown>).output_proof_id || '').trim()
    if (reviewingProof) return 'Reviewing'
    return 'Unspent'
  }, [approvedProofId, execRes])

  const finalProofReady = Boolean(verifyUri || finalProofId)

  return {
    finalProofId,
    approvedProofId,
    tripStage,
    finalProofReady,
  }
}
