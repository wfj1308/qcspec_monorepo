import type { ProjectRegisterMeta } from './appShellShared'
import type {
  ProofWorkspaceProps,
  ProjectsWorkspaceProps,
  RegisterWorkspaceProps,
  TeamWorkspaceProps,
  SettingsWorkspaceProps,
} from './AppWorkspaceContent'
import type { useProofDashboardController } from './useProofDashboardController'
import type { useProjectCatalogController } from './useProjectCatalogController'
import type { useProjectDetailController } from './useProjectDetailController'
import type { useRegisterController } from './useRegisterController'
import type { useRegisterFlowController } from './useRegisterFlowController'
import type { useTeamAccessController } from './useTeamAccessController'
import type { useSettingsController } from './useSettingsController'

type ProofDashboardController = ReturnType<typeof useProofDashboardController>
type ProjectCatalogController = ReturnType<typeof useProjectCatalogController>
type ProjectDetailController = ReturnType<typeof useProjectDetailController>
type RegisterController = ReturnType<typeof useRegisterController>
type RegisterFlowController = ReturnType<typeof useRegisterFlowController>
type TeamAccessController = ReturnType<typeof useTeamAccessController>
type SettingsController = ReturnType<typeof useSettingsController>
type ProjectInspectionTarget = Parameters<ProjectsWorkspaceProps['projectsPanelProps']['onEnterInspection']>[0]

type BuildProofWorkspaceArgs = {
  projectUri?: string
  paymentId: string
  proofDashboard: ProofDashboardController
  onGoInspection?: () => void
  onGoReports?: () => void
}

type BuildProjectsWorkspaceArgs = {
  canUseEnterpriseApi: boolean
  projectMeta: Record<string, ProjectRegisterMeta>
  projectCatalog: ProjectCatalogController
  projectDetailController: ProjectDetailController
  proofDashboard: ProofDashboardController
  projectTypeOptions: ProjectsWorkspaceProps['projectsPanelProps']['projectTypeOptions']
  inspectionTypeOptions: ProjectsWorkspaceProps['projectDetailDrawerProps']['inspectionTypeOptions']
  inspectionTypeLabel: ProjectsWorkspaceProps['projectDetailDrawerProps']['inspectionTypeLabel']
  typeIcon: ProjectsWorkspaceProps['projectsPanelProps']['typeIcon']
  typeLabel: ProjectsWorkspaceProps['projectsPanelProps']['typeLabel']
  sidebarOpen: boolean
  normalizeKmInterval: ProjectsWorkspaceProps['projectDetailDrawerProps']['normalizeKmInterval']
  toggleInspectionType: ProjectsWorkspaceProps['projectDetailDrawerProps']['toggleInspectionType']
  onCreateProject: () => void
  onGoInspection: () => void
  onGoProof: () => void
  onEnterInspection: (project: ProjectInspectionTarget) => void
  onEnterProof: (project: ProjectInspectionTarget) => void
}

type BuildRegisterWorkspaceArgs = {
  projects: RegisterWorkspaceProps['registerWorkspaceProps']['projects']
  settings: RegisterWorkspaceProps['registerWorkspaceProps']['settings']
  registerController: RegisterController
  registerFlowController: RegisterFlowController
  onGoProjects: RegisterWorkspaceProps['registerWorkspaceProps']['onGoProjects']
  onOpenProjectDetail: RegisterWorkspaceProps['registerWorkspaceProps']['onOpenProjectDetail']
  projectTypeOptions: RegisterWorkspaceProps['registerWorkspaceProps']['projectTypeOptions']
  typeIcon: RegisterWorkspaceProps['registerWorkspaceProps']['typeIcon']
  typeLabel: RegisterWorkspaceProps['registerWorkspaceProps']['typeLabel']
  inspectionTypeOptions: RegisterWorkspaceProps['registerWorkspaceProps']['inspectionTypeOptions']
  inspectionTypeLabel: RegisterWorkspaceProps['registerWorkspaceProps']['inspectionTypeLabel']
}

type BuildTeamWorkspaceArgs = {
  projects: TeamWorkspaceProps['inviteMemberModalProps']['projects']
  permissionTreeRoot: TeamWorkspaceProps['permissionsPanelProps']['permissionTreeRoot']
  permissionColumns: TeamWorkspaceProps['permissionsPanelProps']['permissionColumns']
  permissionRoleLabel: TeamWorkspaceProps['permissionsPanelProps']['permissionRoleLabel']
  teamAccessController: TeamAccessController
}

