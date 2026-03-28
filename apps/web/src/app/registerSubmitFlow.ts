import type { Dispatch, SetStateAction } from 'react'
import type { Project } from '@qcspec/types'
import type {
  InspectionTypeKey,
  PermTemplate,
  ProjectRegisterMeta,
  SegType,
  SettingsState,
  ZeroEquipmentRow,
  ZeroMaterialRow,
  ZeroPersonnelRow,
  ZeroSubcontractRow,
} from './appShellShared'
import {
  normalizeZeroEquipmentRows,
  normalizeZeroMaterialRows,
  normalizeZeroPersonnelRows,
  normalizeZeroSubcontractRows,
} from './appShellShared'
import type { RegisterErpBindingState, RegisterFormState } from '../components/register/types'

interface SubmitRegisterFlowArgs {
  regForm: RegisterFormState
  settings: SettingsState
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  erpBinding: RegisterErpBindingState
  projects: Project[]
  regUri: string
  setVpathStatus: (value: 'checking' | 'available' | 'taken') => void
  zeroPersonnel: ZeroPersonnelRow[]
  zeroEquipment: ZeroEquipmentRow[]
  zeroSubcontracts: ZeroSubcontractRow[]
  zeroMaterials: ZeroMaterialRow[]
  buildExecutorUri: (name: string) => string
  buildToolUri: (name: string, modelNo: string) => string
  buildSubcontractUri: (unitName: string) => string
  getEquipmentValidity: (validUntil: string) => { label: string }
  createProjectApi: (body: Record<string, unknown>) => Promise<unknown>
  listProjectsApi: (enterpriseId: string) => Promise<unknown>
  setProjects: (projects: Project[]) => void
  addProject: (project: Project) => void
  setCurrentProject: (project: Project | null) => void
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
  setRegisterSuccess: (value: { id: string; name: string; uri: string } | null) => void
  segType: SegType
  regKmInterval: number
  regInspectionTypes: InspectionTypeKey[]
  contractSegs: Array<{ name: string; range: string }>
  structures: Array<{ kind: string; name: string; code: string }>
  permTemplate: PermTemplate
  memberCount: number
  localEnterpriseId: string
  showToast: (message: string) => void
}

interface CreateProjectResult {
  id?: string
  v_uri?: string
  name?: string
  erp_project_code?: string
  erp_project_name?: string
  autoreg_sync?: {
    enabled?: boolean
    success?: boolean
    pending_activation?: boolean
    skipped?: boolean
    reason?: string
    autoreg?: {
      hosted_register_url?: string
      session_id?: string
      expires_at?: string
    }
    erp_writeback?: {
      attempted?: boolean
      success?: boolean
      reason?: string
    }
  }
}

