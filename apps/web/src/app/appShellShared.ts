/** Shared types, constants, and pure helpers extracted from App.tsx */

export const NAV = [
  { key: 'projects', icon: 'P', label: '项目' },
  { key: 'inspection', icon: 'I', label: '开始质检' },
  { key: 'reports', icon: 'R', label: '生成报告' },
  { key: 'proof', icon: 'V', label: 'Proof 存证' },
  { key: 'team', icon: 'T', label: '团队管理' },
  { key: 'permissions', icon: 'D', label: 'DTO 权限' },
  { key: 'settings', icon: 'S', label: '系统设置' },
]

export const NAV_SECTIONS: Array<{ label: string; keys: string[] }> = [
  { label: '主导航', keys: ['projects', 'inspection', 'reports', 'proof'] },
  { label: '管理中心', keys: ['team', 'permissions', 'settings'] },
]

export type TeamRole = 'OWNER' | 'SUPERVISOR' | 'AI' | 'PUBLIC'
export type PermissionRole = TeamRole | 'REGULATOR' | 'MARKET'
export type PermissionKey = 'view' | 'input' | 'approve' | 'manage' | 'settle' | 'regulator'
export type ZeroLedgerTab = 'personnel' | 'equipment' | 'subcontract' | 'materials'

export const ROLE_NAV_KEYS: Record<TeamRole, string[]> = {
  AI: ['projects', 'inspection', 'reports', 'proof'],
  SUPERVISOR: ['projects', 'inspection', 'reports', 'proof', 'permissions'],
  OWNER: ['projects', 'inspection', 'reports', 'proof', 'team', 'permissions', 'settings'],
  PUBLIC: ['projects', 'reports', 'proof'],
}

export const normalizeTeamRole = (value: unknown, fallback: TeamRole = 'AI'): TeamRole => {
  const role = String(value || '').toUpperCase()
  if (role === 'OWNER' || role === 'SUPERVISOR' || role === 'AI' || role === 'PUBLIC') {
    return role as TeamRole
  }
  return fallback
}

export const getAllowedNavKeysByRole = (role: unknown): string[] => {
  const normalizedRole = normalizeTeamRole(role, 'PUBLIC')
  return ROLE_NAV_KEYS[normalizedRole] || ROLE_NAV_KEYS.PUBLIC
}

export const resolveAllowedTab = (
  tab: string,
  allowedTabs: string[],
  fallbackTab = 'projects'
): string => {
  if (allowedTabs.includes(tab)) return tab
  if (allowedTabs.includes(fallbackTab)) return fallbackTab
  return allowedTabs[0] || fallbackTab
}

export type SegType = 'km' | 'contract' | 'structure'
export type PermTemplate = 'standard' | 'strict' | 'open' | 'custom'
export type InspectionTypeKey = 'flatness' | 'crack' | 'rut' | 'compaction' | 'settlement'

export interface ZeroPersonnelRow {
  id: string
  name: string
  title: string
  dtoRole: TeamRole
  certificate: string
}

export interface ZeroEquipmentRow {
  id: string
  name: string
  modelNo: string
  inspectionItem: string
  validUntil: string
}

export interface ZeroSubcontractRow {
  id: string
  unitName: string
  content: string
  range: string
}

export interface ZeroMaterialRow {
  id: string
  name: string
  spec: string
  supplier: string
  freq: string
}

export interface TeamMember {
  id: string
  name: string
  title: string
  email: string
  role: TeamRole
  color: string
  projects: string[]
}

export interface ProjectRegisterMeta {
  segType: SegType
  segStart: string
  segEnd: string
  kmInterval: number
  inspectionTypes: InspectionTypeKey[]
  contractSegs: { name: string; range: string }[]
  structures: { kind: string; name: string; code: string }[]
  zeroPersonnel: ZeroPersonnelRow[]
  zeroEquipment: ZeroEquipmentRow[]
  zeroSubcontracts: ZeroSubcontractRow[]
  zeroMaterials: ZeroMaterialRow[]
  zeroSignStatus: 'pending' | 'approved' | 'rejected'
  qcLedgerUnlocked: boolean
  permTemplate: PermTemplate
  memberCount: number
}

export interface PermissionRow {
  role: PermissionRole
  view: boolean
  input: boolean
  approve: boolean
  manage: boolean
  settle: boolean
  regulator: boolean
}

