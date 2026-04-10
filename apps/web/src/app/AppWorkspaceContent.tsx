import type { ComponentProps } from 'react'

import Dashboard from '../pages/Dashboard'
import InspectionPage from '../pages/InspectionPage'
import ReportsPage from '../pages/ReportsPage'
import SiteRecordsPage from '../pages/SiteRecordsPage'
import ProofPanel from '../components/proof/ProofPanel'
import ProjectsPanel from '../components/projects/ProjectsPanel'
import TeamPanel from '../components/team/TeamPanel'
import PermissionsPanel from '../components/permissions/PermissionsPanel'
import SettingsPanel from '../components/settings/SettingsPanel'
import InviteMemberModal from '../components/team/InviteMemberModal'
import ProjectDetailDrawer from '../components/projects/ProjectDetailDrawer'

export type ProofWorkspaceProps = {
  proofPanelProps: ComponentProps<typeof ProofPanel>
}

export type ProjectsWorkspaceProps = {
  projectsPanelProps: ComponentProps<typeof ProjectsPanel>
  projectDetailDrawerProps: ComponentProps<typeof ProjectDetailDrawer>
}

export type TeamWorkspaceProps = {
  teamPanelProps: ComponentProps<typeof TeamPanel>
  permissionsPanelProps: ComponentProps<typeof PermissionsPanel>
  inviteMemberModalProps: ComponentProps<typeof InviteMemberModal>
}

export type SettingsWorkspaceProps = {
  settingsPanelProps: ComponentProps<typeof SettingsPanel>
}

type Props = {
  activeTab: string
  proofWorkspace: ProofWorkspaceProps
  projectsWorkspace: ProjectsWorkspaceProps
  teamWorkspace: TeamWorkspaceProps
  settingsWorkspace: SettingsWorkspaceProps
}

export default function AppWorkspaceContent({
  activeTab,
  proofWorkspace,
  projectsWorkspace,
  teamWorkspace,
  settingsWorkspace,
}: Props) {
  return (
    <>
      {activeTab === 'dashboard' && <Dashboard />}
      {activeTab === 'inspection' && <InspectionPage />}
      {activeTab === 'records' && <SiteRecordsPage />}
      {activeTab === 'reports' && <ReportsPage />}
      {activeTab === 'proof' && <ProofPanel {...proofWorkspace.proofPanelProps} />}

      {activeTab === 'projects' && <ProjectsPanel {...projectsWorkspace.projectsPanelProps} />}
      {activeTab === 'team' && <TeamPanel {...teamWorkspace.teamPanelProps} />}
      {activeTab === 'permissions' && <PermissionsPanel {...teamWorkspace.permissionsPanelProps} />}
      {activeTab === 'settings' && <SettingsPanel {...settingsWorkspace.settingsPanelProps} />}

      <InviteMemberModal {...teamWorkspace.inviteMemberModalProps} />
      <ProjectDetailDrawer {...projectsWorkspace.projectDetailDrawerProps} />
    </>
  )
}
