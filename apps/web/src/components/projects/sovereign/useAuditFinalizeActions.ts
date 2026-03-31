import { useCallback, useEffect, useMemo, useState } from 'react'

import { downloadBlob } from './fileUtils'

type DisputeResult = 'PASS' | 'REJECT'

type UseAuditFinalizeActionsArgs = {
  apiProjectUri: string
  projectName: string
  ownerDid: string
  lat: string
  lng: string
  disputeProofId: string
  disputeResolutionNote: string
  disputeResult: DisputeResult
  docFinalPassphrase: string
  docFinalIncludeUnsettled: boolean
  activeUri: string
  finalProofReady: boolean
  consensusConflict: Record<string, unknown> | boolean
  disputeOpen: boolean
  docpegRiskScore: number
  totalHash: string
  evidenceCount: number
  documentCount: number
  finalProofId: string
  inputProofId: string
  triproleExecute: (payload: Record<string, unknown>) => Promise<unknown>
  exportDocFinal: (payload: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
  }) => Promise<unknown>
  finalizeDocFinal: (payload: {
    project_uri: string
    project_name?: string
    passphrase?: string
    verify_base_url?: string
    include_unsettled?: boolean
    run_anchor_rounds?: number
  }) => Promise<unknown>
  loadEvidenceCenter: () => void | Promise<void>
  showToast: (message: string) => void
}