type BuildSettingsWorkspaceArgs = {
  settingsController: SettingsController
}

export function buildProofWorkspace({
  projectUri,
  paymentId,
  proofDashboard,
  onGoInspection,
  onGoReports,
}: BuildProofWorkspaceArgs): ProofWorkspaceProps {
  return {
    projectUri,
    proofPanelProps: {
      projectUri,
      proofStats: proofDashboard.proofStats,
      proofNodeRows: proofDashboard.proofNodeRows,
      proofLoading: proofDashboard.proofLoading,
      proofRows: proofDashboard.proofRows,
      proofVerifying: proofDashboard.proofVerifying,
      onVerifyProof: proofDashboard.handleVerifyProof,
      onGoInspection,
      onGoReports,
    },
    paymentAuditPanelProps: {
      projectUri,
      paymentGenerating: proofDashboard.paymentGenerating,
      paymentResult: proofDashboard.paymentResult,
      railpactSubmitting: proofDashboard.railpactSubmitting,
      railpactResult: proofDashboard.railpactResult,
      auditLoading: proofDashboard.auditLoading,
      auditResult: proofDashboard.auditResult,
      frequencyLoading: proofDashboard.frequencyLoading,
      frequencyResult: proofDashboard.frequencyResult,
      deliveryFinalizing: proofDashboard.deliveryFinalizing,
      onGeneratePaymentCertificate: proofDashboard.handleGeneratePaymentCertificate,
      onGenerateRailPactInstruction: proofDashboard.handleGenerateRailPactInstruction,
      onOpenAuditTrace: proofDashboard.handleOpenAuditTrace,
      onFinalizeDelivery: proofDashboard.handleFinalizeDelivery,
      onOpenVerifyNode: proofDashboard.handleOpenVerifyNode,
    },
    spatialGovernancePanelProps: {
      projectUri,
      spatialLoading: proofDashboard.spatialLoading,
      spatialDashboard: proofDashboard.spatialDashboard,
      aiRunning: proofDashboard.aiRunning,
      aiResult: proofDashboard.aiResult,
      financeExporting: proofDashboard.financeExporting,
      defaultPaymentId: paymentId,
      onRefreshSpatial: proofDashboard.refreshSpatialDashboard,
      onBindSpatial: proofDashboard.handleBindSpatial,
      onRunPredictive: proofDashboard.handleRunPredictive,
      onExportFinanceProof: proofDashboard.handleExportFinanceProof,
      onOpenVerifyNode: proofDashboard.handleOpenVerifyNode,
    },
    rwaOmEvolutionPanelProps: {
      projectUri,
      rwaConverting: proofDashboard.rwaConverting,
      omExporting: proofDashboard.omExporting,
      omEventSubmitting: proofDashboard.omEventSubmitting,
      normRunning: proofDashboard.normEvolutionRunning,
      normResult: proofDashboard.normEvolutionResult,
      lastPaymentId: paymentId,
      lastOmRootProofId: proofDashboard.lastOmRootProofId,
      onConvertRwa: proofDashboard.handleConvertRwaAsset,
      onExportOmBundle: proofDashboard.handleExportOmBundle,
      onRegisterOmEvent: proofDashboard.handleRegisterOmEvent,
      onGenerateNormEvolution: proofDashboard.handleGenerateNormEvolution,
    },
  }
}

