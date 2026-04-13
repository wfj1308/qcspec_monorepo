import type { ComponentProps } from 'react'

import ProjectsPanel from '../components/projects/ProjectsPanel'
import ProjectDetailDrawer from '../components/projects/ProjectDetailDrawer'
import TeamPanel from '../components/team/TeamPanel'
import InviteMemberModal from '../components/team/InviteMemberModal'
import PermissionsPanel from '../components/permissions/PermissionsPanel'
import SettingsPanel from '../components/settings/SettingsPanel'
import ProofPanel from '../components/proof/ProofPanel'
import InspectionPage from '../pages/InspectionPage'
import ReportsPage from '../pages/ReportsPage'

export type ProjectsWorkspaceProps = {
  projectsPanelProps: ComponentProps<typeof ProjectsPanel>
  projectDetailDrawerProps: ComponentProps<typeof ProjectDetailDrawer>
}

export type TeamWorkspaceProps = {
  teamPanelProps: ComponentProps<typeof TeamPanel>
  inviteMemberModalProps: ComponentProps<typeof InviteMemberModal>
}

export type PermissionsWorkspaceProps = {
  permissionsPanelProps: ComponentProps<typeof PermissionsPanel>
}

export type SettingsWorkspaceProps = {
  settingsPanelProps: ComponentProps<typeof SettingsPanel>
}

export type ProofWorkspaceProps = {
  proofPanelProps: ComponentProps<typeof ProofPanel>
}

type Props = {
  activeTab: string
  projectsWorkspace: ProjectsWorkspaceProps
  teamWorkspace: TeamWorkspaceProps
  permissionsWorkspace: PermissionsWorkspaceProps
  settingsWorkspace: SettingsWorkspaceProps
  proofWorkspace: ProofWorkspaceProps
}

export default function AppWorkspaceContent({
  activeTab,
  projectsWorkspace,
  teamWorkspace,
  permissionsWorkspace,
  settingsWorkspace,
  proofWorkspace,
}: Props) {
  return (
    <>
      {activeTab === 'projects' && <ProjectsPanel {...projectsWorkspace.projectsPanelProps} />}
      {activeTab === 'inspection' && <InspectionPage />}
      {activeTab === 'reports' && <ReportsPage />}
      {activeTab === 'proof' && <ProofPanel {...proofWorkspace.proofPanelProps} />}
      {activeTab === 'team' && (
        <>
          <TeamPanel {...teamWorkspace.teamPanelProps} />
          <InviteMemberModal {...teamWorkspace.inviteMemberModalProps} />
        </>
      )}
      {activeTab === 'permissions' && <PermissionsPanel {...permissionsWorkspace.permissionsPanelProps} />}
      {activeTab === 'settings' && <SettingsPanel {...settingsWorkspace.settingsPanelProps} />}
      <ProjectDetailDrawer {...projectsWorkspace.projectDetailDrawerProps} />
    </>
  )
}
