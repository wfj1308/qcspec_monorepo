import { useEffect, useState } from 'react'
import { useUIStore, useProjectStore, useAuthStore } from './store'
import { Toast } from './components/ui'
import { useAuthApi, useProof, useTeam, useSettings, useProjects } from './hooks/api'
import AppShellLayout from './components/layout/AppShellLayout'
import AuthEntry from './components/auth/AuthEntry'
import AppWorkspaceContent from './app/AppWorkspaceContent'
import { useSettingsController } from './app/useSettingsController'
import { useProjectDetailController } from './app/useProjectDetailController'
import { doLoginFlow, doLogoutFlow } from './app/authFlows'
import { useGitpegCallbackSync } from './app/useGitpegCallbackSync'
import { useProjectMetaSync } from './app/useProjectMetaSync'
import { useAuthSessionController } from './app/useAuthSessionController'
import { useTeamSettingsBootstrap } from './app/useTeamSettingsBootstrap'
import { useProofDashboardController } from './app/useProofDashboardController'
import { useProjectCatalogController } from './app/useProjectCatalogController'
import { useTeamAccessController } from './app/useTeamAccessController'
import { useAppWorkspaceProps } from './app/useAppWorkspaceProps'
import {
  buildProofWorkspace,
  buildProjectsWorkspace,
  buildTeamWorkspace,
  buildSettingsWorkspace,
} from './app/workspaceBuilders'


import {
  NAV,
  NAV_SECTIONS,
  InspectionTypeKey,
  ProjectRegisterMeta,
  PERMISSION_ROLE_LABEL,
  PERMISSION_COLUMNS,
  TYPE_LABEL,
  TYPE_ICON,
  PROJECT_TYPE_OPTIONS,
  INSPECTION_TYPE_OPTIONS,
  INSPECTION_TYPE_LABEL,
  getAllowedNavKeysByRole,
  normalizeKmInterval,
  resolveAllowedTab,
} from './app/appShellShared'

const CLEAN_START_MIGRATION_KEY = 'qcspec.clean.start.20260410'