export function buildProjectsWorkspace({
  canUseEnterpriseApi,
  projectMeta,
  projectCatalog,
  projectDetailController,
  proofDashboard,
  projectTypeOptions,
  inspectionTypeOptions,
  inspectionTypeLabel,
  typeIcon,
  typeLabel,
  sidebarOpen,
  normalizeKmInterval,
  toggleInspectionType,
  onCreateProject,
  onGoInspection,
  onGoProof,
  onEnterInspection,
  onEnterProof,
}: BuildProjectsWorkspaceArgs): ProjectsWorkspaceProps {
  return {
    projectsPanelProps: {
      searchText: projectCatalog.searchText,
      statusFilter: projectCatalog.statusFilter,
      typeFilter: projectCatalog.typeFilter,
      projectTypeOptions,
      filteredProjects: projectCatalog.filteredProjects,
      projectMeta,
      typeIcon,
      typeLabel,
      canUseEnterpriseApi,
      syncingProjectId: projectCatalog.syncingProjectId,
      autoregRows: projectCatalog.autoregRows,
      onSearchTextChange: projectCatalog.setSearchText,
      onStatusFilterChange: projectCatalog.setStatusFilter,
      onTypeFilterChange: projectCatalog.setTypeFilter,
      onCreateProject,
      onGoInspection,
      onGoProof,
      onEnterInspection,
      onEnterProof,
      onRetryAutoreg: projectCatalog.retryProjectAutoreg,
      onDirectAutoreg: projectCatalog.directProjectAutoreg,
      onEditProject: (projectId) => projectDetailController.openProjectDetail(projectId, true),
      onOpenProjectDetail: (projectId) => projectDetailController.openProjectDetail(projectId),
      onDeleteProject: projectCatalog.removeProject,
      onRefreshAutoreg: projectCatalog.refreshAutoregRows,
    },
    projectDetailDrawerProps: {
      open: projectDetailController.projectDetailOpen,
      detailProject: projectDetailController.detailProject,
      detailEdit: projectDetailController.detailEdit,
      detailProjectDraft: projectDetailController.detailProjectDraft,
      detailMeta: projectDetailController.detailMeta,
      detailDraft: projectDetailController.detailDraft,
      projectTypeOptions,
      inspectionTypeOptions,
      inspectionTypeLabel,
      typeLabel,
      sidebarOpen,
      onClose: projectDetailController.closeProjectDetail,
      onStartEdit: projectDetailController.startEditDetail,
      onSave: projectDetailController.saveDetailMeta,
      onCancelEdit: projectDetailController.cancelDetailEdit,
      onDetailProjectDraftChange: projectDetailController.setDetailProjectDraft,
      onDetailDraftChange: projectDetailController.setDetailDraft,
      normalizeKmInterval,
      toggleInspectionType,
      boqRealtime: proofDashboard.boqRealtime,
      boqRealtimeLoading: proofDashboard.boqRealtimeLoading,
      boqAudit: proofDashboard.boqAudit,
      boqAuditLoading: proofDashboard.boqAuditLoading,
      boqProofPreview: proofDashboard.boqProofPreview,
      boqProofLoadingUri: proofDashboard.boqProofLoadingUri || undefined,
      boqSovereignPreview: proofDashboard.boqSovereignPreview,
      boqSovereignLoadingCode: proofDashboard.boqSovereignLoadingCode || undefined,
      onOpenBoqProofChain: proofDashboard.handleOpenBoqProofChain,
      onOpenBoqSovereignHistory: proofDashboard.handleOpenBoqSovereignHistory,
    },
  }
}

export function buildRegisterWorkspace({
  projects,
  settings,
  registerController,
  registerFlowController,
  onGoProjects,
  onOpenProjectDetail,
  projectTypeOptions,
  typeIcon,
  typeLabel,
  inspectionTypeOptions,
  inspectionTypeLabel,
}: BuildRegisterWorkspaceArgs): RegisterWorkspaceProps {
  return {
    registerWorkspaceProps: {
      projects,
      registerSegCount: registerController.registerSegCount,
      registerRecordCount: registerController.registerRecordCount,
      registerStep: registerController.registerStep,
      setRegisterStep: registerController.setRegisterStep,
      registerSuccess: registerController.registerSuccess,
      registerPreviewProjects: registerController.registerPreviewProjects,
      projectTypeOptions,
      typeIcon,
      typeLabel,
      onStartInspectionFromSuccess: registerFlowController.startInspectionFromRegisterSuccess,
      onGoProjects,
      onResetRegister: registerFlowController.handleResetRegister,
      onOpenProjectDetail,
      onEnterInspection: registerFlowController.enterInspection,
      regForm: registerController.regForm,
      setRegForm: registerController.setRegForm,
      settings,
      setErpBinding: registerController.setErpBinding,
      pullErpProjectBinding: registerFlowController.pullErpProjectBinding,
      erpBindingLoading: registerController.erpBindingLoading,
      erpBinding: registerController.erpBinding,
      regUri: registerController.regUri,
      vpathStatus: registerController.vpathStatus,
      segType: registerController.segType,
      setSegType: registerController.setSegType,
      regKmInterval: registerController.regKmInterval,
      setRegKmInterval: registerController.setRegKmInterval,
      contractSegs: registerController.contractSegs,
      setContractSegs: registerController.setContractSegs,
      addContractSeg: registerController.addContractSeg,
      structures: registerController.structures,
      setStructures: registerController.setStructures,
      addStructure: registerController.addStructure,
      inspectionTypeOptions,
      regInspectionTypes: registerController.regInspectionTypes,
      setRegInspectionTypes: registerController.setRegInspectionTypes,
      toggleInspectionType: registerController.toggleInspectionType,
      regRangeTreeLines: registerController.regRangeTreeLines,
      zeroLedgerTab: registerController.zeroLedgerTab,
      setZeroLedgerTab: registerController.setZeroLedgerTab,
      zeroPersonnel: registerController.zeroPersonnel,
      setZeroPersonnel: registerController.setZeroPersonnel,
      zeroEquipment: registerController.zeroEquipment,
      setZeroEquipment: registerController.setZeroEquipment,
      zeroSubcontracts: registerController.zeroSubcontracts,
      setZeroSubcontracts: registerController.setZeroSubcontracts,
      zeroMaterials: registerController.zeroMaterials,
      setZeroMaterials: registerController.setZeroMaterials,
      makeRowId: registerController.makeRowId,
      buildExecutorUri: registerController.buildExecutorUri,
      buildToolUri: registerController.buildToolUri,
      buildSubcontractUri: registerController.buildSubcontractUri,
      getEquipmentValidity: registerController.getEquipmentValidity,
      zeroLedgerTreeRows: registerController.zeroLedgerTreeRows,
      zeroLedgerSummary: registerController.zeroLedgerSummary,
      prevRegStep: registerController.prevRegStep,
      nextRegStep: registerController.nextRegStep,
      submitRegister: registerFlowController.submitRegister,
      inspectionTypeLabel,
    },
  }
}

