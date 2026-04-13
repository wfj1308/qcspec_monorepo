import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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
  createProjectApi: (body: Record<string, unknown>) => Promise<unknown>
  removeProjectApi: (projectId: string) => Promise<unknown>
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
  showToast: (message: string) => void
}

function extractProjectsFromListPayload(payload: unknown): Project[] {
  if (!payload || typeof payload !== 'object') return []
  const root = payload as Record<string, unknown>

  const directData = root.data
  if (Array.isArray(directData)) return directData as Project[]

  const items = root.items
  if (Array.isArray(items)) return items as Project[]

  if (directData && typeof directData === 'object') {
    const nested = directData as Record<string, unknown>
    if (Array.isArray(nested.items)) return nested.items as Project[]
  }

  return []
}

export function useProjectCatalogController({
  appReady,
  canUseEnterpriseApi,
  enterpriseId,
  projects,
  currentProject,
  listProjectsApi,
  createProjectApi,
  removeProjectApi,
  setProjects,
  setCurrentProject,
  setProjectMeta,
  showToast,
}: UseProjectCatalogControllerArgs) {
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const currentProjectIdRef = useRef<string | null>(currentProject?.id || null)
  const loadedEnterpriseIdRef = useRef<string | null>(null)
  const loadingInitialRef = useRef(false)

  const filteredProjects = useMemo(() => projects.filter((project) => {
    if (searchText) {
      const row = project as Project & Record<string, unknown>
      const keyword = [
        project.name,
        project.id,
        project.owner_unit,
        project.erp_project_code,
        project.contractor,
        project.supervisor,
        String(row.code || ''),
        String(row.owner_org || row.ownerOrg || ''),
        String(row.client_org || row.clientOrg || ''),
        String(row.designer_org || row.designerOrg || ''),
        String(row.contractor_org || row.contractorOrg || ''),
        String(row.supervisor_org || row.supervisorOrg || ''),
      ]
        .join(' ')
        .toLowerCase()
      if (!keyword.includes(searchText.toLowerCase())) return false
    }
    if (statusFilter && project.status !== statusFilter) return false
    if (typeFilter && project.type !== typeFilter) return false
    return true
  }), [projects, searchText, statusFilter, typeFilter])

  useEffect(() => {
    currentProjectIdRef.current = currentProject?.id || null
  }, [currentProject?.id])

  useEffect(() => {
    if (!appReady || !canUseEnterpriseApi || !enterpriseId) {
      loadedEnterpriseIdRef.current = null
    }
  }, [appReady, canUseEnterpriseApi, enterpriseId])

  const refreshProjects = useCallback(async (options?: { preferredProjectId?: string }) => {
    if (!canUseEnterpriseApi || !enterpriseId) return false
    const res = await listProjectsApi(enterpriseId)
    const nextProjects = extractProjectsFromListPayload(res)
    if (!nextProjects.length) {
      setProjects([])
      setCurrentProject(null)
      return true
    }

    setProjects(nextProjects)

    const preferredId = options?.preferredProjectId || currentProjectIdRef.current || ''
    const nextCurrent = preferredId
      ? nextProjects.find((item) => item.id === preferredId) || nextProjects[0] || null
      : nextProjects[0] || null
    setCurrentProject(nextCurrent)
    return true
  }, [canUseEnterpriseApi, enterpriseId, listProjectsApi, setCurrentProject, setProjects])

  useEffect(() => {
    if (!appReady || !canUseEnterpriseApi || !enterpriseId) return
    if (loadedEnterpriseIdRef.current === enterpriseId || loadingInitialRef.current) return

    loadingInitialRef.current = true
    void refreshProjects()
      .then((ok) => {
        if (ok) loadedEnterpriseIdRef.current = enterpriseId
      })
      .finally(() => {
        loadingInitialRef.current = false
      })
  }, [appReady, canUseEnterpriseApi, enterpriseId, refreshProjects])

  const createProject = async (input: {
    code: string
    name: string
    type: string
    ownerUnit: string
  }): Promise<boolean> => {
    const code = String(input.code || '').trim()
    const name = String(input.name || '').trim()
    const type = String(input.type || '').trim()
    const ownerUnit = String(input.ownerUnit || '').trim()
    if (!code) {
      showToast('项目编码不能为空')
      return false
    }
    if (!name) {
      showToast('项目名称不能为空')
      return false
    }
    if (!type) {
      showToast('项目类型不能为空')
      return false
    }
    if (!ownerUnit) {
      showToast('业主单位不能为空')
      return false
    }

    if (canUseEnterpriseApi) {
      const res = await createProjectApi({
        project_id: code,
        code,
        name,
        type,
        owner_unit: ownerUnit,
        enterprise_id: enterpriseId,
      }) as { data?: Project } | null

      if (!res?.data) {
        showToast('项目创建失败')
        return false
      }

      await refreshProjects({ preferredProjectId: res.data.id })
      showToast('项目已创建')
      return true
    }

    const localId = `PJT-LOCAL-${Date.now()}`
    const localProject: Project = {
      id: localId,
      enterprise_id: enterpriseId || '',
      v_uri: `v://cn.project/${localId}`,
      name,
      type,
      owner_unit: ownerUnit,
      status: 'active',
      record_count: 0,
      photo_count: 0,
      proof_count: 0,
    }
    const next = [localProject, ...projects]
    setProjects(next)
    setCurrentProject(localProject)
    showToast('演示环境：项目已本地创建')
    return true
  }

  const removeProject = async (projectId: string, projectName: string) => {
    const confirmed = typeof window === 'undefined'
      ? true
      : window.confirm(`确认删除项目“${projectName}”？`)
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
    createProject,
    removeProject,
    refreshProjects,
  }
}
