import { useEffect, useMemo, useState } from 'react'

type HashVerification = {
  provided_hash?: string
  recomputed_hash?: string
  matches?: boolean
  source_json?: string
}

type ExecInfo = {
  test_type?: string
  stake?: string
  value?: string
  standard?: string
  norm?: string
  operator?: string
  threshold?: string
}

type PersonInfo = {
  name?: string
  uri?: string
  role?: string
  time?: string
  sign?: string
}

export type TimelineItem = {
  step?: number
  type?: string
  title?: string
  description?: string
  time?: string
  executor?: string
  status?: string
  spec_uri?: string
  spec_excerpt?: string
  operator?: string
  threshold?: string
  rule_source_uri?: string
  proof_id?: string
  from_remediation?: boolean
}

type ChainItem = {
  type?: string
  label?: string
  status?: string
  time?: string
  actor?: string
  proof?: string
  current?: boolean
  proof_id?: string
  result?: string
  parent?: string
  executor?: string
  executor_name?: string
  proof_type?: string
}

type AuditItem = {
  index?: number
  proof_id?: string
  type?: string
  proof_type?: string
  result?: string
  parent?: string
  time?: string
  executor?: string
  executor_name?: string
  spec_uri?: string
  operator?: string
  threshold?: string
  proof_hash?: string
  recomputed_hash?: string
  hash_valid?: boolean
}

type QCGateRule = {
  rule_id?: string
  spec_uri?: string
  spec_excerpt?: string
  operator?: string
  threshold?: string
  measured?: string
  result?: string
  result_cn?: string
  deviation_percent?: number
  source_proof_id?: string
  executed_at?: string
  proof_hash?: string
  recomputed_hash?: string
  hash_valid?: boolean
}

type RemediationRecord = {
  proof_id?: string
  proof_type?: string
  result?: string
  result_cn?: string
  time?: string
  executor?: string
  description?: string
  proof_hash?: string
  hash_valid?: boolean
  parent?: string
}

type EvidenceItem = {
  id?: string
  file_name?: string
  url?: string
  media_type?: string
  evidence_hash?: string
  proof_id?: string
  proof_hash?: string
  size?: number
  time?: string
  source?: string
  hash_matched?: boolean
  hash_match_text?: string
  geo_location?: {
    lat?: number | string
    lng?: number | string
  }
  server_timestamp_proof?: {
    timestamp_fingerprint?: string
    ntp_server?: string
  }
  spatiotemporal_anchor_hash?: string
}

type VerifyPayload = {
  ok?: boolean
  verified?: boolean
  proof_id?: string
  verify_url?: string
  hash_payload?: Record<string, unknown>
  hash_verification?: HashVerification
  context?: {
    project_uri?: string
    segment_uri?: string
    stake?: string
    executor_uri?: string
    contract_uri?: string
    design_uri?: string
  }
  summary?: {
    project_name?: string
    project_uri?: string
    segment_uri?: string
    stake?: string
    test_name?: string
    value?: string
    standard?: string
    result?: string
    result_cn?: string
    deviation_percent?: number
    created_at?: string
    spec_uri?: string
    spec_version?: string
    rule_source_uri?: string
    spec_snapshot?: string
    action_item_id?: string
  }
  sovereignty?: {
    proof_id?: string
    proof_hash?: string
    v_uri?: string
    gitpeg_anchor?: string
    gitpeg_status?: {
      anchored?: boolean
      anchor_ref?: string
      block_height?: number | null
      merkle_root?: string
      message?: string
    }
    ordosign_hash?: string
    executor_uri?: string
    signed_by?: string
    signed_role?: string
    signed_at?: string
  }
  exec?: ExecInfo
  person?: PersonInfo
  timeline?: TimelineItem[]
  chain?: ChainItem[]
  qcgate?: {
    gate_id?: string
    stake?: string
    status?: string
    pass_policy?: string
    all_hash_valid?: boolean
    rule_count?: number
    rules?: QCGateRule[]
  }
  remediation?: {
    issue_id?: string
    has_remediation?: boolean
    latest_pass_proof_id?: string
    records?: RemediationRecord[]
  }
  evidence?: EvidenceItem[]
  audit?: {
    depth?: number
    rows?: AuditItem[]
  }
  lineage_depth?: 'item' | 'unit' | 'project'
  lineage_merkle?: {
    mode?: 'item' | 'unit' | 'project'
    project_uri?: string
    requested_proof_id?: string
    requested_item_uri?: string
    resolved_unit_code?: string
    unit_root_hash?: string
    project_root_hash?: string
    global_project_fingerprint?: string
    item_index?: number
    unit_index?: number
    leaf_count?: number
    item_merkle_path?: Array<{ depth?: number; position?: string; sibling_hash?: string }>
    unit_merkle_path?: Array<{ depth?: number; position?: string; sibling_hash?: string }>
  }
}

