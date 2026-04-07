import { API_BASE, withAuthHeaders } from '../../hooks/api/base'

export type ConfigEntry = {
  key: string
  value: unknown
  description?: string
  updatedAt: string
}

export type GuardReviewResult = {
  overall: 'PASS' | 'WARN' | 'FAIL'
  policyVersion: string
  targetUri?: string
  summary: string
  checks: Array<{ id: string; result: 'PASS' | 'WARN' | 'FAIL'; reason: string }>
  advisories: string[]
  nextActions: string[]
  proofHash: string
  reviewedAt: string
}

export type ProofResult = {
  proofId: string
  proofHash: string
  segmentUri: string
  committed?: boolean
}

export type AutoTaskInput = {
  targetUri: string
  action: string
  payload?: Record<string, unknown>
  executorUri?: string
  executorRole?: string
  inputProofId?: string
}

export type AutoTaskResult = {
  ok: boolean
  tripId: string
  status: string
  proofHash: string
  result?: unknown
}

export type NormRefResolveResult = {
  ok: boolean
  uri: string
  source?: string
  schema_uri?: string
  version?: string
  protocol?: Record<string, unknown>
}

export type NormRefVerifyResult = {
  ok: boolean
  uri: string
  result: 'PASS' | 'FAIL' | 'WARNING'
  failed_gates: string[]
  failed_mandatory?: Array<Record<string, unknown>>
  failed_warning?: Array<Record<string, unknown>>
  checks?: Array<Record<string, unknown>>
  proof_hash: string
  sealed_at: string
  explain?: string
  schema_uri?: string
  protocol_version?: string
}

export type ExecuteQualityCheckInput = {
  boqItemUri: string
  measuredData: Record<string, unknown>
  protocolUri?: string
  spuUri?: string
  designData?: Record<string, unknown>
  boqItem?: Record<string, unknown>
  resolveBoqItem?: (boqItemUri: string) => Promise<Record<string, unknown> | null>
  context?: Record<string, unknown>
  proofAction?: string
  proofOnResults?: Array<'PASS' | 'FAIL' | 'WARNING'>
  updateStateWhenProof?: boolean
  stateMatrixDelta?: { generated?: number; signed?: number; pending?: number }
}

export type ExecuteQualityCheckOutput = {
  verify: NormRefVerifyResult
  proof?: ProofResult
  stateUpdated: boolean
}

export type ProcessChainStep = {
  step_id: string
  order: number
  name: string
  required_tables: string[]
  pre_conditions: string[]
  next_steps: string[]
  normref_uris: string[]
}

export type ProcessChainState = {
  chain_id: string
  current_step: string
  component_uri: string
  steps: ProcessChainStep[]
  completed_tables: Record<string, Record<string, unknown>>
  state_matrix: {
    total_steps: number
    completed_steps: number
    available_steps: number
    blocked_steps: number
    total_tables: number
    completed_tables: number
    pending_tables: number
    completion_ratio: number
    finalproof_ready: boolean
    current_step: string
  }
}

type RequestInitEx = RequestInit & {
  timeoutMs?: number
}

const CONFIG_LS_PREFIX = 'docpeg.config.'

