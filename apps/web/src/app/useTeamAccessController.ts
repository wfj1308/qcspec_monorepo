import { useMemo, useState } from 'react'
import type { Project } from '@qcspec/types'
import type { InviteFormState } from '../components/team/InviteMemberModal'
import type {
  PermTemplate,
  PermissionKey,
  PermissionRole,
  PermissionRow,
  TeamMember,
  TeamRole,
} from './appShellShared'
import {
  DEFAULT_PERMISSION_MATRIX,
  PERMISSION_COLUMNS,
  detectPermissionTemplate,
  normalizePermissionMatrix,
} from './appShellShared'
import { addMemberFlow, removeMemberFlow, saveMemberRoleFlow } from './teamMemberFlows'
import { applyPermissionTemplateFlow, persistPermissionMatrixFlow, updatePermissionCellFlow } from './permissionFlows'

interface UseTeamAccessControllerArgs {
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  projects: Project[]
  currentProjectId: string
  saveSettings: (enterpriseId: string, patch: Record<string, unknown>) => Promise<unknown>
  inviteMember: (payload: Record<string, unknown>) => Promise<unknown>
  listMembers: (enterpriseId: string) => Promise<unknown>
  updateMemberApi: (memberId: string, payload: Record<string, unknown>) => Promise<unknown>
  removeMemberApi: (memberId: string) => Promise<unknown>
  showToast: (message: string) => void
}

const DEFAULT_MEMBERS: TeamMember[] = []
const DEFAULT_ROLE_DRAFTS: Record<string, TeamRole> = {}

export function useTeamAccessController({
  canUseEnterpriseApi,
  enterpriseId,
  projects,
  currentProjectId,
  saveSettings,
  inviteMember,
  listMembers,
  updateMemberApi,
  removeMemberApi,
  showToast,
}: UseTeamAccessControllerArgs) {
  const [inviteOpen, setInviteOpen] = useState(false)
  const [members, setMembers] = useState<TeamMember[]>(DEFAULT_MEMBERS)
  const [inviteForm, setInviteForm] = useState<InviteFormState>({
    name: '',
    email: '',
    role: 'AI',
    projectId: 'all',
  })
  const [memberRoleDrafts, setMemberRoleDrafts] = useState<Record<string, TeamRole>>(DEFAULT_ROLE_DRAFTS)
  const [permissionMatrix, setPermissionMatrix] = useState<PermissionRow[]>(() =>
    normalizePermissionMatrix(DEFAULT_PERMISSION_MATRIX)
  )
  const [permissionTemplate, setPermissionTemplate] = useState<PermTemplate>(() =>
    detectPermissionTemplate(normalizePermissionMatrix(DEFAULT_PERMISSION_MATRIX))
  )

  const permissionTreeRows = useMemo(
    () =>
      permissionMatrix.map((row) => {
        const granted = PERMISSION_COLUMNS.filter((col) => row[col.key]).map((col) => col.label)
        return {
          role: row.role,
          granted: granted.length > 0 ? granted.join(' / ') : '无权限',
        }
      }),
    [permissionMatrix]
  )

  const openInvite = () => setInviteOpen(true)
  const closeInvite = () => setInviteOpen(false)

  const updateMemberRoleDraft = (memberId: string, role: TeamRole) => {
    setMemberRoleDrafts((prev) => ({ ...prev, [memberId]: role }))
  }

  const addMember = async () => {
    await addMemberFlow({
      inviteForm,
      projects,
      fallbackProjectId: currentProjectId,
      canUseEnterpriseApi,
      enterpriseId,
      inviteMember,
      listMembers,
      setMembers,
      setMemberRoleDrafts,
      setInviteForm,
      setInviteOpen,
      showToast,
    })
  }

  const removeMember = async (memberId: string) => {
    await removeMemberFlow({
      memberId,
      canUseEnterpriseApi,
      removeMemberApi,
      setMembers,
      setMemberRoleDrafts,
      showToast,
    })
  }

  const saveMemberRole = async (member: TeamMember) => {
    await saveMemberRoleFlow({
      member,
      memberRoleDrafts,
      canUseEnterpriseApi,
      updateMemberApi,
      setMembers,
      showToast,
    })
  }

  const updatePermissionCell = (role: PermissionRole, key: PermissionKey, value: boolean) => {
    updatePermissionCellFlow(role, key, value, setPermissionMatrix, setPermissionTemplate)
  }

  const applyPermissionTemplate = (template: Exclude<PermTemplate, 'custom'>) => {
    applyPermissionTemplateFlow(template, setPermissionTemplate, setPermissionMatrix)
  }

  const persistPermissionMatrix = async () => {
    await persistPermissionMatrixFlow({
      canUseEnterpriseApi,
      enterpriseId,
      permissionMatrix,
      saveSettings,
      setPermissionMatrix,
      setPermissionTemplate,
      showToast,
    })
  }

  return {
    inviteOpen,
    openInvite,
    closeInvite,
    inviteForm,
    setInviteForm,
    members,
    setMembers,
    memberRoleDrafts,
    setMemberRoleDrafts,
    updateMemberRoleDraft,
    addMember,
    removeMember,
    saveMemberRole,
    permissionMatrix,
    setPermissionMatrix,
    permissionTemplate,
    setPermissionTemplate,
    permissionTreeRows,
    updatePermissionCell,
    applyPermissionTemplate,
    persistPermissionMatrix,
  }
}
