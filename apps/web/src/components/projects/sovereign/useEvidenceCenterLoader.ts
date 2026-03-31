import { useCallback, useEffect, useRef, type Dispatch, type SetStateAction } from 'react'

import type { EvidenceCenterPayload, EvidenceScope } from './types'

type EvidenceLogEntry = Array<Record<string, unknown>>

type SetEvidenceLogEntry = Dispatch<SetStateAction<EvidenceLogEntry>>

type UseEvidenceCenterLoaderArgs = {
  apiProjectUri: string
  activeCode: string
  activeIsLeaf: boolean
  activeUri: string
  evidenceScope: EvidenceScope
  evidenceSmuId: string
  finalProofId: string
  inputProofId: string
  evidenceCenterEvidence: (payload: {
    project_uri?: string
    subitem_code?: string
    boq_item_uri?: string
    smu_id?: string
  }) => Promise<unknown>
  publicVerifyDetail: (proofId: string, scope?: string) => Promise<unknown>
  showToast: (message: string) => void
  setEvidenceCenter: Dispatch<SetStateAction<EvidenceCenterPayload | null>>
  setEvidenceCenterLoading: Dispatch<SetStateAction<boolean>>
  setEvidenceCenterError: Dispatch<SetStateAction<string>>
  scanEntryLog: EvidenceLogEntry
  meshpegLog: EvidenceLogEntry
  formulaLog: EvidenceLogEntry
  gatewayLog: EvidenceLogEntry
  setScanEntryLog: SetEvidenceLogEntry
  setMeshpegLog: SetEvidenceLogEntry
  setFormulaLog: SetEvidenceLogEntry
  setGatewayLog: SetEvidenceLogEntry
}

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function buildEntryKey(item: Record<string, unknown>, includeTokenHash = false) {
  const proofId = String(item.proof_id || '').trim()
  if (proofId) return proofId
  const parts = [
    String(item.offline_packet_id || ''),
    includeTokenHash ? String(item.token_hash || '') : '',
    String(item.created_at || ''),
    String(item.status || ''),
  ]
  return parts.join('|')
}

function mergeEntries(
  remote: EvidenceLogEntry,
  local: EvidenceLogEntry,
  options: { includeTokenHash?: boolean } = {},
) {
  const map = new Map<string, Record<string, unknown>>()
  const add = (item: Record<string, unknown>) => {
    const key = buildEntryKey(item, options.includeTokenHash)
    if (!map.has(key)) {
      map.set(key, item)
      return
    }
    const existing = map.get(key) || {}
    map.set(key, { ...existing, ...item })
  }
  remote.forEach(add)
  local.forEach(add)
  return Array.from(map.values())
}

function reconcileScanEntryLog(prev: EvidenceLogEntry, merged: EvidenceLogEntry) {
  return prev.map((item) => {
    if (item.chain_status === 'onchain') return item
    const match = merged.find((entry) => {
      const hash = String(entry.token_hash || '')
      const created = String(entry.created_at || '')
      if (hash && hash === String(item.token_hash || '')) return true
      if (created && created === String(item.created_at || '')) return true
      return false
    })
    if (!match) return item
    return {
      ...item,
      chain_status: String(match.chain_status || 'onchain'),
      proof_id: String(match.proof_id || item.proof_id || ''),
      proof_hash: String(match.proof_hash || item.proof_hash || ''),
    }
  })
}

function reconcileQueuedLog(prev: EvidenceLogEntry, merged: EvidenceLogEntry) {
  return prev.map((item) => {
    if (item.chain_status === 'onchain') return item
    const match = merged.find((entry) => {
      const proofId = String(entry.proof_id || '')
      if (proofId && proofId === String(item.proof_id || '')) return true
      return String(entry.created_at || '') === String(item.created_at || '')
    })
    if (!match) return item
    return {
      ...item,
      chain_status: String(match.chain_status || 'onchain'),
      proof_id: String(match.proof_id || item.proof_id || ''),
      proof_hash: String(match.proof_hash || item.proof_hash || ''),
    }
  })
}

