import React, { useEffect, useState } from 'react'
import { useUIStore, useProjectStore, useAuthStore } from './store'
import { Toast, Card } from './components/ui'
import { useAuthApi, useProof, useTeam, useSettings, useProjects, useAutoreg, useErpnext } from './hooks/useApi'
import Dashboard from './pages/Dashboard'
import InspectionPage from './pages/InspectionPage'
import PhotosPage from './pages/PhotosPage'
import ReportsPage from './pages/ReportsPage'
import AppShellLayout from './components/layout/AppShellLayout'
import AuthEntry from './components/auth/AuthEntry'
import ProofPanel from './components/proof/ProofPanel'
import PaymentAuditPanel from './components/proof/PaymentAuditPanel'
import SpatialGovernancePanel from './components/proof/SpatialGovernancePanel'
import RwaOmEvolutionPanel from './components/proof/RwaOmEvolutionPanel'
import DocumentGovernancePanel from './components/proof/DocumentGovernancePanel'
import ProjectDetailDrawer from './components/projects/ProjectDetailDrawer'
import ProjectsPanel from './components/projects/ProjectsPanel'
import RegisterPanelFrame from './components/register/RegisterPanelFrame'
import RegisterStepOne from './components/register/RegisterStepOne'
import RegisterStepTwo from './components/register/RegisterStepTwo'
import RegisterStepThree from './components/register/RegisterStepThree'
import RegisterStepConfirm from './components/register/RegisterStepConfirm'
import InviteMemberModal, { type InviteFormState } from './components/team/InviteMemberModal'
import TeamPanel from './components/team/TeamPanel'
import PermissionsPanel from './components/permissions/PermissionsPanel'
import SettingsPanel from './components/settings/SettingsPanel'
import { useSettingsController } from './app/useSettingsController'
import { useRegisterController } from './app/useRegisterController'
import { useProjectDetailController } from './app/useProjectDetailController'
import { submitRegisterFlow } from './app/registerSubmitFlow'
import { pullErpProjectBindingFlow } from './app/registerErpBindingFlow'
import { addMemberFlow, removeMemberFlow, saveMemberRoleFlow } from './app/teamMemberFlows'
import { doLoginFlow, doLogoutFlow, doRegisterEnterpriseFlow } from './app/authFlows'
import { directProjectAutoregFlow, removeProjectFlow, retryProjectAutoregFlow } from './app/projectActionFlows'
import { applyPermissionTemplateFlow, persistPermissionMatrixFlow, updatePermissionCellFlow } from './app/permissionFlows'
import { doDemoLoginFlow, fillQuickLoginFlow, getQuickLoginOptions } from './app/demoLoginFlows'
import { useGitpegCallbackSync } from './app/useGitpegCallbackSync'
import { useProjectMetaSync } from './app/useProjectMetaSync'


