import type { Dispatch, SetStateAction } from 'react'
import type { Project } from '@qcspec/types'
import type { ProjectRegisterMeta } from './appShellShared'

interface RemoveProjectFlowArgs {
  projectId: string
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  projects: Project[]
  currentProject: Project | null
  removeProjectApi: (projectId: string, enterpriseId?: string) => Promise<unknown>
  listProjectsApi: (enterpriseId: string) => Promise<unknown>
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
  showToast: (message: string) => void
}

export async function removeProjectFlow({
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
}: RemoveProjectFlowArgs): Promise<void> {
  if (canUseEnterpriseApi && enterpriseId) {
    const res = (await removeProjectApi(projectId, enterpriseId)) as { ok?: boolean } | null
    if (!res?.ok) return

    const refreshed = (await listProjectsApi(enterpriseId)) as { data?: Project[] } | null
    if (refreshed?.data) {
      setProjects(refreshed.data)
      if (currentProject?.id === projectId) {
        setCurrentProject(refreshed.data[0] || null)
      }
    }
  } else {
    const next = projects.filter((project) => project.id !== projectId)
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
  showToast('ÏîÄ¿ÒÑÉ¾³ý')
}
