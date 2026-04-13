import { docpegHttpClient } from '../../services/docpeg/httpClient'
import type {
  ChainStatusResponse,
  DraftInstanceResponse,
  InterpretPreviewResponse,
  NormrefFormResponse,
  ProcessChainsResponse,
  ProofDetailsResponse,
  SubmitDraftResponse,
  TripHistoryResponse,
  TripSubmitResponse,
  WorkbenchEntitiesResponse,
} from './workbenchTypes'

function encode(input: string): string {
  return encodeURIComponent(String(input || '').trim())
}

async function withFallback<T>(runner: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await runner()
  } catch {
    return fallback
  }
}

const projectIdCache = new Map<string, string>()

type ProjectListRow = {
  id?: string
  project_id?: string
  code?: string
  project?: {
    id?: string
    project_id?: string
    code?: string
  }
}

function normalizeProjectKey(input: string): string {
  return String(input || '').trim().toUpperCase()
}

function readCanonicalProjectId(row: ProjectListRow): string {
  return String(row.project?.id || row.project?.project_id || row.id || row.project_id || '').trim()
}

function matchesProjectKey(row: ProjectListRow, key: string): boolean {
  const candidates = [
    row.id,
    row.project_id,
    row.code,
    row.project?.id,
    row.project?.project_id,
    row.project?.code,
  ]
  return candidates.some((value) => normalizeProjectKey(String(value || '')) === key)
}

async function resolveProjectPathId(projectId: string): Promise<string> {
  const raw = String(projectId || '').trim()
  if (!raw) return ''
  const key = normalizeProjectKey(raw)
  const cached = projectIdCache.get(key)
  if (cached) return cached

  try {
    const payload = await docpegHttpClient.get<{
      ok?: boolean
      items?: ProjectListRow[]
      data?: { items?: ProjectListRow[] }
    }>('/projects', {
      params: { q: raw, limit: 20, offset: 0 },
    })
    const rows = payload.items || payload.data?.items || []
    const hit = rows.find((row) => matchesProjectKey(row, key))
    const resolved = readCanonicalProjectId(hit || ({} as ProjectListRow)) || raw
    projectIdCache.set(key, resolved)
    return resolved
  } catch {
    return raw
  }
}

export const workbenchKeys = {
  entities: (projectId: string) => ['workbench', 'entities', projectId] as const,
  chains: (projectId: string) => ['workbench', 'chains', projectId] as const,
  chainStatus: (projectId: string, chainId: string, componentUri: string) =>
    ['workbench', 'chainStatus', projectId, chainId, componentUri] as const,
  form: (projectId: string, formCode: string) => ['workbench', 'form', projectId, formCode] as const,
  trips: (projectId: string, componentUri: string) => ['workbench', 'trips', projectId, componentUri] as const,
  proof: (proofId: string) => ['workbench', 'proof', proofId] as const,
}

export async function fetchWorkbenchEntities(projectId: string): Promise<WorkbenchEntitiesResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.get<WorkbenchEntitiesResponse>(`/projects/${encode(resolvedProjectId)}/entities`),
    { ok: true, items: [], total: 0 },
  )
}

export async function fetchProjectChains(projectId: string): Promise<ProcessChainsResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.get<ProcessChainsResponse>(`/projects/${encode(resolvedProjectId)}/process-chains`, {
      params: { source_mode: 'hybrid' },
    }),
    { ok: true, items: [] },
  )
}

export async function fetchChainStatus(
  projectId: string,
  chainId: string,
  componentUri: string,
): Promise<ChainStatusResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.get<ChainStatusResponse>(
      `/projects/${encode(resolvedProjectId)}/process-chains/${encode(chainId)}/status`,
      { params: { component_uri: componentUri } },
    ),
    {
      ok: true,
      chain_id: chainId,
      component_uri: componentUri,
      chain_state: 'unknown',
      current_step: '',
      complete: false,
      steps: [],
    },
  )
}

export async function fetchNormrefForm(
  projectId: string,
  formCode: string,
): Promise<NormrefFormResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.get<NormrefFormResponse>(
      `/api/v1/normref/projects/${encode(resolvedProjectId)}/forms/${encode(formCode)}`,
    ),
    {
      ok: true,
      form: {
        form_code: formCode,
        family: '',
        title: '',
        template: {},
        protocol_stub: {},
      },
    },
  )
}

export async function postInterpretPreview(
  projectId: string,
  formCode: string,
  payload: Record<string, unknown>,
): Promise<InterpretPreviewResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.post<InterpretPreviewResponse>(
      `/api/v1/normref/projects/${encode(resolvedProjectId)}/forms/${encode(formCode)}/interpret-preview`,
      payload,
    ),
    {
      ok: true,
      preview: {
        raw: {},
        normalized: {},
        derived: {},
        gate_check: {},
        proof_preview: {},
      },
    },
  )
}

export async function saveDraftInstance(
  projectId: string,
  formCode: string,
  payload: Record<string, unknown>,
): Promise<DraftInstanceResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.post<DraftInstanceResponse>(
      `/api/v1/normref/projects/${encode(resolvedProjectId)}/forms/${encode(formCode)}/draft-instances`,
      payload,
    ),
    {
      ok: true,
      instance_id: `DRAFT-LOCAL-${Date.now()}`,
      status: 'draft',
      updated_at: new Date().toISOString(),
    },
  )
}

export async function submitDraftInstance(
  projectId: string,
  formCode: string,
  instanceId: string,
  payload: Record<string, unknown>,
): Promise<SubmitDraftResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.post<SubmitDraftResponse>(
      `/api/v1/normref/projects/${encode(resolvedProjectId)}/forms/${encode(formCode)}/draft-instances/${encode(instanceId)}/submit`,
      payload,
    ),
    {
      ok: true,
      instance_id: instanceId,
      status: 'submitted',
      trip_id: '',
      proof_id: '',
    },
  )
}

export async function submitTripRole(
  payload: Record<string, unknown>,
): Promise<TripSubmitResponse> {
  return withFallback(
    () => docpegHttpClient.post<TripSubmitResponse>('/api/v1/triprole/submit', payload),
    {
      ok: true,
      trip_id: '',
      status: 'pending',
      proof_id: '',
      next_step: '',
    },
  )
}

export async function fetchTripHistory(
  projectId: string,
  componentUri: string,
): Promise<TripHistoryResponse> {
  const resolvedProjectId = await resolveProjectPathId(projectId)
  return withFallback(
    () => docpegHttpClient.get<TripHistoryResponse>('/api/v1/triprole/trips', {
      params: {
        project_id: resolvedProjectId,
        component_uri: componentUri,
      },
    }),
    {
      ok: true,
      items: [],
      total: 0,
    },
  )
}

export async function fetchProofDetails(proofId: string): Promise<ProofDetailsResponse> {
  return withFallback(
    () => docpegHttpClient.get<ProofDetailsResponse>(`/api/v1/proof/${encode(proofId)}`),
    {
      ok: true,
      proof: {
        proof_id: proofId,
        hash: '',
        signatures: [],
        snapshots: [],
        attachments: [],
        result: '',
        created_at: '',
      },
    },
  )
}