export interface SettingsState {
  emailNotify: boolean
  autoGenerateReport: boolean
  strictProof: boolean
  reportTemplate: string
  reportTemplateUrl?: string
  reportHeader: string
  webhookUrl: string
  gitpegToken: string
  gitpegEnabled: boolean
  gitpegRegistrarBaseUrl: string
  gitpegPartnerCode: string
  gitpegIndustryCode: string
  gitpegClientId: string
  gitpegClientSecret: string
  gitpegRegistrationMode: string
  gitpegReturnUrl: string
  gitpegWebhookUrl: string
  gitpegWebhookSecret: string
  gitpegModuleCandidates: string[]
  erpnextSync: boolean
  droneImport: boolean
}

export interface ErpDraftState {
  url: string
  siteName: string
  apiKey: string
  apiSecret: string
  username: string
  password: string
}

export interface ErpWritebackDraftState {
  projectDoctype: string
  projectLookupField: string
  projectLookupValue: string
  gitpegProjectUriField: string
  gitpegSiteUriField: string
  gitpegStatusField: string
  gitpegResultJsonField: string
  gitpegRegistrationIdField: string
  gitpegNodeUriField: string
  gitpegShellUriField: string
  gitpegProofHashField: string
  gitpegIndustryProfileIdField: string
}

export interface ProjectEditDraft {
  name: string
  type: string
  owner_unit: string
  contractor: string
  supervisor: string
  contract_no: string
  start_date: string
  end_date: string
  erp_project_code: string
  erp_project_name: string
}

export const TYPE_LABEL: Record<string, string> = {
  highway: '高速公路',
  road: '普通公路',
  urban: '城市道路',
  bridge: '桥梁',
  bridge_repair: '桥梁养护',
  tunnel: '隧道',
  municipal: '市政工程',
  water: '水利工程',
}

export const TYPE_ICON: Record<string, string> = {
  highway: '高',
  road: '路',
  urban: '城',
  bridge: '桥',
  bridge_repair: '养',
  tunnel: '隧',
  municipal: '市',
  water: '水',
}

export const PROJECT_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'highway', label: '高速公路' },
  { value: 'road', label: '普通公路' },
  { value: 'urban', label: '城市道路' },
  { value: 'bridge', label: '桥梁' },
  { value: 'bridge_repair', label: '桥梁养护' },
  { value: 'tunnel', label: '隧道' },
  { value: 'municipal', label: '市政工程' },
  { value: 'water', label: '水利工程' },
]

export const INSPECTION_TYPE_OPTIONS: Array<{ key: InspectionTypeKey; label: string }> = [
  { key: 'flatness', label: '平整度' },
  { key: 'crack', label: '裂缝宽度' },
  { key: 'rut', label: '车辙深度' },
  { key: 'compaction', label: '压实度' },
  { key: 'settlement', label: '沉降' },
]

export const INSPECTION_TYPE_LABEL: Record<InspectionTypeKey, string> = INSPECTION_TYPE_OPTIONS.reduce(
  (acc, item) => {
    acc[item.key] = item.label
    return acc
  },
  {} as Record<InspectionTypeKey, string>
)

export const ROLE_LABEL: Record<TeamRole, string> = {
  OWNER: 'OWNER',
  SUPERVISOR: 'SUPERVISOR',
  AI: 'AI',
  PUBLIC: 'PUBLIC',
}

export const roleToTitle = (role: TeamRole): string => {
  if (role === 'AI') return '质检员'
  if (role === 'SUPERVISOR') return '监理'
  if (role === 'OWNER') return '管理员'
  return '只读成员'
}

export const toRoleDraftMap = (rows: TeamMember[]): Record<string, TeamRole> =>
  rows.reduce<Record<string, TeamRole>>((acc, row) => {
    acc[row.id] = row.role
    return acc
  }, {})

export const PERMISSION_ROLE_LABEL: Record<PermissionRole, string> = {
  OWNER: 'OWNER',
  SUPERVISOR: 'SUPERVISOR',
  AI: 'AI',
  PUBLIC: 'PUBLIC',
  REGULATOR: 'REGULATOR',
  MARKET: 'MARKET',
}

export const PERMISSION_COLUMNS: Array<{ key: PermissionKey; label: string }> = [
  { key: 'view', label: '查看' },
  { key: 'input', label: '录入' },
  { key: 'approve', label: '审批' },
  { key: 'manage', label: '项目管理' },
  { key: 'settle', label: '计量结算' },
  { key: 'regulator', label: '监管查看' },
]

