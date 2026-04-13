import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type Dict = Record<string, unknown>

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

type BoqRealtimeItem = {
  boq_item_uri?: string
  item_no?: string
  item_name?: string
  unit?: string
  design_quantity?: number
  settled_quantity?: number
  progress_percent?: number
  latest_settlement_proof_id?: string
}

type BoqRealtimeSummary = {
  boq_item_count?: number
  design_total?: number
  settled_total?: number
  progress_percent?: number
}

type BoqRealtime = {
  summary?: BoqRealtimeSummary
  items?: BoqRealtimeItem[]
}

type BoqAuditItem = {
  subitem_code?: string
  boq_item_uri?: string
  item_name?: string
  unit?: string
  baseline_quantity?: number
  variation_quantity?: number
  settled_quantity?: number
  deviation_quantity?: number
  illegal_attempt_count?: number
  status?: string
}

type BoqAuditAttempt = {
  subitem_code?: string
  proof_id?: string
  reason?: string
  action?: string
  created_at?: string
}

type BoqAuditSummary = {
  item_count?: number
  baseline_total?: number
  variation_total?: number
  settled_total?: number
  deviation_total?: number
  illegal_attempt_count?: number
}

type BoqAudit = {
  summary?: BoqAuditSummary
  items?: BoqAuditItem[]
  illegal_attempts?: BoqAuditAttempt[]
}

type BoqProofPreview = {
  boq_item_uri?: string
  chain_count?: number
  context?: {
    chain_root_hash?: string
    timeline_rows?: Array<{
      step?: number
      label?: string
      result?: string
      time?: string
      proof_id?: string
    }>
  }
}

type BoqSovereignPreview = {
  subitem_code?: string
  root_utxo_id?: string
  boq_item_uri?: string
  totals?: {
    proof_count?: number
    document_count?: number
    variation_count?: number
    settlement_count?: number
    fail_count?: number
  }
  timeline?: Array<{
    proof_id?: string
    proof_type?: string
    result?: string
    created_at?: string
    trip_action?: string
    depth?: number
  }>
  documents?: Array<{
    proof_id?: string
    file_name?: string
    doc_type?: string
    storage_url?: string
    source_utxo_id?: string
  }>
}

type UseProofDashboardControllerArgs = {
  activeTab: string
  proj: { id?: string; v_uri?: string } | null
  projectDetailOpen: boolean
  detailProject: unknown
  showToast: (message: string) => void
  listProofs: (projectId: string) => Promise<unknown>
  verifyProof: (proofId: string) => Promise<unknown>
  proofStatsApi: (projectId: string) => Promise<unknown>
  proofNodeTreeApi: (projectUri: string) => Promise<unknown>
  boqRealtimeStatusApi: (projectUri: string) => Promise<unknown>
  boqItemSovereignHistoryApi: (query: {
    project_uri: string
    subitem_code: string
    max_rows?: number
  }) => Promise<unknown>
  boqReconciliationApi: (query: {
    project_uri: string
    subitem_code?: string
    max_rows?: number
    limit_items?: number
  }) => Promise<unknown>
  docFinalContextApi: (boqItemUri: string) => Promise<unknown>
}

function asDict(value: unknown): Dict {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Dict)
    : {}
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

function toNumber(value: unknown, fallback = 0): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function toText(value: unknown): string {
  return String(value || '').trim()
}

function pickPath(value: unknown, path: string[]): unknown {
  let cursor: unknown = value
  for (const key of path) {
    const row = asDict(cursor)
    if (!(key in row)) return undefined
    cursor = row[key]
  }
  return cursor
}

function pickArrayByPaths(value: unknown, candidates: string[][]): unknown[] {
  for (const path of candidates) {
    const hit = pickPath(value, path)
    if (Array.isArray(hit)) return hit
  }
  return []
}

function resolveProjectId(proj: { id?: string } | null, detailProject: unknown): string {
  const fromDetail = toText(asDict(detailProject).id)
  if (fromDetail) return fromDetail
  return toText(proj?.id)
}

