import { useEffect, useMemo, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { Project } from '@qcspec/types'
import type { ProjectRegisterMeta, SettingsState } from './appShellShared'
import { directProjectAutoregFlow, removeProjectFlow, retryProjectAutoregFlow } from './projectActionFlows'

type AutoregRow = {
  project_code?: string
  project_name?: string
  project_uri?: string
  site_uri?: string
  updated_at?: string
  source_system?: string
}

interface UseProjectCatalogControllerArgs {
  appReady: boolean
  activeTab: string
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  enterpriseVUri?: string
  projects: Project[]
  currentProject: Project | null
  settings: SettingsState
  listProjectsApi: (enterpriseId: string) => Promise<unknown>
  removeProjectApi: (projectId: string) => Promise<unknown>
  syncAutoregApi: (projectId: string) => Promise<unknown>
  registerAutoregProjectApi: (payload: Record<string, unknown>) => Promise<unknown>
  registerAutoregProjectAliasApi: (payload: Record<string, unknown>) => Promise<unknown>
  listAutoregProjectsApi: (limit?: number) => Promise<unknown>
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
  showToast: (message: string) => void
}

export function useProjectCatalogController({
  appReady,
  activeTab,
  canUseEnterpriseApi,
  enterpriseId,
  enterpriseVUri,
  projects,
  currentProject,
  settings,
  listProjectsApi,
  removeProjectApi,
  syncAutoregApi,
  registerAutoregProjectApi,
  registerAutoregProjectAliasApi,
  listAutoregProjectsApi,
  setProjects,
  setCurrentProject,
  setProjectMeta,
  showToast,
}: UseProjectCatalogControllerArgs) {
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [syncingProjectId, setSyncingProjectId] = useState<string | null>(null)
  const [autoregRows, setAutoregRows] = useState<AutoregRow[]>([])

  const filteredProjects = useMemo(() => projects.filter((project) => {
    if (searchText && !`${project.name}${project.owner_unit}`.toLowerCase().includes(searchText.toLowerCase())) return false
    if (statusFilter && project.status !== statusFilter) return false
    if (typeFilter && project.type !== typeFilter) return false
    return true
  }), [projects, searchText, statusFilter, typeFilter])

  const refreshAutoregRows = async () => {
    const latest = await listAutoregProjectsApi(20) as { items?: AutoregRow[] } | null
    if (latest?.items) setAutoregRows(latest.items)
  }

  useEffect(() => {
    if (!canUseEnterpriseApi || (activeTab !== 'projects' && activeTab !== 'settings')) return
    void refreshAutoregRows()
  }, [activeTab, canUseEnterpriseApi, listAutoregProjectsApi])

  useEffect(() => {
    if (!appReady || !canUseEnterpriseApi || !enterpriseId) return
    let cancelled = false
    listProjectsApi(enterpriseId).then((res) => {
      if (cancelled) return
      const payload = res as { data?: Project[] } | null
      if (!payload?.data) return
      setProjects(payload.data)
      if (!currentProject?.id && payload.data.length > 0) {
        setCurrentProject(payload.data[0])
      }
    })
    return () => {
      cancelled = true
    }
  }, [appReady, canUseEnterpriseApi, enterpriseId, listProjectsApi, setProjects, setCurrentProject, currentProject?.id])

  const removeProject = async (projectId: string, projectName: string) => {
    const confirmed = typeof window === 'undefined' ? true : window.confirm(`确认删除项目「${projectName}」？`)
    if (!confirmed) return

    await removeProjectFlow({
      projectId,
      canUseEnterpriseApi,
      enterpriseId,
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
      enterpriseId,
      enterpriseVUri,
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
      enterpriseVUri,
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

  return {
    searchText,
    setSearchText,
    statusFilter,
    setStatusFilter,
    typeFilter,
    setTypeFilter,
    syncingProjectId,
    autoregRows,
    filteredProjects,
    refreshAutoregRows,
    removeProject,
    retryProjectAutoreg,
    directProjectAutoreg,
  }
}