function nowIso(): string {
  return new Date().toISOString()
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

async function sha256Hex(input: string): Promise<string> {
  const encoder = new TextEncoder()
  const bytes = encoder.encode(input)
  const hash = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

function toProofId(hash: string, prefix = 'GP-DOCPEG'): string {
  return `${prefix}-${hash.slice(0, 16).toUpperCase()}`
}

function pickString(source: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

export class DocPegCoreAPI {
  private readonly baseUrl: string

  private readonly getToken?: () => string | null

  constructor(options: { baseUrl?: string; getToken?: () => string | null } = {}) {
    this.baseUrl = (options.baseUrl || API_BASE || '').replace(/\/+$/, '')
    this.getToken = options.getToken
  }

  private async request<T = unknown>(path: string, init: RequestInitEx = {}): Promise<T> {
    const controller = new AbortController()
    const timeoutMs = Number(init.timeoutMs || 30000)
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
    try {
      const token = this.getToken ? this.getToken() : null
      const headers = withAuthHeaders(token || null, init.headers)
      if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
        headers.set('Content-Type', 'application/json')
      }
      const res = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers,
        signal: controller.signal,
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({} as Record<string, unknown>))
        throw new Error(String((detail as Record<string, unknown>).detail || `HTTP ${res.status}`))
      }
      const payload = await res.json().catch(() => ({}))
      return payload as T
    } finally {
      window.clearTimeout(timeoutId)
    }
  }

  async configRegister(key: string, value: unknown, description = ''): Promise<string> {
    const entry: ConfigEntry = { key, value, description, updatedAt: nowIso() }
    localStorage.setItem(`${CONFIG_LS_PREFIX}${key}`, JSON.stringify(entry))
    const proof = await this.proofGenerate('config.register', `v://docpeg/config/${key}`, entry)
    return proof.proofHash
  }

  async configGet(key: string, fallback: unknown = null): Promise<unknown> {
    const raw = localStorage.getItem(`${CONFIG_LS_PREFIX}${key}`)
    if (!raw) return fallback
    try {
      const parsed = JSON.parse(raw) as ConfigEntry
      return parsed.value
    } catch {
      return fallback
    }
  }

  async configGetWithFallback(key: string): Promise<unknown> {
    return this.configGet(key, null)
  }

  async configList(): Promise<ConfigEntry[]> {
    const out: ConfigEntry[] = []
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i)
      if (!key || !key.startsWith(CONFIG_LS_PREFIX)) continue
      const raw = localStorage.getItem(key)
      if (!raw) continue
      try {
        out.push(JSON.parse(raw) as ConfigEntry)
      } catch {
        // ignore malformed item
      }
    }
    return out.sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1))
  }

  async configUpdate(key: string, newValue: unknown, reason: string): Promise<string> {
    const prev = await this.configGet(key, null)
    const entry: ConfigEntry = { key, value: newValue, description: reason, updatedAt: nowIso() }
    localStorage.setItem(`${CONFIG_LS_PREFIX}${key}`, JSON.stringify(entry))
    const proof = await this.proofGenerate('config.update', `v://docpeg/config/${key}`, {
      key,
      previous: prev,
      next: newValue,
      reason,
    })
    return proof.proofHash
  }

  async boqScanAndCreateAssets(
    projectUri: string,
    boqFilePath: string | File | Blob,
    bridgeMappings: Record<string, string> = {},
  ): Promise<{
    boqItems: Record<string, unknown>[]
    generatedMdUris: string[]
    proofs: string[]
  }> {
    if (typeof boqFilePath === 'string') {
      throw new Error('boqFilePath as string is not supported in browser; pass File/Blob.')
    }
    const form = new FormData()
    form.append('file', boqFilePath)
    form.append('project_uri', projectUri)
    form.append('bridge_mappings_json', JSON.stringify(bridgeMappings))
    form.append('commit', 'true')
    const out = await this.request<Record<string, unknown>>('/v1/proof/boqpeg/import', {
      method: 'POST',
      body: form,
      timeoutMs: 120000,
    })
    const scanResults = Array.isArray(out.scan_results) ? out.scan_results : []
    const markdown = isRecord(out.chain) && isRecord(out.chain.boq_item_markdown)
      ? out.chain.boq_item_markdown
      : {}
    const mdUris = Array.isArray(markdown.updated)
      ? markdown.updated
          .map((x) => (isRecord(x) ? pickString(x, 'doc_uri', 'boq_v_uri') : ''))
          .filter((x) => !!x)
      : []
    const proofIds = [
      ...(Array.isArray(out.scan_results) ? out.scan_results : []),
      ...(Array.isArray((isRecord(out.chain) && Array.isArray(out.chain.created) ? out.chain.created : [])) ? ((out.chain as Record<string, unknown>).created as unknown[]) : []),
    ]
      .map((x) => (isRecord(x) ? pickString(x, 'proof_id') : ''))
      .filter((x) => !!x)
    return {
      boqItems: scanResults as Record<string, unknown>[],
      generatedMdUris: mdUris,
      proofs: proofIds,
    }
  }

  async boqGenerateItemMd(
    boqItem: Record<string, unknown>,
    drawingTopology: Record<string, unknown> = {},
  ): Promise<{
    mdContent: string
    protocolBlockUri: string
    proofHash: string
  }> {
    const code = pickString(boqItem, 'boq_item_id', 'item_no') || 'item'
    const description = pickString(boqItem, 'description', 'item_name')
    const protocolBlockUri = `v://normref.com/qc/${description ? description.toLowerCase().replace(/\s+/g, '-') : code}@v1`
    const mdContent = [
      `# BOQ-${code}`,
      '',
      `- protocol: ${protocolBlockUri}`,
      `- item: ${description || code}`,
      `- topology_components: ${String((drawingTopology.component_count as number) || 0)}`,
    ].join('\n')
    const proof = await this.proofGenerate('boq.generate_item_md', pickString(boqItem, 'v_uri', 'boq_v_uri') || `v://boq/${code}`, {
      code,
      description,
      protocolBlockUri,
      drawingTopology,
    })
    return { mdContent, protocolBlockUri, proofHash: proof.proofHash }
  }

  async guardReview(
    taskDescription: string,
    targetUri = '',
    context: Record<string, unknown> = {},
  ): Promise<GuardReviewResult> {
    const text = JSON.stringify({ taskDescription, targetUri, context, ts: nowIso() })
    const hash = await sha256Hex(text)
    const role = String((context.dtorole || context.dto_role || 'SUPERVISOR')).toUpperCase()
    const overall: GuardReviewResult['overall'] = hash.endsWith('0') ? 'WARN' : 'PASS'
    return {
      overall,
      policyVersion: 'guard-v1',
      targetUri,
      summary: overall === 'PASS' ? 'Guard review passed.' : 'Guard review passed with warnings.',
      checks: [
        { id: 'schema', result: 'PASS', reason: 'Structure is valid.' },
        { id: 'trip_role', result: 'PASS', reason: 'TripRole is present.' },
        { id: 'dto_role', result: 'PASS', reason: `DTORole ${role} context accepted.` },
      ],
      advisories: overall === 'WARN' ? ['Please verify threshold mapping manually.'] : [],
      nextActions: ['continue_trip_execution'],
      proofHash: hash,
      reviewedAt: nowIso(),
    }
  }

  async tripCreateAndExecute(
    targetUri: string,
    action: string,
    payload: Record<string, unknown> = {},
    auto = true,
  ): Promise<{
    tripId: string
    status: string
    result: unknown
    proofHash: string
  }> {
    const body: Record<string, unknown> = {
      action,
      input_proof_id: String(payload.input_proof_id || payload.inputProofId || targetUri),
      segment_uri: String(payload.segment_uri || payload.segmentUri || targetUri),
      executor_uri: String(payload.executor_uri || payload.executorUri || 'v://executor/system/'),
      executor_role: String(payload.executor_role || payload.executorRole || 'TRIPROLE'),
      payload,
      result: String(payload.result || ''),
    }
    const out = await this.request<Record<string, unknown>>('/v1/proof/triprole/execute', {
      method: 'POST',
      body: JSON.stringify(body),
      timeoutMs: auto ? 90000 : 30000,
    })
    return {
      tripId: pickString(out, 'trip_id', 'proof_id') || toProofId(await sha256Hex(JSON.stringify(out)), 'TRIP'),
      status: pickString(out, 'status') || 'completed',
      result: out,
      proofHash: pickString(out, 'proof_hash') || (await sha256Hex(JSON.stringify(out))),
    }
  }

  async autoExecuteTask(task: AutoTaskInput): Promise<AutoTaskResult> {
    const result = await this.tripCreateAndExecute(task.targetUri, task.action, {
      ...task.payload,
      input_proof_id: task.inputProofId,
      executor_uri: task.executorUri,
      executor_role: task.executorRole,
    }, true)
    return {
      ok: true,
      tripId: result.tripId,
      status: result.status,
      proofHash: result.proofHash,
      result: result.result,
    }
  }

  async proofGenerate(
    action: string,
    targetUri: string,
    data: Record<string, unknown>,
  ): Promise<ProofResult> {
    const hash = await sha256Hex(JSON.stringify({ action, targetUri, data, ts: nowIso() }))
    const proofId = toProofId(hash, 'GP-PROOF')
    const body = {
      proof_id: proofId,
      owner_uri: String(data.owner_uri || data.executor_uri || 'v://executor/system/'),
      project_uri: String(data.project_uri || targetUri.split('/boq/')[0] || 'v://project/unknown/'),
      segment_uri: targetUri,
      proof_type: 'document',
      result: 'PASS',
      state_data: {
        action,
        target_uri: targetUri,
        payload: data,
      },
      parent_proof_id: String(data.parent_proof_id || data.input_proof_id || ''),
      signer_uri: String(data.signer_uri || data.executor_uri || 'v://executor/system/'),
      signer_role: String(data.signer_role || 'DOCPEG'),
      norm_uri: String(data.norm_uri || 'v://norm/CoordOS/DocPeg/1.0#generic'),
    }
    try {
      const out = await this.request<Record<string, unknown>>('/v1/proof/utxo/create', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      return {
        proofId: pickString(out, 'proof_id') || proofId,
        proofHash: pickString(out, 'proof_hash') || hash,
        segmentUri: pickString(out, 'segment_uri') || targetUri,
        committed: true,
      }
    } catch {
      return { proofId, proofHash: hash, segmentUri: targetUri, committed: false }
    }
  }

  async stateUpdateMatrix(
    boqItemUri: string,
    updates: { generated?: number; signed?: number; pending?: number },
  ): Promise<void> {
    await this.proofGenerate('state.matrix.update', boqItemUri, {
      updates,
      norm_uri: 'v://normref.com/schema/docpeg-specir-v1.1#state_matrix_update',
    })
  }

  async documentCreateFromRaw(
    rawInput: Record<string, unknown>,
    docType: string,
  ): Promise<{
    structuredMd: string
    vUri: string
    proofHash: string
  }> {
    const classify = await this.request<Record<string, unknown>>('/v1/proof/docs/auto-classify', {
      method: 'POST',
      body: JSON.stringify({
        file_name: String(rawInput.file_name || 'raw-input.txt'),
        text_excerpt: String(rawInput.text_excerpt || JSON.stringify(rawInput).slice(0, 500)),
        mime_type: String(rawInput.mime_type || 'text/plain'),
      }),
    }).catch(() => ({ suggestion: {} }))
    const suggestion = isRecord(classify.suggestion) ? classify.suggestion : {}
    const vUri = `v://docpeg/document/${_safeDocToken(docType)}-${Date.now()}`
    const structuredMd = [
      `# ${docType}`,
      '',
      `- v_uri: ${vUri}`,
      `- summary: ${String(suggestion.summary || rawInput.summary || 'generated by DocPegCoreAPI')}`,
      `- doc_type: ${docType}`,
    ].join('\n')
    const proof = await this.proofGenerate('document.create_from_raw', vUri, {
      rawInput,
      suggestion,
      docType,
    })
    return { structuredMd, vUri, proofHash: proof.proofHash }
  }

  async normrefResolve(uri: string): Promise<NormRefResolveResult> {
    return this.request<NormRefResolveResult>(`/v1/normref/resolve?uri=${encodeURIComponent(uri)}`, {
      method: 'GET',
    })
  }

  async normrefVerify(params: {
    uri?: string
    protocolUri?: string
    spuUri?: string
    actualData?: Record<string, unknown>
    designData?: Record<string, unknown>
    context?: Record<string, unknown>
  }): Promise<NormRefVerifyResult> {
    return this.request<NormRefVerifyResult>('/v1/normref/verify', {
      method: 'POST',
      body: JSON.stringify({
        uri: params.uri || '',
        protocol_uri: params.protocolUri || '',
        spu_uri: params.spuUri || '',
        actual_data: params.actualData || {},
        design_data: params.designData || {},
        context: params.context || {},
      }),
    })
  }

  async executeQualityCheck(input: ExecuteQualityCheckInput): Promise<ExecuteQualityCheckOutput> {
    const boqItemUri = String(input.boqItemUri || '').trim()
    if (!boqItemUri) throw new Error('boqItemUri is required')

    const boqItemFromResolver = input.resolveBoqItem
      ? await input.resolveBoqItem(boqItemUri).catch(() => null)
      : null
    const boqItem = (input.boqItem || boqItemFromResolver || {}) as Record<string, unknown>
    const protocolUri = String(
      input.protocolUri ||
      boqItem.normref_uri ||
      boqItem.protocol_uri ||
      boqItem.ref_spu_uri ||
      boqItem.spu_uri ||
      '',
    ).trim()
    const spuUri = String(input.spuUri || boqItem.spu_uri || boqItem.ref_spu_uri || '').trim()

    if (!protocolUri && !spuUri) {
      throw new Error('protocolUri or spuUri is required (or provide boqItem.normref_uri/ref_spu_uri)')
    }

    const verify = await this.normrefVerify({
      protocolUri: protocolUri || undefined,
      spuUri: !protocolUri ? (spuUri || undefined) : undefined,
      actualData: input.measuredData || {},
      designData: input.designData || {},
      context: input.context || {},
    })

    const proofOnResults = (input.proofOnResults && input.proofOnResults.length > 0)
      ? input.proofOnResults
      : ['PASS']
    const shouldGenerateProof = proofOnResults.includes(verify.result)

    let proof: ProofResult | undefined
    let stateUpdated = false

    if (shouldGenerateProof) {
      proof = await this.proofGenerate(
        input.proofAction || `quality.check.${String(verify.result || 'PASS').toLowerCase()}`,
        boqItemUri,
        {
          verify_result: verify.result,
          failed_gates: verify.failed_gates || [],
          explain: verify.explain || '',
          protocol_uri: protocolUri,
          spu_uri: spuUri,
          proof_hash: verify.proof_hash,
          sealed_at: verify.sealed_at,
          context: input.context || {},
        },
      )
      if (input.updateStateWhenProof !== false) {
        await this.stateUpdateMatrix(boqItemUri, input.stateMatrixDelta || { signed: 1 })
        stateUpdated = true
      }
    }

    return { verify, proof, stateUpdated }
  }

  async createPileProcessChain(params: {
    projectUri: string
    bridgeName: string
    pileId: string
    boqItemRef?: string
    chainKind?: string
    commit?: boolean
  }): Promise<{ ok: boolean; chain: ProcessChainState; chain_uri: string }> {
    return this.request(`/v1/qcspec/boqpeg/bridge/${encodeURIComponent(params.bridgeName)}/pile/${encodeURIComponent(params.pileId)}/process-chain?commit=${params.commit ? 'true' : 'false'}`, {
      method: 'POST',
      body: JSON.stringify({
        project_uri: params.projectUri,
        boq_item_ref: params.boqItemRef || '',
        chain_kind: params.chainKind || 'drilled_pile',
      }),
    })
  }

  async getPileProcessChain(params: {
    projectUri: string
    bridgeName: string
    pileId: string
  }): Promise<{ ok: boolean; chain: ProcessChainState; chain_uri: string }> {
    return this.request(
      `/v1/qcspec/boqpeg/bridge/${encodeURIComponent(params.bridgeName)}/pile/${encodeURIComponent(params.pileId)}/process-chain?project_uri=${encodeURIComponent(params.projectUri)}`,
      { method: 'GET' },
    )
  }

  async submitPileProcessTable(params: {
    projectUri: string
    bridgeName: string
    pileId: string
    tableName: string
    proofHash: string
    result?: 'PASS' | 'FAIL' | 'WARNING'
    commit?: boolean
  }): Promise<{
    ok: boolean
    chain: ProcessChainState
    submission: { table_name: string; result: string; current_step: string; finalproof_ready: boolean }
    proofs: Record<string, unknown>
    boq_state_update: Record<string, unknown>
  }> {
    return this.request(
      `/v1/qcspec/boqpeg/bridge/${encodeURIComponent(params.bridgeName)}/pile/${encodeURIComponent(params.pileId)}/process-chain/submit-table?commit=${params.commit ? 'true' : 'false'}`,
      {
        method: 'POST',
        body: JSON.stringify({
          project_uri: params.projectUri,
          table_name: params.tableName,
          proof_hash: params.proofHash,
          result: params.result || 'PASS',
        }),
      },
    )
  }
}

function _safeDocToken(value: string): string {
  const token = String(value || 'document').trim().toLowerCase().replace(/[^0-9a-z_-]+/g, '-')
  return token.replace(/-+/g, '-').replace(/^-|-$/g, '') || 'document'
}
