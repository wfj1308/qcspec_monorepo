import { useEffect, useState } from 'react'
import type { Project } from '@qcspec/types'

type ProofRow = {
  proof_id: string
  summary?: string
  object_type?: string
  action?: string
  created_at?: string
}

type ProofStats = {
  total: number
  by_type: Record<string, number>
  by_action: Record<string, number>
}

type ProofNodeRow = {
  uri?: string
  node_type?: string
  status?: string
}

type ProjectLike = Pick<Project, 'id' | 'name' | 'v_uri'> | null

interface UseProofDashboardControllerArgs {
  activeTab: string
  proj: Pick<Project, 'id' | 'name' | 'v_uri'>
  projectDetailOpen: boolean
  detailProject: ProjectLike
  showToast: (message: string) => void
  listProofs: (projectId: string) => Promise<unknown>
  verifyProof: (proofId: string) => Promise<unknown>
  proofStatsApi: (projectId: string) => Promise<unknown>
  proofNodeTreeApi: (projectUri: string) => Promise<unknown>
  boqRealtimeStatusApi: (projectUri: string) => Promise<unknown>
  boqItemSovereignHistoryApi: (payload: {
    project_uri: string
    subitem_code: string
    max_rows: number
  }) => Promise<unknown>
  boqReconciliationApi: (payload: {
    project_uri: string
    limit_items: number
  }) => Promise<unknown>
  docFinalContextApi: (boqItemUri: string) => Promise<unknown>
}

