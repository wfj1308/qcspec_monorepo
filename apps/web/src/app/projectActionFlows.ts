import type { Dispatch, SetStateAction } from 'react'
import type { Project } from '@qcspec/types'
import type { ProjectRegisterMeta } from './appShellShared'

interface SyncAutoregResult {
  ok?: boolean
  result?: {
    pending_activation?: boolean
    reason?: string
    autoreg?: { hosted_register_url?: string }
    erp_writeback?: { attempted?: boolean; success?: boolean }
  }
}

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

interface RetryProjectAutoregFlowArgs {
  projectId: string
  projectName: string
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  enterpriseVUri?: string
  settingsGitpegEnabled: boolean
  projects: Project[]
  syncAutoregApi: (projectId: string, body: { enterprise_id?: string; force?: boolean; writeback?: boolean }) => Promise<unknown>
  registerAutoregProjectApi: (payload: Record<string, unknown>) => Promise<unknown>
  registerAutoregProjectAliasApi: (payload: Record<string, unknown>) => Promise<unknown>
  listAutoregProjectsApi: (
    limit?: number,
    filters?: { enterpriseId?: string; namespaceUri?: string }
  ) => Promise<unknown>
  setAutoregRows: (rows: Array<{ project_code?: string; project_name?: string; project_uri?: string; site_uri?: string; updated_at?: string; source_system?: string }>) => void
  setSyncingProjectId: (projectId: string | null) => void
  showToast: (message: string) => void
}

interface DirectProjectAutoregFlowArgs {
  projectId: string
  projectName: string
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  enterpriseVUri?: string
  settingsGitpegEnabled: boolean
  projects: Project[]
  registerAutoregProjectApi: (payload: Record<string, unknown>) => Promise<unknown>
  registerAutoregProjectAliasApi: (payload: Record<string, unknown>) => Promise<unknown>
  listAutoregProjectsApi: (
    limit?: number,
    filters?: { enterpriseId?: string; namespaceUri?: string }
  ) => Promise<unknown>
  setAutoregRows: (rows: Array<{ project_code?: string; project_name?: string; project_uri?: string; site_uri?: string; updated_at?: string; source_system?: string }>) => void
  setSyncingProjectId: (projectId: string | null) => void
  showToast: (message: string) => void
}

const refreshAutoregRows = async (
  listAutoregProjectsApi: (
    limit?: number,
    filters?: { enterpriseId?: string; namespaceUri?: string }
  ) => Promise<unknown>,
  setAutoregRows: (rows: Array<{ project_code?: string; project_name?: string; project_uri?: string; site_uri?: string; updated_at?: string; source_system?: string }>) => void,
  filters?: { enterpriseId?: string; namespaceUri?: string }
): Promise<void> => {
  const latest = (await listAutoregProjectsApi(20, filters)) as {
    items?: Array<{ project_code?: string; project_name?: string; project_uri?: string; site_uri?: string; updated_at?: string; source_system?: string }>
  } | null
  if (latest?.items) setAutoregRows(latest.items)
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
  showToast('项目已删除')
}

