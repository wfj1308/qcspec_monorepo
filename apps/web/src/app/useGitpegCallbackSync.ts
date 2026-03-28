import { useEffect } from 'react'
import type { Project } from '@qcspec/types'

interface UseGitpegCallbackSyncArgs {
  gitpegCallbackHandled: boolean
  setGitpegCallbackHandled: (value: boolean) => void
  appReady: boolean
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  completeGitpegApi: (projectId: string, body: {
    code: string
    registration_id?: string
    session_id?: string
    enterprise_id?: string
  }) => Promise<unknown>
  listProjectsApi: (enterpriseId: string) => Promise<unknown>
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setRegisterSuccess: (value: { id: string; name: string; uri: string } | null) => void
  showToast: (message: string) => void
}

export function useGitpegCallbackSync({
  gitpegCallbackHandled,
  setGitpegCallbackHandled,
  appReady,
  canUseEnterpriseApi,
  enterpriseId,
  completeGitpegApi,
  listProjectsApi,
  setProjects,
  setCurrentProject,
  setRegisterSuccess,
  showToast,
}: UseGitpegCallbackSyncArgs): void {
  useEffect(() => {
    if (gitpegCallbackHandled || typeof window === 'undefined') return

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')?.trim() || ''
    if (!code) {
      setGitpegCallbackHandled(true)
      return
    }

    if (!appReady || !canUseEnterpriseApi || !enterpriseId) return

    const projectId = params.get('project_id')?.trim() || params.get('projectId')?.trim() || ''
    const sessionId = params.get('session_id')?.trim() || params.get('sessionId')?.trim() || ''
    const registrationId =
      params.get('registration_id')?.trim() || params.get('registrationId')?.trim() || ''

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
      enterprise_id: enterpriseId,
    })
      .then(async (res) => {
        const payload = res as {
          ok?: boolean
          node_uri?: string
          registration_id?: string
          erp_writeback?: { attempted?: boolean; success?: boolean }
        } | null
        if (!payload?.ok) return

        const refreshed = (await listProjectsApi(enterpriseId)) as { data?: Project[] } | null
        if (refreshed?.data) {
          setProjects(refreshed.data)
          const activated = refreshed.data.find((project) => project.id === projectId) || null
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
      })
      .finally(() => {
        cleanCallbackParams()
      })
  }, [
    gitpegCallbackHandled,
    appReady,
    canUseEnterpriseApi,
    enterpriseId,
    completeGitpegApi,
    listProjectsApi,
    setProjects,
    setCurrentProject,
    setRegisterSuccess,
    showToast,
    setGitpegCallbackHandled,
  ])
}
