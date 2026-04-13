import type { ComponentProps } from 'react'

import AppWorkspaceContent from './AppWorkspaceContent'

type WorkspaceContentProps = ComponentProps<typeof AppWorkspaceContent>

type UseAppWorkspacePropsArgs = {
  activeTab: WorkspaceContentProps['activeTab']
  projectsWorkspace: WorkspaceContentProps['projectsWorkspace']
  teamWorkspace: WorkspaceContentProps['teamWorkspace']
  permissionsWorkspace: WorkspaceContentProps['permissionsWorkspace']
  settingsWorkspace: WorkspaceContentProps['settingsWorkspace']
  proofWorkspace: WorkspaceContentProps['proofWorkspace']
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
    inviteMemberModalProps: teamWorkspace.inviteMemberModalProps,
  }
}

function buildPermissionsWorkspace(
  permissionsWorkspace: UseAppWorkspacePropsArgs['permissionsWorkspace'],
): WorkspaceContentProps['permissionsWorkspace'] {
  return {
    permissionsPanelProps: permissionsWorkspace.permissionsPanelProps,
  }
}

function buildSettingsWorkspace(
  settingsWorkspace: UseAppWorkspacePropsArgs['settingsWorkspace'],
): WorkspaceContentProps['settingsWorkspace'] {
  return {
    settingsPanelProps: settingsWorkspace.settingsPanelProps,
  }
}

function buildProofWorkspace(
  proofWorkspace: UseAppWorkspacePropsArgs['proofWorkspace'],
): WorkspaceContentProps['proofWorkspace'] {
  return {
    proofPanelProps: proofWorkspace.proofPanelProps,
  }
}

export function useAppWorkspaceProps(args: UseAppWorkspacePropsArgs): WorkspaceContentProps {
  return {
    activeTab: args.activeTab,
    projectsWorkspace: buildProjectsWorkspace(args.projectsWorkspace),
    teamWorkspace: buildTeamWorkspace(args.teamWorkspace),
    permissionsWorkspace: buildPermissionsWorkspace(args.permissionsWorkspace),
    settingsWorkspace: buildSettingsWorkspace(args.settingsWorkspace),
    proofWorkspace: buildProofWorkspace(args.proofWorkspace),
  }
}
