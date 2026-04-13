import type { ProjectRegisterMeta } from './appShellShared'
import type {
  ProjectsWorkspaceProps,
} from './AppWorkspaceContent'
import type { useProofDashboardController } from './useProofDashboardController'
import type { useProjectCatalogController } from './useProjectCatalogController'
import type { useProjectDetailController } from './useProjectDetailController'

type ProofDashboardController = ReturnType<typeof useProofDashboardController>
type ProjectCatalogController = ReturnType<typeof useProjectCatalogController>
type ProjectDetailController = ReturnType<typeof useProjectDetailController>
type ProjectInspectionTarget = Parameters<ProjectsWorkspaceProps['projectsPanelProps']['onEnterInspection']>[0]

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
      onCreateProject: projectCatalog.createProject,
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
