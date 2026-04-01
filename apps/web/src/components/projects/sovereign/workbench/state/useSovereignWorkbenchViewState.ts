import { useMemo } from 'react'

import { sanitizeGenericLabel } from '../../treeUtils'
import type { TreeNode } from '../../types'

type SignRole = 'contractor' | 'supervisor' | 'owner'
type SignMarker = {
  page?: number
  x: number
  y: number
} | null

type Args = {
  active: TreeNode | null
  ctx: Record<string, unknown> | null
  signRes: Record<string, unknown> | null
  inputProofId: string
  verifyUri: string
  totalHash: string
  filteredDocs: Array<Record<string, unknown>>
  evidenceTimeline: Array<Record<string, unknown>>
  gateStats: {
    qcCompliant: boolean
    labLatestPass: string
    labQualified: boolean
  }
  signStep: number
  draftStamp: string
  executorDid: string
  supervisorDid: string
  ownerDid: string
  pdfB64: string
  signFocus: SignRole | ''
  buildDraftPdfBase64: (lines: string[]) => string
}

export function useSovereignWorkbenchViewState({
  active,
  ctx,
  signRes,
  inputProofId,
  verifyUri,
  totalHash,
  filteredDocs,
  evidenceTimeline,
  gateStats,
  signStep,
  draftStamp,
  executorDid,
  supervisorDid,
  ownerDid,
  pdfB64,
  signFocus,
  buildDraftPdfBase64,
}: Args) {
  const docpegPageMap = useMemo(() => {
    const raw = ((signRes?.docpeg || {}) as Record<string, unknown>).sign_page_map as Record<string, unknown> | undefined
    const toPage = (value: unknown, fallback: number) => {
      const page = Number(value)
      return Number.isFinite(page) && page > 0 ? Math.floor(page) : fallback
    }
    return {
      contractor: toPage(raw?.contractor, 1),
      supervisor: toPage(raw?.supervisor, 2),
      owner: toPage(raw?.owner, 3),
    }
  }, [signRes])

  const docpegSignPos = useMemo(() => {
    const raw = ((signRes?.docpeg || {}) as Record<string, unknown>).sign_position_map as Record<string, unknown> | undefined
    const clamp = (value: number) => Math.min(1, Math.max(0, value))
    const toPos = (value: unknown): SignMarker => {
      if (!value || typeof value !== 'object') return null
      const rec = value as Record<string, unknown>
      const page = Number(rec.page ?? rec.p)
      const x = Number(rec.x ?? rec.left)
      const y = Number(rec.y ?? rec.top)
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null
      return {
        page: Number.isFinite(page) && page > 0 ? Math.floor(page) : undefined,
        x: clamp(x > 1 ? x / 100 : x),
        y: clamp(y > 1 ? y / 100 : y),
      }
    }
    return {
      contractor: toPos(raw?.contractor),
      supervisor: toPos(raw?.supervisor),
      owner: toPos(raw?.owner),
    }
  }, [signRes])

  const evidenceGraphNodes = useMemo(() => {
    const latestTimeline = evidenceTimeline.length ? evidenceTimeline[evidenceTimeline.length - 1] : null
    const latestDoc = filteredDocs.length ? filteredDocs[filteredDocs.length - 1] : null
    return [
      { id: 'graph-ledger', label: '0# Ledger Genesis', subtitle: String(active?.uri || '-'), tone: 'neutral' as const },
      { id: 'graph-qc', label: 'QCSpec proof', subtitle: String((latestTimeline || {}).proof_id || inputProofId || '-'), tone: gateStats.qcCompliant ? ('ok' as const) : ('warn' as const) },
      { id: 'graph-lab', label: 'LabPeg proof', subtitle: gateStats.labLatestPass || 'pending', tone: gateStats.labQualified ? ('ok' as const) : ('warn' as const) },
      { id: 'graph-doc', label: 'DocPeg / PDF', subtitle: String((latestDoc || {}).file_name || verifyUri || '-'), tone: verifyUri || latestDoc ? ('ok' as const) : ('neutral' as const) },
      { id: 'graph-hash', label: 'Final total_proof_hash', subtitle: String(totalHash || '-'), tone: totalHash ? ('ok' as const) : ('neutral' as const) },
    ]
  }, [active?.uri, evidenceTimeline, filteredDocs, gateStats.labLatestPass, gateStats.labQualified, gateStats.qcCompliant, inputProofId, totalHash, verifyUri])

  const templateBinding = useMemo(() => {
    const node = (ctx?.node || {}) as Record<string, unknown>
    return ((node.docpeg_template || {}) as Record<string, unknown>)
  }, [ctx])

  const templateDisplay = useMemo(() => {
    const code = String(templateBinding.template_code || '').trim()
    const name = String(templateBinding.template_name || '').trim()
    const spuLabel = String(((ctx?.spu || {}) as Record<string, unknown>).spu_template_label || '').trim()
    const cleanCode = sanitizeGenericLabel(code, '')
    const cleanName = sanitizeGenericLabel(name, '')
    const cleanSpu = sanitizeGenericLabel(spuLabel, '')
    if (cleanCode) return cleanName ? `${cleanCode} · ${cleanName}` : cleanCode
    if (cleanName) return cleanName
    if (cleanSpu) return cleanSpu
    return 'No template bound'
  }, [ctx, templateBinding.template_code, templateBinding.template_name])

  const templatePath = String(templateBinding.template_path || '')
  const templateFallback = String(templateBinding.fallback_template || '')
  const templateSourceText = String(
    ((signRes?.docpeg || {}) as Record<string, unknown>).selected_template_path ||
    templatePath ||
    templateFallback ||
    '-',
  )

  const draftReady = signStep >= 1
  const draftPdfB64 = useMemo(() => {
    if (!draftReady) return ''
    const nodeName = String(active?.name || '')
    const nodeCode = String(active?.code || '')
    const lines = [
      'QCSpec DocPeg Draft',
      `Node: ${nodeCode}${nodeName ? ` ${nodeName}` : ''}`,
      `Executor DID: ${executorDid}`,
      `Supervisor DID: ${supervisorDid || '-'}`,
      `Owner DID: ${ownerDid || '-'}`,
      `Stamped at: ${draftStamp || new Date().toISOString()}`,
      `Template: ${templatePath || templateFallback || '-'}`,
    ]
    return buildDraftPdfBase64(lines)
  }, [active?.code, active?.name, buildDraftPdfBase64, draftReady, draftStamp, executorDid, ownerDid, supervisorDid, templateFallback, templatePath])

  const previewPdfB64 = pdfB64 || draftPdfB64
  const previewIsDraft = Boolean(draftPdfB64 && !pdfB64)

  const pdfPage = useMemo(() => {
    if (!signFocus) return docpegPageMap.contractor
    return docpegPageMap[signFocus] || docpegPageMap.contractor
  }, [docpegPageMap, signFocus])

  const activeSignMarker = useMemo(() => {
    if (!signFocus) return null
    const pos = docpegSignPos[signFocus]
    if (!pos) return null
    if (pos.page && pos.page !== pdfPage) return null
    return pos
  }, [docpegSignPos, pdfPage, signFocus])

  return {
    evidenceGraphNodes,
    templateDisplay,
    templatePath,
    templateSourceText,
    draftReady,
    draftPdfB64,
    previewPdfB64,
    previewIsDraft,
    pdfPage,
    activeSignMarker,
  }
}
