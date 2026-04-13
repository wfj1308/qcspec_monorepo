import { useCallback } from 'react'
import type { Project } from '@qcspec/types'
import { useUIStore } from '../../store'
import { useRequest } from './base'
import { useQCSpecDocPegApi } from './qcspecDocpeg'

type ProjectLike = Record<string, unknown>

type ListParams = {
  status?: string
  type?: string
}

const PROJECT_TYPE_ALIAS: Record<string, string> = {
  highway: 'highway',
  h: 'highway',
  h_highway: 'highway',
  road: 'road',
  urban: 'urban',
  bridge: 'bridge',
  bridge_repair: 'bridge_repair',
  bridgerepair: 'bridge_repair',
  tunnel: 'tunnel',
  municipal: 'municipal',
  water: 'water',
}

function normalizeStatus(input: unknown): Project['status'] {
  const value = String(input || '').trim().toLowerCase()
  if (value === 'pending' || value === 'closed' || value === 'active') return value
  return 'active'
}

function normalizeProjectType(input: unknown): string {
  const raw = String(input || '').trim()
  if (!raw) return 'highway'
  const normalized = raw.toLowerCase().replace(/[\s-]+/g, '_')
  if (PROJECT_TYPE_ALIAS[normalized]) return PROJECT_TYPE_ALIAS[normalized]
  if (/^h\s*highway$/i.test(raw)) return 'highway'
  return normalized
}

function toNumber(input: unknown, fallback = 0): number {
  const n = Number(input)
  return Number.isFinite(n) ? n : fallback
}

function extractProjectItems(payload: unknown): ProjectLike[] {
  if (!payload || typeof payload !== 'object') return []
  const root = payload as Record<string, unknown>

  if (Array.isArray(root.items)) return root.items as ProjectLike[]
  if (Array.isArray(root.data)) return root.data as ProjectLike[]
  if (Array.isArray(root.projects)) return root.projects as ProjectLike[]

  if (root.data && typeof root.data === 'object') {
    const nested = root.data as Record<string, unknown>
    if (Array.isArray(nested.items)) return nested.items as ProjectLike[]
    if (Array.isArray(nested.data)) return nested.data as ProjectLike[]
    if (Array.isArray(nested.projects)) return nested.projects as ProjectLike[]
  }

  return []
}

function extractTotal(payload: unknown, fallback: number): number {
  if (!payload || typeof payload !== 'object') return fallback
  const root = payload as Record<string, unknown>

  const directTotal = Number(root.total)
  if (Number.isFinite(directTotal)) return directTotal

  if (root.data && typeof root.data === 'object') {
    const nested = root.data as Record<string, unknown>
    const nestedTotal = Number(nested.total)
    if (Number.isFinite(nestedTotal)) return nestedTotal
  }

  return fallback
}

function unwrapProject(raw: ProjectLike): ProjectLike {
  const nested = raw.project
  if (!nested || typeof nested !== 'object' || Array.isArray(nested)) return raw

  const project = nested as ProjectLike
  return {
    ...raw,
    ...project,
    v_uri: project.v_uri || project.uri || raw.v_uri || raw.uri,
    owner_unit:
      project.ownerOrg ||
      raw.ownerOrg ||
      project.owner_unit ||
      raw.owner_unit ||
      raw.owner ||
      raw.clientOrg ||
      raw.contractorOrg,
    record_count: project.record_count ?? raw.record_count,
    proof_count: project.proof_count ?? raw.proof_count,
    photo_count: project.photo_count ?? raw.photo_count,
  }
}