export function useProofDashboardController({
  activeTab,
  proj,
  projectDetailOpen,
  detailProject,
  showToast,
  listProofs,
  verifyProof,
  proofStatsApi,
  proofNodeTreeApi,
  boqRealtimeStatusApi,
  boqItemSovereignHistoryApi,
  boqReconciliationApi,
  docFinalContextApi,
}: UseProofDashboardControllerArgs) {
  const [proofRows, setProofRows] = useState<ProofRow[]>([])
  const [proofStats, setProofStats] = useState<ProofStats>({
    total: 0,
    by_type: {},
    by_action: {},
  })
  const [proofNodeRows, setProofNodeRows] = useState<ProofNodeRow[]>([])
  const [proofLoading, setProofLoading] = useState(false)
  const [proofVerifying, setProofVerifying] = useState<string | null>(null)
  const [boqRealtimeByProjectId, setBoqRealtimeByProjectId] = useState<Record<string, any>>({})
  const [boqRealtimeLoadingProjectId, setBoqRealtimeLoadingProjectId] = useState<string | null>(null)
  const [boqAuditByProjectId, setBoqAuditByProjectId] = useState<Record<string, any>>({})
  const [boqAuditLoadingProjectId, setBoqAuditLoadingProjectId] = useState<string | null>(null)
  const [boqProofPreview, setBoqProofPreview] = useState<any | null>(null)
  const [boqProofLoadingUri, setBoqProofLoadingUri] = useState<string | null>(null)
  const [boqSovereignPreview, setBoqSovereignPreview] = useState<any | null>(null)
  const [boqSovereignLoadingCode, setBoqSovereignLoadingCode] = useState<string | null>(null)

  useEffect(() => {
    if (!projectDetailOpen || !detailProject?.id || !detailProject.v_uri) return
    if (boqRealtimeByProjectId[detailProject.id]) return

    let cancelled = false
    const load = async () => {
      setBoqRealtimeLoadingProjectId(detailProject.id)
      try {
        const payload = (await boqRealtimeStatusApi(detailProject.v_uri)) as { ok?: boolean } | null
        if (cancelled) return
        if (payload?.ok) {
          setBoqRealtimeByProjectId((prev) => ({ ...prev, [detailProject.id as string]: payload }))
        }
      } catch {
        if (!cancelled) showToast('BOQ 实时进度加载失败')
      } finally {
        if (!cancelled) {
          setBoqRealtimeLoadingProjectId((current) => (current === detailProject.id ? null : current))
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [projectDetailOpen, detailProject?.id, detailProject?.v_uri, boqRealtimeByProjectId, boqRealtimeStatusApi, showToast])

  useEffect(() => {
    if (!projectDetailOpen || !detailProject?.id || !detailProject.v_uri) return
    if (boqAuditByProjectId[detailProject.id]) return

    let cancelled = false
    const load = async () => {
      setBoqAuditLoadingProjectId(detailProject.id)
      try {
        const payload = (await boqReconciliationApi({
          project_uri: detailProject.v_uri,
          limit_items: 1000,
        })) as { ok?: boolean } | null
        if (cancelled) return
        if (payload?.ok) {
          setBoqAuditByProjectId((prev) => ({ ...prev, [detailProject.id as string]: payload }))
        }
      } catch {
        if (!cancelled) showToast('BOQ 主权审计对账加载失败')
      } finally {
        if (!cancelled) {
          setBoqAuditLoadingProjectId((current) => (current === detailProject.id ? null : current))
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [projectDetailOpen, detailProject?.id, detailProject?.v_uri, boqAuditByProjectId, boqReconciliationApi, showToast])

  useEffect(() => {
    if (!projectDetailOpen) {
      setBoqProofPreview(null)
      setBoqProofLoadingUri(null)
      setBoqSovereignPreview(null)
      setBoqSovereignLoadingCode(null)
    }
  }, [projectDetailOpen])

  useEffect(() => {
    if (activeTab !== 'proof' || !proj.id) return
    let cancelled = false
    setProofLoading(true)
    Promise.all([
      listProofs(proj.id),
      proofStatsApi(proj.id),
      proj.v_uri ? proofNodeTreeApi(proj.v_uri) : Promise.resolve(null),
    ])
      .then(([listRes, statsRes, treeRes]) => {
        if (cancelled) return
        const listPayload = listRes as { data?: ProofRow[] } | null
        const statsPayload = statsRes as {
          total?: number
          by_type?: Record<string, number>
          by_action?: Record<string, number>
        } | null
        const treePayload = treeRes as { data?: ProofNodeRow[] } | null

        setProofRows(listPayload?.data || [])
        setProofStats({
          total: Number(statsPayload?.total || 0),
          by_type: statsPayload?.by_type || {},
          by_action: statsPayload?.by_action || {},
        })
        setProofNodeRows(treePayload?.data || [])
      })
      .finally(() => {
        if (!cancelled) setProofLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [activeTab, proj.id, proj.v_uri, listProofs, proofStatsApi, proofNodeTreeApi])

  const handleOpenBoqProofChain = async (boqItemUri: string) => {
    if (!boqItemUri) return
    setBoqProofLoadingUri(boqItemUri)
    try {
      const payload = (await docFinalContextApi(boqItemUri)) as { ok?: boolean } | null
      if (payload?.ok) {
        setBoqProofPreview(payload)
      } else {
        showToast('未获取到该细目的 Proof 链上下文')
      }
    } catch {
      showToast('未获取到该细目的 Proof 链上下文')
    } finally {
      setBoqProofLoadingUri(null)
    }
  }

  const handleOpenBoqSovereignHistory = async (subitemCode: string) => {
    if (!detailProject?.v_uri || !subitemCode) return
    setBoqSovereignLoadingCode(subitemCode)
    try {
      const payload = (await boqItemSovereignHistoryApi({
        project_uri: detailProject.v_uri,
        subitem_code: subitemCode,
        max_rows: 50000,
      })) as { ok?: boolean } | null
      if (payload?.ok) {
        setBoqSovereignPreview(payload)
      } else {
        showToast('未获取到该细目的主权历史')
      }
    } catch {
      showToast('未获取到该细目的主权历史')
    } finally {
      setBoqSovereignLoadingCode(null)
    }
  }

  const handleVerifyProof = async (proofId: string) => {
    setProofVerifying(proofId)
    const res = (await verifyProof(proofId)) as { valid?: boolean; chain_length?: number } | null
    if (res?.valid) {
      showToast(`Proof 校验通过（链长 ${res.chain_length ?? 0}）`)
    } else {
      showToast('Proof 校验失败或不存在')
    }
    setProofVerifying(null)
  }

  return {
    projectUri: proj.v_uri,
    proofRows,
    proofStats,
    proofNodeRows,
    proofLoading,
    proofVerifying,
    boqRealtime: detailProject?.id ? boqRealtimeByProjectId[detailProject.id] || null : null,
    boqRealtimeLoading: boqRealtimeLoadingProjectId === detailProject?.id,
    boqAudit: detailProject?.id ? boqAuditByProjectId[detailProject.id] || null : null,
    boqAuditLoading: boqAuditLoadingProjectId === detailProject?.id,
    boqProofPreview,
    boqProofLoadingUri,
    boqSovereignPreview,
    boqSovereignLoadingCode,
    handleOpenBoqProofChain,
    handleOpenBoqSovereignHistory,
    handleVerifyProof,
  }
}
