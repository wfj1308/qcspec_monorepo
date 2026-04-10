import type { TeamRole } from '../../app/appShellShared'

export interface InviteFormState {
  name: string
  email: string
  role: TeamRole
  projectId: string
}

interface InviteMemberModalProps {
  open: boolean
  form: InviteFormState
  projects: Array<{ id: string; name: string }>
  onChange: (next: InviteFormState) => void
  onClose: () => void
  onSubmit: () => void
}

export default function InviteMemberModal({
  open,
  form,
  projects,
  onChange,
  onClose,
  onSubmit,
}: InviteMemberModalProps) {
  if (!open) return null

  return (
    <div className="invite-mask" onClick={onClose}>
      <div className="invite-panel" onClick={(e) => e.stopPropagation()}>
        <div className="invite-title">邀请成员</div>
        <div className="invite-form">
          <input
            className="setting-input"
            value={form.name}
            placeholder="成员姓名"
            onChange={(e) => onChange({ ...form, name: e.target.value })}
          />
          <input
            className="setting-input"
            value={form.email}
            placeholder="邮箱/手机号"
            onChange={(e) => onChange({ ...form, email: e.target.value })}
          />
          <select
            className="setting-select"
            value={form.role}
            onChange={(e) => onChange({ ...form, role: e.target.value as TeamRole })}
          >
            <option value="AI">质检员</option>
            <option value="SUPERVISOR">监理</option>
            <option value="OWNER">项目管理员</option>
            <option value="PUBLIC">只读成员</option>
          </select>
          <select
            className="setting-select"
            value={form.projectId}
            onChange={(e) => onChange({ ...form, projectId: e.target.value })}
          >
            <option value="all">全部项目</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </div>
        <div className="invite-row">
          <button className="btn-secondary" onClick={onClose}>
            取消
          </button>
          <button className="btn-primary" onClick={onSubmit}>
            发送邀请
          </button>
        </div>
      </div>
    </div>
  )
}