function mapDocpegProject(raw: ProjectLike, enterpriseId?: string): Project | null {
  const source = unwrapProject(raw)
  const id = String(source.id || source.project_id || source.code || '').trim()
  if (!id) return null

  const name = String(source.name || id).trim() || id
  const ownerUnit = String(
    source.ownerOrg ||
      source.owner_unit ||
      source.owner ||
      source.clientOrg ||
      source.contractorOrg ||
      '',
  ).trim() || '待补充'
  const kmIntervalRaw = Number(source.km_interval)
  const descriptionText = String(source.description || '').trim()
  const hasRecordStats =
    source.record_count !== undefined ||
    source.photo_count !== undefined ||
    source.proof_count !== undefined
  const lastUpdatedAt = String(
    source.last_updated_at || source.lastUpdatedAt || source.updated_at || '',
  ).trim()

  const ownerOrg = String(source.ownerOrg || '').trim()
  const ownerOrgUri = String(source.ownerOrgUri || '').trim()
  const clientOrg = String(source.clientOrg || '').trim()
  const clientOrgUri = String(source.clientOrgUri || '').trim()
  const designerOrg = String(source.designerOrg || '').trim()
  const designerOrgUri = String(source.designerOrgUri || '').trim()
  const contractorOrg = String(source.contractorOrg || '').trim()
  const contractorOrgUri = String(source.contractorOrgUri || '').trim()
  const supervisorOrg = String(source.supervisorOrg || '').trim()
  const supervisorOrgUri = String(source.supervisorOrgUri || '').trim()
  const projectCode = String(source.code || '').trim()
  const projectUri = String(source.uri || '').trim()

  const mapped: Project & Record<string, unknown> = {
    id,
    enterprise_id: String(source.enterprise_id || enterpriseId || '').trim(),
    v_uri: String(source.v_uri || source.uri || `v://cn.project/${id}`).trim(),
    name,
    erp_project_code: String(source.erp_project_code || source.code || '').trim() || undefined,
    erp_project_name: String(source.erp_project_name || '').trim() || undefined,
    type: normalizeProjectType(source.type || source.project_type || source.projectType),
    owner_unit: ownerUnit,
    contractor: String(source.contractor || source.contractorOrg || '').trim() || undefined,
    supervisor: String(source.supervisor || source.supervisorOrg || '').trim() || undefined,
    contract_no: String(source.contract_no || '').trim() || undefined,
    start_date: String(source.start_date || '').trim() || undefined,
    end_date: String(source.end_date || '').trim() || undefined,
    description: descriptionText || undefined,
    seg_type: String(source.seg_type || '').trim() || undefined,
    seg_start: String(source.seg_start || '').trim() || undefined,
    seg_end: String(source.seg_end || '').trim() || undefined,
    perm_template: String(source.perm_template || '').trim() || undefined,
    km_interval: Number.isFinite(kmIntervalRaw) ? kmIntervalRaw : undefined,
    inspection_types: Array.isArray(source.inspection_types) ? (source.inspection_types as string[]) : undefined,
    contract_segs: Array.isArray(source.contract_segs) ? (source.contract_segs as Project['contract_segs']) : undefined,
    structures: Array.isArray(source.structures) ? (source.structures as Project['structures']) : undefined,
    zero_personnel: Array.isArray(source.zero_personnel) ? (source.zero_personnel as Project['zero_personnel']) : undefined,
    zero_equipment: Array.isArray(source.zero_equipment) ? (source.zero_equipment as Project['zero_equipment']) : undefined,
    zero_subcontracts: Array.isArray(source.zero_subcontracts) ? (source.zero_subcontracts as Project['zero_subcontracts']) : undefined,
    zero_materials: Array.isArray(source.zero_materials) ? (source.zero_materials as Project['zero_materials']) : undefined,
    zero_sign_status: String(source.zero_sign_status || '').trim() || undefined,
    qc_ledger_unlocked: Boolean(source.qc_ledger_unlocked),
    status: normalizeStatus(source.status),
    record_count: toNumber(source.record_count, 0),
    photo_count: toNumber(source.photo_count, 0),
    proof_count: toNumber(source.proof_count, 0),
  }

  if (ownerOrg) mapped.owner_org = ownerOrg
  if (ownerOrgUri) mapped.owner_org_uri = ownerOrgUri
  if (clientOrg) mapped.client_org = clientOrg
  if (clientOrgUri) mapped.client_org_uri = clientOrgUri
  if (designerOrg) mapped.designer_org = designerOrg
  if (designerOrgUri) mapped.designer_org_uri = designerOrgUri
  if (contractorOrg) mapped.contractor_org = contractorOrg
  if (contractorOrgUri) mapped.contractor_org_uri = contractorOrgUri
  if (supervisorOrg) mapped.supervisor_org = supervisorOrg
  if (supervisorOrgUri) mapped.supervisor_org_uri = supervisorOrgUri
  if (projectCode) mapped.code = projectCode
  if (projectUri) mapped.uri = projectUri
  if (lastUpdatedAt) mapped.last_updated_at = lastUpdatedAt
  mapped.has_record_stats = hasRecordStats

  return mapped
}

function buildProjectId(seed: string): string {
  const normalized = seed.toUpperCase().replace(/[^A-Z0-9]+/g, '').slice(0, 10)
  const stamp = Date.now().toString().slice(-8)
  return `PJT-${normalized || 'AUTO'}${stamp}`
}