export function useAuditFinalizeActions({
  apiProjectUri,
  projectName,
  ownerDid,
  lat,
  lng,
  disputeProofId,
  disputeResolutionNote,
  disputeResult,
  docFinalPassphrase,
  docFinalIncludeUnsettled,
  activeUri,
  finalProofReady,
  consensusConflict,
  disputeOpen,
  docpegRiskScore,
  totalHash,
  evidenceCount,
  documentCount,
  finalProofId,
  inputProofId,
  triproleExecute,
  exportDocFinal,
  finalizeDocFinal,
  loadEvidenceCenter,
  showToast,
}: UseAuditFinalizeActionsArgs) {
  const [disputeResolving, setDisputeResolving] = useState(false)
  const [disputeResolveRes, setDisputeResolveRes] = useState<Record<string, unknown> | null>(null)
  const [docFinalExporting, setDocFinalExporting] = useState(false)
  const [docFinalFinalizing, setDocFinalFinalizing] = useState(false)
  const [docFinalRes, setDocFinalRes] = useState<Record<string, unknown> | null>(null)
  const [archiveLocked, setArchiveLocked] = useState(false)
  const [assetAppraising, setAssetAppraising] = useState(false)
  const [assetAppraisal, setAssetAppraisal] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    setArchiveLocked(false)
    setDocFinalRes(null)
  }, [apiProjectUri])

  const docFinalVerifyBaseUrl = useMemo(() => {
    if (typeof window === 'undefined') return ''
    return `${window.location.origin}/verify`
  }, [])

  const resolveDispute = useCallback(async () => {
    if (!disputeProofId) {
      showToast('请输入争议 Proof ID')
      return
    }
    if (disputeResolving) return
    setDisputeResolving(true)
    setDisputeResolveRes(null)
    try {
      const now = new Date().toISOString()
      const payload = await triproleExecute({
        action: 'dispute.resolve',
        input_proof_id: disputeProofId,
        executor_uri: `${apiProjectUri.replace(/\/$/, '')}/role/owner/system/`,
        executor_did: ownerDid,
        executor_role: 'OWNER',
        result: disputeResult === 'REJECT' ? 'FAIL' : 'PASS',
        payload: {
          note: disputeResolutionNote,
          resolved_by: ownerDid,
        },
        geo_location: { lat: Number(lat), lng: Number(lng) },
        server_timestamp_proof: { ntp_server: 'pool.ntp.org', captured_at: now, proof_hash: `ntp-${now}` },
      }) as Record<string, unknown> | null
      if (!payload?.ok) {
        showToast('争议仲裁失败')
        return
      }
      setDisputeResolveRes(payload)
      showToast('争议已仲裁并解除')
      void loadEvidenceCenter()
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求异常'
      showToast(`争议仲裁失败：${msg}`)
    } finally {
      setDisputeResolving(false)
    }
  }, [
    apiProjectUri,
    disputeProofId,
    disputeResolutionNote,
    disputeResolving,
    disputeResult,
    lat,
    lng,
    loadEvidenceCenter,
    ownerDid,
    showToast,
    triproleExecute,
  ])

  const exportProjectDocFinal = useCallback(async () => {
    if (!apiProjectUri) {
      showToast('项目 URI 缺失')
      return
    }
    if (docFinalExporting) return
    setDocFinalExporting(true)
    try {
      const res = await exportDocFinal({
        project_uri: apiProjectUri,
        project_name: projectName,
        passphrase: docFinalPassphrase || undefined,
        verify_base_url: docFinalVerifyBaseUrl || undefined,
        include_unsettled: docFinalIncludeUnsettled,
      }) as {
        blob: Blob
        filename?: string
        rootHash?: string
        proofId?: string
        gitpegAnchor?: string
      } | null
      if (!res) {
        showToast('DocFinal 导出失败')
        return
      }
      downloadBlob(res.filename || `docfinal-${Date.now()}.pdf`, res.blob)
      setDocFinalRes({
        mode: 'export',
        filename: res.filename,
        rootHash: res.rootHash,
        proofId: res.proofId,
        gitpegAnchor: res.gitpegAnchor,
        exportedAt: new Date().toISOString(),
      })
      showToast(`DocFinal 已导出：${res.proofId || res.rootHash || 'OK'}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求异常'
      showToast(`DocFinal 导出失败：${msg}`)
    } finally {
      setDocFinalExporting(false)
    }
  }, [
    apiProjectUri,
    docFinalExporting,
    docFinalIncludeUnsettled,
    docFinalPassphrase,
    docFinalVerifyBaseUrl,
    exportDocFinal,
    projectName,
    showToast,
  ])

  const finalizeProjectDocFinal = useCallback(async () => {
    if (!apiProjectUri) {
      showToast('项目 URI 缺失')
      return
    }
    if (docFinalFinalizing) return
    setDocFinalFinalizing(true)
    try {
      const res = await finalizeDocFinal({
        project_uri: apiProjectUri,
        project_name: projectName,
        passphrase: docFinalPassphrase || undefined,
        verify_base_url: docFinalVerifyBaseUrl || undefined,
        include_unsettled: docFinalIncludeUnsettled,
        run_anchor_rounds: 1,
      }) as {
        blob: Blob
        filename?: string
        rootHash?: string
        proofId?: string
        gitpegAnchor?: string
        finalGitpegAnchor?: string
        anchorRuns?: unknown
      } | null
      if (!res) {
        showToast('Archive_Trip 封存失败')
        return
      }
      downloadBlob(res.filename || `docfinal-archive-${Date.now()}.pdf`, res.blob)
      setDocFinalRes({
        mode: 'finalize',
        filename: res.filename,
        rootHash: res.rootHash,
        proofId: res.proofId,
        gitpegAnchor: res.gitpegAnchor,
        finalGitpegAnchor: res.finalGitpegAnchor,
        anchorRuns: res.anchorRuns,
        archivedAt: new Date().toISOString(),
      })
      setArchiveLocked(true)
      showToast(`Archive_Trip 已封存：${res.proofId || res.rootHash || 'OK'}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求异常'
      showToast(`Archive_Trip 封存失败：${msg}`)
    } finally {
      setDocFinalFinalizing(false)
    }
  }, [
    apiProjectUri,
    docFinalFinalizing,
    docFinalIncludeUnsettled,
    docFinalPassphrase,
    docFinalVerifyBaseUrl,
    finalizeDocFinal,
    projectName,
    showToast,
  ])

  const buildAssetAppraisal = useCallback(() => {
    if (!activeUri) {
      showToast('请先选择资产细目')
      return
    }
    setAssetAppraising(true)
    try {
      let score = 100
      if (!finalProofReady) score -= 20
      if (disputeOpen) score -= 40
      if (consensusConflict) score -= 15
      if (docpegRiskScore > 0) score -= Math.min(35, docpegRiskScore)
      if (!totalHash) score -= 10
      if (evidenceCount > 3) score += Math.min(6, Math.floor(evidenceCount / 3))
      score = Math.max(0, Math.min(100, Math.round(score)))
      const grade =
        score >= 90 ? 'AAA' :
          score >= 80 ? 'AA' :
            score >= 70 ? 'A' :
              score >= 60 ? 'BBB' :
                score >= 50 ? 'BB' : 'B'
      const payload = {
        ok: true,
        asset_uri: activeUri,
        project_uri: apiProjectUri,
        proof_id: finalProofId || inputProofId || '',
        total_proof_hash: totalHash,
        score,
        grade,
        evidence_count: evidenceCount,
        document_count: documentCount,
        dispute_open: disputeOpen,
        consensus_conflict: consensusConflict,
        risk_score: docpegRiskScore,
        generated_at: new Date().toISOString(),
        engine: 'CoordOS/AssetValue/0.1',
      }
      setAssetAppraisal(payload)
      showToast(`资产评估完成：${score} (${grade})`)
    } finally {
      setAssetAppraising(false)
    }
  }, [
    activeUri,
    apiProjectUri,
    consensusConflict,
    disputeOpen,
    docpegRiskScore,
    documentCount,
    evidenceCount,
    finalProofId,
    finalProofReady,
    inputProofId,
    showToast,
    totalHash,
  ])

  return {
    disputeResolving,
    disputeResolveRes,
    resolveDispute,
    docFinalExporting,
    docFinalFinalizing,
    docFinalRes,
    archiveLocked,
    exportProjectDocFinal,
    finalizeProjectDocFinal,
    assetAppraising,
    assetAppraisal,
    buildAssetAppraisal,
  }
}
