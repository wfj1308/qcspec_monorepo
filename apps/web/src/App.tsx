import { useEffect, useState } from 'react'
import { useUIStore, useProjectStore, useAuthStore } from './store'
import { Toast } from './components/ui'
import { useAuthApi, useProof, useProjects } from './hooks/api'
import { useSettings } from './hooks/api/settings'
import { useTeam } from './hooks/api/team'
import AppShellLayout from './components/layout/AppShellLayout'
import AuthEntry from './components/auth/AuthEntry'
import AppWorkspaceContent from './app/AppWorkspaceContent'
import { useProjectDetailController } from './app/useProjectDetailController'
import { doLoginFlow, doLogoutFlow } from './app/authFlows'
import { useGitpegCallbackSync } from './app/useGitpegCallbackSync'
import { useProjectMetaSync } from './app/useProjectMetaSync'
import { useAuthSessionController } from './app/useAuthSessionController'
import { useProofDashboardController } from './app/useProofDashboardController'
import { useProjectCatalogController } from './app/useProjectCatalogController'
import { useTeamAccessController } from './app/useTeamAccessController'
import { useSettingsController } from './app/useSettingsController'
import { useTeamSettingsBootstrap } from './app/useTeamSettingsBootstrap'
import { useAppWorkspaceProps } from './app/useAppWorkspaceProps'
import {
  buildProjectsWorkspace,
} from './app/workspaceBuilders'


import {
  NAV,
  NAV_SECTIONS,
  InspectionTypeKey,
  ProjectRegisterMeta,
  TYPE_LABEL,
  TYPE_ICON,
  PROJECT_TYPE_OPTIONS,
  INSPECTION_TYPE_OPTIONS,
  INSPECTION_TYPE_LABEL,
  PERMISSION_COLUMNS,
  PERMISSION_ROLE_LABEL,
  getAllowedNavKeysByRole,
  normalizeKmInterval,
  resolveAllowedTab,
} from './app/appShellShared'

const CLEAN_START_MIGRATION_KEY = 'qcspec.clean.start.20260410'
const DOCPEG_ONLY_MODE = String(import.meta.env.VITE_DOCPEG_ONLY_MODE || 'true').trim() !== 'false'
const DOCPEG_ONLY_ALLOWED_TABS = ['projects', 'inspection', 'reports', 'proof', 'team', 'permissions', 'settings'] as const
const DOCPEG_DEFAULT_ENTERPRISE_ID = String(import.meta.env.VITE_DOCPEG_ENTERPRISE_ID || 'DOCPEG-ENTERPRISE').trim() || 'DOCPEG-ENTERPRISE'
const DOCPEG_DEFAULT_ENTERPRISE_NAME = String(import.meta.env.VITE_DOCPEG_ENTERPRISE_NAME || 'DocPeg 联调环境').trim() || 'DocPeg 联调环境'
const DOCPEG_DEFAULT_ENTERPRISE_V_URI = String(import.meta.env.VITE_DOCPEG_ENTERPRISE_V_URI || 'v://cn.docpeg/enterprise/default/').trim() || 'v://cn.docpeg/enterprise/default/'
const DOCPEG_DEFAULT_USER_ID = String(import.meta.env.VITE_DOCPEG_USER_ID || 'docpeg-user').trim() || 'docpeg-user'
const DOCPEG_DEFAULT_USER_NAME = String(import.meta.env.VITE_DOCPEG_USER_NAME || 'DocPeg 操作员').trim() || 'DocPeg 操作员'
const DOCPEG_DEFAULT_DTO_ROLE = String(import.meta.env.VITE_DOCPEG_DTO_ROLE || 'OWNER').trim().toUpperCase() as 'PUBLIC' | 'MARKET' | 'AI' | 'SUPERVISOR' | 'OWNER' | 'REGULATOR'

