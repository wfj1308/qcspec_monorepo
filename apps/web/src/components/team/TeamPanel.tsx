import type { TeamRole } from '../../app/appShellShared'

interface TeamMemberItem {
  id: string
  name: string
  title: string
  email: string
  role: TeamRole
  color: string
  projects: string[]
}

interface TeamPanelProps {
  members: TeamMemberItem[]
  memberRoleDrafts: Record<string, TeamRole>
  onOpenInvite: () => void
  onDraftRoleChange: (memberId: string, role: TeamRole) => void
  onSaveMemberRole: (member: TeamMemberItem) => void
  onRemoveMember: (memberId: string) => void
}

export default function TeamPanel({
  members,
  memberRoleDrafts,
  onOpenInvite,
  onDraftRoleChange,
  onSaveMemberRole,
  onRemoveMember,
}: TeamPanelProps) {
  return (
    <div>
      <div className="toolbar" style={{ justifyContent: 'space-between' }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: '#0F172A' }}>团队成员</div>
        <button className="btn-primary" style={{ flex: 'none' }} onClick={onOpenInvite}>
          ＋ 邀请成员
        </button>
      </div>
      <div className="member-grid">
        {members.map((member) => {
          const roleClass =
            member.role === 'OWNER'
              ? 'role-owner'
              : member.role === 'SUPERVISOR'
                ? 'role-supervisor'
                : member.role === 'AI'
                  ? 'role-inspector'
                  : 'role-viewer'
          const roleLabel =
            member.role === 'OWNER' ? '管理员' : member.role === 'SUPERVISOR' ? '监理' : member.role === 'AI' ? '质检员' : '只读'

          return (
            <div key={member.id} className="member-card">
              <div className="member-header">
                <div className="member-avatar" style={{ background: member.color }}>
                  {member.name.slice(0, 1)}
                </div>
                <div>
                  <div className="member-name">{member.name}</div>
                  <div className="member-title">{member.title}</div>
                </div>
              </div>
              <span className={`role-badge ${roleClass}`}>{roleLabel}</span>
              <div className="member-projects">参与项目：{member.projects.length} 个</div>
              <div style={{ fontSize: 12, color: '#94A3B8' }}>{member.email}</div>
              <div style={{ display: 'grid', gap: 6 }}>
                <select
                  className="setting-select"
                  value={memberRoleDrafts[member.id] || member.role}
                  onChange={(e) => onDraftRoleChange(member.id, e.target.value as TeamRole)}
                >
                  <option value="AI">质检员（AI）</option>
                  <option value="SUPERVISOR">监理</option>
                  <option value="OWNER">管理员</option>
                  <option value="PUBLIC">只读</option>
                </select>
                <div className="member-actions">
                  <button className="act-btn act-edit" onClick={() => onSaveMemberRole(member)}>
                    保存角色
                  </button>
                  <button className="act-btn act-del" onClick={() => onRemoveMember(member.id)}>
                    移除
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
