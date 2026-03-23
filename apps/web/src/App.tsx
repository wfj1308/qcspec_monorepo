import React, { useEffect, useState } from 'react'
import { useUIStore, useProjectStore, useAuthStore } from './store'
import { Toast, Card, Button, VPathDisplay } from './components/ui'
import { useProof, useTeam, useSettings, useProjects } from './hooks/useApi'
import Dashboard from './pages/Dashboard'
import InspectionPage from './pages/InspectionPage'
import PhotosPage from './pages/PhotosPage'
import ReportsPage from './pages/ReportsPage'

const DEMO_ENTERPRISE = {
  id: '11111111-1111-4111-8111-111111111111',
  v_uri: 'v://cn/zhongbei/',
  name: '中北工程设计咨询有限公司',
  short_name: '中北工程',
  plan: 'enterprise' as const,
  proof_quota: 99999,
  proof_used: 47,
}

const DEMO_USER = {
  id: '22222222-2222-4222-8222-222222222222',
  enterprise_id: '11111111-1111-4111-8111-111111111111',
  v_uri: 'v://cn/zhongbei/executor/ligong/',
  name: '李总工',
  email: 'admin@zhongbei.com',
  dto_role: 'OWNER' as const,
  title: '总工程师',
}

const DEMO_PROJECTS = [
  {
    id: '33333333-3333-4333-8333-333333333333',
    enterprise_id: '11111111-1111-4111-8111-111111111111',
    v_uri: 'v://cn/zhongbei/highway/jinggang-2026/',
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
    v_uri: 'v://cn/zhongbei/bridge/qinhe/',
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
  inspectionTypes: InspectionTypeKey[]
  contractSegs: { name: string; range: string }[]
  structures: { kind: string; name: string; code: string }[]
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
  erpnextSync: boolean
  wechatMiniapp: boolean
  droneImport: boolean
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

const ACTIVITY_ITEMS = [
  { dot: '#059669', text: '王质检在京港高速大修录入了路面平整度记录', time: '10 分钟前' },
  { dot: '#1A56DB', text: '张项目经理注册了新项目：沁河特大桥定检', time: '2 小时前' },
  { dot: '#D97706', text: '系统生成了 3 月份质检汇总报告', time: '今天 09:00' },
  { dot: '#DC2626', text: 'K49+200 裂缝宽度超标，请尽快复检', time: '昨天 14:15' },
]

const QUICK_USERS = {
  admin: { ...DEMO_USER, name: '李总工', email: 'admin@zhongbei.com', dto_role: 'OWNER' as const, title: '超级管理员' },
  pm: { ...DEMO_USER, id: '22222222-2222-4222-8222-222222222223', name: '张项目经理', email: 'pm@zhongbei.com', dto_role: 'SUPERVISOR' as const, title: '项目经理' },
  inspector: { ...DEMO_USER, id: '22222222-2222-4222-8222-222222222224', name: '王质检', email: 'qc@zhongbei.com', dto_role: 'AI' as const, title: '质检员' },
}

export default function App() {
  const { activeTab, setActiveTab, toastMsg, sidebarOpen, setSidebarOpen, showToast } = useUIStore()
  const { projects, setProjects, currentProject, setCurrentProject, addProject } = useProjectStore()
  const { setUser, logout, enterprise, user } = useAuthStore()
  const { list: listProjectsApi, create: createProjectApi, update: updateProjectApi, remove: removeProjectApi } = useProjects()
  const { listMembers, inviteMember, updateMember: updateMemberApi, removeMember: removeMemberApi } = useTeam()
  const { getSettings, saveSettings, uploadTemplate } = useSettings()

  const [appReady, setAppReady] = useState(false)
  const [loginTab, setLoginTab] = useState<'login' | 'register'>('login')
  const [loginForm, setLoginForm] = useState({ account: '', pass: '' })
  const [entForm, setEntForm] = useState({ name: '', adminPhone: '', pass: '', uscc: '' })

  useEffect(() => {
    if (!appReady) return
    if (!projects.length) {
      setProjects(DEMO_PROJECTS)
      setCurrentProject(DEMO_PROJECTS[0])
    }
  }, [appReady, projects.length, setProjects, setCurrentProject])

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
    contractor: '',
    supervisor: '',
    contract_no: '',
    start_date: '',
    end_date: '',
    description: '',
    seg_start: 'K0+000',
    seg_end: 'K100+000',
  })
  const [regKmInterval, setRegKmInterval] = useState(20)
  const [registerSuccess, setRegisterSuccess] = useState<{ id: string; name: string; uri: string } | null>(null)
  const [vpathStatus, setVpathStatus] = useState<'checking' | 'available' | 'taken'>('checking')
  const [regInspectionTypes, setRegInspectionTypes] = useState<InspectionTypeKey[]>(['flatness', 'crack'])
  const [contractSegs, setContractSegs] = useState([{ name: '一标段', range: 'K0~K30' }])
  const [structures, setStructures] = useState([{ kind: '桥梁', name: '沁河大桥', code: 'QH-B01' }])

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
    erpnextSync: false,
    wechatMiniapp: true,
    droneImport: false,
  })
  const [erpDraft, setErpDraft] = useState({ url: '', apiKey: '' })
  const [erpTesting, setErpTesting] = useState(false)
  const [erpTestMsg, setErpTestMsg] = useState('')
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
  const { listProofs, verify: verifyProof } = useProof()
  const [proofRows, setProofRows] = useState<Array<{
    proof_id: string
    summary?: string
    object_type?: string
    action?: string
    created_at?: string
  }>>([])
  const [proofLoading, setProofLoading] = useState(false)
  const [proofVerifying, setProofVerifying] = useState<string | null>(null)
  const isDemoEnterprise = enterprise?.id === DEMO_ENTERPRISE.id
  const canUseEnterpriseApi = !!enterprise?.id && !isDemoEnterprise

  const regUri = `v://cn/zhongbei/${regForm.type}/${(regForm.name || 'project').replace(/\s+/g, '').slice(0, 20).toLowerCase()}/`
  const detailProject = projects.find((p) => p.id === projectDetailId) || null
  const detailMeta = (projectDetailId && projectMeta[projectDetailId]) || null
  const buildDefaultProjectMeta = (): ProjectRegisterMeta => ({
    segType: 'km',
    segStart: 'K0+000',
    segEnd: 'K100+000',
    inspectionTypes: ['flatness', 'crack'],
    contractSegs: [],
    structures: [],
    permTemplate: 'standard',
    memberCount: members.length,
  })
  const normalizeProjectMeta = (meta?: Partial<ProjectRegisterMeta> | null): ProjectRegisterMeta => {
    const base = buildDefaultProjectMeta()
    if (!meta) return base
    const selectedInspectionTypes = Array.isArray(meta.inspectionTypes)
      ? meta.inspectionTypes.filter((key): key is InspectionTypeKey => INSPECTION_TYPE_OPTIONS.some((item) => item.key === key))
      : []
    return {
      ...base,
      ...meta,
      inspectionTypes: selectedInspectionTypes.length > 0 ? selectedInspectionTypes : base.inspectionTypes,
      contractSegs: Array.isArray(meta.contractSegs) ? meta.contractSegs.map((item) => ({ ...item })) : base.contractSegs,
      structures: Array.isArray(meta.structures) ? meta.structures.map((item) => ({ ...item })) : base.structures,
    }
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
  const permissionTreeRoot = enterprise?.v_uri || proj.v_uri || 'v://cn/zhongbei/'
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
    listProofs(proj.id).then((res) => {
      if (cancelled) return
      const r = res as { data?: typeof proofRows } | null
      setProofRows(r?.data || [])
    }).finally(() => {
      if (!cancelled) setProofLoading(false)
    })
    return () => { cancelled = true }
  }, [activeTab, proj?.id, listProofs])

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
        settings?: Partial<SettingsState> & { permissionMatrix?: Array<Partial<PermissionRow> & { role?: string }> }
      } | null
      if (!r?.settings) return
      const { permissionMatrix: matrixFromApi, ...settingsFromApi } = r.settings
      setSettings((prev) => ({ ...prev, ...settingsFromApi }))
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
  }, [appReady, canUseEnterpriseApi, enterprise?.id, listMembers, getSettings])

  const nextRegStep = () => {
    if (registerStep === 1 && (!regForm.name || !regForm.owner_unit || !regForm.type)) {
      showToast('请先完成项目基本信息')
      return
    }
    if (registerStep === 2 && regInspectionTypes.length === 0) {
      showToast('请至少选择 1 个主要检测类型')
      return
    }
    setRegisterStep((s) => Math.min(3, s + 1))
  }
  const prevRegStep = () => setRegisterStep((s) => Math.max(1, s - 1))

  const addContractSeg = () => setContractSegs((prev) => [...prev, { name: `新标段${prev.length + 1}`, range: '' }])
  const addStructure = () => setStructures((prev) => [...prev, { kind: '桥梁', name: '', code: '' }])
  const resetRegister = () => {
    setRegisterStep(1)
    setRegisterSuccess(null)
    setRegForm({
      name: '',
      type: 'highway',
      owner_unit: '',
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
  }

  const submitRegister = async () => {
    if (!regForm.name || !regForm.owner_unit) {
      showToast('请先填写项目名称和业主单位')
      return
    }
    if (projects.some((p) => p.v_uri === regUri)) {
      setVpathStatus('taken')
      showToast('该 v:// 节点已存在，请修改项目名称或类型')
      return
    }

    if (canUseEnterpriseApi && enterprise?.id) {
      const created = await createProjectApi({
        enterprise_id: enterprise.id,
        name: regForm.name,
        type: regForm.type,
        owner_unit: regForm.owner_unit,
        contractor: regForm.contractor || undefined,
        supervisor: regForm.supervisor || undefined,
        contract_no: regForm.contract_no || undefined,
        start_date: regForm.start_date || undefined,
        end_date: regForm.end_date || undefined,
        description: regForm.description || undefined,
        seg_type: segType,
        seg_start: regForm.seg_start || undefined,
        seg_end: regForm.seg_end || undefined,
        perm_template: permTemplate,
      }) as { id?: string; v_uri?: string; name?: string } | null

      if (!created?.id) return

      const refreshed = await listProjectsApi(enterprise.id) as { data?: Parameters<typeof setProjects>[0] } | null
      if (refreshed?.data) {
        setProjects(refreshed.data)
        const createdProject = refreshed.data.find((p) => p.id === created.id) || null
        if (createdProject) setCurrentProject(createdProject)
      }

      setProjectMeta((prev) => ({
        ...prev,
        [created.id as string]: {
          segType,
          segStart: regForm.seg_start,
          segEnd: regForm.seg_end,
          inspectionTypes: regInspectionTypes,
          contractSegs,
          structures,
          permTemplate,
          memberCount: members.length,
        },
      }))
      setRegisterSuccess({
        id: created.id,
        name: created.name || regForm.name,
        uri: created.v_uri || regUri,
      })
      showToast('项目注册成功')
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
      type: regForm.type,
      owner_unit: regForm.owner_unit,
      contractor: regForm.contractor,
      supervisor: regForm.supervisor,
      contract_no: regForm.contract_no,
      start_date: regForm.start_date,
      end_date: regForm.end_date,
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
        inspectionTypes: regInspectionTypes,
        contractSegs,
        structures,
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

  const persistSettings = async (patch: Partial<SettingsState>) => {
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

  const verifyGitpegToken = () => {
    if (!settings.gitpegToken.trim()) {
      setGitpegVerifyMsg({ text: '⚠️ 请先填写 Token', color: '#D97706' })
      return
    }
    setGitpegVerifying(true)
    setGitpegVerifyMsg({ text: '⏳ 验证中...', color: '#64748B' })
    setTimeout(() => {
      setGitpegVerifying(false)
      setGitpegVerifyMsg({
        text: '✅ 连接成功 · v://cn/zhongbei/ 节点已就绪 · 延迟 42ms',
        color: '#059669',
      })
    }, 420)
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

  const testErpConnection = () => {
    if (!erpDraft.url.trim() || !erpDraft.apiKey.trim()) {
      setErpTestMsg('⚠️ 请先填写 ERP URL 和 API Key')
      return
    }
    setErpTesting(true)
    setErpTestMsg('⏳ 测试连接中...')
    setTimeout(() => {
      setErpTesting(false)
      setErpTestMsg('✅ ERPNext 连接成功（模拟）')
    }, 600)
  }

  const doLogin = (key: keyof typeof QUICK_USERS = 'admin') => {
    const user = QUICK_USERS[key]
    setUser(user, DEMO_ENTERPRISE, `demo-token-${key}`)
    if (!projects.length) {
      setProjects(DEMO_PROJECTS)
      setCurrentProject(DEMO_PROJECTS[0])
    }
    setAppReady(true)
    showToast(`欢迎回来，${user.name}`)
  }

  const doLogout = () => {
    logout()
    setAppReady(false)
    setLoginTab('login')
    setLoginForm({ account: '', pass: '' })
    showToast('已退出登录')
  }

  const doRegisterEnterprise = () => {
    if (!entForm.name || !entForm.adminPhone || !entForm.pass) {
      showToast('请完整填写企业注册信息')
      return
    }
    showToast('企业注册成功，请登录进入平台')
    setLoginTab('login')
  }

  const openProjectDetail = (id: string, edit = false) => {
    setProjectDetailId(id)
    setProjectDetailOpen(true)
    if (!edit) {
      setDetailEdit(false)
      setDetailProjectDraft(null)
      setDetailDraft(null)
      return
    }
    const selectedProject = projects.find((p) => p.id === id)
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
              <button className="l-btn" onClick={() => doLogin('admin')}>登录</button>
              <div className="l-hint">演示账号快速登录</div>
              <div className="demo-accounts">
                <div className="demo-title">Demo Accounts</div>
                <button className="demo-btn" onClick={() => doLogin('admin')}><strong>admin@zhongbei.com</strong> | 超级管理员</button>
                <button className="demo-btn" onClick={() => doLogin('pm')}><strong>pm@zhongbei.com</strong> | 项目经理</button>
                <button className="demo-btn" onClick={() => doLogin('inspector')}><strong>qc@zhongbei.com</strong> | 质检员</button>
              </div>
            </div>
          )}

          {loginTab === 'register' && (
            <div className="login-form">
              <input className="l-input" value={entForm.name} onChange={(e) => setEntForm({ ...entForm, name: e.target.value })} placeholder="企业名称" />
              <input className="l-input" value={entForm.adminPhone} onChange={(e) => setEntForm({ ...entForm, adminPhone: e.target.value })} placeholder="管理员手机号" />
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
                        <span style={{ fontSize: 11, color: '#94A3B8' }}>
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
                            <div style={{ fontSize: 11, color: '#94A3B8' }}>{p.contract_no || '-'} | {p.start_date || '-'} ~ {p.end_date || '-'}</div>
                          </td>
                          <td>
                            <span className={`type-chip chip-${p.type}`}>
                              {TYPE_ICON[p.type] || '🏗️'} {TYPE_LABEL[p.type] || p.type}
                            </span>
                          </td>
                          <td style={{ color: '#475569' }}>{p.owner_unit}</td>
                          <td>
                            <div style={{ fontSize: 12, color: '#334155' }}>{segLabel}</div>
                            <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>{permLabel}</div>
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
                  { num: 3, label: '确认注册' },
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
                            检测范围会映射为 v:// 子节点，每个分段都将成为独立归档节点。
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
                          <div className="node-tree-sub">└─ reports/</div>
                        </div>
                      </div>
                    </>
                  )}

                  {registerStep === 3 && (
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
                        <span style={{ color: '#64748B' }}>工期</span><span>{regForm.start_date || '-'} ~ {regForm.end_date || '-'}</span>
                        <span style={{ color: '#64748B' }}>分段方式</span><span>{segType === 'km' ? '按桩号' : segType === 'contract' ? '按合同段' : '按结构物'}</span>
                        <span style={{ color: '#64748B' }}>主要检测类型</span>
                        <span>{regInspectionTypes.length ? regInspectionTypes.map((key) => INSPECTION_TYPE_LABEL[key]).join(' / ') : '-'}</span>
                        <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{regUri}</code>
                      </div>
                    </div>
                  )}

                  <div className="btn-row">
                    <button className="btn-secondary" onClick={prevRegStep} disabled={registerStep === 1}>上一步</button>
                    {registerStep < 3 ? (
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
                              <span style={{ marginLeft: 6, fontSize: 10, color: '#059669', fontWeight: 800 }}>NEW</span>
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
                      <div style={{ fontSize: 11, color: '#94A3B8' }}>{m.email}</div>
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
                    <div style={{ fontSize: 10, color: '#475569', letterSpacing: 1, marginBottom: 6 }}>V:// 节点权限结构 · 实时预览</div>
                    <div>{permissionTreeRoot}</div>
                    {permissionTreeRows.map((row, idx) => (
                      <div key={`${row.role}-${idx}`} className="node-tree-sub">
                        {idx === permissionTreeRows.length - 1 ? '└' : '├'}─ {row.role.toLowerCase()}/ <span style={{ color: '#64748B' }}>{row.granted}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: '#64748B', lineHeight: 1.6, marginTop: 8 }}>
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
                          fontSize: 10,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.gitpegEnabled ? '#ECFDF5' : '#F8FAFC',
                          color: settings.gitpegEnabled ? '#059669' : '#64748B',
                        }}>
                          {settings.gitpegEnabled ? '已启用' : '未接入'}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#64748B' }}>质检记录自动推送到 GitPeg v:// 链，不可篡改存证</div>
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
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#334155', marginBottom: 8 }}>GitPeg 连接配置</div>
                        <div style={{ display: 'grid', gap: 8 }}>
                          <input
                            className="setting-input"
                            value={settings.gitpegToken}
                            onChange={(e) => setSettings({ ...settings, gitpegToken: e.target.value })}
                            placeholder="gitpeg_token_xxxxxxxxxxxxxxxx"
                            type="password"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input className="setting-input" value={enterpriseInfo.vUri} readOnly style={{ fontFamily: 'var(--mono)', color: '#1A56DB' }} />
                          <button className="btn-primary" style={{ flex: 'none' }} onClick={verifyGitpegToken} disabled={gitpegVerifying}>
                            {gitpegVerifying ? '验证中...' : '验证'}
                          </button>
                          {gitpegVerifyMsg.text && (
                            <div style={{ fontSize: 11, color: gitpegVerifyMsg.color }}>{gitpegVerifyMsg.text}</div>
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
                          fontSize: 10,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.erpnextSync ? '#ECFDF5' : '#F8FAFC',
                          color: settings.erpnextSync ? '#059669' : '#64748B',
                        }}>
                          {settings.erpnextSync ? '已启用' : '未接入'}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#64748B' }}>与 ERPNext 系统同步，质检合格才能计量</div>
                    </div>
                    <input type="checkbox" checked={settings.erpnextSync} onChange={(e) => setSettings({ ...settings, erpnextSync: e.target.checked })} />
                  </div>
                  {settings.erpnextSync && (
                    <div style={{ padding: '0 0 10px 40px' }}>
                      <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 8, padding: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#334155', marginBottom: 8 }}>ERPNext 连接配置</div>
                        <div style={{ display: 'grid', gap: 8 }}>
                          <input
                            className="setting-input"
                            value={erpDraft.url}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, url: e.target.value }))}
                            placeholder="https://erp.zhongbei.com"
                            style={{ fontFamily: 'var(--mono)' }}
                          />
                          <input
                            className="setting-input"
                            value={erpDraft.apiKey}
                            onChange={(e) => setErpDraft((prev) => ({ ...prev, apiKey: e.target.value }))}
                            placeholder="erpnext_api_key"
                            type="password"
                          />
                          <button className="btn-primary" style={{ flex: 'none' }} onClick={testErpConnection} disabled={erpTesting}>
                            {erpTesting ? '测试中...' : '测试连接'}
                          </button>
                          {erpTestMsg && <div style={{ fontSize: 11, color: erpTestMsg.includes('✅') ? '#059669' : '#D97706' }}>{erpTestMsg}</div>}
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
                          fontSize: 10,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.wechatMiniapp ? '#ECFDF5' : '#F8FAFC',
                          color: settings.wechatMiniapp ? '#059669' : '#64748B',
                        }}>
                          {settings.wechatMiniapp ? '已启用' : '未接入'}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#64748B' }}>施工人员通过微信扫码登录，现场质检录入</div>
                    </div>
                    <input type="checkbox" checked={settings.wechatMiniapp} onChange={(e) => setSettings({ ...settings, wechatMiniapp: e.target.checked })} />
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0' }}>
                    <div style={{ fontSize: 20, width: 28, textAlign: 'center' }}>🚁</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A' }}>无人机数据接入</div>
                        <span style={{
                          fontSize: 10,
                          fontWeight: 700,
                          borderRadius: 10,
                          padding: '2px 8px',
                          background: settings.droneImport ? '#ECFDF5' : '#FFFBEB',
                          color: settings.droneImport ? '#059669' : '#D97706',
                        }}>
                          {settings.droneImport ? '已启用' : 'Beta'}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#64748B' }}>大疆无人机巡检数据自动接入质检系统</div>
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
                    <div style={{ marginTop: 6, fontSize: 11, color: webhookResult.color, fontFamily: 'var(--mono)' }}>
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
                        erpnextSync: settings.erpnextSync,
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
                    <span style={{ color: '#64748B' }}>工期</span><span>{detailProject.start_date || '-'} ~ {detailProject.end_date || '-'}</span>
                    <span style={{ color: '#64748B' }}>v:// URI</span><code style={{ color: '#1A56DB', wordBreak: 'break-all' }}>{detailProject.v_uri}</code>
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
