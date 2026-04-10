import React, { useState } from 'react'
import type { ComponentProps } from 'react'

import Dashboard from '../pages/Dashboard'
import InspectionPage from '../pages/InspectionPage'
import PhotosPage from '../pages/PhotosPage'
import ReportsPage from '../pages/ReportsPage'
import LogPegPage from '../pages/LogPegPage'
import NormRefRulesPage from '../pages/NormRefRulesPage'
import ExecutorAdminPage from '../pages/ExecutorAdminPage'
import ExecutorRegisterPage from '../pages/ExecutorRegisterPage'
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
  const [proofSection, setProofSection] = useState<'overview' | 'pay' | 'spatial' | 'rwa' | 'docs'>('overview')

  return (
    <>
      {activeTab === 'dashboard' && <Dashboard />}
      {activeTab === 'inspection' && <InspectionPage />}
      {activeTab === 'photos' && <PhotosPage />}
      {activeTab === 'normref' && <NormRefRulesPage />}
      {activeTab === 'reports' && <ReportsPage />}
      {activeTab === 'logpeg' && <LogPegPage />}
      {activeTab === 'executors' && <ExecutorAdminPage />}
      {activeTab === 'executor-register' && <ExecutorRegisterPage />}

      {activeTab === 'proof' && (
        <>
          <div
            style={{
              display: 'flex',
              gap: 8,
              flexWrap: 'wrap',
              marginBottom: 12,
              position: 'sticky',
              top: 56,
              zIndex: 90,
              background: '#F0F4F8',
              paddingBottom: 8,
            }}
          >
            <button
              type="button"
              className={`act-btn ${proofSection === 'overview' ? 'act-enter' : 'act-detail'}`}
              onClick={() => setProofSection('overview')}
            >
              总览存证链
            </button>
            <button
              type="button"
              className={`act-btn ${proofSection === 'pay' ? 'act-enter' : 'act-detail'}`}
              onClick={() => setProofSection('pay')}
            >
              支付审计
            </button>
            <button
              type="button"
              className={`act-btn ${proofSection === 'spatial' ? 'act-enter' : 'act-detail'}`}
              onClick={() => setProofSection('spatial')}
            >
              空间孪生
            </button>
            <button
              type="button"
              className={`act-btn ${proofSection === 'rwa' ? 'act-enter' : 'act-detail'}`}
              onClick={() => setProofSection('rwa')}
            >
              RWA + 运维
            </button>
            <button
              type="button"
              className={`act-btn ${proofSection === 'docs' ? 'act-enter' : 'act-detail'}`}
              onClick={() => setProofSection('docs')}
            >
              文档治理
            </button>
          </div>

          {proofSection === 'overview' && <ProofPanel {...proofWorkspace.proofPanelProps} />}
          {proofSection === 'pay' && <PaymentAuditPanel {...proofWorkspace.paymentAuditPanelProps} />}
          {proofSection === 'spatial' && <SpatialGovernancePanel {...proofWorkspace.spatialGovernancePanelProps} />}
          {proofSection === 'rwa' && <RwaOmEvolutionPanel {...proofWorkspace.rwaOmEvolutionPanelProps} />}
          {proofSection === 'docs' && <DocumentGovernancePanel projectUri={proofWorkspace.projectUri} />}
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