export const DEFAULT_PERMISSION_MATRIX: PermissionRow[] = [
  { role: 'OWNER', view: true, input: true, approve: true, manage: true, settle: true, regulator: true },
  { role: 'SUPERVISOR', view: true, input: true, approve: true, manage: false, settle: false, regulator: false },
  { role: 'AI', view: true, input: true, approve: false, manage: false, settle: false, regulator: false },
  { role: 'PUBLIC', view: true, input: false, approve: false, manage: false, settle: false, regulator: false },
  { role: 'REGULATOR', view: true, input: false, approve: false, manage: false, settle: false, regulator: true },
]

export const PERMISSION_TEMPLATES: Record<Exclude<PermTemplate, 'custom'>, PermissionRow[]> = {
  standard: DEFAULT_PERMISSION_MATRIX,
  strict: [
    { role: 'OWNER', view: true, input: true, approve: true, manage: true, settle: true, regulator: true },
    { role: 'SUPERVISOR', view: true, input: true, approve: true, manage: false, settle: false, regulator: false },
    { role: 'AI', view: true, input: true, approve: false, manage: false, settle: false, regulator: false },
    { role: 'PUBLIC', view: false, input: false, approve: false, manage: false, settle: false, regulator: false },
    { role: 'REGULATOR', view: true, input: false, approve: false, manage: false, settle: false, regulator: true },
  ],
  open: [
    { role: 'OWNER', view: true, input: true, approve: true, manage: true, settle: true, regulator: true },
    { role: 'SUPERVISOR', view: true, input: true, approve: true, manage: true, settle: true, regulator: false },
    { role: 'AI', view: true, input: true, approve: true, manage: false, settle: true, regulator: false },
    { role: 'PUBLIC', view: true, input: true, approve: false, manage: false, settle: false, regulator: false },
    { role: 'REGULATOR', view: true, input: false, approve: false, manage: false, settle: false, regulator: true },
  ],
}

export const clonePermissionRows = (rows: PermissionRow[]): PermissionRow[] => rows.map((row) => ({ ...row }))

export const normalizePermissionMatrix = (
  rows?: Array<Partial<PermissionRow> & { role?: string }>
): PermissionRow[] => {
  if (!rows || rows.length === 0) {
    return DEFAULT_PERMISSION_MATRIX.map((row) => ({ ...row }))
  }

  const validRoles: PermissionRole[] = ['OWNER', 'SUPERVISOR', 'AI', 'PUBLIC', 'REGULATOR', 'MARKET']
  const parsed = rows
    .map((row) => {
      const role = String(row.role || '').toUpperCase() as PermissionRole
      if (!validRoles.includes(role)) return null
      return {
        role,
        view: Boolean(row.view),
        input: Boolean(row.input),
        approve: Boolean(row.approve),
        manage: Boolean(row.manage),
        settle: Boolean(row.settle),
        regulator: Boolean(row.regulator),
      }
    })
    .filter((row): row is PermissionRow => row !== null)

  if (parsed.length === 0) {
    return DEFAULT_PERMISSION_MATRIX.map((row) => ({ ...row }))
  }

  const parsedByRole = new Map(parsed.map((row) => [row.role, row]))
  const merged = DEFAULT_PERMISSION_MATRIX.map((row) => {
    const override = parsedByRole.get(row.role)
    return override ? { ...row, ...override, role: row.role } : { ...row }
  })

  const market = parsedByRole.get('MARKET')
  if (market) merged.push(market)
  return merged
}

export const detectPermissionTemplate = (rows: PermissionRow[]): PermTemplate => {
  const templateNames: Exclude<PermTemplate, 'custom'>[] = ['standard', 'strict', 'open']
  const normalizeForCompare = (list: PermissionRow[]) => clonePermissionRows(list).sort((a, b) => a.role.localeCompare(b.role))

  for (const templateName of templateNames) {
    const templateRows = normalizeForCompare(PERMISSION_TEMPLATES[templateName])
    const inputRows = normalizeForCompare(rows)
    if (templateRows.length !== inputRows.length) continue

    const matched = templateRows.every((row, idx) => {
      const cur = inputRows[idx]
      return (
        row.role === cur.role &&
        row.view === cur.view &&
        row.input === cur.input &&
        row.approve === cur.approve &&
        row.manage === cur.manage &&
        row.settle === cur.settle &&
        row.regulator === cur.regulator
      )
    })
    if (matched) return templateName
  }

  return 'custom'
}

