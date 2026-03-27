import React, { useEffect, useMemo, useState } from 'react'
import './PublicVerifyPage.css'

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

type TimelineItem = {
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
  for (const b of bases) {
    const key = normalizeApiBase(b)
    if (!key || seen.has(key)) continue
    seen.add(key)
    uniq.push(key)
  }
  return uniq
}

function formatTimestamp(raw: unknown): string {
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
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = normalizePayload(v)
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
  return Array.from(bytes).map((b) => b.toString(16).padStart(2, '0')).join('')
}

function normalizeStatusToken(input: string): 'pass' | 'fail' | 'pending' {
  const token = String(input || '').trim().toUpperCase()
  if (token === 'PASS' || token === 'OK' || token === 'SUCCESS') return 'pass'
  if (token === 'FAIL' || token === 'ERROR' || token === 'REJECTED') return 'fail'
  return 'pending'
}

function chainIcon(type: string): string {
  const t = String(type || '').toLowerCase()
  if (t.includes('spec')) return '📘'
  if (t.includes('rule')) return '⚙️'
  if (t.includes('triprole')) return '👤'
  if (t.includes('proof')) return '⛓️'
  if (t.includes('inspection')) return '📍'
  if (t.includes('lab')) return '🧪'
  if (t.includes('payment')) return '💵'
  if (t.includes('archive')) return '📦'
  if (t.includes('rect') || t.includes('repair') || t.includes('remed')) return '🛠️'
  if (t.includes('approval')) return '✅'
  if (t.includes('notify')) return '📨'
  if (t.includes('ordosign')) return '🔏'
  return '⛓️'
}

function requestPathProofId(): string {
  const path = String(window.location.pathname || '')
  const raw = path.startsWith('/v/') ? path.slice(3) : path
  return decodeURIComponent(raw).trim()
}

async function requestVerifyPayload(apiBases: string[], proofId: string): Promise<VerifyPayload> {
  const encoded = encodeURIComponent(proofId)

  let lastError = '请求失败'
  for (const base of apiBases) {
    const candidates = [`${base}/api/v1/verify/${encoded}`, `${base}/api/verify/${encoded}`]
    for (const url of candidates) {
      try {
        const res = await fetch(url, { method: 'GET' })
        const body = (await res.json().catch(() => ({}))) as VerifyPayload | { detail?: string }
        if (res.ok) return normalizePayload(body as VerifyPayload)
        lastError = (body as { detail?: string }).detail || `请求失败: ${res.status}`
        if (res.status !== 404) break
      } catch (e) {
        lastError = e instanceof Error ? e.message : '请求失败'
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
          const a = document.createElement('a')
          a.href = href
          a.download = `DSP-${proofId}.zip`
          document.body.appendChild(a)
          a.click()
          a.remove()
          URL.revokeObjectURL(href)
          return
        }
        const body = await res.json().catch(() => ({} as { detail?: string }))
        lastError = body?.detail || `下载失败: ${res.status}`
        if (res.status !== 404) break
      } catch (e) {
        lastError = e instanceof Error ? e.message : '下载失败'
      }
    }
  }
  throw new Error(lastError)
}