type HashState = {
  status: 'loading' | 'pass' | 'fail' | 'fallback'
  computed: string
}

type ChainViewItem = {
  type: string
  label: string
  status: 'pass' | 'fail' | 'pending'
  time: string
  actor: string
  proof: string
  current: boolean
}

type SpecModalState = {
  title: string
  uri: string
  excerpt: string
  source?: string
} | null

function normalizeApiBase(raw: string): string {
  const text = String(raw || '').trim().replace(/\/+$/, '')
  if (!text) return ''
  if (text.endsWith('/v1')) return text.slice(0, -3)
  return text
}

function buildApiBases(envBaseRaw: string): string[] {
  const bases: string[] = []
  const envBase = normalizeApiBase(envBaseRaw)
  if (envBase) bases.push(envBase)

  const origin = normalizeApiBase(window.location.origin)
  if (origin) bases.push(origin)

  const host = String(window.location.hostname || '').toLowerCase()
  const isLocal = host === '127.0.0.1' || host === 'localhost'
  if (isLocal) {
    const proto = window.location.protocol === 'https:' ? 'https' : 'http'
    bases.push(`${proto}://127.0.0.1:8010`)
    bases.push(`${proto}://127.0.0.1:8000`)
    bases.push(`${proto}://localhost:8010`)
    bases.push(`${proto}://localhost:8000`)
  }

  const uniq: string[] = []
  const seen = new Set<string>()
  for (const base of bases) {
    const key = normalizeApiBase(base)
    if (!key || seen.has(key)) continue
    seen.add(key)
    uniq.push(key)
  }
  return uniq
}

export function formatTimestamp(raw: unknown): string {
  const text = String(raw ?? '').trim()
  if (!text) return '-'
  const normalized = text.replace('T', ' ').replace('Z', '')
  const withoutMicros = normalized.replace(/\.(\d+)/, '')
  const withoutOffset = withoutMicros.replace(/[+-]\d{2}:?\d{2}$/, '').trim()

  const sec = withoutOffset.match(/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/)
  if (sec?.[1]) return sec[1].replace(/\s+/, ' ')
  const minute = withoutOffset.match(/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})$/)
  if (minute?.[1]) return `${minute[1]}:00`

  const dt = new Date(text)
  if (!Number.isNaN(dt.getTime())) {
    const y = dt.getFullYear()
    const m = `${dt.getMonth() + 1}`.padStart(2, '0')
    const d = `${dt.getDate()}`.padStart(2, '0')
    const hh = `${dt.getHours()}`.padStart(2, '0')
    const mm = `${dt.getMinutes()}`.padStart(2, '0')
    const ss = `${dt.getSeconds()}`.padStart(2, '0')
    return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
  }
  return withoutOffset || text
}

function looksLikeMojibake(input: string): boolean {
  if (!input || /[\u4e00-\u9fff]/.test(input)) return false
  let latinExtended = 0
  for (const ch of input) {
    const code = ch.charCodeAt(0)
    if (code >= 0x00c0 && code <= 0x00ff) latinExtended += 1
  }
  return latinExtended >= 2
}