const INSPECTION_TYPE_KEYS = new Set<InspectionTypeKey>(INSPECTION_TYPE_OPTIONS.map((item) => item.key))

export const normalizeSegType = (value: unknown): SegType => {
  const text = String(value || '').toLowerCase()
  return text === 'contract' || text === 'structure' ? text : 'km'
}

export const normalizePermTemplate = (value: unknown): PermTemplate => {
  const text = String(value || '').toLowerCase()
  return text === 'strict' || text === 'open' || text === 'custom' ? text : 'standard'
}

export const normalizeKmInterval = (value: unknown, fallback = 20): number => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return Math.max(1, Math.min(500, Math.round(parsed)))
}

export const normalizeInspectionTypeKeys = (values: unknown): InspectionTypeKey[] => {
  if (!Array.isArray(values)) return []
  const out: InspectionTypeKey[] = []
  values.forEach((item) => {
    const key = String(item || '') as InspectionTypeKey
    if (INSPECTION_TYPE_KEYS.has(key) && !out.includes(key)) out.push(key)
  })
  return out
}

export const normalizeContractSegs = (values: unknown): Array<{ name: string; range: string }> => {
  if (!Array.isArray(values)) return []
  return values
    .filter((item): item is { name?: unknown; range?: unknown } => typeof item === 'object' && item !== null)
    .map((item) => ({
      name: String(item.name || '').trim(),
      range: String(item.range || '').trim(),
    }))
    .filter((item) => item.name || item.range)
}

export const normalizeStructures = (values: unknown): Array<{ kind: string; name: string; code: string }> => {
  if (!Array.isArray(values)) return []
  return values
    .filter((item): item is { kind?: unknown; name?: unknown; code?: unknown } => typeof item === 'object' && item !== null)
    .map((item) => ({
      kind: String(item.kind || '').trim(),
      name: String(item.name || '').trim(),
      code: String(item.code || '').trim(),
    }))
    .filter((item) => item.kind || item.name || item.code)
}

export const normalizeZeroPersonnelRows = (values: unknown): ZeroPersonnelRow[] => {
  if (!Array.isArray(values)) return []
  return values
    .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
    .map((item, idx) => ({
      id: String(item.id || `zp-${idx + 1}`),
      name: String(item.name || '').trim(),
      title: String(item.title || '').trim(),
      dtoRole: normalizeTeamRole(item.dto_role ?? item.dtoRole, 'AI'),
      certificate: String(item.certificate || '').trim(),
    }))
    .filter((item) => item.name || item.title || item.certificate)
}

export const normalizeZeroEquipmentRows = (values: unknown): ZeroEquipmentRow[] => {
  if (!Array.isArray(values)) return []
  return values
    .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
    .map((item, idx) => ({
      id: String(item.id || `ze-${idx + 1}`),
      name: String(item.name || '').trim(),
      modelNo: String(item.model_no ?? item.modelNo ?? '').trim(),
      inspectionItem: String(item.inspection_item ?? item.inspectionItem ?? '').trim(),
      validUntil: String(item.valid_until ?? item.validUntil ?? '').trim(),
    }))
    .filter((item) => item.name || item.modelNo || item.inspectionItem || item.validUntil)
}

export const normalizeZeroSubcontractRows = (values: unknown): ZeroSubcontractRow[] => {
  if (!Array.isArray(values)) return []
  return values
    .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
    .map((item, idx) => ({
      id: String(item.id || `zs-${idx + 1}`),
      unitName: String(item.unit_name ?? item.unitName ?? '').trim(),
      content: String(item.content || '').trim(),
      range: String(item.range || '').trim(),
    }))
    .filter((item) => item.unitName || item.content || item.range)
}

export const normalizeZeroMaterialRows = (values: unknown): ZeroMaterialRow[] => {
  if (!Array.isArray(values)) return []
  return values
    .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
    .map((item, idx) => ({
      id: String(item.id || `zm-${idx + 1}`),
      name: String(item.name || '').trim(),
      spec: String(item.spec || '').trim(),
      supplier: String(item.supplier || '').trim(),
      freq: String(item.freq || '').trim(),
    }))
    .filter((item) => item.name || item.spec || item.supplier || item.freq)
}

export const normalizeZeroSignStatus = (value: unknown): 'pending' | 'approved' | 'rejected' => {
  const v = String(value || '').toLowerCase()
  if (v === 'approved' || v === 'rejected') return v
  return 'pending'
}
