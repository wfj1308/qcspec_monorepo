import { API_BASE, withAuthHeaders } from '../../hooks/api/base'

export type NormRefProtocol = {
  uri: string
  schemaUri?: string
  version?: string
  layers?: NormRefFiveLayers
  metadata?: Record<string, unknown>
  gates?: Array<Record<string, unknown>>
  logicInputs?: Array<Record<string, unknown>>
  stateMatrix?: Record<string, unknown>
  stateMatrixNormalized?: NormRefStateMatrix
  verdictLogic?: string | Record<string, unknown>
  outputSchema?: Record<string, unknown>
  raw?: Record<string, unknown>
}

export type NormRefStateMatrix = {
  componentCount: number
  formsPerComponent: number
  expectedQcTableCount: number
  generatedQcTableCount: number
  signedPassTableCount: number
  pendingQcTableCount: number
  totalQcTables: number
  total: number
  generated: number
  signed: number
  pending: number
}

export type NormRefFiveLayers = {
  header?: {
    doc_type?: string
    doc_id?: string
    v_uri?: string
    project_ref?: string
    version?: string
    created_at?: string
    jurisdiction?: string
  }
  gate?: {
    pre_conditions?: string[]
    entry_rules?: Array<Record<string, unknown>>
    required_trip_roles?: string[]
  }
  body?: {
    basic?: Record<string, unknown>
    test_data?: Array<Record<string, unknown>>
    relations?: string[]
  }
  proof?: {
    data_hash?: string
    proof_hash?: string
    signatures?: string[]
    witness_logs?: string[]
    timestamps?: Record<string, string>
  }
  state?: {
    lifecycle_stage?: string
    state_matrix?: Record<string, unknown>
    next_action?: string
    valid_until?: string
  }
}

export type NormRefVerifyInput = {
  protocolUri: string
  actualData: Record<string, unknown>
  designData?: Record<string, unknown>
  context?: Record<string, unknown>
}

export type NormRefVerifyOutput = {
  result: 'PASS' | 'FAIL' | 'WARNING'
  failedGates: string[]
  explain: string
  proofHash: string
  sealedAt: string
  raw?: Record<string, unknown>
}

export type NormRefRule = {
  ruleId: string
  version: string
  uri: string
  category: string
  hash: string
  scope?: string
  sourceStdCode?: string
  overrideApplied?: boolean
  raw?: Record<string, unknown>
}

export type NormRefGetRuleOutput = {
  ruleId: string
  requestedVersion: string
  resolvedVersion: string
  uri: string
  category: string
  hash: string
  rule: Record<string, unknown>
  raw?: Record<string, unknown>
}

export type NormRefListRulesOutput = {
  category: string
  requestedVersion: string
  count: number
  rules: NormRefRule[]
  raw?: Record<string, unknown>
}

export type NormRefValidateRulesInput = {
  rules: string[]
  data?: Record<string, unknown>
  normrefVersion?: string
  scope?: string
}

export type NormRefValidateRulesOutput = {
  requestedVersion: string
  requestedScope?: string
  passed: boolean
  failedRules: string[]
  results: Array<Record<string, unknown>>
  ruleSnapshots: Array<{ ruleId: string; version: string; hash: string }>
  normrefSnapshotHash: string
  raw?: Record<string, unknown>
}

export type NormRefRuleConflict = {
  ruleId: string
  version: string
  selectedUri: string
  selectedScope: string
  overrideApplied?: boolean
  candidateCount: number
  candidates: Array<{ uri: string; scope: string; sourceStdCode?: string; hash: string }>
  raw?: Record<string, unknown>
}

export type NormRefRuleConflictsOutput = {
  category: string
  requestedVersion: string
  requestedScope?: string
  count: number
  conflicts: NormRefRuleConflict[]
  raw?: Record<string, unknown>
}

export type NormRefRuleOverride = {
  ruleId: string
  version: string
  selectedUri: string
  reason: string
  updatedAt: string
  updatedBy: string
  raw?: Record<string, unknown>
}

