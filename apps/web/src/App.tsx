import React, { useEffect, useState } from 'react'
import { useUIStore, useProjectStore, useAuthStore } from './store'
import { Toast, Card, Button, VPathDisplay } from './components/ui'
import { useAuthApi, useProof, useTeam, useSettings, useProjects, useAutoreg, useErpnext } from './hooks/useApi'
import Dashboard from './pages/Dashboard'
import InspectionPage from './pages/InspectionPage'
import PhotosPage from './pages/PhotosPage'
import ReportsPage from './pages/ReportsPage'

const DEMO_ENTERPRISE = {
  id: '11111111-1111-4111-8111-111111111111',
  v_uri: 'v://cn.zhongbei/',
  name: '中北工程设计咨询有限公司',
  short_name: '中北工程',
  plan: 'enterprise' as const,
  proof_quota: 99999,
  proof_used: 47,
}

const DEMO_USER = {
  id: '22222222-2222-4222-8222-222222222222',
  enterprise_id: '11111111-1111-4111-8111-111111111111',
  v_uri: 'v://cn.zhongbei/executor/ligong/',
  name: '李总工',
  email: 'admin@zhongbei.com',
  dto_role: 'OWNER' as const,
  title: '总工程师',
}

const DEMO_PROJECTS = [
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

const NAV = [
  { key: 'dashboard', icon: '📊', label: '控制台' },
  { key: 'inspection', icon: '📝', label: '质检录入' },
  { key: 'photos', icon: '📷', label: '现场照片' },
  { key: 'reports', icon: '📄', label: '报告生成' },
  { key: 'proof', icon: '🔒', label: 'Proof 链' },
  { key: 'projects', icon: '🏗️', label: '项目管理' },
  { key: 'register', icon: '➕', label: '注册新项目' },
  { key: 'team', icon: '👥', label: '团队成员' },
  { key: 'permissions', icon: '🔐', label: '权限管理' },
  { key: 'settings', icon: '⚙️', label: '系统设置' },
]

const NAV_SECTIONS: Array<{ label: string; keys: string[] }> = [
  { label: '概览', keys: ['dashboard'] },
  { label: '质检业务', keys: ['inspection', 'photos', 'reports', 'proof'] },
  { label: '项目管理', keys: ['projects', 'register'] },
  { label: '团队', keys: ['team', 'permissions'] },
  { label: '系统', keys: ['settings'] },
]

type TeamRole = 'OWNER' | 'SUPERVISOR' | 'AI' | 'PUBLIC'
type SegType = 'km' | 'contract' | 'structure'
type PermTemplate = 'standard' | 'strict' | 'open' | 'custom'
type InspectionTypeKey = 'flatness' | 'crack' | 'rut' | 'compaction' | 'settlement'
type PermissionRole = TeamRole | 'REGULATOR' | 'MARKET'
type PermissionKey = 'view' | 'input' | 'approve' | 'manage' | 'settle' | 'regulator'
type ZeroLedgerTab = 'personnel' | 'equipment' | 'subcontract' | 'materials'

interface ZeroPersonnelRow {
  id: string
  name: string
  title: string
  dtoRole: TeamRole
  certificate: string
}

interface ZeroEquipmentRow {
  id: string
  name: string
  modelNo: string
  inspectionItem: string
  validUntil: string
}

interface ZeroSubcontractRow {
  id: string
  unitName: string
  content: string
  range: string
}

interface ZeroMaterialRow {
  id: string
  name: string
  spec: string
  supplier: string
  freq: string
}

interface TeamMember {
  id: string
  name: string
  title: string
  email: string
  role: TeamRole
  color: string
  projects: string[]
}

interface ProjectRegisterMeta {
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

interface ProjectEditDraft {
  name: string
  type: string
  owner_unit: string
  contractor: string
  supervisor: string
  contract_no: string
  start_date: string
  end_date: string
}

interface PermissionRow {
  role: PermissionRole
  view: boolean
  input: boolean
  approve: boolean
  manage: boolean
  settle: boolean
  regulator: boolean
}

interface SettingsState {
  emailNotify: boolean
  wechatNotify: boolean
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
  wechatMiniapp: boolean
  droneImport: boolean
}

interface ErpDraftState {
  url: string
  siteName: string
  apiKey: string
  apiSecret: string
  username: string
  password: string
}

interface ErpWritebackDraftState {
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

const ROLE_LABEL: Record<TeamRole, string> = {
  OWNER: 'OWNER',
  SUPERVISOR: 'SUPERVISOR',
  AI: 'AI',
  PUBLIC: 'PUBLIC',
}

const roleToTitle = (role: TeamRole): string => {
  if (role === 'AI') return '质检员'
  if (role === 'SUPERVISOR') return '监理'
  if (role === 'OWNER') return '管理员'
  return '只读成员'
}

const toRoleDraftMap = (rows: TeamMember[]): Record<string, TeamRole> =>
  rows.reduce<Record<string, TeamRole>>((acc, row) => {
    acc[row.id] = row.role
    return acc
  }, {})

const PERMISSION_ROLE_LABEL: Record<PermissionRole, string> = {
  OWNER: 'OWNER',
  SUPERVISOR: 'SUPERVISOR',
  AI: 'AI',
  PUBLIC: 'PUBLIC',
  REGULATOR: 'REGULATOR',
  MARKET: 'MARKET',
}

const PERMISSION_COLUMNS: Array<{ key: PermissionKey; label: string }> = [
  { key: 'view', label: '查看' },
  { key: 'input', label: '录入' },
  { key: 'approve', label: '审批' },
  { key: 'manage', label: '项目管理' },
  { key: 'settle', label: '计量结算' },
  { key: 'regulator', label: '监管查看' },
]

const DEFAULT_PERMISSION_MATRIX: PermissionRow[] = [
  { role: 'OWNER', view: true, input: true, approve: true, manage: true, settle: true, regulator: true },
  { role: 'SUPERVISOR', view: true, input: true, approve: true, manage: false, settle: false, regulator: false },
  { role: 'AI', view: true, input: true, approve: false, manage: false, settle: false, regulator: false },
  { role: 'PUBLIC', view: true, input: false, approve: false, manage: false, settle: false, regulator: false },
  { role: 'REGULATOR', view: true, input: false, approve: false, manage: false, settle: false, regulator: true },
]

const PERMISSION_TEMPLATES: Record<Exclude<PermTemplate, 'custom'>, PermissionRow[]> = {
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

const clonePermissionRows = (rows: PermissionRow[]): PermissionRow[] => rows.map((row) => ({ ...row }))

const normalizePermissionMatrix = (
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

const detectPermissionTemplate = (rows: PermissionRow[]): PermTemplate => {
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

const TYPE_LABEL: Record<string, string> = {
  highway: '高速公路',
  road: '普通公路',
  urban: '城市道路',
  bridge: '桥梁工程',
  bridge_repair: '桥梁维修',
  tunnel: '隧道工程',
  municipal: '市政工程',
  water: '水利工程',
}

const TYPE_ICON: Record<string, string> = {
  highway: '🛣️',
  road: '🛤️',
  urban: '🏙️',
  bridge: '🌉',
  bridge_repair: '🔧',
  tunnel: '🚇',
  municipal: '🏙️',
  water: '💧',
}

const PROJECT_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'highway', label: '高速公路' },
  { value: 'road', label: '普通公路' },
  { value: 'urban', label: '城市道路' },
  { value: 'bridge', label: '桥梁工程' },
  { value: 'bridge_repair', label: '桥梁维修' },
  { value: 'tunnel', label: '隧道工程' },
  { value: 'municipal', label: '市政工程' },
  { value: 'water', label: '水利工程' },
]

const INSPECTION_TYPE_OPTIONS: Array<{ key: InspectionTypeKey; label: string }> = [
  { key: 'flatness', label: '路面平整度' },
  { key: 'crack', label: '裂缝宽度' },
  { key: 'rut', label: '车辙深度' },
  { key: 'compaction', label: '压实度' },
  { key: 'settlement', label: '路基沉降' },
]

const INSPECTION_TYPE_LABEL: Record<InspectionTypeKey, string> = INSPECTION_TYPE_OPTIONS.reduce(
  (acc, item) => {
    acc[item.key] = item.label
    return acc
  },
  {} as Record<InspectionTypeKey, string>
)

const INSPECTION_TYPE_KEYS = new Set<InspectionTypeKey>(INSPECTION_TYPE_OPTIONS.map((item) => item.key))

const normalizeSegType = (value: unknown): SegType => {
  const text = String(value || '').toLowerCase()
  return text === 'contract' || text === 'structure' ? text : 'km'
}

const normalizePermTemplate = (value: unknown): PermTemplate => {
  const text = String(value || '').toLowerCase()
  return text === 'strict' || text === 'open' || text === 'custom' ? text : 'standard'
}

const normalizeKmInterval = (value: unknown, fallback = 20): number => {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return Math.max(1, Math.min(500, Math.round(parsed)))
}

const normalizeInspectionTypeKeys = (values: unknown): InspectionTypeKey[] => {
  if (!Array.isArray(values)) return []
  const out: InspectionTypeKey[] = []
  values.forEach((item) => {
    const key = String(item || '') as InspectionTypeKey
    if (INSPECTION_TYPE_KEYS.has(key) && !out.includes(key)) out.push(key)
  })
  return out
}

const normalizeContractSegs = (values: unknown): Array<{ name: string; range: string }> => {
  if (!Array.isArray(values)) return []
  return values
    .filter((item): item is { name?: unknown; range?: unknown } => typeof item === 'object' && item !== null)
    .map((item) => ({
      name: String(item.name || '').trim(),
      range: String(item.range || '').trim(),
    }))
    .filter((item) => item.name || item.range)
}

const normalizeStructures = (values: unknown): Array<{ kind: string; name: string; code: string }> => {
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

const normalizeTeamRole = (value: unknown, fallback: TeamRole = 'AI'): TeamRole => {
  const role = String(value || '').toUpperCase()
  if (role === 'OWNER' || role === 'SUPERVISOR' || role === 'AI' || role === 'PUBLIC') {
    return role as TeamRole
  }
  return fallback
}

const normalizeZeroPersonnelRows = (values: unknown): ZeroPersonnelRow[] => {
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

const normalizeZeroEquipmentRows = (values: unknown): ZeroEquipmentRow[] => {
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

const normalizeZeroSubcontractRows = (values: unknown): ZeroSubcontractRow[] => {
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

const normalizeZeroMaterialRows = (values: unknown): ZeroMaterialRow[] => {
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

const normalizeZeroSignStatus = (value: unknown): 'pending' | 'approved' | 'rejected' => {
  const v = String(value || '').toLowerCase()
  if (v === 'approved' || v === 'rejected') return v
  return 'pending'
}

const ACTIVITY_ITEMS = [
  { dot: '#059669', text: '王质检在京港高速大修录入了路面平整度记录', time: '10 分钟前' },
  { dot: '#1A56DB', text: '张项目经理注册了新项目：沁河特大桥定检', time: '2 小时前' },
  { dot: '#D97706', text: '系统生成了 3 月份质检汇总报告', time: '今天 09:00' },
  { dot: '#DC2626', text: 'K49+200 裂缝宽度超标，请尽快复检', time: '昨天 14:15' },
]

const QUICK_USERS = {
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

const QUICK_LOGIN_ACCOUNTS: Array<{
  key: keyof typeof QUICK_USERS
  account: string
  password: string
  roleLabel: string
  desc: string
}> = [
  {
    key: 'admin',
    account: 'admin@zhongbei.com',
    password: 'Admin@2026',
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

export default function App() {
  const { activeTab, setActiveTab, toastMsg, sidebarOpen, setSidebarOpen, showToast } = useUIStore()
  const { projects, setProjects, currentProject, setCurrentProject, addProject } = useProjectStore()
  const { setUser, logout, enterprise, user, token } = useAuthStore()
  const {
    list: listProjectsApi,
    create: createProjectApi,
    getById: getProjectByIdApi,
    update: updateProjectApi,
    remove: removeProjectApi,
    syncAutoreg: syncAutoregApi,
    completeGitpeg: completeGitpegApi,
  } = useProjects()
  const {
    registerProject: registerAutoregProjectApi,
    registerProjectAlias: registerAutoregProjectAliasApi,
    listProjects: listAutoregProjectsApi,
  } = useAutoreg()
  const { getProjectBasics: getErpProjectBasicsApi } = useErpnext()
  const {
    login: loginApi,
    me: meApi,
    getEnterprise: getEnterpriseApi,
    logout: logoutApi,
    registerEnterprise: registerEnterpriseApi,
  } = useAuthApi()
  const { listMembers, inviteMember, updateMember: updateMemberApi, removeMember: removeMemberApi } = useTeam()
  const { getSettings, saveSettings, testErpnext, testGitpegRegistrar, uploadTemplate } = useSettings()

  const isDemoToken = typeof token === 'string' && token.startsWith('demo-token-')
  const hasPersistedSession = Boolean(token && user?.id && enterprise?.id)
  const [appReady, setAppReady] = useState(hasPersistedSession && isDemoToken)
  const [sessionChecking, setSessionChecking] = useState(Boolean(token) && !isDemoToken)
  const [loginTab, setLoginTab] = useState<'login' | 'register'>('login')
  const [loginForm, setLoginForm] = useState({ account: '', pass: '' })
  const [loggingIn, setLoggingIn] = useState(false)
  const [entForm, setEntForm] = useState({ name: '', adminPhone: '', pass: '', uscc: '' })

  useEffect(() => {
    if (!appReady) return
    if (!projects.length && enterprise?.id === DEMO_ENTERPRISE.id) {
      setProjects(DEMO_PROJECTS)
      setCurrentProject(DEMO_PROJECTS[0])
    }
  }, [appReady, projects.length, enterprise?.id, setProjects, setCurrentProject])

  useEffect(() => {
    let cancelled = false
    const abortController = new AbortController()
    const bootstrapTimeoutMs = Number(import.meta.env.VITE_BOOTSTRAP_TIMEOUT_MS || 8000)
    const restoreSession = async () => {
      if (!token) {
        setAppReady(false)
        setSessionChecking(false)
        return
      }

      const hasLocalSession = Boolean(user?.id && enterprise?.id)
      if (token.startsWith('demo-token-')) {
        setAppReady(hasLocalSession)
        setSessionChecking(false)
        return
      }
      if (hasLocalSession && appReady) {
        setSessionChecking(false)
        return
      }
      setAppReady(false)
      setSessionChecking(true)

      const meRes = await meApi({
        signal: abortController.signal,
        timeoutMs: bootstrapTimeoutMs,
      }) as {
        id?: string
        name?: string
        email?: string
        title?: string
        dto_role?: string
        enterprise_id?: string
        v_uri?: string
      } | null
      if (cancelled || abortController.signal.aborted) return
      if (!meRes?.id || !meRes.enterprise_id) {
        setAppReady(false)
        setSessionChecking(false)
        return
      }

      const enterpriseRes = await getEnterpriseApi(meRes.enterprise_id, {
        signal: abortController.signal,
        timeoutMs: bootstrapTimeoutMs,
      }) as {
        id?: string
        name?: string
        v_uri?: string
        short_name?: string
        plan?: 'basic' | 'pro' | 'enterprise'
        proof_quota?: number
        proof_used?: number
      } | null
      if (cancelled || abortController.signal.aborted) return
      if (!enterpriseRes?.id) {
        setAppReady(false)
        setSessionChecking(false)
        return
      }

      setUser(
        {
          id: meRes.id,
          enterprise_id: meRes.enterprise_id,
          v_uri: meRes.v_uri || '',
          name: meRes.name || '用户',
          email: meRes.email || undefined,
          dto_role: (meRes.dto_role || 'PUBLIC') as 'PUBLIC' | 'MARKET' | 'AI' | 'SUPERVISOR' | 'OWNER' | 'REGULATOR',
          title: meRes.title || undefined,
        },
        {
          id: enterpriseRes.id,
          name: enterpriseRes.name || '企业',
          v_uri: enterpriseRes.v_uri || 'v://cn/enterprise/',
          short_name: enterpriseRes.short_name,
          plan: enterpriseRes.plan || 'enterprise',
          proof_quota: Number(enterpriseRes.proof_quota || 0),
          proof_used: Number(enterpriseRes.proof_used || 0),
        },
        token
      )
      setAppReady(true)
      setSessionChecking(false)
    }
    restoreSession()
    return () => {
      cancelled = true
      abortController.abort()
    }
  }, [token, user?.id, enterprise?.id, appReady, meApi, getEnterpriseApi, setUser])

  useEffect(() => {
    setEnterpriseInfo({
      name: enterprise?.name || DEMO_ENTERPRISE.name,
      vUri: enterprise?.v_uri || DEMO_ENTERPRISE.v_uri,
      creditCode: '',
      adminEmail: user?.email || DEMO_USER.email,
    })
  }, [enterprise?.name, enterprise?.v_uri, user?.email])

  const proj = currentProject || DEMO_PROJECTS[0]

  const [registerStep, setRegisterStep] = useState(1)
  const [segType, setSegType] = useState<SegType>('km')
  const [permTemplate, setPermTemplate] = useState<PermTemplate>('standard')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [projectDetailOpen, setProjectDetailOpen] = useState(false)
  const [projectDetailId, setProjectDetailId] = useState<string | null>(null)
  const [detailEdit, setDetailEdit] = useState(false)
  const [detailProjectDraft, setDetailProjectDraft] = useState<ProjectEditDraft | null>(null)
  const [detailDraft, setDetailDraft] = useState<ProjectRegisterMeta | null>(null)
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const [regForm, setRegForm] = useState({
    name: '',
    type: 'highway',
    owner_unit: '',
    erp_project_code: '',
    erp_project_name: '',
    contractor: '',
    supervisor: '',
    contract_no: '',
    start_date: '',
    end_date: '',
    description: '',
    seg_start: 'K0+000',
    seg_end: 'K100+000',
  })
  const [erpBindingLoading, setErpBindingLoading] = useState(false)
  const [erpBinding, setErpBinding] = useState<{
    success: boolean
    code: string
    name: string
    reason: string
  }>({
    success: false,
    code: '',
    name: '',
    reason: 'pending',
  })
  const [regKmInterval, setRegKmInterval] = useState(20)
  const [registerSuccess, setRegisterSuccess] = useState<{ id: string; name: string; uri: string } | null>(null)
  const [vpathStatus, setVpathStatus] = useState<'checking' | 'available' | 'taken'>('checking')
  const [regInspectionTypes, setRegInspectionTypes] = useState<InspectionTypeKey[]>(['flatness', 'crack'])
  const [contractSegs, setContractSegs] = useState([{ name: '一标段', range: 'K0~K30' }])
  const [structures, setStructures] = useState([{ kind: '桥梁', name: '沁河大桥', code: 'QH-B01' }])
  const [zeroLedgerTab, setZeroLedgerTab] = useState<ZeroLedgerTab>('personnel')
  const [zeroPersonnel, setZeroPersonnel] = useState<ZeroPersonnelRow[]>([
    { id: 'zp-1', name: '石玉山', title: '项目负责人', dtoRole: 'OWNER', certificate: '一级建造师' },
    { id: 'zp-2', name: '王质检', title: '质检员', dtoRole: 'AI', certificate: '质检员证' },
  ])
  const [zeroEquipment, setZeroEquipment] = useState<ZeroEquipmentRow[]>([
    { id: 'ze-1', name: '灌砂筒', modelNo: 'BZY-001', inspectionItem: '压实度', validUntil: '2027-03-01' },
    { id: 'ze-2', name: '弯沉仪', modelNo: 'BZY-002', inspectionItem: '弯沉值', validUntil: '2026-12-31' },
  ])
  const [zeroSubcontracts, setZeroSubcontracts] = useState<ZeroSubcontractRow[]>([
    { id: 'zs-1', unitName: '', content: '路面施工', range: '' },
  ])
  const [zeroMaterials, setZeroMaterials] = useState<ZeroMaterialRow[]>([
    { id: 'zm-1', name: '沥青混合料', spec: 'AC-13C', supplier: '', freq: '每批次检测' },
  ])

  const [members, setMembers] = useState<TeamMember[]>([
    { id: '55555555-5555-4555-8555-555555555551', name: '李总工', title: '总工程师', email: 'admin@zhongbei.com', role: 'OWNER', color: '#1A56DB', projects: ['33333333-3333-4333-8333-333333333333', '44444444-4444-4444-8444-444444444444'] },
    { id: '55555555-5555-4555-8555-555555555552', name: '王质检', title: '质检员', email: 'wang@zhongbei.com', role: 'AI', color: '#059669', projects: ['33333333-3333-4333-8333-333333333333'] },
    { id: '55555555-5555-4555-8555-555555555553', name: '钱监理', title: '监理工程师', email: 'qian@zhongbei.com', role: 'SUPERVISOR', color: '#7C3AED', projects: ['33333333-3333-4333-8333-333333333333'] },
  ])

  const [inviteForm, setInviteForm] = useState({ name: '', email: '', role: 'AI' as TeamRole, projectId: 'all' })
  const [memberRoleDrafts, setMemberRoleDrafts] = useState<Record<string, TeamRole>>(() => ({
    '55555555-5555-4555-8555-555555555551': 'OWNER',
    '55555555-5555-4555-8555-555555555552': 'AI',
    '55555555-5555-4555-8555-555555555553': 'SUPERVISOR',
  }))

  const [settings, setSettings] = useState<SettingsState>({
    emailNotify: true,
    wechatNotify: true,
    autoGenerateReport: false,
    strictProof: true,
    reportTemplate: 'default.docx',
    reportTemplateUrl: '',
    reportHeader: DEMO_ENTERPRISE.name,
    webhookUrl: '',
    gitpegToken: '',
    gitpegEnabled: false,
    gitpegRegistrarBaseUrl: 'https://gitpeg.cn',
    gitpegPartnerCode: 'wastewater-site',
    gitpegIndustryCode: 'wastewater',
    gitpegClientId: 'ptn_wastewater_001',
    gitpegClientSecret: '',
    gitpegRegistrationMode: 'DOMAIN',
    gitpegReturnUrl: '',
    gitpegWebhookUrl: '',
    gitpegWebhookSecret: '',
    gitpegModuleCandidates: ['proof', 'utrip', 'openapi'],
    erpnextSync: false,
    wechatMiniapp: true,
    droneImport: false,
  })
  const [erpDraft, setErpDraft] = useState<ErpDraftState>({
    url: '',
    siteName: 'development.localhost',
    apiKey: '',
    apiSecret: '',
    username: '',
    password: '',
  })
  const [erpWritebackDraft, setErpWritebackDraft] = useState<ErpWritebackDraftState>({
    projectDoctype: 'Project',
    projectLookupField: 'name',
    projectLookupValue: '',
    gitpegProjectUriField: 'gitpeg_project_uri',
    gitpegSiteUriField: 'gitpeg_site_uri',
    gitpegStatusField: 'gitpeg_status',
    gitpegResultJsonField: 'gitpeg_register_result_json',
    gitpegRegistrationIdField: 'gitpeg_registration_id',
    gitpegNodeUriField: 'gitpeg_node_uri',
    gitpegShellUriField: 'gitpeg_shell_uri',
    gitpegProofHashField: 'gitpeg_proof_hash',
    gitpegIndustryProfileIdField: 'gitpeg_industry_profile_id',
  })
  const [erpTesting, setErpTesting] = useState(false)
  const [erpTestMsg, setErpTestMsg] = useState('')
  const [syncingProjectId, setSyncingProjectId] = useState<string | null>(null)
  const [gitpegVerifying, setGitpegVerifying] = useState(false)
  const [gitpegVerifyMsg, setGitpegVerifyMsg] = useState<{ text: string; color: string }>({ text: '', color: '#64748B' })
  const [webhookTesting, setWebhookTesting] = useState(false)
  const [webhookResult, setWebhookResult] = useState<{ text: string; color: string; visible: boolean }>({
    text: '',
    color: '#64748B',
    visible: false,
  })
  const [enterpriseInfo, setEnterpriseInfo] = useState({
    name: DEMO_ENTERPRISE.name,
    vUri: DEMO_ENTERPRISE.v_uri,
    creditCode: '',
    adminEmail: DEMO_USER.email,
  })
  const [reportTemplateFile, setReportTemplateFile] = useState<File | null>(null)
  const [permissionMatrix, setPermissionMatrix] = useState<PermissionRow[]>(() => normalizePermissionMatrix())
  const [permissionTemplate, setPermissionTemplate] = useState<PermTemplate>(() => detectPermissionTemplate(normalizePermissionMatrix()))
  const [projectMeta, setProjectMeta] = useState<Record<string, ProjectRegisterMeta>>({})
  const { listProofs, verify: verifyProof, stats: proofStatsApi, nodeTree: proofNodeTreeApi } = useProof()
  const [proofRows, setProofRows] = useState<Array<{
    proof_id: string
    summary?: string
    object_type?: string
    action?: string
    created_at?: string
  }>>([])
  const [proofStats, setProofStats] = useState<{
    total: number
    by_type: Record<string, number>
    by_action: Record<string, number>
  }>({
    total: 0,
    by_type: {},
    by_action: {},
  })
  const [proofNodeRows, setProofNodeRows] = useState<Array<{
    uri?: string
    node_type?: string
    status?: string
  }>>([])
  const [autoregRows, setAutoregRows] = useState<Array<{
    project_code?: string
    project_name?: string
    project_uri?: string
    site_uri?: string
    updated_at?: string
    source_system?: string
  }>>([])
  const [proofLoading, setProofLoading] = useState(false)
  const [proofVerifying, setProofVerifying] = useState<string | null>(null)
  const [gitpegCallbackHandled, setGitpegCallbackHandled] = useState(false)
  const isDemoEnterprise = enterprise?.id === DEMO_ENTERPRISE.id
  const canUseEnterpriseApi = !!enterprise?.id && !isDemoEnterprise

  const regUri = `v://cn.zhongbei/${regForm.type}/${(regForm.name || 'project').replace(/\s+/g, '').slice(0, 20).toLowerCase()}/`
  const detailProject = projects.find((p) => p.id === projectDetailId) || null
  const detailMeta = (projectDetailId && projectMeta[projectDetailId]) || null
  const buildDefaultProjectMeta = (): ProjectRegisterMeta => ({
    segType: 'km',
    segStart: 'K0+000',
    segEnd: 'K100+000',
    kmInterval: 20,
    inspectionTypes: ['flatness', 'crack'],
    contractSegs: [],
    structures: [],
    zeroPersonnel: [],
    zeroEquipment: [],
    zeroSubcontracts: [],
    zeroMaterials: [],
    zeroSignStatus: 'pending',
    qcLedgerUnlocked: false,
    permTemplate: 'standard',
    memberCount: members.length,
  })
  const normalizeProjectMeta = (meta?: Partial<ProjectRegisterMeta> | null): ProjectRegisterMeta => {
    const base = buildDefaultProjectMeta()
    if (!meta) return base
    const selectedInspectionTypes = normalizeInspectionTypeKeys(meta.inspectionTypes)
    return {
      ...base,
      ...meta,
      segType: normalizeSegType(meta.segType ?? base.segType),
      permTemplate: normalizePermTemplate(meta.permTemplate ?? base.permTemplate),
      kmInterval: normalizeKmInterval(meta.kmInterval, base.kmInterval),
      inspectionTypes: selectedInspectionTypes.length > 0 ? selectedInspectionTypes : base.inspectionTypes,
      contractSegs: normalizeContractSegs(meta.contractSegs).length > 0
        ? normalizeContractSegs(meta.contractSegs)
        : base.contractSegs,
      structures: normalizeStructures(meta.structures).length > 0
        ? normalizeStructures(meta.structures)
        : base.structures,
      zeroPersonnel: normalizeZeroPersonnelRows(meta.zeroPersonnel).length > 0
        ? normalizeZeroPersonnelRows(meta.zeroPersonnel)
        : base.zeroPersonnel,
      zeroEquipment: normalizeZeroEquipmentRows(meta.zeroEquipment).length > 0
        ? normalizeZeroEquipmentRows(meta.zeroEquipment)
        : base.zeroEquipment,
      zeroSubcontracts: normalizeZeroSubcontractRows(meta.zeroSubcontracts).length > 0
        ? normalizeZeroSubcontractRows(meta.zeroSubcontracts)
        : base.zeroSubcontracts,
      zeroMaterials: normalizeZeroMaterialRows(meta.zeroMaterials).length > 0
        ? normalizeZeroMaterialRows(meta.zeroMaterials)
        : base.zeroMaterials,
      zeroSignStatus: normalizeZeroSignStatus(meta.zeroSignStatus),
      qcLedgerUnlocked: Boolean(meta.qcLedgerUnlocked),
    }
  }
  const projectMetaFromRow = (project: typeof projects[number]): ProjectRegisterMeta | null => {
    const row = project as unknown as Record<string, unknown>
    const hasPersistedMeta =
      typeof row.seg_type === 'string' ||
      typeof row.seg_start === 'string' ||
      typeof row.seg_end === 'string' ||
      typeof row.km_interval !== 'undefined' ||
      Array.isArray(row.inspection_types) ||
      Array.isArray(row.contract_segs) ||
      Array.isArray(row.structures) ||
      Array.isArray(row.zero_personnel) ||
      Array.isArray(row.zero_equipment) ||
      Array.isArray(row.zero_subcontracts) ||
      Array.isArray(row.zero_materials) ||
      typeof row.zero_sign_status === 'string' ||
      typeof row.qc_ledger_unlocked !== 'undefined' ||
      typeof row.perm_template === 'string'

    if (!hasPersistedMeta) return null

    return normalizeProjectMeta({
      segType: normalizeSegType(row.seg_type),
      segStart: String(row.seg_start || 'K0+000'),
      segEnd: String(row.seg_end || 'K100+000'),
      kmInterval: normalizeKmInterval(row.km_interval, 20),
      inspectionTypes: normalizeInspectionTypeKeys(row.inspection_types),
      contractSegs: normalizeContractSegs(row.contract_segs),
      structures: normalizeStructures(row.structures),
      zeroPersonnel: normalizeZeroPersonnelRows(row.zero_personnel),
      zeroEquipment: normalizeZeroEquipmentRows(row.zero_equipment),
      zeroSubcontracts: normalizeZeroSubcontractRows(row.zero_subcontracts),
      zeroMaterials: normalizeZeroMaterialRows(row.zero_materials),
      zeroSignStatus: normalizeZeroSignStatus(row.zero_sign_status),
      qcLedgerUnlocked: Boolean(row.qc_ledger_unlocked),
      permTemplate: normalizePermTemplate(row.perm_template),
      memberCount: members.length,
    })
  }
  const toggleInspectionType = (
    key: InspectionTypeKey,
    selected: InspectionTypeKey[],
    setter: (next: InspectionTypeKey[]) => void
  ) => {
    if (selected.includes(key)) {
      setter(selected.filter((x) => x !== key))
      return
    }
    setter([...selected, key])
  }
  const buildProjectEditDraft = (project: typeof projects[number]): ProjectEditDraft => ({
    name: project.name || '',
    type: project.type || 'highway',
    owner_unit: project.owner_unit || '',
    contractor: project.contractor || '',
    supervisor: project.supervisor || '',
    contract_no: project.contract_no || '',
    start_date: project.start_date || '',
    end_date: project.end_date || '',
  })
  const permissionTreeRoot = enterprise?.v_uri || proj.v_uri || 'v://cn.zhongbei/'
  const permissionTreeRows = permissionMatrix.map((row) => {
    const granted = PERMISSION_COLUMNS.filter((col) => row[col.key]).map((col) => col.label)
    return {
      role: row.role,
      granted: granted.length > 0 ? granted.join(' / ') : '无权限',
    }
  })

  const parseKm = (s: string) => {
    const m = (s || '').match(/K?(\d+)\+?(\d{1,3})?/)
    if (!m) return Number.NaN
    return Number(m[1]) + Number((m[2] || '0').padStart(3, '0')) / 1000
  }
  const formatKmCompact = (v: number) => {
    const k = Math.floor(v)
    const m = Math.round((v - k) * 1000)
    if (m === 0) return `K${k}`
    return `K${k}+${String(m).padStart(3, '0')}`
  }
  const makeRowId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
  const normalizeNodeSegment = (value: string, fallback = '（待填）') => {
    const cleaned = String(value || '').trim().replace(/[\\/]/g, '-').replace(/\s+/g, '')
    return cleaned || fallback
  }
  const normalizeCodeSegment = (value: string) => String(value || '').trim().replace(/[^\w\u4e00-\u9fa5-]/g, '').replace(/\s+/g, '')
  const buildExecutorUri = (name: string) => `v://cn.zhongbei/executor/${normalizeNodeSegment(name)}/`
  const buildToolNodeName = (name: string, modelNo: string) => {
    const safeName = normalizeNodeSegment(name, '待填仪器')
    const safeModel = normalizeCodeSegment(modelNo)
    return safeModel ? `${safeName}-${safeModel}` : safeName
  }
  const buildToolUri = (name: string, modelNo: string) => `v://cn.zhongbei/tools/${buildToolNodeName(name, modelNo)}/`
  const buildSubcontractUri = (unitName: string) => `v://cn.zhongbei/subcontract/${normalizeNodeSegment(unitName, '待填分包')}/`
  const getEquipmentValidity = (validUntil: string) => {
    if (!validUntil) {
      return { label: '待填', color: '#64748B', bg: '#F1F5F9', ok: false }
    }
    const now = new Date()
    const target = new Date(`${validUntil}T23:59:59`)
    const days = Math.floor((target.getTime() - now.getTime()) / 86400000)
    if (days < 0) {
      return { label: '❌ 已过期', color: '#DC2626', bg: '#FEE2E2', ok: false }
    }
    if (days < 90) {
      return { label: `⚠️ ${days}天`, color: '#D97706', bg: '#FEF3C7', ok: false }
    }
    return { label: '✓ 有效', color: '#059669', bg: '#DCFCE7', ok: true }
  }
  const regRangeTreeLines = (() => {
    if (segType === 'km') {
      const s = parseKm(regForm.seg_start)
      const e = parseKm(regForm.seg_end)
      if (Number.isNaN(s) || Number.isNaN(e) || e <= s) return []
      const lines: string[] = []
      for (let cur = s; cur < e; cur += regKmInterval) {
        lines.push(`${formatKmCompact(cur)}~${formatKmCompact(Math.min(cur + regKmInterval, e))}/`)
        if (lines.length >= 12) {
          lines.push('...(更多分段)')
          break
        }
      }
      return lines
    }
    if (segType === 'contract') {
      return contractSegs
        .filter((seg) => seg.name.trim() || seg.range.trim())
        .map((seg, idx) => `${seg.name || `标段${idx + 1}`}${seg.range ? ` (${seg.range})` : ''}/`)
    }
    return structures
      .filter((st) => st.kind.trim() || st.name.trim() || st.code.trim())
      .map((st, idx) => `${st.kind || '构造物'}/${st.name || `节点${idx + 1}`}${st.code ? ` (${st.code})` : ''}/`)
  })()
  const zeroPersonnelCount = zeroPersonnel.filter((row) => row.name.trim()).length
  const zeroEquipmentCount = zeroEquipment.filter((row) => row.name.trim()).length
  const zeroLedgerSummary = `${zeroPersonnelCount}名人员 · ${zeroEquipmentCount}台仪器 · 等待秩签审批`
  const zeroLedgerTreeRows = (() => {
    const rows: Array<{ text: string; color?: string }> = []
    zeroPersonnel
      .filter((row) => row.name.trim())
      .forEach((row) => rows.push({ text: `executor/${normalizeNodeSegment(row.name)}/ [${row.dtoRole}]`, color: '#34D399' }))
    zeroEquipment
      .filter((row) => row.name.trim())
      .forEach((row) => {
        const validity = getEquipmentValidity(row.validUntil)
        rows.push({ text: `tools/${buildToolNodeName(row.name, row.modelNo)}/ ${validity.label}`, color: validity.ok ? '#A78BFA' : validity.color })
      })
    zeroSubcontracts
      .filter((row) => row.unitName.trim())
      .forEach((row) => rows.push({ text: `subcontract/${normalizeNodeSegment(row.unitName)}/ 自动生成`, color: '#60A5FA' }))
    zeroMaterials
      .filter((row) => row.name.trim())
      .forEach((row) => rows.push({ text: `materials/${normalizeNodeSegment(row.name)}${row.spec ? `-${normalizeCodeSegment(row.spec)}` : ''}/`, color: '#F59E0B' }))
    return rows
  })()
  const registerSegCount = projects.reduce((sum, project) => {
    const meta = projectMeta[project.id]
    if (!meta) return sum + 1
    if (meta.segType === 'contract') return sum + Math.max(1, meta.contractSegs.length)
    if (meta.segType === 'structure') return sum + Math.max(1, meta.structures.length)
    const s = parseKm(meta.segStart)
    const e = parseKm(meta.segEnd)
    if (Number.isNaN(s) || Number.isNaN(e) || e <= s) return sum + 1
    return sum + Math.max(1, Math.ceil((e - s) / 20))
  }, 0)
  const registerRecordCount = projects.reduce((sum, project) => sum + Number(project.record_count || 0), 0)
  const registerPreviewProjects = projects.slice(0, 5)

  const filteredProjects = projects.filter((p) => {
    if (searchText && !`${p.name}${p.owner_unit}`.toLowerCase().includes(searchText.toLowerCase())) return false
    if (statusFilter && p.status !== statusFilter) return false
    if (typeFilter && p.type !== typeFilter) return false
    return true
  })

  useEffect(() => {
    if (gitpegCallbackHandled || typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')?.trim() || ''
    if (!code) {
      setGitpegCallbackHandled(true)
      return
    }
    if (!appReady || !canUseEnterpriseApi || !enterprise?.id) return

    const projectId = params.get('project_id')?.trim() || params.get('projectId')?.trim() || ''
    const sessionId = params.get('session_id')?.trim() || params.get('sessionId')?.trim() || ''
    const registrationId = params.get('registration_id')?.trim() || params.get('registrationId')?.trim() || ''
    const cleanCallbackParams = () => {
      const url = new URL(window.location.href)
      ;[
        'code',
        'session_id',
        'sessionId',
        'registration_id',
        'registrationId',
        'project_id',
        'projectId',
        'enterprise_id',
        'enterpriseId',
      ].forEach((key) => url.searchParams.delete(key))
      const nextSearch = url.searchParams.toString()
      const nextUrl = `${url.pathname}${nextSearch ? `?${nextSearch}` : ''}${url.hash}`
      window.history.replaceState({}, '', nextUrl)
    }

    setGitpegCallbackHandled(true)
    if (!projectId) {
      showToast('GitPeg 已回跳，但缺少 project_id；请确认 return_url 带 project_id 参数，或等待 webhook 自动激活')
      cleanCallbackParams()
      return
    }

    completeGitpegApi(projectId, {
      code,
      session_id: sessionId || undefined,
      registration_id: registrationId || undefined,
      enterprise_id: enterprise.id,
    }).then(async (res) => {
      const payload = res as {
        ok?: boolean
        node_uri?: string
        registration_id?: string
        erp_writeback?: { attempted?: boolean; success?: boolean }
      } | null
      if (!payload?.ok) return

      const refreshed = await listProjectsApi(enterprise.id) as { data?: Parameters<typeof setProjects>[0] } | null
      if (refreshed?.data) {
        setProjects(refreshed.data)
        const activated = refreshed.data.find((p) => p.id === projectId) || null
        if (activated) {
          setCurrentProject(activated)
          setRegisterSuccess({
            id: activated.id,
            name: activated.name,
            uri: activated.v_uri,
          })
        }
      }

      const writeback = payload.erp_writeback
      if (writeback?.attempted && !writeback?.success) {
        showToast('GitPeg 节点已激活，但 ERP 回写失败，请在系统设置检查 ERP 字段映射')
      } else {
        showToast(`GitPeg 节点激活成功：${payload.node_uri || '-'}`)
      }
    }).finally(() => {
      cleanCallbackParams()
    })
  }, [
    gitpegCallbackHandled,
    appReady,
    canUseEnterpriseApi,
    enterprise?.id,
    completeGitpegApi,
    listProjectsApi,
    setProjects,
    setCurrentProject,
    showToast,
  ])

  useEffect(() => {
    setProjectMeta((prev) => {
      let changed = false
      const next = { ...prev }
      const validIds = new Set(projects.map((project) => project.id))

      Object.keys(next).forEach((projectId) => {
        if (!validIds.has(projectId)) {
          delete next[projectId]
          changed = true
        }
      })

      projects.forEach((project) => {
        const derived = projectMetaFromRow(project)
        if (!derived) return
        const existing = next[project.id]
        const same = existing && JSON.stringify(existing) === JSON.stringify(derived)
        if (!same) {
          next[project.id] = derived
          changed = true
        }
      })

      return changed ? next : prev
    })
  }, [projects, members.length])

  useEffect(() => {
    if (registerSuccess) {
      setVpathStatus('available')
      return
    }
    if (!regForm.name.trim() || !regForm.type) {
      setVpathStatus('checking')
      return
    }
    setVpathStatus('checking')
    const timer = setTimeout(() => {
      const taken = projects.some((p) => p.v_uri === regUri)
      setVpathStatus(taken ? 'taken' : 'available')
    }, 420)
    return () => clearTimeout(timer)
  }, [projects, regForm.name, regForm.type, regUri, registerSuccess])

  useEffect(() => {
    if (activeTab !== 'proof' || !proj?.id) return
    let cancelled = false
    setProofLoading(true)
    Promise.all([
      listProofs(proj.id),
      proofStatsApi(proj.id),
      proj.v_uri ? proofNodeTreeApi(proj.v_uri) : Promise.resolve(null),
    ]).then(([listRes, statsRes, treeRes]) => {
      if (cancelled) return
      const listPayload = listRes as { data?: typeof proofRows } | null
      const statsPayload = statsRes as {
        total?: number
        by_type?: Record<string, number>
        by_action?: Record<string, number>
      } | null
      const treePayload = treeRes as { data?: Array<{ uri?: string; node_type?: string; status?: string }> } | null

      setProofRows(listPayload?.data || [])
      setProofStats({
        total: Number(statsPayload?.total || 0),
        by_type: statsPayload?.by_type || {},
        by_action: statsPayload?.by_action || {},
      })
      setProofNodeRows(treePayload?.data || [])
    }).finally(() => {
      if (!cancelled) setProofLoading(false)
    })
    return () => { cancelled = true }
  }, [activeTab, proj?.id, proj?.v_uri, listProofs, proofStatsApi, proofNodeTreeApi])

  useEffect(() => {
    if (!canUseEnterpriseApi || (activeTab !== 'projects' && activeTab !== 'settings')) return
    listAutoregProjectsApi(20).then((res) => {
      const payload = res as {
        items?: Array<{
          project_code?: string
          project_name?: string
          project_uri?: string
          site_uri?: string
          updated_at?: string
          source_system?: string
        }>
      } | null
      setAutoregRows(payload?.items || [])
    })
  }, [activeTab, canUseEnterpriseApi, listAutoregProjectsApi])

  useEffect(() => {
    if (!appReady || !canUseEnterpriseApi || !enterprise?.id) return
    let cancelled = false
    listProjectsApi(enterprise.id).then((res) => {
      if (cancelled) return
      const payload = res as { data?: Parameters<typeof setProjects>[0] } | null
      if (!payload?.data) return
      setProjects(payload.data)
      if (!currentProject?.id && payload.data.length > 0) {
        setCurrentProject(payload.data[0])
      }
    })
    return () => { cancelled = true }
  }, [appReady, canUseEnterpriseApi, enterprise?.id, listProjectsApi, setProjects, setCurrentProject])

  const handleVerifyProof = async (proofId: string) => {
    setProofVerifying(proofId)
    const res = await verifyProof(proofId) as { valid?: boolean; chain_length?: number } | null
    if (res?.valid) {
      showToast(`Proof 校验通过（链长 ${res.chain_length ?? 0}）`)
    } else {
      showToast('Proof 校验失败或不存在')
    }
    setProofVerifying(null)
  }

  useEffect(() => {
    if (!appReady || !canUseEnterpriseApi || !enterprise?.id) return
    const needTeamOrSettings =
      activeTab === 'team' ||
      activeTab === 'permissions' ||
      activeTab === 'settings'
    if (!needTeamOrSettings) return

    listMembers(enterprise.id).then((res) => {
      const r = res as { data?: Array<{
        id: string
        name: string
        title?: string
        email?: string
        dto_role?: string
        projects?: string[]
      }> } | null
      if (!r?.data || r.data.length === 0) return
      const roleFallback = (role?: string): TeamRole => {
        const normalized = String(role || '').toUpperCase()
        if (normalized === 'OWNER' || normalized === 'SUPERVISOR' || normalized === 'AI' || normalized === 'PUBLIC') {
          return normalized as TeamRole
        }
        return 'PUBLIC'
      }
      const mapped = r.data.map((m, idx) => ({
        id: m.id,
        name: m.name || '未命名成员',
        title: m.title || roleToTitle(roleFallback(m.dto_role)),
        email: m.email || '',
        role: roleFallback(m.dto_role),
        color: ['#1A56DB', '#059669', '#7C3AED', '#D97706', '#0891B2'][idx % 5],
        projects: m.projects || [],
      }))
      setMembers(mapped)
      setMemberRoleDrafts(toRoleDraftMap(mapped))
    })

    getSettings(enterprise.id).then((res) => {
      const r = res as {
        enterprise?: { name?: string; v_uri?: string; credit_code?: string }
        settings?: Partial<SettingsState> & {
          permissionMatrix?: Array<Partial<PermissionRow> & { role?: string }>
          erpnextUrl?: string
          erpnextSiteName?: string
          erpnextApiKey?: string
          erpnextApiSecret?: string
          erpnextUsername?: string
          erpnextPassword?: string
          erpnextProjectDoctype?: string
          erpnextProjectLookupField?: string
          erpnextProjectLookupValue?: string
          erpnextGitpegProjectUriField?: string
          erpnextGitpegSiteUriField?: string
          erpnextGitpegStatusField?: string
          erpnextGitpegResultJsonField?: string
          erpnextGitpegRegistrationIdField?: string
          erpnextGitpegNodeUriField?: string
          erpnextGitpegShellUriField?: string
          erpnextGitpegProofHashField?: string
          erpnextGitpegIndustryProfileIdField?: string
        }
      } | null
      if (!r?.settings) return
      const {
        permissionMatrix: matrixFromApi,
        erpnextUrl,
        erpnextSiteName,
        erpnextApiKey,
        erpnextApiSecret,
        erpnextUsername,
        erpnextPassword,
        erpnextProjectDoctype,
        erpnextProjectLookupField,
        erpnextProjectLookupValue,
        erpnextGitpegProjectUriField,
        erpnextGitpegSiteUriField,
        erpnextGitpegStatusField,
        erpnextGitpegResultJsonField,
        erpnextGitpegRegistrationIdField,
        erpnextGitpegNodeUriField,
        erpnextGitpegShellUriField,
        erpnextGitpegProofHashField,
        erpnextGitpegIndustryProfileIdField,
        ...settingsFromApi
      } = r.settings
      setSettings((prev) => ({ ...prev, ...settingsFromApi }))
      setErpDraft((prev) => ({
        ...prev,
        url: erpnextUrl ?? prev.url,
        siteName: erpnextSiteName ?? prev.siteName,
        apiKey: erpnextApiKey ?? prev.apiKey,
        apiSecret: erpnextApiSecret ?? prev.apiSecret,
        username: erpnextUsername ?? prev.username,
        password: erpnextPassword ?? prev.password,
      }))
      setErpWritebackDraft((prev) => ({
        ...prev,
        projectDoctype: erpnextProjectDoctype ?? prev.projectDoctype,
        projectLookupField: erpnextProjectLookupField ?? prev.projectLookupField,
        projectLookupValue: erpnextProjectLookupValue ?? prev.projectLookupValue,
        gitpegProjectUriField: erpnextGitpegProjectUriField ?? prev.gitpegProjectUriField,
        gitpegSiteUriField: erpnextGitpegSiteUriField ?? prev.gitpegSiteUriField,
        gitpegStatusField: erpnextGitpegStatusField ?? prev.gitpegStatusField,
        gitpegResultJsonField: erpnextGitpegResultJsonField ?? prev.gitpegResultJsonField,
        gitpegRegistrationIdField: erpnextGitpegRegistrationIdField ?? prev.gitpegRegistrationIdField,
        gitpegNodeUriField: erpnextGitpegNodeUriField ?? prev.gitpegNodeUriField,
        gitpegShellUriField: erpnextGitpegShellUriField ?? prev.gitpegShellUriField,
        gitpegProofHashField: erpnextGitpegProofHashField ?? prev.gitpegProofHashField,
        gitpegIndustryProfileIdField: erpnextGitpegIndustryProfileIdField ?? prev.gitpegIndustryProfileIdField,
      }))
      if (matrixFromApi) {
        const matrix = normalizePermissionMatrix(matrixFromApi)
        setPermissionMatrix(matrix)
        setPermissionTemplate(detectPermissionTemplate(matrix))
      }
      if (r.enterprise) {
        setEnterpriseInfo((prev) => ({
          ...prev,
          name: r.enterprise?.name || prev.name,
          vUri: r.enterprise?.v_uri || prev.vUri,
          creditCode: r.enterprise?.credit_code || prev.creditCode,
        }))
      }
    })
  }, [appReady, canUseEnterpriseApi, enterprise?.id, activeTab, listMembers, getSettings])

  const normalizeDateOnly = (value?: string): string => {
    const text = String(value || '').trim()
    if (!text) return ''
    const match = text.match(/^(\d{4}-\d{2}-\d{2})/)
    return match ? match[1] : ''
  }

  const pullErpProjectBinding = async () => {
    if (!settings.erpnextSync) {
      showToast('ERP 同步未启用，无需拉取 ERP 项目')
      return
    }
    if (!canUseEnterpriseApi || !enterprise?.id) {
      showToast('当前环境未连接企业后端，无法从 ERP 拉取项目')
      return
    }
    const lookupCode = String(regForm.erp_project_code || '').trim()
    const lookupName = String(regForm.erp_project_name || '').trim()
    if (!lookupCode) {
      showToast('请先填写 ERP 项目编码（如 PROJ-0001）')
      return
    }
    setErpBindingLoading(true)
    const res = await getErpProjectBasicsApi({
      enterprise_id: enterprise.id,
      project_code: lookupCode,
      ...(lookupName ? { project_name: lookupName } : {}),
    }) as {
      project_basics?: {
        project_code?: string
        project_name?: string
        owner_unit?: string
        contractor?: string
        supervisor?: string
        contract_no?: string
        start_date?: string
        end_date?: string
        description?: string
      }
    } | null
    setErpBindingLoading(false)
    const basics = res?.project_basics
    if (!basics) {
      setErpBinding({ success: false, code: lookupCode, name: '', reason: 'fetch_failed' })
      return
    }
    const boundCode = String(basics.project_code || lookupCode).trim()
    const boundName = String(basics.project_name || '').trim()
    if (!boundCode || !boundName) {
      setErpBinding({ success: false, code: boundCode || lookupCode, name: boundName, reason: 'missing_basics' })
      showToast('ERP 返回缺少项目编码或项目名称，无法绑定')
      return
    }

    setRegForm((prev) => ({
      ...prev,
      erp_project_code: boundCode,
      erp_project_name: boundName,
      owner_unit: String(basics.owner_unit || prev.owner_unit || '').trim(),
      contractor: String(basics.contractor || prev.contractor || '').trim(),
      supervisor: String(basics.supervisor || prev.supervisor || '').trim(),
      contract_no: String(basics.contract_no || prev.contract_no || '').trim(),
      start_date: normalizeDateOnly(basics.start_date) || prev.start_date,
      end_date: normalizeDateOnly(basics.end_date) || prev.end_date,
      description: String(basics.description || prev.description || '').trim(),
    }))
    setErpBinding({
      success: true,
      code: boundCode,
      name: boundName,
      reason: '',
    })
    showToast(`ERP 绑定成功：${boundCode} / ${boundName}`)
  }

  const nextRegStep = () => {
    if (registerStep === 1 && (!regForm.name || !regForm.owner_unit || !regForm.type)) {
      showToast('请先完成项目基本信息')
      return
    }
    if (
      registerStep === 1 &&
      settings.erpnextSync &&
      (!erpBinding.success
        || erpBinding.code !== String(regForm.erp_project_code || '').trim()
        || erpBinding.name !== String(regForm.erp_project_name || '').trim())
    ) {
      showToast('ERP 同步已启用，请先点击“从 ERP 拉取并绑定”')
      return
    }
    if (registerStep === 2 && regInspectionTypes.length === 0) {
      showToast('请至少选择 1 个主要检测类型')
      return
    }
    if (registerStep === 3 && zeroPersonnelCount === 0 && zeroEquipmentCount === 0) {
      showToast('零号台帐至少需要 1 名人员或 1 台仪器')
      return
    }
    setRegisterStep((s) => Math.min(4, s + 1))
  }
  const prevRegStep = () => setRegisterStep((s) => Math.max(1, s - 1))

  const addContractSeg = () => setContractSegs((prev) => [...prev, { name: `新标段${prev.length + 1}`, range: '' }])
  const addStructure = () => setStructures((prev) => [...prev, { kind: '桥梁', name: '', code: '' }])
  const resetRegister = () => {
    setRegisterStep(1)
    setRegisterSuccess(null)
    setErpBindingLoading(false)
    setErpBinding({ success: false, code: '', name: '', reason: 'pending' })
    setRegForm({
      name: '',
      type: 'highway',
      owner_unit: '',
      erp_project_code: '',
      erp_project_name: '',
      contractor: '',
      supervisor: '',
      contract_no: '',
      start_date: '',
      end_date: '',
      description: '',
      seg_start: 'K0+000',
      seg_end: 'K100+000',
    })
    setContractSegs([{ name: '一标段', range: 'K0~K30' }])
    setStructures([{ kind: '桥梁', name: '沁河大桥', code: 'QH-B01' }])
    setRegInspectionTypes(['flatness', 'crack'])
    setSegType('km')
    setPermTemplate('standard')
    setRegKmInterval(20)
    setZeroLedgerTab('personnel')
    setZeroPersonnel([
      { id: 'zp-1', name: '石玉山', title: '项目负责人', dtoRole: 'OWNER', certificate: '一级建造师' },
      { id: 'zp-2', name: '王质检', title: '质检员', dtoRole: 'AI', certificate: '质检员证' },
    ])
    setZeroEquipment([
      { id: 'ze-1', name: '灌砂筒', modelNo: 'BZY-001', inspectionItem: '压实度', validUntil: '2027-03-01' },
      { id: 'ze-2', name: '弯沉仪', modelNo: 'BZY-002', inspectionItem: '弯沉值', validUntil: '2026-12-31' },
    ])
    setZeroSubcontracts([{ id: 'zs-1', unitName: '', content: '路面施工', range: '' }])
    setZeroMaterials([{ id: 'zm-1', name: '沥青混合料', spec: 'AC-13C', supplier: '', freq: '每批次检测' }])
  }

  const submitRegister = async () => {
    if (!regForm.name || !regForm.owner_unit) {
      showToast('请先填写项目名称和业主单位')
      return
    }
    if (settings.erpnextSync && (!canUseEnterpriseApi || !enterprise?.id)) {
      showToast('ERP 同步已启用，当前环境不支持离线注册，请连接后端后重试')
      return
    }
    if (settings.erpnextSync && !regForm.erp_project_code.trim()) {
      showToast('ERP 同步已启用，请填写 ERP 项目编码（如 PROJ-0001）')
      return
    }
    if (
      settings.erpnextSync &&
      (!erpBinding.success
        || erpBinding.code !== String(regForm.erp_project_code || '').trim()
        || erpBinding.name !== String(regForm.erp_project_name || '').trim())
    ) {
      showToast('请先从 ERP 拉取并绑定项目，再确认注册')
      return
    }
    if (projects.some((p) => p.v_uri === regUri)) {
      setVpathStatus('taken')
      showToast('该 v:// 节点已存在，请修改项目名称或类型')
      return
    }

    const zeroPersonnelPayload = zeroPersonnel
      .map((row) => ({
        name: row.name.trim(),
        title: row.title.trim(),
        dto_role: row.dtoRole,
        certificate: row.certificate.trim(),
        executor_uri: buildExecutorUri(row.name),
      }))
      .filter((row) => row.name || row.title || row.certificate)

    const zeroEquipmentPayload = zeroEquipment
      .map((row) => {
        const validity = getEquipmentValidity(row.validUntil)
        return {
          name: row.name.trim(),
          model_no: row.modelNo.trim(),
          inspection_item: row.inspectionItem.trim(),
          valid_until: row.validUntil,
          toolpeg_uri: buildToolUri(row.name, row.modelNo),
          status: validity.label,
        }
      })
      .filter((row) => row.name || row.model_no)

    const zeroSubcontractsPayload = zeroSubcontracts
      .map((row) => ({
        unit_name: row.unitName.trim(),
        content: row.content.trim(),
        range: row.range.trim(),
        node_uri: buildSubcontractUri(row.unitName),
      }))
      .filter((row) => row.unit_name || row.content || row.range)

    const zeroMaterialsPayload = zeroMaterials
      .map((row) => ({
        name: row.name.trim(),
        spec: row.spec.trim(),
        supplier: row.supplier.trim(),
        freq: row.freq.trim(),
      }))
      .filter((row) => row.name || row.spec || row.supplier || row.freq)

    if (canUseEnterpriseApi && enterprise?.id) {
      const created = await createProjectApi({
        enterprise_id: enterprise.id,
        name: regForm.name,
        type: regForm.type,
        owner_unit: regForm.owner_unit,
        erp_project_code: (settings.erpnextSync ? erpBinding.code : regForm.erp_project_code) || undefined,
        erp_project_name: (settings.erpnextSync ? erpBinding.name : regForm.erp_project_name) || undefined,
        contractor: regForm.contractor || undefined,
        supervisor: regForm.supervisor || undefined,
        contract_no: regForm.contract_no || undefined,
        start_date: regForm.start_date || undefined,
        end_date: regForm.end_date || undefined,
        description: regForm.description || undefined,
        seg_type: segType,
        seg_start: regForm.seg_start || undefined,
        seg_end: regForm.seg_end || undefined,
        km_interval: regKmInterval,
        inspection_types: regInspectionTypes,
        contract_segs: contractSegs,
        structures,
        zero_personnel: zeroPersonnelPayload,
        zero_equipment: zeroEquipmentPayload,
        zero_subcontracts: zeroSubcontractsPayload,
        zero_materials: zeroMaterialsPayload,
        zero_sign_status: 'pending',
        qc_ledger_unlocked: false,
        perm_template: permTemplate,
      }) as {
        id?: string
        v_uri?: string
        name?: string
        erp_project_code?: string
        erp_project_name?: string
        autoreg_sync?: {
          enabled?: boolean
          success?: boolean
          pending_activation?: boolean
          skipped?: boolean
          reason?: string
          autoreg?: {
            hosted_register_url?: string
            session_id?: string
            expires_at?: string
          }
          erp_writeback?: {
            attempted?: boolean
            success?: boolean
            reason?: string
          }
        }
      } | null

      if (!created?.id) return

      const refreshed = await listProjectsApi(enterprise.id) as { data?: Parameters<typeof setProjects>[0] } | null
      let createdProject: Parameters<typeof setCurrentProject>[0] = null
      if (refreshed?.data && refreshed.data.length > 0) {
        setProjects(refreshed.data)
        createdProject = refreshed.data.find((p) => p.id === created.id) || null
      } else {
        const fallbackProject = {
          id: created.id,
          enterprise_id: enterprise.id,
          v_uri: created.v_uri || regUri,
          name: created.name || regForm.name,
          erp_project_code: created.erp_project_code || (settings.erpnextSync ? erpBinding.code : regForm.erp_project_code) || '',
          erp_project_name: created.erp_project_name || (settings.erpnextSync ? erpBinding.name : regForm.erp_project_name) || '',
          type: regForm.type,
          owner_unit: regForm.owner_unit,
          contractor: regForm.contractor || '',
          supervisor: regForm.supervisor || '',
          contract_no: regForm.contract_no || '',
          start_date: regForm.start_date || '',
          end_date: regForm.end_date || '',
          status: 'active' as const,
          record_count: 0,
          photo_count: 0,
          proof_count: 0,
        }
        const nextProjects = [fallbackProject, ...projects.filter((p) => p.id !== fallbackProject.id)]
        setProjects(nextProjects)
        createdProject = fallbackProject
        showToast('项目已创建，项目列表刷新超时或为空，已本地兜底展示')
      }
      if (createdProject) {
        setCurrentProject(createdProject)
      }

      setProjectMeta((prev) => ({
        ...prev,
        [created.id as string]: {
          segType,
          segStart: regForm.seg_start,
          segEnd: regForm.seg_end,
          kmInterval: regKmInterval,
          inspectionTypes: regInspectionTypes,
          contractSegs,
          structures,
          zeroPersonnel: normalizeZeroPersonnelRows(zeroPersonnelPayload),
          zeroEquipment: normalizeZeroEquipmentRows(zeroEquipmentPayload),
          zeroSubcontracts: normalizeZeroSubcontractRows(zeroSubcontractsPayload),
          zeroMaterials: normalizeZeroMaterialRows(zeroMaterialsPayload),
          zeroSignStatus: 'pending',
          qcLedgerUnlocked: false,
          permTemplate,
          memberCount: members.length,
        },
      }))
      setRegisterSuccess({
        id: created.id,
        name: created.name || regForm.name,
        uri: created.v_uri || regUri,
      })
      if (created.autoreg_sync?.enabled && created.autoreg_sync?.pending_activation) {
        const hostedUrl = created.autoreg_sync?.autoreg?.hosted_register_url
        if (hostedUrl && typeof window !== 'undefined') {
          window.open(hostedUrl, '_blank', 'noopener,noreferrer')
        }
        showToast(hostedUrl
          ? '项目已创建，已打开 GitPeg 注册页，请完成节点激活'
          : '项目已创建，GitPeg 注册会话已创建，请完成节点激活')
      } else if (created.autoreg_sync?.enabled && created.autoreg_sync?.success) {
        const wb = created.autoreg_sync.erp_writeback
        if (wb?.attempted && !wb?.success) {
          showToast('项目注册成功，GitPeg 已登记；ERP 回写失败，可手动重试')
        } else {
          showToast('项目注册成功，已完成自动登记')
        }
      } else if (created.autoreg_sync?.enabled && !created.autoreg_sync?.success) {
        if (created.autoreg_sync?.reason === 'gitpeg_registrar_config_incomplete') {
          showToast('项目注册成功，但 GitPeg Registrar 配置不完整，尚未激活主权节点')
        } else {
          showToast('项目注册成功，但自动登记失败，可手动重试')
        }
      } else {
        showToast('项目注册成功（自动登记未启用）')
      }
      return
    }

    const newId = (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : `66666666-6666-4666-8666-${String(Date.now()).slice(-12).padStart(12, '0')}`
    const localProject = {
      id: newId,
      enterprise_id: proj.enterprise_id,
      v_uri: regUri,
      name: regForm.name,
      erp_project_code: settings.erpnextSync ? erpBinding.code : regForm.erp_project_code,
      erp_project_name: settings.erpnextSync ? erpBinding.name : (regForm.erp_project_name || regForm.name),
      type: regForm.type,
      owner_unit: regForm.owner_unit,
      contractor: regForm.contractor,
      supervisor: regForm.supervisor,
      contract_no: regForm.contract_no,
      start_date: regForm.start_date,
      end_date: regForm.end_date,
      seg_type: segType,
      seg_start: regForm.seg_start,
      seg_end: regForm.seg_end,
      km_interval: regKmInterval,
      inspection_types: regInspectionTypes,
      contract_segs: contractSegs,
      structures,
      zero_personnel: zeroPersonnelPayload,
      zero_equipment: zeroEquipmentPayload,
      zero_subcontracts: zeroSubcontractsPayload,
      zero_materials: zeroMaterialsPayload,
      zero_sign_status: 'pending',
      qc_ledger_unlocked: false,
      perm_template: permTemplate,
      status: 'active' as const,
      record_count: 0,
      photo_count: 0,
      proof_count: 0,
    }
    addProject(localProject)
    setCurrentProject(localProject)
    setProjectMeta((prev) => ({
      ...prev,
      [newId]: {
        segType,
        segStart: regForm.seg_start,
        segEnd: regForm.seg_end,
        kmInterval: regKmInterval,
        inspectionTypes: regInspectionTypes,
        contractSegs,
        structures,
        zeroPersonnel: normalizeZeroPersonnelRows(zeroPersonnelPayload),
        zeroEquipment: normalizeZeroEquipmentRows(zeroEquipmentPayload),
        zeroSubcontracts: normalizeZeroSubcontractRows(zeroSubcontractsPayload),
        zeroMaterials: normalizeZeroMaterialRows(zeroMaterialsPayload),
        zeroSignStatus: 'pending',
        qcLedgerUnlocked: false,
        permTemplate,
        memberCount: members.length,
      },
    }))
    setRegisterSuccess({ id: newId, name: regForm.name, uri: regUri })
    showToast('项目注册成功')
  }

  const addMember = async () => {
    if (!inviteForm.name || !inviteForm.email) {
      showToast('请填写成员姓名和邮箱')
      return
    }
    const invitedProjectIds = inviteForm.projectId === 'all'
      ? projects.map((p) => p.id)
      : inviteForm.projectId
        ? [inviteForm.projectId]
        : [proj.id]
    if (canUseEnterpriseApi && enterprise?.id) {
      const res = await inviteMember({
        enterprise_id: enterprise.id,
        name: inviteForm.name,
        email: inviteForm.email,
        dto_role: inviteForm.role,
        title: roleToTitle(inviteForm.role),
        project_ids: invitedProjectIds,
      }) as { data?: { id: string } } | null

      if (res?.data?.id) {
        const refreshed = await listMembers(enterprise.id) as { data?: Array<{
          id: string
          name: string
          title?: string
          email?: string
          dto_role?: string
          projects?: string[]
        }> } | null
        if (refreshed?.data) {
          const roleFallback = (role?: string): TeamRole => {
            const normalized = String(role || '').toUpperCase()
            if (normalized === 'OWNER' || normalized === 'SUPERVISOR' || normalized === 'AI' || normalized === 'PUBLIC') {
              return normalized as TeamRole
            }
            return 'PUBLIC'
          }
          const mapped = refreshed.data.map((m, idx) => ({
            id: m.id,
            name: m.name || '未命名成员',
            title: m.title || roleToTitle(roleFallback(m.dto_role)),
            email: m.email || '',
            role: roleFallback(m.dto_role),
            color: ['#1A56DB', '#059669', '#7C3AED', '#D97706', '#0891B2'][idx % 5],
            projects: m.projects || [],
          }))
          setMembers(mapped)
          setMemberRoleDrafts(toRoleDraftMap(mapped))
        }
      }
    } else {
      const localId = `u-${Date.now()}`
      setMembers((prev) => [{
        id: localId,
        name: inviteForm.name,
        title: roleToTitle(inviteForm.role),
        email: inviteForm.email,
        role: inviteForm.role,
        color: ['#1A56DB', '#059669', '#7C3AED', '#D97706'][prev.length % 4],
        projects: invitedProjectIds,
      }, ...prev])
      setMemberRoleDrafts((prev) => ({ ...prev, [localId]: inviteForm.role }))
    }

    setInviteForm({ name: '', email: '', role: 'AI', projectId: 'all' })
    setInviteOpen(false)
    showToast('已邀请新成员')
  }

  const removeMember = async (id: string) => {
    if (canUseEnterpriseApi && enterprise?.id) {
      const res = await removeMemberApi(id) as { ok?: boolean } | null
      if (res?.ok) {
        setMembers((prev) => prev.filter((m) => m.id !== id))
        setMemberRoleDrafts((prev) => {
          const next = { ...prev }
          delete next[id]
          return next
        })
      }
    } else {
      setMembers((prev) => prev.filter((m) => m.id !== id))
      setMemberRoleDrafts((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
    }
    showToast('成员已移除')
  }

  const saveMemberRole = async (member: TeamMember) => {
    const nextRole = memberRoleDrafts[member.id] || member.role
    if (nextRole === member.role) {
      showToast('角色未变化')
      return
    }

    if (canUseEnterpriseApi && enterprise?.id) {
      const res = await updateMemberApi(member.id, {
        dto_role: nextRole,
        title: roleToTitle(nextRole),
      }) as { data?: { id?: string } } | null
      if (!res) return
    }

    setMembers((prev) => prev.map((m) => (
      m.id === member.id ? { ...m, role: nextRole, title: roleToTitle(nextRole) } : m
    )))
    showToast(`成员角色已更新：${member.name} -> ${ROLE_LABEL[nextRole]}`)
  }

  const removeProject = async (projectId: string, projectName: string) => {
    const confirmed = typeof window === 'undefined' ? true : window.confirm(`确认删除项目「${projectName}」？`)
    if (!confirmed) return

    if (canUseEnterpriseApi && enterprise?.id) {
      const res = await removeProjectApi(projectId, enterprise.id) as { ok?: boolean } | null
      if (!res?.ok) return
      const refreshed = await listProjectsApi(enterprise.id) as { data?: Parameters<typeof setProjects>[0] } | null
      if (refreshed?.data) {
        setProjects(refreshed.data)
        if (currentProject?.id === projectId) {
          setCurrentProject(refreshed.data[0] || null)
        }
      }
    } else {
      const next = projects.filter((p) => p.id !== projectId)
      setProjects(next)
      if (currentProject?.id === projectId) {
        setCurrentProject(next[0] || null)
      }
    }

    setProjectMeta((prev) => {
      const next = { ...prev }
      delete next[projectId]
      return next
    })
    showToast('项目已删除')
  }

  const retryProjectAutoreg = async (projectId: string, projectName: string) => {
    if (!canUseEnterpriseApi || !enterprise?.id) {
      showToast('演示环境不支持自动登记重试')
      return
    }
    const project = projects.find((p) => p.id === projectId)
    if (!project) {
      showToast('项目不存在，无法执行自动登记')
      return
    }
    setSyncingProjectId(projectId)
    const res = await syncAutoregApi(projectId, {
      enterprise_id: enterprise.id,
      force: true,
      writeback: true,
    }) as {
      ok?: boolean
      result?: {
        pending_activation?: boolean
        reason?: string
        autoreg?: { hosted_register_url?: string }
        erp_writeback?: { attempted?: boolean; success?: boolean }
      }
    } | null
    setSyncingProjectId(null)
    if (!res) return

    if (res.ok) {
      if (res.result?.pending_activation) {
        const hostedUrl = res.result?.autoreg?.hosted_register_url
        if (hostedUrl && typeof window !== 'undefined') {
          window.open(hostedUrl, '_blank', 'noopener,noreferrer')
        }
        showToast(hostedUrl
          ? `项目「${projectName}」已创建 GitPeg 注册会话，已打开激活页`
          : `项目「${projectName}」已创建 GitPeg 注册会话，待完成激活`)
        const latestAutoreg = await listAutoregProjectsApi(20) as { items?: typeof autoregRows } | null
        if (latestAutoreg?.items) setAutoregRows(latestAutoreg.items)
        return
      }
      const wb = res.result?.erp_writeback
      if (wb?.attempted && !wb?.success) {
        showToast(`项目「${projectName}」自动登记成功，ERP 回写失败`)
      } else {
        showToast(`项目「${projectName}」自动登记成功`)
      }
      const latestAutoreg = await listAutoregProjectsApi(20) as { items?: typeof autoregRows } | null
      if (latestAutoreg?.items) setAutoregRows(latestAutoreg.items)
      return
    }

    if (res.result?.reason === 'gitpeg_registrar_config_incomplete') {
      showToast(`项目「${projectName}」未激活：请先配置 GitPeg Registrar 参数`)
      return
    }
    if (settings.gitpegEnabled) {
      showToast(`项目「${projectName}」GitPeg 激活失败，请检查 Registrar 服务与凭证`)
      return
    }

    const directPayload = {
      project_code: project.contract_no || project.id,
      project_name: project.name,
      site_code: project.name,
      site_name: project.name,
      namespace_uri: enterprise.v_uri,
      source_system: 'qcspec',
    }
    const directRes = await registerAutoregProjectApi(directPayload) as { success?: boolean } | null
    if (directRes?.success) {
      showToast(`项目「${projectName}」自动登记成功（直连通道）`)
      const latestAutoreg = await listAutoregProjectsApi(20) as { items?: typeof autoregRows } | null
      if (latestAutoreg?.items) setAutoregRows(latestAutoreg.items)
      return
    }

    const aliasRes = await registerAutoregProjectAliasApi(directPayload) as { success?: boolean } | null
    if (aliasRes?.success) {
      showToast(`项目「${projectName}」自动登记成功（兼容通道）`)
      const latestAutoreg = await listAutoregProjectsApi(20) as { items?: typeof autoregRows } | null
      if (latestAutoreg?.items) setAutoregRows(latestAutoreg.items)
      return
    }

    showToast(`项目「${projectName}」自动登记失败（已尝试 3 条通道）`)
  }

  const directProjectAutoreg = async (projectId: string, projectName: string) => {
    if (!canUseEnterpriseApi || !enterprise?.id) {
      showToast('演示环境不支持直连登记')
      return
    }
    const project = projects.find((p) => p.id === projectId)
    if (!project) {
      showToast('项目不存在，无法执行直连登记')
      return
    }
    if (settings.gitpegEnabled) {
      showToast('当前为 GitPeg Registrar 模式，请使用“重试同步”完成节点激活')
      return
    }
    setSyncingProjectId(projectId)
    const payload = {
      project_code: project.contract_no || project.id,
      project_name: project.name,
      site_code: project.name,
      site_name: project.name,
      namespace_uri: enterprise.v_uri,
      source_system: 'qcspec',
    }
    const primary = await registerAutoregProjectApi(payload) as { success?: boolean } | null
    const fallback = primary?.success
      ? primary
      : await registerAutoregProjectAliasApi(payload) as { success?: boolean } | null
    setSyncingProjectId(null)
    if (!fallback?.success) {
      showToast(`项目「${projectName}」直连登记失败`)
      return
    }
    const latestAutoreg = await listAutoregProjectsApi(20) as { items?: typeof autoregRows } | null
    if (latestAutoreg?.items) setAutoregRows(latestAutoreg.items)
    showToast(`项目「${projectName}」直连登记成功`)
  }

  const persistSettings = async (patch: Partial<SettingsState> & {
    erpnextUrl?: string
    erpnextSiteName?: string
    erpnextApiKey?: string
    erpnextApiSecret?: string
    erpnextUsername?: string
    erpnextPassword?: string
    erpnextProjectDoctype?: string
    erpnextProjectLookupField?: string
    erpnextProjectLookupValue?: string
    erpnextGitpegProjectUriField?: string
    erpnextGitpegSiteUriField?: string
    erpnextGitpegStatusField?: string
    erpnextGitpegResultJsonField?: string
    erpnextGitpegRegistrationIdField?: string
    erpnextGitpegNodeUriField?: string
    erpnextGitpegShellUriField?: string
    erpnextGitpegProofHashField?: string
    erpnextGitpegIndustryProfileIdField?: string
  }) => {
    const next = { ...settings, ...patch }
    setSettings(next)

    if (!canUseEnterpriseApi || !enterprise?.id) {
      showToast('演示环境：已本地保存')
      return
    }

    const res = await saveSettings(enterprise.id, patch) as { settings?: Partial<SettingsState> } | null
    if (res?.settings) {
      setSettings((prev) => ({ ...prev, ...res.settings }))
      showToast('设置已保存')
    }
  }

  const persistEnterpriseInfo = async () => {
    if (!canUseEnterpriseApi || !enterprise?.id) {
      showToast('演示环境：已本地保存')
      return
    }

    const res = await saveSettings(enterprise.id, {
      enterpriseName: enterpriseInfo.name,
      enterpriseVUri: enterpriseInfo.vUri,
      enterpriseCreditCode: enterpriseInfo.creditCode,
    }) as { enterprise?: { name?: string; v_uri?: string; credit_code?: string } } | null

    if (res?.enterprise) {
      setEnterpriseInfo((prev) => ({
        ...prev,
        name: res.enterprise?.name || prev.name,
        vUri: res.enterprise?.v_uri || prev.vUri,
        creditCode: res.enterprise?.credit_code || prev.creditCode,
      }))
    }
    showToast('企业信息已保存')
  }

  const persistReportTemplate = async () => {
    if (settings.reportTemplate === 'custom-upload') {
      if (!reportTemplateFile) {
        showToast('请先选择 Word 模板文件')
        return
      }
      if (!canUseEnterpriseApi || !enterprise?.id) {
        setSettings((prev) => ({
          ...prev,
          reportTemplate: reportTemplateFile.name,
          reportTemplateUrl: '',
        }))
        showToast('演示环境：已本地保存模板名与报告抬头')
        return
      }
      const res = await uploadTemplate(enterprise.id, reportTemplateFile) as {
        settings?: Partial<SettingsState>
      } | null
      if (res?.settings) {
        setSettings((prev) => ({ ...prev, ...res.settings }))
        setReportTemplateFile(null)
      }
      const headerRes = await saveSettings(enterprise.id, {
        reportHeader: settings.reportHeader,
      }) as { settings?: Partial<SettingsState> } | null
      if (headerRes?.settings) {
        setSettings((prev) => ({ ...prev, ...headerRes.settings }))
      }
      showToast('模板与报告抬头已保存')
      return
    }
    await persistSettings({
      reportTemplate: settings.reportTemplate,
      reportHeader: settings.reportHeader,
    })
  }

  const updatePermissionCell = (role: PermissionRole, key: PermissionKey, value: boolean) => {
    setPermissionMatrix((prev) => prev.map((row) => (
      row.role === role ? { ...row, [key]: value } : row
    )))
    setPermissionTemplate('custom')
  }

  const applyPermissionTemplate = (template: Exclude<PermTemplate, 'custom'>) => {
    setPermissionTemplate(template)
    setPermissionMatrix(clonePermissionRows(PERMISSION_TEMPLATES[template]))
  }

  const persistPermissionMatrix = async () => {
    if (!canUseEnterpriseApi || !enterprise?.id) {
      showToast('演示环境：已本地保存')
      return
    }

    const res = await saveSettings(enterprise.id, { permissionMatrix }) as {
      settings?: { permissionMatrix?: Array<Partial<PermissionRow> & { role?: string }> }
    } | null
    if (res?.settings?.permissionMatrix) {
      const matrix = normalizePermissionMatrix(res.settings.permissionMatrix)
      setPermissionMatrix(matrix)
      setPermissionTemplate(detectPermissionTemplate(matrix))
    }
    showToast('权限矩阵已保存')
  }

  const verifyGitpegToken = async () => {
    const baseUrl = settings.gitpegRegistrarBaseUrl.trim()
    const partnerCode = settings.gitpegPartnerCode.trim()
    const industryCode = settings.gitpegIndustryCode.trim()
    const clientId = settings.gitpegClientId.trim()
    const clientSecret = settings.gitpegClientSecret.trim()

    if (!baseUrl || !partnerCode || !industryCode || !clientId || !clientSecret) {
      setGitpegVerifyMsg({
        text: '⚠️ 请填写 Base URL / Partner Code / Industry Code / Client ID / Client Secret',
        color: '#D97706',
      })
      return
    }

    if (!/^https?:\/\//i.test(baseUrl)) {
      setGitpegVerifyMsg({ text: '⚠️ Base URL 需要以 http:// 或 https:// 开头', color: '#D97706' })
      return
    }

    setGitpegVerifying(true)
    setGitpegVerifyMsg({ text: '⏳ 验证中...', color: '#64748B' })
    const res = await testGitpegRegistrar({
      baseUrl,
      partnerCode,
      industryCode,
      clientId,
      clientSecret,
      registrationMode: settings.gitpegRegistrationMode || 'DOMAIN',
      returnUrl: settings.gitpegReturnUrl.trim() || undefined,
      webhookUrl: settings.gitpegWebhookUrl.trim() || undefined,
      moduleCandidates: (settings.gitpegModuleCandidates || []).map((item) => String(item || '').trim()).filter(Boolean),
      timeoutMs: 12000,
    }) as {
      ok?: boolean
      session_id?: string
      warnings?: string[]
      token_exchange_probe?: {
        result?: string
      }
    } | null

    setGitpegVerifying(false)
    if (!res?.ok) {
      setGitpegVerifyMsg({ text: '❌ 联调失败，请查看后端错误提示', color: '#DC2626' })
      return
    }

    const warnings = Array.isArray(res.warnings) ? res.warnings : []
    const probe = res.token_exchange_probe?.result || ''
    if (warnings.length > 0) {
      setGitpegVerifyMsg({
        text: `⚠️ 连通成功（session: ${res.session_id || '-' }），但有告警：${warnings.join('；')}`,
        color: '#D97706',
      })
      return
    }
    if (probe === 'credentials_rejected') {
      setGitpegVerifyMsg({
        text: `⚠️ 会话创建成功（session: ${res.session_id || '-' }），但 client_id/client_secret 可能被拒绝`,
        color: '#D97706',
      })
      return
    }
    setGitpegVerifyMsg({
      text: `✅ 联调成功（session: ${res.session_id || '-' }）`,
      color: '#059669',
    })
  }

  const testWebhook = () => {
    if (!settings.webhookUrl.trim()) {
      setWebhookResult({ text: '⚠️ 请先填写 Webhook URL', color: '#D97706', visible: true })
      return
    }
    setWebhookTesting(true)
    setWebhookResult({ text: '⏳ 发送测试请求...', color: '#64748B', visible: true })
    setTimeout(() => {
      setWebhookTesting(false)
      setWebhookResult({
        text: `✅ 200 OK · {"event":"test","source":"qcspec","ts":${Date.now()}}`,
        color: '#059669',
        visible: true,
      })
    }, 700)
  }

  const testErpConnection = async () => {
    const hasTokenAuth = Boolean(erpDraft.apiKey.trim())
    const hasSessionAuth = Boolean(erpDraft.username.trim() && erpDraft.password.trim())
    if (!erpDraft.url.trim()) {
      setErpTestMsg('⚠️ 请先填写 ERP URL')
      return
    }
    if (!hasTokenAuth && !hasSessionAuth) {
      setErpTestMsg('⚠️ 请填写 API Key 或 用户名+密码')
      return
    }
    setErpTesting(true)
    setErpTestMsg('⏳ 测试连接中...')
    const res = await testErpnext({
      url: erpDraft.url.trim(),
      siteName: erpDraft.siteName.trim() || undefined,
      apiKey: erpDraft.apiKey.trim() || undefined,
      apiSecret: erpDraft.apiSecret.trim() || undefined,
      username: erpDraft.username.trim() || undefined,
      password: erpDraft.password.trim() || undefined,
      timeoutMs: 10000,
    }) as {
      ok?: boolean
      user?: string
      authMode?: string
      latencyMs?: number
    } | null

    setErpTesting(false)
    if (res?.ok) {
      const userLabel = res.user ? `用户 ${res.user}` : '用户已验证'
      const modeLabel = res.authMode ? ` · ${res.authMode}` : ''
      const latencyLabel = typeof res.latencyMs === 'number' ? ` · ${res.latencyMs}ms` : ''
      setErpTestMsg(`✅ ERPNext 连接成功（${userLabel}${modeLabel}${latencyLabel}）`)
      return
    }
    setErpTestMsg('❌ ERPNext 连接失败，请检查 URL、站点名和认证信息')
  }

  const doDemoLogin = (key: keyof typeof QUICK_USERS = 'admin') => {
    const user = QUICK_USERS[key]
    setUser(user, DEMO_ENTERPRISE, `demo-token-${key}`)
    if (!projects.length) {
      setProjects(DEMO_PROJECTS)
      setCurrentProject(DEMO_PROJECTS[0])
    }
    setAppReady(true)
    showToast(`欢迎回来，${user.name}`)
  }

  const fillQuickLogin = (key: keyof typeof QUICK_USERS) => {
    const preset = QUICK_LOGIN_ACCOUNTS.find((item) => item.key === key)
    if (!preset) return
    setLoginForm({
      account: preset.account,
      pass: preset.password,
    })
    showToast(`已填充 ${preset.roleLabel} 账号信息`)
  }

  const quickLoginNow = (key: keyof typeof QUICK_USERS) => {
    fillQuickLogin(key)
    doDemoLogin(key)
  }

  const doLogin = async () => {
    const account = loginForm.account.trim()
    const pass = loginForm.pass
    if (!account || !pass) {
      showToast('请填写账号和密码')
      return
    }

    setLoggingIn(true)
    try {
      const loginRes = await loginApi({
        email: account,
        password: pass,
      }) as {
        access_token?: string
        user_id?: string
        name?: string
        dto_role?: string
        enterprise_id?: string
        v_uri?: string
      } | null

      if (!loginRes?.access_token || !loginRes.user_id || !loginRes.enterprise_id) {
        return
      }

      const enterpriseRes = await getEnterpriseApi(loginRes.enterprise_id) as {
        id?: string
        name?: string
        v_uri?: string
        short_name?: string
        plan?: 'basic' | 'pro' | 'enterprise'
        proof_quota?: number
        proof_used?: number
      } | null

      setUser(
        {
          id: loginRes.user_id,
          enterprise_id: loginRes.enterprise_id,
          v_uri: loginRes.v_uri || '',
          name: loginRes.name || account,
          email: account,
          dto_role: (loginRes.dto_role || 'PUBLIC') as 'PUBLIC' | 'MARKET' | 'AI' | 'SUPERVISOR' | 'OWNER' | 'REGULATOR',
          title: undefined,
        },
        {
          id: enterpriseRes?.id || loginRes.enterprise_id,
          name: enterpriseRes?.name || '企业',
          v_uri: enterpriseRes?.v_uri || 'v://cn/enterprise/',
          short_name: enterpriseRes?.short_name,
          plan: enterpriseRes?.plan || 'enterprise',
          proof_quota: Number(enterpriseRes?.proof_quota || 0),
          proof_used: Number(enterpriseRes?.proof_used || 0),
        },
        loginRes.access_token
      )
      setProjects([])
      setCurrentProject(null)
      setAppReady(true)
      showToast(`欢迎回来，${loginRes.name || account}`)
    } finally {
      setLoggingIn(false)
    }
  }

  const doLogout = async () => {
    try {
      await logoutApi()
    } catch {
      // Ignore remote logout failures and always clear local session.
    }
    logout()
    setAppReady(false)
    setLoginTab('login')
    setLoginForm({ account: '', pass: '' })
    showToast('已退出登录')
  }

  const doRegisterEnterprise = async () => {
    const adminPhone = entForm.adminPhone.trim()
    if (!entForm.name || !adminPhone || !entForm.pass) {
      showToast('请完整填写企业注册信息')
      return
    }
    if (adminPhone.includes('@')) {
      showToast('管理员手机号请输入 11 位手机号码，不能填写邮箱')
      return
    }
    if (!/^1\d{10}$/.test(adminPhone)) {
      showToast('管理员手机号格式不正确，请输入 11 位手机号码')
      return
    }
    const res = await registerEnterpriseApi({
      name: entForm.name.trim(),
      adminPhone,
      password: entForm.pass,
      creditCode: entForm.uscc.trim() || undefined,
    }) as {
      ok?: boolean
      account?: string
    } | null
    if (!res?.ok) return
    setLoginForm({
      account: res.account || adminPhone,
      pass: entForm.pass,
    })
    setEntForm({ name: '', adminPhone: '', pass: '', uscc: '' })
    showToast('企业注册成功，请使用管理员账号登录')
    setLoginTab('login')
  }

  const openProjectDetail = async (id: string, edit = false) => {
    setProjectDetailId(id)
    setProjectDetailOpen(true)
    let selectedProject = projects.find((p) => p.id === id) || null
    if (canUseEnterpriseApi) {
      const latest = await getProjectByIdApi(id) as Record<string, unknown> | null
      if (latest?.id) {
        const mergedProjects = projects.map((p) => (p.id === id ? { ...p, ...latest } : p))
        setProjects(mergedProjects)
        if (currentProject?.id === id) {
          const mergedCurrent = mergedProjects.find((p) => p.id === id) || null
          setCurrentProject(mergedCurrent)
        }
        selectedProject = { ...(selectedProject || {}), ...latest } as typeof selectedProject
      }
    }
    if (!edit) {
      setDetailEdit(false)
      setDetailProjectDraft(null)
      setDetailDraft(null)
      return
    }
    if (!selectedProject) return
    const meta = projectMeta[id]
    setDetailProjectDraft(buildProjectEditDraft(selectedProject))
    setDetailDraft(normalizeProjectMeta(meta))
    setDetailEdit(true)
  }

  const startEditDetail = () => {
    if (!projectDetailId) return
    if (!detailProject) return
    setDetailProjectDraft(buildProjectEditDraft(detailProject))
    setDetailDraft(normalizeProjectMeta(detailMeta))
    setDetailEdit(true)
  }

  const saveDetailMeta = async () => {
    if (!projectDetailId || !detailDraft || !detailProjectDraft) return
    const name = detailProjectDraft.name.trim()
    const ownerUnit = detailProjectDraft.owner_unit.trim()
    if (!name || !ownerUnit) {
      showToast('项目名称和业主单位不能为空')
      return
    }
    if (detailDraft.inspectionTypes.length === 0) {
      showToast('请至少选择 1 个主要检测类型')
      return
    }

    const patch = {
      name,
      type: detailProjectDraft.type,
      owner_unit: ownerUnit,
      contractor: detailProjectDraft.contractor || '',
      supervisor: detailProjectDraft.supervisor || '',
      contract_no: detailProjectDraft.contract_no || '',
      start_date: detailProjectDraft.start_date || '',
      end_date: detailProjectDraft.end_date || '',
      seg_type: detailDraft.segType,
      seg_start: detailDraft.segStart || '',
      seg_end: detailDraft.segEnd || '',
      km_interval: normalizeKmInterval(detailDraft.kmInterval, 20),
      inspection_types: detailDraft.inspectionTypes,
      contract_segs: detailDraft.contractSegs,
      structures: detailDraft.structures,
      zero_personnel: detailDraft.zeroPersonnel.map((row) => ({
        name: row.name,
        title: row.title,
        dto_role: row.dtoRole,
        certificate: row.certificate,
        executor_uri: buildExecutorUri(row.name),
      })),
      zero_equipment: detailDraft.zeroEquipment.map((row) => ({
        name: row.name,
        model_no: row.modelNo,
        inspection_item: row.inspectionItem,
        valid_until: row.validUntil,
        toolpeg_uri: buildToolUri(row.name, row.modelNo),
        status: getEquipmentValidity(row.validUntil).label,
      })),
      zero_subcontracts: detailDraft.zeroSubcontracts.map((row) => ({
        unit_name: row.unitName,
        content: row.content,
        range: row.range,
        node_uri: buildSubcontractUri(row.unitName),
      })),
      zero_materials: detailDraft.zeroMaterials.map((row) => ({
        name: row.name,
        spec: row.spec,
        supplier: row.supplier,
        freq: row.freq,
      })),
      zero_sign_status: detailDraft.zeroSignStatus,
      qc_ledger_unlocked: detailDraft.qcLedgerUnlocked,
      perm_template: detailDraft.permTemplate,
    }

    if (canUseEnterpriseApi && enterprise?.id) {
      const saved = await updateProjectApi(projectDetailId, patch) as { id?: string } | null
      if (!saved) return
    }

    const nextProjects = projects.map((p) => (p.id === projectDetailId ? { ...p, ...patch } : p))
    setProjects(nextProjects)
    if (currentProject?.id === projectDetailId) {
      const nextCurrent = nextProjects.find((p) => p.id === projectDetailId) || null
      setCurrentProject(nextCurrent)
    }
    setProjectMeta((prev) => ({ ...prev, [projectDetailId]: detailDraft }))
    setDetailEdit(false)
    setDetailProjectDraft(null)
    showToast(canUseEnterpriseApi ? '项目信息已保存' : '演示环境：项目信息已本地保存')
  }

  if (sessionChecking) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <div className="l-hint">会话校验中...</div>
        </div>
      </div>
    )
  }

  if (!appReady) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <div className="login-logo">
            <div className="login-brand"><span className="qc">QC</span><span className="spec">Spec</span></div>
            <div className="login-tagline">工程质检管理平台 | 企业注册中心</div>
          </div>

          <div className="login-tab">
            <button className={`ltab ${loginTab === 'login' ? 'active' : ''}`} onClick={() => setLoginTab('login')}>登录</button>
            <button className={`ltab ${loginTab === 'register' ? 'active' : ''}`} onClick={() => setLoginTab('register')}>注册企业</button>
          </div>

          {loginTab === 'login' && (
            <div className="login-form">
              <input className="l-input" value={loginForm.account} onChange={(e) => setLoginForm({ ...loginForm, account: e.target.value })} placeholder="手机号 / 邮箱" />
              <input className="l-input" type="password" value={loginForm.pass} onChange={(e) => setLoginForm({ ...loginForm, pass: e.target.value })} placeholder="密码" />
              <button className="l-btn" onClick={doLogin} disabled={loggingIn}>{loggingIn ? '登录中...' : '登录'}</button>
              <div className="l-hint">演示账号快速登录</div>
              <div className="demo-accounts">
                <div className="demo-title">Demo Accounts</div>
                {QUICK_LOGIN_ACCOUNTS.map((item) => {
                  const profile = QUICK_USERS[item.key]
                  return (
                    <div className="demo-item" key={item.key}>
                      <div className="demo-line">
                        <strong>{item.account}</strong>
                        <span>{item.roleLabel}</span>
                      </div>
                      <div className="demo-subline">
                        姓名：{profile.name} · 密码：{item.password}
                      </div>
                      <div className="demo-subline">{item.desc}</div>
                      <div className="demo-actions">
                        <button className="demo-btn demo-btn-ghost" onClick={() => fillQuickLogin(item.key)}>填充</button>
                        <button className="demo-btn demo-btn-primary" onClick={() => quickLoginNow(item.key)}>快捷登录</button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {loginTab === 'register' && (
            <div className="login-form">
              <input className="l-input" value={entForm.name} onChange={(e) => setEntForm({ ...entForm, name: e.target.value })} placeholder="企业名称" />
              <input className="l-input" value={entForm.adminPhone} onChange={(e) => setEntForm({ ...entForm, adminPhone: e.target.value })} placeholder="管理员手机号（11位）" />
              <input className="l-input" type="password" value={entForm.pass} onChange={(e) => setEntForm({ ...entForm, pass: e.target.value })} placeholder="登录密码" />
              <input className="l-input" value={entForm.uscc} onChange={(e) => setEntForm({ ...entForm, uscc: e.target.value })} placeholder="统一社会信用代码" />
              <button className="l-btn" style={{ background: 'var(--green)' }} onClick={doRegisterEnterprise}>注册企业账号</button>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell visible">
      <div className={`sidebar ${sidebarOpen ? 'open' : ''}`} style={{ transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)' }}>
        <div className="sidebar-brand">
          <div className="sb-logo"><span className="qc">QC</span><span className="spec">Spec</span></div>
          <div className="sb-version">v2.0 | qcspec.com</div>
        </div>

        <div className="sidebar-nav">
          {NAV_SECTIONS.map((section) => (
            <div className="nav-section" key={section.label}>
              <div className="nav-section-label">{section.label}</div>
              {section.keys.map((key) => {
                const item = NAV.find((n) => n.key === key)
                if (!item) return null
                const isActive = activeTab === item.key
                return (
                  <div key={item.key} className={`nav-item ${isActive ? 'active' : ''}`} onClick={() => setActiveTab(item.key)}>
                    <span className="nav-icon">{item.icon}</span>
                    <span>{item.label}</span>
                    {item.key === 'projects' && <span className="nav-badge">{projects.length}</span>}
                  </div>
                )
              })}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-card">
            <div className="user-avatar">{(user?.name || '中')[0]}</div>
            <div className="user-info">
              <div className="user-name">{user?.name || DEMO_USER.name}</div>
              <div className="user-role">{user?.title || '超级管理员'}</div>
            </div>
            <div className="logout-btn" onClick={doLogout} title="退出登录">⏻</div>
          </div>
        </div>
      </div>

      <div className="main-content" style={{ marginLeft: sidebarOpen ? 220 : 0 }}>
        <div className="topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={() => setSidebarOpen(!sidebarOpen)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: '#6B7280', padding: 4 }}>☰</button>
            <div className="topbar-title">{NAV.find((n) => n.key === activeTab)?.label || '控制台'}</div>
          </div>
          <div className="topbar-right">
            <select value={proj.id} onChange={(e) => { const p = projects.find((x) => x.id === e.target.value); if (p) setCurrentProject(p) }} style={{ background: '#F0F4F8', border: '1px solid #E2E8F0', borderRadius: 8, padding: '6px 12px', fontSize: 13, fontFamily: 'var(--sans)', outline: 'none' }}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <button className="topbar-btn btn-outline" onClick={() => setActiveTab('register')}>＋ 注册项目</button>
            <button className="topbar-btn btn-blue" onClick={() => setActiveTab('inspection')}>📷 开始质检</button>
            <button className="topbar-btn btn-logout" onClick={doLogout}>退出登录</button>
          </div>
        </div>

        <div className="content-body">
          {activeTab === 'dashboard' && <Dashboard />}

          {activeTab === 'inspection' && <InspectionPage />}

          {activeTab === 'photos' && <PhotosPage />}

          {activeTab === 'reports' && <ReportsPage />}

          {activeTab === 'proof' && (
            <Card title="Proof 存证链" icon="🔒">
              <VPathDisplay uri={proj.v_uri} />
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
                  gap: 8,
                  marginBottom: 10,
                }}
              >
                <div style={{ background: '#F8FAFF', border: '1px solid #DBEAFE', borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 12, color: '#64748B' }}>总存证</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#1A56DB', lineHeight: 1.2 }}>{proofStats.total}</div>
                </div>
                <div style={{ background: '#F8FAFF', border: '1px solid #E2E8F0', borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 12, color: '#64748B' }}>对象类型</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#0F172A', lineHeight: 1.2 }}>
                    {Object.keys(proofStats.by_type).length}
                  </div>
                </div>
                <div style={{ background: '#F8FAFF', border: '1px solid #E2E8F0', borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 12, color: '#64748B' }}>动作类型</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#0F172A', lineHeight: 1.2 }}>
                    {Object.keys(proofStats.by_action).length}
                  </div>
                </div>
              </div>
              <div style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, marginBottom: 12, background: '#FCFDFF' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#0F172A', marginBottom: 8 }}>节点树（v://）</div>
                {proofNodeRows.length === 0 ? (
                  <div style={{ fontSize: 12, color: '#94A3B8' }}>当前项目暂无节点数据</div>
                ) : (
                  <div style={{ display: 'grid', gap: 5 }}>
                    {proofNodeRows.slice(0, 8).map((node, idx) => (
                      <div
                        key={`${node.uri || 'node'}-${idx}`}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 86px 70px',
                          gap: 8,
                          alignItems: 'center',
                          fontSize: 12,
                        }}
                      >
                        <span style={{ fontFamily: 'monospace', color: '#334155', wordBreak: 'break-all' }}>{node.uri || '-'}</span>
                        <span style={{ color: '#64748B' }}>{node.node_type || '-'}</span>
                        <span style={{ color: '#1A56DB', fontWeight: 700 }}>{node.status || '-'}</span>
                      </div>
                    ))}
                    {proofNodeRows.length > 8 && (
                      <div style={{ fontSize: 12, color: '#64748B' }}>仅展示前 8 条，共 {proofNodeRows.length} 条</div>
                    )}
                  </div>
                )}
              </div>
              {proofLoading ? (
                <div style={{ fontSize: 13, color: '#64748B', padding: '8px 2px' }}>加载中...</div>
              ) : proofRows.length === 0 ? (
                <div style={{ fontSize: 13, color: '#94A3B8', padding: '8px 2px' }}>暂无 Proof 记录</div>
              ) : (
                <div style={{ display: 'grid', gap: 8 }}>
                  {proofRows.map((p) => (
                    <div key={p.proof_id} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, background: '#F8FAFC' }}>
                      <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#0F172A', fontWeight: 700 }}>{p.proof_id}</div>
                      <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
                        {(p.object_type || 'object')} · {(p.action || 'create')} · {p.summary || '-'}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                        <span style={{ fontSize: 12, color: '#94A3B8' }}>
                          {p.created_at ? new Date(p.created_at).toLocaleString('zh-CN').slice(0, 16) : '-'}
                        </span>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleVerifyProof(p.proof_id)}
                          disabled={proofVerifying === p.proof_id}
                        >
                          {proofVerifying === p.proof_id ? '校验中...' : '校验'}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          {activeTab === 'projects' && (
            <div>
              <Card title="项目列表" icon="🏗️">
                <div className="toolbar">
                  <input className="search-input" value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="搜索项目/业主" />
                  <select className="filter-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="">全部状态</option><option value="active">进行中</option><option value="pending">待开始</option><option value="closed">已完成</option>
                  </select>
                  <select className="filter-select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                    <option value="">全部类型</option>
                    {PROJECT_TYPE_OPTIONS.map((opt) => (
                      <option key={`filter-${opt.value}`} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, overflow: 'hidden' }}>
                  <table className="proj-table">
                    <thead>
                      <tr>
                        {['项目名称', '类型', '业主单位', '范围模型', 'v:// URI', '记录', '状态', '操作'].map((h) => (
                          <th key={h}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredProjects.map((p) => (
                        <tr key={p.id}>
                          {(() => {
                            const meta = projectMeta[p.id]
                            const segLabel = !meta
                              ? '默认'
                              : meta.segType === 'km'
                                ? `桩号 ${meta.segStart || '-'} ~ ${meta.segEnd || '-'}`
                                : meta.segType === 'contract'
                                  ? `合同段 ${meta.contractSegs.length} 个`
                                  : `结构物 ${meta.structures.length} 个`
                            const permLabel = meta
                              ? `${meta.permTemplate} / ${meta.memberCount}人 / 检测${(meta.inspectionTypes || []).length}类`
                              : '-'
                            const statusClass = p.status === 'active' ? 'pill-active' : p.status === 'pending' ? 'pill-pending' : 'pill-closed'
                            return (
                              <>
                          <td>
                            <div style={{ fontWeight: 700 }}>{p.name}</div>
                            <div style={{ fontSize: 12, color: '#94A3B8' }}>{p.contract_no || '-'} | {p.start_date || '-'} ~ {p.end_date || '-'}</div>
                          </td>
                          <td>
                            <span className={`type-chip chip-${p.type}`}>
                              {TYPE_ICON[p.type] || '🏗️'} {TYPE_LABEL[p.type] || p.type}
                            </span>
                          </td>
                          <td style={{ color: '#475569' }}>{p.owner_unit}</td>
                          <td>
                            <div style={{ fontSize: 12, color: '#334155' }}>{segLabel}</div>
                            <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>{permLabel}</div>
                          </td>
                          <td style={{ fontFamily: 'monospace', color: '#1A56DB' }}>{p.v_uri}</td>
                          <td>📝 {p.record_count} | 📷 {p.photo_count}</td>
                          <td>
                            <span className={`status-pill ${statusClass}`}>
                              {p.status === 'active' ? '进行中' : p.status === 'pending' ? '待开始' : '已完成'}
                            </span>
                          </td>
                          <td>
                            <div className="action-btns">
                              <button className="act-btn act-enter" onClick={() => { setCurrentProject(p); setActiveTab('inspection') }}>进入质检</button>
                              {canUseEnterpriseApi && (
                                <button
                                  className="act-btn act-detail"
                                  onClick={() => retryProjectAutoreg(p.id, p.name)}
                                  disabled={syncingProjectId === p.id}
                                >
                                  {syncingProjectId === p.id ? '同步中...' : '重试同步'}
                                </button>
                              )}
                              {canUseEnterpriseApi && (
                                <button
                                  className="act-btn act-detail"
                                  onClick={() => directProjectAutoreg(p.id, p.name)}
                                  disabled={syncingProjectId === p.id}
                                >
                                  {syncingProjectId === p.id ? '登记中...' : '直连登记'}
                                </button>
                              )}
                              <button className="act-btn act-edit" onClick={() => openProjectDetail(p.id, true)}>编辑</button>
                              <button className="act-btn act-detail" onClick={() => openProjectDetail(p.id)}>详情</button>
                              <button className="act-btn act-del" onClick={() => removeProject(p.id, p.name)}>删除</button>
                            </div>
                          </td>
                              </>
                            )
                          })()}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {canUseEnterpriseApi && (
                  <div style={{ marginTop: 12, border: '1px solid #E2E8F0', borderRadius: 10, padding: 12, background: '#FCFDFF' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>自动登记记录</div>
                      <button
                        className="act-btn act-detail"
                        onClick={async () => {
                          const latest = await listAutoregProjectsApi(20) as { items?: typeof autoregRows } | null
                          if (latest?.items) setAutoregRows(latest.items)
                        }}
                      >
                        刷新
                      </button>
                    </div>
                    {autoregRows.length === 0 ? (
                      <div style={{ fontSize: 12, color: '#94A3B8' }}>暂无自动登记记录，可在项目操作列点击“重试同步/直连登记”。</div>
                    ) : (
                      <div style={{ display: 'grid', gap: 8 }}>
                        {autoregRows.slice(0, 6).map((row, idx) => (
                          <div key={`${row.project_code || row.project_name || 'autoreg'}-${idx}`} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: 10, background: '#fff' }}>
                            <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>
                              {row.project_name || '-'} <span style={{ fontWeight: 500, color: '#64748B' }}>({row.project_code || '-'})</span>
                            </div>
                            <div style={{ fontSize: 12, color: '#1A56DB', fontFamily: 'monospace', marginTop: 2, wordBreak: 'break-all' }}>
                              {row.project_uri || '-'}
                            </div>
                            <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
                              site: {row.site_uri || '-'} | 来源：{row.source_system || '-'}
                            </div>
                            <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>
                              更新：{row.updated_at ? new Date(row.updated_at).toLocaleString('zh-CN') : '-'}
                            </div>
                          </div>
                        ))}
                        {autoregRows.length > 6 && (
                          <div style={{ fontSize: 12, color: '#64748B' }}>仅展示前 6 条，共 {autoregRows.length} 条</div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            </div>
          )}

          {activeTab === 'register' && (
            <div>
              <div className="register-hero">
                <div className="register-eyebrow">QCSpec Register Center</div>
                <h2 className="register-title">注册项目并激活 <span className="hl">v:// 质检节点</span></h2>
                <p className="register-sub">每个项目将绑定唯一 v:// URI，质检记录、照片与报告统一归档并可追溯。</p>
                <div className="register-hero-stats">
                  <div className="hero-stat">
                    <div className="hero-stat-val">{projects.length}</div>
                    <div className="hero-stat-label">已注册项目</div>
                  </div>
                  <div className="hero-stat">
                    <div className="hero-stat-val">{registerSegCount}</div>
                    <div className="hero-stat-label">检测分段</div>
                  </div>
                  <div className="hero-stat">
                    <div className="hero-stat-val">{registerRecordCount}</div>
                    <div className="hero-stat-label">质检记录</div>
                  </div>
                </div>
              </div>

              <div className="reg-steps">
                {[
                  { num: 1, label: '项目信息' },
                  { num: 2, label: '检测范围' },
                  { num: 3, label: '零号台帐' },
                  { num: 4, label: '确认注册' },
                ].map((step) => (
                  <div
                    key={step.num}
                    className={`reg-step ${registerStep === step.num ? 'active' : registerStep > step.num ? 'done' : ''}`}
                    onClick={() => {
                      if (registerSuccess) return
                      setRegisterStep(step.num)
                    }}
                    style={{ cursor: registerSuccess ? 'default' : 'pointer' }}
                  >
                    <div className="reg-step-num">{registerStep > step.num ? '✓' : step.num}</div>
                    <div className="reg-step-label">{step.label}</div>
                  </div>
                ))}
              </div>

              {registerSuccess ? (
                <div className="success-banner">
                  <div className="success-icon-big">✓</div>
                  <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>项目注册成功</div>
                  <div style={{ fontSize: 13, color: '#A7F3D0' }}>已生成项目节点与基础配置</div>
                  <div className="success-uri">{registerSuccess.uri}</div>
                  <div style={{ fontSize: 12, color: '#D1FAE5', marginBottom: 10 }}>
                    项目编号：{registerSuccess.id} | 项目名称：{registerSuccess.name}
                  </div>
                  <div className="btn-row" style={{ maxWidth: 620, margin: '8px auto 0' }}>
                    <button
                      className="btn-primary btn-green"
                      onClick={() => {
                        const created = projects.find((p) => p.id === registerSuccess.id)
                        if (created) setCurrentProject(created)
                        setActiveTab('inspection')
                      }}
                    >
                      开始质检录入
                    </button>
                    <button className="btn-primary" onClick={() => setActiveTab('projects')}>进入项目列表</button>
                    <button className="btn-secondary" onClick={resetRegister}>继续注册</button>
                  </div>
                </div>
              ) : (
                <>
                  {registerStep === 1 && (
                    <div className="form-card">
                      <div className="form-card-title">📁 项目基础信息</div>
                      <div className="form-grid">
                        <div className="form-group">
                          <label className="form-label">项目名称 <span className="req">*</span></label>
                          <input className="form-input" value={regForm.name} onChange={(e) => setRegForm({ ...regForm, name: e.target.value })} placeholder="例如：京港高速大修工程（2026）" />
                        </div>
                        <div className="form-group">
                          <label className="form-label">项目类型 <span className="req">*</span></label>
                          <select className="form-select" value={regForm.type} onChange={(e) => setRegForm({ ...regForm, type: e.target.value })}>
                            {PROJECT_TYPE_OPTIONS.map((opt) => (
                              <option key={`reg-${opt.value}`} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        </div>
                        <div className="form-group">
                          <label className="form-label">业主单位 <span className="req">*</span></label>
                          <input className="form-input" value={regForm.owner_unit} onChange={(e) => setRegForm({ ...regForm, owner_unit: e.target.value })} placeholder="业主单位全称" />
                        </div>
                        <div className="form-group">
                          <label className="form-label">施工单位</label>
                          <input className="form-input" value={regForm.contractor} onChange={(e) => setRegForm({ ...regForm, contractor: e.target.value })} placeholder="施工单位名称" />
                        </div>
                        <div className="form-group">
                          <label className="form-label">监理单位</label>
                          <input className="form-input" value={regForm.supervisor} onChange={(e) => setRegForm({ ...regForm, supervisor: e.target.value })} placeholder="监理单位名称" />
                        </div>
                        <div className="form-group">
                          <label className="form-label">合同编号</label>
                          <input className="form-input" value={regForm.contract_no} onChange={(e) => setRegForm({ ...regForm, contract_no: e.target.value })} placeholder="合同编号" />
                        </div>
                        <div className="form-group">
                          <label className="form-label">ERP 项目编码</label>
                          <input
                            className="form-input"
                            value={regForm.erp_project_code}
                            onChange={(e) => {
                              const value = e.target.value
                              setRegForm((prev) => ({ ...prev, erp_project_code: value }))
                              if (settings.erpnextSync) setErpBinding({ success: false, code: '', name: '', reason: 'dirty' })
                            }}
                            placeholder="例如：PROJ-0001"
                          />
                        </div>
                        <div className="form-group">
                          <label className="form-label">ERP 项目名称</label>
                          <input
                            className="form-input"
                            value={regForm.erp_project_name}
                            onChange={(e) => {
                              const value = e.target.value
                              setRegForm((prev) => ({ ...prev, erp_project_name: value }))
                              if (settings.erpnextSync) setErpBinding({ success: false, code: '', name: '', reason: 'dirty' })
                            }}
                            placeholder={settings.erpnextSync ? '将由 ERP 拉取后自动回填' : '可选：用于 ERP 精准匹配'}
                          />
                        </div>
                        {settings.erpnextSync && (
                          <div className="form-group full">
                            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                              <button className="btn-secondary" onClick={pullErpProjectBinding} disabled={erpBindingLoading}>
                                {erpBindingLoading ? '拉取中...' : '从 ERP 拉取并绑定'}
                              </button>
                              <span style={{
                                fontSize: 12,
                                color: erpBinding.success ? '#047857' : '#B45309',
                                background: erpBinding.success ? '#ECFDF5' : '#FFFBEB',
                                border: `1px solid ${erpBinding.success ? '#A7F3D0' : '#FCD34D'}`,
                                borderRadius: 999,
                                padding: '4px 10px',
                                fontWeight: 600,
                              }}>
                                {erpBinding.success
                                  ? `已绑定：${erpBinding.code} / ${erpBinding.name}`
                                  : '未绑定：请先从 ERP 拉取后再进入下一步'}
                              </span>
                            </div>
                          </div>
                        )}
                        {!settings.erpnextSync && (
                          <div className="form-group full">
                            <div className="form-hint">ERP 同步未启用，当前注册不做 ERP 强制绑定。</div>
                          </div>
                        )}
                        <div className="form-group">
                          <label className="form-label">开工日期</label>
                          <input className="form-input" type="date" value={regForm.start_date} onChange={(e) => setRegForm({ ...regForm, start_date: e.target.value })} />
                        </div>
                        <div className="form-group">
                          <label className="form-label">完工日期</label>
                          <input className="form-input" type="date" value={regForm.end_date} onChange={(e) => setRegForm({ ...regForm, end_date: e.target.value })} />
                        </div>
                        <div className="form-group full">
                          <label className="form-label">项目说明</label>
                          <textarea className="form-textarea" value={regForm.description} onChange={(e) => setRegForm({ ...regForm, description: e.target.value })} placeholder="项目背景、检测重点等（可选）" />
                        </div>
                      </div>
                      <div className="vpath-box" style={{ marginTop: 12 }}>
                        <span className="vpath-label">v:// 节点预览</span>
                        <span className="vpath-uri">{regUri}</span>
                        <span className={vpathStatus === 'taken' ? 'vpath-busy' : vpathStatus === 'available' ? 'vpath-ok' : 'vpath-checking'}>
                          {vpathStatus === 'taken' ? '已占用' : vpathStatus === 'available' ? '可用' : '检测中'}
                        </span>
                      </div>
                    </div>
                  )}

                  {registerStep === 2 && (
                    <>
                      <div className="form-card">
                        <div className="form-card-title">🧭 范围模型与节点</div>
                        <div className="reg-info-box blue">
                          <span className="reg-info-icon">ℹ️</span>
                          <div className="reg-info-text">
                            检测范围会映射为 v:// 子节点，并与零号台帐、质检台帐共同组成项目主节点结构。
                          </div>
                        </div>
                        <div className="seg-grid">
                          {[
                            { key: 'km', icon: '🛣️', name: '按桩号', desc: 'K 起止区间自动分段', info: '推荐用于公路项目' },
                            { key: 'contract', icon: '📦', name: '按合同段', desc: '按标段配置', info: '多标段项目使用' },
                            { key: 'structure', icon: '🏛️', name: '按构造物', desc: '桥梁/隧道/涵洞', info: '构造物专项检测' },
                          ].map((seg) => (
                            <div key={seg.key} className={`seg-opt ${segType === seg.key ? 'sel' : ''}`} onClick={() => setSegType(seg.key as SegType)}>
                              <div className="seg-opt-icon">{seg.icon}</div>
                              <div className="seg-opt-name">{seg.name}</div>
                              <div className="seg-opt-desc">{seg.desc}</div>
                              <div className="seg-opt-info">{seg.info}</div>
                            </div>
                          ))}
                        </div>

                        {segType === 'km' && (
                          <div style={{ marginBottom: 12 }}>
                            <div className="form-group" style={{ marginBottom: 8 }}>
                              <label className="form-label">桩号范围</label>
                              <div className="range-row">
                                <input className="form-input" value={regForm.seg_start} onChange={(e) => setRegForm({ ...regForm, seg_start: e.target.value })} placeholder="K0+000" />
                                <span className="range-sep">→</span>
                                <input className="form-input" value={regForm.seg_end} onChange={(e) => setRegForm({ ...regForm, seg_end: e.target.value })} placeholder="K100+000" />
                              </div>
                            </div>
                            <div className="form-group">
                              <label className="form-label">分段间隔（km）</label>
                              <input className="form-input" type="number" min={1} value={regKmInterval} onChange={(e) => setRegKmInterval(Math.max(1, Number(e.target.value) || 1))} />
                              <div className="form-hint">建议 10-20km，系统将自动切分子节点。</div>
                            </div>
                          </div>
                        )}

                        {segType === 'contract' && (
                          <div style={{ marginBottom: 10 }}>
                            {contractSegs.map((seg, idx) => (
                              <div key={`${seg.name}-${idx}`} className="form-grid" style={{ marginBottom: 8, gridTemplateColumns: '1fr 1fr auto' }}>
                                <input className="form-input" value={seg.name} onChange={(e) => setContractSegs((prev) => prev.map((x, i) => i === idx ? { ...x, name: e.target.value } : x))} placeholder="标段名称" />
                                <input className="form-input" value={seg.range} onChange={(e) => setContractSegs((prev) => prev.map((x, i) => i === idx ? { ...x, range: e.target.value } : x))} placeholder="范围（如 K0~K30）" />
                                <button className="btn-secondary" onClick={() => setContractSegs((prev) => prev.filter((_, i) => i !== idx))}>删除</button>
                              </div>
                            ))}
                            <button className="btn-secondary" onClick={addContractSeg}>+ 添加合同段</button>
                          </div>
                        )}

                        {segType === 'structure' && (
                          <div style={{ marginBottom: 10 }}>
                            {structures.map((st, idx) => (
                              <div key={`${st.name}-${idx}`} className="form-grid" style={{ marginBottom: 8, gridTemplateColumns: '100px 1fr 1fr auto' }}>
                                <select className="form-select" value={st.kind} onChange={(e) => setStructures((prev) => prev.map((x, i) => i === idx ? { ...x, kind: e.target.value } : x))}>
                                  <option>桥梁</option><option>隧道</option><option>涵洞</option>
                                </select>
                                <input className="form-input" value={st.name} onChange={(e) => setStructures((prev) => prev.map((x, i) => i === idx ? { ...x, name: e.target.value } : x))} placeholder="结构物名称" />
                                <input className="form-input" value={st.code} onChange={(e) => setStructures((prev) => prev.map((x, i) => i === idx ? { ...x, code: e.target.value } : x))} placeholder="编号" />
                                <button className="btn-secondary" onClick={() => setStructures((prev) => prev.filter((_, i) => i !== idx))}>删除</button>
                              </div>
                            ))}
                            <button className="btn-secondary" onClick={addStructure}>+ 添加结构物</button>
                          </div>
                        )}

                        <div className="form-group full" style={{ marginBottom: 10 }}>
                          <label className="form-label">主要检测类型（可多选）</label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {INSPECTION_TYPE_OPTIONS.map((opt) => {
                              const checked = regInspectionTypes.includes(opt.key)
                              return (
                                <label key={opt.key} className="perm-role-tag" style={{ cursor: 'pointer', background: checked ? '#DBEAFE' : '#EEF2FF', color: checked ? '#1D4ED8' : '#4338CA' }}>
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => toggleInspectionType(opt.key, regInspectionTypes, setRegInspectionTypes)}
                                    style={{ marginRight: 5 }}
                                  />
                                  {opt.label}
                                </label>
                              )
                            })}
                          </div>
                        </div>

                        <div className="vpath-box">
                          <span className="vpath-label">v:// URI</span>
                          <span className="vpath-uri">{regUri}</span>
                          <span className={vpathStatus === 'taken' ? 'vpath-busy' : vpathStatus === 'available' ? 'vpath-ok' : 'vpath-checking'}>
                            {vpathStatus === 'taken' ? '已占用' : vpathStatus === 'available' ? '可用' : '检测中'}
                          </span>
                        </div>
                        <div className="node-tree">
                          <div>{regUri}</div>
                          {regRangeTreeLines.length > 0
                            ? regRangeTreeLines.map((line, idx) => (
                              <div className="node-tree-sub" key={`${line}-${idx}`}>├─ {line}</div>
                            ))
                            : <div className="node-tree-sub">├─ 输入范围参数后自动生成子节点</div>}
                          <div className="node-tree-sub">├─ 零号台帐/（步骤3填写）</div>
                          <div className="node-tree-sub">└─ 质检台帐/（监理秩签后解锁）</div>
                        </div>
                      </div>
                    </>
                  )}

                  {registerStep === 3 && (
                    <div className="form-card">
                      <div className="form-card-title">📋 零号台帐</div>
                      <div className="reg-info-box green">
                        <span className="reg-info-icon">ℹ️</span>
                        <div className="reg-info-text">开工前建立零号台帐，监理秩签审批通过后质检台帐解锁。</div>
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
                        {[
                          { key: 'personnel', label: '👤 施工人员' },
                          { key: 'equipment', label: '🔧 检测仪器' },
                          { key: 'subcontract', label: '🏢 分包单位' },
                          { key: 'materials', label: '📦 原材料' },
                        ].map((tab) => (
                          <button
                            key={tab.key}
                            className="btn-secondary"
                            style={{
                              padding: '8px 14px',
                              borderColor: zeroLedgerTab === tab.key ? '#1D4ED8' : '#CBD5E1',
                              color: zeroLedgerTab === tab.key ? '#1D4ED8' : '#475569',
                              background: zeroLedgerTab === tab.key ? '#EFF6FF' : '#fff',
                            }}
                            onClick={() => setZeroLedgerTab(tab.key as ZeroLedgerTab)}
                          >
                            {tab.label}
                          </button>
                        ))}
                      </div>

                      {zeroLedgerTab === 'personnel' && (
                        <div style={{ marginBottom: 14 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <div style={{ fontSize: 12, color: '#64748B' }}>姓名 · 职务 · DTORole · 资质证书 · executor 节点地址实时生成</div>
                            <button
                              className="btn-secondary"
                              onClick={() => setZeroPersonnel((prev) => [...prev, {
                                id: makeRowId('zp'),
                                name: '',
                                title: '质检员',
                                dtoRole: 'AI',
                                certificate: '',
                              }])}
                            >
                              + 添加人员
                            </button>
                          </div>
                          <div style={{ overflowX: 'auto' }}>
                            <table className="perm-table" style={{ minWidth: 900 }}>
                              <thead>
                                <tr>
                                  <th>姓名</th><th>职务</th><th>DTORole</th><th>资质证书</th><th>executor 节点</th><th style={{ width: 68 }}>操作</th>
                                </tr>
                              </thead>
                              <tbody>
                                {zeroPersonnel.map((row) => (
                                  <tr key={row.id}>
                                    <td><input className="form-input" value={row.name} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, name: e.target.value } : x))} placeholder="姓名" /></td>
                                    <td><input className="form-input" value={row.title} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, title: e.target.value } : x))} placeholder="职务/职称" /></td>
                                    <td>
                                      <select className="form-select" value={row.dtoRole} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, dtoRole: e.target.value as TeamRole } : x))}>
                                        <option value="OWNER">OWNER</option>
                                        <option value="SUPERVISOR">SUPERVISOR</option>
                                        <option value="AI">AI</option>
                                        <option value="PUBLIC">PUBLIC</option>
                                      </select>
                                    </td>
                                    <td><input className="form-input" value={row.certificate} onChange={(e) => setZeroPersonnel((prev) => prev.map((x) => x.id === row.id ? { ...x, certificate: e.target.value } : x))} placeholder="资质证书" /></td>
                                    <td><code style={{ color: '#1D4ED8', fontSize: 12 }}>{buildExecutorUri(row.name)}</code></td>
                                    <td><button className="act-btn act-del" onClick={() => setZeroPersonnel((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {zeroLedgerTab === 'equipment' && (
                        <div style={{ marginBottom: 14 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <div style={{ fontSize: 12, color: '#64748B' }}>检定有效期自动计算剩余天数：&gt;90天有效，&lt;90天预警，已过期标红</div>
                            <button
                              className="btn-secondary"
                              onClick={() => setZeroEquipment((prev) => [...prev, {
                                id: makeRowId('ze'),
                                name: '',
                                modelNo: '',
                                inspectionItem: '压实度',
                                validUntil: '',
                              }])}
                            >
                              + 添加仪器
                            </button>
                          </div>
                          <div style={{ overflowX: 'auto' }}>
                            <table className="perm-table" style={{ minWidth: 980 }}>
                              <thead>
                                <tr>
                                  <th>仪器名称</th><th>型号编号</th><th>检测项目</th><th>检定有效期</th><th>ToolPeg 节点</th><th>状态</th><th style={{ width: 68 }}>操作</th>
                                </tr>
                              </thead>
                              <tbody>
                                {zeroEquipment.map((row) => {
                                  const validity = getEquipmentValidity(row.validUntil)
                                  return (
                                    <tr key={row.id}>
                                      <td><input className="form-input" value={row.name} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, name: e.target.value } : x))} placeholder="仪器名称" /></td>
                                      <td><input className="form-input" value={row.modelNo} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, modelNo: e.target.value } : x))} placeholder="型号/编号" /></td>
                                      <td><input className="form-input" value={row.inspectionItem} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, inspectionItem: e.target.value } : x))} placeholder="检测项目" /></td>
                                      <td><input className="form-input" type="date" value={row.validUntil} onChange={(e) => setZeroEquipment((prev) => prev.map((x) => x.id === row.id ? { ...x, validUntil: e.target.value } : x))} /></td>
                                      <td><code style={{ color: '#1D4ED8', fontSize: 12 }}>{buildToolUri(row.name, row.modelNo)}</code></td>
                                      <td><span style={{ fontSize: 12, fontWeight: 700, color: validity.color, background: validity.bg, borderRadius: 999, padding: '3px 10px' }}>{validity.label}</span></td>
                                      <td><button className="act-btn act-del" onClick={() => setZeroEquipment((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {zeroLedgerTab === 'subcontract' && (
                        <div style={{ marginBottom: 14 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <div style={{ fontSize: 12, color: '#64748B' }}>单位名称 · 分包内容 · 桩号范围 · 自动生成子节点</div>
                            <button
                              className="btn-secondary"
                              onClick={() => setZeroSubcontracts((prev) => [...prev, {
                                id: makeRowId('zs'),
                                unitName: '',
                                content: '路面施工',
                                range: '',
                              }])}
                            >
                              + 添加分包
                            </button>
                          </div>
                          <div style={{ overflowX: 'auto' }}>
                            <table className="perm-table" style={{ minWidth: 860 }}>
                              <thead>
                                <tr>
                                  <th>单位名称</th><th>分包内容</th><th>桩号范围</th><th>自动生成子节点</th><th style={{ width: 68 }}>操作</th>
                                </tr>
                              </thead>
                              <tbody>
                                {zeroSubcontracts.map((row) => (
                                  <tr key={row.id}>
                                    <td><input className="form-input" value={row.unitName} onChange={(e) => setZeroSubcontracts((prev) => prev.map((x) => x.id === row.id ? { ...x, unitName: e.target.value } : x))} placeholder="分包单位全称" /></td>
                                    <td><input className="form-input" value={row.content} onChange={(e) => setZeroSubcontracts((prev) => prev.map((x) => x.id === row.id ? { ...x, content: e.target.value } : x))} placeholder="分包内容" /></td>
                                    <td><input className="form-input" value={row.range} onChange={(e) => setZeroSubcontracts((prev) => prev.map((x) => x.id === row.id ? { ...x, range: e.target.value } : x))} placeholder="K0~K20" /></td>
                                    <td><code style={{ color: '#1D4ED8', fontSize: 12 }}>{buildSubcontractUri(row.unitName)}</code></td>
                                    <td><button className="act-btn act-del" onClick={() => setZeroSubcontracts((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {zeroLedgerTab === 'materials' && (
                        <div style={{ marginBottom: 14 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <div style={{ fontSize: 12, color: '#64748B' }}>材料名称 · 规格 · 供应商 · 检测频率要求</div>
                            <button
                              className="btn-secondary"
                              onClick={() => setZeroMaterials((prev) => [...prev, {
                                id: makeRowId('zm'),
                                name: '',
                                spec: '',
                                supplier: '',
                                freq: '每批次检测',
                              }])}
                            >
                              + 添加材料
                            </button>
                          </div>
                          <div style={{ overflowX: 'auto' }}>
                            <table className="perm-table" style={{ minWidth: 860 }}>
                              <thead>
                                <tr>
                                  <th>材料名称</th><th>规格</th><th>供应商</th><th>检测频率要求</th><th style={{ width: 68 }}>操作</th>
                                </tr>
                              </thead>
                              <tbody>
                                {zeroMaterials.map((row) => (
                                  <tr key={row.id}>
                                    <td><input className="form-input" value={row.name} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, name: e.target.value } : x))} placeholder="材料名称" /></td>
                                    <td><input className="form-input" value={row.spec} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, spec: e.target.value } : x))} placeholder="规格型号" /></td>
                                    <td><input className="form-input" value={row.supplier} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, supplier: e.target.value } : x))} placeholder="供应商" /></td>
                                    <td><input className="form-input" value={row.freq} onChange={(e) => setZeroMaterials((prev) => prev.map((x) => x.id === row.id ? { ...x, freq: e.target.value } : x))} placeholder="每批次检测" /></td>
                                    <td><button className="act-btn act-del" onClick={() => setZeroMaterials((prev) => prev.filter((x) => x.id !== row.id))}>删除</button></td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      <div style={{ fontSize: 12, color: '#475569', fontWeight: 700, marginBottom: 6 }}>节点树实时预览</div>
                      <div className="node-tree" style={{ marginBottom: 12 }}>
                        <div>{regUri}</div>
                        <div className="node-tree-sub" style={{ color: '#F59E0B' }}>├─ 零号台帐/</div>
                        {zeroLedgerTreeRows.length > 0 ? zeroLedgerTreeRows.map((row, idx) => (
                          <div key={`${row.text}-${idx}`} className="node-tree-sub" style={{ color: row.color || '#34D399' }}>
                            {idx === zeroLedgerTreeRows.length - 1 ? '└─' : '├─'} {row.text}
                          </div>
                        )) : (
                          <div className="node-tree-sub">└─ （等待填写零号台帐）</div>
                        )}
                        <div className="node-tree-sub" style={{ color: '#94A3B8' }}>└─ 质检台帐/（等待监理秩签后解锁）</div>
                      </div>

                      <div className="reg-info-box green" style={{ marginBottom: 0, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 700, color: '#047857', marginBottom: 4 }}>🔏 秩签（Ordosign）审批</div>
                          <div style={{ fontSize: 12, color: '#334155' }}>项目负责人秩签 → 监理工程师秩签 → 质检台帐解锁</div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ width: 42, height: 42, borderRadius: '50%', border: '2px dashed #6EE7B7', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>项</div>
                            <div style={{ fontSize: 10, color: '#64748B' }}>待签</div>
                          </div>
                          <span style={{ color: '#10B981' }}>→</span>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ width: 42, height: 42, borderRadius: '50%', border: '2px dashed #6EE7B7', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>监</div>
                            <div style={{ fontSize: 10, color: '#64748B' }}>待签</div>
                          </div>
                          <span style={{ color: '#10B981' }}>→</span>
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ width: 42, height: 42, borderRadius: '50%', border: '2px dashed #6EE7B7', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fff' }}>🔓</div>
                            <div style={{ fontSize: 10, color: '#64748B' }}>质检台帐</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {registerStep === 4 && (
                    <div className="form-card">
                      <div className="form-card-title">✅ 确认项目信息</div>
                      <div className="reg-info-box green">
                        <span className="reg-info-icon">✅</span>
                        <div className="reg-info-text">确认后将创建项目主节点并写入初始范围模型。</div>
                      </div>
                      <div className="reg-info-box gold">
                        <span className="reg-info-icon">⚠️</span>
                        <div className="reg-info-text">建议再次确认项目名称与业主单位，注册后 URI 作为主键不建议频繁变更。</div>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 8, fontSize: 13 }}>
                        <span style={{ color: '#64748B' }}>项目名称</span><strong>{regForm.name || '-'}</strong>
                        <span style={{ color: '#64748B' }}>项目类型</span><span>{TYPE_LABEL[regForm.type] || regForm.type}</span>
                        <span style={{ color: '#64748B' }}>业主单位</span><span>{regForm.owner_unit || '-'}</span>
                        <span style={{ color: '#64748B' }}>施工单位</span><span>{regForm.contractor || '-'}</span>
                        <span style={{ color: '#64748B' }}>监理单位</span><span>{regForm.supervisor || '-'}</span>
                        <span style={{ color: '#64748B' }}>合同编号</span><span>{regForm.contract_no || '-'}</span>
                        <span style={{ color: '#64748B' }}>ERP 项目编码</span><span>{regForm.erp_project_code || '-'}</span>
                        <span style={{ color: '#64748B' }}>ERP 项目名称</span><span>{regForm.erp_project_name || '-'}</span>
                        <span style={{ color: '#64748B' }}>工期</span><span>{regForm.start_date || '-'} ~ {regForm.end_date || '-'}</span>
                        <span style={{ color: '#64748B' }}>分段方式</span><span>{segType === 'km' ? '按桩号' : segType === 'contract' ? '按合同段' : '按结构物'}</span>
                        <span style={{ color: '#64748B' }}>分段间隔</span><span>{regKmInterval} km</span>
                        <span style={{ color: '#64748B' }}>主要检测类型</span>
                        <span>{regInspectionTypes.length ? regInspectionTypes.map((key) => INSPECTION_TYPE_LABEL[key]).join(' / ') : '-'}</span>
                        <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{regUri}</code>
                        <span style={{ color: '#64748B' }}>零号台帐</span><span style={{ color: '#047857', fontWeight: 700 }}>{zeroLedgerSummary}</span>
                      </div>
                    </div>
                  )}

                  <div className="btn-row">
                    <button className="btn-secondary" onClick={prevRegStep} disabled={registerStep === 1}>上一步</button>
                    {registerStep < 4 ? (
                      <button className="btn-primary" onClick={nextRegStep}>下一步</button>
                    ) : (
                      <button className="btn-primary btn-green" onClick={submitRegister}>确认注册</button>
                    )}
                  </div>
                </>
              )}

              <div className="register-projects">
                <div className="register-projects-head">
                  <div className="register-projects-title">已注册项目</div>
                  <span className="register-projects-count">{projects.length}</span>
                </div>
                {registerPreviewProjects.length === 0 ? (
                  <div className="register-empty">
                    <div className="register-empty-icon">🏗️</div>
                    <div className="register-empty-title">暂无注册项目</div>
                    <div className="register-empty-sub">完成上方步骤即可创建第一个项目。</div>
                  </div>
                ) : (
                  <div className="register-project-list">
                    {registerPreviewProjects.map((p) => (
                      <div
                        key={`reg-${p.id}`}
                        className="reg-proj-card"
                        onClick={() => openProjectDetail(p.id)}
                        style={p.id === registerSuccess?.id ? { background: '#F0FDF4', borderColor: '#86EFAC' } : undefined}
                      >
                        <div className={`type-chip chip-${p.type}`}>{TYPE_ICON[p.type] || '🏗️'} {TYPE_LABEL[p.type] || p.type}</div>
                        <div className="reg-proj-main">
                          <div className="reg-proj-name">
                            {p.name}
                            {p.id === registerSuccess?.id && (
                              <span style={{ marginLeft: 6, fontSize: 12, color: '#059669', fontWeight: 800 }}>NEW</span>
                            )}
                          </div>
                          <div className="reg-proj-uri">{p.v_uri}</div>
                          <div className="reg-proj-meta">业主：{p.owner_unit || '-'} | 记录：{p.record_count} | 照片：{p.photo_count}</div>
                        </div>
                        <div className="reg-proj-actions">
                          <span className={`status-pill ${p.status === 'active' ? 'pill-active' : p.status === 'pending' ? 'pill-pending' : 'pill-closed'}`}>
                            {p.status === 'active' ? '进行中' : p.status === 'pending' ? '待开始' : '已完成'}
                          </span>
                          <button
                            className="act-btn act-enter"
                            onClick={(e) => {
                              e.stopPropagation()
                              setCurrentProject(p)
                              setActiveTab('inspection')
                            }}
                          >
                            进入质检
                          </button>
                        </div>
                      </div>
                    ))}
                    {projects.length > registerPreviewProjects.length && (
                      <button className="btn-secondary" style={{ width: '100%' }} onClick={() => setActiveTab('projects')}>
                        查看全部项目
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'team' && (
            <div>
              <div className="toolbar" style={{ justifyContent: 'space-between' }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#0F172A' }}>团队成员</div>
                <button className="btn-primary" style={{ flex: 'none' }} onClick={() => setInviteOpen(true)}>＋ 邀请成员</button>
              </div>
              <div className="member-grid">
                {members.map((m) => {
                  const roleClass = m.role === 'OWNER' ? 'role-owner' : m.role === 'SUPERVISOR' ? 'role-supervisor' : m.role === 'AI' ? 'role-inspector' : 'role-viewer'
                  const roleLabel = m.role === 'OWNER' ? '管理员' : m.role === 'SUPERVISOR' ? '监理' : m.role === 'AI' ? '质检员' : '只读'
                  return (
                    <div key={m.id} className="member-card">
                      <div className="member-header">
                        <div className="member-avatar" style={{ background: m.color }}>{m.name.slice(0, 1)}</div>
                        <div>
                          <div className="member-name">{m.name}</div>
                          <div className="member-title">{m.title}</div>
                        </div>
                      </div>
                      <span className={`role-badge ${roleClass}`}>{roleLabel}</span>
                      <div className="member-projects">参与项目：{m.projects.length} 个</div>
                      <div style={{ fontSize: 12, color: '#94A3B8' }}>{m.email}</div>
                      <div style={{ display: 'grid', gap: 6 }}>
                        <select
                          className="setting-select"
                          value={memberRoleDrafts[m.id] || m.role}
                          onChange={(e) => setMemberRoleDrafts((prev) => ({ ...prev, [m.id]: e.target.value as TeamRole }))}
                        >
                          <option value="AI">质检员（AI）</option>
                          <option value="SUPERVISOR">监理</option>
                          <option value="OWNER">管理员</option>
                          <option value="PUBLIC">只读</option>
                        </select>
                        <div className="member-actions">
                          <button className="act-btn act-edit" onClick={() => saveMemberRole(m)}>保存角色</button>
                          <button className="act-btn act-del" onClick={() => removeMember(m.id)}>移除</button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {activeTab === 'permissions' && (
            <div className="form-card">
              <div className="form-card-title">🔐 权限管理矩阵</div>
              <div className="perm-toolbar">
                {(['standard', 'strict', 'open'] as const).map((tpl) => (
                  <button key={tpl} className={permissionTemplate === tpl ? 'btn-primary' : 'btn-secondary'} style={{ flex: 'none', padding: '8px 12px' }} onClick={() => applyPermissionTemplate(tpl)}>
                    {tpl}
                  </button>
                ))}
                <span style={{ fontSize: 12, color: '#64748B' }}>当前模板：<strong>{permissionTemplate}</strong>（可继续微调）</span>
              </div>
              <div className="perm-layout">
                <div>
                  <table className="perm-table">
                    <thead>
                      <tr>
                        {['角色', ...PERMISSION_COLUMNS.map((col) => col.label)].map((h) => <th key={h}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {permissionMatrix.map((row) => (
                        <tr key={row.role}>
                          <td>
                            <span className={`perm-role perm-role-${row.role.toLowerCase()}`}>
                              {PERMISSION_ROLE_LABEL[row.role]}
                            </span>
                          </td>
                          {PERMISSION_COLUMNS.map((col) => (
                            <td key={`${row.role}-${col.key}`}>
                              <input type="checkbox" checked={row[col.key]} onChange={(e) => updatePermissionCell(row.role, col.key, e.target.checked)} />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div style={{ marginTop: 10 }}>
                    <button className="btn-primary" style={{ flex: 'none' }} onClick={persistPermissionMatrix}>保存权限矩阵</button>
                  </div>
                </div>
                <div>
                  <div className="node-tree" style={{ marginTop: 0 }}>
                    <div style={{ fontSize: 12, color: '#475569', letterSpacing: 1, marginBottom: 6 }}>V:// 节点权限结构 · 实时预览</div>
                    <div>{permissionTreeRoot}</div>
                    {permissionTreeRows.map((row, idx) => (
                      <div key={`${row.role}-${idx}`} className="node-tree-sub">
                        {idx === permissionTreeRows.length - 1 ? '└' : '├'}─ {row.role.toLowerCase()}/ <span style={{ color: '#64748B' }}>{row.granted}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.6, marginTop: 8 }}>
                    修改矩阵后节点树立即更新。保存后写入 v:// DTORole 配置。
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="settings-grid">
              <div className="settings-section">
                <div className="settings-title">🏢 企业信息</div>
                <div style={{ display: 'grid', gap: 8 }}>
                  <input className="setting-input" value={enterpriseInfo.name} onChange={(e) => setEnterpriseInfo({ ...enterpriseInfo, name: e.target.value })} placeholder="企业名称" />
                  <input className="setting-input" value={enterpriseInfo.vUri} onChange={(e) => setEnterpriseInfo({ ...enterpriseInfo, vUri: e.target.value })} placeholder="v:// 企业根节点" style={{ fontFamily: 'var(--mono)' }} />
                  <input className="setting-input" value={enterpriseInfo.creditCode} onChange={(e) => setEnterpriseInfo({ ...enterpriseInfo, creditCode: e.target.value })} placeholder="统一社会信用代码（可选）" />
                  <input className="setting-input" value={enterpriseInfo.adminEmail} readOnly />
                </div>
                <div style={{ marginTop: 10 }}>
                  <button className="btn-primary" style={{ flex: 'none' }} onClick={persistEnterpriseInfo}>保存企业信息</button>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-title">🔔 通知设置</div>
                <div className="toggle-row">
                  <span className="toggle-label">邮件通知</span>
                  <input type="checkbox" checked={settings.emailNotify} onChange={(e) => setSettings({ ...settings, emailNotify: e.target.checked })} />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">微信通知</span>
                  <input type="checkbox" checked={settings.wechatNotify} onChange={(e) => setSettings({ ...settings, wechatNotify: e.target.checked })} />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">自动生成报告</span>
                  <input type="checkbox" checked={settings.autoGenerateReport} onChange={(e) => setSettings({ ...settings, autoGenerateReport: e.target.checked })} />
                </div>
                <div className="toggle-row">
                  <span className="toggle-label">强制 Proof 存证</span>
                  <input type="checkbox" checked={settings.strictProof} onChange={(e) => setSettings({ ...settings, strictProof: e.target.checked })} />
                </div>
                <div style={{ marginTop: 10 }}>
                  <button
                    className="btn-primary"
                    style={{ flex: 'none' }}
                    onClick={() => persistSettings({
                      emailNotify: settings.emailNotify,
                      wechatNotify: settings.wechatNotify,
                      autoGenerateReport: settings.autoGenerateReport,
                      strictProof: settings.strictProof,
                    })}
                  >
                    保存通知设置
                  </button>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-title">📄 报告模板</div>
                <div style={{ display: 'grid', gap: 8 }}>
                  <select className="setting-select" value={settings.reportTemplate} onChange={(e) => setSettings({ ...settings, reportTemplate: e.target.value })}>
                    <option>default.docx</option>
                    <option>highway-monthly.docx</option>
                    <option>bridge-inspection.docx</option>
                    <option value="custom-upload">自定义模板（上传Word）</option>
                    {!['default.docx', 'highway-monthly.docx', 'bridge-inspection.docx', 'custom-upload'].includes(settings.reportTemplate) && (
                      <option value={settings.reportTemplate}>{settings.reportTemplate}</option>
                    )}
                  </select>
                  {settings.reportTemplate === 'custom-upload' && (
                    <input type="file" accept=".doc,.docx" onChange={(e) => setReportTemplateFile(e.target.files?.[0] || null)} className="setting-input" />
                  )}
                  <input className="setting-input" value={settings.reportHeader} onChange={(e) => setSettings({ ...settings, reportHeader: e.target.value })} placeholder="报告抬头（例如：中北工程设计咨询有限公司）" />
                  {settings.reportTemplateUrl && (
                    <a href={settings.reportTemplateUrl} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#1A56DB', textDecoration: 'none' }}>
                      查看当前模板文件
                    </a>
                  )}
                  <div className="setting-note">数字签章：后续版本将接入 QCPeg / SealPeg 协议，支持报告自动签章与验签。</div>
                  <button className="btn-primary" style={{ flex: 'none' }} onClick={persistReportTemplate}>保存模板设置</button>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-title">🔗 系统集成</div>
                <div style={{ display: 'grid', gap: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>⚡</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>GitPeg v:// Proof 存证</div>
                        <span style={{
                          fontSize: 12,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.gitpegEnabled ? '#ECFDF5' : '#F8FAFC',
                          color: settings.gitpegEnabled ? '#059669' : '#64748B',
                        }}>
                          {settings.gitpegEnabled ? '已启用' : '未接入'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B' }}>质检记录自动推送到 GitPeg v:// 链，不可篡改存证</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={settings.gitpegEnabled}
                      onChange={(e) => {
                        setSettings({ ...settings, gitpegEnabled: e.target.checked })
                        if (!e.target.checked) {
                          setGitpegVerifyMsg({ text: '', color: '#64748B' })
                          setGitpegVerifying(false)
                        }
                      }}
                    />
                  </div>
                  {settings.gitpegEnabled && (
                    <div style={{ padding: '0 0 10px 40px' }}>
                      <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 12 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>GitPeg 连接配置</div>
                        <div style={{ display: 'grid', gap: 8 }}>
                          <input
                            className="setting-input"
                            value={settings.gitpegToken}
                            onChange={(e) => setSettings({ ...settings, gitpegToken: e.target.value })}
                            placeholder="可选：兼容模式 Token（官方 Partner 接口可留空）"
                            type="password"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input className="setting-input" value={enterpriseInfo.vUri} readOnly style={{ fontFamily: 'var(--mono)', color: '#1A56DB' }} />
                          <input
                            className="setting-input"
                            value={settings.gitpegRegistrarBaseUrl}
                            onChange={(e) => setSettings({ ...settings, gitpegRegistrarBaseUrl: e.target.value })}
                            placeholder="GitPeg Registrar Base URL（例如：https://gitpeg.cn）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={settings.gitpegPartnerCode}
                            onChange={(e) => setSettings({ ...settings, gitpegPartnerCode: e.target.value })}
                            placeholder="Partner Code（例如：wastewater-site）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={settings.gitpegIndustryCode}
                            onChange={(e) => setSettings({ ...settings, gitpegIndustryCode: e.target.value })}
                            placeholder="Industry Code（例如：wastewater）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={settings.gitpegClientId}
                            onChange={(e) => setSettings({ ...settings, gitpegClientId: e.target.value })}
                            placeholder="Client ID（例如：ptn_wastewater_001）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={settings.gitpegClientSecret}
                            onChange={(e) => setSettings({ ...settings, gitpegClientSecret: e.target.value })}
                            placeholder="Client Secret"
                            type="password"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <select
                            className="setting-select"
                            value={settings.gitpegRegistrationMode}
                            onChange={(e) => setSettings({ ...settings, gitpegRegistrationMode: e.target.value })}
                          >
                            <option value="DOMAIN">DOMAIN</option>
                            <option value="SHELL">SHELL</option>
                          </select>
                          <input
                            className="setting-input"
                            value={settings.gitpegReturnUrl}
                            onChange={(e) => setSettings({ ...settings, gitpegReturnUrl: e.target.value })}
                            placeholder="Return URL（GitPeg 回跳地址）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={settings.gitpegWebhookUrl}
                            onChange={(e) => setSettings({ ...settings, gitpegWebhookUrl: e.target.value })}
                            placeholder="Webhook URL（GitPeg 回调到 QCSpec）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={settings.gitpegWebhookSecret}
                            onChange={(e) => setSettings({ ...settings, gitpegWebhookSecret: e.target.value })}
                            placeholder="Webhook Secret（用于 X-Gitpeg-Signature HMAC-SHA256 校验）"
                            type="password"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={(settings.gitpegModuleCandidates || []).join(',')}
                            onChange={(e) => setSettings({
                              ...settings,
                              gitpegModuleCandidates: e.target.value
                                .split(',')
                                .map((item) => item.trim())
                                .filter(Boolean),
                            })}
                            placeholder="Module Candidates（逗号分隔：proof,utrip,openapi）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <button className="btn-primary" style={{ flex: 'none' }} onClick={verifyGitpegToken} disabled={gitpegVerifying}>
                            {gitpegVerifying ? '验证中...' : '验证'}
                          </button>
                          {gitpegVerifyMsg.text && (
                            <div style={{ fontSize: 12, color: gitpegVerifyMsg.color }}>{gitpegVerifyMsg.text}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>📊</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>ERPNext 数据同步</div>
                        <span style={{
                          fontSize: 12,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.erpnextSync ? '#ECFDF5' : '#F8FAFC',
                          color: settings.erpnextSync ? '#059669' : '#64748B',
                        }}>
                          {settings.erpnextSync ? '已启用' : '未接入'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B' }}>与 ERPNext 系统同步，质检合格才能计量</div>
                    </div>
                    <input type="checkbox" checked={settings.erpnextSync} onChange={(e) => setSettings({ ...settings, erpnextSync: e.target.checked })} />
                  </div>
                  {settings.erpnextSync && (
                    <div style={{ padding: '0 0 10px 40px' }}>
                      <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 12 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>ERPNext 连接配置</div>
                        <div style={{ display: 'grid', gap: 8 }}>
                          <input
                            className="setting-input"
                            value={erpDraft.url}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, url: e.target.value }))}
                            placeholder="http://development.localhost:8000"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={erpDraft.siteName}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, siteName: e.target.value }))}
                            placeholder="development.localhost（可选）"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={erpDraft.apiKey}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, apiKey: e.target.value }))}
                            placeholder="API Key 或 token key:secret"
                            type="password"
                          />
                          <input
                            className="setting-input"
                            value={erpDraft.apiSecret}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, apiSecret: e.target.value }))}
                            placeholder="API Secret（若上面填 key:secret 可留空）"
                            type="password"
                          />
                          <input
                            className="setting-input"
                            value={erpDraft.username}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, username: e.target.value }))}
                            placeholder="用户名（可选，用于 session 测试）"
                          />
                          <input
                            className="setting-input"
                            value={erpDraft.password}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, password: e.target.value }))}
                            placeholder="密码（可选，用于 session 测试）"
                            type="password"
                          />
                          <button className="btn-primary" style={{ flex: 'none' }} onClick={testErpConnection} disabled={erpTesting}>
                            {erpTesting ? '测试中...' : '测试连接'}
                          </button>
                          {erpTestMsg && <div style={{ fontSize: 12, color: erpTestMsg.includes('✅') ? '#059669' : '#D97706' }}>{erpTestMsg}</div>}
                          <div style={{ fontSize: 12, color: '#64748B' }}>
                            推荐先用 API Key/Secret；若本地 `frappe-bench` 仅有账号密码，可填写用户名/密码测试。
                          </div>
                          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px dashed #CBD5E1', fontSize: 12, color: '#334155', fontWeight: 700 }}>
                            ERP 回写映射（Project on_submit 同步）
                          </div>
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.projectDoctype}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, projectDoctype: e.target.value }))}
                            placeholder="ERP Project Doctype（默认 Project）"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.projectLookupField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, projectLookupField: e.target.value }))}
                            placeholder="查找字段（默认 name，可改 custom 字段）"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.projectLookupValue}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, projectLookupValue: e.target.value }))}
                            placeholder="固定查找值（可空；空时回退合同号/项目名）"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegProjectUriField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegProjectUriField: e.target.value }))}
                            placeholder="回写字段：gitpeg_project_uri"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegSiteUriField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegSiteUriField: e.target.value }))}
                            placeholder="回写字段：gitpeg_site_uri"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegStatusField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegStatusField: e.target.value }))}
                            placeholder="回写字段：gitpeg_status"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegResultJsonField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegResultJsonField: e.target.value }))}
                            placeholder="回写字段：gitpeg_register_result_json"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegRegistrationIdField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegRegistrationIdField: e.target.value }))}
                            placeholder="回写字段：gitpeg_registration_id"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegNodeUriField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegNodeUriField: e.target.value }))}
                            placeholder="回写字段：gitpeg_node_uri"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegShellUriField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegShellUriField: e.target.value }))}
                            placeholder="回写字段：gitpeg_shell_uri"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegProofHashField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegProofHashField: e.target.value }))}
                            placeholder="回写字段：gitpeg_proof_hash"
                          />
                          <input
                            className="setting-input"
                            value={erpWritebackDraft.gitpegIndustryProfileIdField}
                            onChange={(e) => setErpWritebackDraft((prev) => ({ ...prev, gitpegIndustryProfileIdField: e.target.value }))}
                            placeholder="回写字段：gitpeg_industry_profile_id"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #E2E8F0' }}>
                    <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>💬</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>微信小程序登入</div>
                        <span style={{
                          fontSize: 12,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.wechatMiniapp ? '#ECFDF5' : '#F8FAFC',
                          color: settings.wechatMiniapp ? '#059669' : '#64748B',
                        }}>
                          {settings.wechatMiniapp ? '已启用' : '未接入'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B' }}>施工人员通过微信扫码登录，现场质检录入</div>
                    </div>
                    <input type="checkbox" checked={settings.wechatMiniapp} onChange={(e) => setSettings({ ...settings, wechatMiniapp: e.target.checked })} />
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0' }}>
                    <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>🚁</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>无人机数据接入</div>
                        <span style={{
                          fontSize: 12,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.droneImport ? '#ECFDF5' : '#FFFBEB',
                          color: settings.droneImport ? '#059669' : '#D97706',
                        }}>
                          {settings.droneImport ? '已启用' : 'Beta'}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B' }}>大疆无人机巡检数据自动接入质检系统</div>
                    </div>
                    <input type="checkbox" checked={settings.droneImport} onChange={(e) => setSettings({ ...settings, droneImport: e.target.checked })} />
                  </div>
                </div>

                <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #E2E8F0' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 8 }}>Webhook URL（可选）</div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <input
                      className="setting-input"
                      value={settings.webhookUrl}
                      onChange={(e) => setSettings({ ...settings, webhookUrl: e.target.value })}
                      placeholder="https://your-server.com/qcspec/webhook"
                      style={{ fontFamily: 'var(--mono)' }}
                    />
                    <button className="btn-secondary" style={{ padding: '10px 12px', whiteSpace: 'nowrap' }} onClick={testWebhook} disabled={webhookTesting}>
                      {webhookTesting ? '发送中...' : '发送测试'}
                    </button>
                  </div>
                  {webhookResult.visible && (
                    <div style={{ marginTop: 6, fontSize: 12, color: webhookResult.color, fontFamily: 'var(--mono)' }}>
                      {webhookResult.text}
                    </div>
                  )}
                </div>

                <div style={{ marginTop: 12 }}>
                  <button
                    className="btn-primary btn-green"
                    style={{ flex: 'none' }}
                    onClick={() =>
                      persistSettings({
                        webhookUrl: settings.webhookUrl,
                        gitpegToken: settings.gitpegToken,
                        gitpegEnabled: settings.gitpegEnabled,
                        gitpegRegistrarBaseUrl: settings.gitpegRegistrarBaseUrl,
                        gitpegPartnerCode: settings.gitpegPartnerCode,
                        gitpegIndustryCode: settings.gitpegIndustryCode,
                        gitpegClientId: settings.gitpegClientId,
                        gitpegClientSecret: settings.gitpegClientSecret,
                        gitpegRegistrationMode: settings.gitpegRegistrationMode,
                        gitpegReturnUrl: settings.gitpegReturnUrl,
                        gitpegWebhookUrl: settings.gitpegWebhookUrl,
                        gitpegWebhookSecret: settings.gitpegWebhookSecret,
                        gitpegModuleCandidates: settings.gitpegModuleCandidates,
                        erpnextSync: settings.erpnextSync,
                        erpnextUrl: erpDraft.url,
                        erpnextSiteName: erpDraft.siteName,
                        erpnextApiKey: erpDraft.apiKey,
                        erpnextApiSecret: erpDraft.apiSecret,
                        erpnextUsername: erpDraft.username,
                        erpnextPassword: erpDraft.password,
                        erpnextProjectDoctype: erpWritebackDraft.projectDoctype,
                        erpnextProjectLookupField: erpWritebackDraft.projectLookupField,
                        erpnextProjectLookupValue: erpWritebackDraft.projectLookupValue,
                        erpnextGitpegProjectUriField: erpWritebackDraft.gitpegProjectUriField,
                        erpnextGitpegSiteUriField: erpWritebackDraft.gitpegSiteUriField,
                        erpnextGitpegStatusField: erpWritebackDraft.gitpegStatusField,
                        erpnextGitpegResultJsonField: erpWritebackDraft.gitpegResultJsonField,
                        erpnextGitpegRegistrationIdField: erpWritebackDraft.gitpegRegistrationIdField,
                        erpnextGitpegNodeUriField: erpWritebackDraft.gitpegNodeUriField,
                        erpnextGitpegShellUriField: erpWritebackDraft.gitpegShellUriField,
                        erpnextGitpegProofHashField: erpWritebackDraft.gitpegProofHashField,
                        erpnextGitpegIndustryProfileIdField: erpWritebackDraft.gitpegIndustryProfileIdField,
                        wechatMiniapp: settings.wechatMiniapp,
                        droneImport: settings.droneImport,
                      })
                    }
                  >
                    保存配置
                  </button>
                </div>
              </div>
            </div>
          )}

          {inviteOpen && (
            <div className="invite-mask" onClick={() => setInviteOpen(false)}>
              <div className="invite-panel" onClick={(e) => e.stopPropagation()}>
                <div className="invite-title">邀请成员</div>
                <div className="invite-form">
                  <input className="setting-input" value={inviteForm.name} placeholder="成员姓名" onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })} />
                  <input className="setting-input" value={inviteForm.email} placeholder="邮箱/手机号" onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })} />
                  <select className="setting-select" value={inviteForm.role} onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value as TeamRole })}>
                    <option value="AI">质检员</option>
                    <option value="SUPERVISOR">监理</option>
                    <option value="OWNER">项目管理员</option>
                    <option value="PUBLIC">只读成员</option>
                  </select>
                  <select className="setting-select" value={inviteForm.projectId} onChange={(e) => setInviteForm({ ...inviteForm, projectId: e.target.value })}>
                    <option value="all">全部项目</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div className="invite-row">
                  <button className="btn-secondary" onClick={() => setInviteOpen(false)}>取消</button>
                  <button className="btn-primary" onClick={addMember}>发送邀请</button>
                </div>
              </div>
            </div>
          )}

          {projectDetailOpen && detailProject && (
            <div
              style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.35)', zIndex: 998 }}
              onClick={() => { setProjectDetailOpen(false); setDetailEdit(false); setDetailProjectDraft(null); setDetailDraft(null) }}
            >
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  right: 0,
                  width: 480,
                  maxWidth: '92vw',
                  height: '100%',
                  background: '#fff',
                  borderLeft: '1px solid #E2E8F0',
                  padding: 16,
                  overflowY: 'auto',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0F172A' }}>项目详情</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {!detailEdit && <button onClick={startEditDetail} style={{ border: '1px solid #BFDBFE', background: '#EFF6FF', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: '#1A56DB' }}>编辑</button>}
                    {detailEdit && (
                      <>
                        <button onClick={saveDetailMeta} style={{ border: '1px solid #86EFAC', background: '#ECFDF5', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', color: '#059669' }}>保存</button>
                        <button onClick={() => { setDetailEdit(false); setDetailProjectDraft(null); setDetailDraft(null) }} style={{ border: '1px solid #E2E8F0', background: '#fff', borderRadius: 6, padding: '4px 10px', cursor: 'pointer' }}>取消</button>
                      </>
                    )}
                    <button onClick={() => { setProjectDetailOpen(false); setDetailEdit(false); setDetailProjectDraft(null); setDetailDraft(null) }} style={{ border: '1px solid #E2E8F0', background: '#fff', borderRadius: 6, padding: '4px 10px', cursor: 'pointer' }}>关闭</button>
                  </div>
                </div>

                {!detailEdit && (
                  <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', rowGap: 8, fontSize: 13, marginBottom: 14 }}>
                    <span style={{ color: '#64748B' }}>项目名称</span><strong>{detailProject.name}</strong>
                    <span style={{ color: '#64748B' }}>项目类型</span><span>{TYPE_LABEL[detailProject.type] || detailProject.type}</span>
                    <span style={{ color: '#64748B' }}>业主单位</span><span>{detailProject.owner_unit}</span>
                    <span style={{ color: '#64748B' }}>施工单位</span><span>{detailProject.contractor || '-'}</span>
                    <span style={{ color: '#64748B' }}>监理单位</span><span>{detailProject.supervisor || '-'}</span>
                    <span style={{ color: '#64748B' }}>合同编号</span><span>{detailProject.contract_no || '-'}</span>
                    <span style={{ color: '#64748B' }}>ERP 项目编码</span><span>{detailProject.erp_project_code || '-'}</span>
                    <span style={{ color: '#64748B' }}>ERP 项目名称</span><span>{detailProject.erp_project_name || '-'}</span>
                    <span style={{ color: '#64748B' }}>工期</span><span>{detailProject.start_date || '-'} ~ {detailProject.end_date || '-'}</span>
                    <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{detailProject.v_uri}</code>
                    <span style={{ color: '#64748B' }}>零号台帐</span>
                    <span>
                      {`${(Array.isArray(detailProject.zero_personnel) ? detailProject.zero_personnel.filter((row) => String(row?.name || '').trim()).length : 0)}名人员 · ${(Array.isArray(detailProject.zero_equipment) ? detailProject.zero_equipment.filter((row) => String(row?.name || '').trim()).length : 0)}台仪器 · 等待秩签审批`}
                    </span>
                    <span style={{ color: '#64748B' }}>秩签状态</span>
                    <span>{detailProject.zero_sign_status || 'pending'}</span>
                    <span style={{ color: '#64748B' }}>质检台帐</span>
                    <span>{detailProject.qc_ledger_unlocked ? '已解锁' : '待解锁（监理秩签后）'}</span>
                  </div>
                )}

                {detailEdit && detailProjectDraft && (
                  <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', rowGap: 8, fontSize: 13, marginBottom: 14 }}>
                    <span style={{ color: '#64748B' }}>项目名称</span>
                    <input value={detailProjectDraft.name} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, name: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                    <span style={{ color: '#64748B' }}>项目类型</span>
                    <select value={detailProjectDraft.type} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, type: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
                      {PROJECT_TYPE_OPTIONS.map((opt) => (
                        <option key={`detail-${opt.value}`} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <span style={{ color: '#64748B' }}>业主单位</span>
                    <input value={detailProjectDraft.owner_unit} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, owner_unit: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                    <span style={{ color: '#64748B' }}>施工单位</span>
                    <input value={detailProjectDraft.contractor} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, contractor: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                    <span style={{ color: '#64748B' }}>监理单位</span>
                    <input value={detailProjectDraft.supervisor} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, supervisor: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                    <span style={{ color: '#64748B' }}>合同编号</span>
                    <input value={detailProjectDraft.contract_no} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, contract_no: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                    <span style={{ color: '#64748B' }}>开工日期</span>
                    <input type="date" value={detailProjectDraft.start_date} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, start_date: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                    <span style={{ color: '#64748B' }}>完工日期</span>
                    <input type="date" value={detailProjectDraft.end_date} onChange={(e) => setDetailProjectDraft({ ...detailProjectDraft, end_date: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                    <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{detailProject.v_uri}</code>
                  </div>
                )}

                <Card title="范围模型" icon="🧭" style={{ marginBottom: 10 }}>
                  {!detailMeta && <div style={{ color: '#94A3B8', fontSize: 12 }}>该项目暂无扩展注册信息（老数据）。</div>}
                  {detailMeta && !detailEdit && (
                    <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 8, fontSize: 13 }}>
                      <span style={{ color: '#64748B' }}>分段方式</span><span>{detailMeta.segType}</span>
                      <span style={{ color: '#64748B' }}>桩号范围</span><span>{detailMeta.segStart || '-'} ~ {detailMeta.segEnd || '-'}</span>
                      <span style={{ color: '#64748B' }}>分段间隔</span><span>{detailMeta.kmInterval} km</span>
                      <span style={{ color: '#64748B' }}>主要检测类型</span>
                      <span>
                        {(detailMeta.inspectionTypes || []).length
                          ? (detailMeta.inspectionTypes || []).map((key) => INSPECTION_TYPE_LABEL[key as InspectionTypeKey] || key).join(' / ')
                          : '-'}
                      </span>
                      <span style={{ color: '#64748B' }}>权限模板</span><span>{detailMeta.permTemplate}</span>
                      <span style={{ color: '#64748B' }}>初始成员</span><span>{detailMeta.memberCount} 人</span>
                    </div>
                  )}
                  {detailEdit && detailDraft && (
                    <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', rowGap: 8, fontSize: 13 }}>
                      <span style={{ color: '#64748B' }}>分段方式</span>
                      <select value={detailDraft.segType} onChange={(e) => setDetailDraft({ ...detailDraft, segType: e.target.value as SegType })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
                        <option value="km">km</option><option value="contract">contract</option><option value="structure">structure</option>
                      </select>
                      <span style={{ color: '#64748B' }}>桩号起点</span>
                      <input value={detailDraft.segStart} onChange={(e) => setDetailDraft({ ...detailDraft, segStart: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                      <span style={{ color: '#64748B' }}>桩号终点</span>
                      <input value={detailDraft.segEnd} onChange={(e) => setDetailDraft({ ...detailDraft, segEnd: e.target.value })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                      <span style={{ color: '#64748B' }}>分段间隔(km)</span>
                      <input
                        type="number"
                        min={1}
                        value={detailDraft.kmInterval}
                        onChange={(e) => setDetailDraft({ ...detailDraft, kmInterval: normalizeKmInterval(e.target.value, detailDraft.kmInterval) })}
                        style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}
                      />
                      <span style={{ color: '#64748B' }}>主要检测类型</span>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {INSPECTION_TYPE_OPTIONS.map((opt) => {
                          const checked = detailDraft.inspectionTypes.includes(opt.key)
                          return (
                            <label
                              key={`detail-${opt.key}`}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 5,
                                padding: '4px 8px',
                                border: `1px solid ${checked ? '#1A56DB' : '#E2E8F0'}`,
                                borderRadius: 999,
                                background: checked ? '#EFF6FF' : '#fff',
                                color: checked ? '#1A56DB' : '#475569',
                                fontSize: 12,
                                cursor: 'pointer',
                                userSelect: 'none',
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() =>
                                  toggleInspectionType(
                                    opt.key,
                                    detailDraft.inspectionTypes,
                                    (next) => setDetailDraft({ ...detailDraft, inspectionTypes: next })
                                  )
                                }
                              />
                              {opt.label}
                            </label>
                          )
                        })}
                      </div>
                      <span style={{ color: '#64748B' }}>权限模板</span>
                      <select value={detailDraft.permTemplate} onChange={(e) => setDetailDraft({ ...detailDraft, permTemplate: e.target.value as PermTemplate })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
                        <option value="standard">standard</option><option value="strict">strict</option><option value="open">open</option><option value="custom">custom</option>
                      </select>
                    </div>
                  )}
                </Card>

                {detailMeta && !detailEdit && detailMeta.contractSegs.length > 0 && (
                  <Card title="合同段明细" icon="📦" style={{ marginBottom: 10 }}>
                    {detailMeta.contractSegs.map((seg, idx) => (
                      <div key={`${seg.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                        <strong>{seg.name || `合同段 ${idx + 1}`}</strong>
                        <span style={{ color: '#475569' }}>{seg.range || '-'}</span>
                      </div>
                    ))}
                  </Card>
                )}
                {detailEdit && detailDraft && (
                  <Card title="合同段明细" icon="📦" style={{ marginBottom: 10 }}>
                    {detailDraft.contractSegs.map((seg, idx) => (
                      <div key={`${seg.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                        <input value={seg.name} onChange={(e) => setDetailDraft({ ...detailDraft, contractSegs: detailDraft.contractSegs.map((x, i) => i === idx ? { ...x, name: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                        <input value={seg.range} onChange={(e) => setDetailDraft({ ...detailDraft, contractSegs: detailDraft.contractSegs.map((x, i) => i === idx ? { ...x, range: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                        <button onClick={() => setDetailDraft({ ...detailDraft, contractSegs: detailDraft.contractSegs.filter((_, i) => i !== idx) })} style={{ padding: '4px 8px', border: '1px solid #FECACA', borderRadius: 6, background: '#FEF2F2', color: '#DC2626', cursor: 'pointer' }}>删</button>
                      </div>
                    ))}
                    <button onClick={() => setDetailDraft({ ...detailDraft, contractSegs: [...detailDraft.contractSegs, { name: '', range: '' }] })} style={{ marginTop: 8, padding: '6px 10px', border: '1px solid #E2E8F0', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>+ 添加合同段</button>
                  </Card>
                )}

                {detailMeta && !detailEdit && detailMeta.structures.length > 0 && (
                  <Card title="结构物明细" icon="🏛️" style={{ marginBottom: 10 }}>
                    {detailMeta.structures.map((st, idx) => (
                      <div key={`${st.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 100px', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                        <span style={{ color: '#1A56DB', fontWeight: 700 }}>{st.kind || '-'}</span>
                        <strong>{st.name || `结构物 ${idx + 1}`}</strong>
                        <span style={{ color: '#64748B' }}>{st.code || '-'}</span>
                      </div>
                    ))}
                  </Card>
                )}
                {detailEdit && detailDraft && (
                  <Card title="结构物明细" icon="🏛️" style={{ marginBottom: 10 }}>
                    {detailDraft.structures.map((st, idx) => (
                      <div key={`${st.name}-${idx}`} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 100px auto', gap: 8, padding: '8px 0', borderBottom: '1px solid #F1F5F9', fontSize: 13 }}>
                        <select value={st.kind} onChange={(e) => setDetailDraft({ ...detailDraft, structures: detailDraft.structures.map((x, i) => i === idx ? { ...x, kind: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }}>
                          <option>桥梁</option><option>隧道</option><option>涵洞</option>
                        </select>
                        <input value={st.name} onChange={(e) => setDetailDraft({ ...detailDraft, structures: detailDraft.structures.map((x, i) => i === idx ? { ...x, name: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                        <input value={st.code} onChange={(e) => setDetailDraft({ ...detailDraft, structures: detailDraft.structures.map((x, i) => i === idx ? { ...x, code: e.target.value } : x) })} style={{ padding: 8, border: '1px solid #E2E8F0', borderRadius: 6 }} />
                        <button onClick={() => setDetailDraft({ ...detailDraft, structures: detailDraft.structures.filter((_, i) => i !== idx) })} style={{ padding: '4px 8px', border: '1px solid #FECACA', borderRadius: 6, background: '#FEF2F2', color: '#DC2626', cursor: 'pointer' }}>删</button>
                      </div>
                    ))}
                    <button onClick={() => setDetailDraft({ ...detailDraft, structures: [...detailDraft.structures, { kind: '桥梁', name: '', code: '' }] })} style={{ marginTop: 8, padding: '6px 10px', border: '1px solid #E2E8F0', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>+ 添加结构物</button>
                  </Card>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <Toast message={toastMsg} />
    </div>
  )
}

