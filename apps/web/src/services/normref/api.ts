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

  return {
    async resolve(uri: string): Promise<NormRefProtocol> {
      const payload = await request<Record<string, unknown>>(
        `/v1/normref/resolve?uri=${encodeURIComponent(uri)}`,
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
      const payload = await request<Record<string, unknown>>('/v1/normref/verify', {
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
  }
}

export const normrefApi = createNormRefApi()