export type NormRefIngestRuleCandidate = {
  candidateId: string
  jobId: string
  ruleId: string
  category: string
  fieldKey: string
  operator: string
  thresholdValue: string
  unit: string
  severity: string
  normRef: string
  sourceLine: string
  confidence: number
  status: 'pending' | 'approved' | 'rejected'
  notes: string
  raw?: Record<string, unknown>
}

export type NormRefIngestJob = {
  jobId: string
  stdCode: string
  title: string
  level: string
  fileName: string
  fileHash: string
  status: 'queued' | 'running' | 'review_required' | 'failed' | 'completed'
  createdAt: string
  updatedAt: string
  completedAt: string
  warnings: string[]
  sections: Array<Record<string, unknown>>
  candidates: NormRefIngestRuleCandidate[]
  sourceTextPreview: string
  raw?: Record<string, unknown>
}

export type NormRefIngestPublishOutput = {
  jobId: string
  versionTag: string
  publishedCount: number
  snapshotHash: string
  rules: Array<Record<string, unknown>>
  writeToDocs: boolean
  raw?: Record<string, unknown>
}

export type NormRefIngestCandidatePatchInput = {
  ruleId?: string
  category?: string
  fieldKey?: string
  operator?: string
  thresholdValue?: string
  unit?: string
  severity?: string
  normRef?: string
  sourceLine?: string
  notes?: string
}

type RequestOptions = {
  baseUrl?: string
  getToken?: () => string | null
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function pickString(source: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const n = Number(value.trim())
    if (Number.isFinite(n)) return n
  }
  return null
}

function pickNumber(source: Record<string, unknown>, ...keys: string[]): number | null {
  for (const key of keys) {
    const value = asNumber(source[key])
    if (value !== null) return value
  }
  return null
}

function normalizeStateMatrix(
  matrix: Record<string, unknown>,
  layers: NormRefFiveLayers | undefined,
): NormRefStateMatrix {
  const layerState = asRecord(layers?.state?.state_matrix)
  const merged = { ...layerState, ...matrix }

  const expected = pickNumber(merged, 'expected_qc_table_count', 'total_qc_tables', 'total') ?? 0
  const generated = pickNumber(merged, 'generated_qc_table_count', 'generated') ?? 0
  const signed = pickNumber(merged, 'signed_pass_table_count', 'signed') ?? 0
  const pending = pickNumber(merged, 'pending_qc_table_count', 'pending') ?? Math.max(expected - generated, 0)
  const total = pickNumber(merged, 'total', 'total_qc_tables', 'expected_qc_table_count') ?? expected

  return {
    componentCount: pickNumber(merged, 'component_count') ?? 0,
    formsPerComponent: pickNumber(merged, 'forms_per_component') ?? 0,
    expectedQcTableCount: expected,
    generatedQcTableCount: generated,
    signedPassTableCount: signed,
    pendingQcTableCount: pending,
    totalQcTables: pickNumber(merged, 'total_qc_tables') ?? total,
    total,
    generated: pickNumber(merged, 'generated') ?? generated,
    signed: pickNumber(merged, 'signed') ?? signed,
    pending: pickNumber(merged, 'pending') ?? pending,
  }
}

function normalizeIngestCandidate(source: Record<string, unknown>): NormRefIngestRuleCandidate {
  return {
    candidateId: pickString(source, 'candidate_id', 'candidateId'),
    jobId: pickString(source, 'job_id', 'jobId'),
    ruleId: pickString(source, 'rule_id', 'ruleId'),
    category: pickString(source, 'category'),
    fieldKey: pickString(source, 'field_key', 'fieldKey'),
    operator: pickString(source, 'operator') || 'eq',
    thresholdValue: pickString(source, 'threshold_value', 'thresholdValue'),
    unit: pickString(source, 'unit'),
    severity: pickString(source, 'severity') || 'mandatory',
    normRef: pickString(source, 'norm_ref', 'normRef'),
    sourceLine: pickString(source, 'source_line', 'sourceLine'),
    confidence: asNumber(source.confidence) ?? 0,
    status: (pickString(source, 'status') || 'pending') as 'pending' | 'approved' | 'rejected',
    notes: pickString(source, 'notes'),
    raw: source,
  }
}