export default function PublicVerifyPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [payload, setPayload] = useState<VerifyPayload | null>(null)
  const [hashState, setHashState] = useState<HashState>({ status: 'loading', computed: '' })
  const [showAudit, setShowAudit] = useState(true)
  const [specModal, setSpecModal] = useState<{ title: string; uri: string; excerpt: string; source?: string } | null>(null)
  const [showRectify, setShowRectify] = useState(false)
  const [downloadingDsp, setDownloadingDsp] = useState(false)

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
        const body = await requestVerifyPayload(apiBases, proofId)
        if (!active) return
        setPayload(body)
      } catch (e) {
        if (!active) return
        setPayload(null)
        setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }
    void run()
    return () => {
      active = false
    }
  }, [apiBases, proofId])

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
      return [
        {
          type: 'proof',
          label: 'Proof 节点',
          status: businessFail ? 'fail' : 'pass',
          time: formatTimestamp(summary.created_at || sovereignty.signed_at),
          actor: `${personInfo.name} [${personInfo.role}]`,
          proof: currentProof || '-',
          current: true,
        },
      ]
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

  const auditRows = useMemo(() => (Array.isArray(payload?.audit?.rows) ? payload?.audit?.rows : []), [payload])
  const timeline = useMemo(() => (Array.isArray(payload?.timeline) ? payload?.timeline : []), [payload])
  const gateRules = useMemo(() => (Array.isArray(qcgate.rules) ? qcgate.rules : []), [qcgate.rules])
  const evidenceItems = useMemo(() => (Array.isArray(payload?.evidence) ? payload?.evidence : []), [payload?.evidence])

  const remediationTimelineNodes = useMemo<TimelineItem[]>(() => {
    if (!businessFail || !showRectify || !Array.isArray(remediationRecords) || remediationRecords.length === 0) return []
    return remediationRecords.map((rec, idx) => {
      const status = normalizeStatusToken(String(rec.result || 'PENDING'))
      return {
        step: timeline.length + idx + 1,
        type: 'Remediation',
        title: `整改链路节点 ${idx + 1}`,
        description: rec.description || '整改记录',
        time: rec.time,
        executor: rec.executor || 'RectifyFlow',
        status,
        proof_id: rec.proof_id,
        spec_uri: summary.spec_uri,
        spec_excerpt: summary.spec_snapshot || summary.spec_uri || '',
        from_remediation: true,
      }
    })
  }, [businessFail, showRectify, remediationRecords, timeline.length, summary.spec_uri, summary.spec_snapshot])

  const timelineView = useMemo<TimelineItem[]>(() => [...timeline, ...remediationTimelineNodes], [timeline, remediationTimelineNodes])

  const proofIdDisplay = String(sovereignty.proof_id || payload?.proof_id || '-')
  const expectedHash = String(sovereignty.proof_hash || payload?.hash_verification?.provided_hash || '')
  const hashDisplay = expectedHash ? (expectedHash.startsWith('sha256:') ? expectedHash : `sha256: ${expectedHash}`) : '-'
  const vpath = String(sovereignty.v_uri || context.project_uri || summary.project_uri || '-').replace(/^v:\/\//, '')
  const gitpegStatus = sovereignty.gitpeg_status || {}
  const gitpegMessage = String(gitpegStatus.message || '')
  const anchorRef = String(gitpegStatus.anchor_ref || sovereignty.gitpeg_anchor || '-')

  const handleDownloadDsp = async () => {
    if (!proofId || downloadingDsp) return
    setDownloadingDsp(true)
    try {
      await downloadDsp(apiBases, proofId)
    } catch (e) {
      const msg = e instanceof Error ? e.message : '下载失败'
      window.alert(msg)
    } finally {
      setDownloadingDsp(false)
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

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-ring" />
        <div className="loading-text">正在验证 Proof...</div>
      </div>
    )
  }

  if (error || !payload) {
    return (
      <div className="loading">
        <div className="error-card">
          <div className="error-title">验证失败</div>
          <div className="error-text">{error || '未获取到验证数据'}</div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="status-bar">
        <div className={`status-icon ${hashVerified ? 'ok' : 'fail'}`}>{hashVerified ? '✓' : '!'}</div>
        <div className={`status-text ${hashVerified ? 'ok' : 'fail'}`}>
          {hashVerified ? '哈希校验通过 · 主权可信' : '哈希校验失败 · 数据异常'}
        </div>
        <div className={`status-badge ${hashVerified ? '' : 'fail'}`}>{hashVerified ? 'VERIFIED' : 'HASH FAIL'}</div>
      </div>

      <div className={`wrap ${traceMode ? 'trace-mode' : ''}`}>
        <div className="proof-id-card">
          <div className="pic-label">Proof ID</div>
          <div className="pic-id">{proofIdDisplay}</div>
          <div className="pic-hash">{hashDisplay}</div>
          <div className={`verify-stamp ${hashVerified ? 'pass' : 'fail'}`}>{hashVerified ? '验证通过' : '校验异常'}</div>
        </div>

        <div className={`result-card ${businessFail ? 'fail' : 'pass'}`}>
          <div className="rc-icon">{businessFail ? '✖' : '✓'}</div>
          <div>
            <div className={`rc-title ${businessFail ? 'fail' : 'pass'}`}>
              业务结论：{businessFail ? '不合格' : '合格'}
            </div>
            <div className="rc-sub">
              {businessFail
                ? '业务判定不合格，系统判定节点已进入红色预警态。'
                : '业务判定合格，链路追溯结果完整。'}
            </div>
            <div className="result-actions">
              {businessFail ? (
                <button type="button" className="result-btn warn" onClick={() => setShowRectify((s) => !s)}>
                  {showRectify ? '收起整改链路' : '查看整改链路'}
                </button>
              ) : null}
              <button type="button" className="result-btn" onClick={handleDownloadDsp} disabled={downloadingDsp}>
                {downloadingDsp ? '正在打包...' : '下载存档包'}
              </button>
            </div>
            {businessFail ? (
              <div className="result-action-id">
                Action Item: {summary.action_item_id || remediation.issue_id || '-'}
              </div>
            ) : null}
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">📍</span><span className="ic-title">执行信息</span></div>
          <div className="ic-body">
            <div className="ic-row"><span className="ic-key">检测项目</span><span className="ic-val">{execInfo.testType}</span></div>
            <div className="ic-row"><span className="ic-key">桩号位置</span><span className="ic-val blue">{execInfo.stake}</span></div>
            <div className="ic-row"><span className="ic-key">实测值</span><span className={`ic-val ${businessFail ? '' : 'green'}`} style={businessFail ? { color: 'var(--red)' } : undefined}>{execInfo.value}</span></div>
            <div className="ic-row"><span className="ic-key">标准值</span><span className="ic-val">{execInfo.standard}</span></div>
            <div className="ic-row"><span className="ic-key">偏差百分比</span><span className={`ic-val ${Number(summary.deviation_percent) > 0 ? '' : 'green'}`} style={Number(summary.deviation_percent) > 0 ? { color: 'var(--red)' } : undefined}>{typeof summary.deviation_percent === 'number' ? `${summary.deviation_percent > 0 ? '+' : ''}${summary.deviation_percent.toFixed(2)}%` : '-'}</span></div>
            <div className="ic-row"><span className="ic-key">规范地址</span><span className="ic-val blue">{execInfo.norm}</span></div>
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">🖼️</span><span className="ic-title">原始物证</span></div>
          <div className="ic-body">
            {evidenceItems.length ? (
              <div className="evidence-grid">
                {evidenceItems.map((ev, idx) => {
                  const mediaType = String(ev.media_type || '').toLowerCase()
                  const isImage = mediaType === 'image'
                  const isVideo = mediaType === 'video'
                  const hashOk = ev.hash_matched === true
                  const url = String(ev.url || '')
                  return (
                    <div className="evidence-item" key={`${ev.id || ev.proof_id || ev.file_name || 'evidence'}-${idx}`}>
                      <div className="evidence-preview">
                        {isImage && url ? <img src={url} alt={String(ev.file_name || 'evidence')} loading="lazy" /> : null}
                        {isVideo && url ? <video src={url} controls preload="metadata" /> : null}
                        {!url ? <div className="evidence-empty">无预览</div> : null}
                      </div>
                      <div className="evidence-name">{ev.file_name || '-'}</div>
                      <div className={`evidence-hash-badge ${hashOk ? 'ok' : 'pending'}`}>
                        {ev.hash_match_text || (hashOk ? '文件哈希已匹配' : '文件哈希待核验')}
                      </div>
                      <div className="evidence-hash">sha256: {ev.evidence_hash || '-'}</div>
                      <div className="evidence-meta">
                        <span>{formatTimestamp(ev.time)}</span>
                        <span>{ev.proof_id || '-'}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="empty-note">暂无关联物证</div>
            )}
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">📊</span><span className="ic-title">追溯时间轴</span></div>
          <div className="ic-body">
            {timelineView.map((node, idx) => {
              const status = normalizeStatusToken(String(node.status || 'pending'))
              return (
                <div className={`timeline-node ${status} ${traceMode ? 'trace-step' : ''} ${node.from_remediation ? 'remediation-append' : ''}`} style={{ ['--trace-order' as string]: idx + 1 }} key={`${node.step}-${node.title}-${idx}`}>
                  <div className="timeline-head">
                    <span className={`timeline-dot ${status}`} />
                    <span className="timeline-title">{chainIcon(String(node.type || 'proof'))} {node.title || '节点'}</span>
                    <span className="timeline-time">{formatTimestamp(node.time)}</span>
                  </div>
                  <div className="timeline-desc">{node.description || '-'}</div>
                  <div className="timeline-meta">执行体：{node.executor || '-'}</div>
                  {node.proof_id ? <div className="timeline-meta">Proof: {node.proof_id}</div> : null}
                  {node.spec_uri ? (
                    <div className="timeline-spec-wrap">
                      <button
                        type="button"
                        className="timeline-spec-link"
                        onClick={() => openSpecModal(node)}
                      >
                        {node.spec_uri}
                      </button>
                      <div className="timeline-spec-tooltip">{node.spec_excerpt || '规范摘要暂未提供'}</div>
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>

        {businessFail && showRectify ? (
          <div className="info-card">
            <div className="ic-header"><span className="ic-icon">🛠️</span><span className="ic-title">整改闭环追溯</span></div>
            <div className="ic-body">
              <div className="ic-row"><span className="ic-key">整改单</span><span className="ic-val blue">{remediation.issue_id || '-'}</span></div>
              <div className="ic-row"><span className="ic-key">整改状态</span><span className={`ic-val ${hasRemediation ? 'green' : ''}`} style={!hasRemediation ? { color: 'var(--red)' } : undefined}>{hasRemediation ? '已关联后代记录' : '未发现后代整改记录'}</span></div>
              <div className="ic-row"><span className="ic-key">复检合格 Proof</span><span className="ic-val">{remediation.latest_pass_proof_id || '-'}</span></div>
              {hasRemediation ? (
                <div className="rectify-list">
                  {remediationRecords.map((rec, idx) => {
                    const fail = String(rec.result || '').toUpperCase() === 'FAIL'
                    return (
                      <div className={`rectify-item ${fail ? 'fail' : 'pass'}`} key={`${rec.proof_id}-${idx}`}>
                        <div className="rectify-head">
                          <span>{rec.proof_type || '整改记录'}</span>
                          <span>{formatTimestamp(rec.time)}</span>
                        </div>
                        <div className="rectify-desc">{rec.description || '-'}</div>
                        <div className="rectify-meta">{rec.executor || '-'} · {rec.proof_id || '-'}</div>
                      </div>
                    )
                  })}
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">👤</span><span className="ic-title">执行人</span></div>
          <div className="ic-body">
            <div className="ic-row"><span className="ic-key">检测人员</span><span className="ic-val green">{personInfo.name}</span></div>
            <div className="ic-row"><span className="ic-key">执行体节点</span><span className="ic-val blue">{personInfo.uri}</span></div>
            <div className="ic-row"><span className="ic-key">DTORole</span><span className="ic-val">{personInfo.role}</span></div>
            <div className="ic-row"><span className="ic-key">执行时间</span><span className="ic-val">{personInfo.time}</span></div>
            <div className="ic-row"><span className="ic-key">OrdoSign 秩签</span><span className="ic-val orange">{personInfo.sign}</span></div>
          </div>
        </div>

        <div className="chain-card">
          <div className="ic-header"><span className="ic-icon">⛓️</span><span className="ic-title">Proof Chain · 执行链</span></div>
          <div>
            {chainItems.map((step, idx) => (
              <div className={`chain-step ${step.current ? 'current' : ''} ${traceMode ? 'trace-step' : ''}`} style={{ ['--trace-order' as string]: idx + 1 }} key={`${step.proof}-${idx}`}>
                <div className={`cs-dot ${step.status}`} />
                <div className="cs-content">
                  <div className={`cs-type ${step.status}`}>
                    {chainIcon(step.type)} {step.label}
                    {step.current ? <span className="cs-current">当前</span> : null}
                  </div>
                  <div className="cs-meta">{step.actor} · {step.time}</div>
                  <div className="cs-proof">{step.proof}</div>
                </div>
                <div className="cs-arrow">→</div>
              </div>
            ))}
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">🚪</span><span className="ic-title">QCGate 规则执行</span></div>
          <div className="ic-body">
            <div className="ic-row"><span className="ic-key">Gate</span><span className="ic-val">{qcgate.gate_id || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">状态</span><span className={`ic-val ${String(qcgate.status || '').toUpperCase() === 'FAIL' ? '' : 'green'}`} style={String(qcgate.status || '').toUpperCase() === 'FAIL' ? { color: 'var(--red)' } : undefined}>{qcgate.status || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">通过策略</span><span className="ic-val">{qcgate.pass_policy || 'all_pass'}</span></div>
            <div className="ic-row"><span className="ic-key">规则数</span><span className="ic-val">{qcgate.rule_count ?? gateRules.length}</span></div>
            <div className="ic-row"><span className="ic-key">哈希一致性</span><span className={`ic-val ${gateHashOk ? 'green' : ''}`} style={!gateHashOk ? { color: 'var(--red)' } : undefined}>{gateHashOk ? '全量通过' : '存在异常'}</span></div>
            <div className="gate-rules-wrap">
              <table className="gate-rules-table">
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Spec</th>
                    <th>Operator</th>
                    <th>Threshold</th>
                    <th>Measured</th>
                    <th>Result</th>
                    <th>ProofHash</th>
                    <th>Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {gateRules.map((r, i) => {
                    const fail = String(r.result || '').toUpperCase() === 'FAIL'
                    const hasHash = Boolean(String(r.proof_hash || '').trim())
                    const hashOk = r.hash_valid === true
                    return (
                      <tr key={`${r.rule_id}-${i}`} className={fail ? 'gate-rule-fail-row' : ''}>
                        <td className="audit-mono">{r.rule_id || '-'}</td>
                        <td className="audit-mono">{r.spec_uri || '-'}</td>
                        <td>{r.operator || '-'}</td>
                        <td>{r.threshold || '-'}</td>
                        <td>{r.measured || '-'}</td>
                        <td className={fail ? 'audit-fail' : 'audit-pass'}>
                          {r.result || '-'}{typeof r.deviation_percent === 'number' ? ` (${r.deviation_percent > 0 ? '+' : ''}${r.deviation_percent.toFixed(2)}%)` : ''}
                        </td>
                        <td className="audit-mono">{r.proof_hash || '-'}</td>
                        <td className={hasHash ? (hashOk ? 'audit-pass' : 'audit-fail') : ''}>{hasHash ? (hashOk ? 'OK' : 'FAIL') : '-'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">🧾</span><span className="ic-title">链审计详情（全链路穿透）</span></div>
          <div className="ic-body">
            <button type="button" className="audit-toggle" onClick={() => setShowAudit((s) => !s)}>
              {showAudit ? '收起审计表' : '展开审计表'}
            </button>
            {showAudit ? (
              <div className="audit-table-wrap">
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Proof ID</th>
                      <th>Result</th>
                      <th>Parent ID</th>
                      <th>Type</th>
                      <th>ProofType</th>
                      <th>SpecIR</th>
                      <th>ProofHash</th>
                      <th>Hash</th>
                      <th>时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditRows.map((row, idx) => {
                      const fail = String(row.result || '').toUpperCase() === 'FAIL'
                      const hasHash = Boolean(String(row.proof_hash || '').trim())
                      const hashOk = row.hash_valid === true
                      return (
                        <tr key={`${row.proof_id}-${idx}`} className={fail ? 'audit-fail-row' : ''}>
                          <td>{row.index || idx + 1}</td>
                          <td className="audit-mono">{row.proof_id || '-'}</td>
                          <td className={fail ? 'audit-fail' : 'audit-pass'}>{row.result || '-'}</td>
                          <td className="audit-mono">{row.parent || '-'}</td>
                          <td>{row.type || '-'}</td>
                          <td>{row.proof_type || '-'}</td>
                          <td className="audit-mono">{row.spec_uri || '-'}</td>
                          <td className="audit-mono">{row.proof_hash || '-'}</td>
                          <td className={hasHash ? (hashOk ? 'audit-pass' : 'audit-fail') : ''}>{hasHash ? (hashOk ? 'OK' : 'FAIL') : '-'}</td>
                          <td>{row.time || '-'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        </div>

        <div className="vpath-box">
          <span className="vb-pre">v://</span>
          <span className="vb-uri">{vpath}</span>
          <span className="vb-ok">{gitpegStatus.anchored ? '✓ 已锚定' : '⌛ 待锚定'}</span>
        </div>

        <div className="info-card">
          <div className="ic-header"><span className="ic-icon">🔐</span><span className="ic-title">GitPeg 链上锚定</span></div>
          <div className="ic-body">
            <div className="ic-row"><span className="ic-key">锚定状态</span><span className={`ic-val ${gitpegStatus.anchored ? 'green' : ''}`}>{gitpegMessage || '已在本地存证，等待全局锚定'}</span></div>
            <div className="ic-row"><span className="ic-key">锚定引用</span><span className="ic-val blue">{anchorRef}</span></div>
            <div className="ic-row"><span className="ic-key">Merkle 根</span><span className="ic-val">{gitpegStatus.merkle_root || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">三维锚定</span><span className="ic-val">{context.project_uri || '-'} | {context.segment_uri || '-'} | {context.executor_uri || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">源头要求</span><span className="ic-val">{context.contract_uri || '-'} | {context.design_uri || '-'}</span></div>
            <div className="ic-row"><span className="ic-key">重算 Hash</span><span className="ic-val">{hashState.computed || payload.hash_verification?.recomputed_hash || '-'}</span></div>
          </div>
        </div>

        <div className="footer-card">
          <div className="fc-brand">QCSpec · coordOS</div>
          <div className="fc-sub">
            本验证页由 GitPeg v:// 主权协议驱动
            <br />
            Proof Hash 不可篡改 · 链上永久存证
          </div>
          <a className="fc-btn" href={payload.verify_url || '/'}>进入项目控制台</a>
        </div>
      </div>
      {specModal ? (
        <div className="spec-modal-mask" role="presentation" onClick={() => setSpecModal(null)}>
          <div className="spec-modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="spec-modal-head">
              <div className="spec-modal-title">{specModal.title || '规范条文摘要'}</div>
              <button type="button" className="spec-modal-close" onClick={() => setSpecModal(null)}>关闭</button>
            </div>
            <div className="spec-modal-uri">{specModal.uri}</div>
            <div className="spec-modal-content">{specModal.excerpt || '规范摘要暂未提供'}</div>
            {specModal.source ? <div className="spec-modal-source">规则源: {specModal.source}</div> : null}
          </div>
        </div>
      ) : null}
    </>
  )
}
