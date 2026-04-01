import type { ComponentProps } from 'react'

import AppWorkspaceContent from './AppWorkspaceContent'

type WorkspaceContentProps = ComponentProps<typeof AppWorkspaceContent>

type UseAppWorkspacePropsArgs = {
  activeTab: WorkspaceContentProps['activeTab']
  proofWorkspace: WorkspaceContentProps['proofWorkspace']
  projectsWorkspace: WorkspaceContentProps['projectsWorkspace']
  registerWorkspace: WorkspaceContentProps['registerWorkspace']
  teamWorkspace: WorkspaceContentProps['teamWorkspace']
  settingsWorkspace: WorkspaceContentProps['settingsWorkspace']
}

function buildProofWorkspace(
  proofWorkspace: UseAppWorkspacePropsArgs['proofWorkspace'],
): WorkspaceContentProps['proofWorkspace'] {
  return {
    projectUri: proofWorkspace.projectUri,
    proofPanelProps: proofWorkspace.proofPanelProps,
    paymentAuditPanelProps: proofWorkspace.paymentAuditPanelProps,
    spatialGovernancePanelProps: proofWorkspace.spatialGovernancePanelProps,
    rwaOmEvolutionPanelProps: proofWorkspace.rwaOmEvolutionPanelProps,
  }
}

function buildProjectsWorkspace(
  projectsWorkspace: UseAppWorkspacePropsArgs['projectsWorkspace'],
): WorkspaceContentProps['projectsWorkspace'] {
  return {
    projectsPanelProps: projectsWorkspace.projectsPanelProps,
    projectDetailDrawerProps: projectsWorkspace.projectDetailDrawerProps,
  }
}

function buildRegisterWorkspace(
  registerWorkspace: UseAppWorkspacePropsArgs['registerWorkspace'],
): WorkspaceContentProps['registerWorkspace'] {
  return {
    registerWorkspaceProps: registerWorkspace.registerWorkspaceProps,
  }
}

function buildTeamWorkspace(
  teamWorkspace: UseAppWorkspacePropsArgs['teamWorkspace'],
): WorkspaceContentProps['teamWorkspace'] {
  return {
    teamPanelProps: teamWorkspace.teamPanelProps,
    permissionsPanelProps: teamWorkspace.permissionsPanelProps,
    inviteMemberModalProps: teamWorkspace.inviteMemberModalProps,
  }
}

function buildSettingsWorkspace(
  settingsWorkspace: UseAppWorkspacePropsArgs['settingsWorkspace'],
): WorkspaceContentProps['settingsWorkspace'] {
  return {
    settingsPanelProps: settingsWorkspace.settingsPanelProps,
  }
}

export function useAppWorkspaceProps(args: UseAppWorkspacePropsArgs): WorkspaceContentProps {
  return {
    activeTab: args.activeTab,
    proofWorkspace: buildProofWorkspace(args.proofWorkspace),
    projectsWorkspace: buildProjectsWorkspace(args.projectsWorkspace),
    registerWorkspace: buildRegisterWorkspace(args.registerWorkspace),
    teamWorkspace: buildTeamWorkspace(args.teamWorkspace),
    settingsWorkspace: buildSettingsWorkspace(args.settingsWorkspace),
  }
}