function normalizeIngestJob(source: Record<string, unknown>): NormRefIngestJob {
  const candidates = Array.isArray(source.candidates)
    ? source.candidates.map((x) => normalizeIngestCandidate(asRecord(x)))
    : []
  return {
    jobId: pickString(source, 'job_id', 'jobId'),
    stdCode: pickString(source, 'std_code', 'stdCode'),
    title: pickString(source, 'title'),
    level: pickString(source, 'level'),
    fileName: pickString(source, 'file_name', 'fileName'),
    fileHash: pickString(source, 'file_hash', 'fileHash'),
    status: (pickString(source, 'status') || 'queued') as 'queued' | 'running' | 'review_required' | 'failed' | 'completed',
    createdAt: pickString(source, 'created_at', 'createdAt'),
    updatedAt: pickString(source, 'updated_at', 'updatedAt'),
    completedAt: pickString(source, 'completed_at', 'completedAt'),
    warnings: Array.isArray(source.warnings) ? source.warnings.map((x) => String(x || '')) : [],
    sections: Array.isArray(source.sections) ? source.sections.map((x) => asRecord(x)) : [],
    candidates,
    sourceTextPreview: pickString(source, 'source_text_preview', 'sourceTextPreview'),
    raw: source,
  }
}

export function createNormRefApi(options: RequestOptions = {}) {
  const baseUrl = (options.baseUrl || API_BASE || '').replace(/\/+$/, '')
  const getToken = options.getToken

  async function request<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
    const token = getToken ? getToken() : null
    const headers = withAuthHeaders(token || null, init.headers)
    if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }
    const response = await fetch(`${baseUrl}${path}`, { ...init, headers })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(String(asRecord(detail).detail || `HTTP ${response.status}`))
    }
    return (await response.json()) as T
  }

  function shouldRetryWithFallback(error: unknown): boolean {
    const message = String((error as Error)?.message || '')
    return /404|not found/i.test(message)
  }

  async function requestWithNormRefPrefixFallback<T = unknown>(
    path: string,
    init: RequestInit = {},
  ): Promise<T> {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    try {
      return await request<T>(`/v1/normref${normalizedPath}`, init)
    } catch (error) {
      if (!shouldRetryWithFallback(error)) throw error
      try {
        return await request<T>(`/api/normref${normalizedPath}`, init)
      } catch (fallbackError) {
        if (!shouldRetryWithFallback(fallbackError)) throw fallbackError
        return request<T>(`/v1/proof${normalizedPath}`, init)
      }
    }
  }

  return {
    async resolve(uri: string): Promise<NormRefProtocol> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(
        `/resolve?uri=${encodeURIComponent(uri)}`,
        { method: 'GET' },
      )
      const protocol = asRecord(payload.protocol)
      const layers = asRecord(protocol.layers) as NormRefFiveLayers
      const stateMatrix = asRecord(protocol.state_matrix)
      return {
        uri: pickString(payload, 'uri') || uri,
        schemaUri: pickString(payload, 'schema_uri') || pickString(protocol, 'schema_uri'),
        version: pickString(payload, 'version') || pickString(protocol, 'version'),
        layers,
        metadata: asRecord(protocol.metadata),
        gates: Array.isArray(protocol.gates) ? (protocol.gates as Array<Record<string, unknown>>) : [],
        logicInputs: Array.isArray(protocol.logic_inputs)
          ? (protocol.logic_inputs as Array<Record<string, unknown>>)
          : [],
        stateMatrix,
        stateMatrixNormalized: normalizeStateMatrix(stateMatrix, layers),
        verdictLogic: (protocol.verdict_logic as string | Record<string, unknown>) || {},
        outputSchema: asRecord(protocol.output_schema),
        raw: payload,
      }
    },

    async verify(input: NormRefVerifyInput): Promise<NormRefVerifyOutput> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>('/verify', {
        method: 'POST',
        body: JSON.stringify({
          protocol_uri: input.protocolUri,
          actual_data: input.actualData || {},
          design_data: input.designData || {},
          context: input.context || {},
        }),
      })
      return {
        result: (pickString(payload, 'result') || 'FAIL') as 'PASS' | 'FAIL' | 'WARNING',
        failedGates: Array.isArray(payload.failed_gates)
          ? (payload.failed_gates as unknown[]).map((x) => String(x || '')).filter((x) => !!x)
          : [],
        explain: pickString(payload, 'explain'),
        proofHash: pickString(payload, 'proof_hash'),
        sealedAt: pickString(payload, 'sealed_at'),
        raw: payload,
      }
    },

    async getRule(ruleId: string, version = 'latest', scope = ''): Promise<NormRefGetRuleOutput> {
      const scopeQuery = scope ? `&scope=${encodeURIComponent(scope)}` : ''
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(
        `/rules/${encodeURIComponent(ruleId)}?version=${encodeURIComponent(version)}${scopeQuery}`,
        { method: 'GET' },
      )
      return {
        ruleId: pickString(payload, 'rule_id') || ruleId,
        requestedVersion: pickString(payload, 'requested_version') || version,
        resolvedVersion: pickString(payload, 'resolved_version'),
        uri: pickString(payload, 'uri'),
        category: pickString(payload, 'category'),
        hash: pickString(payload, 'hash'),
        rule: asRecord(payload.rule),
        raw: payload,
      }
    },

    async listRules(category = '', version = 'latest', options?: { refresh?: boolean; scope?: string }): Promise<NormRefListRulesOutput> {
      const refresh = options?.refresh ? '&refresh=true' : ''
      const scope = options?.scope ? `&scope=${encodeURIComponent(options.scope)}` : ''
      const q = `category=${encodeURIComponent(category)}&version=${encodeURIComponent(version)}${scope}${refresh}`
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(`/rules?${q}`, { method: 'GET' })
      const rules = Array.isArray(payload.rules)
        ? payload.rules
            .map((item) => asRecord(item))
            .map(
              (item): NormRefRule => ({
                ruleId: pickString(item, 'rule_id'),
                version: pickString(item, 'version'),
                uri: pickString(item, 'uri'),
                category: pickString(item, 'category'),
                hash: pickString(item, 'hash'),
                scope: pickString(item, 'scope'),
                sourceStdCode: pickString(item, 'source_std_code', 'sourceStdCode'),
                overrideApplied: Boolean(item.override_applied),
                raw: item,
              }),
            )
            .filter((item) => !!item.ruleId)
        : []
      return {
        category: pickString(payload, 'category') || category,
        requestedVersion: pickString(payload, 'requested_version') || version,
        count: asNumber(payload.count) ?? rules.length,
        rules,
        raw: payload,
      }
    },

    async validateRules(input: NormRefValidateRulesInput): Promise<NormRefValidateRulesOutput> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>('/validate', {
        method: 'POST',
        body: JSON.stringify({
          rules: Array.isArray(input.rules) ? input.rules : [],
          data: input.data || {},
          normref_version: input.normrefVersion || 'latest',
          scope: input.scope || '',
        }),
      })
      const failedRules = Array.isArray(payload.failed_rules)
        ? payload.failed_rules.map((x) => String(x || '')).filter((x) => !!x)
        : []
      const ruleSnapshots = Array.isArray(payload.rule_snapshots)
        ? payload.rule_snapshots
            .map((x) => asRecord(x))
            .map((x) => ({
              ruleId: pickString(x, 'rule_id'),
              version: pickString(x, 'version'),
              hash: pickString(x, 'hash'),
            }))
            .filter((x) => !!x.ruleId)
        : []
      return {
        requestedVersion: pickString(payload, 'requested_version') || (input.normrefVersion || 'latest'),
        requestedScope: pickString(payload, 'requested_scope'),
        passed: Boolean(payload.passed),
        failedRules,
        results: Array.isArray(payload.results) ? payload.results.map((x) => asRecord(x)) : [],
        ruleSnapshots,
        normrefSnapshotHash: pickString(payload, 'normref_snapshot_hash'),
        raw: payload,
      }
    },

    async listRuleConflicts(
      category = '',
      version = 'latest',
      scope = '',
    ): Promise<NormRefRuleConflictsOutput> {
      const q = `category=${encodeURIComponent(category)}&version=${encodeURIComponent(version)}&scope=${encodeURIComponent(scope)}`
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(`/rules-conflicts?${q}`, { method: 'GET' })
      const conflicts = Array.isArray(payload.conflicts)
        ? payload.conflicts.map((x) => asRecord(x)).map((item): NormRefRuleConflict => ({
            ruleId: pickString(item, 'rule_id', 'ruleId'),
            version: pickString(item, 'version'),
            selectedUri: pickString(item, 'selected_uri', 'selectedUri'),
            selectedScope: pickString(item, 'selected_scope', 'selectedScope'),
            overrideApplied: Boolean(item.override_applied),
            candidateCount: asNumber(item.candidate_count) ?? 0,
            candidates: Array.isArray(item.candidates)
              ? item.candidates.map((c) => asRecord(c)).map((c) => ({
                  uri: pickString(c, 'uri'),
                  scope: pickString(c, 'scope'),
                  sourceStdCode: pickString(c, 'source_std_code', 'sourceStdCode'),
                  hash: pickString(c, 'hash'),
                }))
              : [],
            raw: item,
          }))
        : []
      return {
        category: pickString(payload, 'category') || category,
        requestedVersion: pickString(payload, 'requested_version') || version,
        requestedScope: pickString(payload, 'requested_scope'),
        count: asNumber(payload.count) ?? conflicts.length,
        conflicts,
        raw: payload,
      }
    },

    async listRuleOverrides(): Promise<{ count: number; overrides: NormRefRuleOverride[]; raw?: Record<string, unknown> }> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>('/rules-overrides', { method: 'GET' })
      const rows = Array.isArray(payload.overrides)
        ? payload.overrides.map((x) => asRecord(x)).map((x): NormRefRuleOverride => ({
            ruleId: pickString(x, 'rule_id', 'ruleId'),
            version: pickString(x, 'version'),
            selectedUri: pickString(x, 'selected_uri', 'selectedUri'),
            reason: pickString(x, 'reason'),
            updatedAt: pickString(x, 'updated_at', 'updatedAt'),
            updatedBy: pickString(x, 'updated_by', 'updatedBy'),
            raw: x,
          }))
        : []
      return { count: asNumber(payload.count) ?? rows.length, overrides: rows, raw: payload }
    },

    async setRuleOverride(input: { ruleId: string; version: string; selectedUri: string; reason?: string; updatedBy?: string }): Promise<NormRefRuleOverride> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>('/rules-overrides/set', {
        method: 'POST',
        body: JSON.stringify({
          rule_id: input.ruleId,
          version: input.version,
          selected_uri: input.selectedUri,
          reason: input.reason || '',
          updated_by: input.updatedBy || '',
        }),
      })
      const x = asRecord(payload.override)
      return {
        ruleId: pickString(x, 'rule_id', 'ruleId'),
        version: pickString(x, 'version'),
        selectedUri: pickString(x, 'selected_uri', 'selectedUri'),
        reason: pickString(x, 'reason'),
        updatedAt: pickString(x, 'updated_at', 'updatedAt'),
        updatedBy: pickString(x, 'updated_by', 'updatedBy'),
        raw: x,
      }
    },

    async clearRuleOverride(ruleId: string, version: string): Promise<{ removed: boolean; raw?: Record<string, unknown> }> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>('/rules-overrides/clear', {
        method: 'POST',
        body: JSON.stringify({ rule_id: ruleId, version }),
      })
      return { removed: Boolean(payload.removed), raw: payload }
    },

    async ingestUpload(
      file: File,
      stdCode: string,
      title = '',
      level = 'industry',
      options?: { asyncMode?: boolean },
    ): Promise<NormRefIngestJob> {
      const form = new FormData()
      form.append('file', file)
      form.append('std_code', stdCode)
      form.append('title', title)
      form.append('level', level)
      form.append('async_mode', options?.asyncMode ? 'true' : 'false')
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>('/ingest/upload', {
        method: 'POST',
        body: form,
      })
      return normalizeIngestJob(asRecord(payload.job))
    },

    async ingestGetJob(jobId: string): Promise<NormRefIngestJob> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(
        `/ingest/jobs/${encodeURIComponent(jobId)}`,
        { method: 'GET' },
      )
      return normalizeIngestJob(asRecord(payload.job))
    },

    async ingestListCandidates(jobId: string, status = ''): Promise<NormRefIngestRuleCandidate[]> {
      const q = status ? `?status=${encodeURIComponent(status)}` : ''
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(
        `/ingest/jobs/${encodeURIComponent(jobId)}/candidates${q}`,
        { method: 'GET' },
      )
      const rows = Array.isArray(payload.candidates) ? payload.candidates : []
      return rows.map((x) => normalizeIngestCandidate(asRecord(x)))
    },

    async ingestSetCandidateStatus(
      candidateId: string,
      jobId: string,
      status: 'approved' | 'rejected',
    ): Promise<NormRefIngestRuleCandidate> {
      const action = status === 'approved' ? 'approve' : 'reject'
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(
        `/ingest/candidates/${encodeURIComponent(candidateId)}/${action}`,
        {
          method: 'POST',
          body: JSON.stringify({ job_id: jobId }),
        },
      )
      return normalizeIngestCandidate(asRecord(payload.candidate))
    },

    async ingestPatchCandidate(
      candidateId: string,
      jobId: string,
      patch: NormRefIngestCandidatePatchInput,
    ): Promise<NormRefIngestRuleCandidate> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>(
        `/ingest/candidates/${encodeURIComponent(candidateId)}/patch`,
        {
          method: 'POST',
          body: JSON.stringify({
            job_id: jobId,
            patch: {
              rule_id: patch.ruleId,
              category: patch.category,
              field_key: patch.fieldKey,
              operator: patch.operator,
              threshold_value: patch.thresholdValue,
              unit: patch.unit,
              severity: patch.severity,
              norm_ref: patch.normRef,
              source_line: patch.sourceLine,
              notes: patch.notes,
            },
          }),
        },
      )
      return normalizeIngestCandidate(asRecord(payload.candidate))
    },

    async ingestPublish(input: {
      jobId: string
      candidateIds?: string[]
      versionTag?: string
      writeToDocs?: boolean
    }): Promise<NormRefIngestPublishOutput> {
      const payload = await requestWithNormRefPrefixFallback<Record<string, unknown>>('/ingest/publish', {
        method: 'POST',
        body: JSON.stringify({
          job_id: input.jobId,
          candidate_ids: Array.isArray(input.candidateIds) ? input.candidateIds : [],
          version_tag: input.versionTag || 'latest',
          write_to_docs: Boolean(input.writeToDocs),
        }),
      })
      return {
        jobId: pickString(payload, 'job_id', 'jobId'),
        versionTag: pickString(payload, 'version_tag', 'versionTag'),
        publishedCount: asNumber(payload.published_count) ?? 0,
        snapshotHash: pickString(payload, 'snapshot_hash', 'snapshotHash'),
        rules: Array.isArray(payload.rules) ? payload.rules.map((x) => asRecord(x)) : [],
        writeToDocs: Boolean(payload.write_to_docs),
        raw: payload,
      }
    },
  }
}

export const normrefApi = createNormRefApi()