import {
  DEMO_ENTERPRISE,
  DEMO_USER,
  DEMO_PROJECTS,
  NAV,
  NAV_SECTIONS,
  TeamRole,
  SegType,
  PermTemplate,
  InspectionTypeKey,
  PermissionRole,
  PermissionKey,
  ZeroLedgerTab,
  ZeroPersonnelRow,
  ZeroEquipmentRow,
  ZeroSubcontractRow,
  ZeroMaterialRow,
  TeamMember,
  ProjectRegisterMeta,
  PermissionRow,
  SettingsState,
  roleToTitle,
  toRoleDraftMap,
  PERMISSION_ROLE_LABEL,
  PERMISSION_COLUMNS,
  DEFAULT_PERMISSION_MATRIX,
  normalizePermissionMatrix,
  detectPermissionTemplate,
  TYPE_LABEL,
  TYPE_ICON,
  PROJECT_TYPE_OPTIONS,
  INSPECTION_TYPE_OPTIONS,
  INSPECTION_TYPE_LABEL,
  INSPECTION_TYPE_KEYS,
  normalizeKmInterval,
  normalizeTeamRole,
  ACTIVITY_ITEMS,
  QUICK_USERS,
} from './app/appShellShared'

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

  const [permTemplate, setPermTemplate] = useState<PermTemplate>('standard')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')


  const [members, setMembers] = useState<TeamMember[]>([
    { id: '55555555-5555-4555-8555-555555555551', name: '李总工', title: '总工程师', email: 'admin@zhongbei.com', role: 'OWNER', color: '#1A56DB', projects: ['33333333-3333-4333-8333-333333333333', '44444444-4444-4444-8444-444444444444'] },
    { id: '55555555-5555-4555-8555-555555555552', name: '王质检', title: '质检员', email: 'wang@zhongbei.com', role: 'AI', color: '#059669', projects: ['33333333-3333-4333-8333-333333333333'] },
    { id: '55555555-5555-4555-8555-555555555553', name: '钱监理', title: '监理工程师', email: 'qian@zhongbei.com', role: 'SUPERVISOR', color: '#7C3AED', projects: ['33333333-3333-4333-8333-333333333333'] },
  ])

  const [inviteForm, setInviteForm] = useState<InviteFormState>({
    name: '',
    email: '',
    role: 'AI',
    projectId: 'all',
  })
  const [memberRoleDrafts, setMemberRoleDrafts] = useState<Record<string, TeamRole>>(() => ({
    '55555555-5555-4555-8555-555555555551': 'OWNER',
    '55555555-5555-4555-8555-555555555552': 'AI',
    '55555555-5555-4555-8555-555555555553': 'SUPERVISOR',
  }))

  const [syncingProjectId, setSyncingProjectId] = useState<string | null>(null)
  const [permissionMatrix, setPermissionMatrix] = useState<PermissionRow[]>(() => normalizePermissionMatrix())
  const [permissionTemplate, setPermissionTemplate] = useState<PermTemplate>(() => detectPermissionTemplate(normalizePermissionMatrix()))
  const [projectMeta, setProjectMeta] = useState<Record<string, ProjectRegisterMeta>>({})
  const {
    listProofs,
    verify: verifyProof,
    stats: proofStatsApi,
    nodeTree: proofNodeTreeApi,
    boqRealtimeStatus: boqRealtimeStatusApi,
    boqItemSovereignHistory: boqItemSovereignHistoryApi,
    boqReconciliation: boqReconciliationApi,
    docFinalContext: docFinalContextApi,
    generatePaymentCertificate: generatePaymentCertificateApi,
    frequencyDashboard: frequencyDashboardApi,
    generateRailPactInstruction: generateRailPactInstructionApi,
    paymentAuditTrace: paymentAuditTraceApi,
    finalizeDocFinal: finalizeDocFinalApi,
    bindSpatialUtxo: bindSpatialUtxoApi,
    spatialDashboard: spatialDashboardApi,
    predictiveQualityAnalysis: predictiveQualityAnalysisApi,
    exportFinanceProof: exportFinanceProofApi,
    convertRwaAsset: convertRwaAssetApi,
    exportOmHandoverBundle: exportOmHandoverBundleApi,
    registerOmEvent: registerOmEventApi,
    generateNormEvolutionReport: generateNormEvolutionReportApi,
  } = useProof()
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
  const [paymentGenerating, setPaymentGenerating] = useState(false)
  const [paymentResult, setPaymentResult] = useState<any | null>(null)
  const [railpactSubmitting, setRailpactSubmitting] = useState(false)
  const [railpactResult, setRailpactResult] = useState<any | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditResult, setAuditResult] = useState<any | null>(null)
  const [frequencyLoading, setFrequencyLoading] = useState(false)
  const [frequencyResult, setFrequencyResult] = useState<any | null>(null)
  const [deliveryFinalizing, setDeliveryFinalizing] = useState(false)
  const [spatialLoading, setSpatialLoading] = useState(false)
  const [spatialDashboard, setSpatialDashboard] = useState<any | null>(null)
  const [aiRunning, setAiRunning] = useState(false)
  const [aiResult, setAiResult] = useState<any | null>(null)
  const [financeExporting, setFinanceExporting] = useState(false)
  const [rwaConverting, setRwaConverting] = useState(false)
  const [omExporting, setOmExporting] = useState(false)
  const [omEventSubmitting, setOmEventSubmitting] = useState(false)
  const [normEvolutionRunning, setNormEvolutionRunning] = useState(false)
  const [normEvolutionResult, setNormEvolutionResult] = useState<any | null>(null)
  const [lastOmRootProofId, setLastOmRootProofId] = useState('')
  const [boqRealtimeByProjectId, setBoqRealtimeByProjectId] = useState<Record<string, any>>({})
  const [boqRealtimeLoadingProjectId, setBoqRealtimeLoadingProjectId] = useState<string | null>(null)
  const [boqAuditByProjectId, setBoqAuditByProjectId] = useState<Record<string, any>>({})
  const [boqAuditLoadingProjectId, setBoqAuditLoadingProjectId] = useState<string | null>(null)
  const [boqProofPreview, setBoqProofPreview] = useState<any | null>(null)
  const [boqProofLoadingUri, setBoqProofLoadingUri] = useState<string | null>(null)
  const [boqSovereignPreview, setBoqSovereignPreview] = useState<any | null>(null)
  const [boqSovereignLoadingCode, setBoqSovereignLoadingCode] = useState<string | null>(null)
  const [gitpegCallbackHandled, setGitpegCallbackHandled] = useState(false)
  const isDemoEnterprise = enterprise?.id === DEMO_ENTERPRISE.id
  const canUseEnterpriseApi = !!enterprise?.id && !isDemoEnterprise

  const {
    settings,
    setSettings,
    erpDraft,
    setErpDraft,
    erpWritebackDraft,
    setErpWritebackDraft,
    erpTesting,
    erpTestMsg,
    gitpegVerifying,
    setGitpegVerifying,
    gitpegVerifyMsg,
    setGitpegVerifyMsg,
    webhookTesting,
    webhookResult,
    enterpriseInfo,
    setEnterpriseInfo,
    setReportTemplateFile,
    persistSettings,
    persistEnterpriseInfo,
    persistReportTemplate,
    verifyGitpegToken,
    testWebhook,
    testErpConnection,
  } = useSettingsController({
    canUseEnterpriseApi,
    enterpriseId: enterprise?.id || undefined,
    initialReportHeader: DEMO_ENTERPRISE.name,
    initialEnterpriseInfo: {
      name: DEMO_ENTERPRISE.name,
      vUri: DEMO_ENTERPRISE.v_uri,
      creditCode: '',
      adminEmail: DEMO_USER.email,
    },
    saveSettings,
    uploadTemplate,
    testGitpegRegistrar,
    testErpnext,
    showToast,
  })

  const {
    registerStep,
    setRegisterStep,
    segType,
    setSegType,
    regForm,
    setRegForm,
    erpBindingLoading,
    setErpBindingLoading,
    erpBinding,
    setErpBinding,
    regKmInterval,
    setRegKmInterval,
    registerSuccess,
    setRegisterSuccess,
    vpathStatus,
    setVpathStatus,
    regInspectionTypes,
    setRegInspectionTypes,
    contractSegs,
    setContractSegs,
    structures,
    setStructures,
    zeroLedgerTab,
    setZeroLedgerTab,
    zeroPersonnel,
    setZeroPersonnel,
    zeroEquipment,
    setZeroEquipment,
    zeroSubcontracts,
    setZeroSubcontracts,
    zeroMaterials,
    setZeroMaterials,
    regUri,
    makeRowId,
    buildExecutorUri,
    buildToolUri,
    buildSubcontractUri,
    getEquipmentValidity,
    regRangeTreeLines,
    zeroPersonnelCount,
    zeroEquipmentCount,
    zeroLedgerSummary,
    zeroLedgerTreeRows,
    registerSegCount,
    registerRecordCount,
    registerPreviewProjects,
    toggleInspectionType,
    nextRegStep,
    prevRegStep,
    addContractSeg,
    addStructure,
    resetRegister,
  } = useRegisterController({
    projects,
    projectMeta,
    settings,
    showToast,
  })

  const {
    projectDetailOpen,
    detailEdit,
    detailProjectDraft,
    detailDraft,
    detailProject,
    detailMeta,
    setDetailProjectDraft,
    setDetailDraft,
    openProjectDetail,
    startEditDetail,
    saveDetailMeta,
    closeProjectDetail,
    cancelDetailEdit,
  } = useProjectDetailController({
    projects,
    setProjects,
    currentProject,
    setCurrentProject,
    projectMeta,
    setProjectMeta,
    canUseEnterpriseApi,
    enterpriseId: enterprise?.id || undefined,
    memberCount: members.length,
    getProjectByIdApi,
    updateProjectApi,
    normalizeKmInterval,
    buildExecutorUri,
    buildToolUri,
    buildSubcontractUri,
    getEquipmentValidity,
    showToast,
  })
  const permissionTreeRoot = enterprise?.v_uri || proj.v_uri || 'v://cn.zhongbei/'
  const permissionTreeRows = permissionMatrix.map((row) => {
    const granted = PERMISSION_COLUMNS.filter((col) => row[col.key]).map((col) => col.label)
    return {
      role: row.role,
      granted: granted.length > 0 ? granted.join(' / ') : '无权限',
    }
  })

  const filteredProjects = projects.filter((p) => {
    if (searchText && !`${p.name}${p.owner_unit}`.toLowerCase().includes(searchText.toLowerCase())) return false
    if (statusFilter && p.status !== statusFilter) return false
    if (typeFilter && p.type !== typeFilter) return false
    return true
  })

  useEffect(() => {
    if (!projectDetailOpen || !detailProject?.id || !detailProject?.v_uri) return
    if (boqRealtimeByProjectId[detailProject.id]) return

    let cancelled = false
    const load = async () => {
      setBoqRealtimeLoadingProjectId(detailProject.id)
      try {
        const payload = await boqRealtimeStatusApi(detailProject.v_uri) as { ok?: boolean } | null
        if (cancelled) return
        if (payload?.ok) {
          setBoqRealtimeByProjectId((prev) => ({ ...prev, [detailProject.id]: payload }))
        }
      } catch {
        if (!cancelled) showToast('BOQ 实时进度加载失败')
      } finally {
        if (!cancelled) {
          setBoqRealtimeLoadingProjectId((current) => (current === detailProject.id ? null : current))
        }
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [projectDetailOpen, detailProject?.id, detailProject?.v_uri, boqRealtimeByProjectId, boqRealtimeStatusApi])

  useEffect(() => {
    if (!projectDetailOpen || !detailProject?.id || !detailProject?.v_uri) return
    if (boqAuditByProjectId[detailProject.id]) return

    let cancelled = false
    const load = async () => {
      setBoqAuditLoadingProjectId(detailProject.id)
      try {
        const payload = await boqReconciliationApi({
          project_uri: detailProject.v_uri,
          limit_items: 1000,
        }) as { ok?: boolean } | null
        if (cancelled) return
        if (payload?.ok) {
          setBoqAuditByProjectId((prev) => ({ ...prev, [detailProject.id]: payload }))
        }
      } catch {
        if (!cancelled) showToast('BOQ 主权审计对账加载失败')
      } finally {
        if (!cancelled) {
          setBoqAuditLoadingProjectId((current) => (current === detailProject.id ? null : current))
        }
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [projectDetailOpen, detailProject?.id, detailProject?.v_uri, boqAuditByProjectId, boqReconciliationApi])

  useEffect(() => {
    if (!projectDetailOpen) {
      setBoqProofPreview(null)
      setBoqProofLoadingUri(null)
      setBoqSovereignPreview(null)
      setBoqSovereignLoadingCode(null)
    }
  }, [projectDetailOpen])

  const handleOpenBoqProofChain = async (boqItemUri: string) => {
    if (!boqItemUri) return
    setBoqProofLoadingUri(boqItemUri)
    try {
      const payload = await docFinalContextApi(boqItemUri) as { ok?: boolean } | null
      if (payload?.ok) {
        setBoqProofPreview(payload)
      } else {
        showToast('未获取到该细目的 Proof 链上下文')
      }
    } catch {
      showToast('未获取到该细目的 Proof 链上下文')
    } finally {
      setBoqProofLoadingUri(null)
    }
  }

  const handleOpenBoqSovereignHistory = async (subitemCode: string) => {
    if (!detailProject?.v_uri || !subitemCode) return
    setBoqSovereignLoadingCode(subitemCode)
    try {
      const payload = await boqItemSovereignHistoryApi({
        project_uri: detailProject.v_uri,
        subitem_code: subitemCode,
        max_rows: 50000,
      }) as { ok?: boolean } | null
      if (payload?.ok) {
        setBoqSovereignPreview(payload)
      } else {
        showToast('未获取到该细目的主权历史')
      }
    } catch {
      showToast('未获取到该细目的主权历史')
    } finally {
      setBoqSovereignLoadingCode(null)
    }
  }

  useGitpegCallbackSync({
    gitpegCallbackHandled,
    setGitpegCallbackHandled,
    appReady,
    canUseEnterpriseApi,
    enterpriseId: enterprise?.id || undefined,
    completeGitpegApi,
    listProjectsApi,
    setProjects,
    setCurrentProject,
    setRegisterSuccess,
    showToast,
  })

  useProjectMetaSync({
    projects,
    memberCount: members.length,
    setProjectMeta,
  })

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
    setPaymentResult(null)
    setRailpactResult(null)
    setAuditResult(null)
    setFrequencyResult(null)
    setSpatialDashboard(null)
    setAiResult(null)
    setNormEvolutionResult(null)
    setLastOmRootProofId('')
  }, [proj?.id])

  useEffect(() => {
    if (activeTab !== 'proof' || !proj?.v_uri) return
    let cancelled = false
    setFrequencyLoading(true)
    frequencyDashboardApi(proj.v_uri, 200).then((res) => {
      if (cancelled) return
      const payload = res as { ok?: boolean } | null
      if (payload?.ok) {
        setFrequencyResult(payload)
      }
    }).finally(() => {
      if (!cancelled) setFrequencyLoading(false)
    })
    return () => { cancelled = true }
  }, [activeTab, proj?.v_uri, frequencyDashboardApi])

  useEffect(() => {
    if (activeTab !== 'proof' || !proj?.v_uri) return
    let cancelled = false
    setSpatialLoading(true)
    spatialDashboardApi(proj.v_uri).then((res) => {
      if (cancelled) return
      const payload = res as { ok?: boolean } | null
      if (payload?.ok) {
        setSpatialDashboard(payload)
      }
    }).finally(() => {
      if (!cancelled) setSpatialLoading(false)
    })
    return () => { cancelled = true }
  }, [activeTab, proj?.v_uri, spatialDashboardApi])

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

  const handleGeneratePaymentCertificate = async (period: string) => {
    if (!proj?.v_uri) return
    setPaymentGenerating(true)
    const payload = await generatePaymentCertificateApi({
      project_uri: proj.v_uri,
      period,
      project_name: proj.name,
      create_proof: true,
      enforce_dual_pass: true,
      executor_uri: 'v://executor/system/',
    }) as { ok?: boolean } | null
    if (payload?.ok) {
      setPaymentResult(payload)
      setAuditResult(null)
      showToast(`支付证书已生成：${String((payload as any).payment_id || '-')}`)
    } else {
      showToast('支付证书生成失败')
    }
    setPaymentGenerating(false)
  }

  const handleOpenAuditTrace = async (paymentId: string) => {
    if (!paymentId) return
    setAuditLoading(true)
    const payload = await paymentAuditTraceApi(paymentId) as { ok?: boolean } | null
    if (payload?.ok) {
      setAuditResult(payload)
      showToast(`审计穿透完成：节点 ${(payload as any).nodes?.length || 0}`)
    } else {
      showToast('审计穿透失败')
    }
    setAuditLoading(false)
  }

  const handleGenerateRailPactInstruction = async (paymentId: string) => {
    if (!paymentId) return
    setRailpactSubmitting(true)
    const payload = await generateRailPactInstructionApi({
      payment_id: paymentId,
      executor_uri: 'v://executor/owner/system/',
      auto_submit: false,
    }) as { ok?: boolean; instruction_id?: string } | null
    if (payload?.ok) {
      setRailpactResult(payload)
      showToast(`RailPact 指令已生成：${String(payload.instruction_id || '-')}`)
    } else {
      showToast('RailPact 支付指令生成失败')
    }
    setRailpactSubmitting(false)
  }

  const handleOpenVerifyNode = (proofId: string) => {
    if (!proofId) return
    const base = (window.location?.origin || '').replace(/\/$/, '')
    window.open(`${base}/v/${encodeURIComponent(proofId)}?trace=true`, '_blank', 'noopener,noreferrer')
  }

  const handleFinalizeDelivery = async () => {
    if (!proj?.v_uri) return
    setDeliveryFinalizing(true)
    const pack = await finalizeDocFinalApi({
      project_uri: proj.v_uri,
      project_name: proj.name,
      include_unsettled: false,
      run_anchor_rounds: 1,
    }) as {
      blob: Blob
      filename?: string
      finalGitpegAnchor?: string
      rootHash?: string
    } | null
    if (pack?.blob) {
      const href = URL.createObjectURL(pack.blob)
      const a = document.createElement('a')
      a.href = href
      a.download = pack.filename || 'MASTER-DSP.qcdsp'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(href)
      showToast(`竣工包交付完成，RootHash: ${pack.rootHash || '-'}，FinalAnchor: ${pack.finalGitpegAnchor || 'pending'}`)
    } else {
      showToast('竣工包交付失败')
    }
    setDeliveryFinalizing(false)
  }

  const refreshSpatialDashboard = async () => {
    if (!proj?.v_uri) return
    setSpatialLoading(true)
    const payload = await spatialDashboardApi(proj.v_uri) as { ok?: boolean } | null
    if (payload?.ok) {
      setSpatialDashboard(payload)
    } else {
      showToast('空间孪生看板刷新失败')
    }
    setSpatialLoading(false)
  }

  const handleBindSpatial = async (payload: {
    utxo_id: string
    project_uri: string
    bim_id?: string
    label?: string
    coordinate?: Record<string, unknown>
  }) => {
    if (!payload.utxo_id) return
    const res = await bindSpatialUtxoApi(payload) as { ok?: boolean } | null
    if (res?.ok) {
      showToast('空间指纹绑定成功')
      await refreshSpatialDashboard()
    } else {
      showToast('空间指纹绑定失败')
    }
  }

  const handleRunPredictive = async (payload: {
    nearThresholdRatio: number
    minSamples: number
    applyDynamicGate: boolean
    defaultCriticalThreshold: number
  }) => {
    if (!proj?.v_uri) return
    setAiRunning(true)
    const res = await predictiveQualityAnalysisApi({
      project_uri: proj.v_uri,
      near_threshold_ratio: payload.nearThresholdRatio,
      min_samples: payload.minSamples,
      apply_dynamic_gate: payload.applyDynamicGate,
      default_critical_threshold: payload.defaultCriticalThreshold,
    }) as { ok?: boolean } | null
    if (res?.ok) {
      setAiResult(res)
      showToast(`AI 治理分析完成，预警 ${Number((res as any).warning_count || 0)} 条`)
      await refreshSpatialDashboard()
    } else {
      showToast('AI 治理分析失败')
    }
    setAiRunning(false)
  }

  const handleExportFinanceProof = async (payload: {
    paymentId: string
    bankCode: string
    runAnchorRounds: number
  }) => {
    if (!payload.paymentId) return
    setFinanceExporting(true)
    const pack = await exportFinanceProofApi({
      payment_id: payload.paymentId,
      bank_code: payload.bankCode,
      run_anchor_rounds: payload.runAnchorRounds,
    }) as {
      blob: Blob
      filename?: string
      proofId?: string
      gitpegAnchor?: string
    } | null
    if (pack?.blob) {
      const href = URL.createObjectURL(pack.blob)
      const a = document.createElement('a')
      a.href = href
      a.download = pack.filename || 'FINANCE-PROOF.qcfp'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(href)
      showToast(`金融凭证导出完成，Proof: ${pack.proofId || '-'}，Anchor: ${pack.gitpegAnchor || 'pending'}`)
    } else {
      showToast('金融凭证导出失败')
    }
    setFinanceExporting(false)
  }

  const handleConvertRwaAsset = async (payload: {
    boqGroupId: string
    bankCode: string
    runAnchorRounds: number
  }) => {
    if (!proj?.v_uri || !payload.boqGroupId) return
    setRwaConverting(true)
    const pack = await convertRwaAssetApi({
      project_uri: proj.v_uri,
      boq_group_id: payload.boqGroupId,
      project_name: proj.name,
      bank_code: payload.bankCode,
      run_anchor_rounds: payload.runAnchorRounds,
    }) as {
      blob: Blob
      filename?: string
      proofId?: string
      gitpegAnchor?: string
    } | null
    if (pack?.blob) {
      const href = URL.createObjectURL(pack.blob)
      const a = document.createElement('a')
      a.href = href
      a.download = pack.filename || 'RWA-ASSET.qcrwa'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(href)
      showToast(`RWA 资产转换完成，Proof: ${pack.proofId || '-'}，Anchor: ${pack.gitpegAnchor || 'pending'}`)
    } else {
      showToast('RWA 资产转换失败')
    }
    setRwaConverting(false)
  }

  const handleExportOmBundle = async (payload: {
    omOwnerUri: string
    runAnchorRounds: number
  }) => {
    if (!proj?.v_uri) return
    setOmExporting(true)
    const pack = await exportOmHandoverBundleApi({
      project_uri: proj.v_uri,
      project_name: proj.name,
      om_owner_uri: payload.omOwnerUri,
      run_anchor_rounds: payload.runAnchorRounds,
    }) as {
      blob: Blob
      filename?: string
      omRootProofId?: string
      omGitpegAnchor?: string
      omRootUri?: string
    } | null
    if (pack?.blob) {
      const href = URL.createObjectURL(pack.blob)
      const a = document.createElement('a')
      a.href = href
      a.download = pack.filename || 'OM-HANDOVER.zip'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(href)
      if (pack.omRootProofId) {
        setLastOmRootProofId(pack.omRootProofId)
      }
      showToast(`运维移交包导出完成，OM Root: ${pack.omRootUri || '-'}，Anchor: ${pack.omGitpegAnchor || 'pending'}`)
    } else {
      showToast('运维移交包导出失败')
    }
    setOmExporting(false)
  }

  const handleRegisterOmEvent = async (payload: {
    omRootProofId: string
    title: string
    eventType: string
  }) => {
    if (!payload.omRootProofId || !payload.title) return
    setOmEventSubmitting(true)
    const res = await registerOmEventApi({
      om_root_proof_id: payload.omRootProofId,
      title: payload.title,
      event_type: payload.eventType,
      executor_uri: 'v://operator/om/default',
    }) as { ok?: boolean; event_proof_id?: string } | null
    if (res?.ok) {
      showToast(`运维事件挂载完成：${String(res.event_proof_id || '-')}`)
    } else {
      showToast('运维事件挂载失败')
    }
    setOmEventSubmitting(false)
  }

  const handleGenerateNormEvolution = async (payload: {
    minSamples: number
    nearThresholdRatio: number
    anonymize: boolean
  }) => {
    setNormEvolutionRunning(true)
    const res = await generateNormEvolutionReportApi({
      project_uris: proj?.v_uri ? [proj.v_uri] : [],
      min_samples: payload.minSamples,
      near_threshold_ratio: payload.nearThresholdRatio,
      anonymize: payload.anonymize,
      create_proof: true,
    }) as { ok?: boolean } | null
    if (res?.ok) {
      setNormEvolutionResult(res)
      showToast(`规范演进报告生成完成，发现 ${Number((res as any).report?.finding_count || 0)} 条`)
    } else {
      showToast('规范演进报告生成失败')
    }
    setNormEvolutionRunning(false)
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

  const pullErpProjectBinding = async () => {
    await pullErpProjectBindingFlow({
      settings,
      canUseEnterpriseApi,
      enterpriseId: enterprise?.id || undefined,
      regForm,
      setRegForm,
      setErpBindingLoading,
      setErpBinding,
      getErpProjectBasicsApi,
      showToast,
    })
  }

  const handleResetRegister = () => {
    resetRegister()
    setPermTemplate('standard')
  }

  const submitRegister = async () => {
    await submitRegisterFlow({
      regForm,
      settings,
      canUseEnterpriseApi,
      enterpriseId: enterprise?.id || undefined,
      erpBinding,
      projects,
      regUri,
      setVpathStatus,
      zeroPersonnel,
      zeroEquipment,
      zeroSubcontracts,
      zeroMaterials,
      buildExecutorUri,
      buildToolUri,
      buildSubcontractUri,
      getEquipmentValidity,
      createProjectApi,
      listProjectsApi,
      setProjects,
      addProject,
      setCurrentProject,
      setProjectMeta,
      setRegisterSuccess,
      segType,
      regKmInterval,
      regInspectionTypes,
      contractSegs,
      structures,
      permTemplate,
      memberCount: members.length,
      localEnterpriseId: proj.enterprise_id,
      showToast,
    })
  }

  const addMember = async () => {
    await addMemberFlow({
      inviteForm,
      projects,
      fallbackProjectId: proj.id,
      canUseEnterpriseApi,
      enterpriseId: enterprise?.id || undefined,
      inviteMember,
      listMembers,
      setMembers,
      setMemberRoleDrafts,
      setInviteForm,
      setInviteOpen,
      showToast,
    })
  }

  const removeMember = async (id: string) => {
    await removeMemberFlow({
      memberId: id,
      canUseEnterpriseApi,
      removeMemberApi,
      setMembers,
      setMemberRoleDrafts,
      showToast,
    })
  }

  const saveMemberRole = async (member: TeamMember) => {
    await saveMemberRoleFlow({
      member,
      memberRoleDrafts,
      canUseEnterpriseApi,
      updateMemberApi,
      setMembers,
      showToast,
    })
  }

  const removeProject = async (projectId: string, projectName: string) => {
    const confirmed = typeof window === 'undefined' ? true : window.confirm(`确认删除项目「${projectName}」？`)
    if (!confirmed) return

    await removeProjectFlow({
      projectId,
      canUseEnterpriseApi,
      enterpriseId: enterprise?.id || undefined,
      projects,
      currentProject,
      removeProjectApi,
      listProjectsApi,
      setProjects,
      setCurrentProject,
      setProjectMeta,
      showToast,
    })
  }

  const retryProjectAutoreg = async (projectId: string, projectName: string) => {
    await retryProjectAutoregFlow({
      projectId,
      projectName,
      canUseEnterpriseApi,
      enterpriseId: enterprise?.id || undefined,
      enterpriseVUri: enterprise?.v_uri,
      settingsGitpegEnabled: settings.gitpegEnabled,
      projects,
      syncAutoregApi,
      registerAutoregProjectApi,
      registerAutoregProjectAliasApi,
      listAutoregProjectsApi,
      setAutoregRows,
      setSyncingProjectId,
      showToast,
    })
  }

  const directProjectAutoreg = async (projectId: string, projectName: string) => {
    await directProjectAutoregFlow({
      projectId,
      projectName,
      canUseEnterpriseApi,
      enterpriseVUri: enterprise?.v_uri,
      settingsGitpegEnabled: settings.gitpegEnabled,
      projects,
      registerAutoregProjectApi,
      registerAutoregProjectAliasApi,
      listAutoregProjectsApi,
      setAutoregRows,
      setSyncingProjectId,
      showToast,
    })
  }

  const updatePermissionCell = (role: PermissionRole, key: PermissionKey, value: boolean) => {
    updatePermissionCellFlow(role, key, value, setPermissionMatrix, setPermissionTemplate)
  }

  const applyPermissionTemplate = (template: Exclude<PermTemplate, 'custom'>) => {
    applyPermissionTemplateFlow(template, setPermissionTemplate, setPermissionMatrix)
  }

  const persistPermissionMatrix = async () => {
    await persistPermissionMatrixFlow({
      canUseEnterpriseApi,
      enterpriseId: enterprise?.id || undefined,
      permissionMatrix,
      saveSettings,
      setPermissionMatrix,
      setPermissionTemplate,
      showToast,
    })
  }

  const doDemoLogin = (key: keyof typeof QUICK_USERS = 'admin') => {
    doDemoLoginFlow({
      key,
      hasProjects: projects.length > 0,
      setUser,
      setProjects,
      setCurrentProject,
      setAppReady,
      showToast,
    })
  }

  const fillQuickLogin = (key: keyof typeof QUICK_USERS) => {
    fillQuickLoginFlow({
      key,
      setLoginForm,
      showToast,
    })
  }

  const quickLoginNow = (key: keyof typeof QUICK_USERS) => {
    fillQuickLogin(key)
    doDemoLogin(key)
  }

  const doLogin = async () => {
    await doLoginFlow({
      loginForm,
      loginApi,
      getEnterpriseApi,
      setUser,
      setProjects,
      setCurrentProject,
      setAppReady,
      setLoggingIn,
      showToast,
    })
  }

  const doLogout = async () => {
    await doLogoutFlow({
      logoutApi,
      logout,
      setAppReady,
      setLoginTab,
      setLoginForm,
      showToast,
    })
  }

  const doRegisterEnterprise = async () => {
    await doRegisterEnterpriseFlow({
      entForm,
      registerEnterpriseApi,
      setLoginForm,
      setEntForm,
      setLoginTab,
      showToast,
    })
  }

  const quickLoginOptions = getQuickLoginOptions()

  if (sessionChecking || !appReady) {
    return (
      <AuthEntry
        sessionChecking={sessionChecking}
        loginTab={loginTab}
        loginForm={loginForm}
        loggingIn={loggingIn}
        entForm={entForm}
        quickLoginOptions={quickLoginOptions}
        onSwitchTab={setLoginTab}
        onLoginFormChange={setLoginForm}
        onEnterpriseFormChange={setEntForm}
        onLogin={doLogin}
        onRegisterEnterprise={doRegisterEnterprise}
        onFillQuickLogin={(key) => fillQuickLogin(key as keyof typeof QUICK_USERS)}
        onQuickLoginNow={(key) => quickLoginNow(key as keyof typeof QUICK_USERS)}
      />
    )
  }

  return (
    <>
      <AppShellLayout
        sidebarOpen={sidebarOpen}
        activeTab={activeTab}
        navItems={NAV}
        navSections={NAV_SECTIONS}
        projects={projects}
        currentProjectId={proj.id}
        currentUserName={user?.name || DEMO_USER.name}
        currentUserTitle={user?.title || '超级管理员'}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onNavigate={setActiveTab}
        onSelectProject={(projectId) => {
          const selected = projects.find((p) => p.id === projectId)
          if (selected) setCurrentProject(selected)
        }}
        onLogout={doLogout}
      >
        {activeTab === 'dashboard' && <Dashboard />}

        {activeTab === 'inspection' && <InspectionPage />}

        {activeTab === 'photos' && <PhotosPage />}

        {activeTab === 'reports' && <ReportsPage />}

        {activeTab === 'proof' && (
          <>
            <ProofPanel
              projectUri={proj.v_uri}
              proofStats={proofStats}
              proofNodeRows={proofNodeRows}
              proofLoading={proofLoading}
              proofRows={proofRows}
              proofVerifying={proofVerifying}
              onVerifyProof={handleVerifyProof}
            />
            <PaymentAuditPanel
              projectUri={proj.v_uri}
              paymentGenerating={paymentGenerating}
              paymentResult={paymentResult}
              railpactSubmitting={railpactSubmitting}
              railpactResult={railpactResult}
              auditLoading={auditLoading}
              auditResult={auditResult}
              frequencyLoading={frequencyLoading}
              frequencyResult={frequencyResult}
              deliveryFinalizing={deliveryFinalizing}
              onGeneratePaymentCertificate={handleGeneratePaymentCertificate}
              onGenerateRailPactInstruction={handleGenerateRailPactInstruction}
              onOpenAuditTrace={handleOpenAuditTrace}
              onFinalizeDelivery={handleFinalizeDelivery}
              onOpenVerifyNode={handleOpenVerifyNode}
            />
            <SpatialGovernancePanel
              projectUri={proj.v_uri}
              spatialLoading={spatialLoading}
              spatialDashboard={spatialDashboard}
              aiRunning={aiRunning}
              aiResult={aiResult}
              financeExporting={financeExporting}
              defaultPaymentId={String(paymentResult?.payment_id || '')}
              onRefreshSpatial={refreshSpatialDashboard}
              onBindSpatial={handleBindSpatial}
              onRunPredictive={handleRunPredictive}
              onExportFinanceProof={handleExportFinanceProof}
              onOpenVerifyNode={handleOpenVerifyNode}
            />
            <RwaOmEvolutionPanel
              projectUri={proj.v_uri}
              rwaConverting={rwaConverting}
              omExporting={omExporting}
              omEventSubmitting={omEventSubmitting}
              normRunning={normEvolutionRunning}
              normResult={normEvolutionResult}
              lastPaymentId={String(paymentResult?.payment_id || '')}
              lastOmRootProofId={lastOmRootProofId}
              onConvertRwa={handleConvertRwaAsset}
              onExportOmBundle={handleExportOmBundle}
              onRegisterOmEvent={handleRegisterOmEvent}
              onGenerateNormEvolution={handleGenerateNormEvolution}
            />
            <DocumentGovernancePanel projectUri={proj.v_uri} />
          </>
        )}

          {activeTab === 'projects' && (
            <ProjectsPanel
              searchText={searchText}
              statusFilter={statusFilter}
              typeFilter={typeFilter}
              projectTypeOptions={PROJECT_TYPE_OPTIONS}
              filteredProjects={filteredProjects}
              projectMeta={projectMeta}
              typeIcon={TYPE_ICON}
              typeLabel={TYPE_LABEL}
              canUseEnterpriseApi={canUseEnterpriseApi}
              syncingProjectId={syncingProjectId}
              autoregRows={autoregRows}
              onSearchTextChange={setSearchText}
              onStatusFilterChange={setStatusFilter}
              onTypeFilterChange={setTypeFilter}
              onEnterInspection={(project) => {
                setCurrentProject(project)
                setActiveTab('inspection')
              }}
              onRetryAutoreg={retryProjectAutoreg}
              onDirectAutoreg={directProjectAutoreg}
              onEditProject={(projectId) => openProjectDetail(projectId, true)}
              onOpenProjectDetail={(projectId) => openProjectDetail(projectId)}
              onDeleteProject={removeProject}
              onRefreshAutoreg={async () => {
                const latest = await listAutoregProjectsApi(20) as { items?: typeof autoregRows } | null
                if (latest?.items) setAutoregRows(latest.items)
              }}
            />
          )}

          {activeTab === 'register' && (
            <RegisterPanelFrame
              projects={projects}
              registerSegCount={registerSegCount}
              registerRecordCount={registerRecordCount}
              registerStep={registerStep}
              registerSuccess={registerSuccess}
              registerPreviewProjects={registerPreviewProjects}
              typeIcon={TYPE_ICON}
              typeLabel={TYPE_LABEL}
              onStepClick={setRegisterStep}
              onStartInspectionFromSuccess={() => {
                const created = projects.find((p) => p.id === registerSuccess?.id)
                if (created) setCurrentProject(created)
                setActiveTab('inspection')
              }}
              onGoProjects={() => setActiveTab('projects')}
              onResetRegister={handleResetRegister}
              onOpenProjectDetail={openProjectDetail}
              onEnterInspection={(project) => {
                setCurrentProject(project)
                setActiveTab('inspection')
              }}
            >
              <>
                  {registerStep === 1 && (
                    <RegisterStepOne
                      regForm={regForm}
                      setRegForm={setRegForm}
                      projectTypeOptions={PROJECT_TYPE_OPTIONS}
                      settings={settings}
                      setErpBinding={setErpBinding}
                      pullErpProjectBinding={pullErpProjectBinding}
                      erpBindingLoading={erpBindingLoading}
                      erpBinding={erpBinding}
                      regUri={regUri}
                      vpathStatus={vpathStatus}
                    />
                  )}

                  {registerStep === 2 && (
                    <RegisterStepTwo
                      regForm={regForm}
                      setRegForm={setRegForm}
                      segType={segType}
                      setSegType={setSegType}
                      regKmInterval={regKmInterval}
                      setRegKmInterval={setRegKmInterval}
                      contractSegs={contractSegs}
                      setContractSegs={setContractSegs}
                      addContractSeg={addContractSeg}
                      structures={structures}
                      setStructures={setStructures}
                      addStructure={addStructure}
                      inspectionTypeOptions={INSPECTION_TYPE_OPTIONS}
                      regInspectionTypes={regInspectionTypes}
                      setRegInspectionTypes={setRegInspectionTypes}
                      toggleInspectionType={toggleInspectionType}
                      regUri={regUri}
                      vpathStatus={vpathStatus}
                      regRangeTreeLines={regRangeTreeLines}
                    />
                  )}

                  {registerStep === 3 && (
                    <RegisterStepThree
                      zeroLedgerTab={zeroLedgerTab}
                      setZeroLedgerTab={setZeroLedgerTab}
                      zeroPersonnel={zeroPersonnel}
                      setZeroPersonnel={setZeroPersonnel}
                      zeroEquipment={zeroEquipment}
                      setZeroEquipment={setZeroEquipment}
                      zeroSubcontracts={zeroSubcontracts}
                      setZeroSubcontracts={setZeroSubcontracts}
                      zeroMaterials={zeroMaterials}
                      setZeroMaterials={setZeroMaterials}
                      makeRowId={makeRowId}
                      buildExecutorUri={buildExecutorUri}
                      buildToolUri={buildToolUri}
                      buildSubcontractUri={buildSubcontractUri}
                      getEquipmentValidity={getEquipmentValidity}
                      regUri={regUri}
                      zeroLedgerTreeRows={zeroLedgerTreeRows}
                    />
                  )}

                  {registerStep === 4 && (
                    <RegisterStepConfirm
                      regForm={regForm}
                      typeLabel={TYPE_LABEL}
                      segType={segType}
                      regKmInterval={regKmInterval}
                      regInspectionTypes={regInspectionTypes}
                      inspectionTypeLabel={INSPECTION_TYPE_LABEL}
                      regUri={regUri}
                      zeroLedgerSummary={zeroLedgerSummary}
                    />
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
            </RegisterPanelFrame>
          )}

          {activeTab === 'team' && (
            <TeamPanel
              members={members}
              memberRoleDrafts={memberRoleDrafts}
              onOpenInvite={() => setInviteOpen(true)}
              onDraftRoleChange={(memberId, role) => setMemberRoleDrafts((prev) => ({ ...prev, [memberId]: role }))}
              onSaveMemberRole={saveMemberRole}
              onRemoveMember={removeMember}
            />
          )}

          {activeTab === 'permissions' && (
            <PermissionsPanel
              permissionTemplate={permissionTemplate}
              permissionMatrix={permissionMatrix}
              permissionColumns={PERMISSION_COLUMNS}
              permissionRoleLabel={PERMISSION_ROLE_LABEL}
              permissionTreeRoot={permissionTreeRoot}
              permissionTreeRows={permissionTreeRows}
              onApplyTemplate={applyPermissionTemplate}
              onUpdateCell={updatePermissionCell}
              onSaveMatrix={persistPermissionMatrix}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsPanel
              enterpriseInfo={enterpriseInfo}
              setEnterpriseInfo={setEnterpriseInfo}
              persistEnterpriseInfo={persistEnterpriseInfo}
              settings={settings}
              setSettings={setSettings}
              persistSettings={persistSettings}
              setReportTemplateFile={setReportTemplateFile}
              persistReportTemplate={persistReportTemplate}
              verifyGitpegToken={verifyGitpegToken}
              gitpegVerifying={gitpegVerifying}
              gitpegVerifyMsg={gitpegVerifyMsg}
              setGitpegVerifyMsg={setGitpegVerifyMsg}
              setGitpegVerifying={setGitpegVerifying}
              erpDraft={erpDraft}
              setErpDraft={setErpDraft}
              testErpConnection={testErpConnection}
              erpTesting={erpTesting}
              erpTestMsg={erpTestMsg}
              erpWritebackDraft={erpWritebackDraft}
              setErpWritebackDraft={setErpWritebackDraft}
              testWebhook={testWebhook}
              webhookTesting={webhookTesting}
              webhookResult={webhookResult}
            />
          )}

          <InviteMemberModal
            open={inviteOpen}
            form={inviteForm}
            projects={projects}
            onChange={setInviteForm}
            onClose={() => setInviteOpen(false)}
            onSubmit={addMember}
          />

          <ProjectDetailDrawer
            open={projectDetailOpen}
            detailProject={detailProject}
            detailEdit={detailEdit}
            detailProjectDraft={detailProjectDraft}
            detailMeta={detailMeta}
            detailDraft={detailDraft}
            projectTypeOptions={PROJECT_TYPE_OPTIONS}
            inspectionTypeOptions={INSPECTION_TYPE_OPTIONS}
            inspectionTypeLabel={INSPECTION_TYPE_LABEL}
            typeLabel={TYPE_LABEL}
            onClose={closeProjectDetail}
            onStartEdit={startEditDetail}
            onSave={saveDetailMeta}
            onCancelEdit={cancelDetailEdit}
            onDetailProjectDraftChange={setDetailProjectDraft}
            onDetailDraftChange={setDetailDraft}
            normalizeKmInterval={normalizeKmInterval}
            toggleInspectionType={toggleInspectionType}
            boqRealtime={detailProject ? boqRealtimeByProjectId[detailProject.id] || null : null}
            boqRealtimeLoading={boqRealtimeLoadingProjectId === detailProject?.id}
            boqAudit={detailProject ? boqAuditByProjectId[detailProject.id] || null : null}
            boqAuditLoading={boqAuditLoadingProjectId === detailProject?.id}
            boqProofPreview={boqProofPreview}
            boqProofLoadingUri={boqProofLoadingUri || undefined}
            boqSovereignPreview={boqSovereignPreview}
            boqSovereignLoadingCode={boqSovereignLoadingCode || undefined}
            onOpenBoqProofChain={handleOpenBoqProofChain}
            onOpenBoqSovereignHistory={handleOpenBoqSovereignHistory}
          />
      </AppShellLayout>

      <Toast message={toastMsg} />
    </>
  )
}