export function useEvidenceCenterLoader({
  apiProjectUri,
  activeCode,
  activeIsLeaf,
  activeUri,
  evidenceScope,
  evidenceSmuId,
  finalProofId,
  inputProofId,
  evidenceCenterEvidence,
  publicVerifyDetail,
  showToast,
  setEvidenceCenter,
  setEvidenceCenterLoading,
  setEvidenceCenterError,
  scanEntryLog,
  meshpegLog,
  formulaLog,
  gatewayLog,
  setScanEntryLog,
  setMeshpegLog,
  setFormulaLog,
  setGatewayLog,
}: UseEvidenceCenterLoaderArgs) {
  const scanEntryLogRef = useRef(scanEntryLog)
  const meshpegLogRef = useRef(meshpegLog)
  const formulaLogRef = useRef(formulaLog)
  const gatewayLogRef = useRef(gatewayLog)

  useEffect(() => {
    scanEntryLogRef.current = scanEntryLog
  }, [scanEntryLog])

  useEffect(() => {
    meshpegLogRef.current = meshpegLog
  }, [meshpegLog])

  useEffect(() => {
    formulaLogRef.current = formulaLog
  }, [formulaLog])

  useEffect(() => {
    gatewayLogRef.current = gatewayLog
  }, [gatewayLog])

  const loadEvidenceCenter = useCallback(async () => {
    if (!apiProjectUri || !activeCode) {
      showToast('请选择细目后再加载证据中心')
      return
    }
    setEvidenceCenterLoading(true)
    setEvidenceCenterError('')
    try {
      const activeSmu = evidenceSmuId || String(activeCode || '').split('-')[0]
      const useSmuScope = evidenceScope === 'smu' && !!activeSmu
      const evidencePayload = useSmuScope
        ? await evidenceCenterEvidence({
            project_uri: apiProjectUri,
            smu_id: activeSmu,
          }) as Record<string, unknown> | null
        : await evidenceCenterEvidence({
            project_uri: apiProjectUri,
            subitem_code: activeCode,
          }) as Record<string, unknown> | null
      const timeline = Array.isArray((evidencePayload || {}).timeline)
        ? ((evidencePayload || {}).timeline as EvidenceLogEntry)
        : []
      const ledger = (asDict((evidencePayload || {}).ledger) || asDict((evidencePayload || {}).ledger_snapshot)) as Record<string, unknown>
      const documents = Array.isArray((evidencePayload || {}).documents)
        ? ((evidencePayload || {}).documents as EvidenceLogEntry)
        : []
      const riskAudit = (asDict((evidencePayload || {}).risk_audit) || asDict((evidencePayload || {}).riskAudit)) as Record<string, unknown>
      const totalProofHash = String((evidencePayload || {}).total_proof_hash || (evidencePayload || {}).totalProofHash || '')
      const fallbackProofId = String((timeline[timeline.length - 1] || {}).proof_id || (evidencePayload || {}).proof_id || (evidencePayload || {}).latest_proof_id || '')
      const proofId = String(finalProofId || inputProofId || fallbackProofId || '').trim()
      let evidence = Array.isArray((evidencePayload || {}).evidence)
        ? ((evidencePayload || {}).evidence as EvidenceLogEntry)
        : []
      let evidenceSource = String((evidencePayload || {}).evidence_source || '').trim()
      const consensusDispute = asDict((evidencePayload || {}).consensus_dispute)
      const assetOrigin = (asDict((evidencePayload || {}).asset_origin) || asDict((evidencePayload || {}).assetOrigin)) as Record<string, unknown>
      const assetOriginStatement = String((evidencePayload || {}).asset_origin_statement || (evidencePayload || {}).assetOriginStatement || assetOrigin.statement || '').trim()
      const didReputation = (asDict((evidencePayload || {}).did_reputation) || asDict((evidencePayload || {}).didReputation)) as Record<string, unknown>
      const sealingTrip = (asDict((evidencePayload || {}).sealing_trip) || asDict((evidencePayload || {}).sealingTrip)) as Record<string, unknown>
      const scanEntriesPayload = Array.isArray((evidencePayload || {}).scan_entries)
        ? ((evidencePayload || {}).scan_entries as EvidenceLogEntry)
        : []
      const meshpegEntriesPayload = Array.isArray((evidencePayload || {}).meshpeg_entries)
        ? ((evidencePayload || {}).meshpeg_entries as EvidenceLogEntry)
        : []
      const formulaEntriesPayload = Array.isArray((evidencePayload || {}).formula_entries)
        ? ((evidencePayload || {}).formula_entries as EvidenceLogEntry)
        : []
      const gatewayEntriesPayload = Array.isArray((evidencePayload || {}).gateway_entries)
        ? ((evidencePayload || {}).gateway_entries as EvidenceLogEntry)
        : []
      const mergedScanEntries = mergeEntries(scanEntriesPayload, scanEntryLogRef.current, { includeTokenHash: true })
      const mergedMeshpegEntries = mergeEntries(meshpegEntriesPayload, meshpegLogRef.current)
      const mergedFormulaEntries = mergeEntries(formulaEntriesPayload, formulaLogRef.current)
      const mergedGatewayEntries = mergeEntries(gatewayEntriesPayload, gatewayLogRef.current)

      if (!evidence.length && proofId) {
        const verifyDetail = await publicVerifyDetail(proofId, 'item') as Record<string, unknown> | null
        evidence = Array.isArray((verifyDetail || {}).evidence)
          ? ((verifyDetail || {}).evidence as EvidenceLogEntry)
          : []
        evidenceSource = evidenceSource || 'verify_detail'
      }

      const payloadSmuId = String((evidencePayload || {}).smu_id || activeSmu || '').trim()
      const completeness = asDict((evidencePayload || {}).evidence_completeness)
      const settlementRiskScoreRaw = Number((evidencePayload || {}).settlement_risk_score)
      const settlementRiskScore = Number.isFinite(settlementRiskScoreRaw)
        ? settlementRiskScoreRaw
        : Number(riskAudit.risk_score || 0)

      setEvidenceCenter({
        ledger,
        timeline,
        documents,
        evidence,
        proofId,
        riskAudit,
        totalProofHash,
        evidenceSource,
        consensusDispute,
        scanEntries: mergedScanEntries,
        meshpegEntries: mergedMeshpegEntries,
        formulaEntries: mergedFormulaEntries,
        gatewayEntries: mergedGatewayEntries,
        scope: String((evidencePayload || {}).scope || (useSmuScope ? 'smu' : 'item')),
        smuId: payloadSmuId,
        evidenceCompleteness: completeness,
        settlementRiskScore,
        assetOrigin,
        assetOriginStatement,
        didReputation,
        sealingTrip,
      })

      setScanEntryLog((prev) => reconcileScanEntryLog(prev, mergedScanEntries))
      setMeshpegLog((prev) => reconcileQueuedLog(prev, mergedMeshpegEntries))
      setFormulaLog((prev) => reconcileQueuedLog(prev, mergedFormulaEntries))
      setGatewayLog((prev) => reconcileQueuedLog(prev, mergedGatewayEntries))
    } catch {
      setEvidenceCenterError('证据中心加载失败')
    } finally {
      setEvidenceCenterLoading(false)
    }
  }, [
    activeCode,
    apiProjectUri,
    evidenceCenterEvidence,
    evidenceScope,
    evidenceSmuId,
    finalProofId,
    inputProofId,
    publicVerifyDetail,
    setEvidenceCenter,
    setEvidenceCenterError,
    setEvidenceCenterLoading,
    setFormulaLog,
    setGatewayLog,
    setMeshpegLog,
    setScanEntryLog,
    showToast,
  ])

  useEffect(() => {
    if (!apiProjectUri || !activeIsLeaf) return
    void loadEvidenceCenter()
  }, [activeIsLeaf, activeUri, apiProjectUri, loadEvidenceCenter])

  return { loadEvidenceCenter }
}
