interface ProjectCreateModalProps {
  open: boolean
  submitting?: boolean
  code: string
  name: string
  type: string
  ownerUnit: string
  typeOptions: Array<{ value: string; label: string }>
  error?: string
  onChangeCode: (value: string) => void
  onChangeName: (value: string) => void
  onChangeType: (value: string) => void
  onChangeOwnerUnit: (value: string) => void
  onClose: () => void
  onSubmit: () => void
}

export default function ProjectCreateModal({
  open,
  submitting = false,
  code,
  name,
  type,
  ownerUnit,
  typeOptions,
  error,
  onChangeCode,
  onChangeName,
  onChangeType,
  onChangeOwnerUnit,
  onClose,
  onSubmit,
}: ProjectCreateModalProps) {
  if (!open) return null

  return (
    <div className="project-create-mask" onClick={onClose}>
      <div className="project-create-panel" onClick={(e) => e.stopPropagation()}>
        <div className="project-create-title">创建项目</div>
        <div className="project-create-form">
          <label className="project-create-label" htmlFor="project-create-code">
            项目编码
          </label>
          <input
            id="project-create-code"
            className="setting-input"
            value={code}
            placeholder="如：PJT-YA-GS-001"
            onChange={(e) => onChangeCode(e.target.value)}
            autoFocus
          />

          <label className="project-create-label" htmlFor="project-create-name">
            项目名称
          </label>
          <input
            id="project-create-name"
            className="setting-input"
            value={name}
            placeholder="请输入项目名称"
            onChange={(e) => onChangeName(e.target.value)}
          />

          <label className="project-create-label" htmlFor="project-create-type">
            项目类型
          </label>
          <select
            id="project-create-type"
            className="setting-select"
            value={type}
            onChange={(e) => onChangeType(e.target.value)}
          >
            {typeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <label className="project-create-label" htmlFor="project-create-owner-unit">
            业主单位
          </label>
          <input
            id="project-create-owner-unit"
            className="setting-input"
            value={ownerUnit}
            placeholder="请输入业主单位"
            onChange={(e) => onChangeOwnerUnit(e.target.value)}
          />

          {error ? <div className="project-create-error">{error}</div> : null}
        </div>

        <div className="project-create-row">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
            取消
          </button>
          <button type="button" className="btn-primary" onClick={onSubmit} disabled={submitting}>
            {submitting ? '创建中...' : '确定'}
          </button>
        </div>
      </div>
    </div>
  )
}
