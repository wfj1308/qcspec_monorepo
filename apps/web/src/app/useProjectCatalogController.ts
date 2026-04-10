import { useEffect, useMemo, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { Project } from '@qcspec/types'
import type { ProjectRegisterMeta } from './appShellShared'
import { removeProjectFlow } from './projectActionFlows'

interface UseProjectCatalogControllerArgs {
  appReady: boolean
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  projects: Project[]
  currentProject: Project | null
  listProjectsApi: (enterpriseId: string) => Promise<unknown>
  removeProjectApi: (projectId: string) => Promise<unknown>
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
  showToast: (message: string) => void
}

export function useProjectCatalogController({
  appReady,
  canUseEnterpriseApi,
  enterpriseId,
  projects,
  currentProject,
  listProjectsApi,
  removeProjectApi,
  setProjects,
  setCurrentProject,
  setProjectMeta,
  showToast,
}: UseProjectCatalogControllerArgs) {
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const filteredProjects = useMemo(() => projects.filter((project) => {
    if (searchText && !`${project.name}${project.owner_unit}`.toLowerCase().includes(searchText.toLowerCase())) return false
    if (statusFilter && project.status !== statusFilter) return false
    if (typeFilter && project.type !== typeFilter) return false
    return true
  }), [projects, searchText, statusFilter, typeFilter])

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

  return {
    searchText,
    setSearchText,
    statusFilter,
    setStatusFilter,
    typeFilter,
    setTypeFilter,
    filteredProjects,
    removeProject,
  }
}
