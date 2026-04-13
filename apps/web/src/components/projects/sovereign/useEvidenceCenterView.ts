import { useCallback, useEffect, useMemo, useState } from 'react'
import { downloadBlob, downloadJson } from './fileUtils'
import type { EvidenceCenterPayload, EvidenceFilter, EvidenceScope } from './types'

type DownloadEvidenceCenterZip = (payload: {
  project_uri: string
  subitem_code: string
  proof_id: string
}) => Promise<{ blob?: Blob | null; filename?: string } | null | undefined>

type UseEvidenceCenterViewArgs = {
  activeCode: string
  apiProjectUri: string
  smuOptions: string[]
  evidenceCenter: EvidenceCenterPayload | null
  evidenceDocs: Array<Record<string, unknown>>
  evidenceItems: Array<Record<string, unknown>>
  evidenceTimeline: Array<Record<string, unknown>>
  meshpegItems: Array<Record<string, unknown>>
  formulaItems: Array<Record<string, unknown>>
  gatewayItems: Array<Record<string, unknown>>
  ledgerSnapshot: Record<string, unknown>
  docpegRisk: Record<string, unknown>
  didReputation: Record<string, unknown>
  assetOrigin: Record<string, unknown>
  assetOriginStatement: string
  sealingTrip: Record<string, unknown>
  totalHash: string
  showToast: (message: string) => void
  downloadEvidenceCenterZip: DownloadEvidenceCenterZip
}

function matchesEvidenceFocus(item: Record<string, unknown>, focusId: string) {
  return String(item.id || item.hash || item.file_name || '').trim() === focusId
}

function matchesDocumentFocus(item: Record<string, unknown>, focusId: string) {
  return String(item.id || item.file_name || '').trim() === focusId
}

function escapeCsvCell(value: unknown) {
  const text = String(value ?? '')
  if (text.includes('"') || text.includes(',') || text.includes('\n')) {
    return `"${text.replace(/"/g, '""')}"`
  }
  return text
}

