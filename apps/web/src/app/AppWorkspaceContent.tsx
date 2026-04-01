import React from 'react'
import type { ComponentProps } from 'react'

import Dashboard from '../pages/Dashboard'
import InspectionPage from '../pages/InspectionPage'
import PhotosPage from '../pages/PhotosPage'
import ReportsPage from '../pages/ReportsPage'
import ProofPanel from '../components/proof/ProofPanel'
import PaymentAuditPanel from '../components/proof/PaymentAuditPanel'
import SpatialGovernancePanel from '../components/proof/SpatialGovernancePanel'
import RwaOmEvolutionPanel from '../components/proof/RwaOmEvolutionPanel'
import DocumentGovernancePanel from '../components/proof/DocumentGovernancePanel'
import ProjectsPanel from '../components/projects/ProjectsPanel'
import RegisterWorkspace from '../components/register/RegisterWorkspace'
import TeamPanel from '../components/team/TeamPanel'
import PermissionsPanel from '../components/permissions/PermissionsPanel'
import SettingsPanel from '../components/settings/SettingsPanel'
import InviteMemberModal from '../components/team/InviteMemberModal'
import ProjectDetailDrawer from '../components/projects/ProjectDetailDrawer'

export type ProofWorkspaceProps = {
  projectUri?: string
  proofPanelProps: ComponentProps<typeof ProofPanel>
  paymentAuditPanelProps: ComponentProps<typeof PaymentAuditPanel>
  spatialGovernancePanelProps: ComponentProps<typeof SpatialGovernancePanel>
  rwaOmEvolutionPanelProps: ComponentProps<typeof RwaOmEvolutionPanel>
}

export type ProjectsWorkspaceProps = {
  projectsPanelProps: ComponentProps<typeof ProjectsPanel>
  projectDetailDrawerProps: ComponentProps<typeof ProjectDetailDrawer>
}

export type RegisterWorkspaceProps = {
  registerWorkspaceProps: ComponentProps<typeof RegisterWorkspace>
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
  registerWorkspace: RegisterWorkspaceProps
  teamWorkspace: TeamWorkspaceProps
  settingsWorkspace: SettingsWorkspaceProps
}

export default function AppWorkspaceContent({
  activeTab,
  proofWorkspace,
  projectsWorkspace,
  registerWorkspace,
  teamWorkspace,
  settingsWorkspace,
}: Props) {
  return (
    <>
      {activeTab === 'dashboard' && <Dashboard />}
      {activeTab === 'inspection' && <InspectionPage />}
      {activeTab === 'photos' && <PhotosPage />}
      {activeTab === 'reports' && <ReportsPage />}

      {activeTab === 'proof' && (
        <>
          <ProofPanel {...proofWorkspace.proofPanelProps} />
          <PaymentAuditPanel {...proofWorkspace.paymentAuditPanelProps} />
          <SpatialGovernancePanel {...proofWorkspace.spatialGovernancePanelProps} />
          <RwaOmEvolutionPanel {...proofWorkspace.rwaOmEvolutionPanelProps} />
          <DocumentGovernancePanel projectUri={proofWorkspace.projectUri} />
        </>
      )}

      {activeTab === 'projects' && <ProjectsPanel {...projectsWorkspace.projectsPanelProps} />}
      {activeTab === 'register' && <RegisterWorkspace {...registerWorkspace.registerWorkspaceProps} />}
      {activeTab === 'team' && <TeamPanel {...teamWorkspace.teamPanelProps} />}
      {activeTab === 'permissions' && <PermissionsPanel {...teamWorkspace.permissionsPanelProps} />}
      {activeTab === 'settings' && <SettingsPanel {...settingsWorkspace.settingsPanelProps} />}

      <InviteMemberModal {...teamWorkspace.inviteMemberModalProps} />
      <ProjectDetailDrawer {...projectsWorkspace.projectDetailDrawerProps} />
    </>
  )
}