export async function retryProjectAutoregFlow({
  projectId,
  projectName,
  canUseEnterpriseApi,
  enterpriseId,
  enterpriseVUri,
  settingsGitpegEnabled,
  projects,
  syncAutoregApi,
  registerAutoregProjectApi,
  registerAutoregProjectAliasApi,
  listAutoregProjectsApi,
  setAutoregRows,
  setSyncingProjectId,
  showToast,
}: RetryProjectAutoregFlowArgs): Promise<void> {
  if (!canUseEnterpriseApi || !enterpriseId) {
    showToast('演示环境不支持自动登记重试')
    return
  }

  const project = projects.find((row) => row.id === projectId)
  if (!project) {
    showToast('项目不存在，无法执行自动登记')
    return
  }

  setSyncingProjectId(projectId)
  let res: SyncAutoregResult | null = null
  try {
    res = (await syncAutoregApi(projectId, {
      enterprise_id: enterpriseId,
      force: true,
      writeback: true,
    })) as SyncAutoregResult | null
  } finally {
    setSyncingProjectId(null)
  }
  if (!res) return

  if (res.ok) {
    if (res.result?.pending_activation) {
      const hostedUrl = res.result?.autoreg?.hosted_register_url
      if (hostedUrl && typeof window !== 'undefined') {
        window.open(hostedUrl, '_blank', 'noopener,noreferrer')
      }
      showToast(
        hostedUrl
          ? `项目「${projectName}」已创建 GitPeg 注册会话，已打开激活页`
          : `项目「${projectName}」已创建 GitPeg 注册会话，待完成激活`
      )
      await refreshAutoregRows(listAutoregProjectsApi, setAutoregRows, {
        enterpriseId,
        namespaceUri: enterpriseVUri,
      })
      return
    }

    const writeback = res.result?.erp_writeback
    if (writeback?.attempted && !writeback?.success) {
      showToast(`项目「${projectName}」自动登记成功，ERP 回写失败`)
    } else {
      showToast(`项目「${projectName}」自动登记成功`)
    }
    await refreshAutoregRows(listAutoregProjectsApi, setAutoregRows, {
      enterpriseId,
      namespaceUri: enterpriseVUri,
    })
    return
  }

  if (res.result?.reason === 'gitpeg_registrar_config_incomplete') {
    showToast(`项目「${projectName}」未激活：请先配置 GitPeg Registrar 参数`)
    return
  }
  if (settingsGitpegEnabled) {
    showToast(`项目「${projectName}」GitPeg 激活失败，请检查 Registrar 服务与凭证`)
    return
  }

  const directPayload = {
    project_code: project.contract_no || project.id,
    project_name: project.name,
    site_code: project.name,
    site_name: project.name,
    namespace_uri: enterpriseVUri,
    source_system: 'qcspec',
  }

  const directRes = (await registerAutoregProjectApi(directPayload)) as { success?: boolean } | null
  if (directRes?.success) {
    showToast(`项目「${projectName}」自动登记成功（直连通道）`)
    await refreshAutoregRows(listAutoregProjectsApi, setAutoregRows, {
      enterpriseId,
      namespaceUri: enterpriseVUri,
    })
    return
  }

  const aliasRes = (await registerAutoregProjectAliasApi(directPayload)) as { success?: boolean } | null
  if (aliasRes?.success) {
    showToast(`项目「${projectName}」自动登记成功（兼容通道）`)
    await refreshAutoregRows(listAutoregProjectsApi, setAutoregRows, {
      enterpriseId,
      namespaceUri: enterpriseVUri,
    })
    return
  }

  showToast(`项目「${projectName}」自动登记失败（已尝试 3 条通道）`)
}

export async function directProjectAutoregFlow({
  projectId,
  projectName,
  canUseEnterpriseApi,
  enterpriseVUri,
  settingsGitpegEnabled,
  projects,
  registerAutoregProjectApi,
  registerAutoregProjectAliasApi,
  listAutoregProjectsApi,
  setAutoregRows,
  enterpriseId,
  setSyncingProjectId,
  showToast,
}: DirectProjectAutoregFlowArgs): Promise<void> {
  if (!canUseEnterpriseApi) {
    showToast('演示环境不支持直连登记')
    return
  }

  const project = projects.find((row) => row.id === projectId)
  if (!project) {
    showToast('项目不存在，无法执行直连登记')
    return
  }

  if (settingsGitpegEnabled) {
    showToast('当前为 GitPeg Registrar 模式，请使用“重试同步”完成节点激活')
    return
  }

  const payload = {
    project_code: project.contract_no || project.id,
    project_name: project.name,
    site_code: project.name,
    site_name: project.name,
    namespace_uri: enterpriseVUri,
    source_system: 'qcspec',
  }

  setSyncingProjectId(projectId)
  let fallback: { success?: boolean } | null = null
  try {
    const primary = (await registerAutoregProjectApi(payload)) as { success?: boolean } | null
    fallback = primary?.success
      ? primary
      : ((await registerAutoregProjectAliasApi(payload)) as { success?: boolean } | null)
  } finally {
    setSyncingProjectId(null)
  }

  if (!fallback?.success) {
    showToast(`项目「${projectName}」直连登记失败`)
    return
  }

  await refreshAutoregRows(listAutoregProjectsApi, setAutoregRows, {
    enterpriseId,
    namespaceUri: enterpriseVUri,
  })
  showToast(`项目「${projectName}」直连登记成功`)
}