export function buildTeamWorkspace({
  projects,
  permissionTreeRoot,
  permissionColumns,
  permissionRoleLabel,
  teamAccessController,
}: BuildTeamWorkspaceArgs): TeamWorkspaceProps {
  return {
    teamPanelProps: {
      members: teamAccessController.members,
      memberRoleDrafts: teamAccessController.memberRoleDrafts,
      onOpenInvite: teamAccessController.openInvite,
      onDraftRoleChange: teamAccessController.updateMemberRoleDraft,
      onSaveMemberRole: teamAccessController.saveMemberRole,
      onRemoveMember: teamAccessController.removeMember,
    },
    permissionsPanelProps: {
      permissionTemplate: teamAccessController.permissionTemplate,
      permissionMatrix: teamAccessController.permissionMatrix,
      permissionColumns,
      permissionRoleLabel,
      permissionTreeRoot,
      permissionTreeRows: teamAccessController.permissionTreeRows,
      onApplyTemplate: teamAccessController.applyPermissionTemplate,
      onUpdateCell: teamAccessController.updatePermissionCell,
      onSaveMatrix: teamAccessController.persistPermissionMatrix,
    },
    inviteMemberModalProps: {
      open: teamAccessController.inviteOpen,
      form: teamAccessController.inviteForm,
      projects,
      onChange: teamAccessController.setInviteForm,
      onClose: teamAccessController.closeInvite,
      onSubmit: teamAccessController.addMember,
    },
  }
}

export function buildSettingsWorkspace({
  settingsController,
}: BuildSettingsWorkspaceArgs): SettingsWorkspaceProps {
  return {
    settingsPanelProps: {
      enterpriseInfo: settingsController.enterpriseInfo,
      setEnterpriseInfo: settingsController.setEnterpriseInfo,
      persistEnterpriseInfo: settingsController.persistEnterpriseInfo,
      settings: settingsController.settings,
      setSettings: settingsController.setSettings,
      persistSettings: settingsController.persistSettings,
      setReportTemplateFile: settingsController.setReportTemplateFile,
      persistReportTemplate: settingsController.persistReportTemplate,
      verifyGitpegToken: settingsController.verifyGitpegToken,
      gitpegVerifying: settingsController.gitpegVerifying,
      gitpegVerifyMsg: settingsController.gitpegVerifyMsg,
      setGitpegVerifyMsg: settingsController.setGitpegVerifyMsg,
      setGitpegVerifying: settingsController.setGitpegVerifying,
      erpDraft: settingsController.erpDraft,
      setErpDraft: settingsController.setErpDraft,
      testErpConnection: settingsController.testErpConnection,
      erpTesting: settingsController.erpTesting,
      erpTestMsg: settingsController.erpTestMsg,
      erpWritebackDraft: settingsController.erpWritebackDraft,
      setErpWritebackDraft: settingsController.setErpWritebackDraft,
      testWebhook: settingsController.testWebhook,
      webhookTesting: settingsController.webhookTesting,
      webhookResult: settingsController.webhookResult,
    },
  }
}