function resolveProjectUri(proj: { id?: string; v_uri?: string } | null, detailProject: unknown): string {
  const detail = asDict(detailProject)
  const detailUri = toText(detail.v_uri || detail.uri)
  if (detailUri) return detailUri

  const projUri = toText(proj?.v_uri)
  if (projUri) return projUri

  const projectId = resolveProjectId(proj, detailProject)
  if (!projectId) return ''
  return `v://cn.docpeg/project/${projectId}`
}

function mapProofRows(payload: unknown): ProofRow[] {
  const rows = pickArrayByPaths(payload, [
    ['data'],
    ['items'],
    ['rows'],
    ['proofs'],
    ['result', 'items'],
    ['payload', 'items'],
  ])

  const mapped: Array<ProofRow | null> = rows.map((item) => {
      const row = asDict(item)
      const proofId = toText(row.proof_id || row.proofId || row.id)
      if (!proofId) return null
      return {
        proof_id: proofId,
        summary: toText(row.summary || row.reason || row.message) || undefined,
        object_type: toText(row.object_type || row.objectType || row.type) || undefined,
        action: toText(row.action || row.trip_action || row.proof_type) || undefined,
        created_at: toText(row.created_at || row.createdAt || row.time) || undefined,
      }
    })
  return mapped.filter((item): item is ProofRow => item !== null)
}

function buildProofStatsFromRows(rows: ProofRow[]): ProofStats {
  const byType: Record<string, number> = {}
  const byAction: Record<string, number> = {}
  for (const row of rows) {
    const typeKey = toText(row.object_type) || 'unknown'
    const actionKey = toText(row.action) || 'unknown'
    byType[typeKey] = (byType[typeKey] || 0) + 1
    byAction[actionKey] = (byAction[actionKey] || 0) + 1
  }
  return {
    total: rows.length,
    by_type: byType,
    by_action: byAction,
  }
}

function mapProofStats(payload: unknown, fallbackRows: ProofRow[]): ProofStats {
  const row = asDict(payload)
  const total = toNumber(row.total, Number.NaN)
  const byType = asDict(row.by_type)
  const byAction = asDict(row.by_action)

  if (Number.isFinite(total) || Object.keys(byType).length || Object.keys(byAction).length) {
    return {
      total: Number.isFinite(total) ? total : fallbackRows.length,
      by_type: Object.fromEntries(Object.entries(byType).map(([k, v]) => [k, toNumber(v)])),
      by_action: Object.fromEntries(Object.entries(byAction).map(([k, v]) => [k, toNumber(v)])),
    }
  }

  return buildProofStatsFromRows(fallbackRows)
}

function mapProofNodeRows(payload: unknown): ProofNodeRow[] {
  const rows = pickArrayByPaths(payload, [
    ['data'],
    ['items'],
    ['rows'],
    ['nodes'],
    ['result', 'items'],
    ['payload', 'items'],
  ])

  const mapped: Array<ProofNodeRow | null> = rows.map((item) => {
      const row = asDict(item)
      const uri = toText(row.uri || row.v_uri || row.node_uri)
      if (!uri) return null
      return {
        uri,
        node_type: toText(row.node_type || row.type || row.kind) || undefined,
        status: toText(row.status || row.state) || undefined,
      }
    })
  return mapped.filter((item): item is ProofNodeRow => item !== null)
}

function mapBoqRealtime(payload: unknown): BoqRealtime {
  const row = asDict(payload)
  const items = asArray<Dict>(row.items).map((item) => ({
    boq_item_uri: toText(item.boq_item_uri || item.item_uri) || undefined,
    item_no: toText(item.item_no || item.subitem_code) || undefined,
    item_name: toText(item.item_name || item.name) || undefined,
    unit: toText(item.unit) || undefined,
    design_quantity: toNumber(item.design_quantity),
    settled_quantity: toNumber(item.settled_quantity),
    progress_percent: toNumber(item.progress_percent),
    latest_settlement_proof_id: toText(item.latest_settlement_proof_id) || undefined,
  }))

  const summaryRaw = asDict(row.summary)
  const summary: BoqRealtimeSummary = {
    boq_item_count: toNumber(summaryRaw.boq_item_count, items.length),
    design_total: toNumber(summaryRaw.design_total),
    settled_total: toNumber(summaryRaw.settled_total),
    progress_percent: toNumber(summaryRaw.progress_percent),
  }

  return {
    summary,
    items,
  }
}

