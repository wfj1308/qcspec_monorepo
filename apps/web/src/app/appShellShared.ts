/** Shared types, constants, and pure helpers extracted from App.tsx */

export const DEMO_ENTERPRISE = {
  id: '11111111-1111-4111-8111-111111111111',
  v_uri: 'v://cn.zhongbei/',
  name: '中北工程设计咨询有限公司',
  short_name: '中北工程',
  plan: 'enterprise' as const,
  proof_quota: 99999,
  proof_used: 47,
}

export const DEMO_USER = {
  id: '22222222-2222-4222-8222-222222222222',
  enterprise_id: '11111111-1111-4111-8111-111111111111',
  v_uri: 'v://cn.zhongbei/executor/ligong/',
  name: '李总工',
  email: 'admin@zhongbei.com',
  dto_role: 'OWNER' as const,
  title: '总工程师',
}

export const DEMO_PROJECTS = [
  {
    id: '33333333-3333-4333-8333-333333333333',
    enterprise_id: '11111111-1111-4111-8111-111111111111',
    v_uri: 'v://cn.zhongbei/highway/jinggang-2026/',
    name: '京港高速大修工程（2026）',
    type: 'highway',
    owner_unit: '河南省高速公路发展有限公司',
    contractor: '中铁一局',
    supervisor: '中北工程',
    contract_no: 'JSHG-2026-001',
    start_date: '2026-03-01',
    end_date: '2026-10-31',
    status: 'active' as const,
    record_count: 47,
    photo_count: 128,
    proof_count: 175,
  },
  {
    id: '44444444-4444-4444-8444-444444444444',
    enterprise_id: '11111111-1111-4111-8111-111111111111',
    v_uri: 'v://cn.zhongbei/bridge/qinhe/',
    name: '沁河特大桥定期检测工程',
    type: 'bridge',
    owner_unit: '焦作市交通运输局',
    contractor: '',
    supervisor: '中北工程',
    contract_no: 'QR-2026-03',
    start_date: '2026-04-01',
    end_date: '2026-05-30',
    status: 'pending' as const,
    record_count: 0,
    photo_count: 0,
    proof_count: 0,
  },
]

export const NAV = [
  { key: 'dashboard', icon: '📊', label: '控制台' },
  { key: 'inspection', icon: '📝', label: '质检录入' },
  { key: 'photos', icon: '📷', label: '现场照片' },
  { key: 'reports', icon: '📄', label: '报告生成' },
  { key: 'logpeg', icon: '📘', label: '施工日志' },
  { key: 'proof', icon: '🔒', label: 'Proof 链' },
  { key: 'projects', icon: '🏗️', label: '项目管理' },
  { key: 'register', icon: '➕', label: '注册新项目' },
  { key: 'team', icon: '👥', label: '团队成员' },
  { key: 'permissions', icon: '🔐', label: '权限管理' },
  { key: 'settings', icon: '⚙️', label: '系统设置' },
]

export const NAV_SECTIONS: Array<{ label: string; keys: string[] }> = [
  { label: '概览', keys: ['dashboard'] },
  { label: '质检业务', keys: ['inspection', 'photos', 'reports', 'logpeg', 'proof'] },
  { label: '项目管理', keys: ['projects', 'register'] },
  { label: '团队', keys: ['team', 'permissions'] },
  { label: '系统', keys: ['settings'] },
]

export type TeamRole = 'OWNER' | 'SUPERVISOR' | 'AI' | 'PUBLIC'
export type SegType = 'km' | 'contract' | 'structure'
export type PermTemplate = 'standard' | 'strict' | 'open' | 'custom'
export type InspectionTypeKey = 'flatness' | 'crack' | 'rut' | 'compaction' | 'settlement'
export type PermissionRole = TeamRole | 'REGULATOR' | 'MARKET'
export type PermissionKey = 'view' | 'input' | 'approve' | 'manage' | 'settle' | 'regulator'
export type ZeroLedgerTab = 'personnel' | 'equipment' | 'subcontract' | 'materials'

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
  description: string
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

export const TYPE_LABEL: Record<string, string> = {
  highway: '高速公路',
  road: '普通公路',
  urban: '城市道路',
  bridge: '桥梁工程',
  bridge_repair: '桥梁维修',
  tunnel: '隧道工程',
  municipal: '市政工程',
  water: '水利工程',
}