export function useEvidenceCenterView({
  activeCode,
  apiProjectUri,
  smuOptions,
  evidenceCenter,
  evidenceDocs,
  evidenceItems,
  evidenceTimeline,
  meshpegItems,
  formulaItems,
  gatewayItems,
  ledgerSnapshot,
  docpegRisk,
  didReputation,
  assetOrigin,
  assetOriginStatement,
  sealingTrip,
  totalHash,
  showToast,
  downloadEvidenceCenterZip,
}: UseEvidenceCenterViewArgs) {
  const [evidenceQuery, setEvidenceQuery] = useState('')
  const [evidenceFilter, setEvidenceFilter] = useState<EvidenceFilter>('all')
  const [evidenceScope, setEvidenceScope] = useState<EvidenceScope>('item')
  const [evidenceSmuId, setEvidenceSmuId] = useState('')
  const [evidencePage, setEvidencePage] = useState(1)
  const [evidenceFocusId, setEvidenceFocusId] = useState('')
  const [evidenceDocFocusId, setEvidenceDocFocusId] = useState('')
  const [evidenceZipDownloading, setEvidenceZipDownloading] = useState(false)

  useEffect(() => {
    if (evidenceSmuId && smuOptions.includes(evidenceSmuId)) return
    const activeSmu = String(activeCode || '').split('-')[0]
    if (activeSmu && smuOptions.includes(activeSmu)) {
      setEvidenceSmuId(activeSmu)
      return
    }
    if (smuOptions.length) setEvidenceSmuId(smuOptions[0])
  }, [activeCode, evidenceSmuId, smuOptions])

  const evidenceQueryText = evidenceQuery.trim().toLowerCase()

  const filteredEvidenceItems = useMemo(() => {
    return evidenceItems.filter((item) => {
      const name = String(item.file_name || item.id || '').toLowerCase()
      const media = String(item.media_type || '').toLowerCase()
      const matched = Boolean(item.hash_matched)
      if (evidenceFilter === 'matched' && !matched) return false
      if (evidenceFilter === 'unmatched' && matched) return false
      if (evidenceFilter === 'image' && !media.startsWith('image')) return false
      if (evidenceQueryText && !name.includes(evidenceQueryText)) return false
      return true
    })
  }, [evidenceFilter, evidenceItems, evidenceQueryText])

  const filteredDocs = useMemo(() => {
    return evidenceDocs.filter((doc) => {
      const name = String(doc.file_name || doc.doc_type || '').toLowerCase()
      if (!evidenceQueryText) return true
      return name.includes(evidenceQueryText)
    })
  }, [evidenceDocs, evidenceQueryText])

  const erpReceiptDoc = useMemo(() => {
    const receipts = evidenceDocs.filter((doc) => String(doc.doc_type || '').toLowerCase() === 'erpnext_receipt')
    if (!receipts.length) return null
    return receipts[receipts.length - 1]
  }, [evidenceDocs])

  const evidencePageSize = 6
  const totalEvidencePages = Math.max(1, Math.ceil(filteredEvidenceItems.length / evidencePageSize))
  const evidencePageSafe = Math.min(Math.max(1, evidencePage), totalEvidencePages)
  const evidenceItemsPaged = useMemo(() => {
    return filteredEvidenceItems.slice(
      (evidencePageSafe - 1) * evidencePageSize,
      evidencePageSafe * evidencePageSize,
    )
  }, [evidencePageSafe, filteredEvidenceItems])

  useEffect(() => {
    setEvidencePage(1)
  }, [evidenceFilter, evidenceQueryText])

  const evidenceCenterFocus = useMemo(() => {
    if (!evidenceFocusId) return null
    return evidenceItems.find((item) => matchesEvidenceFocus(item, evidenceFocusId)) || null
  }, [evidenceFocusId, evidenceItems])

  const evidenceCenterDocFocus = useMemo(() => {
    if (!evidenceDocFocusId) return null
    return evidenceDocs.find((item) => matchesDocumentFocus(item, evidenceDocFocusId)) || null
  }, [evidenceDocFocusId, evidenceDocs])

  const openEvidenceFocus = useCallback((value: string) => {
    setEvidenceFocusId(String(value || '').trim())
  }, [])

  const closeEvidenceFocus = useCallback(() => {
    setEvidenceFocusId('')
  }, [])

  const openDocumentFocus = useCallback((value: string) => {
    setEvidenceDocFocusId(String(value || '').trim())
  }, [])

  const closeDocumentFocus = useCallback(() => {
    setEvidenceDocFocusId('')
  }, [])

  const exportEvidenceCenter = useCallback(() => {
    downloadJson(`evidence-center-${activeCode || 'item'}.json`, {
      exported_at: new Date().toISOString(),
      project_uri: apiProjectUri,
      subitem_code: activeCode || '',
      ledger: ledgerSnapshot,
      timeline: evidenceTimeline,
      documents: evidenceDocs,
      evidence: evidenceItems,
      meshpeg_entries: meshpegItems,
      formula_entries: formulaItems,
      gateway_entries: gatewayItems,
      risk_audit: docpegRisk,
      did_reputation: didReputation,
      asset_origin: assetOrigin,
      asset_origin_statement: assetOriginStatement,
      sealing_trip: sealingTrip,
      total_proof_hash: totalHash || '',
      evidence_source: evidenceCenter?.evidenceSource || '',
      proof_id: evidenceCenter?.proofId || '',
    })
  }, [
    activeCode,
    apiProjectUri,
    assetOrigin,
    assetOriginStatement,
    didReputation,
    docpegRisk,
    evidenceCenter?.evidenceSource,
    evidenceCenter?.proofId,
    evidenceDocs,
    evidenceItems,
    evidenceTimeline,
    formulaItems,
    gatewayItems,
    ledgerSnapshot,
    meshpegItems,
    sealingTrip,
    totalHash,
  ])

  const exportEvidenceCenterCsv = useCallback(() => {
    const lines: string[] = []
    lines.push([
      '#',
      `total_proof_hash=${totalHash || ''}`,
      `evidence_source=${evidenceCenter?.evidenceSource || ''}`,
    ].join(','))
    lines.push([
      'type',
      'label',
      'proof_id',
      'hash',
      'time',
      'status',
      'trip_action',
      'lifecycle_stage',
      'matched',
      'url',
      'qty',
      'unit_price',
      'amount',
      'deviation_percent',
      'total_proof_hash',
    ].join(','))
    evidenceItems.forEach((item) => {
      lines.push([
        'evidence',
        escapeCsvCell(item.file_name || item.id || ''),
        escapeCsvCell(item.proof_id || ''),
        escapeCsvCell(item.evidence_hash || ''),
        escapeCsvCell(item.time || ''),
        '',
        '',
        '',
        escapeCsvCell(item.hash_matched ? 'matched' : 'unmatched'),
        escapeCsvCell(item.url || ''),
        '',
        '',
        '',
        '',
        '',
      ].join(','))
    })
    evidenceDocs.forEach((doc) => {
      lines.push([
        'document',
        escapeCsvCell(doc.file_name || doc.doc_type || ''),
        escapeCsvCell(doc.proof_id || ''),
        escapeCsvCell(doc.proof_hash || ''),
        escapeCsvCell(doc.created_at || ''),
        escapeCsvCell(doc.doc_status || ''),
        escapeCsvCell(doc.trip_action || ''),
        escapeCsvCell(doc.lifecycle_stage || ''),
        '',
        escapeCsvCell(doc.storage_url || doc.report_url || ''),
        '',
        '',
        '',
        '',
        '',
      ].join(','))
    })
    meshpegItems.forEach((item) => {
      lines.push([
        'meshpeg',
        escapeCsvCell(item.bim || item.cloud || ''),
        escapeCsvCell(item.proof_id || ''),
        escapeCsvCell(item.proof_hash || ''),
        escapeCsvCell(item.created_at || ''),
        escapeCsvCell(item.status || ''),
        'meshpeg.verify',
        'MESHPEG',
        '',
        '',
        escapeCsvCell(item.mesh_volume || ''),
        '',
        '',
        escapeCsvCell(item.deviation_percent || ''),
        '',
      ].join(','))
    })
    formulaItems.forEach((item) => {
      lines.push([
        'railpact',
        escapeCsvCell(item.railpact_id || ''),
        escapeCsvCell(item.proof_id || ''),
        escapeCsvCell(item.proof_hash || ''),
        escapeCsvCell(item.created_at || ''),
        escapeCsvCell(item.status || ''),
        'formula.price',
        'PRICING',
        '',
        '',
        escapeCsvCell(item.qty || ''),
        escapeCsvCell(item.unit_price || ''),
        escapeCsvCell(item.amount || ''),
        '',
        '',
      ].join(','))
    })
    gatewayItems.forEach((item) => {
      lines.push([
        'gateway_sync',
        escapeCsvCell(item.total_proof_hash || ''),
        escapeCsvCell(item.proof_id || ''),
        escapeCsvCell(item.proof_hash || ''),
        escapeCsvCell(item.created_at || ''),
        'PASS',
        'gateway.sync',
        'GATEWAY_SYNC',
        '',
        '',
        '',
        '',
        '',
        '',
        escapeCsvCell(item.total_proof_hash || ''),
      ].join(','))
    })
    downloadBlob(
      `evidence-center-${activeCode || 'item'}.csv`,
      new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' }),
    )
  }, [
    activeCode,
    evidenceCenter?.evidenceSource,
    evidenceDocs,
    evidenceItems,
    formulaItems,
    gatewayItems,
    meshpegItems,
    totalHash,
  ])

  const downloadEvidenceCenterPackage = useCallback(async () => {
    if (!apiProjectUri || !activeCode) {
      showToast('请选择细目后再下载证据包')
      return
    }
    if (evidenceZipDownloading) return
    setEvidenceZipDownloading(true)
    try {
      const res = await downloadEvidenceCenterZip({
        project_uri: apiProjectUri,
        subitem_code: activeCode,
        proof_id: evidenceCenter?.proofId || '',
      })
      if (!res?.blob) {
        showToast('证据包下载失败')
        return
      }
      downloadBlob(res.filename || `evidence-center-${activeCode}.zip`, res.blob)
    } finally {
      setEvidenceZipDownloading(false)
    }
  }, [
    activeCode,
    apiProjectUri,
    downloadEvidenceCenterZip,
    evidenceCenter?.proofId,
    evidenceZipDownloading,
    showToast,
  ])

  return {
    evidenceQuery,
    setEvidenceQuery,
    evidenceFilter,
    setEvidenceFilter,
    evidenceScope,
    setEvidenceScope,
    evidenceSmuId,
    setEvidenceSmuId,
    evidencePage,
    setEvidencePage,
    evidenceCenterFocus,
    evidenceCenterDocFocus,
    openEvidenceFocus,
    closeEvidenceFocus,
    openDocumentFocus,
    closeDocumentFocus,
    evidenceZipDownloading,
    filteredEvidenceItems,
    filteredDocs,
    erpReceiptDoc,
    evidencePageSafe,
    totalEvidencePages,
    evidenceItemsPaged,
    exportEvidenceCenter,
    exportEvidenceCenterCsv,
    downloadEvidenceCenterPackage,
  }
}