function mapBoqAudit(payload: unknown): BoqAudit {
  const row = asDict(payload)
  const items = asArray<Dict>(row.items).map((item) => ({
    subitem_code: toText(item.subitem_code || item.item_no) || undefined,
    boq_item_uri: toText(item.boq_item_uri || item.item_uri) || undefined,
    item_name: toText(item.item_name || item.name) || undefined,
    unit: toText(item.unit) || undefined,
    baseline_quantity: toNumber(item.baseline_quantity),
    variation_quantity: toNumber(item.variation_quantity),
    settled_quantity: toNumber(item.settled_quantity),
    deviation_quantity: toNumber(item.deviation_quantity),
    illegal_attempt_count: toNumber(item.illegal_attempt_count),
    status: toText(item.status) || undefined,
  }))

  const illegalAttempts = asArray<Dict>(row.illegal_attempts).map((item) => ({
    subitem_code: toText(item.subitem_code) || undefined,
    proof_id: toText(item.proof_id || item.id) || undefined,
    reason: toText(item.reason || item.message) || undefined,
    action: toText(item.action) || undefined,
    created_at: toText(item.created_at || item.createdAt) || undefined,
  }))

  const summaryRaw = asDict(row.summary)
  const summary: BoqAuditSummary = {
    item_count: toNumber(summaryRaw.item_count, items.length),
    baseline_total: toNumber(summaryRaw.baseline_total),
    variation_total: toNumber(summaryRaw.variation_total),
    settled_total: toNumber(summaryRaw.settled_total),
    deviation_total: toNumber(summaryRaw.deviation_total),
    illegal_attempt_count: toNumber(summaryRaw.illegal_attempt_count, illegalAttempts.length),
  }

  return {
    summary,
    items,
    illegal_attempts: illegalAttempts,
  }
}

function mapBoqProofPreview(boqItemUri: string, payload: unknown): BoqProofPreview {
  const row = asDict(payload)
  const ctx = asDict(row.context)
  const timelineRows = asArray<Dict>(ctx.timeline_rows).map((item, idx) => ({
    step: toNumber(item.step, idx + 1),
    label: toText(item.label || item.action || item.trip_action) || undefined,
    result: toText(item.result || item.status) || undefined,
    time: toText(item.time || item.created_at || item.createdAt) || undefined,
    proof_id: toText(item.proof_id || item.id) || undefined,
  }))

  return {
    boq_item_uri: boqItemUri,
    chain_count: toNumber(row.chain_count, timelineRows.length),
    context: {
      chain_root_hash: toText(ctx.chain_root_hash || row.chain_root_hash) || undefined,
      timeline_rows: timelineRows,
    },
  }
}

