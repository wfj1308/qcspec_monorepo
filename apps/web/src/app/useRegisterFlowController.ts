import { useState } from 'react'
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
import type { RegisterErpBindingState, RegisterFormState } from '../components/register/types'
import { pullErpProjectBindingFlow } from './registerErpBindingFlow'
import { submitRegisterFlow } from './registerSubmitFlow'

interface UseRegisterFlowControllerArgs {
  settings: SettingsState
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  currentProject: Project
  projects: Project[]
  addProject: (project: Project) => void
  setProjects: (projects: Project[]) => void
  setCurrentProject: (project: Project | null) => void
  setActiveTab: (tab: string) => void
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
  getErpProjectBasicsApi: (payload: Record<string, unknown>) => Promise<unknown>
  createProjectApi: (body: Record<string, unknown>) => Promise<unknown>
  listProjectsApi: (enterpriseId: string) => Promise<unknown>
  showToast: (message: string) => void
  regForm: RegisterFormState
  setRegForm: Dispatch<SetStateAction<RegisterFormState>>
  setErpBindingLoading: (value: boolean) => void
  erpBinding: RegisterErpBindingState
  setErpBinding: (value: RegisterErpBindingState) => void
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
  segType: SegType
  regKmInterval: number
  regInspectionTypes: InspectionTypeKey[]
  contractSegs: Array<{ name: string; range: string }>
  structures: Array<{ kind: string; name: string; code: string }>
  memberCount: number
  registerSuccess: { id: string; name: string; uri: string } | null
  setRegisterSuccess: (value: { id: string; name: string; uri: string } | null) => void
  resetRegister: () => void
}

export function useRegisterFlowController({
  settings,
  canUseEnterpriseApi,
  enterpriseId,
  currentProject,
  projects,
  addProject,
  setProjects,
  setCurrentProject,
  setActiveTab,
  setProjectMeta,
  getErpProjectBasicsApi,
  createProjectApi,
  listProjectsApi,
  showToast,
  regForm,
  setRegForm,
  setErpBindingLoading,
  erpBinding,
  setErpBinding,
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
  segType,
  regKmInterval,
  regInspectionTypes,
  contractSegs,
  structures,
  memberCount,
  registerSuccess,
  setRegisterSuccess,
  resetRegister,
}: UseRegisterFlowControllerArgs) {
  const [permTemplate, setPermTemplate] = useState<PermTemplate>('standard')

  const pullErpProjectBinding = async () => {
    await pullErpProjectBindingFlow({
      settings,
      canUseEnterpriseApi,
      enterpriseId,
      regForm,
      setRegForm,
      setErpBindingLoading,
      setErpBinding,
      getErpProjectBasicsApi,
      showToast,
    })
  }

  const handleResetRegister = () => {
    resetRegister()
    setPermTemplate('standard')
  }

  const submitRegister = async () => {
    await submitRegisterFlow({
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
      localEnterpriseId: currentProject.enterprise_id,
      showToast,
    })
  }

  const startInspectionFromRegisterSuccess = () => {
    const created = projects.find((project) => project.id === registerSuccess?.id)
    if (created) setCurrentProject(created)
    setActiveTab('inspection')
  }

  const enterInspection = (project: Project) => {
    setCurrentProject(project)
    setActiveTab('inspection')
  }

  return {
    pullErpProjectBinding,
    handleResetRegister,
    submitRegister,
    startInspectionFromRegisterSuccess,
    enterInspection,
  }
}