export const TYPE_ICON: Record<string, string> = {
  highway: '🛣️',
  road: '🛤️',
  urban: '🏙️',
  bridge: '🌉',
  bridge_repair: '🔧',
  tunnel: '🚇',
  municipal: '🏙️',
  water: '💧',
}

export const PROJECT_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'highway', label: '高速公路' },
  { value: 'road', label: '普通公路' },
  { value: 'urban', label: '城市道路' },
  { value: 'bridge', label: '桥梁工程' },
  { value: 'bridge_repair', label: '桥梁维修' },
  { value: 'tunnel', label: '隧道工程' },
  { value: 'municipal', label: '市政工程' },
  { value: 'water', label: '水利工程' },
]

export const INSPECTION_TYPE_OPTIONS: Array<{ key: InspectionTypeKey; label: string }> = [
  { key: 'flatness', label: '路面平整度' },
  { key: 'crack', label: '裂缝宽度' },
  { key: 'rut', label: '车辙深度' },
  { key: 'compaction', label: '压实度' },
  { key: 'settlement', label: '路基沉降' },
]

export const INSPECTION_TYPE_LABEL: Record<InspectionTypeKey, string> = INSPECTION_TYPE_OPTIONS.reduce(
  (acc, item) => {
    acc[item.key] = item.label
    return acc
  },
  {} as Record<InspectionTypeKey, string>
)

export const INSPECTION_TYPE_KEYS = new Set<InspectionTypeKey>(INSPECTION_TYPE_OPTIONS.map((item) => item.key))

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

export const normalizeTeamRole = (value: unknown, fallback: TeamRole = 'AI'): TeamRole => {
  const role = String(value || '').toUpperCase()
  if (role === 'OWNER' || role === 'SUPERVISOR' || role === 'AI' || role === 'PUBLIC') {
    return role as TeamRole
  }
  return fallback
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

export const ACTIVITY_ITEMS = [
  { dot: '#059669', text: '王质检在京港高速大修录入了路面平整度记录', time: '10 分钟前' },
  { dot: '#1A56DB', text: '张项目经理注册了新项目：沁河特大桥定检', time: '2 小时前' },
  { dot: '#D97706', text: '系统生成了 3 月份质检汇总报告', time: '今天 09:00' },
  { dot: '#DC2626', text: 'K49+200 裂缝宽度超标，请尽快复检', time: '昨天 14:15' },
]

export const QUICK_USERS = {
  admin: {
    ...DEMO_USER,
    name: '李总工',
    email: 'admin@zhongbei.com',
    dto_role: 'OWNER' as const,
    title: '超级管理员',
    v_uri: 'v://cn.zhongbei/executor/admin/',
  },
  pm: {
    ...DEMO_USER,
    id: '22222222-2222-4222-8222-222222222223',
    name: '张项目经理',
    email: 'pm@zhongbei.com',
    dto_role: 'SUPERVISOR' as const,
    title: '项目经理',
    v_uri: 'v://cn.zhongbei/executor/pm/',
  },
  inspector: {
    ...DEMO_USER,
    id: '22222222-2222-4222-8222-222222222224',
    name: '王质检',
    email: 'qc@zhongbei.com',
    dto_role: 'AI' as const,
    title: '质检员',
    v_uri: 'v://cn.zhongbei/executor/qc/',
  },
}

export const QUICK_LOGIN_ACCOUNTS: Array<{
  key: keyof typeof QUICK_USERS
  account: string
  password: string
  roleLabel: string
  desc: string
}> = [
  {
    key: 'admin',
    account: 'admin@zhongbei.com',
    password: '123456',
    roleLabel: '超级管理员',
    desc: '企业配置 / 权限模板 / 系统集成',
  },
  {
    key: 'pm',
    account: 'pm@zhongbei.com',
    password: 'PM@2026',
    roleLabel: '项目经理',
    desc: '项目注册 / 进度与报告管理',
  },
  {
    key: 'inspector',
    account: 'qc@zhongbei.com',
    password: 'QC@2026',
    roleLabel: '质检员',
    desc: '现场录入 / 拍照 / 提交质检',
  },
]

