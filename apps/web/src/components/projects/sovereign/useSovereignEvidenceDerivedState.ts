import { useMemo } from 'react'

import type { EvidenceCenterPayload } from './types'

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

type Args = {
  evidenceCenter: EvidenceCenterPayload | null
  signRes: Record<string, unknown> | null
  mockDocRes: Record<string, unknown> | null
  activeStatus: string
}

export function useSovereignEvidenceDerivedState({
  evidenceCenter,
  signRes,
  mockDocRes,
  activeStatus,
}: Args) {
  const evidenceTimeline = (evidenceCenter?.timeline || []) as Array<Record<string, unknown>>
  const evidenceDocs = (evidenceCenter?.documents || []) as Array<Record<string, unknown>>
  const evidenceItems = (evidenceCenter?.evidence || []) as Array<Record<string, unknown>>
  const scanEntryItems = (evidenceCenter?.scanEntries || []) as Array<Record<string, unknown>>
  const meshpegItems = (evidenceCenter?.meshpegEntries || []) as Array<Record<string, unknown>>
  const formulaItems = (evidenceCenter?.formulaEntries || []) as Array<Record<string, unknown>>
  const gatewayItems = (evidenceCenter?.gatewayEntries || []) as Array<Record<string, unknown>>
  const ledgerSnapshot = (evidenceCenter?.ledger || {}) as Record<string, unknown>
  const consensusDispute = asDict(evidenceCenter?.consensusDispute || {})
  const latestEvidenceNode = evidenceTimeline.length ? evidenceTimeline[evidenceTimeline.length - 1] : null
  const utxoConsumed = Boolean((latestEvidenceNode || {}).spent)
  const utxoStatusText = activeStatus === 'Settled' || utxoConsumed ? '已消费' : '未消费'

  const docpegRisk = useMemo(() => {
    const fromEvidence = asDict(evidenceCenter?.riskAudit || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    return asDict(((signRes?.docpeg || {}) as Record<string, unknown>).risk_audit)
  }, [evidenceCenter?.riskAudit, signRes])

  const docpegContext = useMemo(
    () => asDict(((signRes?.docpeg || {}) as Record<string, unknown>).context),
    [signRes],
  )

  const docpegRiskScore = Number(docpegRisk.risk_score || 0)
  const mockRiskAudit = asDict(mockDocRes?.risk_audit || {})
  const effectiveRiskScore = Number.isFinite(Number(mockRiskAudit.risk_score))
    ? Number(mockRiskAudit.risk_score)
    : docpegRiskScore

  const evidenceCompleteness = asDict(evidenceCenter?.evidenceCompleteness || {})
  const evidenceCompletenessScore = Number(evidenceCompleteness.score || 0)
  const settlementRiskScore = Number.isFinite(Number(evidenceCenter?.settlementRiskScore))
    ? Number(evidenceCenter?.settlementRiskScore)
    : docpegRiskScore

  const assetOrigin = useMemo(() => {
    const fromEvidence = asDict(evidenceCenter?.assetOrigin || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    return asDict(docpegContext.asset_origin || {})
  }, [docpegContext.asset_origin, evidenceCenter?.assetOrigin])

  const assetOriginStatement = useMemo(() => {
    const fromEvidence = String(evidenceCenter?.assetOriginStatement || '').trim()
    if (fromEvidence) return fromEvidence
    const fromAsset = String(assetOrigin.statement || '').trim()
    if (fromAsset) return fromAsset
    return String(docpegContext.asset_origin_statement || '').trim()
  }, [assetOrigin.statement, docpegContext.asset_origin_statement, evidenceCenter?.assetOriginStatement])

  const didReputation = useMemo(() => {
    const fromEvidence = asDict(evidenceCenter?.didReputation || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    const fromRisk = asDict(docpegRisk.did_reputation || {})
    if (Object.keys(fromRisk).length) return fromRisk
    return asDict(asDict(docpegContext.risk_audit).did_reputation || {})
  }, [docpegContext.risk_audit, docpegRisk.did_reputation, evidenceCenter?.didReputation])

  const didReputationScore = Number(didReputation.aggregate_score ?? didReputation.score ?? 0)
  const didReputationGrade = String(didReputation.grade || asDict(didReputation.items?.[0]).grade || '-')
  const didSamplingMultiplier = Number(didReputation.sampling_multiplier ?? didReputation.samplingMultiplier ?? 1)
  const didHighRiskList = Array.isArray(didReputation.high_risk_dids)
    ? (didReputation.high_risk_dids as Array<Record<string, unknown>>)
    : []

  const sealingTrip = useMemo(() => {
    const fromEvidence = asDict(evidenceCenter?.sealingTrip || {})
    if (Object.keys(fromEvidence).length) return fromEvidence
    return asDict(docpegContext.sealing_trip || {})
  }, [docpegContext.sealing_trip, evidenceCenter?.sealingTrip])

  const sealingPatternId = String(sealingTrip.pattern_id || '')
  const sealingScanHint = String(sealingTrip.scan_hint || '')
  const sealingRows = Array.isArray(sealingTrip.ascii_pattern)
    ? (sealingTrip.ascii_pattern as string[]).slice(0, 8)
    : []
  const sealingMicrotext = Array.isArray(sealingTrip.margin_microtext)
    ? (sealingTrip.margin_microtext as string[]).slice(0, 6)
    : []

  const disputeOpen = Boolean(consensusDispute.open)
  const disputeProof = String(consensusDispute.open_proof_id || consensusDispute.latest_proof_id || '')
  const disputeProofShort = disputeProof.length > 12 ? `${disputeProof.slice(0, 12)}...` : disputeProof
  const disputeConflict = asDict(consensusDispute.open_conflict || consensusDispute.latest_conflict || {})
  const disputeDeviation = Number(disputeConflict.deviation || 0)
  const disputeDeviationPct = Number(disputeConflict.deviation_percent || disputeConflict.deviationPercent || 0)
  const disputeAllowedAbs = disputeConflict.allowed_deviation ?? disputeConflict.allowedDeviation
  const disputeAllowedPct = disputeConflict.allowed_deviation_percent ?? disputeConflict.allowedDeviationPercent
  const disputeValues = Array.isArray(disputeConflict.values) ? (disputeConflict.values as Array<unknown>) : []

  return {
    evidenceTimeline,
    evidenceDocs,
    evidenceItems,
    scanEntryItems,
    meshpegItems,
    formulaItems,
    gatewayItems,
    ledgerSnapshot,
    consensusDispute,
    latestEvidenceNode,
    utxoStatusText,
    docpegRisk,
    docpegContext,
    docpegRiskScore,
    effectiveRiskScore,
    evidenceCompletenessScore,
    settlementRiskScore,
    assetOrigin,
    assetOriginStatement,
    didReputation,
    didReputationScore,
    didReputationGrade,
    didSamplingMultiplier,
    didHighRiskList,
    sealingTrip,
    sealingPatternId,
    sealingScanHint,
    sealingRows,
    sealingMicrotext,
    disputeOpen,
    disputeProof,
    disputeProofShort,
    disputeConflict,
    disputeDeviation,
    disputeDeviationPct,
    disputeAllowedAbs,
    disputeAllowedPct,
    disputeValues,
  }
}