export default function App() {
  const { activeTab, setActiveTab, toastMsg, sidebarOpen, setSidebarOpen, showToast } = useUIStore()
  const { projects, setProjects, currentProject, setCurrentProject } = useProjectStore()
  const { setUser, logout, enterprise, user, token } = useAuthStore()
  const {
    list: listProjectsApi,
    create: createProjectApi,
    getById: getProjectByIdApi,
    update: updateProjectApi,
    remove: removeProjectApi,
    completeGitpeg: completeGitpegApi,
  } = useProjects()
  const {
    login: loginApi,
    me: meApi,
    getEnterprise: getEnterpriseApi,
    logout: logoutApi,
  } = useAuthApi()
  const {
    getSettings,
    saveSettings,
    testErpnext,
    testGitpegRegistrar,
    uploadTemplate,
  } = useSettings()
  const {
    listMembers,
    inviteMember,
    updateMember,
    removeMember,
  } = useTeam()

  const {
    appReady,
    setAppReady,
    sessionChecking,
    loginForm,
    setLoginForm,
    loggingIn,
    setLoggingIn,
  } = useAuthSessionController({
    token,
    user,
    enterprise,
    meApi,
    getEnterpriseApi,
    setUser,
    setProjects,
    setCurrentProject,
    skipAuthBootstrap: DOCPEG_ONLY_MODE,
  })

  useEffect(() => {
    if (!DOCPEG_ONLY_MODE) return
    if (user?.id && enterprise?.id) return

    setUser(
      {
        id: DOCPEG_DEFAULT_USER_ID,
        enterprise_id: DOCPEG_DEFAULT_ENTERPRISE_ID,
        v_uri: `${DOCPEG_DEFAULT_ENTERPRISE_V_URI}user/${DOCPEG_DEFAULT_USER_ID}/`,
        name: DOCPEG_DEFAULT_USER_NAME,
        dto_role: DOCPEG_DEFAULT_DTO_ROLE,
      },
      {
        id: DOCPEG_DEFAULT_ENTERPRISE_ID,
        name: DOCPEG_DEFAULT_ENTERPRISE_NAME,
        v_uri: DOCPEG_DEFAULT_ENTERPRISE_V_URI,
        plan: 'enterprise',
        proof_quota: 0,
        proof_used: 0,
      },
      token || '',
    )
  }, [enterprise?.id, setUser, token, user?.id])

  const [projectMeta, setProjectMeta] = useState<Record<string, ProjectRegisterMeta>>({})
  const [, setRegisterSuccess] = useState<{ id: string; name: string; uri: string } | null>(null)
  const {
    listProofs,
    verify: verifyProof,
    stats: proofStatsApi,
    nodeTree: proofNodeTreeApi,
    boqRealtimeStatus: boqRealtimeStatusApi,
    boqItemSovereignHistory: boqItemSovereignHistoryApi,
    boqReconciliation: boqReconciliationApi,
    docFinalContext: docFinalContextApi,
  } = useProof()
  const [gitpegCallbackHandled, setGitpegCallbackHandled] = useState(false)
  const effectiveEnterpriseId = enterprise?.id || DOCPEG_DEFAULT_ENTERPRISE_ID
  const canUseDocpegProjectApi = DOCPEG_ONLY_MODE ? true : !!enterprise?.id
  const canUseLegacyEnterpriseApi = DOCPEG_ONLY_MODE ? false : !!enterprise?.id
  const proj = currentProject || projects[0] || { id: '', name: '', v_uri: '' }

  const normalizeNodeSegment = (value: string, fallback = 'pending') =>
    String(value || '').trim().replace(/[\\/]/g, '-').replace(/\s+/g, '') || fallback
  const normalizeCodeSegment = (value: string) =>
    String(value || '').trim().replace(/[^\w\u4e00-\u9fa5-]/g, '').replace(/\s+/g, '')
  const enterpriseNodeRoot = String(enterprise?.v_uri || '').trim().replace(/\/+$/, '')
  const fallbackNodeRoot = enterpriseNodeRoot || 'v://cn/enterprise'
  const buildExecutorUri = (name: string) => `${fallbackNodeRoot}/executor/${normalizeNodeSegment(name)}/`
  const buildToolNodeName = (name: string, modelNo: string) => {
    const safeName = normalizeNodeSegment(name, 'tool')
    const safeModel = normalizeCodeSegment(modelNo)
    return safeModel ? `${safeName}-${safeModel}` : safeName
  }
  const buildToolUri = (name: string, modelNo: string) => `${fallbackNodeRoot}/tools/${buildToolNodeName(name, modelNo)}/`
  const buildSubcontractUri = (unitName: string) => `${fallbackNodeRoot}/subcontract/${normalizeNodeSegment(unitName, 'unit')}/`
  const getEquipmentValidity = (validUntil: string) => {
    if (!validUntil) return { label: '待填', color: '#64748B', bg: '#F1F5F9', ok: false }
    const now = new Date()
    const target = new Date(`${validUntil}T23:59:59`)
    const days = Math.floor((target.getTime() - now.getTime()) / 86400000)
    if (days < 0) return { label: '已过期', color: '#DC2626', bg: '#FEE2E2', ok: false }
    if (days < 90) return { label: `${days}天内到期`, color: '#D97706', bg: '#FEF3C7', ok: false }
    return { label: '有效', color: '#059669', bg: '#ECFDF5', ok: true }
  }
  const toggleInspectionType = (
    key: InspectionTypeKey,
    current: InspectionTypeKey[],
    setter: (next: InspectionTypeKey[]) => void
  ) => {
    const exists = current.includes(key)
    if (exists) {
      if (current.length === 1) {
        showToast('至少保留一个检测类型')
        return
      }
      setter(current.filter((item) => item !== key))
      return
    }
    setter([...current, key])
  }

  const projectDetailController = useProjectDetailController({
    projects,
    setProjects,
    currentProject,
    setCurrentProject,
    projectMeta,
    setProjectMeta,
    canUseEnterpriseApi: canUseLegacyEnterpriseApi,
    enterpriseId: canUseLegacyEnterpriseApi ? effectiveEnterpriseId : undefined,
    memberCount: 0,
    getProjectByIdApi,
    updateProjectApi,
    normalizeKmInterval,
    buildExecutorUri,
    buildToolUri,
    buildSubcontractUri,
    getEquipmentValidity,
    showToast,
  })
  const proofDashboard = useProofDashboardController({
    activeTab,
    proj,
    projectDetailOpen: projectDetailController.projectDetailOpen,
    detailProject: projectDetailController.detailProject,
    showToast,
    listProofs,
    verifyProof: DOCPEG_ONLY_MODE ? (async () => null) : verifyProof,
    proofStatsApi: DOCPEG_ONLY_MODE ? (async () => null) : proofStatsApi,
    proofNodeTreeApi: DOCPEG_ONLY_MODE ? (async () => null) : proofNodeTreeApi,
    boqRealtimeStatusApi: DOCPEG_ONLY_MODE ? (async () => null) : boqRealtimeStatusApi,
    boqItemSovereignHistoryApi: DOCPEG_ONLY_MODE ? (async () => null) : boqItemSovereignHistoryApi,
    boqReconciliationApi: DOCPEG_ONLY_MODE ? (async () => null) : boqReconciliationApi,
    docFinalContextApi: DOCPEG_ONLY_MODE ? (async () => null) : docFinalContextApi,
  })
  const projectCatalog = useProjectCatalogController({
    appReady,
    canUseEnterpriseApi: canUseDocpegProjectApi,
    enterpriseId: effectiveEnterpriseId,
    projects,
    currentProject,
    listProjectsApi,
    createProjectApi,
    removeProjectApi,
    setProjects,
    setCurrentProject,
    setProjectMeta,
    showToast,
  })
  const settingsController = useSettingsController({
    canUseEnterpriseApi: canUseLegacyEnterpriseApi,
    enterpriseId: canUseLegacyEnterpriseApi ? effectiveEnterpriseId : undefined,
    initialReportHeader: `${enterprise?.name || DOCPEG_DEFAULT_ENTERPRISE_NAME} 质检报告`,
    initialEnterpriseInfo: {
      name: enterprise?.name || DOCPEG_DEFAULT_ENTERPRISE_NAME,
      vUri: enterprise?.v_uri || DOCPEG_DEFAULT_ENTERPRISE_V_URI,
      creditCode: '',
      adminEmail: user?.email || '',
    },
    saveSettings,
    uploadTemplate,
    testGitpegRegistrar,
    testErpnext,
    showToast,
  })
  const teamAccessController = useTeamAccessController({
    canUseEnterpriseApi: canUseLegacyEnterpriseApi,
    enterpriseId: canUseLegacyEnterpriseApi ? effectiveEnterpriseId : undefined,
    projects,
    currentProjectId: currentProject?.id || projects[0]?.id || '',
    saveSettings,
    inviteMember,
    listMembers,
    updateMemberApi: updateMember,
    removeMemberApi: removeMember,
    showToast,
  })

  useTeamSettingsBootstrap({
    appReady,
    activeTab,
    canUseEnterpriseApi: canUseLegacyEnterpriseApi,
    enterpriseId: canUseLegacyEnterpriseApi ? effectiveEnterpriseId : undefined,
    listMembers,
    getSettings,
    setMembers: teamAccessController.setMembers,
    setMemberRoleDrafts: teamAccessController.setMemberRoleDrafts,
    setSettings: settingsController.setSettings,
    setErpDraft: settingsController.setErpDraft,
    setErpWritebackDraft: settingsController.setErpWritebackDraft,
    setPermissionMatrix: teamAccessController.setPermissionMatrix,
    setPermissionTemplate: teamAccessController.setPermissionTemplate,
    setEnterpriseInfo: settingsController.setEnterpriseInfo,
  })

  const roleAllowedNavKeys = getAllowedNavKeysByRole(user?.dto_role)
  const docpegAllowedNavKeys = DOCPEG_ONLY_ALLOWED_TABS.filter((key) => roleAllowedNavKeys.includes(key))
  const globalAllowedNavKeys = DOCPEG_ONLY_MODE
    ? (docpegAllowedNavKeys.length ? [...docpegAllowedNavKeys] : [...DOCPEG_ONLY_ALLOWED_TABS])
    : roleAllowedNavKeys
  const roleAwareNavItems = NAV.filter((item) => globalAllowedNavKeys.includes(item.key))
  const roleAwareNavSections = NAV_SECTIONS
    .map((section) => ({ ...section, keys: section.keys.filter((key) => globalAllowedNavKeys.includes(key)) }))
    .filter((section) => section.keys.length > 0)
  const defaultTab = roleAwareNavItems[0]?.key || 'dashboard'
  const navigateToAllowedTab = (nextTab: string) => {
    setActiveTab(resolveAllowedTab(nextTab, globalAllowedNavKeys, defaultTab))
  }

  useEffect(() => {
    const match = (window.location.pathname || '').match(/^\/project\/([^/]+)\/(contractor|supervisor|auditor)\/workbench\/?$/)
    if (!match) return
    const projectId = decodeURIComponent(match[1] || '')
    if (!projectId) return
    if (projectDetailController.projectDetailOpen && projectDetailController.detailProject?.id === projectId) return
    if (!projects.some((item) => item.id === projectId)) return
    void projectDetailController.openProjectDetail(projectId, false)
  }, [projectDetailController, projects])

  useEffect(() => {
    const nextTab = resolveAllowedTab(activeTab, globalAllowedNavKeys, defaultTab)
    if (nextTab !== activeTab) setActiveTab(nextTab)
  }, [activeTab, defaultTab, globalAllowedNavKeys, setActiveTab])

  useGitpegCallbackSync({
    gitpegCallbackHandled,
    setGitpegCallbackHandled,
    appReady,
    canUseEnterpriseApi: canUseLegacyEnterpriseApi,
    enterpriseId: canUseLegacyEnterpriseApi ? effectiveEnterpriseId : undefined,
    completeGitpegApi,
    listProjectsApi,
    setProjects,
    setCurrentProject,
    setRegisterSuccess,
    showToast,
  })

  useProjectMetaSync({
    projects,
    memberCount: 0,
    setProjectMeta,
  })

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
      setLoginForm,
      showToast,
    })
  }

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (localStorage.getItem(CLEAN_START_MIGRATION_KEY) === '1') return

    try {
      localStorage.removeItem('qcspec-auth')
      Object.keys(localStorage)
        .filter((key) => key.startsWith('qcspec.docpeg.inspection.linkage.'))
        .forEach((key) => localStorage.removeItem(key))
      localStorage.setItem(CLEAN_START_MIGRATION_KEY, '1')
    } catch {
      // ignore storage failures
    }

    setProjects([])
    setCurrentProject(null)
    if (DOCPEG_ONLY_MODE) {
      showToast('已清理历史本地缓存，当前使用 DocPeg API 联调模式')
      return
    }

    logout()
    setAppReady(false)
    showToast('已清理历史本地数据，请使用真实账号重新登录')
  }, [logout, setAppReady, setCurrentProject, setProjects, showToast])

  const openProjectWorkbench = (
    targetProject?: typeof projects[number],
    targetTab: 'projects' | 'inspection' | 'proof' = 'projects',
  ) => {
    const selected = targetProject || currentProject || projects[0]
    if (!selected) {
      showToast('请先在上游系统完成项目创建并同步到 QCSpec')
      navigateToAllowedTab('projects')
      return
    }
    setCurrentProject(selected)
    navigateToAllowedTab(targetTab)
    if (targetTab === 'projects') {
      void projectDetailController.openProjectDetail(selected.id, false)
    }
  }

  const permissionTreeRoot = `${String(
    settingsController.enterpriseInfo.vUri || enterprise?.v_uri || DOCPEG_DEFAULT_ENTERPRISE_V_URI,
  ).replace(/\/+$/, '')}/dtorole/`

  const workspaceContentProps = useAppWorkspaceProps({
    activeTab,
    projectsWorkspace: buildProjectsWorkspace({
      projectMeta,
      projectCatalog,
      projectDetailController,
      proofDashboard,
      projectTypeOptions: PROJECT_TYPE_OPTIONS,
      inspectionTypeOptions: INSPECTION_TYPE_OPTIONS,
      inspectionTypeLabel: INSPECTION_TYPE_LABEL,
      typeIcon: TYPE_ICON,
      typeLabel: TYPE_LABEL,
      sidebarOpen,
      normalizeKmInterval,
      toggleInspectionType,
      onEnterInspection: (project) => openProjectWorkbench(project, 'inspection'),
      onEnterProof: (project) => openProjectWorkbench(project, 'proof'),
    }),
    proofWorkspace: {
      proofPanelProps: {
        projectUri: proofDashboard.projectUri,
        proofStats: proofDashboard.proofStats,
        proofNodeRows: proofDashboard.proofNodeRows,
        proofLoading: proofDashboard.proofLoading,
        proofRows: proofDashboard.proofRows,
        proofVerifying: proofDashboard.proofVerifying,
        onVerifyProof: proofDashboard.handleVerifyProof,
        onGoInspection: () => openProjectWorkbench(undefined, 'inspection'),
        onGoReports: () => navigateToAllowedTab('reports'),
      },
    },
    teamWorkspace: {
      teamPanelProps: {
        members: teamAccessController.members,
        memberRoleDrafts: teamAccessController.memberRoleDrafts,
        onOpenInvite: teamAccessController.openInvite,
        onDraftRoleChange: teamAccessController.updateMemberRoleDraft,
        onSaveMemberRole: teamAccessController.saveMemberRole,
        onRemoveMember: teamAccessController.removeMember,
      },
      inviteMemberModalProps: {
        open: teamAccessController.inviteOpen,
        form: teamAccessController.inviteForm,
        projects: projects.map((project) => ({ id: project.id, name: project.name })),
        onChange: (next) => teamAccessController.setInviteForm(next),
        onClose: teamAccessController.closeInvite,
        onSubmit: teamAccessController.addMember,
      },
    },
    permissionsWorkspace: {
      permissionsPanelProps: {
        permissionTemplate: teamAccessController.permissionTemplate,
        permissionMatrix: teamAccessController.permissionMatrix,
        permissionColumns: PERMISSION_COLUMNS,
        permissionRoleLabel: PERMISSION_ROLE_LABEL,
        permissionTreeRoot,
        permissionTreeRows: teamAccessController.permissionTreeRows,
        onApplyTemplate: teamAccessController.applyPermissionTemplate,
        onUpdateCell: teamAccessController.updatePermissionCell,
        onSaveMatrix: teamAccessController.persistPermissionMatrix,
      },
    },
    settingsWorkspace: {
      settingsPanelProps: {
        enterpriseInfo: settingsController.enterpriseInfo,
        setEnterpriseInfo: settingsController.setEnterpriseInfo,
        persistEnterpriseInfo: settingsController.persistEnterpriseInfo,
        settings: settingsController.settings,
        setSettings: settingsController.setSettings,
        persistSettings: settingsController.persistSettings,
        setReportTemplateFile: settingsController.setReportTemplateFile,
        persistReportTemplate: settingsController.persistReportTemplate,
        verifyGitpegToken: settingsController.verifyGitpegToken,
        gitpegVerifying: settingsController.gitpegVerifying,
        gitpegVerifyMsg: settingsController.gitpegVerifyMsg,
        setGitpegVerifyMsg: settingsController.setGitpegVerifyMsg,
        setGitpegVerifying: settingsController.setGitpegVerifying,
        erpDraft: settingsController.erpDraft,
        setErpDraft: settingsController.setErpDraft,
        testErpConnection: settingsController.testErpConnection,
        erpTesting: settingsController.erpTesting,
        erpTestMsg: settingsController.erpTestMsg,
        erpWritebackDraft: settingsController.erpWritebackDraft,
        setErpWritebackDraft: settingsController.setErpWritebackDraft,
        testWebhook: settingsController.testWebhook,
        webhookTesting: settingsController.webhookTesting,
        webhookResult: settingsController.webhookResult,
      },
    },
  })

  if (sessionChecking || !appReady) {
    return (
      <AuthEntry
        sessionChecking={sessionChecking}
        loginForm={loginForm}
        loggingIn={loggingIn}
        onLoginFormChange={setLoginForm}
        onLogin={doLogin}
      />
    )
  }

  return (
    <>
      <AppShellLayout
        sidebarOpen={sidebarOpen}
        activeTab={activeTab}
        navItems={roleAwareNavItems}
        navSections={roleAwareNavSections}
        projects={projects}
        currentProjectId={proj.id}
        currentUserName={user?.name || '未命名用户'}
        currentUserTitle={user?.title || '-'}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onNavigate={navigateToAllowedTab}
        onSelectProject={(projectId) => {
          const selected = projects.find((p) => p.id === projectId)
          if (selected) setCurrentProject(selected)
        }}
        onLogout={doLogout}
      >
        <AppWorkspaceContent {...workspaceContentProps} />
      </AppShellLayout>

      <Toast message={toastMsg} />
    </>
  )
}