function normalizeProjectId(input: unknown, fallbackSeed: string): string {
  const text = String(input || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

  if (!text) return buildProjectId(fallbackSeed)
  return text.startsWith('PJT-') ? text : `PJT-${text}`
}

export function useProjects() {
  const { loading } = useRequest()
  const showToast = useUIStore((s) => s.showToast)

  const {
    listProjects: listDocpegProjects,
    createProject: createDocpegProject,
    getProject: getDocpegProject,
  } = useQCSpecDocPegApi()

  const unsupported = useCallback((feature: string) => {
    showToast(`[Info] ${feature} 暂未接入同事 API`)
  }, [showToast])

  const list = useCallback(async (
    enterprise_id: string,
    params: ListParams = {},
  ) => {
    const payload = await listDocpegProjects({
      ...(params.status ? { status: params.status } : {}),
      ...(params.type ? { type: params.type } : {}),
    })

    const mappedItems = extractProjectItems(payload)
      .map((item) => mapDocpegProject(item, enterprise_id))
      .filter((item): item is Project => Boolean(item && item.id))

    return {
      ok: true,
      data: mappedItems,
      total: extractTotal(payload, mappedItems.length),
    }
  }, [listDocpegProjects])

  const create = useCallback(async (body: Record<string, unknown>) => {
    const name = String(body.name || body.project_name || '').trim()
    if (!name) {
      showToast('[Error] 项目名称不能为空')
      return null
    }

    const projectIdInput = String(
      body.project_id || body.project_code || body.code || body.id || body.erp_project_code || name,
    ).trim()

    const project_id = normalizeProjectId(projectIdInput, name)
    const type = String(body.type || '').trim()
    const ownerUnit = String(body.owner_unit || body.ownerUnit || '').trim()
    const description = String(body.description || '').trim()
    const idempotencyKey = String(body.idempotency_key || body.request_id || '').trim() || `${project_id}-${Date.now()}`

    const createPayload: {
      project_id: string
      name: string
      type?: string
      owner_unit?: string
      description?: string
    } = {
      project_id,
      name,
      ...(type ? { type } : {}),
      ...(ownerUnit ? { owner_unit: ownerUnit } : {}),
      ...(description ? { description } : {}),
    }

    const payload = await createDocpegProject(createPayload, { idempotencyKey }) as { project?: ProjectLike } | null
    const projectRaw = payload?.project
    if (!projectRaw || typeof projectRaw !== 'object') return null

    const enterprise_id = String(body.enterprise_id || '').trim()
    const mergedRaw = { ...createPayload, ...projectRaw }
    const mapped = mapDocpegProject(mergedRaw, enterprise_id)
    if (!mapped) return null

    return { ok: true, data: mapped, project: mapped }
  }, [createDocpegProject, showToast])

  const getById = useCallback(async (project_id: string) => {
    const payload = await getDocpegProject(project_id) as { project?: ProjectLike } | ProjectLike | null

    const raw = (payload && typeof payload === 'object' && 'project' in payload)
      ? (payload.project as ProjectLike)
      : (payload as ProjectLike | null)

    if (!raw || typeof raw !== 'object') return null
    return mapDocpegProject(raw)
  }, [getDocpegProject])

  const update = useCallback(async (project_id: string, _body: Record<string, unknown>) => {
    unsupported('项目编辑同步')
    return { id: project_id, ok: false, unsupported: true }
  }, [unsupported])

  const remove = useCallback(async (_project_id: string, _enterprise_id?: string) => {
    unsupported('项目删除')
    return { ok: false, unsupported: true }
  }, [unsupported])

  const completeGitpeg = useCallback(async (
    _project_id: string,
    _body: {
      code: string
      registration_id?: string
      session_id?: string
      enterprise_id?: string
    },
  ) => {
    unsupported('GitPeg 回调激活')
    return { ok: false, unsupported: true }
  }, [unsupported])

  const listActivity = useCallback(async (_enterprise_id: string, _limit = 12) => {
    return { ok: true, data: [] as Array<{ dot?: string; text?: string; created_at?: string }> }
  }, [])

  const exportCsv = useCallback(async (enterprise_id: string) => {
    const listed = await list(enterprise_id)
    const rows = listed.data || []
    const lines = [
      'project_id,name,type,status,owner_unit,v_uri',
      ...rows.map((row) => [
        row.id,
        row.name || '',
        row.type || '',
        row.status || '',
        row.owner_unit || '',
        row.v_uri || '',
      ].map((cell) => `"${String(cell || '').replace(/"/g, '""')}"`).join(',')),
    ]
    return new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  }, [list])

  return {
    list,
    create,
    update,
    getById,
    remove,
    completeGitpeg,
    listActivity,
    exportCsv,
    loading,
  }
}