function decodeLatin1Utf8(input: string): string {
  if (!looksLikeMojibake(input)) return input
  try {
    const bytes = new Uint8Array(Array.from(input, (ch) => ch.charCodeAt(0) & 0xff))
    const decoded = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
    return /[\u4e00-\u9fff]/.test(decoded) ? decoded : input
  } catch {
    return input
  }
}

function normalizePayload<T>(value: T): T {
  if (typeof value === 'string') return decodeLatin1Utf8(value) as T
  if (Array.isArray(value)) return value.map((item) => normalizePayload(item)) as T
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      out[key] = normalizePayload(item)
    }
    return out as T
  }
  return value
}

function stableStringify(value: unknown): string {
  if (value === null || value === undefined) return 'null'
  if (typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map((item) => stableStringify(item)).join(',')}]`
  const obj = value as Record<string, unknown>
  const keys = Object.keys(obj).sort()
  const pairs = keys.map((key) => `${JSON.stringify(key)}:${stableStringify(obj[key])}`)
  return `{${pairs.join(',')}}`
}

async function sha256Hex(text: string): Promise<string> {
  if (!window.crypto?.subtle) throw new Error('WebCrypto unavailable')
  const data = new TextEncoder().encode(text)
  const digest = await window.crypto.subtle.digest('SHA-256', data)
  const bytes = new Uint8Array(digest)
  return Array.from(bytes).map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

export function normalizeStatusToken(input: string): 'pass' | 'fail' | 'pending' {
  const token = String(input || '').trim().toUpperCase()
  if (token === 'PASS' || token === 'OK' || token === 'SUCCESS') return 'pass'
  if (token === 'FAIL' || token === 'ERROR' || token === 'REJECTED') return 'fail'
  return 'pending'
}

export function chainIcon(type: string): string {
  const token = String(type || '').toLowerCase()
  if (token.includes('spec')) return '📘'
  if (token.includes('rule')) return '⚙️'
  if (token.includes('triprole')) return '👤'
  if (token.includes('proof')) return '⛓️'
  if (token.includes('inspection')) return '📍'
  if (token.includes('lab')) return '🧪'
  if (token.includes('payment')) return '💵'
  if (token.includes('archive')) return '📦'
  if (token.includes('rect') || token.includes('repair') || token.includes('remed')) return '🛠️'
  if (token.includes('approval')) return '✅'
  if (token.includes('notify')) return '📨'
  if (token.includes('ordosign')) return '🔏'
  return '⛓️'
}

function requestPathProofId(): string {
  const path = String(window.location.pathname || '')
  const raw = path.startsWith('/v/') ? path.slice(3) : path
  return decodeURIComponent(raw).trim()
}

async function requestVerifyPayload(apiBases: string[], proofId: string, lineageDepth: 'item' | 'unit' | 'project'): Promise<VerifyPayload> {
  const encoded = encodeURIComponent(proofId)
  const depthQuery = `lineage_depth=${encodeURIComponent(lineageDepth)}`

  let lastError = '请求失败'
  for (const base of apiBases) {
    const candidates = [`${base}/api/v1/verify/${encoded}?${depthQuery}`, `${base}/api/verify/${encoded}?${depthQuery}`]
    for (const url of candidates) {
      try {
        const res = await fetch(url, { method: 'GET' })
        const body = (await res.json().catch(() => ({}))) as VerifyPayload | { detail?: string }
        if (res.ok) return normalizePayload(body as VerifyPayload)
        lastError = (body as { detail?: string }).detail || `请求失败: ${res.status}`
        if (res.status !== 404) break
      } catch (error) {
        lastError = error instanceof Error ? error.message : '请求失败'
      }
    }
  }
  throw new Error(lastError)
}

async function downloadDsp(apiBases: string[], proofId: string): Promise<void> {
  const encoded = encodeURIComponent(proofId)
  let lastError = '下载失败'
  for (const base of apiBases) {
    const candidates = [`${base}/api/v1/verify/${encoded}/dsp`, `${base}/api/verify/${encoded}/dsp`]
    for (const url of candidates) {
      try {
        const res = await fetch(url, { method: 'GET' })
        if (res.ok) {
          const blob = await res.blob()
          const href = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = href
          link.download = `DSP-${proofId}.zip`
          document.body.appendChild(link)
          link.click()
          link.remove()
          URL.revokeObjectURL(href)
          return
        }
        const body = await res.json().catch(() => ({} as { detail?: string }))
        lastError = body?.detail || `下载失败: ${res.status}`
        if (res.status !== 404) break
      } catch (error) {
        lastError = error instanceof Error ? error.message : '下载失败'
      }
    }
  }
  throw new Error(lastError)
}

export function usePublicVerifyController() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [payload, setPayload] = useState<VerifyPayload | null>(null)
  const [hashState, setHashState] = useState<HashState>({ status: 'loading', computed: '' })
  const [showAudit, setShowAudit] = useState(true)
  const [specModal, setSpecModal] = useState<SpecModalState>(null)
  const [showRectify, setShowRectify] = useState(false)
  const [downloadingDsp, setDownloadingDsp] = useState(false)
  const [lineageDepth, setLineageDepth] = useState<'item' | 'unit' | 'project'>(() => {
    const qs = new URLSearchParams(window.location.search)
    const raw = String(qs.get('lineage_depth') || 'item').toLowerCase()
    if (raw === 'unit' || raw === 'project') return raw
    return 'item'
  })

  const proofId = useMemo(() => requestPathProofId(), [])
  const traceMode = useMemo(() => {
    const qs = new URLSearchParams(window.location.search)
    return qs.get('trace') === 'true'
  }, [])

  const apiBases = useMemo(() => {
    const envBase = (import.meta.env.VITE_PUBLIC_VERIFY_API_BASE || import.meta.env.VITE_API_URL || '').toString()
    return buildApiBases(envBase)
  }, [])

  useEffect(() => {
    let active = true
    const run = async () => {
      if (!proofId) {
        if (active) {
          setError('proof_id 缺失')
          setLoading(false)
        }
        return
      }
      try {
        setLoading(true)
        setError('')
        const body = await requestVerifyPayload(apiBases, proofId, lineageDepth)
        if (!active) return
        setPayload(body)
      } catch (err) {
        if (!active) return
        setPayload(null)
        setError(err instanceof Error ? err.message : '加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [apiBases, proofId, lineageDepth])

  useEffect(() => {
    let active = true
    const run = async () => {
      if (!payload) {
        if (active) setHashState({ status: 'loading', computed: '' })
        return
      }
      const expected = String(payload.sovereignty?.proof_hash || payload.hash_verification?.provided_hash || '').trim().toLowerCase()
      if (!expected) {
        if (active) setHashState({ status: 'fail', computed: '' })
        return
      }

      const source = String(payload.hash_verification?.source_json || '').trim()
      const fallbackSource = source || stableStringify(payload.hash_payload || {})

      try {
        const computed = (await sha256Hex(fallbackSource)).toLowerCase()
        if (!active) return
        setHashState({ status: computed === expected ? 'pass' : 'fail', computed })
      } catch {
        if (!active) return
        const fallbackMatches = Boolean(payload.hash_verification?.matches || payload.verified)
        setHashState({ status: fallbackMatches ? 'fallback' : 'fail', computed: '' })
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [payload])

  const hashVerified = useMemo(() => hashState.status === 'pass' || hashState.status === 'fallback', [hashState.status])

  const summary = payload?.summary || {}
  const sovereignty = payload?.sovereignty || {}
  const context = payload?.context || {}
  const qcgate = payload?.qcgate || {}
  const remediation = payload?.remediation || {}
  const gateHashOk = qcgate.all_hash_valid !== false
  const remediationRecords = useMemo(() => (Array.isArray(remediation.records) ? remediation.records : []), [remediation.records])
  const hasRemediation = Boolean(remediation.has_remediation && remediationRecords.length)

  const execInfo = useMemo(() => {
    const rawExec = payload?.exec || {}
    return {
      testType: String(rawExec.test_type || summary.test_name || '-'),
      stake: String(rawExec.stake || context.stake || summary.stake || 'K50+200'),
      value: String(rawExec.value || summary.value || '-'),
      standard: String(rawExec.standard || summary.standard || '-'),
      norm: String(rawExec.norm || summary.spec_uri || (payload?.hash_payload || {}).norm_uri || '-'),
      operator: String(rawExec.operator || '-'),
      threshold: String(rawExec.threshold || '-'),
    }
  }, [payload, summary, context.stake])

  const personInfo = useMemo(() => {
    const rawPerson = payload?.person || {}
    const role = String(rawPerson.role || sovereignty.signed_role || '-')
    const signRaw = String(rawPerson.sign || sovereignty.ordosign_hash || '-')
    const sign = signRaw.length > 18 ? `${signRaw.slice(0, 18)}...` : signRaw
    return {
      name: String(rawPerson.name || sovereignty.signed_by || '-'),
      uri: String(rawPerson.uri || sovereignty.executor_uri || context.executor_uri || '-'),
      role,
      time: formatTimestamp(rawPerson.time || sovereignty.signed_at || summary.created_at),
      sign,
    }
  }, [payload, sovereignty, summary.created_at, context.executor_uri])

  const businessFail = useMemo(() => {
    const token = String(summary.result || '').toUpperCase()
    const cn = String(summary.result_cn || '')
    return token === 'FAIL' || cn.includes('不合格')
  }, [summary.result, summary.result_cn])

  useEffect(() => {
    if (businessFail && hasRemediation) {
      setShowRectify(true)
    }
  }, [businessFail, hasRemediation])

  const chainItems = useMemo<ChainViewItem[]>(() => {
    const rawChain = Array.isArray(payload?.chain) ? payload.chain : []
    const currentProof = String(sovereignty.proof_id || payload?.proof_id || '')

    if (!rawChain.length) {
      return [{
        type: 'proof',
        label: 'Proof 节点',
        status: businessFail ? 'fail' : 'pass',
        time: formatTimestamp(summary.created_at || sovereignty.signed_at),
        actor: `${personInfo.name} [${personInfo.role}]`,
        proof: currentProof || '-',
        current: true,
      }]
    }

    return rawChain.map((row, idx) => {
      const proof = String(row.proof || row.proof_id || '-')
      const status = normalizeStatusToken(String(row.status || row.result || ''))
      const actor = String(
        row.actor
          || row.executor_name
          || row.executor
          || (proof === currentProof || idx === rawChain.length - 1 ? `${personInfo.name} [${personInfo.role}]` : '-'),
      )
      return {
        type: String(row.type || row.proof_type || 'proof'),
        label: String(row.label || row.proof_type || 'Proof 节点'),
        status,
        time: formatTimestamp(row.time || summary.created_at),
        actor,
        proof,
        current: Boolean(row.current) || proof === currentProof,
      }
    })
  }, [payload, sovereignty.proof_id, payload?.proof_id, businessFail, summary.created_at, sovereignty.signed_at, personInfo])

  const auditRows = useMemo(() => (Array.isArray(payload?.audit?.rows) ? payload.audit?.rows : []), [payload])
  const timeline = useMemo(() => (Array.isArray(payload?.timeline) ? payload.timeline : []), [payload])
  const gateRules = useMemo(() => (Array.isArray(qcgate.rules) ? qcgate.rules : []), [qcgate.rules])
  const evidenceItems = useMemo(() => (Array.isArray(payload?.evidence) ? payload.evidence : []), [payload?.evidence])

  const remediationTimelineNodes = useMemo<TimelineItem[]>(() => {
    if (!businessFail || !showRectify || remediationRecords.length === 0) return []
    return remediationRecords.map((rec, idx) => ({
      step: timeline.length + idx + 1,
      type: 'Remediation',
      title: `整改链路节点 ${idx + 1}`,
      description: rec.description || '整改记录',
      time: rec.time,
      executor: rec.executor || 'RectifyFlow',
      status: normalizeStatusToken(String(rec.result || 'PENDING')),
      proof_id: rec.proof_id,
      spec_uri: summary.spec_uri,
      spec_excerpt: summary.spec_snapshot || summary.spec_uri || '',
      from_remediation: true,
    }))
  }, [businessFail, showRectify, remediationRecords, timeline.length, summary.spec_uri, summary.spec_snapshot])

  const timelineView = useMemo<TimelineItem[]>(() => [...timeline, ...remediationTimelineNodes], [timeline, remediationTimelineNodes])

  const proofIdDisplay = String(sovereignty.proof_id || payload?.proof_id || '-')
  const expectedHash = String(sovereignty.proof_hash || payload?.hash_verification?.provided_hash || '')
  const hashDisplay = expectedHash ? (expectedHash.startsWith('sha256:') ? expectedHash : `sha256: ${expectedHash}`) : '-'
  const vpath = String(sovereignty.v_uri || context.project_uri || summary.project_uri || '-').replace(/^v:\/\//, '')
  const gitpegStatus = sovereignty.gitpeg_status || {}
  const lineageMerkle = payload?.lineage_merkle || {}
  const gitpegMessage = String(gitpegStatus.message || '')
  const anchorRef = String(gitpegStatus.anchor_ref || sovereignty.gitpeg_anchor || '-')

  const handleDownloadDsp = async () => {
    if (!proofId || downloadingDsp) return
    setDownloadingDsp(true)
    try {
      await downloadDsp(apiBases, proofId)
    } catch (err) {
      const message = err instanceof Error ? err.message : '下载失败'
      window.alert(message)
    } finally {
      setDownloadingDsp(false)
    }
  }

  const handleLineageDepthChange = (next: 'item' | 'unit' | 'project') => {
    setLineageDepth(next)
    try {
      const url = new URL(window.location.href)
      url.searchParams.set('lineage_depth', next)
      window.history.replaceState({}, '', url.toString())
    } catch {
      // no-op
    }
  }

  const openSpecModal = (node: TimelineItem) => {
    const uri = String(node.spec_uri || summary.spec_uri || execInfo.norm || '').trim()
    if (!uri) return
    setSpecModal({
      title: node.title || '规范条文摘要',
      uri,
      excerpt: String(node.spec_excerpt || summary.spec_snapshot || '规范摘要暂未提供'),
      source: String(node.rule_source_uri || summary.rule_source_uri || ''),
    })
  }

  const closeSpecModal = () => setSpecModal(null)
  const toggleAudit = () => setShowAudit((state) => !state)
  const toggleRectify = () => setShowRectify((state) => !state)

  return {
    loading,
    error,
    payload,
    hashState,
    hashVerified,
    showAudit,
    specModal,
    showRectify,
    downloadingDsp,
    lineageDepth,
    traceMode,
    summary,
    sovereignty,
    context,
    qcgate,
    remediation,
    gateHashOk,
    remediationRecords,
    hasRemediation,
    execInfo,
    personInfo,
    businessFail,
    chainItems,
    auditRows,
    timelineView,
    gateRules,
    evidenceItems,
    proofIdDisplay,
    hashDisplay,
    vpath,
    gitpegStatus,
    lineageMerkle,
    gitpegMessage,
    anchorRef,
    handleDownloadDsp,
    handleLineageDepthChange,
    openSpecModal,
    closeSpecModal,
    toggleAudit,
    toggleRectify,
  }
}