export default function App() {
  const { activeTab, setActiveTab, toastMsg, sidebarOpen, setSidebarOpen, showToast } = useUIStore()
  const { projects, setProjects, currentProject, setCurrentProject } = useProjectStore()
  const { setUser, logout, enterprise, user, token } = useAuthStore()
  const {
    list: listProjectsApi,
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
  const { listMembers, inviteMember, updateMember: updateMemberApi, removeMember: removeMemberApi } = useTeam()
  const { getSettings, saveSettings, testErpnext, testGitpegRegistrar, uploadTemplate } = useSettings()

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
  })

  useEffect(() => {
    setEnterpriseInfo({
      name: enterprise?.name || '',
      vUri: enterprise?.v_uri || '',
      creditCode: '',
      adminEmail: user?.email || '',
    })
  }, [enterprise?.name, enterprise?.v_uri, user?.email])

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
  const canUseEnterpriseApi = !!enterprise?.id
  const proj = currentProject || projects[0] || { id: '', name: '', v_uri: '' }

  const teamAccessController = useTeamAccessController({
    canUseEnterpriseApi,
    enterpriseId: enterprise?.id || undefined,
    projects,
    currentProjectId: proj.id,
    saveSettings,
    inviteMember,
    listMembers,
    updateMemberApi,
    removeMemberApi,
    showToast,
  })
  const {
    members,
    setMembers,
    setMemberRoleDrafts,
    setPermissionMatrix,
    setPermissionTemplate,
  } = teamAccessController
  const settingsController = useSettingsController({
    canUseEnterpriseApi,
    enterpriseId: enterprise?.id || undefined,
    initialReportHeader: enterprise?.name || '',
    initialEnterpriseInfo: {
      name: enterprise?.name || '',
      vUri: enterprise?.v_uri || '',
      creditCode: '',
      adminEmail: user?.email || '',
    },
    saveSettings,
    uploadTemplate,
    testGitpegRegistrar,
    testErpnext,
    showToast,
  })
  const {
    setSettings,
    setErpDraft,
    setErpWritebackDraft,
    setEnterpriseInfo,
  } = settingsController

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
  const proofDashboard = useProofDashboardController({
    activeTab,
    proj,
    projectDetailOpen: projectDetailController.projectDetailOpen,
    detailProject: projectDetailController.detailProject,
    showToast,
    listProofs,
    verifyProof,
    proofStatsApi,
    proofNodeTreeApi,
    boqRealtimeStatusApi,
    boqItemSovereignHistoryApi,
    boqReconciliationApi,
    docFinalContextApi,
  })
  const projectCatalog = useProjectCatalogController({
    appReady,
    canUseEnterpriseApi,
    enterpriseId: enterprise?.id || undefined,
    projects,
    currentProject,
    listProjectsApi,
    removeProjectApi,
    setProjects,
    setCurrentProject,
    setProjectMeta,
    showToast,
  })
  const permissionTreeRoot = enterprise?.v_uri || proj.v_uri || `${fallbackNodeRoot}/`

  const globalAllowedNavKeys = getAllowedNavKeysByRole(user?.dto_role)
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

  useTeamSettingsBootstrap({
    appReady,
    activeTab,
    canUseEnterpriseApi,
    enterpriseId: enterprise?.id || undefined,
    listMembers,
    getSettings,
    setMembers,
    setMemberRoleDrafts,
    setSettings,
    setErpDraft,
    setErpWritebackDraft,
    setPermissionMatrix,
    setPermissionTemplate,
    setEnterpriseInfo,
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

  const canQuickInspection = globalAllowedNavKeys.includes('inspection')
  const canQuickProof = globalAllowedNavKeys.includes('proof')
  const canQuickReports = globalAllowedNavKeys.includes('reports')

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

    logout()
    setProjects([])
    setCurrentProject(null)
    setAppReady(false)
    showToast('已清理历史本地数据，请使用真实账号重新登录')
  }, [logout, setAppReady, setCurrentProject, setProjects, showToast])

  const openInspectionWorkspace = (targetProject?: typeof projects[number]) => {
    if (!canQuickInspection) {
      showToast('当前角色无质检录入权限')
      return
    }
    const selected = targetProject || currentProject || projects[0]
    if (!selected) {
      showToast('请先在上游系统完成项目创建并同步到 QCSpec')
      navigateToAllowedTab('projects')
      return
    }
    setCurrentProject(selected)
    navigateToAllowedTab('inspection')
  }

  const openProofWorkspace = (targetProject?: typeof projects[number]) => {
    if (!canQuickProof) {
      showToast('当前角色无 Proof 工作台权限')
      return
    }
    const selected = targetProject || currentProject || projects[0]
    if (!selected) {
      showToast('请先在上游系统完成项目创建并同步到 QCSpec')
      navigateToAllowedTab('projects')
      return
    }
    setCurrentProject(selected)
    navigateToAllowedTab('proof')
  }

  const workspaceContentProps = useAppWorkspaceProps({
    activeTab,
    proofWorkspace: buildProofWorkspace({
      proofDashboard,
      onGoInspection: () => openInspectionWorkspace(),
      onGoReports: canQuickReports ? () => navigateToAllowedTab('reports') : undefined,
    }),
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
      onEnterInspection: (project) => openInspectionWorkspace(project),
      onEnterProof: (project) => openProofWorkspace(project),
    }),
    teamWorkspace: buildTeamWorkspace({
      projects,
      permissionTreeRoot,
      permissionColumns: PERMISSION_COLUMNS,
      permissionRoleLabel: PERMISSION_ROLE_LABEL,
      teamAccessController,
    }),
    settingsWorkspace: buildSettingsWorkspace({
      settingsController,
    }),
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
        canQuickInspection={canQuickInspection}
        canQuickProof={canQuickProof}
        onQuickInspection={() => openInspectionWorkspace()}
        onQuickProof={() => openProofWorkspace()}
        onLogout={doLogout}
      >
        <AppWorkspaceContent {...workspaceContentProps} />
      </AppShellLayout>

      <Toast message={toastMsg} />
    </>
  )
}