function mapBoqSovereignPreview(subitemCode: string, payload: unknown): BoqSovereignPreview {
  const row = asDict(payload)
  const timeline = asArray<Dict>(row.rows || row.timeline || row.items).map((item, idx) => ({
    proof_id: toText(item.proof_id || item.id) || undefined,
    proof_type: toText(item.proof_type || item.type) || undefined,
    result: toText(item.result || item.status) || undefined,
    created_at: toText(item.created_at || item.createdAt || item.time) || undefined,
    trip_action: toText(item.trip_action || item.action) || undefined,
    depth: toNumber(item.depth, idx + 1),
  }))

  return {
    subitem_code: subitemCode,
    root_utxo_id: toText(row.root_utxo_id) || undefined,
    boq_item_uri: toText(row.boq_item_uri) || undefined,
    totals: {
      proof_count: timeline.length,
      document_count: toNumber(row.document_count),
      variation_count: toNumber(row.variation_count),
      settlement_count: toNumber(row.settlement_count),
      fail_count: timeline.filter((item) => toText(item.result).toLowerCase() === 'fail').length,
    },
    timeline,
    documents: asArray<Dict>(row.documents).map((item) => ({
      proof_id: toText(item.proof_id || item.id) || undefined,
      file_name: toText(item.file_name || item.name) || undefined,
      doc_type: toText(item.doc_type || item.type) || undefined,
      storage_url: toText(item.storage_url || item.url) || undefined,
      source_utxo_id: toText(item.source_utxo_id) || undefined,
    })),
  }
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
  const projectId = useMemo(() => resolveProjectId(proj, detailProject), [proj, detailProject])
  const projectUri = useMemo(() => resolveProjectUri(proj, detailProject), [proj, detailProject])
  const projectUriRef = useRef(projectUri)
  const showToastRef = useRef(showToast)
  const listProofsRef = useRef(listProofs)
  const verifyProofRef = useRef(verifyProof)
  const proofStatsApiRef = useRef(proofStatsApi)
  const proofNodeTreeApiRef = useRef(proofNodeTreeApi)
  const boqRealtimeStatusApiRef = useRef(boqRealtimeStatusApi)
  const boqItemSovereignHistoryApiRef = useRef(boqItemSovereignHistoryApi)
  const boqReconciliationApiRef = useRef(boqReconciliationApi)
  const docFinalContextApiRef = useRef(docFinalContextApi)

  useEffect(() => {
    projectUriRef.current = projectUri
  }, [projectUri])

  useEffect(() => {
    showToastRef.current = showToast
  }, [showToast])

  useEffect(() => {
    listProofsRef.current = listProofs
  }, [listProofs])

  useEffect(() => {
    verifyProofRef.current = verifyProof
  }, [verifyProof])

  useEffect(() => {
    proofStatsApiRef.current = proofStatsApi
  }, [proofStatsApi])

  useEffect(() => {
    proofNodeTreeApiRef.current = proofNodeTreeApi
  }, [proofNodeTreeApi])

  useEffect(() => {
    boqRealtimeStatusApiRef.current = boqRealtimeStatusApi
  }, [boqRealtimeStatusApi])

  useEffect(() => {
    boqItemSovereignHistoryApiRef.current = boqItemSovereignHistoryApi
  }, [boqItemSovereignHistoryApi])

  useEffect(() => {
    boqReconciliationApiRef.current = boqReconciliationApi
  }, [boqReconciliationApi])

  useEffect(() => {
    docFinalContextApiRef.current = docFinalContextApi
  }, [docFinalContextApi])

  const [proofStats, setProofStats] = useState<ProofStats>({ total: 0, by_type: {}, by_action: {} })
  const [proofNodeRows, setProofNodeRows] = useState<ProofNodeRow[]>([])
  const [proofRows, setProofRows] = useState<ProofRow[]>([])
  const [proofLoading, setProofLoading] = useState(false)
  const [proofVerifying, setProofVerifying] = useState<string | null>(null)

  const [boqRealtime, setBoqRealtime] = useState<BoqRealtime | null>(null)
  const [boqRealtimeLoading, setBoqRealtimeLoading] = useState(false)
  const [boqAudit, setBoqAudit] = useState<BoqAudit | null>(null)
  const [boqAuditLoading, setBoqAuditLoading] = useState(false)

  const [boqProofPreview, setBoqProofPreview] = useState<BoqProofPreview | null>(null)
  const [boqProofLoadingUri, setBoqProofLoadingUri] = useState<string | null>(null)
  const [boqSovereignPreview, setBoqSovereignPreview] = useState<BoqSovereignPreview | null>(null)
  const [boqSovereignLoadingCode, setBoqSovereignLoadingCode] = useState<string | null>(null)

  useEffect(() => {
    if (activeTab !== 'proof') return
    if (!projectId) {
      setProofRows([])
      setProofStats({ total: 0, by_type: {}, by_action: {} })
      setProofNodeRows([])
      return
    }

    let cancelled = false

    const loadProofPanel = async () => {
      setProofLoading(true)
      try {
        const [proofListRes, statsRes, nodeRes] = await Promise.all([
          listProofsRef.current(projectId),
          proofStatsApiRef.current(projectId),
          proofNodeTreeApiRef.current(projectUri || `v://cn.docpeg/project/${projectId}`),
        ])

        if (cancelled) return

        const rows = mapProofRows(proofListRes)
        setProofRows(rows)
        setProofStats(mapProofStats(statsRes, rows))
        setProofNodeRows(mapProofNodeRows(nodeRes))
      } catch {
        if (!cancelled) {
          setProofRows([])
          setProofStats({ total: 0, by_type: {}, by_action: {} })
          setProofNodeRows([])
        }
      } finally {
        if (!cancelled) setProofLoading(false)
      }
    }

    void loadProofPanel()

    return () => {
      cancelled = true
    }
  }, [activeTab, projectId, projectUri])

  useEffect(() => {
    if (!projectDetailOpen) return
    if (!projectUri) return

    let cancelled = false

    const loadBoqPanels = async () => {
      setBoqRealtimeLoading(true)
      setBoqAuditLoading(true)

      try {
        const [realtimeRes, auditRes] = await Promise.all([
          boqRealtimeStatusApiRef.current(projectUri),
          boqReconciliationApiRef.current({
            project_uri: projectUri,
            max_rows: 200,
            limit_items: 120,
          }),
        ])

        if (cancelled) return

        setBoqRealtime(mapBoqRealtime(realtimeRes))
        setBoqAudit(mapBoqAudit(auditRes))
      } catch {
        if (!cancelled) {
          setBoqRealtime({ summary: { boq_item_count: 0, design_total: 0, settled_total: 0, progress_percent: 0 }, items: [] })
          setBoqAudit({ summary: { item_count: 0, baseline_total: 0, variation_total: 0, settled_total: 0, deviation_total: 0, illegal_attempt_count: 0 }, items: [], illegal_attempts: [] })
        }
      } finally {
        if (!cancelled) {
          setBoqRealtimeLoading(false)
          setBoqAuditLoading(false)
        }
      }
    }

    void loadBoqPanels()

    return () => {
      cancelled = true
    }
  }, [projectDetailOpen, projectUri])

  const handleVerifyProof = useCallback(async (proofId: string) => {
    const id = toText(proofId)
    if (!id) return

    setProofVerifying(id)
    try {
      const res = asDict(await verifyProofRef.current(id))
      const verified = Boolean(res.valid ?? res.verified)
      showToastRef.current(verified ? `Proof 校验通过：${id}` : `Proof 校验失败：${id}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误'
      showToastRef.current(`Proof 校验失败：${message}`)
    } finally {
      setProofVerifying((current) => (current === id ? null : current))
    }
  }, [])

  const handleOpenBoqProofChain = useCallback(async (boqItemUri: string) => {
    const uri = toText(boqItemUri)
    if (!uri) return

    setBoqProofLoadingUri(uri)
    try {
      const payload = await docFinalContextApiRef.current(uri)
      setBoqProofPreview(mapBoqProofPreview(uri, payload))
    } catch {
      setBoqProofPreview({
        boq_item_uri: uri,
        chain_count: 0,
        context: {
          chain_root_hash: '',
          timeline_rows: [],
        },
      })
    } finally {
      setBoqProofLoadingUri((current) => (current === uri ? null : current))
    }
  }, [])

  const handleOpenBoqSovereignHistory = useCallback(async (subitemCode: string) => {
    const code = toText(subitemCode)
    const uri = projectUriRef.current
    if (!code || !uri) return

    setBoqSovereignLoadingCode(code)
    try {
      const payload = await boqItemSovereignHistoryApiRef.current({
        project_uri: uri,
        subitem_code: code,
        max_rows: 120,
      })
      setBoqSovereignPreview(mapBoqSovereignPreview(code, payload))
    } catch {
      setBoqSovereignPreview({
        subitem_code: code,
        totals: {
          proof_count: 0,
          document_count: 0,
          variation_count: 0,
          settlement_count: 0,
          fail_count: 0,
        },
        timeline: [],
        documents: [],
      })
    } finally {
      setBoqSovereignLoadingCode((current) => (current === code ? null : current))
    }
  }, [])

  return {
    projectUri,
    proofStats,
    proofNodeRows,
    proofLoading,
    proofRows,
    proofVerifying,
    handleVerifyProof,

    boqRealtime,
    boqRealtimeLoading,
    boqAudit,
    boqAuditLoading,
    boqProofPreview,
    boqProofLoadingUri,
    boqSovereignPreview,
    boqSovereignLoadingCode,
    handleOpenBoqProofChain,
    handleOpenBoqSovereignHistory,
  }
}
