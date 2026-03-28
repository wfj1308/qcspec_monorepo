import type { Dispatch, SetStateAction } from 'react'
import type { InviteFormState } from '../components/team/InviteMemberModal'
import type { TeamMember, TeamRole } from './appShellShared'
import { ROLE_LABEL, normalizeTeamRole, roleToTitle, toRoleDraftMap } from './appShellShared'

interface TeamMemberApiRow {
  id: string
  name?: string
  title?: string
  email?: string
  dto_role?: string
  projects?: string[]
}

interface AddMemberFlowArgs {
  inviteForm: InviteFormState
  projects: Array<{ id: string }>
  fallbackProjectId: string
  canUseEnterpriseApi: boolean
  enterpriseId?: string
  inviteMember: (payload: Record<string, unknown>) => Promise<unknown>
  listMembers: (enterpriseId: string) => Promise<unknown>
  setMembers: Dispatch<SetStateAction<TeamMember[]>>
  setMemberRoleDrafts: Dispatch<SetStateAction<Record<string, TeamRole>>>
  setInviteForm: (value: InviteFormState) => void
  setInviteOpen: (value: boolean) => void
  showToast: (message: string) => void
}

interface RemoveMemberFlowArgs {
  memberId: string
  canUseEnterpriseApi: boolean
  removeMemberApi: (memberId: string) => Promise<unknown>
  setMembers: Dispatch<SetStateAction<TeamMember[]>>
  setMemberRoleDrafts: Dispatch<SetStateAction<Record<string, TeamRole>>>
  showToast: (message: string) => void
}

interface SaveMemberRoleFlowArgs {
  member: TeamMember
  memberRoleDrafts: Record<string, TeamRole>
  canUseEnterpriseApi: boolean
  updateMemberApi: (memberId: string, payload: Record<string, unknown>) => Promise<unknown>
  setMembers: Dispatch<SetStateAction<TeamMember[]>>
  showToast: (message: string) => void
}

const REMOTE_MEMBER_COLORS = ['#1A56DB', '#059669', '#7C3AED', '#D97706', '#0891B2']
const LOCAL_MEMBER_COLORS = ['#1A56DB', '#059669', '#7C3AED', '#D97706']

const invitedProjectIdsFromForm = (
  inviteForm: InviteFormState,
  projects: Array<{ id: string }>,
  fallbackProjectId: string
): string[] => {
  if (inviteForm.projectId === 'all') return projects.map((project) => project.id)
  if (inviteForm.projectId) return [inviteForm.projectId]
  return [fallbackProjectId]
}

const mapRemoteMembers = (rows: TeamMemberApiRow[]): TeamMember[] =>
  rows.map((row, idx) => {
    const role = normalizeTeamRole(row.dto_role, 'PUBLIC')
    return {
      id: row.id,
      name: row.name || '未命名成员',
      title: row.title || roleToTitle(role),
      email: row.email || '',
      role,
      color: REMOTE_MEMBER_COLORS[idx % REMOTE_MEMBER_COLORS.length],
      projects: row.projects || [],
    }
  })

const dropRoleDraft = (
  prev: Record<string, TeamRole>,
  memberId: string
): Record<string, TeamRole> => {
  const next = { ...prev }
  delete next[memberId]
  return next
}

export async function addMemberFlow({
  inviteForm,
  projects,
  fallbackProjectId,
  canUseEnterpriseApi,
  enterpriseId,
  inviteMember,
  listMembers,
  setMembers,
  setMemberRoleDrafts,
  setInviteForm,
  setInviteOpen,
  showToast,
}: AddMemberFlowArgs): Promise<void> {
  if (!inviteForm.name || !inviteForm.email) {
    showToast('请填写成员姓名和邮箱')
    return
  }

  const invitedProjectIds = invitedProjectIdsFromForm(inviteForm, projects, fallbackProjectId)

  if (canUseEnterpriseApi && enterpriseId) {
    const res = (await inviteMember({
      enterprise_id: enterpriseId,
      name: inviteForm.name,
      email: inviteForm.email,
      dto_role: inviteForm.role,
      title: roleToTitle(inviteForm.role),
      project_ids: invitedProjectIds,
    })) as { data?: { id?: string } } | null

    if (res?.data?.id) {
      const refreshed = (await listMembers(enterpriseId)) as { data?: TeamMemberApiRow[] } | null
      if (refreshed?.data) {
        const mapped = mapRemoteMembers(refreshed.data)
        setMembers(mapped)
        setMemberRoleDrafts(toRoleDraftMap(mapped))
      }
    }
  } else {
    const localId = `u-${Date.now()}`
    setMembers((prev) => [
      {
        id: localId,
        name: inviteForm.name,
        title: roleToTitle(inviteForm.role),
        email: inviteForm.email,
        role: inviteForm.role,
        color: LOCAL_MEMBER_COLORS[prev.length % LOCAL_MEMBER_COLORS.length],
        projects: invitedProjectIds,
      },
      ...prev,
    ])
    setMemberRoleDrafts((prev) => ({ ...prev, [localId]: inviteForm.role }))
  }

  setInviteForm({ name: '', email: '', role: 'AI', projectId: 'all' })
  setInviteOpen(false)
  showToast('已邀请新成员')
}

export async function removeMemberFlow({
  memberId,
  canUseEnterpriseApi,
  removeMemberApi,
  setMembers,
  setMemberRoleDrafts,
  showToast,
}: RemoveMemberFlowArgs): Promise<void> {
  if (canUseEnterpriseApi) {
    const res = (await removeMemberApi(memberId)) as { ok?: boolean } | null
    if (!res?.ok) return
  }

  setMembers((prev) => prev.filter((member) => member.id !== memberId))
  setMemberRoleDrafts((prev) => dropRoleDraft(prev, memberId))
  showToast('成员已移除')
}

export async function saveMemberRoleFlow({
  member,
  memberRoleDrafts,
  canUseEnterpriseApi,
  updateMemberApi,
  setMembers,
  showToast,
}: SaveMemberRoleFlowArgs): Promise<void> {
  const nextRole = memberRoleDrafts[member.id] || member.role
  if (nextRole === member.role) {
    showToast('角色未变化')
    return
  }

  if (canUseEnterpriseApi) {
    const res = (await updateMemberApi(member.id, {
      dto_role: nextRole,
      title: roleToTitle(nextRole),
    })) as { data?: { id?: string } } | null
    if (!res) return
  }

  setMembers((prev) =>
    prev.map((item) =>
      item.id === member.id ? { ...item, role: nextRole, title: roleToTitle(nextRole) } : item
    )
  )
  showToast(`成员角色已更新：${member.name} -> ${ROLE_LABEL[nextRole]}`)
}

