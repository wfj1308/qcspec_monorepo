import type { ProjectRegisterMeta } from './appShellShared'
import type {
  ProofWorkspaceProps,
  ProjectsWorkspaceProps,
  TeamWorkspaceProps,
  SettingsWorkspaceProps,
} from './AppWorkspaceContent'
import type { useProofDashboardController } from './useProofDashboardController'
import type { useProjectCatalogController } from './useProjectCatalogController'
import type { useProjectDetailController } from './useProjectDetailController'
import type { useTeamAccessController } from './useTeamAccessController'
import type { useSettingsController } from './useSettingsController'

type ProofDashboardController = ReturnType<typeof useProofDashboardController>
type ProjectCatalogController = ReturnType<typeof useProjectCatalogController>
type ProjectDetailController = ReturnType<typeof useProjectDetailController>
type TeamAccessController = ReturnType<typeof useTeamAccessController>
type SettingsController = ReturnType<typeof useSettingsController>
type ProjectInspectionTarget = Parameters<ProjectsWorkspaceProps['projectsPanelProps']['onEnterInspection']>[0]

type BuildProofWorkspaceArgs = {
  proofDashboard: ProofDashboardController
  onGoInspection?: () => void
  onGoReports?: () => void
}

type BuildProjectsWorkspaceArgs = {
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
  onEnterInspection: (project: ProjectInspectionTarget) => void
  onEnterProof: (project: ProjectInspectionTarget) => void
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
  proofDashboard,
  onGoInspection,
  onGoReports,
}: BuildProofWorkspaceArgs): ProofWorkspaceProps {
  return {
    proofPanelProps: {
      projectUri: proofDashboard.projectUri,
      proofStats: proofDashboard.proofStats,
      proofNodeRows: proofDashboard.proofNodeRows,
      proofLoading: proofDashboard.proofLoading,
      proofRows: proofDashboard.proofRows,
      proofVerifying: proofDashboard.proofVerifying,
      onVerifyProof: proofDashboard.handleVerifyProof,
      onGoInspection,
      onGoReports,
    },
  }
}

export function buildProjectsWorkspace({
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
      onSearchTextChange: projectCatalog.setSearchText,
      onStatusFilterChange: projectCatalog.setStatusFilter,
      onTypeFilterChange: projectCatalog.setTypeFilter,
      onEnterInspection,
      onEnterProof,
      onEditProject: (projectId) => projectDetailController.openProjectDetail(projectId, true),
      onOpenProjectDetail: (projectId) => projectDetailController.openProjectDetail(projectId),
      onDeleteProject: projectCatalog.removeProject,
    },
    projectDetailDrawerProps: {
      open: projectDetailController.projectDetailOpen,
      detailProject: projectDetailController.detailProject,
      detailEdit: projectDetailController.detailEdit,
      detailProjectDraft: projectDetailController.detailProjectDraft,
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
