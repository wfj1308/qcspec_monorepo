import type { ComponentProps } from 'react'

import AppWorkspaceContent from './AppWorkspaceContent'

type WorkspaceContentProps = ComponentProps<typeof AppWorkspaceContent>

type UseAppWorkspacePropsArgs = {
  activeTab: WorkspaceContentProps['activeTab']
  proofWorkspace: WorkspaceContentProps['proofWorkspace']
  projectsWorkspace: WorkspaceContentProps['projectsWorkspace']
  teamWorkspace: WorkspaceContentProps['teamWorkspace']
  settingsWorkspace: WorkspaceContentProps['settingsWorkspace']
}

function buildProofWorkspace(
  proofWorkspace: UseAppWorkspacePropsArgs['proofWorkspace'],
): WorkspaceContentProps['proofWorkspace'] {
  return {
    proofPanelProps: proofWorkspace.proofPanelProps,
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
    teamWorkspace: buildTeamWorkspace(args.teamWorkspace),
    settingsWorkspace: buildSettingsWorkspace(args.settingsWorkspace),
  }
}