export async function submitRegisterFlow({
  regForm,
  settings,
  canUseEnterpriseApi,
  enterpriseId,
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
  memberCount,
  localEnterpriseId,
  showToast,
}: SubmitRegisterFlowArgs): Promise<void> {
  if (!regForm.name || !regForm.owner_unit) {
    showToast('请先填写项目名称和业主单位')
    return
  }
  if (settings.erpnextSync && (!canUseEnterpriseApi || !enterpriseId)) {
    showToast('ERP 同步已启用，当前环境不支持离线注册，请连接后端后重试')
    return
  }
  if (settings.erpnextSync && !regForm.erp_project_code.trim()) {
    showToast('ERP 同步已启用，请填写 ERP 项目编码（如 PROJ-0001）')
    return
  }
  if (
    settings.erpnextSync &&
    (!erpBinding.success ||
      erpBinding.code !== String(regForm.erp_project_code || '').trim() ||
      erpBinding.name !== String(regForm.erp_project_name || '').trim())
  ) {
    showToast('请先从 ERP 拉取并绑定项目，再确认注册')
    return
  }
  if (projects.some((project) => project.v_uri === regUri)) {
    setVpathStatus('taken')
    showToast('该 v:// 节点已存在，请修改项目名称或类型')
    return
  }

  const zeroPersonnelPayload = zeroPersonnel
    .map((row) => ({
      name: row.name.trim(),
      title: row.title.trim(),
      dto_role: row.dtoRole,
      certificate: row.certificate.trim(),
      executor_uri: buildExecutorUri(row.name),
    }))
    .filter((row) => row.name || row.title || row.certificate)

  const zeroEquipmentPayload = zeroEquipment
    .map((row) => {
      const validity = getEquipmentValidity(row.validUntil)
      return {
        name: row.name.trim(),
        model_no: row.modelNo.trim(),
        inspection_item: row.inspectionItem.trim(),
        valid_until: row.validUntil,
        toolpeg_uri: buildToolUri(row.name, row.modelNo),
        status: validity.label,
      }
    })
    .filter((row) => row.name || row.model_no)

  const zeroSubcontractsPayload = zeroSubcontracts
    .map((row) => ({
      unit_name: row.unitName.trim(),
      content: row.content.trim(),
      range: row.range.trim(),
      node_uri: buildSubcontractUri(row.unitName),
    }))
    .filter((row) => row.unit_name || row.content || row.range)

  const zeroMaterialsPayload = zeroMaterials
    .map((row) => ({
      name: row.name.trim(),
      spec: row.spec.trim(),
      supplier: row.supplier.trim(),
      freq: row.freq.trim(),
    }))
    .filter((row) => row.name || row.spec || row.supplier || row.freq)

  if (canUseEnterpriseApi && enterpriseId) {
    const created = (await createProjectApi({
      enterprise_id: enterpriseId,
      name: regForm.name,
      type: regForm.type,
      owner_unit: regForm.owner_unit,
      erp_project_code: (settings.erpnextSync ? erpBinding.code : regForm.erp_project_code) || undefined,
      erp_project_name: (settings.erpnextSync ? erpBinding.name : regForm.erp_project_name) || undefined,
      contractor: regForm.contractor || undefined,
      supervisor: regForm.supervisor || undefined,
      contract_no: regForm.contract_no || undefined,
      start_date: regForm.start_date || undefined,
      end_date: regForm.end_date || undefined,
      description: regForm.description || undefined,
      seg_type: segType,
      seg_start: regForm.seg_start || undefined,
      seg_end: regForm.seg_end || undefined,
      km_interval: regKmInterval,
      inspection_types: regInspectionTypes,
      contract_segs: contractSegs,
      structures,
      zero_personnel: zeroPersonnelPayload,
      zero_equipment: zeroEquipmentPayload,
      zero_subcontracts: zeroSubcontractsPayload,
      zero_materials: zeroMaterialsPayload,
      zero_sign_status: 'pending',
      qc_ledger_unlocked: false,
      perm_template: permTemplate,
    })) as CreateProjectResult | null

    if (!created?.id) return

    const refreshed = (await listProjectsApi(enterpriseId)) as { data?: Project[] } | null
    let createdProject: Project | null = null
    if (refreshed?.data && refreshed.data.length > 0) {
      setProjects(refreshed.data)
      createdProject = refreshed.data.find((project) => project.id === created.id) || null
    } else {
      const fallbackProject: Project = {
        id: created.id,
        enterprise_id: enterpriseId,
        v_uri: created.v_uri || regUri,
        name: created.name || regForm.name,
        erp_project_code:
          created.erp_project_code ||
          (settings.erpnextSync ? erpBinding.code : regForm.erp_project_code) ||
          '',
        erp_project_name:
          created.erp_project_name ||
          (settings.erpnextSync ? erpBinding.name : regForm.erp_project_name) ||
          '',
        type: regForm.type,
        owner_unit: regForm.owner_unit,
        contractor: regForm.contractor || '',
        supervisor: regForm.supervisor || '',
        contract_no: regForm.contract_no || '',
        start_date: regForm.start_date || '',
        end_date: regForm.end_date || '',
        status: 'active',
        record_count: 0,
        photo_count: 0,
        proof_count: 0,
      }
      const nextProjects = [fallbackProject, ...projects.filter((project) => project.id !== fallbackProject.id)]
      setProjects(nextProjects)
      createdProject = fallbackProject
      showToast('项目已创建，项目列表刷新超时或为空，已本地兜底展示')
    }

    if (createdProject) {
      setCurrentProject(createdProject)
    }

    setProjectMeta((prev) => ({
      ...prev,
      [created.id as string]: {
        segType: segType,
        segStart: regForm.seg_start,
        segEnd: regForm.seg_end,
        kmInterval: regKmInterval,
        inspectionTypes: regInspectionTypes,
        contractSegs,
        structures,
        zeroPersonnel: normalizeZeroPersonnelRows(zeroPersonnelPayload),
        zeroEquipment: normalizeZeroEquipmentRows(zeroEquipmentPayload),
        zeroSubcontracts: normalizeZeroSubcontractRows(zeroSubcontractsPayload),
        zeroMaterials: normalizeZeroMaterialRows(zeroMaterialsPayload),
        zeroSignStatus: 'pending',
        qcLedgerUnlocked: false,
        permTemplate,
        memberCount,
      },
    }))

    setRegisterSuccess({
      id: created.id,
      name: created.name || regForm.name,
      uri: created.v_uri || regUri,
    })

    if (created.autoreg_sync?.enabled && created.autoreg_sync?.pending_activation) {
      const hostedUrl = created.autoreg_sync?.autoreg?.hosted_register_url
      if (hostedUrl && typeof window !== 'undefined') {
        window.open(hostedUrl, '_blank', 'noopener,noreferrer')
      }
      showToast(
        hostedUrl
          ? '项目已创建，已打开 GitPeg 注册页，请完成节点激活'
          : '项目已创建，GitPeg 注册会话已创建，请完成节点激活'
      )
    } else if (created.autoreg_sync?.enabled && created.autoreg_sync?.success) {
      const writeback = created.autoreg_sync.erp_writeback
      if (writeback?.attempted && !writeback?.success) {
        showToast('项目注册成功，GitPeg 已登记；ERP 回写失败，可手动重试')
      } else {
        showToast('项目注册成功，已完成自动登记')
      }
    } else if (created.autoreg_sync?.enabled && !created.autoreg_sync?.success) {
      if (created.autoreg_sync?.reason === 'gitpeg_registrar_config_incomplete') {
        showToast('项目注册成功，但 GitPeg Registrar 配置不完整，尚未激活主权节点')
      } else {
        showToast('项目注册成功，但自动登记失败，可手动重试')
      }
    } else {
      showToast('项目注册成功（自动登记未启用）')
    }

    return
  }

  const newId =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `66666666-6666-4666-8666-${String(Date.now()).slice(-12).padStart(12, '0')}`

  const localProject: Project = {
    id: newId,
    enterprise_id: localEnterpriseId,
    v_uri: regUri,
    name: regForm.name,
    erp_project_code: settings.erpnextSync ? erpBinding.code : regForm.erp_project_code,
    erp_project_name: settings.erpnextSync ? erpBinding.name : regForm.erp_project_name || regForm.name,
    type: regForm.type,
    owner_unit: regForm.owner_unit,
    contractor: regForm.contractor,
    supervisor: regForm.supervisor,
    contract_no: regForm.contract_no,
    start_date: regForm.start_date,
    end_date: regForm.end_date,
    seg_type: segType,
    seg_start: regForm.seg_start,
    seg_end: regForm.seg_end,
    km_interval: regKmInterval,
    inspection_types: regInspectionTypes,
    contract_segs: contractSegs,
    structures,
    zero_personnel: zeroPersonnelPayload,
    zero_equipment: zeroEquipmentPayload,
    zero_subcontracts: zeroSubcontractsPayload,
    zero_materials: zeroMaterialsPayload,
    zero_sign_status: 'pending',
    qc_ledger_unlocked: false,
    perm_template: permTemplate,
    status: 'active',
    record_count: 0,
    photo_count: 0,
    proof_count: 0,
  }

  addProject(localProject)
  setCurrentProject(localProject)
  setProjectMeta((prev) => ({
    ...prev,
    [newId]: {
      segType,
      segStart: regForm.seg_start,
      segEnd: regForm.seg_end,
      kmInterval: regKmInterval,
      inspectionTypes: regInspectionTypes,
      contractSegs,
      structures,
      zeroPersonnel: normalizeZeroPersonnelRows(zeroPersonnelPayload),
      zeroEquipment: normalizeZeroEquipmentRows(zeroEquipmentPayload),
      zeroSubcontracts: normalizeZeroSubcontractRows(zeroSubcontractsPayload),
      zeroMaterials: normalizeZeroMaterialRows(zeroMaterialsPayload),
      zeroSignStatus: 'pending',
      qcLedgerUnlocked: false,
      permTemplate,
      memberCount,
    },
  }))
  setRegisterSuccess({ id: newId, name: regForm.name, uri: regUri })
  showToast('项目注册成功')
}

