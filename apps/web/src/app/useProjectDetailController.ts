import { useMemo, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { Project } from '@qcspec/types'
import type { ProjectEditDraft, ProjectRegisterMeta } from './appShellShared'
import { buildProjectEditDraft, normalizeProjectMeta } from './projectMetaUtils'

interface EquipmentValidityResult {
  label: string
}

interface UseProjectDetailControllerArgs {
  projects: Project[]
  setProjects: (projects: Project[]) => void
  currentProject: Project | null
  setCurrentProject: (project: Project | null) => void
  projectMeta: Record<string, ProjectRegisterMeta>
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  memberCount: number
  getProjectByIdApi: (projectId: string) => Promise<unknown>
  updateProjectApi: (projectId: string, patch: Record<string, unknown>) => Promise<unknown>
  normalizeKmInterval: (value: unknown, fallback?: number) => number
  buildExecutorUri: (name: string) => string
  buildToolUri: (name: string, modelNo: string) => string
  buildSubcontractUri: (unitName: string) => string
  getEquipmentValidity: (validUntil: string) => EquipmentValidityResult
  showToast: (message: string) => void
}

export function useProjectDetailController({
  projects,
  setProjects,
  currentProject,
  setCurrentProject,
  projectMeta,
  setProjectMeta,
  canUseEnterpriseApi,
  enterpriseId,
  memberCount,
  getProjectByIdApi,
  updateProjectApi,
  normalizeKmInterval,
  buildExecutorUri,
  buildToolUri,
  buildSubcontractUri,
  getEquipmentValidity,
  showToast,
}: UseProjectDetailControllerArgs) {
  const [projectDetailOpen, setProjectDetailOpen] = useState(false)
  const [projectDetailId, setProjectDetailId] = useState<string | null>(null)
  const [detailEdit, setDetailEdit] = useState(false)
  const [detailProjectDraft, setDetailProjectDraft] = useState<ProjectEditDraft | null>(null)
  const [detailDraft, setDetailDraft] = useState<ProjectRegisterMeta | null>(null)

  const detailProject = useMemo(
    () => projects.find((project) => project.id === projectDetailId) || null,
    [projects, projectDetailId]
  )

  const detailMeta = useMemo(
    () => (projectDetailId && projectMeta[projectDetailId]) || null,
    [projectMeta, projectDetailId]
  )

  const clearDetailDrafts = () => {
    setDetailEdit(false)
    setDetailProjectDraft(null)
    setDetailDraft(null)
  }

  const closeProjectDetail = () => {
    setProjectDetailOpen(false)
    clearDetailDrafts()
  }

  const openProjectDetail = async (id: string, edit = false) => {
    setProjectDetailId(id)
    setProjectDetailOpen(true)

    let selectedProject = projects.find((project) => project.id === id) || null
    if (canUseEnterpriseApi) {
      const latest = (await getProjectByIdApi(id)) as Record<string, unknown> | null
      if (latest?.id) {
        const mergedProjects = projects.map((project) => (project.id === id ? { ...project, ...latest } as Project : project))
        setProjects(mergedProjects)
        if (currentProject?.id === id) {
          const mergedCurrent = mergedProjects.find((project) => project.id === id) || null
          setCurrentProject(mergedCurrent)
        }
        selectedProject = { ...(selectedProject || {}), ...latest } as Project
      }
    }

    if (!edit) {
      clearDetailDrafts()
      return
    }

    if (!selectedProject) return

    const meta = projectMeta[id]
    setDetailProjectDraft(buildProjectEditDraft(selectedProject))
    setDetailDraft(normalizeProjectMeta(meta, memberCount))
    setDetailEdit(true)
  }

  const startEditDetail = () => {
    if (!projectDetailId || !detailProject) return

    setDetailProjectDraft(buildProjectEditDraft(detailProject))
    setDetailDraft(normalizeProjectMeta(detailMeta, memberCount))
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
      erp_project_code: detailProjectDraft.erp_project_code || '',
      erp_project_name: detailProjectDraft.erp_project_name || '',
      seg_type: detailDraft.segType,
      seg_start: detailDraft.segStart || '',
      seg_end: detailDraft.segEnd || '',
      km_interval: normalizeKmInterval(detailDraft.kmInterval, 20),
      inspection_types: detailDraft.inspectionTypes,
      contract_segs: detailDraft.contractSegs,
      structures: detailDraft.structures,
      zero_personnel: detailDraft.zeroPersonnel.map((row) => ({
        name: row.name,
        title: row.title,
        dto_role: row.dtoRole,
        certificate: row.certificate,
        executor_uri: buildExecutorUri(row.name),
      })),
      zero_equipment: detailDraft.zeroEquipment.map((row) => ({
        name: row.name,
        model_no: row.modelNo,
        inspection_item: row.inspectionItem,
        valid_until: row.validUntil,
        toolpeg_uri: buildToolUri(row.name, row.modelNo),
        status: getEquipmentValidity(row.validUntil).label,
      })),
      zero_subcontracts: detailDraft.zeroSubcontracts.map((row) => ({
        unit_name: row.unitName,
        content: row.content,
        range: row.range,
        node_uri: buildSubcontractUri(row.unitName),
      })),
      zero_materials: detailDraft.zeroMaterials.map((row) => ({
        name: row.name,
        spec: row.spec,
        supplier: row.supplier,
        freq: row.freq,
      })),
      zero_sign_status: detailDraft.zeroSignStatus,
      qc_ledger_unlocked: detailDraft.qcLedgerUnlocked,
      perm_template: detailDraft.permTemplate,
    }

    if (canUseEnterpriseApi && enterpriseId) {
      const saved = (await updateProjectApi(projectDetailId, patch)) as { id?: string } | null
      if (!saved) return
    }

    const nextProjects = projects.map((project) =>
      project.id === projectDetailId ? { ...project, ...patch } as Project : project
    )
    setProjects(nextProjects)
    if (currentProject?.id === projectDetailId) {
      const nextCurrent = nextProjects.find((project) => project.id === projectDetailId) || null
      setCurrentProject(nextCurrent)
    }
    setProjectMeta((prev) => ({ ...prev, [projectDetailId]: detailDraft }))
    clearDetailDrafts()
    showToast(canUseEnterpriseApi ? '项目信息已保存' : '演示环境：项目信息已本地保存')
  }

  return {
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
    cancelDetailEdit: clearDetailDrafts,
  }
}

